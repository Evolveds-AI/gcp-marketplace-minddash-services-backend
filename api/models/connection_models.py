from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class DataConnection(BaseModel):
    """
    Modelo base para representar una conexión de datos.
    """

    pass


class DataConnectionByOrganization(BaseModel):
    """
    Representa una conexión de datos con información de la organización.
    """

    connection_id: str = Field(..., description="ID de la conexión.")
    connection_name: str = Field(..., description="Nombre de la conexión.")
    connection_type: str = Field(..., description="Tipo de conexión.")
    connection_configuration: Optional[Dict[str, Any]] = Field(
        None, description="Configuración de la conexión."
    )
    organization_id: Optional[str] = Field(None, description="ID de la organización.")
    organization_name: Optional[str] = Field(
        None, description="Nombre de la organización."
    )
    organization_company_name: Optional[str] = Field(
        None, description="Nombre de la empresa."
    )
    organization_country: Optional[str] = Field(
        None, description="País de la organización."
    )

    class Config:
        from_attributes = True


class DataConnectionRegisterRequest(BaseModel):
    """
    Datos necesarios para llamar a spu_minddash_app_insert_data_connection.
    """

    # --- Parámetros OBLIGATORIOS ---
    organization_id: str = Field(
        ..., description="ID de la organización a la que pertenece la conexión."
    )
    name: str = Field(..., description="Nombre de la conexión.")
    type: str = Field(
        ..., description="Tipo de conexión (ej: 'postgresql', 'mysql', 'mongodb')."
    )
    configuration: Dict[str, Any] = Field(
        ..., description="Configuración JSONB de la conexión."
    )

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "organization_id": "a6f38618-4308-4dfc-83d7-4f98651649c1",
                "name": "Conexión PostgreSQL Principal",
                "type": "postgresql",
                "configuration": {
                    "host": "localhost",
                    "port": 5432,
                    "database": "minddash_db",
                    "username": "admin",
                    "password": "secret123",
                    "ssl_mode": "require",
                },
            }
        }


class DataConnectionUpdateRequest(BaseModel):
    """
    Datos necesarios para llamar a spu_minddash_app_update_data_connection.
    """

    # --- Parámetros de Identificación ---
    id: str = Field(..., description="ID de la conexión que se va a actualizar.")
    organization_id: str = Field(..., description="ID de la organización.")

    # --- Parámetros de Actualización ---
    name: str = Field(..., description="Nuevo nombre de la conexión.")
    type: str = Field(..., description="Nuevo tipo de conexión.")
    configuration: Dict[str, Any] = Field(..., description="Nueva configuración JSONB.")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "1ee67952-ef83-4038-ae9d-d95d2f16c32e",
                "organization_id": "a6f38618-4308-4dfc-83d7-4f98651649c1",
                "name": "Conexión PostgreSQL Actualizada",
                "type": "postgresql",
                "configuration": {
                    "host": "new-host.example.com",
                    "port": 5432,
                    "database": "updated_db",
                    "username": "new_admin",
                    "password": "new_secret123",
                    "ssl_mode": "prefer",
                },
            }
        }


class DataConnectionCreationResponse(BaseModel):
    """
    Respuesta al crear una nueva conexión de datos.
    """

    id_connection: str = Field(..., description="ID de la conexión creada.")


class DataConnectionUpdateResponse(BaseModel):
    """
    Respuesta al actualizar una conexión de datos.
    """

    message: str = Field(
        "Conexión actualizada exitosamente.", description="Mensaje de confirmación."
    )
    connection_id: str = Field(..., description="ID de la conexión actualizada.")


class DataConnectionDeleteRequest(BaseModel):
    """
    Datos necesarios para llamar a spu_minddash_app_delete_data_connection.
    Solo requiere el ID.
    """

    id: str = Field(..., description="ID de la conexión que se va a eliminar.")

    class Config:
        from_attributes = True
        json_schema_extra = {"example": {"id": "1ee67952-ef83-4038-ae9d-d95d2f16c32e"}}


class DataConnectionDeleteResponse(BaseModel):
    """
    Respuesta al eliminar una conexión de datos.
    """

    message: str = Field(
        "Conexión eliminada exitosamente.", description="Mensaje de confirmación."
    )
    connection_id: str = Field(..., description="ID de la conexión eliminada.")


class GetDataConnectionsByOrganizationRequest(BaseModel):
    """
    Modelo para validar el cuerpo de la solicitud que contiene el ID de organización.
    """

    organization_id: str = Field(
        ..., description="ID de la organización para la cual se buscan las conexiones."
    )


class GetDataConnectionsRequest(BaseModel):
    """
    Modelo para validar el cuerpo de la solicitud que puede contener un ID de conexión opcional.
    Si no se proporciona ID, retorna todas las conexiones.
    """

    connection_id: Optional[str] = Field(
        None,
        description="ID de la conexión específica. Si no se proporciona, retorna todas las conexiones.",
    )

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {"connection_id": "1ee67952-ef83-4038-ae9d-d95d2f16c32e"}
        }


class DataConnectionResponse(BaseModel):
    """
    Respuesta para una conexión de datos individual.
    """

    connection_id: str = Field(..., description="ID de la conexión.")
    connection_name: str = Field(..., description="Nombre de la conexión.")
    connection_type: str = Field(..., description="Tipo de conexión.")
    connection_configuration: Optional[Dict[str, Any]] = Field(
        None, description="Configuración de la conexión."
    )
    organization_id: Optional[str] = Field(None, description="ID de la organización.")
    organization_name: Optional[str] = Field(
        None, description="Nombre de la organización."
    )
    organization_company_name: Optional[str] = Field(
        None, description="Nombre de la empresa."
    )
    organization_country: Optional[str] = Field(
        None, description="País de la organización."
    )

    class Config:
        from_attributes = True
