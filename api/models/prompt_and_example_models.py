from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


class Prompt(BaseModel):
    """Representa la estructura de la tabla 'prompts'."""

    id: UUID = Field(..., description="UUID del prompt.")
    product_id: UUID = Field(
        ..., description="UUID del producto al que pertenece este prompt."
    )
    name: str = Field(..., max_length=255, description="Nombre descriptivo del prompt.")
    config_prompt: Dict[str, Any] = Field(
        ..., description="Configuración del prompt en formato JSONB."
    )
    path_config_file: Optional[str] = Field(
        None, max_length=255, description="Ruta al archivo de configuración."
    )
    created_at: datetime = Field(..., description="Fecha de creación.")
    updated_at: datetime = Field(..., description="Fecha de última actualización.")

    class Config:
        from_attributes = True


"""
    Crear el Yaml con los datos de BD
"""


class UploadPromptRequestByProduct(BaseModel):
    """Solicitud para generar y subir el prompt YAML usando solo el ID del producto."""

    product_id: uuid.UUID = Field(
        ..., description="ID del producto para extraer la configuración del prompt."
    )
    bucket_name: str = Field(..., description="Nombre del bucket de GCS de destino.")
    object_path: str = Field(
        ...,
        description="Ruta y nombre del archivo YAML dentro del bucket (ej: prompts/agent/cyt_v2.yaml).",
    )
    embeddings_npy_path: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "product_id": "72a7c5c5-dcbb-4f08-8016-ae1ca63230a3",
                "bucket_name": "gs-minddash-agent-env",
                "object_path": "profiling/prompt_example_load.yaml",
            }
        }


class UploadPromptResponse(BaseModel):
    """Respuesta para la subida exitosa del archivo YAML."""

    status: str
    url: str


"""
    Modelos de gestiond y generacion de prompts
"""


class GetPromptsRequestByProduct(BaseModel):
    """
    Define los parámetros necesarios para obtener la lista de prompts
    filtrados por un producto y un usuario.
    """

    product_id: str = Field(
        ..., description="ID del producto cuyas prompts se desean obtener."
    )

    class Config:
        json_schema_extra = {
            "example": {"product_id": "a6f38618-4308-4dfc-83d7-4f98651649c1"}
        }


class GetPromptsResponseByProduct(BaseModel):
    """
    Define la estructura de datos de un prompt retornado desde la base de datos.
    Corresponde a las columnas seleccionadas en view_info_prompt_product.
    """

    prompt_id: uuid.UUID = Field(..., description="ID único del prompt registrado.")
    prompt_name: str = Field(..., description="Nombre descriptivo del prompt.")
    config_prompt: Dict[str, Any] = Field(
        ...,
        description="Contenido JSON (JSONB) del prompt, incluyendo reglas, lógica, etc.",
    )
    path_config_file: Optional[str] = Field(
        None,
        description="Ruta donde se almacena el archivo YAML/JSON de configuración.",
    )
    product_id: uuid.UUID = Field(
        ..., description="ID del producto al que pertenece el prompt."
    )
    name: str = Field(..., description="Nombre del producto asociado.")
    description: Optional[str] = Field(
        None, description="Descripción del producto o del prompt."
    )
    prompt_content: str = Field(..., description="Contenido del prompt.")

    class Config:
        # Permite la conversión de nombres de snake_case a camelCase en la respuesta
        # y asegura el manejo de datos provenientes de la DB
        from_attributes = True
        json_schema_extra = {
            "example": {
                "prompt_id": "11111111-2222-3333-4444-555555555555",
                "prompt_name": "Prompt Cyt Ventas",
                "config_prompt": {
                    "role_principal_del_agente": "Eres Diablo...",
                    "logica_seleccion_tabla": [],
                },
                "path_config_file": "prompts/cyt/ventas.yaml",
                "product_id": "a6f38618-4308-4dfc-83d7-4f98651649c1",
                "name": "Cyt Chile",
                "prompt_content": "",
                "description": "Prompts de ventas para el BU Chile.",
            }
        }


class PromptsExample(BaseModel):
    user_query: str
    sql_query: str


class BuildPromptsExamplesRequest(BaseModel):
    examples: List[PromptsExample]
    bucket_name: str
    # rutas destino dentro del bucket
    examples_yaml_path: str  # p.ej. examples_agents/cliente_x.yaml
    embeddings_npy_path: str  # p.ej. examples_agents/cliente_x.npy
    model_name: Optional[str] = "paraphrase-multilingual-mpnet-base-v2"


class BuildPromptsExamplesResponse(BaseModel):
    status: str
    examples_yaml_url: str
    embeddings_npy_url: str


class UploadPromptRequest(BaseModel):
    version: str
    product: str
    prompt_name: str
    description: str
    prompt_content: str
    bucket_name: str
    object_path: str  # p.ej. prompts/agent_prompt_x.yaml


# class ExampleListResponseItem(BaseModel):
#     id: str
#     product_id: str
#     name: str  # Corresponde a 'user_query'
#     description: Optional[str] = None
#     data_query: str  # Corresponde a 'sql_query'
#     created_at: Any
#     updated_at: Any


# class BuildPromptsExamplesByProductRequest(BaseModel):
#     product_id: str
#     bucket_name: str
#     # rutas destino dentro del bucket
#     examples_yaml_path: str  # p.ej. examples_agents/cliente_x.yaml
#     embeddings_npy_path: str  # p.ej. examples_agents/cliente_x.npy
#     model_name: Optional[str] = "paraphrase-multilingual-mpnet-base-v2"


"""
    Modelos de gestiond de datos de prompts
"""


class PromptRegisterRequest(BaseModel):
    """Datos necesarios para llamar a spu_minddash_app_insert_prompt."""

    product_id: str = Field(..., description="ID del producto al que pertenece.")
    name: str = Field(..., max_length=255, description="Nombre del prompt.")
    config_prompt: Dict[str, Any] = Field(
        default_factory=lambda: {}, description="Configuración JSONB."
    )
    path_config_file: Optional[str] = Field(
        None, max_length=255, description="Ruta opcional al archivo."
    )
    prompt_content: str = Field(..., description="Contenido del prompt.")


class PromptRegisterRequestV2(BaseModel):
    """Datos necesarios para llamar a spu_minddash_app_insert_prompt."""

    product_id: str = Field(..., description="ID del producto al que pertenece.")
    name: str = Field(..., max_length=255, description="Nombre del prompt.")
    config_prompt: Optional[PromptConfig] = Field(
        None, description="Configuración JSONB (opcional)."
    )
    path_config_file: Optional[str] = Field(
        None, max_length=255, description="Ruta opcional al archivo."
    )
    prompt_content: str = Field(..., description="Contenido del prompt.")


class PromptUpdateRequest(BaseModel):
    """Datos necesarios para llamar a spu_minddash_app_update_prompt."""

    id: str = Field(..., description="ID del prompt a actualizar.")
    product_id: Optional[str] = Field(
        None, description="Nuevo ID del producto (opcional)."
    )
    name: Optional[str] = Field(
        None, max_length=255, description="Nuevo nombre (opcional)."
    )
    config_prompt: Optional[Dict[str, Any]] = Field(
        None, description="Nueva configuración JSONB (opcional)."
    )
    path_config_file: Optional[str] = Field(
        None, max_length=255, description="Nueva ruta opcional (opcional)."
    )
    prompt_content: str = Field(..., description="Contenido del prompt.")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "1e2f3g4h-5i6j-7k8l-9m0n-1o2p3q4r5s6t",
                "name": "Generación de Resumen V2",
                "config_prompt": {"temperature": 0.5},
                "path_config_file": "example.yaml",
                "prompt_content": "prompt_content",
                "product_id": "a6f38618-4308-4dfc-83d7-4f98651649c1",
            }
        }


class PromptUpdateRequestV2(BaseModel):
    """Datos necesarios para llamar a spu_minddash_app_update_prompt."""

    id: str = Field(..., description="ID del prompt a actualizar.")
    product_id: Optional[str] = Field(
        None, description="Nuevo ID del producto (opcional)."
    )
    name: Optional[str] = Field(
        None, max_length=255, description="Nuevo nombre (opcional)."
    )
    config_prompt: Optional[PromptConfig] = Field(
        None, description="Nueva configuración JSONB (opcional)."
    )
    path_config_file: Optional[str] = Field(
        None, max_length=255, description="Nueva ruta opcional (opcional)."
    )
    prompt_content: str = Field(..., description="Contenido del prompt.")


class PromptConfig(BaseModel):
    temperature: Optional[float] = Field(..., ge=0, le=1)
    agent_main_role: str
    business_rules: str
    advanced_agent_metrics: List[Optional[Metric]]
    table_selection_logic: List[TableSelectionLogic]
    additional_considerations: Optional[str] = None

    @field_validator("agent_main_role")
    @classmethod
    def append_current_date_info(cls, v: str) -> str:
        suffix = " La fecha actual para todas las consultas es: {fecha_actual}."
        if v and not v.endswith(suffix):
            return f"{v}{suffix}"
        return v


class TableSelectionLogic(BaseModel):
    table_name: str
    usage_instructions: str
    validation: str
    important_notes: str


class Metric(BaseModel):
    name: str
    metric: str
    parameters: List[MetricParameter]


class MetricParameter(BaseModel):
    parameter: str
    meaning: str


class PromptDeleteRequest(BaseModel):
    """Datos necesarios para llamar a spu_minddash_app_delete_prompt."""

    id: str = Field(..., description="ID del prompt a eliminar.")


class PromptCreationResponse(BaseModel):
    id_prompt: str = Field(..., description="UUID del prompt recién creado.")


class PromptUpdateResponse(BaseModel):
    message: str = Field(
        "Prompt actualizado exitosamente.", description="Mensaje de confirmación."
    )
    id_prompt: str = Field(..., description="UUID del prompt actualizado.")


class PromptDeleteResponse(BaseModel):
    message: str = Field(
        "Prompt eliminado exitosamente.", description="Mensaje de confirmación."
    )
    id_prompt: str = Field(..., description="UUID del prompt eliminado.")


"""
    Modelos de gestiond de datos de examples
"""


# class ExampleListResponseItem(BaseModel):
#     id: str
#     product_id: str
#     name: str  # Corresponde a 'user_query'
#     description: Optional[str] = None
#     data_query: str  # Corresponde a 'sql_query'
#     created_at: Any
#     updated_at: Any


# --- Nuevo Request Model para la nueva ruta ---


class BuildPromptsExamplesByProductRequest(BaseModel):
    product_id: str
    bucket_name: str
    # rutas destino dentro del bucket
    examples_yaml_path: str  # p.ej. examples_agents/cliente_x.yaml
    embeddings_npy_path: str  # p.ej. examples_agents/cliente_x.npy
    model_name: Optional[str] = "paraphrase-multilingual-mpnet-base-v2"

    class Config:
        json_schema_extra = {
            "example": {
                "bucket_name": "gs-minddash-agent-env",
                "embeddings_npy_path": "examples_agents/few_shot_examples_develop.npy",
                "examples_yaml_path": "examples_agents/few_shot_examples_develop.yaml",
                "model_name": "paraphrase-multilingual-mpnet-base-v2",
                "product_id": "72a7c5c5-dcbb-4f08-8016-ae1ca63230a3",
            }
        }


class ExampleListRequest(BaseModel):
    """Define el UUID del producto para filtrar los ejemplos."""

    product_id: str = Field(..., description="UUID del producto para filtrar.")

    class Config:
        json_schema_extra = {
            "example": {"product_id": "72a7c5c5-dcbb-4f08-8016-ae1ca63230a3"}
        }


class ExampleListResponseItem(BaseModel):
    """Estructura de un solo ejemplo devuelto por el GET."""

    id: str = Field(..., description="UUID del ejemplo.")
    product_id: str = Field(..., description="UUID del producto asociado.")
    name: str = Field(..., description="Nombre del ejemplo.")
    description: str = Field(..., description="Descripción del ejemplo.")
    data_query: str = Field(..., description="Consulta de datos asociada al ejemplo.")
    created_at: datetime = Field(..., description="Fecha de creación.")
    updated_at: datetime = Field(..., description="Fecha de última actualización.")

    class Config:
        # Permite mapear los nombres de columna (snake_case) a los campos del modelo
        from_attributes = True


# --- Peticiones (Requests) ---


class ExampleRegisterRequest(BaseModel):
    """Datos necesarios para llamar a spu_minddash_app_insert_example."""

    product_id: str = Field(
        ..., description="ID del producto al que pertenece el ejemplo."
    )
    name: str = Field(..., max_length=255, description="Nombre del ejemplo.")
    description: str = Field(
        ..., max_length=200, description="Descripción del ejemplo (VARCHAR)."
    )
    data_query: str = Field(..., description="Query SQL o datos de ejemplo (TEXT).")

    class Config:
        json_schema_extra = {
            "example": {
                "product_id": "72a7c5c5-dcbb-4f08-8016-ae1ca63230a3",
                "name": "Ejemplo de Ventas Regionales",
                "description": "Query para sumar ventas por región.",
                "data_query": "SELECT region, sum(sales) FROM transactions WHERE date > current_date - interval '1 month' GROUP BY region",
            }
        }


class ExampleUpdateRequest(BaseModel):
    """Datos necesarios para llamar a spu_minddash_app_update_example."""

    id: str = Field(..., description="ID del ejemplo a actualizar.")
    product_id: Optional[str] = Field(
        None, description="Nuevo ID del producto (opcional)."
    )
    name: Optional[str] = Field(
        None, max_length=200, description="Nuevo nombre (opcional)."
    )
    description: Optional[str] = Field(
        None, max_length=200, description="Nueva descripción (opcional)."
    )
    data_query: Optional[str] = Field(None, description="Nuevo query SQL (opcional).")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "1e2f3g4h-5i6j-7k8l-9m0n-1o2p3q4r5s6t",
                "name": "Ejemplo de Ventas Regionales V2",
                "description": "Versión actualizada del query.",
                "product_id": "1e2f3g4h-5i6j-7k8l-9m0n-1o2p3q4r5s6t",
                "data_query": "SELECT region, sum(sales) FROM transactions WHERE date > current_date - interval ''1 month'' GROUP BY region",
            }
        }


class ExampleDeleteRequest(BaseModel):
    """Datos necesarios para llamar a spu_minddash_app_delete_example."""

    id: str = Field(..., description="ID del ejemplo a eliminar.")


# --- Respuestas (Responses) ---


class ExampleCreationResponse(BaseModel):
    id_example: str = Field(..., description="UUID del ejemplo recién creado.")


class ExampleUpdateResponse(BaseModel):
    message: str = Field(
        "Ejemplo actualizado exitosamente.", description="Mensaje de confirmación."
    )
    id_example: str = Field(..., description="UUID del ejemplo actualizado.")


class ExampleDeleteResponse(BaseModel):
    id_example: str = Field(..., description="UUID del ejemplo eliminado.")
