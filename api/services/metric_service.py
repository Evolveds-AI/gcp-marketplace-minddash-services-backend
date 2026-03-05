from typing import Dict, Any, List
import json
import yaml
from api.models.metric_models import (
    MetricRegisterRequest,
    MetricUpdateRequest,
    MetricDeleteRequest,
    MetricByProduct,
    GetMetricsByProductRequest,
    GetMetricsRequest,
    MetricResponse,
    LiteralStr,
    LiteralDumper,
    literal_str_representer,
    MetricDefinition,
)
from api.utils.db_client import execute_procedure_with_out, execute, query_all

import logging

logger = logging.getLogger(__name__)


# Registrar el representador en el dumper personalizado
LiteralDumper.add_representer(LiteralStr, literal_str_representer)


def build_metrics_yaml_2(
    version: str,
    product: str,
    metrics_name: str,
    description: str,
    # ¡CAMBIO CLAVE AQUÍ! Recibe la lista de modelos Pydantic
    metrics_data: List[MetricDefinition],
) -> str:
    """
    Construye un YAML de definiciones de métricas a partir de una lista de objetos MetricDefinition.
    """

    # 1. Procesar la lista de modelos para crear el diccionario final de métricas
    final_metrics_dict = {}

    for metric_obj in metrics_data:
        # Convertimos el modelo Pydantic a un diccionario, excluyendo el nombre clave
        # para ponerlo como clave del diccionario padre.
        metric_dict = metric_obj.model_dump(by_alias=False, exclude={"metric_name"})

        # Envolvemos el sql_template en LiteralStr para forzar el estilo | en el YAML
        if "sql_template" in metric_dict:
            metric_dict["sql_template"] = LiteralStr(metric_dict["sql_template"])

        # Usamos el nombre de la métrica como clave en el diccionario final
        final_metrics_dict[metric_obj.metric_name] = metric_dict

    # 2. Definir la estructura principal del YAML (payload)
    payload = {
        "version": version,
        "product": product,
        "prompt_name": metrics_name,
        "description": description,
        "metrics": final_metrics_dict,  # <- El diccionario de métricas procesado
    }

    # 3. Generar el YAML
    return yaml.dump(
        payload,
        Dumper=LiteralDumper,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    )


def build_metrics_yaml(
    version: str,
    product: str,
    metrics_name: str,
    description: str,
    metrics_data: List[MetricDefinition],
) -> str:
    """
    Construye un YAML de definiciones de métricas a partir de una lista de objetos MetricDefinition.
    Ahora genera 'metrics' como una LISTA de objetos con la propiedad 'name'.
    """

    # 1. CAMBIO: Usamos una lista en lugar de un diccionario
    final_metrics_list = []

    for metric_obj in metrics_data:
        # Volcamos el modelo pydantic a un dict
        raw_dict = metric_obj.model_dump(by_alias=False)

        # Construimos el diccionario ordenado para el item de la lista
        # Esto asegura que 'name' salga primero en el YAML visualmente
        metric_item = {
            "name": metric_obj.metric_name,  # Mapeamos metric_name -> name
            "sql_template": LiteralStr(
                raw_dict.get("sql_template", "")
            ),  # Forzamos el formato |
            "required_params": raw_dict.get("required_params", []),
            "optional_params": raw_dict.get("optional_params", []),
        }

        # Si tu modelo tiene más campos que quieras incluir dinámicamente,
        # puedes hacer un merge, pero lo anterior es lo más limpio para tu formato deseado.

        final_metrics_list.append(metric_item)

    # 2. Definir la estructura principal del YAML (payload)
    payload = {
        "version": version,
        "product": product,
        "prompt_name": metrics_name,
        "description": description,
        "metrics": final_metrics_list,  # <- Ahora pasamos la LISTA
    }

    # 3. Generar el YAML
    return yaml.dump(
        payload,
        Dumper=LiteralDumper,  # Asumiendo que tienes tu Dumper configurado
        sort_keys=False,  # CRÍTICO: Para respetar el orden name -> sql -> params
        allow_unicode=True,
        default_flow_style=False,
    )


def format_db_metrics_for_yaml(
    db_metrics: List[MetricByProduct],
) -> List[MetricDefinition]:
    """
    Convierte una lista de modelos MetricByProduct (obtenidos de la DB)
    a una lista de MetricDefinition, que es el formato esperado por build_metrics_yaml.
    """

    formatted_list: List[MetricDefinition] = []

    for db_metric in db_metrics:
        formatted_name = db_metric.metric_name.replace(" ", "_").lower()
        # Mapeamos los campos de la DB al formato de MetricDefinition
        definition = MetricDefinition(
            # Nota: Usamos 'metric_name' como el alias 'name_metrics' para el YAML clave
            name_metrics=formatted_name,
            sql_template=db_metric.metric_data_query,
            required_params=db_metric.metric_required_params,
            optional_params=db_metric.metric_optional_params,
        )
        formatted_list.append(definition)

    return formatted_list


def send_register_metric(metric_data: MetricRegisterRequest) -> str:
    """
    Llama al Stored Procedure para registrar una nueva métrica y retorna el ID.
    """

    # 1. *** MANEJAR EL JSONB: Serializar el diccionario a una cadena JSON ***
    data_query = metric_data.data_query if metric_data.data_query is not None else {}
    data_query_json_str = json.dumps(data_query)

    query_str = """
        CALL spu_minddash_app_insert_metric(
            p_product_id            => %s::UUID,
            p_name                  => %s::VARCHAR,
            p_description           => %s::VARCHAR,
            p_data_query            => %s::TEXT,
            p_required_params       => %s::TEXT[],
            p_optional_params       => %s::TEXT[],
            new_metric_id           => %s
        );
    """

    params = (
        metric_data.product_id,
        metric_data.name,
        metric_data.description,
        data_query_json_str,
        metric_data.required_params,
        metric_data.optional_params,
        None,  # new_metric_id se llena automáticamente
    )

    # Ejecuta el CALL y obtiene el diccionario de resultados
    result: Dict[str, Any] | None = execute_procedure_with_out(query_str, params=params)

    if result and "new_metric_id" in result:
        return str(result["new_metric_id"])
    else:
        raise Exception(
            "Registro de métrica fallido: no se pudo obtener el ID del procedimiento."
        )


def send_update_metric(metric_data: MetricUpdateRequest) -> int:
    """
    Llama al Stored Procedure para actualizar una métrica.
    Retorna el rowcount (número de filas afectadas, o -1 si CALL es exitoso).
    """

    # 1. *** MANEJAR EL JSONB: Serializar el diccionario a una cadena JSON ***
    data_query = metric_data.data_query if metric_data.data_query is not None else {}
    data_query_json_str = json.dumps(data_query)

    query_str = """
        CALL spu_minddash_app_update_metric(
            p_id                    := %s,
            p_product_id            := %s::UUID,
            p_name                  := %s::VARCHAR,
            p_description           := %s::VARCHAR,
            p_data_query            := %s::TEXT,
            p_required_params       := %s::TEXT[],
            p_optional_params       := %s::TEXT[]
        );
    """

    params = (
        metric_data.id,
        metric_data.product_id,
        metric_data.name,
        metric_data.description,
        data_query_json_str,
        metric_data.required_params,
        metric_data.optional_params,
    )

    # Ejecuta el CALL y obtiene el rowcount
    rowcount = execute(query_str, params=params)
    return rowcount


def send_delete_metric(metric_data: MetricDeleteRequest) -> int:
    """
    Llama al Stored Procedure para eliminar una métrica.
    Retorna el rowcount (-1 si es exitoso con CALL).
    """
    metric_id = metric_data.id
    logger.info("Iniciando eliminación de métrica ID: %s", metric_id)

    query_str = """
        CALL spu_minddash_app_delete_metric(
            p_metric_id := %s
        );
    """

    params = (metric_id,)

    try:
        rowcount = execute(query_str, params=params)
        logger.info(
            "Eliminación de métrica ID: %s completada. Filas afectadas: %d",
            metric_id,
            rowcount,
        )
        return rowcount
    except Exception as e:
        logger.error(
            "Error al ejecutar la eliminación para ID %s: %s", metric_id, str(e)
        )
        raise


def get_metrics_by_product(
    request_data: GetMetricsByProductRequest,
) -> List[MetricByProduct]:
    """
    Obtiene la lista de métricas de un producto específico.
    """
    product_id = request_data.product_id

    query_str = f"""
        SELECT 
            metric_id,
            metric_name,
            metric_description,
            metric_data_query,
            metric_required_params,
            metric_optional_params,
            product_id,
            product_name
        FROM view_list_metrics
        WHERE product_id = '{product_id}'
        ORDER BY metric_name
    """

    rows = query_all(query_str)

    # Mapeo de los resultados de la DB al modelo Pydantic
    return [MetricByProduct(**r) for r in rows]


def get_metrics(request_data: GetMetricsRequest) -> List[MetricResponse]:
    """
    Obtiene todas las métricas o una específica por ID.
    Si se proporciona metric_id, retorna solo esa métrica.
    Si no se proporciona metric_id, retorna todas las métricas.
    """
    metric_id = request_data.metric_id

    if metric_id:
        # Buscar métrica específica por ID
        query_str = f"""
            SELECT 
                metric_id,
                metric_name,
                metric_description,
                metric_data_query,
                metric_required_params,
                metric_optional_params,
                product_id,
                product_name
            FROM view_list_metrics
            WHERE metric_id = '{metric_id}'
        """
    else:
        # Buscar todas las métricas
        query_str = """
            SELECT 
                metric_id,
                metric_name,
                metric_description,
                metric_data_query,
                metric_required_params,
                metric_optional_params,
                product_id,
                product_name
            FROM view_list_metrics
            ORDER BY metric_name
        """

    rows = query_all(query_str)

    # Mapeo de los resultados de la DB al modelo Pydantic
    return [MetricResponse(**r) for r in rows]
