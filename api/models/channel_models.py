from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

# --- Modelos de Solicitud (Request) - Creacion de Canales  ---


class ChannelRegisterRequest(BaseModel):
    """
    Datos para la creación de un nuevo canal.
    """

    name: str = Field(
        ..., max_length=100, description="Nombre del canal (ej: 'WhatsApp', 'Web')."
    )
    description: Optional[str] = Field(
        None, max_length=100, description="Descripción del canal."
    )

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Canal de Telegram",
                "description": "El canal oficial de atención vía Telegram.",
            }
        }


class ChannelUpdateRequest(BaseModel):
    """
    Datos para la actualización de un canal existente.
    """

    id: str = Field(..., description="ID del canal que se va a actualizar.")
    name: str = Field(..., max_length=100, description="Nuevo nombre del canal.")
    description: Optional[str] = Field(
        None, max_length=100, description="Nueva descripción del canal."
    )

    class Config:
        json_schema_extra = {
            "example": {
                "id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
                "name": "Canal de Telegram Oficial",
                "description": "El canal de atención vía Telegram v2.0.",
            }
        }


class ChannelDeleteRequest(BaseModel):
    """
    Datos para la eliminación de un canal.
    """

    id: str = Field(..., description="ID del canal que se va a eliminar.")

    class Config:
        json_schema_extra = {"example": {"id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d"}}


# --- Modelos de Respuesta (Response) - Creacion de Canales ---


class ChannelCreationResponse(BaseModel):
    id_channel: str = Field(..., description="El ID (str) del canal recién creado.")


class ChannelUpdateResponse(BaseModel):
    message: str = Field(
        "Canal actualizado exitosamente.", description="Mensaje de confirmación."
    )
    channel_id: str = Field(..., description="ID del canal actualizado.")


class ChannelDeleteResponse(BaseModel):
    message: str = Field(
        "Canal eliminado exitosamente.", description="Mensaje de confirmación."
    )
    channel_id: str = Field(..., description="ID del canal eliminado.")


# --- Modelos de Solicitud (Request) - Creacion de Canales/Producto     ---


class ChannelProductRegisterRequest(BaseModel):
    """
    Datos necesarios para crear una nueva relación.
    """

    channel_id: str = Field(..., description="ID del Canal.")
    product_id: str = Field(..., description="ID del Producto.")

    # --- CAMPO NUEVO ---
    channel_product_type: Optional[str] = Field(
        None,
        max_length=100,
        description="Tipo de la relación (ej: 'prod', 'test', 'dev').",
    )

    configuration: Optional[Dict[str, Any]] = Field(
        default_factory=lambda: {}, description="Configuración JSONB específica."
    )

    class Config:
        json_schema_extra = {
            "example": {
                "channel_id": "a6f38618-4308-4dfc-83d7-4f98651649c1",
                "product_id": "1ee67952-ef83-4038-ae9d-d95d2f16c32e",
                "channel_product_type": "prod",  # NUEVO
                "configuration": {"deployment_name": "channel_prod_v1"},
            }
        }


class ChannelProductUpdateRequest(BaseModel):
    """
    Datos para la actualización de una relación.
    """

    id: str = Field(..., description="ID principal del registro de relación.")
    channel_id: str = Field(..., description="Nuevo ID del Canal.")
    product_id: str = Field(..., description="Nuevo ID del Producto.")

    # --- CAMPO NUEVO ---
    channel_product_type: Optional[str] = Field(
        None, max_length=100, description="Nuevo tipo de la relación."
    )

    configuration: Optional[Dict[str, Any]] = Field(
        default_factory=lambda: {}, description="Nueva configuración JSONB."
    )

    class Config:
        json_schema_extra = {
            "example": {
                "id": "b1c2d3e4-f5g6-7h8i-9j0k-1l2m3n4o5p6q",
                "channel_id": "a6f38618-4308-4dfc-83d7-4f98651649c1",
                "product_id": "1ee67952-ef83-4038-ae9d-d95d2f16c32e",
                "channel_product_type": "test",  # NUEVO
                "configuration": {"deployment_name": "channel_prod_v2"},
            }
        }


class ChannelProductDeleteRequest(BaseModel):
    """
    Datos para la eliminación de una relación Canal-Producto.
    """

    id: str = Field(
        ...,
        description="ID principal del registro de relación (channel_product) que se va a eliminar.",
    )

    class Config:
        json_schema_extra = {"example": {"id": "b1c2d3e4-f5g6-7h8i-9j0k-1l2m3n4o5p6q"}}


# --- Modelos de Respuesta (Response) - Creacion de Canales/Producto    ---


class ChannelProductCreationResponse(BaseModel):
    id_channel_product: str = Field(
        ..., description="El ID (str) de la relación recién creada."
    )
    url_webhook_channel: str = Field(
        ..., description="El url webhook generado para la comunicacion."
    )


class ChannelProductUpdateResponse(BaseModel):
    message: str = Field(
        "Relación Canal-Producto actualizada exitosamente.",
        description="Mensaje de confirmación.",
    )
    channel_product_id: str = Field(..., description="ID de la relación actualizada.")

    url_webhook_channel: str = Field(
        ..., description="El url webhook generado para la comunicacion."
    )


class ChannelProductDeleteResponse(BaseModel):
    message: str = Field(
        "Relación Canal-Producto eliminada exitosamente.",
        description="Mensaje de confirmación.",
    )
    channel_product_id: str = Field(..., description="ID de la relación eliminada.")
