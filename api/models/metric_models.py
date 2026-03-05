from __future__ import annotations

from typing import List, Optional

import yaml
from pydantic import BaseModel, Field

"""
    MODELOS PARA CARGAR EL YAML
"""


class LiteralStr(str):
    """Clase auxiliar para marcar strings que deben usar estilo literal en YAML (|)."""

    pass


def literal_str_representer(dumper, data):
    """Representador que usa el estilo literal | para preservar saltos de línea."""
    # Asegura que siempre use el estilo literal
    # Agregamos \n si es necesario para que PyYAML use | en lugar de |-
    normalized_data = str(data)
    if not normalized_data.endswith("\n"):
        normalized_data += "\n"

    return dumper.represent_scalar("tag:yaml.org,2002:str", normalized_data, style="|")


class LiteralDumper(yaml.SafeDumper):
    """Dumper personalizado que hereda de SafeDumper y usa LiteralStr."""

    pass


class MetricDefinition(BaseModel):
    """Define la estructura de una métrica individual enviada en el request."""

    metric_name: str = Field(
        ...,
        alias="name_metrics",
        description="Nombre clave de la métrica (ej: cross_selling_general)",
    )
    sql_template: str = Field(..., description="Plantilla SQL que define la métrica.")
    required_params: List[str] = Field(
        default_factory=list, description="Parámetros obligatorios en el SQL."
    )
    optional_params: Optional[List[str]] = Field(
        default_factory=list, description="Parámetros opcionales en el SQL."
    )

    # Permite usar 'name_metrics' en el JSON de entrada y mapearlo a 'metric_name'
    class Config:
        populate_by_name = True


# --- Clase Principal Modificada ---
class UploadMetricsRequest(BaseModel):
    version: str
    product: str
    metrics_name: str
    description: str
    # ¡CAMBIO CLAVE AQUÍ! Ahora es una lista de MetricDefinition
    metrics_data: List[MetricDefinition] = Field(
        ...,
        alias="metrics_content",
        description="Lista de objetos con las definiciones de métricas.",
    )
    bucket_name: str
    object_path: str

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "bucket_name": "gs-minddash-agent-env",
                "description": "Colección de métricas de Cross Selling y NIP.",
                "metrics_content": [
                    {
                        "name_metrics": "cross_selling_general",
                        "optional_params": ["group_by_select"],
                        "required_params": ["start_date", "end_date"],
                        "sql_template": "SELECT count(*) FROM facturacion WHERE...",
                    },
                    {
                        "name_metrics": "nip_real_ponderado",
                        "optional_params": [],
                        "required_params": ["start_date", "end_date"],
                        "sql_template": 'SELECT (SUM("Importe") / SUM("Fact_UEQ")) AS NIP FROM...',
                    },
                ],
                "metrics_name": "Metrics Collection V1",
                "object_path": "profiling/metrics_upload_example.yaml",
                "product": "cross_and_nip",
                "version": "1.0",
            }
        }


class UploadMetricsResponse(BaseModel):
    status: str
    url: str


class Metric(BaseModel):
    """
    Modelo base para representar una métrica.
    """

    pass


class MetricByProduct(BaseModel):
    """
    Representa una métrica con información del producto.
    """

    metric_id: str = Field(..., description="ID de la métrica.")
    metric_name: str = Field(..., description="Nombre de la métrica.")
    metric_description: Optional[str] = Field(
        None, description="Descripción de la métrica."
    )
    metric_data_query: Optional[str] = Field(
        None, description="Query de datos de la métrica."
    )
    metric_required_params: Optional[List[str]] = Field(
        None, description="Lista de nombres de parametros requeridos."
    )
    metric_optional_params: Optional[List[str]] = Field(
        None, description="Lista de nombres de parametros opcionales."
    )
    product_id: str = Field(..., description="ID del producto.")
    product_name: Optional[str] = Field(None, description="Nombre del producto.")

    class Config:
        from_attributes = True


class MetricRegisterRequest(BaseModel):
    """
    Datos necesarios para llamar a spu_minddash_app_insert_metric.
    """

    # --- Parámetros OBLIGATORIOS ---
    product_id: str = Field(
        ..., description="ID del producto al que pertenece la métrica."
    )
    name: str = Field(..., max_length=200, description="Nombre de la métrica.")
    description: str = Field(
        ..., max_length=200, description="Descripción de la métrica."
    )
    data_query: Optional[str] = Field(None, description="Query de datos de la métrica.")
    required_params: Optional[List[str]] = Field(
        None, description="Lista de nombres de parametros requeridos."
    )
    optional_params: Optional[List[str]] = Field(
        None, description="Lista de nombres de parametros opcionales."
    )

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "product_id": "a6f38618-4308-4dfc-83d7-4f98651649c1",
                "name": "Usuarios Activos Diarios",
                "description": "Número de usuarios únicos que interactúan con el producto cada día",
                "data_query": "SELECT COUNT(DISTINCT user_id) FROM user_interactions WHERE DATE(created_at) = CURRENT_DATE",
                "required_params": ["user_count", "order_volume", "revenue"],
                "optional_params": ["user_count", "order_volume", "revenue"],
            }
        }


class MetricUpdateRequest(BaseModel):
    """
    Datos necesarios para llamar a spu_minddash_app_update_metric.
    """

    # --- Parámetros de Identificación ---
    id: str = Field(..., description="ID de la métrica que se va a actualizar.")
    product_id: str = Field(..., description="ID del producto.")

    # --- Parámetros de Actualización ---
    name: str = Field(..., max_length=200, description="Nuevo nombre de la métrica.")
    description: str = Field(..., max_length=200, description="Nueva descripción.")
    data_query: Optional[str] = Field(None, description="Query de datos de la métrica.")
    required_params: Optional[List[str]] = Field(
        None, description="Lista de nombres de parametros requeridos."
    )
    optional_params: Optional[List[str]] = Field(
        None, description="Lista de nombres de parametros opcionales."
    )

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "1ee67952-ef83-4038-ae9d-d95d2f16c32e",
                "product_id": "a6f38618-4308-4dfc-83d7-4f98651649c1",
                "name": "Usuarios Activos Semanales",
                "description": "Número de usuarios únicos que interactúan con el producto cada semana",
                "data_query": {
                    "query": "SELECT COUNT(DISTINCT user_id) FROM user_interactions WHERE DATE(created_at) >= DATE_TRUNC('week', CURRENT_DATE)",
                    "type": "count",
                    "aggregation": "weekly",
                },
                "required_params": ["user_count", "order_volume", "revenue"],
                "optional_params": ["user_count", "order_volume", "revenue"],
            }
        }


class MetricDeleteRequest(BaseModel):
    """
    Datos necesarios para llamar a spu_minddash_app_delete_metric.
    Solo requiere el ID.
    """

    id: str = Field(..., description="ID de la métrica que se va a eliminar.")

    class Config:
        from_attributes = True
        json_schema_extra = {"example": {"id": "1ee67952-ef83-4038-ae9d-d95d2f16c32e"}}


class GetMetricsRequest(BaseModel):
    """
    Modelo para validar el cuerpo de la solicitud que puede contener un ID de métrica opcional.
    Si no se proporciona ID, retorna todas las métricas.
    """

    metric_id: Optional[str] = Field(
        None,
        description="ID de la métrica específica. Si no se proporciona, retorna todas las métricas.",
    )

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {"metric_id": "1ee67952-ef83-4038-ae9d-d95d2f16c32e"}
        }


class GetMetricsByProductRequest(BaseModel):
    """
    Modelo para validar el cuerpo de la solicitud que contiene el ID de producto.
    """

    product_id: str = Field(
        ..., description="ID del producto para el cual se buscan las métricas."
    )

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {"product_id": "a6f38618-4308-4dfc-83d7-4f98651649c1"}
        }


class MetricCreationResponse(BaseModel):
    """
    Respuesta al crear una nueva métrica.
    """

    id_metric: str = Field(..., description="ID de la métrica creada.")


# --- 1. Request Body Model ---
class UploadMetricsByProductRequest(BaseModel):
    """
    Define los parámetros necesarios para obtener métricas por ID de producto,
    formatearlas en YAML y subirlas a GCS.
    """

    product_id: str = Field(
        ...,
        description="ID del producto cuyas métricas se cargarán de la base de datos.",
    )
    bucket_name: str = Field(..., description="Nombre del bucket de GCS de destino.")
    object_path: str = Field(
        ...,
        description="Ruta y nombre del archivo dentro del bucket (ej: metrics/v1/producto_x.yaml).",
    )
    client: Optional[str] = None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "product_id": "72a7c5c5-dcbb-4f08-8016-ae1ca63230a3",
                "bucket_name": "gs-minddash-agent-env",
                "object_path": "profiling/metrics_example.yaml",
            }
        }


# --- 2. Response Model ---
class UploadMetricsByProductResponse(BaseModel):
    """
    Define la respuesta que confirma el éxito de la subida del YAML a GCS.
    """

    status: str = Field(..., description="Estado de la operación (ej: 'success').")
    url: str = Field(
        ..., description="URL pública o interna del archivo YAML subido en GCS."
    )

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "status": "success",
                "url": "https://storage.googleapis.com/minddash-metrics-definitions-prod/metrics/v1/cross_and_nip_metrics.yaml",
            }
        }


class MetricUpdateResponse(BaseModel):
    """
    Respuesta al actualizar una métrica.
    """

    message: str = Field(
        "Métrica actualizada exitosamente.", description="Mensaje de confirmación."
    )
    metric_id: str = Field(..., description="ID de la métrica actualizada.")


class MetricDeleteResponse(BaseModel):
    """
    Respuesta al eliminar una métrica.
    """

    message: str = Field(
        "Métrica eliminada exitosamente.", description="Mensaje de confirmación."
    )
    metric_id: str = Field(..., description="ID de la métrica eliminada.")


class MetricResponse(BaseModel):
    """
    Respuesta para una métrica individual.
    """

    metric_id: str = Field(..., description="ID de la métrica.")
    metric_name: str = Field(..., description="Nombre de la métrica.")
    metric_description: Optional[str] = Field(
        None, description="Descripción de la métrica."
    )
    metric_data_query: Optional[str] = Field(
        None, description="Query de datos de la métrica."
    )
    metric_required_params: Optional[List[str]] = Field(
        None, description="Lista de nombres de parametros requeridos."
    )
    metric_optional_params: Optional[List[str]] = Field(
        None, description="Lista de nombres de parametros opcionales."
    )
    product_id: str = Field(..., description="ID del producto.")
    product_name: Optional[str] = Field(None, description="Nombre del producto.")

    class Config:
        from_attributes = True
