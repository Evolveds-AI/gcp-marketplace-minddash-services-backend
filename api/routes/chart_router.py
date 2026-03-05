import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, HttpUrl

logger = logging.getLogger(__name__)
from typing import List, Optional

from api.models.chart_models import ChartSpec
from api.services.chart_service import (
    SecureChartGenerator,
    generate_chart_spec,
    get_chart_generator,
)

chart_router = APIRouter(prefix="/chart")


class ChartRequest(BaseModel):
    agent_reply: str
    user_prompt: Optional[str] = None
    preferred_types: Optional[List[str]] = None  # ej: ["pie"] o ["bar","line","pie"]
    is_table: Optional[bool] = None  # True si se detecto tabla en el cliente
    column_count: Optional[int] = None  # cantidad de columnas si hay tabla


@chart_router.post(
    "",
    response_model=ChartSpec,
    tags=["Visualización y Gráficos"],
    summary="Crear Especificación de Gráfico a partir de una respuesta de Agente",
    description=(
        "Recibe la respuesta natural del agente (`agent_reply`) y señales opcionales "
        "para preferir ciertos tipos de gráfico. Devuelve un ChartSpec."
    ),
)
def create_chart_spec(req: ChartRequest) -> ChartSpec:
    try:
        return generate_chart_spec(
            req.agent_reply,
            req.user_prompt,
            req.preferred_types,
            req.is_table,
            req.column_count,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# --- NUEVO ENDPOINT (Añade esto al final del archivo) ---


# --- Nuevo Modelo de Respuesta (Añádelo) ---
class RenderedChartResponse(BaseModel):
    """
    Respuesta que contiene la URL segura de la imagen generada.
    """

    image_url: HttpUrl
    chart_type: str
    message: str = "Gráfico renderizado exitosamente."


@chart_router.post(
    "/render",
    response_model=RenderedChartResponse,
    tags=["Visualización y Gráficos"],
    summary="Renderizar Especificación de Gráfico a Imagen Segura",
    description=(
        "Recibe un objeto **ChartSpec** (JSON) y lo renderiza como una imagen PNG. "
        "La imagen se sube de forma segura a un bucket de GCS privado y "
        "se devuelve una **URL firmada** (Signed URL) de corta duración para su visualización."
    ),
)
def render_chart_from_spec(
    spec: ChartSpec, generator: SecureChartGenerator = Depends(get_chart_generator)
) -> RenderedChartResponse:
    """
    Toma una especificación de gráfico y la convierte en una imagen PNG
    alojada en GCS con una URL firmada.
    """
    try:
        # Convierte el modelo Pydantic de nuevo a un string JSON
        # que nuestra clase generadora espera.
        json_string = spec.model_dump_json()

        # Llama al generador
        signed_url = generator.generate_signed_url(json_string)

        if not signed_url:
            logger.error(f"El generador falló al procesar el spec: {spec.title}")
            raise HTTPException(
                status_code=500,
                detail="Error interno: El generador no pudo crear la URL de la imagen.",
            )

        return RenderedChartResponse(image_url=signed_url, chart_type=spec.type)

    except Exception as e:
        logger.exception(f"Error inesperado en /render: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {e}")
