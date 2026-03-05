from __future__ import annotations
from datetime import datetime

from typing import Optional, Dict, Any, List, Literal, Tuple
from pydantic import BaseModel, EmailStr, Field
import uuid
import logging

logger = logging.getLogger(__name__)


"""
    Bloque para flujo Databricks
"""


class DatabricksConfig(BaseModel):
    """Configuración específica requerida si engine='databricks'"""

    http_path: str = Field(..., description="El HTTP Path del SQL Warehouse")
    client_id: str = Field(..., description="Service Principal Client ID")
    client_secret: str = Field(..., description="Service Principal Client Secret")


# class SemanticSelection(BaseModel):
#     """Define la selección de una tabla y sus columnas"""
#     schema_name: str
#     table: str
#     columns: Optional[List[str]] = None
#     column_specs: Optional[List[Dict[str, Any]]] = None
#     time_dimension: Optional[str] = None
#     primary_key: Optional[str] = None

####


class ColumnSelection(BaseModel):
    schema_name: str
    table: str
    columns: Optional[List[str]] = None
    column_specs: Optional[List[Dict[str, Optional[str]]]] = (
        None  # {'name','description','data_type','role(dimension|measure)','aggregation(sum|count|avg|min|max)'}
    )
    time_dimension: Optional[str] = None
    primary_key: Optional[str] = None


class BuildRequest(BaseModel):
    server_url: str
    product_id: Optional[str] = None
    database: str
    selections: List[ColumnSelection]
    infer_types: Optional[bool] = True
    add_default_measures: Optional[bool] = True
    time_dimension_candidates: Optional[List[str]] = [
        "fecha",
        "date",
        "created_at",
        "updated_at",
        "timestamp",
        "fecha_factura",
    ]
    engine: Optional[
        Literal[
            "postgres",
            "mysql",
            "bigquery",
            "databricks",
            "mariadb",
            "mssql",
            "synapsemssql",
            "redshift",
            "snowflake",
            "aurora",
            "aurorapostgres",
            "auroramysql",
            "hana",
            "oracle",
            "teradata",
            "clickhouse",
        ]
    ] = "postgres"
    include_profiling: Optional[bool] = False
    bucket_name: Optional[str] = None
    object_path: Optional[str] = None

    databricks_config: Optional[DatabricksConfig] = None


class UpdateRequest(BaseModel):
    server_url: str
    database: str
    product_id: Optional[str] = None
    client: Optional[str] = None
    selections: List[ColumnSelection]
    infer_types: Optional[bool] = True
    add_default_measures: Optional[bool] = True
    time_dimension_candidates: Optional[List[str]] = [
        "fecha",
        "date",
        "created_at",
        "updated_at",
        "timestamp",
        "fecha_factura",
    ]
    engine: Optional[
        Literal[
            "postgres",
            "mysql",
            "bigquery",
            "mariadb",
            "mssql",
            "synapsemssql",
            "redshift",
            "snowflake",
            "aurora",
            "aurorapostgres",
            "auroramysql",
            "hana",
            "oracle",
            "teradata",
            "clickhouse",
        ]
    ] = "postgres"
    include_profiling: Optional[bool] = False
    # Ruta obligatoria del YAML previo. El nuevo reemplaza en el MISMO path.
    previous_gs_uri: str
    # Relaciones entre datasets (opcional)
    # Ej: {'left_dataset':'public.orders','left_key':'user_id','right_dataset':'public.users','right_key':'id','join_type':'inner','cardinality':'many_to_one'}
    relationships: Optional[List[Dict[str, Optional[str]]]] = None


class DescribeResponse(BaseModel):
    datasets: Dict[str, Dict]


# Construir SQL avanzado (multi-datasets con relaciones)
class QueryBuildAdvancedRequest(BaseModel):
    gs_uri: str
    engine: Optional[
        Literal[
            "postgres",
            "mysql",
            "bigquery",
            "mariadb",
            "mssql",
            "synapsemssql",
            "redshift",
            "snowflake",
            "aurora",
            "aurorapostgres",
            "auroramysql",
            "hana",
            "oracle",
            "teradata",
            "clickhouse",
        ]
    ] = "postgres"
    dimensions: List[str]  # ['schema.table.field']
    measures: List[str]  # ['schema.table.field']
    filters: Optional[List[Dict]] = None  # [{'dataset_key','field','op','value'}]
    order_by: Optional[List[Tuple[int, Literal["ASC", "DESC"]]]] = None
    limit: Optional[int] = None
    # Medidas derivadas inline (opcional) para no depender de editar el YAML previo
    # Ej: [{"dataset_key":"public.facturacion_argentina","name":"NIP_Real_Ponderado","expression":"ROUND((SUM(\"Importe\") / SUM(\"Fact_UEQ\"))::numeric, 2)","description":"NIP real ponderado"}]
    derived_measures: Optional[List[Dict[str, Optional[str]]]] = None


class QueryBuildAdvancedResponse(BaseModel):
    sql: str


# Ejecutar SQL en MindsDB
class QueryRunRequest(BaseModel):
    server_url: str
    database: str
    sql: str


class QueryRunReq(BaseModel):
    connection_id: Optional[str] = Field(None, description="El ID único de la conexión")
    sql: str = Field(..., description="La consulta SQL a ejecutar")
    connection_name: Optional[str] = Field(
        None, description="Nombre opcional de la conexión"
    )


class QueryRunResponse(BaseModel):
    status: str
    rows: Optional[List[Dict]] = None
    message: Optional[str] = None


"""
    Bloque para control de Semantic Layers:
"""


class SemanticLayerGetByIDRequest(BaseModel):
    """Modelo para obtener un registro por ID, enviado en el body."""

    config_id: str = Field(..., description="UUID del registro de configuración.")


class SemanticLayerGetByProductRequest(BaseModel):
    """Modelo para obtener registros por product_id, enviado en el body."""

    product_id: str = Field(..., description="UUID del producto para filtrar.")


# --- Modelos de Datos de la Tabla ---
class SemanticLayerConfigData(BaseModel):
    """Modelo para representar un registro de semantic_layer_configs."""

    id: str = Field(..., description="str del registro de configuración.")
    product_id: str = Field(..., description="str del producto asociado.")
    object_path_saved: str = Field(..., description="Ruta del objeto guardado.")
    bucket_name_saved: str = Field(
        ..., description="Nombre del bucket donde se guardó."
    )
    object_path_deployed: Optional[str] = Field(
        None, description="Ruta del objeto desplegado."
    )
    bucket_name_deployed: Optional[str] = Field(
        None, description="Nombre del bucket donde se desplegó."
    )
    created_at: datetime = Field(..., description="Fecha de creación.")
    updated_at: datetime = Field(..., description="Fecha de última actualización.")

    class Config:
        # Permite mapear los nombres de columna del DB (snake_case) a Pydantic (snake_case o camelCase si se configura alias)
        # Usamos from_attributes=True para Pydantic v2 (alias de orm_mode=True en v1)
        from_attributes = True


# --- Modelos de Request (Crea, Actualiza, Borra, Filtra) ---


# 1. INSERT (Mapea a los parámetros de spu_minddash_app_insert_role_semantic_layer)
class SemanticLayerCreateRequest(BaseModel):
    product_id: str
    object_path_saved: str
    bucket_name_saved: str
    object_path_deployed: Optional[str] = None
    bucket_name_deployed: Optional[str] = None


# 2. UPDATE (Mapea a los parámetros de spu_minddash_app_update_role_semantic_layer)
class SemanticLayerUpdateRequest(SemanticLayerCreateRequest):
    id: str = Field(..., description="str del registro a actualizar.")


# 3. DELETE (Mapea a los parámetros de spu_minddash_app_delete_role_semantic_layer)
class SemanticLayerDeleteRequest(BaseModel):
    id: str = Field(..., description="str del registro a eliminar.")


# --- Modelos de Response ---


# 1. GET - Filtro por un solo ID (semantic_layer_configs.id)
class SemanticLayerSingleResponse(BaseModel):
    config: SemanticLayerConfigData


# 2. GET - Filtro por product_id
class SemanticLayerListResponse(BaseModel):
    configs: List[SemanticLayerConfigData]


# 3. POST (INSERT)
class SemanticLayerCreationResponse(BaseModel):
    config_id: str = Field(
        ..., description="str del nuevo registro de configuración creado."
    )


# 4. PUT (UPDATE)
class SemanticLayerUpdateResponse(BaseModel):
    message: str = "Configuración de capa semántica actualizada exitosamente."
    config_id: str = Field(..., description="str del registro actualizado.")


# 5. DELETE
class SemanticLayerDeleteResponse(BaseModel):
    message: str = "Configuración de capa semántica eliminada exitosamente."
    config_id: str = Field(..., description="str del registro eliminado.")
