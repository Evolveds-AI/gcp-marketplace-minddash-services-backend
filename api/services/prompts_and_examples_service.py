import io
import json
from typing import Any, Dict, List, Tuple
import unicodedata

import numpy as np
import yaml
from google.cloud import aiplatform

# try:
#     from sentence_transformers import SentenceTransformer
# except Exception:
#     SentenceTransformer = None
from api.models.prompt_and_example_models import (
    ExampleDeleteRequest,
    ExampleListResponseItem,
    ExampleRegisterRequest,
    ExampleUpdateRequest,
    GetPromptsResponseByProduct,
    PromptConfig,
    PromptDeleteRequest,
    PromptRegisterRequest,
    PromptRegisterRequestV2,
    PromptUpdateRequest,
    PromptUpdateRequestV2,
)
from api.utils.db_client import execute, execute_procedure_with_out, query_all

# _MODEL_CACHE: Dict[str, object] = {}

# def _get_model(model_name: str) -> object:
#     """Obtiene un modelo de SentenceTransformer con cache simple en memoria."""
#     global _MODEL_CACHE
#     if model_name in _MODEL_CACHE:
#         return _MODEL_CACHE[model_name]
#     if SentenceTransformer is None:
#         raise RuntimeError("sentence-transformers no está disponible en el entorno")
#     model = SentenceTransformer(model_name)
#     _MODEL_CACHE[model_name] = model
#     return model


def encode_user_queries_with_vertex(
    texts: List[str],
    project_id: str,
    region: str,
    model_name: str = "gemini-embedding-001",
) -> Tuple[bytes, Dict[str, Any]]:
    """
    Genera embeddings usando la API de Vertex AI y devuelve (npy_bytes, metadata_dict).

    Args:
        texts: Lista de strings (queries/documentos) a codificar.
        project_id: ID del proyecto de Google Cloud.
        region: Región de Vertex AI donde se accede al modelo.
        model_name: El nombre del modelo de embedding de Gemini a usar.

    Returns:
        Una tupla que contiene:
        - npy_bytes: Los embeddings serializados en formato NumPy (.npy).
        - metadata: Un diccionario con metadatos de la codificación.
    """

    # --- 1. Generación de Embeddings usando Vertex AI (Tu Lógica) ---
    try:
        # Configurar el cliente para la región específica
        client_options = {"api_endpoint": f"{region}-aiplatform.googleapis.com"}
        prediction_client = aiplatform.gapic.PredictionServiceClient(
            client_options=client_options
        )

        # Definir el endpoint del modelo de Google
        # El formato para los modelos pre-entrenados de Google es:
        # projects/{PROJECT_ID}/locations/{REGION}/publishers/google/models/{MODEL_NAME}
        endpoint = f"projects/{project_id}/locations/{region}/publishers/google/models/{model_name}"

        all_embeddings = []

        # Creamos las instancias de entrada
        instances = [{"content": text} for text in texts]

        if not instances:
            # Maneja el caso de lista vacía
            embeddings_np = np.empty((0, 0), dtype=np.float32)
        else:
            print(
                f"Generando {len(texts)} embeddings con el modelo {model_name} en Vertex AI..."
            )

            # Realiza la predicción (el SDK maneja el batching/limitaciones)
            response = prediction_client.predict(
                endpoint=endpoint,
                instances=instances,
                parameters={},  # No se requieren parámetros especiales para este modelo
            )

            # Extrae los valores de los embeddings
            for prediction in response.predictions:
                # Los embeddings están anidados en 'embeddings' -> 'values'
                vector = prediction["embeddings"]["values"]
                all_embeddings.append(vector)

            # Convierte a un array de NumPy
            embeddings_np = np.array(all_embeddings, dtype=np.float32)

    except Exception as e:
        print(f"Error al generar embeddings con Vertex AI: {e}")
        raise

    # --- 2. Serializar y Metadata (Tu Formato de Salida Requerido) ---

    # Serializar el array de NumPy a bytes (.npy)
    buffer = io.BytesIO()
    np.save(buffer, embeddings_np)
    npy_bytes = buffer.getvalue()

    # Preparar metadatos
    num_examples = len(texts)
    embedding_dim = (
        int(embeddings_np.shape[1])
        if embeddings_np.ndim == 2 and embeddings_np.shape[0] > 0
        else 0
    )

    metadata = {
        "model_name": model_name,
        "num_examples": num_examples,
        "embedding_dim": embedding_dim,
        "source": "Vertex AI",  # Añadir un tag para saber la fuente del embedding
    }

    return npy_bytes, metadata


def build_examples_yaml(examples: List[Dict[str, str]]) -> str:
    """Construye YAML de ejemplos con clave 'examples'."""
    payload = {"examples": []}
    for item in examples:
        user_query = (item or {}).get("user_query")
        sql_query = (item or {}).get("sql_query")
        if not user_query or not sql_query:
            continue
        payload["examples"].append(
            {"user_query": str(user_query), "sql_query": str(sql_query)}
        )
    return yaml.safe_dump(payload, sort_keys=False, allow_unicode=True)


# --- 1. Definición y Registro del LiteralString ---


# Clase personalizada para etiquetar cadenas que SIEMPRE deben ser literales
class LiteralString(str):
    pass


# Función Representadora que fuerza el estilo literal '|'
def literal_presenter(dumper, data):
    """
    Representa una cadena de texto multilínea con el estilo de bloque literal (|).
    """
    # Usamos style='|'. PyYAML se encargará de la indentación del bloque.
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")


# REGISTRO:
# Registramos el presentador en el SafeDumper, que es el que usa yaml.safe_dump.
# Esto asegura que CUALQUIER objeto LiteralString sea manejado por literal_presenter.
try:
    yaml.SafeDumper.add_representer(LiteralString, literal_presenter)
except AttributeError:
    # Manejo para versiones de PyYAML donde add_representer está en la instancia
    # (Aunque registrarlo en la clase es lo estándar)
    yaml.add_representer(LiteralString, literal_presenter, Dumper=yaml.SafeDumper)


# --- 2. Función de Construcción de YAML (Corregida) ---


def build_examples_yaml_by_product(examples: List[Dict[str, str]]) -> str:
    """
    Construye YAML de ejemplos, forzando el formato de bloque literal (|)
    para TODAS las consultas SQL.
    """
    payload = {"examples": []}

    for item in examples:
        user_query = (item or {}).get("user_query")
        sql_query = (item or {}).get("sql_query")

        if not user_query or not sql_query:
            continue

        # --- MODIFICACIÓN CLAVE ---

        # 1. Limpiamos los '\n' escapados (si vinieran de un JSON)
        # 2. Usamos .strip() para eliminar espacios/saltos de línea AL FINAL.
        #    Esto evita que PyYAML use el formato '|-'.
        clean_sql = sql_query.replace(r"\n", "\n").strip()

        # 3. Envolvemos SIEMPRE en LiteralString para forzar el bloque '|'
        query_object = LiteralString(clean_sql)

        payload["examples"].append(
            {
                "user_query": str(user_query),
                "sql_query": query_object,  # Usamos el objeto LiteralString
            }
        )

    # Usamos yaml.safe_dump.
    # El 'default_flow_style=False' también ayuda a preferir bloques.
    return yaml.safe_dump(
        payload, sort_keys=False, allow_unicode=True, default_flow_style=False
    )


# def encode_user_queries_to_npy_bytes(
#     user_queries: List[str],
#     model_name: str = 'paraphrase-multilingual-mpnet-base-v2'
# ) -> Tuple[bytes, Dict[str, object]]:
#     """Codifica user_query a embeddings y devuelve (npy_bytes, metadata_dict)."""

#     model = _get_model(model_name)

#     embeddings_tensor = model.encode(user_queries, convert_to_tensor=True)

#     embeddings_np = embeddings_tensor.detach().cpu().numpy()
#     buffer = io.BytesIO()
#     np.save(buffer, embeddings_np)
#     npy_bytes = buffer.getvalue()
#     metadata = {
#         'model_name': model_name,
#         'num_examples': len(user_queries),
#         'embedding_dim': int(embeddings_np.shape[1]) if embeddings_np.ndim == 2 else None,
#     }
#     return npy_bytes, metadata


class LiteralStr(str):
    """
    Clase auxiliar para marcar strings que deben usar el estilo literal en YAML (|).
    """

    pass


def literal_str_representer(dumper: yaml.Dumper, data: LiteralStr) -> yaml.ScalarNode:
    """
    Representador que usa el estilo literal | para preservar saltos de línea.
    """
    normalized_data = str(data)
    # Aseguramos que termine con \n para que PyYAML use | en lugar de |-
    if not normalized_data.endswith("\n"):
        normalized_data += "\n"
    return dumper.represent_scalar("tag:yaml.org,2002:str", normalized_data, style="|")


class LiteralDumper(yaml.SafeDumper):
    """
    Dumper personalizado que hereda de SafeDumper y sabe cómo manejar LiteralStr.
    """

    pass


# REGISTRO GLOBAL: Le dice a LiteralDumper cómo manejar los objetos LiteralStr
LiteralDumper.add_representer(LiteralStr, literal_str_representer)


def build_prompt_yaml_by_product(
    version: str,
    product: str,
    prompt_name: str,
    description: str,
    config_prompt_dict: Dict[str, Any],
    prompt_content: str,
) -> str:
    # --- Función de ayuda para obtener y limpiar el texto (Mejorada) ---
    def get_clean_content(key: str, default: str = "") -> str:
        """
        Obtiene el contenido del diccionario y des-escapa los caracteres
        que fueron escapados por json.dumps() al guardar en JSONB.
        """
        content = config_prompt_dict.get(key, default)
        if isinstance(content, str):
            # CLAVE: Des-escapar los caracteres que JSONB/json.dumps() escapó.

            # 1. Reemplazar los escapes literales \\n, \\t, \\"
            cleaned = content.replace(
                r"\\n", "\n"
            )  # Reconvierte \\n (literal) en \n (salto de línea)
            cleaned = cleaned.replace(r'\\"', '"')  # Reconvierte \\" en "
            cleaned = cleaned.replace(r"\\t", "\t")  # Reconvierte \\t en \t

            # 2. Manejar barras invertidas que escapan a otros caracteres (ej. \` o \*)
            # Si el JSON guardó "texto con \`backticks\`", Python lo leerá como "texto con \\`backticks\\`"
            # Este regex busca una barra invertida seguida de CUALQUIER caracter
            # y lo reemplaza solo con el caracter (quitando la barra de escape)
            # cleaned = re.sub(r'\\(.)', r'\1', cleaned) # Descomentar si aún ves barras extra

            return cleaned.strip()
        return default

    # --- Reconstrucción del Prompt Content Final ---

    # 1. Procesar Lógica de Selección de Tablas
    logica_tabla_list: List[Dict[str, Any]] = config_prompt_dict.get(
        "logica_seleccion_tabla", []
    )
    logica_tabla_str = "No hay lógica de selección de tablas configurada."
    if logica_tabla_list:
        tabla_data = logica_tabla_list[0]
        uso_tabla = get_clean_content(
            "como_utilizarlo", tabla_data.get("como_utilizarlo", "")
        )

        logica_tabla_str = (
            "Antes de construir cualquier consulta, debes decidir qué tabla principal usar. Esta es tu regla más importante:\n\n"
            + uso_tabla
        )

    # 2. Definir el orden y los títulos de las secciones
    prompt_sections = [
        ("Rol Principal del Agente", get_clean_content("role_principal_del_agente")),
        (
            "Regla y Criterio de fecha actual",
            get_clean_content("regla_criterio_fecha_actual"),
        ),
        (
            "Tu Flujo de Trabajo Obligatorio:",
            get_clean_content("flujo_trabajo_obligatorio"),
        ),
        (
            "Lógica de Métricas Avanzadas (¡Revisar Primero!)",
            "No existe una metrica avanzada por el momento",
        ),  # get_clean_content("metricas_avanzadas_del_agente"))
        ("Rol del usuario", get_clean_content("rol_del_usuario")),
        (
            "Lógica de Selección de Tablas (Regla Maestra)",
            logica_tabla_str,
        ),  # Usa el str ya limpio
        ("Reglas de Negocio y Calculo", get_clean_content("reglas_negocio")),
        (
            "Reglas Críticas para la Generación de SQL",
            get_clean_content("reglas_criticas_sql"),
        ),
        ("Control de acceso a datos", get_clean_content("control_acceso_datos")),
        (
            "Reglas para generar las Alertas",
            get_clean_content("reglas_generar_alertas"),
        ),
        ("Reglas para envio de Alertas", get_clean_content("reglas_envio_alertas")),
        ("Formato y Tono de la Respuesta", get_clean_content("formato_respuesta")),
    ]

    # 3. Concatenar todas las secciones
    final_prompt_content = []
    for title, content in prompt_sections:
        if content:
            final_prompt_content.append(f"**{title}**\n\n{content.strip()}")

    # Unir todas las secciones
    prompt_content_reconstructed = "\n\n---\n\n".join(final_prompt_content)

    # --- 4. Generación del Payload YAML ---

    # Marcamos el string final con LiteralStr (que PyYAML ahora reconoce globalmente)
    prompt_content_str = LiteralStr(prompt_content_reconstructed)

    payload = {
        "version": version,
        "product": product,
        "prompt_name": prompt_name,
        "description": description,
        "prompt_content": prompt_content,
    }

    # Usamos el Dumper registrado globalmente
    return yaml.dump(
        payload,
        Dumper=LiteralDumper,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=float("inf"),
    )


def build_prompt_yaml_by_productV2(
    version: str,
    product: str,
    prompt_name: str,
    description: str,
    config_prompt_dict: Dict[str, Any],
    prompt_content: str,
) -> str:
    # 1. Instanciamos el modelo para obtener los defaults definidos en la clase
    config_obj = PromptConfig(**config_prompt_dict)

    def get_clean_content(content: Any) -> str:
        if not content or str(content).strip().lower() == "string":
            return ""

        if isinstance(content, str):
            try:
                content = content.encode("latin-1").decode("utf-8")
            except (UnicodeEncodeError, UnicodeDecodeError):
                pass

            content = remove_accents(content)

            cleaned = content.replace(r"\\n", "\n").replace(r"\n", "\n")
            cleaned = cleaned.replace(r'\\"', '"').replace(r"\"", '"')
            cleaned = cleaned.replace(r"\\t", "\t")
            return cleaned.strip()
        return str(content)

    # --- 1. Logica de Seleccion de Tablas ---
    table_logic_list = config_obj.table_selection_logic
    table_selection_str = "No hay logica de seleccion de tablas configurada."

    if table_logic_list:
        header = (
            "Antes de construir cualquier consulta, debes decidir que tabla principal usar. "
            "Esta es tu regla mas importante:\n"
        )

        table_details = []

        for table in table_logic_list:
            t_name = remove_accents(getattr(table, "table_name", "N/A"))
            t_instr = remove_accents(getattr(table, "usage_instructions", "N/A"))
            t_note = remove_accents(getattr(table, "important_notes", "N/A"))

            validations = []

            # Validación adicional
            validations.append(
                "Primero, usa el resultado que te dio `list_tables` para verificar si "
                "`facturacion_argentina` está disponible. Si no lo está, informa al usuario "
                "que no es posible realizar la consulta porque la tabla de "
                "`facturacion_argentina` no se encuentra disponible para su usuario."
            )

            # Validación existente
            base_validation = remove_accents(getattr(table, "validation", None))
            if base_validation:
                validations.append(base_validation)

            validation_block = "\n".join(f"    - {v}" for v in validations)

            table_details.append(
                f"TABLA A USAR: **{t_name}**\n"
                f"  - Instrucciones: {t_instr}\n"
                f"  - Validacion:\n{validation_block}\n"
                f"  - Importante: {t_note}"
            )

        table_selection_str = header + "\n".join(table_details)

    # --- 2. Logica de Metricas Avanzadas ---
    metrics_list = config_obj.advanced_agent_metrics
    metrics_str = "No hay metricas avanzadas configuradas."
    if metrics_list:
        metrics_parts = []
        for m in metrics_list:
            if m is None:
                continue
            name = remove_accents(m.name)
            definition = remove_accents(m.metric)
            htui = remove_accents(
                "**Si el usuario ya es específico:** Usa la herramienta `get_metric_query` usando como argumento de nombre de metrica: 'cross_selling_general'"
            )
            args = remove_accents(
                "Identifica los campos de agrupación (`group_by_fields`), el rango de fechas ('start_date' y 'end_date') para usarlo como argumento de la herramienta."
            )
            params_str = ""
            if m.parameters:
                params_str = f"""
    **Si el usuario ya es especifico:** Usa la herramienta `get_metric_query` usando como argumento de nombre de metrica: 'cross_selling_general'
    Identifica los campos de agrupacion (`group_by_fields`), el rango de fechas ('start_date' y 'end_date') para usarlo como argumento de la herramienta.*
    Parametros requeridos:
    """.rstrip()  # noqa: F541

                for p in m.parameters:
                    params_str += f"\n    - {remove_accents(p.parameter)}: {remove_accents(p.meaning)}"
            metrics_parts.append(f"- **{name}**: {definition}\n{params_str}")

        metrics_str = "\n".join(metrics_parts)

    # --- 3. Construccion del Cuerpo del Prompt ---
    prompt_sections = [
        ("Rol Principal del Agente", get_clean_content(config_obj.agent_main_role)),
        (
            "Tu Flujo de Trabajo Obligatorio",
            get_clean_content("{mandatory_workflow_generate}"),
        ),
        ("Logica de Metricas Avanzadas", metrics_str),
        ("Logica de Seleccion de Tablas (Regla Maestra)", table_selection_str),
        ("Reglas de Negocio y Calculo", get_clean_content(config_obj.business_rules)),
        (
            "Reglas Criticas para la Generacion de SQL",
            get_clean_content(
                remove_accents("""{sql_generation_instruction_section}
- Seguridad: Solo genera consultas "SELECT", en ningun caso realiza consultas "UPDATE", "INSERT", "DELETE", que alteren las tablas.
- Claridad: Usa alias cortos y logicos para las tablas (ej: sir para Sell_in_real).
- Fechas: Usa DATE_TRUNC para agrupar por periodos.
- Nulos: Usa COALESCE("columna", 0) en agregaciones.
- Limites: Finaliza la consulta con LIMIT 100 a menos que se pida lo contrario.
- Ordenamiento: Incluye ORDER BY en consultas de "top N".
- Solo puedes la consultas con las tablas generadas en `list_tables`.""")
            ),
        ),
        ("Rol del usuario", get_clean_content(remove_accents("{section_rol_usuario}"))),
        (
            "Control de acceso a datos",
            get_clean_content("{data_access_section}"),
        ),
        (
            "Reglas para generar las Alertas",
            get_clean_content("{data_alert_section}"),
        ),
        (
            "Reglas para generar las Alertas",
            get_clean_content("{data_alert_section_generate}"),
        ),
        (
            "Formato y Tono de la Respuesta",
            get_clean_content(
                remove_accents("""Instrucciones para el Agente: Formato y Tono de la Respuesta
Tu respuesta final al usuario debe seguir estas reglas de presentacion de forma obligatoria:

1. Analisis del Resultado:
Primero, analiza los datos obtenidos de la fuente de informacion. Cuenta cuantas lineas de registros hay (sin incluir encabezados).

2. Presentacion en Tabla (Multiples Registros):
Si hay mas de una fila de datos, tu respuesta DEBE estar en formato de tabla Markdown.
Incluye siempre un breve texto introductorio descriptivo.
Ejemplo: "Aqui tienes el resumen de ventas por categoria para el periodo seleccionado:" | Categoria | Resultado | | :--- | :--- | | Electronica | 15,102.53 | | Hogar | 468.27 |

Sufijos: Para campos que representen porcentajes o avances, añade siempre el simbolo %.
Valores Nulos: Representa los valores "N/A" o vacios con un guion -.

3. Presentacion en Frase (Un Solo Registro):
Si el resultado es un unico valor o una sola fila de datos, presentalo de forma directa en una frase concisa y amable.
Ejemplo: "El indice de satisfaccion general para el año 2025 es de 0.85 (un 85%)."

4. Proporcionar Insights de Negocio:
Despues de presentar el dato (ya sea en tabla o frase), añade una oracion que explique el significado del numero en un contexto de negocio.
Ejemplo de Valor Financiero: "El ingreso promedio por unidad en la zona Norte es de $150.25. Esto significa que, tras aplicar descuentos, este es el valor neto recuperado por cada articulo vendido en dicha region."
Ejemplo de Proporcion: "La tasa de penetracion de mercado es de 0.85. Esto indica que el 85% de los clientes activos realizaron compras en mas de una categoria de producto durante este periodo."

5. Reglas Generales de Formato:
- Lenguaje Natural: La respuesta debe ser siempre en español claro y profesional. NUNCA muestres codigo tecnico, consultas SQL ni resultados de base de datos en bruto.
- Formato de Numeros: Usa separadores de miles y el simbolo de moneda correspondiente (ej: "$1,234,567.89").
- Nombres de Campos: No utilices nombres tecnicos de columnas de la base de datos (ej: ID_CLI_2024). Traducelos a terminos de negocio faciles de entender (ej: "Codigo de Cliente").
- Honestidad: Si no hay resultados o ocurre un error, comunicalo de forma clara y sencilla.

6. Gestion de Visualizaciones:
Si el usuario solicita graficos o elementos visuales, proporciona unicamente la tabla de datos que los respalda.
Usa siempre un mensaje de cortesia neutral: "¡Aqui tienes! He procesado la informacion. Los resultados en formato de tabla para lo que solicitaste son los siguientes:\"""")
            ),
        ),
        (
            "Instrucciones Adicionales",
            get_clean_content(config_obj.additional_considerations),
        ),
    ]

    parts = []
    for title, content in prompt_sections:
        if content and content.strip() != "":
            parts.append(f"**{title}**\n\n{content.strip()}")

    full_body = remove_accents("\n\n---\n\n".join(parts))

    # --- 4. Generacion del YAML ---
    payload = {
        "version": version,
        "product": remove_accents(product),
        "prompt_name": remove_accents(prompt_name),
        "description": remove_accents(description),
        "prompt_content": LiteralStr(full_body),
    }

    return yaml.dump(
        payload,
        Dumper=LiteralDumper,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=1000,
    )


def remove_accents(input_str: str) -> str:
    """
    Elimina tildes y caracteres especiales de un string para evitar
    problemas de codificacion (ej: convierte 'ó' en 'o').
    """
    if not input_str:
        return ""
    nfkd_form = unicodedata.normalize("NFKD", input_str)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])


def send_update_promptV2(prompt_data: PromptUpdateRequestV2) -> int:
    """
    Llama al Stored Procedure para actualizar un prompt existente.
    SP: spu_minddash_app_update_prompt
    """

    config_json_str = json.dumps(
        prompt_data.config_prompt.model_dump(exclude_none=True), ensure_ascii=False
    )

    query_str = """
        CALL spu_minddash_app_update_prompt(
            p_id := %s,
            p_product_id := %s,
            p_name := %s,
            p_config_prompt := %s::JSONB,
            p_content_prompt := %s,
            p_path_config_file := %s
        );
    """

    params = (
        prompt_data.id,
        prompt_data.product_id,
        prompt_data.name,
        config_json_str,
        prompt_data.prompt_content,
        prompt_data.path_config_file,
    )

    rowcount = execute(query_str, params=params)
    return rowcount


def send_register_promptV2(prompt_data: PromptRegisterRequestV2) -> str:
    """
    Llama al Stored Procedure para registrar un nuevo prompt y retorna el ID.
    Usa el SP: spu_minddash_app_insert_prompt
    """

    # 1. PromptConfig → dict → JSON
    config_json_str = json.dumps(
        prompt_data.config_prompt.model_dump(exclude_none=True), ensure_ascii=False
    )

    # 2. Stored Procedure
    query_str = """
        CALL spu_minddash_app_insert_prompt(
            %s::UUID,            -- p_product_id
            %s,                  -- p_name
            %s::JSONB,           -- p_config_prompt
            %s::TEXT,            -- p_content_prompt
            %s,                  -- p_path_config_file
            %s::UUID             -- new_prompt_id (OUT)
        );
    """

    params = (
        prompt_data.product_id,
        prompt_data.name,
        config_json_str,
        prompt_data.prompt_content,
        prompt_data.path_config_file,
        None,  # OUT
    )

    result: Dict[str, Any] | None = execute_procedure_with_out(query_str, params=params)

    if result and "new_prompt_id" in result:
        return str(result["new_prompt_id"])

    raise Exception(
        "Registro de prompt fallido: no se pudo obtener el ID del procedimiento."
    )


def build_prompt_yaml(
    version: str, product: str, prompt_name: str, description: str, prompt_content: str
) -> str:
    """Construye un YAML de prompt general de agente con los campos solicitados."""

    # Crear un dumper personalizado que preserve saltos de línea usando estilo literal
    class LiteralStr(str):
        """Clase auxiliar para marcar strings que deben usar estilo literal en YAML."""

        pass

    def literal_str_representer(dumper, data):
        """Representador que usa el estilo literal | para preservar saltos de línea."""
        return dumper.represent_scalar("tag:yaml.org,2002:str", str(data), style="|")

    # Crear un dumper personalizado que herede de SafeDumper
    class LiteralDumper(yaml.SafeDumper):
        pass

    # Registrar el representador en el dumper personalizado
    LiteralDumper.add_representer(LiteralStr, literal_str_representer)

    # Convertir description y prompt_content a LiteralStr si contienen saltos de línea
    # Esto preservará los saltos de línea en el YAML generado
    # Aseguramos que termine con \n para que use | en lugar de |-
    def normalize_for_literal(text: str) -> str:
        """Normaliza el texto para que use estilo literal | sin -"""
        if "\n" in text:
            # Si no termina con \n, lo agregamos para que PyYAML use | en lugar de |-
            return text if text.endswith("\n") else text + "\n"
        return text

    description_normalized = normalize_for_literal(str(description))
    prompt_content_normalized = normalize_for_literal(str(prompt_content))

    description_str = (
        LiteralStr(description_normalized)
        if "\n" in description_normalized
        else description_normalized
    )
    prompt_content_str = (
        LiteralStr(prompt_content_normalized)
        if "\n" in prompt_content_normalized
        else prompt_content_normalized
    )

    payload = {
        "version": version,
        "product": product,
        "prompt_name": prompt_name,
        "description": description_str,
        "prompt_content": prompt_content_str,
    }
    return yaml.dump(
        payload,
        Dumper=LiteralDumper,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    )


# --- SERVICIO DE INSERT (UPDATE) ---

"""
    SERVICIO DE INSERT (UPDATE) DE PROMPTS
"""


def get_prompt_by_product(product_id: str) -> List[GetPromptsResponseByProduct]:
    """
    Obtiene la lista consolidada de prompts filtrado por products.
    """
    query_str = f"""
        select 
            prompt_id,
            prompt_name,
            config_prompt,
            path_config_file,
            product_id,
            prompt_content,
            name,
            description
        from view_info_prompt_product
        WHERE
                product_id = '{product_id}'
    """
    rows = query_all(query_str)

    # Mapeo de los resultados de la DB al modelo Pydantic
    return [GetPromptsResponseByProduct(**r) for r in rows]


def send_register_prompt(prompt_data: PromptRegisterRequest) -> str:
    """
    Llama al Stored Procedure para registrar un nuevo prompt y retorna el ID.
    Usa el SP: spu_minddash_app_insert_prompt
    """

    # 1. PromptConfig → dict → JSON
    # Intentamos usar model_dump, si falla, usamos el dict directamente
    if hasattr(prompt_data.config_prompt, "model_dump"):
        config_data = prompt_data.config_prompt.model_dump(exclude_none=True)
    else:
        # Si es un dict, filtramos los None manualmente
        config_data = {
            k: v for k, v in prompt_data.config_prompt.items() if v is not None
        }

    config_json_str = json.dumps(config_data, ensure_ascii=False)

    # config_json_str = json.dumps(
    #     prompt_data.config_prompt.model_dump(exclude_none=True), ensure_ascii=False
    # )

    # 2. Stored Procedure
    query_str = """
        CALL spu_minddash_app_insert_prompt(
            %s::UUID,            -- p_product_id
            %s,                  -- p_name
            %s::JSONB,           -- p_config_prompt
            %s::TEXT,            -- p_content_prompt
            %s,                  -- p_path_config_file
            %s::UUID             -- new_prompt_id (OUT)
        );
    """

    params = (
        prompt_data.product_id,
        prompt_data.name,
        config_json_str,
        prompt_data.prompt_content,
        prompt_data.path_config_file,
        None,  # OUT
    )

    result: Dict[str, Any] | None = execute_procedure_with_out(query_str, params=params)

    if result and "new_prompt_id" in result:
        return str(result["new_prompt_id"])

    raise Exception(
        "Registro de prompt fallido: no se pudo obtener el ID del procedimiento."
    )


def send_update_prompt(prompt_data: PromptUpdateRequest) -> int:
    """
    Llama al Stored Procedure para actualizar un prompt existente.
    SP: spu_minddash_app_update_prompt
    """

    if hasattr(prompt_data.config_prompt, "model_dump"):
        config_data = prompt_data.config_prompt.model_dump(exclude_none=True)
    else:
        # Si es un dict, filtramos los None manualmente
        config_data = {
            k: v for k, v in prompt_data.config_prompt.items() if v is not None
        }

    config_json_str = json.dumps(config_data, ensure_ascii=False)

    query_str = """
        CALL spu_minddash_app_update_prompt(
            p_id := %s,
            p_product_id := %s,
            p_name := %s,
            p_config_prompt := %s::JSONB,
            p_content_prompt := %s,
            p_path_config_file := %s
        );
    """

    params = (
        prompt_data.id,
        prompt_data.product_id,
        prompt_data.name,
        config_json_str,
        prompt_data.prompt_content,
        prompt_data.path_config_file,
    )

    rowcount = execute(query_str, params=params)
    return rowcount


def send_delete_prompt(prompt_data: PromptDeleteRequest) -> int:
    """
    Llama al Stored Procedure para eliminar un prompt.
    Usa el SP: spu_minddash_app_delete_prompt
    """
    prompt_id = prompt_data.id

    query_str = """
        CALL spu_minddash_app_delete_prompt(
            p_id := %s
        );
    """

    params = (prompt_id,)  # Tupla de un solo elemento

    try:
        rowcount = execute(query_str, params=params)
        return rowcount
    except Exception:
        raise


"""
    SERVICIO DE INSERT (UPDATE) DE EXAMPLES
"""


def get_examples_by_product(product_id: str) -> List[Dict[str, Any]]:
    """
    Recupera una lista de ejemplos filtrados por product_id desde la vista view_list_examples.
    """

    query_str = f"""
        SELECT 
            id,
            product_id,
            name,
            description,
            data_query,
            created_at,
            updated_at 
        FROM view_list_examples
        WHERE product_id = '{product_id}';
    """
    print(f"query_str = {query_str}")
    rows = query_all(query_str)

    # Mapeo de los resultados de la DB al modelo Pydantic
    return [ExampleListResponseItem(**r) for r in rows]


def send_register_example(example_data: ExampleRegisterRequest) -> str:
    """
    Llama al Stored Procedure para registrar un nuevo ejemplo y retorna el ID.
    Usa el SP: spu_minddash_app_insert_example
    """

    # El SP espera una cadena para p_description y p_data_query

    query_str = """
        CALL spu_minddash_app_insert_example(
            %s::UUID,            -- 1. p_product_id
            %s,                  -- 2. p_name
            %s,                  -- 3. p_description (VARCHAR(200))
            %s,                  -- 4. p_data_query (TEXT)
            %s::UUID             -- 5. new_example_id (OUT)
        );
    """

    params = (
        example_data.product_id,
        example_data.name,
        example_data.description,
        example_data.data_query,
        None,  # Valor inicial para el parámetro OUT
    )

    # Ejecuta el CALL y obtiene el diccionario de resultados
    result: Dict[str, Any] | None = execute_procedure_with_out(query_str, params=params)

    if result and "new_example_id" in result:
        return str(result["new_example_id"])
    else:
        raise Exception(
            "Registro de ejemplo fallido: no se pudo obtener el ID del procedimiento."
        )


def send_update_example(example_data: ExampleUpdateRequest) -> int:
    """
    Llama al Stored Procedure para actualizar un ejemplo existente.
    Usa el SP: spu_minddash_app_update_example
    """

    query_str = """
        CALL spu_minddash_app_update_example(
            p_id := %s,
            p_product_id := %s,
            p_name := %s,
            p_description := %s,
            p_data_query := %s
        );
    """

    params = (
        example_data.id,
        example_data.product_id,
        example_data.name,
        example_data.description,
        example_data.data_query,
    )

    # Usamos execute. El SP maneja las validaciones y lanza RAISE EXCEPTION si algo falla.
    rowcount = execute(query_str, params=params)
    return rowcount


def send_delete_example(example_data: ExampleDeleteRequest) -> int:
    """
    Llama al Stored Procedure para eliminar un ejemplo.
    Usa el SP: spu_minddash_app_delete_example
    """
    example_id = example_data.id

    query_str = """
        CALL spu_minddash_app_delete_example(
            p_id := %s
        );
    """

    params = (example_id,)

    try:
        rowcount = execute(query_str, params=params)
        return rowcount
    except Exception:
        raise
