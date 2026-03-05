from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

"""
    Gestion de acceso a tabla roles
"""


class RoleDataAccess(BaseModel):
    """
    Modelo base para representar un rol de acceso a datos.
    """

    pass


class RoleDataAccessByProduct(BaseModel):
    """
    Representa un rol de acceso a datos con información del producto.
    """

    role_id: str = Field(..., description="ID del rol de acceso a datos.")
    role_name: str = Field(..., description="Nombre del rol.")
    role_table_names: List[str] = Field(..., description="Lista de nombres de tablas.")
    role_data_access: Optional[Dict[str, Any]] = Field(
        None, description="Configuración de acceso a datos."
    )
    role_metrics_access: List[str] = Field(
        None, description="Configuración de acceso a métricas."
    )
    product_id: str = Field(..., description="ID del producto.")
    product_name: Optional[str] = Field(None, description="Nombre del producto.")
    created_at: Optional[datetime] = Field(None, description="Fecha de creación.")
    updated_at: Optional[datetime] = Field(
        None, description="Fecha de última actualización."
    )

    class Config:
        from_attributes = True


class RoleDataAccessRegisterRequest(BaseModel):
    """
    Datos necesarios para llamar a spu_minddash_app_insert_role_data_access.
    """

    # --- Parámetros OBLIGATORIOS ---
    product_id: str = Field(..., description="ID del producto al que pertenece el rol.")
    name: str = Field(
        ..., max_length=255, description="Nombre del rol de acceso a datos."
    )
    table_names: List[str] = Field(..., description="Lista de nombres de tablas.")

    # --- Parámetros OPCIONALES ---
    data_access: Optional[Dict[str, Any]] = Field(
        None, description="Configuración de acceso a datos JSONB."
    )
    metrics_access: Optional[List[str]] = Field(
        None, description="Configuración de acceso a métricas JSONB."
    )

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "product_id": "82c9669b-7ad4-429f-a52f-8985a7b279e2",
                "name": "AllAccess",
                "table_names": [
                    "facturacion_argentina",
                    "tablon_target_real_2025",
                    "tablon_target_one_page_2025",
                    "dev_tablon_target_FYV_2025",
                ],
                "data_access": None,  # <<-- Valor None, que genera 'null' en JSON
                "metrics_access": [
                    "cross_selling_general",
                    "cross_selling_specific",
                    "cross_selling_agronomic",
                    "nip_real_ponderado",
                    "nip_target_ponderado",
                ],
            }
        }


class RoleDataAccessUpdateRequest(BaseModel):
    """
    Datos necesarios para llamar a spu_minddash_app_update_role_data_access.
    """

    # --- Parámetros de Identificación ---
    id: str = Field(..., description="ID del rol que se va a actualizar.")
    product_id: str = Field(..., description="ID del producto.")

    # --- Parámetros de Actualización ---
    name: str = Field(..., max_length=255, description="Nuevo nombre del rol.")
    table_names: List[str] = Field(..., description="Nueva lista de nombres de tablas.")
    data_access: Optional[Dict[str, Any]] = Field(
        None, description="Nueva configuración de acceso a datos."
    )
    metrics_access: Optional[List[str]] = Field(
        None, description="Nueva configuración de acceso a métricas."
    )

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "1ee67952-ef83-4038-ae9d-d95d2f16c32e",
                "product_id": "82c9669b-7ad4-429f-a52f-8985a7b279e2",
                "name": "AllAccess",
                "table_names": [
                    "facturacion_argentina",
                    "tablon_target_real_2025",
                    "tablon_target_one_page_2025",
                    "dev_tablon_target_FYV_2025",
                ],
                "data_access": None,  # <<-- Valor None, que genera 'null' en JSON
                "metrics_access": [
                    "cross_selling_general",
                    "cross_selling_specific",
                    "cross_selling_agronomic",
                    "nip_real_ponderado",
                    "nip_target_ponderado",
                ],
            }
        }


class RoleDataAccessDeleteRequest(BaseModel):
    """
    Datos necesarios para llamar a spu_minddash_app_delete_role_data_access.
    Solo requiere el ID.
    """

    id: str = Field(..., description="ID del rol que se va a eliminar.")

    class Config:
        from_attributes = True
        json_schema_extra = {"example": {"id": "1ee67952-ef83-4038-ae9d-d95d2f16c32e"}}


class GetRolesDataAccessRequest(BaseModel):
    """
    Modelo para validar el cuerpo de la solicitud que puede contener un ID de rol opcional.
    Si no se proporciona ID, retorna todos los roles.
    """

    role_id: Optional[str] = Field(
        None,
        description="ID del rol específico. Si no se proporciona, retorna todos los roles.",
    )

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {"role_id": "1ee67952-ef83-4038-ae9d-d95d2f16c32e"}
        }


class GetRolesDataAccessByProductRequest(BaseModel):
    """
    Modelo para validar el cuerpo de la solicitud que contiene el ID de producto.
    """

    product_id: str = Field(
        ..., description="ID del producto para el cual se buscan los roles."
    )

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {"product_id": "a6f38618-4308-4dfc-83d7-4f98651649c1"}
        }


class RoleDataAccessCreationResponse(BaseModel):
    """
    Respuesta al crear un nuevo rol de acceso a datos.
    """

    id_role: str = Field(..., description="ID del rol creado.")


class RoleDataAccessUpdateResponse(BaseModel):
    """
    Respuesta al actualizar un rol de acceso a datos.
    """

    message: str = Field(
        "Rol de acceso a datos actualizado exitosamente.",
        description="Mensaje de confirmación.",
    )
    role_id: str = Field(..., description="ID del rol actualizado.")


class RoleDataAccessDeleteResponse(BaseModel):
    """
    Respuesta al eliminar un rol de acceso a datos.
    """

    message: str = Field(
        "Rol de acceso a datos eliminado exitosamente.",
        description="Mensaje de confirmación.",
    )
    role_id: str = Field(..., description="ID del rol eliminado.")


class RoleDataAccessResponse(BaseModel):
    """
    Respuesta para un rol de acceso a datos individual.
    """

    role_id: str = Field(..., description="ID del rol.")
    role_name: str = Field(..., description="Nombre del rol.")
    role_table_names: List[str] = Field(..., description="Lista de nombres de tablas.")
    role_data_access: Optional[Dict[str, Any]] = Field(
        None, description="Configuración de acceso a datos."
    )
    role_metrics_access: Optional[List[str]] = Field(
        None, description="Configuración de acceso a métricas."
    )
    product_id: str = Field(..., description="ID del producto.")
    product_name: Optional[str] = Field(None, description="Nombre del producto.")
    created_at: Optional[datetime] = Field(None, description="Fecha de creación.")
    updated_at: Optional[datetime] = Field(
        None, description="Fecha de última actualización."
    )

    class Config:
        from_attributes = True


"""
    Gestion de acceso a tabla usuario
"""


class UserDataAccess(BaseModel):
    """
    Modelo base para representar un acceso de datos de usuario.
    """

    pass


class UserDataAccessByRole(BaseModel):
    """
    Representa un acceso de datos de usuario con información del rol.
    """

    user_data_access_id: str = Field(
        ..., description="ID del acceso de datos de usuario."
    )
    role_data_id: str = Field(..., description="ID del rol de acceso a datos.")
    role_name: Optional[str] = Field(None, description="Nombre del rol.")
    user_id: Optional[str] = Field(None, description="ID del usuario.")
    user_name: Optional[str] = Field(None, description="Username del usuario.")
    user_email: Optional[str] = Field(None, description="Email del usuario.")
    user_table_names: Optional[List[str]] = Field(
        None, description="Lista de nombres de tablas del usuario."
    )
    user_data_access: Optional[Dict[str, Any]] = Field(
        None, description="Configuración de acceso a datos del usuario."
    )
    user_metrics_access: Optional[List[str]] = Field(
        None, description="Configuración de acceso a métricas del usuario."
    )
    created_at: Optional[datetime] = Field(None, description="Fecha de creación.")
    updated_at: Optional[datetime] = Field(
        None, description="Fecha de última actualización."
    )

    class Config:
        from_attributes = True


class UserDataAccessByUser(BaseModel):
    """
    Representa un acceso de datos de usuario con información del usuario.
    """

    user_data_access_id: str = Field(
        ..., description="ID del acceso de datos de usuario."
    )
    role_data_id: str = Field(..., description="ID del rol de acceso a datos.")
    role_name: Optional[str] = Field(None, description="Nombre del rol.")
    user_id: str = Field(..., description="ID del usuario.")
    user_name: Optional[str] = Field(None, description="Username del usuario.")
    user_email: Optional[str] = Field(None, description="Email del usuario.")
    user_table_names: Optional[List[str]] = Field(
        None, description="Lista de nombres de tablas del usuario."
    )
    user_data_access: Optional[Dict[str, Any]] = Field(
        None, description="Configuración de acceso a datos del usuario."
    )
    user_metrics_access: Optional[List[str]] = Field(
        None, description="Configuración de acceso a métricas del usuario."
    )
    created_at: Optional[datetime] = Field(None, description="Fecha de creación.")
    updated_at: Optional[datetime] = Field(
        None, description="Fecha de última actualización."
    )

    class Config:
        from_attributes = True


class UserDataAccessRegisterRequest(BaseModel):
    """
    Datos necesarios para llamar a spu_minddash_app_insert_user_data_access.
    """

    # --- Parámetros OBLIGATORIOS ---
    role_data_id: str = Field(..., description="ID del rol de acceso a datos.")

    # --- Parámetros OPCIONALES ---
    user_id: Optional[str] = Field(None, description="ID del usuario.")
    table_names: Optional[List[str]] = Field(
        None, description="Lista de nombres de tablas."
    )
    data_access: Optional[Dict[str, Any]] = Field(
        None, description="Configuración de acceso a datos JSONB."
    )
    metrics_access: Optional[List[str]] = Field(
        None, description="Configuración de acceso a métricas JSONB."
    )

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "role_data_id": "a6f38618-4308-4dfc-83d7-4f98651649c1",
                "user_id": "b7f49729-5419-5efd-94e8-5g09762750d2",
                "table_names": ["users", "orders", "products", "analytics"],
                "metrics_access": None,
                "data_access": {
                    "facturacion_argentina.BU.in": ["BU CENTRO"],
                    "facturacion_argentina.es_fyv.in": ["no"],
                },
            }
        }


class UserDataAccessUpdateRequest(BaseModel):
    """
    Datos necesarios para llamar a spu_minddash_app_update_user_data_access.
    """

    # --- Parámetros de Identificación ---
    id: str = Field(
        ..., description="ID del acceso de datos de usuario que se va a actualizar."
    )
    role_data_id: str = Field(..., description="ID del rol de acceso a datos.")

    # --- Parámetros de Actualización ---
    user_id: Optional[str] = Field(None, description="ID del usuario.")
    table_names: Optional[List[str]] = Field(
        None, description="Lista de nombres de tablas."
    )
    data_access: Optional[Dict[str, Any]] = Field(
        None, description="Configuración de acceso a datos."
    )
    metrics_access: Optional[List[str]] = Field(
        None, description="Configuración de acceso a métricas."
    )

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "1ee67952-ef83-4038-ae9d-d95d2f16c32e",
                "role_data_id": "a6f38618-4308-4dfc-83d7-4f98651649c1",
                "user_id": "b7f49729-5419-5efd-94e8-5g09762750d2",
                "table_names": ["users", "orders", "products", "analytics"],
                "data_access": None,
                "metrics_access": ["user_count", "order_volume", "revenue"],
            }
        }


class UserDataAccessDeleteRequest(BaseModel):
    """
    Datos necesarios para llamar a spu_minddash_app_delete_user_data_access.
    Solo requiere el ID.
    """

    id: str = Field(
        ..., description="ID del acceso de datos de usuario que se va a eliminar."
    )

    class Config:
        from_attributes = True
        json_schema_extra = {"example": {"id": "1ee67952-ef83-4038-ae9d-d95d2f16c32e"}}


class GetUserDataAccessRequest(BaseModel):
    """
    Modelo para validar el cuerpo de la solicitud que puede contener un ID de acceso de datos de usuario opcional.
    Si no se proporciona ID, retorna todos los accesos.
    """

    user_data_access_id: Optional[str] = Field(
        None,
        description="ID del acceso de datos de usuario específico. Si no se proporciona, retorna todos los accesos.",
    )

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {"user_data_access_id": "1ee67952-ef83-4038-ae9d-d95d2f16c32e"}
        }


class GetUserDataAccessByRoleRequest(BaseModel):
    """
    Modelo para validar el cuerpo de la solicitud que contiene el ID del rol de acceso a datos.
    """

    role_data_id: str = Field(
        ...,
        description="ID del rol de acceso a datos para el cual se buscan los accesos de usuarios.",
    )

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {"role_data_id": "a6f38618-4308-4dfc-83d7-4f98651649c1"}
        }


class GetUserDataAccessByUserRequest(BaseModel):
    """
    Modelo para validar el cuerpo de la solicitud que contiene el ID del usuario.
    """

    user_id: str = Field(
        ..., description="ID del usuario para el cual se buscan los accesos de datos."
    )

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {"user_id": "b7f49729-5419-5efd-94e8-5g09762750d2"}
        }


class UserDataAccessCreationResponse(BaseModel):
    """
    Respuesta al crear un nuevo acceso de datos de usuario.
    """

    id_user_data_access: str = Field(
        ..., description="ID del acceso de datos de usuario creado."
    )


class UserDataAccessUpdateResponse(BaseModel):
    """
    Respuesta al actualizar un acceso de datos de usuario.
    """

    message: str = Field(
        "Acceso de datos de usuario actualizado exitosamente.",
        description="Mensaje de confirmación.",
    )
    user_data_access_id: str = Field(
        ..., description="ID del acceso de datos de usuario actualizado."
    )


class UserDataAccessDeleteResponse(BaseModel):
    """
    Respuesta al eliminar un acceso de datos de usuario.
    """

    message: str = Field(
        "Acceso de datos de usuario eliminado exitosamente.",
        description="Mensaje de confirmación.",
    )
    user_data_access_id: str = Field(
        ..., description="ID del acceso de datos de usuario eliminado."
    )


class UserDataAccessResponse(BaseModel):
    """
    Respuesta para un acceso de datos de usuario individual.
    """

    user_data_access_id: str = Field(
        ..., description="ID del acceso de datos de usuario."
    )
    role_data_id: str = Field(..., description="ID del rol de acceso a datos.")
    role_name: Optional[str] = Field(None, description="Nombre del rol.")
    user_id: Optional[str] = Field(None, description="ID del usuario.")
    user_name: Optional[str] = Field(None, description="Username del usuario.")
    user_email: Optional[str] = Field(None, description="Email del usuario.")
    user_table_names: Optional[List[str]] = Field(
        None, description="Lista de nombres de tablas del usuario."
    )
    user_data_access: Optional[Dict[str, Any]] = Field(
        None, description="Configuración de acceso a datos del usuario."
    )
    user_metrics_access: Optional[List[str]] = Field(
        None, description="Configuración de acceso a métricas del usuario."
    )
    created_at: Optional[datetime] = Field(None, description="Fecha de creación.")
    updated_at: Optional[datetime] = Field(
        None, description="Fecha de última actualización."
    )

    class Config:
        from_attributes = True


"""
    Actualizacion del deplo de agente
"""


# --- Modelo Base de Datos ---
class ClientDeployData(BaseModel):
    """Modelo para representar un registro de clients_products_deploys."""

    id: str = Field(..., description="str del registro de despliegue.")
    product_id: str = Field(..., description="str del producto asociado.")
    bucket_config: Optional[str] = Field(
        None, description="Ruta/Bucket de la configuración principal."
    )
    gs_examples_agent: Optional[str] = Field(
        None, description="Ruta del Google Storage para ejemplos del agente."
    )
    gs_prompt_agent: Optional[str] = Field(
        None, description="Ruta del Google Storage para prompt del agente."
    )
    gs_prompt_sql: Optional[str] = Field(
        None, description="Ruta del Google Storage para prompt SQL."
    )
    gs_profiling_agent: Optional[str] = Field(
        None, description="Ruta del Google Storage para profiling del agente."
    )
    gs_metrics_config_agent: Optional[str] = Field(
        None, description="Ruta del Google Storage para configuración de métricas."
    )
    client: Optional[str] = Field(
        None, description="Nombre o ID del cliente (campo 'client')."
    )
    created_at: datetime = Field(..., description="Fecha de creación.")
    updated_at: datetime = Field(..., description="Fecha de última actualización.")

    class Config:
        from_attributes = True


# --- Modelos de Request (CRUD) ---


class ClientDeployRegisterRequest(BaseModel):
    """Datos necesarios para la inserción/Update."""

    product_id: str = Field(..., description="ID del producto.")
    bucket_config: Optional[str] = None
    gs_semantic_config: Optional[str] = None
    gs_examples_agent: Optional[str] = None
    gs_prompt_agent: Optional[str] = None
    gs_prompt_sql: Optional[str] = None
    gs_profiling_agent: Optional[str] = None
    gs_metrics_config_agent: Optional[str] = None
    client: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "product_id": "a6f38618-4308-4dfc-83d7-4f98651649c1",
                "bucket_config": "deploy-config-s3/prod",
                "gs_examples_agent": "gs://mindash-agents/v3/examples_kmd",
                "gs_prompt_agent": "gs://mindash-agents/v3/prompt_kmd",
                "gs_prompt_sql": "gs://mindash-agents/v3/prompt_sql_kmd",
                "gs_profiling_agent": "gs://mindash-agents/v3/profiling_kmd",
                "gs_metrics_config_agent": "gs://mindash-agents/v3/metrics_kmd",
                "client": "KM Dev",
            }
        }


class ClientDeployUpdateRequest(ClientDeployRegisterRequest):
    """Datos necesarios para la actualización."""

    id: str = Field(..., description="ID del registro a actualizar.")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "1ee67952-ef83-4038-ae9d-d95d2f16c32e",
                "product_id": "a6f38618-4308-4dfc-83d7-4f98651649c1",
                "bucket_config": "deploy-config-s3/staging",  # Valor actualizado
                "gs_examples_agent": "gs://mindash-agents/v3/examples_kmd",
                "gs_prompt_agent": "gs://mindash-agents/v3/prompt_kmd",
                "gs_prompt_sql": "gs://mindash-agents/v3/prompt_sql_kmd",
                "gs_profiling_agent": "gs://mindash-agents/v3/profiling_kmd",
                "gs_metrics_config_agent": "gs://mindash-agents/v3/metrics_kmd",
                "client": "KM Dev (Staging)",
            }
        }


class ClientDeployDeleteRequest(BaseModel):
    """Datos necesarios para la eliminación."""

    id: str = Field(..., description="ID del registro a eliminar.")

    class Config:
        json_schema_extra = {"example": {"id": "1ee67952-ef83-4038-ae9d-d95d2f16c32e"}}


# --- Modelos de Request (Consulta) ---


class GetClientDeployRequest(BaseModel):
    """Obtiene todos los registros o uno específico por ID."""

    deploy_id: Optional[str] = Field(
        None, description="ID del registro de despliegue. Si es None, retorna todos."
    )

    class Config:
        json_schema_extra = {
            "example": {
                "deploy_id": "1ee67952-ef83-4038-ae9d-d95d2f16c32e"  # Ejemplo para buscar un ID específico
            }
        }


class GetClientDeployByProductRequest(BaseModel):
    """Obtiene registros filtrados por product_id."""

    product_id: str = Field(..., description="ID del producto para filtrar.")

    class Config:
        json_schema_extra = {
            "example": {"product_id": "a6f38618-4308-4dfc-83d7-4f98651649c1"}
        }


# --- Modelos de Response ---


class ClientDeployCreationResponse(BaseModel):
    id_deploy: str = Field(
        ..., description="ID del nuevo registro de despliegue creado."
    )


class ClientDeployUpdateResponse(BaseModel):
    message: str = "Registro de despliegue actualizado exitosamente."
    deploy_id: str = Field(..., description="ID del registro actualizado.")


class ClientDeployDeleteResponse(BaseModel):
    message: str = "Registro de despliegue eliminado exitosamente."
    deploy_id: str = Field(..., description="ID del registro eliminado.")


class ClientDeploySingleResponse(BaseModel):
    deploy: ClientDeployData


class ClientDeployListResponse(BaseModel):
    deploys: List[ClientDeployData]
