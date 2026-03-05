import hashlib
import json
import logging
import os
import re
import time
from typing import Dict, List, Optional, Tuple

import google.auth
from google import genai
from pydantic import ValidationError

from api.models.chart_models import ChartSpec

logger = logging.getLogger(__name__)

# ---------- Configuración/Globals ----------
_DEFAULT_MODEL = os.getenv("VERTEX_MODEL", "gemini-2.5-flash")
_DEFAULT_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
_CACHE_TTL_SEC = int(os.getenv("CHARTSPEC_CACHE_TTL_SEC", "300"))  # 5 min
_CACHE_CAPACITY = int(os.getenv("CHARTSPEC_CACHE_CAPACITY", "128"))
_INPUT_MAX_CHARS = int(os.getenv("CHARTSPEC_INPUT_MAX_CHARS", "4000"))

_client: Optional[genai.Client] = None
_model_name: str = _DEFAULT_MODEL
_cache: Dict[str, Tuple[float, ChartSpec]] = {}


def _detect_gcp_project() -> Optional[str]:
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    if project:
        return project
    try:
        _creds, project_id = google.auth.default()
        return project_id
    except Exception:
        return None


def _get_client() -> genai.Client:
    global _client
    if _client is not None:
        return _client
    project = _detect_gcp_project()
    if not project:
        raise RuntimeError(
            "No se pudo determinar el proyecto GCP para google-genai (Vertex)."
        )
    _client = genai.Client(vertexai=True, project=project, location=_DEFAULT_LOCATION)
    return _client


def _get_model_name() -> str:
    global _model_name
    return _model_name


def _trim_text(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    # Heurística: dejar cabecera y cola
    head = text[: limit // 2]
    tail = text[-limit // 2 :]
    return head + "\n...\n" + tail


def _normalize_text(text: str) -> str:
    # Normaliza espacios para mejorar cache-hit
    return " ".join((text or "").strip().split())


def _cache_key(agent_reply: str) -> str:
    normalized = _normalize_text(agent_reply)
    h = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return f"v2|{_get_model_name()}|{h}"


def _cache_get(key: str) -> Optional[ChartSpec]:
    now = time.time()
    item = _cache.get(key)
    if not item:
        return None
    ts, value = item
    if now - ts > _CACHE_TTL_SEC:
        _cache.pop(key, None)
        return None
    return value


def _cache_put(key: str, value: ChartSpec) -> None:
    # Evict si excede capacidad simple
    if len(_cache) >= _CACHE_CAPACITY:
        # eliminar el más antiguo
        oldest_key = min(_cache.items(), key=lambda kv: kv[1][0])[0]
        _cache.pop(oldest_key, None)
    _cache[key] = (time.time(), value)


def _extract_json_object(text: str) -> Optional[dict]:
    """
    Intenta extraer el primer objeto JSON válido de un texto que puede incluir
    fences Markdown, comentarios u otro ruido.
    """

    def _try_load(candidate: str):
        try:
            obj = json.loads(candidate)
            if isinstance(obj, list) and obj and isinstance(obj[0], dict):
                return obj[0]
            if isinstance(obj, dict):
                return obj
        except Exception:
            return None
        return None

    def _coerce_json_like(s: str) -> Optional[dict]:
        # Normalizar comillas tipográficas
        t = (
            s.replace("\u201c", '"')
            .replace("\u201d", '"')
            .replace("“", '"')
            .replace("”", '"')
            .replace("’", "'")
        )
        # Reemplazar True/False/None por JSON válido
        t = re.sub(r"\bTrue\b", "true", t)
        t = re.sub(r"\bFalse\b", "false", t)
        t = re.sub(r"\bNone\b", "null", t)
        # Quitar comillas en code fences
        t = re.sub(r"```json|```", "", t, flags=re.IGNORECASE)
        # Reemplazar claves con comillas simples por dobles: 'key':
        t = re.sub(r"'([A-Za-z0-9_]+)'\s*:", r'"\1":', t)
        # Reemplazar valores string con comillas simples: : 'value'
        t = re.sub(
            r":\s*'([^']*)'", lambda m: ': "' + m.group(1).replace('"', '\\"') + '"', t
        )
        # Quitar comas colgantes antes de } o ]
        t = re.sub(r",\s*([}\]])", r"\1", t)
        return _try_load(t)

    # Intento directo
    obj = _try_load(text)
    if obj is not None:
        return obj

    # Quitar code fences ```json ... ``` o ``` ... ```
    cleaned = re.sub(r"```json|```", "", text, flags=re.IGNORECASE)

    # Trim espacios
    s = cleaned.strip()
    # Buscar primer '{' y balancear llaves
    start = s.find("{")
    if start == -1:
        return None
    depth = 0
    end = -1
    for i in range(start, len(s)):
        ch = s[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i
                break
    if end != -1:
        candidate = s[start : end + 1]
        obj = _try_load(candidate)
        if obj is not None:
            return obj
        # Intentar coerción
        coerced = _coerce_json_like(candidate)
        if coerced is not None:
            return coerced
    # Intentar con arrays: [ ... ]
    bstart = s.find("[")
    if bstart != -1:
        depth = 0
        bend = -1
        for i in range(bstart, len(s)):
            ch = s[i]
            if ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    bend = i
                    break
        if bend != -1:
            candidate = s[bstart : bend + 1]
            obj = _try_load(candidate)
            if obj is not None:
                return obj
            coerced = _coerce_json_like(candidate)
            if coerced is not None:
                return coerced
    # Coerción sobre texto completo como último recurso
    coerced = _coerce_json_like(s)
    if coerced is not None:
        return coerced
    return None


def generate_chart_spec(
    agent_reply: str,
    user_prompt: Optional[str] = None,
    preferred_types: Optional[List[str]] = None,
    is_table: Optional[bool] = None,
    column_count: Optional[int] = None,
    fallback_on_error: bool = True,
) -> ChartSpec:
    if not agent_reply or not agent_reply.strip():
        raise ValueError("agent_reply es requerido")

    print("agent_reply: ", agent_reply)
    print("user_prompt: ", user_prompt)
    print("preferred_types: ", preferred_types)
    print("is_table: ", is_table)
    print("column_count: ", column_count)

    key = _cache_key(agent_reply)
    cached = _cache_get(key)
    if cached is not None:
        return cached

    client = _get_client()
    model_name = _get_model_name()

    # Construir preferencia a partir de flags si no fue provista (para decidir fast-path)
    computed_preferred: List[str] = []
    if (preferred_types is None or len(preferred_types) == 0) and is_table is not None:
        if is_table and (column_count or 0) >= 3:
            computed_preferred = ["pie"]
        elif is_table and (column_count or 0) == 2:
            computed_preferred = ["bar", "line", "pie"]
    prefer_list = preferred_types or computed_preferred

    schema_hint = {
        "type": "object",
        "properties": {
            "type": {"type": "string", "enum": ["bar", "line", "pie"]},
            "title": {"type": "string"},
            "labels": {"type": "array", "items": {"type": "string"}},
            "series": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "data": {"type": "array", "items": {"type": "number"}},
                        "color": {"type": "string"},
                    },
                    "required": ["name", "data"],
                },
            },
            # meta es libre, pero sugerimos estas claves
            "meta": {
                "type": "object",
                "properties": {
                    "unit_type": {
                        "type": "string",
                        "enum": ["number", "currency", "percent", "unit"],
                    },
                    "currency": {"type": "string", "description": "Ej.: USD, ARS, EUR"},
                    "unit_label": {
                        "type": "string",
                        "description": "Ej.: UEQ, Kg, Uds",
                    },
                    "value_prefix": {"type": "string"},
                    "value_suffix": {"type": "string"},
                    "decimals": {
                        "type": "string",
                        "description": "Número de decimales como string: '0'..'6'",
                    },
                    "stacked": {
                        "type": "string",
                        "description": "true si el gráfico es apilado, false si no",
                    },
                },
            },
        },
        "required": ["type", "labels", "series"],
    }

    compact_reply = _trim_text(agent_reply.strip(), _INPUT_MAX_CHARS)
    user_ctx = (user_prompt or "").strip()
    prefer_ctx = ", ".join(prefer_list) if prefer_list else ""

    prompt = (
        f"""
    REGLA ESTRICTA:
    - SOLO DEVOLVER UN GRÁFICO CUANDO EL USUARIO LO PIDA EXPLÍCITAMENTE. sin importar el contexto. Si no lo pide, devolve un json así: {{ "no_chart": true }}.

    Eres un generador de especificaciones de gráficos. A partir del texto del asistente a continuación, produce UN solo gráfico.
    Devuelve SOLO JSON válido, sin comentarios ni texto extra. El JSON debe seguir este esquema:
    {json.dumps(schema_hint, ensure_ascii=False)}

    Reglas estrictas:
    - labels y cada series[i].data deben tener la misma longitud.
    - Si no hay datos suficientes, devuelve un gráfico 'bar' con una sola etiqueta 'Sin datos' y valores 0.
    - No inventes categorías o valores extremos si el texto no lo sugiere.
    - Usa nombres legibles para series y títulos breves.
    - *default:* Si existen más de 7 categorías distintas, consolida aquellas con los valores más bajos bajo la categoría 'Otros'.
    - +Excepciones:* Si la categoria es fechas, no generes el grupo 'Otros' y brinda el resultado completo.
    - +Excepciones:* Si el usuario te indica ver el grafico completo a detalle, no generes el grupo 'Otros' y brinda el resultado completo
 
    Formato y unidades (importante):
    - Si del texto se infieren unidades, completa el campo meta con:
    - unit_type: uno de ["number", "currency", "percent", "unit"].
    - currency: código de moneda (ej.: "USD", "ARS") si aplica.
    - unit_label: etiqueta corta de unidad (ej.: "UEQ", "Kg", "Uds") si aplica.
    - value_prefix y/o value_suffix si corresponde (ej.: "$" como prefijo, "%" como sufijo).
    - decimals sugerido como string entre '0' y '6' (por ejemplo: "2").
    - Ejemplos: "$44,167,913.43 USD" -> unit_type="currency", currency="USD", value_prefix="$"; "79.66%" -> unit_type="percent", value_suffix="%"; "965,589.00 UEQ" -> unit_type="unit", unit_label="UEQ".

    Preferencias (si existen):
    - Prompt del usuario: {user_ctx}
    - Tipos preferidos: [{prefer_ctx}] (elige el primero que tenga sentido con los datos)
    - Si el texto contiene tabla con 3+ columnas, prioriza 'pie' salvo que no tenga sentido.

    Contexto estructural:
    - is_table: {is_table}
    - column_count: {column_count}

    Intención de gráfico:
    - Solo genera un gráfico si el prompt del usuario pide explícitamente visualizar/graficar (p. ej.: “gráfico”, “grafico”, “chart”, “visualizar”, “barras”, “línea/linea”, “pie/torta”, “stacked/apilado”).
    - Si NO hay intención explícita de gráfico, responde EXACTAMENTE este JSON sin texto adicional:
    {{ "no_chart": true }}

    Regla de legibilidad (importante):
    - Si la cantidad de categorías supera 7, devuelve solo las 7 de mayor valor
    y agrega una categoría final llamada "Otros" que agrupe el resto (sumando).
    Asegúrate de que 'labels' y 'series[0].data' reflejen esa agregación.
    - Default: Si existen más de 7 categorías distintas, consolida las de menor valor bajo 'Otros'.
    - Excepciones: Si la categoría es de fechas (por ejemplo YYYY-MM-DD o DD/MM/YYYY), no generes 'Otros' y devuelve el resultado completo.
    - Excepciones: Si el usuario pide ver el gráfico completo/detallado (por ejemplo contiene 'detalle', 'completo', 'sin agrupar', 'ver completo'), no generes 'Otros' y devuelve el resultado completo.

    # REGLA: Series múltiples y Apilado
    - Series múltiples (array 'series'):
    1) Si se comparan 2+ métricas para las mismas categorías (ej.: "Ventas vs Costos" por mes), o
    2) Si hay 1 métrica desglosada por un segmento/dimensión (ej.: "Ventas por Región/Cliente").
    Por defecto: 'name' de la serie = segmento; 'labels' = la otra dimensión.
    - Apilado (meta.stacked = "true"):
    - Actívalo si el texto pide "apilado/stacked", o "apilados por [DIMENSIÓN]", o si las series son "partes de un todo" (desglosados/compuesto por).
    - Si dice "apilados por [DIMENSIÓN]", usa esa [DIMENSIÓN] para los 'name' de 'series' y la otra dimensión como 'labels'.
    - Coherencia de eje (crítica): TODAS las series deben usar EXACTAMENTE el mismo arreglo de 'labels' (mismo orden y longitud).
    No concatentes listas separadas por segmento. Si una categoría no existe para una serie, usa 0 en esa posición.

    Formato y unidades (importante):
    - Si del texto se infieren unidades, completa el campo meta con:
    - unit_type: uno de ["number", "currency", "percent", "unit"].
    - currency: código de moneda (ej.: "USD", "ARS") si aplica.
    - unit_label: etiqueta corta de unidad (ej.: "UEQ", "Kg", "Uds") si aplica.
    - value_prefix y/o value_suffix si corresponde (ej.: "$" como prefijo, "%" como sufijo).
    - decimals sugerido como string entre '0' y '6' (por ejemplo: "2").
    - Ejemplos: "$44,167,913.43 USD" -> unit_type="currency", currency="USD", value_prefix="$"; "79.66%" -> unit_type="percent", value_suffix="%"; "965,589.00 UEQ" -> unit_type="unit", unit_label="UEQ".

    Texto del asistente:
    """
        + compact_reply
        + """
    """
    )

    try:
        resp = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "temperature": 0,
                "top_p": 0.8,
                "top_k": 20,
                "max_output_tokens": 8192,
            },
        )
        raw_text: Optional[str] = getattr(resp, "text", None)
        if not raw_text or not raw_text.strip():
            raise RuntimeError("La respuesta de Vertex AI (google-genai) está vacía")

        print("raw_text: ", raw_text)
        parsed = _extract_json_object(raw_text)

        # Si la IA indica explícitamente que NO genere gráfico
        if isinstance(parsed, dict) and parsed.get("no_chart") is True:
            return ChartSpec(
                type="bar",
                title="Sin datos suficientes",
                labels=["Sin datos"],
                series=[{"name": "Valores", "data": [0]}],
                meta={"reason": "fallback"},
            )

        if parsed is None:
            raise RuntimeError("Respuesta de IA no fue JSON válido")
        # Normalización de meta.decimals a string para cumplir con el modelo
        try:
            meta = parsed.get("meta") if isinstance(parsed, dict) else None
            if isinstance(meta, dict) and "decimals" in meta:
                if isinstance(meta["decimals"], int):
                    meta["decimals"] = str(meta["decimals"])  # e.g., 2 -> "2"
                elif meta["decimals"] is None:
                    meta.pop("decimals", None)
            # Normalizar stacked a string si viene boolean (compat Pydantic actual)
            if isinstance(meta, dict) and "stacked" in meta:
                if isinstance(meta["stacked"], bool):
                    meta["stacked"] = "true" if meta["stacked"] else "false"
        except Exception:
            pass
        # Forzar tipo preferido si se indicó y el generado no está permitido
        try:
            if (prefer_list) and isinstance(parsed, dict):
                pt = [t for t in prefer_list if isinstance(t, str)]
                if pt:
                    gen_type = (parsed.get("type") or "").lower()
                    pt_norm = [t.lower() for t in pt]
                    if gen_type not in pt_norm:
                        parsed["type"] = pt[0]
        except Exception:
            pass

        spec = ChartSpec.model_validate(parsed)
        _cache_put(key, spec)
        return spec

    except (json.JSONDecodeError, ValidationError, Exception) as e:
        logger.exception("Fallo generando ChartSpec: %s", e)
        if not fallback_on_error:
            raise
        spec = ChartSpec(
            type="bar",
            title="Sin datos suficientes",
            labels=["Sin datos"],
            series=[{"name": "Valores", "data": [0]}],
            meta={"reason": "fallback"},
        )
        _cache_put(key, spec)
        return spec


"""
    Generacion de graficos
"""

import os

import matplotlib

matplotlib.use("Agg")
import datetime
import io
import logging
import uuid
from functools import lru_cache

import matplotlib.pyplot as plt
from google.cloud import storage

# --- Configuración ---
# Lee el nombre del bucket desde una variable de entorno
GCS_BUCKET_NAME = os.getenv("GCS_CHARTS_BUCKET")
SA_KEY_PATH = os.getenv("SERVICE_ACCOUNT_KEY_PATH")
if not GCS_BUCKET_NAME:
    logging.warning("GCS_CHARTS_BUCKET no está configurada. El renderizador fallará.")
if not SA_KEY_PATH:
    logging.warning(
        "SERVICE_ACCOUNT_KEY_PATH no está configurada. Se usará ADC si es posible."
    )


class SecureChartGenerator:
    """
    Renderiza un JSON de gráfico a PNG, lo sube a GCS
    y devuelve una URL firmada.
    """

    # --- __init__ (Modificado) ---
    def __init__(self, bucket_name: str, key_file_path: str):
        """
        Inicializa el generador usando un bucket y una llave SA explícita.
        """
        if not bucket_name:
            raise ValueError("El nombre del bucket de GCS no puede estar vacío.")
        if not key_file_path:
            raise ValueError(
                "La ruta del archivo de llave SA (key_file_path) no puede estar vacía."
            )

        try:
            # USA LA LLAVE SA EXPLÍCITA
            self.storage_client = storage.Client.from_service_account_json(
                key_file_path
            )
            logger.info(f"Cliente de GCS inicializado con llave: {key_file_path}")
        except Exception as e:
            logger.error(
                f"Error fatal: No se pudo cargar la llave SA desde '{key_file_path}'. {e}"
            )
            raise e

        try:
            self.bucket = self.storage_client.get_bucket(bucket_name)
            logger.info(f"Conectado al bucket de GCS: {bucket_name}")
        except Exception as e:
            logger.error(
                f"Error fatal: No se pudo acceder al bucket '{bucket_name}'. {e}"
            )
            raise e

    # --- generate_signed_url (Modificado para usar la firma correcta) ---
    def generate_signed_url(self, json_string: str) -> str:
        try:
            data = json.loads(json_string)
        except json.JSONDecodeError as e:
            logger.error(f"Error al decodificar JSON: {e}")
            return None

        # ... (lógica de _plot_pie, _plot_bar, etc. ... sin cambios)
        chart_type = data.get("type")
        image_buffer = None
        if chart_type == "pie":
            image_buffer = self._plot_pie(data)
        elif chart_type == "bar":
            image_buffer = self._plot_bar(data)
        elif chart_type == "line":
            image_buffer = self._plot_line(data)
        # ... (resto de la lógica) ...

        if image_buffer is None:
            logger.error("No se pudo generar el buffer de la imagen.")
            return None

        # ... (lógica de subida a GCS ... sin cambios)
        try:
            blob_name = f"charts/render_{uuid.uuid4()}.png"
            blob = self.bucket.blob(blob_name)
            blob.upload_from_file(image_buffer, content_type="image/png")
        except Exception as e:
            logger.error(f"Error al subir a GCS: {e}")
            return None

        # 3. Generar la URL firmada (V4)
        try:
            # USA EL MÉTODO CORREGIDO
            signed_url = blob.generate_signed_url(
                version="v4", expiration=datetime.timedelta(hours=1), method="GET"
            )
            return signed_url
        except Exception as e:
            # Este error ya no debería ser por credenciales
            logger.error(f"Error al firmar la URL: {e}")
            return None

    # ... (El resto de tus métodos _save_to_buffer, _plot_pie, _plot_bar, _plot_line
    # ...  permanecen exactamente iguales que antes) ...

    def _save_to_buffer(self, fig) -> io.BytesIO:
        """Helper: Guarda una figura de Matplotlib en un buffer de memoria."""
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        return buf

    def _plot_pie(self, data):
        try:
            fig, ax = plt.subplots(figsize=(8, 6))
            meta = data.get("meta", {})
            decimals = int(meta.get("decimals", 0))
            suffix = meta.get("value_suffix", "%")

            # Escapar el '%' para autopct
            if suffix == "%":
                suffix = "%%"

            autopct_format = f"%.{decimals}f{suffix}"

            ax.pie(
                data["series"][0]["data"],
                labels=data["labels"],
                autopct=autopct_format,
                startangle=90,
                colors=plt.cm.Paired.colors,
            )
            ax.axis("equal")
            plt.title(data.get("title", "Gráfico"), fontsize=16)
            return self._save_to_buffer(fig)
        except Exception as e:
            logger.error(f"Error en _plot_pie: {e} | Data: {data}")
            plt.close(fig)
            return None

    def _plot_bar(self, data):
        try:
            fig, ax = plt.subplots(figsize=(10, 6))
            series = data["series"][0]
            ax.bar(data["labels"], series["data"], color="#007bff")
            ax.set_title(data.get("title", "Gráfico"), fontsize=16)
            ax.set_ylabel(series.get("name", "Valores"))

            # --- SOLUCIÓN ---
            # Se eliminó 'ha="right"' de esta línea
            ax.tick_params(axis="x", rotation=45)
            # -----------------

            plt.grid(axis="y", linestyle="--", alpha=0.7)
            return self._save_to_buffer(fig)
        except Exception as e:
            logger.error(f"Error en _plot_bar: {e} | Data: {data}")
            plt.close(fig)
            return None

    def _plot_line(self, data):
        try:
            fig, ax = plt.subplots(figsize=(10, 6))
            series = data["series"][0]
            ax.plot(data["labels"], series["data"], marker="o", color="#28a745")
            ax.set_title(data.get("title", "Gráfico"), fontsize=16)
            ax.set_ylabel(series.get("name", "Valores"))

            # --- SOLUCIÓN ---
            # Se eliminó 'ha="right"' de esta línea
            ax.tick_params(axis="x", rotation=45)
            # -----------------

            plt.grid(axis="both", linestyle="--", alpha=0.7)
            return self._save_to_buffer(fig)
        except Exception as e:
            logger.error(f"Error en _plot_line: {e} | Data: {data}")
            plt.close(fig)
            return None


@lru_cache()
def get_chart_generator() -> SecureChartGenerator:
    """
    Dependencia de FastAPI para obtener el generador de gráficos singleton.
    Ahora usa GCS_CHARTS_BUCKET y SERVICE_ACCOUNT_KEY_PATH.
    """
    if not GCS_BUCKET_NAME:
        raise RuntimeError(
            "GCS_CHARTS_BUCKET no está configurado. El servicio no puede inicializarse."
        )

    # AÑADE ESTA VALIDACIÓN
    if not SA_KEY_PATH:
        raise RuntimeError(
            "SERVICE_ACCOUNT_KEY_PATH no está configurado. "
            "El servicio no puede inicializarse con la llave explícita."
        )

    # PASA LA RUTA DE LA LLAVE AL CONSTRUCTOR
    return SecureChartGenerator(bucket_name=GCS_BUCKET_NAME, key_file_path=SA_KEY_PATH)
