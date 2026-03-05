from __future__ import annotations

import logging
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

logger = logging.getLogger(__name__)


class Organization(BaseModel):
    # --- Datos de la Organización (Mapeados desde la vista) ---

    # La view no devuelve 'nombre', sino 'organization_name'
    nombre: str = Field(
        ...,
        alias="organization_name",
        description="Nombre corto/comercial de la organización.",
    )
    # La view no devuelve 'company_name', sino 'organization_company_name'
    company_name: str = Field(
        ...,
        alias="organization_company_name",
        description="Nombre legal de la compañía.",
    )
    # La view no devuelve 'country', sino 'organization_country'
    country: str = Field(
        ..., alias="organization_country", description="País de la organización."
    )
    # --- Datos del Usuario/Acceso (Mapeados desde la vista) ---
    user_id: str = Field(..., description="ID del usuario asociado al acceso.")
    user_role_name: str = Field(
        ..., description="Rol del usuario en esta organización."
    )
    user_name: str = Field(..., description="Nombre completo del usuario.")
    user_phone: Optional[str] = Field(None, description="Teléfono del usuario.")
    user_email: EmailStr = Field(..., description="Correo del usuario.")
    organization_id: str = Field(..., description="UUID del registro de organización.")
    # Campos de tiempo que suelen faltar o están bajo otros nombres
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        # Habilita el mapeo de campos por sus nombres en la DB (aliases)
        from_attributes = True


class OrganizationRegisterRequest(BaseModel):
    """
    Modelo para la entrada de datos al registrar una nueva organización.
    Corresponde a los parámetros de entrada del store procedure.
    """

    name: str = Field(
        ..., max_length=50, description="Nombre corto o comercial de la organización."
    )
    company_name: str = Field(
        ..., max_length=100, description="Nombre legal o razón social de la compañía."
    )
    description: str = Field(
        ..., max_length=200, description="Descripción de la organización."
    )
    country: str = Field(..., max_length=25, description="País de la organización.")


class OrganizationUpdateRequest(BaseModel):
    """
    Modelo para la entrada de datos al actualizar una organización existente.
    """

    id: str = Field(..., description="UUID de la organización a actualizar.")
    name: str = Field(
        ..., max_length=50, description="Nombre corto o comercial de la organización."
    )
    company_name: str = Field(
        ..., max_length=100, description="Nombre legal o razón social de la compañía."
    )
    description: str = Field(
        ..., max_length=200, description="Descripción de la organización."
    )
    country: str = Field(..., max_length=25, description="País de la organización.")


class OrganizationByUser(BaseModel):
    """
    Representa una tupla de acceso a una Organización para un usuario específico
    """

    user_id: str = Field(..., description="UUID del usuario.")
    user_name: str = Field(..., description="Nombre completo del usuario.")
    user_phone: Optional[str] = Field(
        None, description="Número de teléfono del usuario (puede ser opcional)."
    )
    user_email: EmailStr = Field(..., description="Correo electrónico del usuario.")
    user_role_name: str = Field(
        ...,
        description="Nombre del rol más efectivo del usuario en esta organización (ej. 'SuperAdmin', 'Administrador').",
    )
    organization_id: str = Field(
        ..., description="UUID de la organización a la que el usuario tiene acceso."
    )
    organization_name: str = Field(
        ..., description="Nombre corto o comercial de la organización."
    )
    organization_company_name: str = Field(
        ..., description="Nombre legal o razón social de la compañía."
    )
    organization_country: str = Field(..., description="País de la organización.")

    class Config:
        # Permite que la clase acepte objetos ORM/SQLAlchemy/PostgreSQL
        from_attributes = True


class GetOrganizationRequestByOrg(BaseModel):
    """
    Modelo para validar el cuerpo de la solicitud que contiene el ID de usuario.
    """

    user_id: str = Field(
        ..., description="UUID del usuario para el cual se buscan las organizaciones."
    )
    organization_id: str = Field(
        ..., description="UUID de la organizacion para el cual se buscan."
    )


class GetOrganizationRequest(BaseModel):
    """
    Modelo para validar el cuerpo de la solicitud que contiene el ID de usuario.
    """

    user_id: str = Field(
        ..., description="UUID del usuario para el cual se buscan las organizaciones."
    )


class OrganizationDeleteRequest(BaseModel):
    """
    Modelo para la entrada de datos al eliminar una organización.
    Solo requiere el ID.
    """

    id: str = Field(..., description="UUID de la organización a eliminar.")


class OrganizationCreationResponse(BaseModel):
    id_organization: str


class OrganizationUpdateResponse(BaseModel):
    message: str = Field(
        "Organización actualizada exitosamente.", description="Mensaje de confirmación."
    )
    organization_id: str = Field(
        ..., description="UUID de la organización actualizada."
    )


class OrganizationDeleteResponse(BaseModel):
    message: str = Field(
        "Organización eliminada exitosamente.", description="Mensaje de confirmación."
    )
    organization_id: str = Field(..., description="UUID de la organización eliminada.")


"""
    Bloque para control de accesos de organizacion:
"""


class OrganizationRegisterAccessRequest(BaseModel):
    """
    Modelo para la entrada de datos al registrar un nuevo acceso (INSERT).
    Corresponde a los parámetros del SP: user_id, organization_id, role_id.
    """

    user_id: str = Field(..., description="UUID del usuario al que se le da acceso.")
    organization_id: str = Field(
        ..., description="UUID de la organización a la que se da acceso."
    )
    role_id: str = Field(
        ..., description="UUID del rol que se asigna en esa organización."
    )


class OrganizationUpdateAccessRequest(BaseModel):
    """
    Modelo para la entrada de datos al actualizar un registro de acceso existente (UPDATE).
    Corresponde a los parámetros del SP: id, user_id, organization_id, role_id.
    """

    id: str = Field(
        ...,
        description="UUID del registro de acceso a actualizar (access_user_organization.id).",
    )
    user_id: str = Field(
        ..., description="Nuevo UUID del usuario (generalmente el mismo)."
    )
    organization_id: str = Field(
        ..., description="Nuevo UUID de la organización (generalmente el mismo)."
    )
    role_id: str = Field(..., description="Nuevo UUID del rol que se asigna.")


class OrganizationDeleteAccessRequest(BaseModel):
    """
    Modelo para la entrada de datos al eliminar un registro de acceso (DELETE).
    Solo requiere el ID del registro de acceso.
    """

    id: str = Field(
        ...,
        description="UUID del registro de acceso a eliminar (access_user_organization.id).",
    )


class OrganizationCreationAccessResponse(BaseModel):
    """Respuesta para el registro exitoso."""

    organization_access_id: str = Field(
        ..., description="UUID del nuevo registro de acceso creado."
    )


class OrganizationAccessResponse(BaseModel):
    message: str = "Acceso a organización registrado exitosamente."
    organization_access_id: str


class OrganizationUpdateAccessResponse(BaseModel):
    """Respuesta para la actualización exitosa."""

    message: str = "Acceso a organización actualizado exitosamente."
    organization_access_id: str = Field(
        ..., description="UUID del registro de acceso actualizado."
    )


class OrganizationDeleteAccessResponse(BaseModel):
    """Respuesta para la eliminación exitosa."""

    message: str = "Acceso a organización eliminado exitosamente."
    organization_access_id: str = Field(
        ..., description="UUID del registro de acceso eliminado."
    )
