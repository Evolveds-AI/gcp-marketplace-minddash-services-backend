from __future__ import annotations

import logging
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

logger = logging.getLogger(__name__)


class Project(BaseModel):
    """
    Representa una tupla de acceso a un Proyecto para un usuario específico,
    incluyendo la jerarquía superior (Organización).
    """

    # --- Datos del Usuario ---
    user_id: str = Field(..., description="str del usuario.")
    user_role_name: str = Field(
        ...,
        description="Nombre del rol más efectivo del usuario en la jerarquía (ej. 'SuperAdmin').",
    )
    user_name: str = Field(..., description="Nombre completo del usuario.")
    user_phone: Optional[str] = Field(
        None, description="Número de teléfono del usuario."
    )
    user_email: EmailStr = Field(..., description="Correo electrónico del usuario.")

    # --- Datos de la Organización (Padre) ---
    organization_id: str = Field(
        ..., description="str de la Proyecto a la que pertenece el proyecto."
    )
    organization_name: str = Field(..., description="Nombre de la Proyecto.")

    # --- Datos del Proyecto ---
    project_id: str = Field(..., description="str del proyecto.")
    project_name: str = Field(..., description="Nombre del proyecto.")
    project_label: Optional[str] = Field(None, description="Etiqueta del proyecto.")
    project_label_color: Optional[str] = Field(
        None, description="Color de la etiqueta del proyecto (ej. #2ecc71)."
    )
    project_description: Optional[str] = Field(
        None, description="Descripción del proyecto."
    )

    class Config:
        from_attributes = True


# class Project(BaseModel):
#     id: str
#     project_id: str
#     nombre: str
#     label: str
#     label_color: str
#     description: str
#     created_at: Optional[str] = None
#     updated_at: Optional[str] = None


# --- Modelo para la respuesta de la vista de Proyectos por Usuario ---
class ProjectRegisterRequest(BaseModel):
    """
    Datos necesarios para llamar a spu_minddash_app_insert_project.
    """

    organization_id: str = Field(
        ..., description="ID de la organización a la que pertenece el proyecto."
    )
    name: str = Field(
        ..., max_length=50, description="Nombre del proyecto (máx. 50 caracteres)."
    )
    label: Optional[str] = Field(
        None,
        max_length=50,
        description="Etiqueta corta del proyecto (ej: 'ALFA-2025').",
    )
    label_color: Optional[str] = Field(
        None,
        max_length=20,
        description="Código de color para la etiqueta (ej: '#007bff').",
    )
    description: Optional[str] = Field(
        None,
        max_length=200,
        description="Descripción detallada del proyecto (máx. 200 caracteres).",
    )

    class Config:
        # Permite la carga de datos de ORM (útil si se usa un ORM para inicializar)
        from_attributes = True
        # Añade un ejemplo para la documentación de FastAPI/Swagger
        json_schema_extra = {
            "example": {
                "organization_id": "e7c77bdf-8f8e-438c-b038-5ea9253e0ad7",
                "name": "Proyecto Neptuno",
                "label": "NEP-2026",
                "label_color": "#ffc107",
                "description": "Desarrollo de la fase inicial de la plataforma de datos.",
            }
        }


class ProjectUpdateRequest(BaseModel):
    """
    Datos necesarios para llamar a spu_minddash_app_update_project.
    Todos los campos son obligatorios para la actualización completa.
    """

    id: str = Field(..., description="ID del proyecto que se va a actualizar.")
    organization_id: str = Field(
        ..., description="ID de la organización (puede ser el mismo o uno nuevo)."
    )
    name: str = Field(..., max_length=50, description="Nuevo nombre del proyecto.")
    label: Optional[str] = Field(
        None, max_length=50, description="Nueva etiqueta del proyecto."
    )
    label_color: Optional[str] = Field(
        None, max_length=20, description="Nuevo código de color."
    )
    description: Optional[str] = Field(
        None, max_length=200, description="Nueva descripción del proyecto."
    )

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "46c1189b-0670-47db-b764-5b5df74d0ace",
                "organization_id": "e7c77bdf-8f8e-438c-b038-5ea9253e0ad7",
                "name": "Proyecto Neptuno (Fase Beta)",
                "label": "NEP-BETA",
                "label_color": "#17a2b8",
                "description": "Se actualizó la descripción para reflejar el inicio de la fase beta.",
            }
        }


class GetProjectRequest(BaseModel):
    """
    Modelo para validar el cuerpo de la solicitud que contiene el ID de usuario.
    """

    user_id: str = Field(
        ..., description="str del usuario para el cual se buscan las organizaciones."
    )


class ProjectDeleteRequest(BaseModel):
    """
    Datos necesarios para llamar a spu_minddash_app_delete_project.
    Solo requiere el ID.
    """

    id: str = Field(..., description="ID del proyecto que se va a eliminar.")

    class Config:
        from_attributes = True
        json_schema_extra = {"example": {"id": "46c1189b-0670-47db-b764-5b5df74d0ace"}}


class ProjectCreationResponse(BaseModel):
    id_project: str


class ProjectUpdateResponse(BaseModel):
    message: str = Field(
        "Organización actualizada exitosamente.", description="Mensaje de confirmación."
    )
    project_id: str = Field(..., description="str de la Proyecto actualizada.")


class ProjectDeleteResponse(BaseModel):
    message: str = Field(
        "Organización eliminada exitosamente.", description="Mensaje de confirmación."
    )
    project_id: str = Field(..., description="str de la Proyecto eliminada.")


class ProjectByUser(BaseModel):
    """
    Representa una tupla de acceso a un Proyecto para un usuario específico,
    incluyendo la jerarquía superior (Organización).
    """

    # --- Datos del Usuario ---
    user_id: str = Field(..., description="str del usuario.")
    user_role_name: str = Field(
        ...,
        description="Nombre del rol más efectivo del usuario en la jerarquía (ej. 'SuperAdmin').",
    )
    user_name: str = Field(..., description="Nombre completo del usuario.")
    user_phone: Optional[str] = Field(
        None, description="Número de teléfono del usuario."
    )
    user_email: EmailStr = Field(..., description="Correo electrónico del usuario.")

    # --- Datos de la Organización (Padre) ---
    organization_id: str = Field(
        ..., description="str de la Proyecto a la que pertenece el proyecto."
    )
    organization_name: str = Field(..., description="Nombre de la Proyecto.")

    # --- Datos del Proyecto ---
    project_id: str = Field(..., description="str del proyecto.")
    project_name: str = Field(..., description="Nombre del proyecto.")
    project_label: Optional[str] = Field(None, description="Etiqueta del proyecto.")
    project_label_color: Optional[str] = Field(
        None, description="Color de la etiqueta del proyecto (ej. #2ecc71)."
    )
    project_description: Optional[str] = Field(
        None, description="Descripción del proyecto."
    )

    class Config:
        from_attributes = True


"""
    Bloque para control de accesos de organizacion:
"""


class ProjectRegisterAccessRequest(BaseModel):
    """
    Modelo para la entrada de datos al registrar un nuevo acceso (INSERT).
    Corresponde a los parámetros del SP: user_id, project_id, role_id.
    """

    user_id: str = Field(..., description="UUID del usuario al que se le da acceso.")
    project_id: str = Field(
        ..., description="UUID de la organización a la que se da acceso."
    )
    role_id: str = Field(
        ..., description="UUID del rol que se asigna en esa organización."
    )


class ProjectUpdateAccessRequest(BaseModel):
    """
    Modelo para la entrada de datos al actualizar un registro de acceso existente (UPDATE).
    Corresponde a los parámetros del SP: id, user_id, project_id, role_id.
    """

    id: str = Field(
        ...,
        description="UUID del registro de acceso a actualizar (access_user_project.id).",
    )
    user_id: str = Field(
        ..., description="Nuevo UUID del usuario (generalmente el mismo)."
    )
    project_id: str = Field(
        ..., description="Nuevo UUID de la organización (generalmente el mismo)."
    )
    role_id: str = Field(..., description="Nuevo UUID del rol que se asigna.")


class ProjectDeleteAccessRequest(BaseModel):
    """
    Modelo para la entrada de datos al eliminar un registro de acceso (DELETE).
    Solo requiere el ID del registro de acceso.
    """

    id: str = Field(
        ...,
        description="UUID del registro de acceso a eliminar (access_user_project.id).",
    )


class ProjectCreationAccessResponse(BaseModel):
    """Respuesta para el registro exitoso."""

    project_access_id: str = Field(
        ..., description="UUID del nuevo registro de acceso creado."
    )


class ProjectAccessResponse(BaseModel):
    message: str = "Acceso a organización registrado exitosamente."
    project_access_id: str


class ProjectUpdateAccessResponse(BaseModel):
    """Respuesta para la actualización exitosa."""

    message: str = "Acceso a organización actualizado exitosamente."
    project_access_id: str = Field(
        ..., description="UUID del registro de acceso actualizado."
    )


class ProjectDeleteAccessResponse(BaseModel):
    """Respuesta para la eliminación exitosa."""

    message: str = "Acceso a organización eliminado exitosamente."
    project_access_id: str = Field(
        ..., description="UUID del registro de acceso eliminado."
    )
