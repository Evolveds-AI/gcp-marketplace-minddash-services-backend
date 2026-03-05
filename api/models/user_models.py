from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

logger = logging.getLogger(__name__)


class GetUserRequest(BaseModel):
    """
    Modelo para validar el cuerpo de la solicitud que contiene el ID de usuario.
    """

    user_id: str = Field(
        ..., description="str del usuario para el cual se buscan las organizaciones."
    )


class UserBaseInfoResponse(BaseModel):
    """
    Mapea todos los campos del view_info_user_details (datos de usuario + rol base).
    """

    # --- Datos del Usuario (Users table) ---
    user_id: str = Field(..., description="UUID del usuario.")
    username: str = Field(..., description="Nombre de usuario.")
    user_email: EmailStr = Field(
        ..., alias="email", description="Correo electrónico del usuario."
    )

    # Datos de seguridad y estado
    password_hash: str = Field(
        ..., description="Hash de la contraseña (NO debe exponerse en el API final)."
    )
    email_verified: bool = Field(
        ..., description="Indica si el correo ha sido verificado."
    )
    is_active: bool = Field(..., description="Estado de actividad de la cuenta.")
    failed_attempts: int = Field(
        ..., description="Número de intentos de login fallidos."
    )
    locked_until: Optional[datetime] = Field(
        None, description="Momento hasta el cual la cuenta está bloqueada."
    )
    created_at: datetime = Field(..., description="Fecha de creación del registro.")
    updated_at: Optional[datetime] = Field(
        None, description="Última fecha de actualización del registro."
    )

    # Datos específicos de la aplicación
    primary_chatbot_id: Optional[str] = Field(
        None, description="ID del chatbot principal asociado al usuario."
    )
    can_manage_users: bool = Field(
        ...,
        description="Indica si el usuario tiene permiso para gestionar otros usuarios.",
    )
    phone_number: Optional[str] = Field(
        None, description="Número de teléfono del usuario."
    )
    is_active_whatsapp: bool = Field(
        ..., description="Estado de actividad de WhatsApp."
    )
    role_acceso_data_id: Optional[str] = Field(
        None, description="ID del rol específico para acceso a datos."
    )  # Asumiendo que es UUID

    # --- Datos del Rol (Roles table) ---
    role_id: str = Field(..., description="UUID del rol base del usuario.")
    role_name: str = Field(..., description="Nombre del rol base (ej. 'Admin').")
    role_type: Optional[str] = Field(
        None,
        description="Tipo o clasificación del rol (ej. 'Administrador del servicio').",
    )
    role_description: Optional[str] = Field(
        None, description="Descripción de las funciones del rol."
    )

    class Config:
        from_attributes = True
