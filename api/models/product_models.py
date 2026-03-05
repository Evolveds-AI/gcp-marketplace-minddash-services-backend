from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, EmailStr, Field, conint


class Product(BaseModel):
    """
    Representa una tupla de acceso a un Producto para un usuario específico,
    incluyendo la jerarquía superior (Producto y Producto).
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
    organization_id: str = Field(
        ..., description="str de la producto a la que pertenece el proyecto."
    )
    organization_name: str = Field(..., description="Nombre de la producto.")
    project_id: str = Field(..., description="str del proyecto.")
    project_name: str = Field(..., description="Nombre del proyecto.")

    # --- Datos del Producto ---
    product_id: str = Field(..., description="str del producto.")
    product_name: str = Field(..., description="Nombre del producto.")
    product_description: Optional[str] = Field(
        None, description="Descripción del producto."
    )

    class Config:
        from_attributes = True
        # json_encoders = {uuid.str: str} # Puedes mantener o quitar si el str ya viene como str


# --- Modelo para la respuesta de la vista de Productos por Usuario ---
class ProductByUser(BaseModel):
    """
    Representa una tupla de acceso a un Producto para un usuario específico,
    incluyendo la jerarquía superior (Producto y Producto).
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
    organization_id: str = Field(
        ..., description="str de la producto a la que pertenece el proyecto."
    )
    organization_name: str = Field(..., description="Nombre de la producto.")
    project_id: str = Field(..., description="str del proyecto.")
    project_name: str = Field(..., description="Nombre del proyecto.")

    # --- Datos del Producto ---
    product_id: str = Field(..., description="str del producto.")
    product_name: str = Field(..., description="Nombre del producto.")
    product_description: Optional[str] = Field(
        None, description="Descripción del producto."
    )

    class Config:
        from_attributes = True
        # json_encoders = {uuid.str: str} # Puedes mantener o quitar si el str ya viene como str


# --- Modelo para la respuesta de la vista de Productos por Usuario ---
class ProductRegisterRequest(BaseModel):
    """
    Datos necesarios para llamar a spu_minddash_app_insert_product.
    """

    # --- Parámetros OBLIGATORIOS (NOT NULL en la tabla o el SP) ---
    project_id: str = Field(
        ..., description="ID del proyecto al que pertenece este producto."
    )
    name: str = Field(
        ...,
        max_length=200,
        description="Nombre del producto (ej: 'Chatbot de Soporte').",
    )

    # --- Parámetros con DEFAULT en el SP (opcionales en la solicitud, pero con valor) ---
    description: Optional[str] = Field(
        None, max_length=200, description="Descripción del producto."
    )
    language: Optional[str] = Field(
        None, max_length=50, description="Idioma principal (ej: 'es', 'en')."
    )
    tipo: Optional[str] = Field(
        "chatbot",
        max_length=20,
        description="Tipo de producto ('chatbot' por defecto).",
    )

    # Nota: Usamos Union[Dict, str] ya que Pydantic puede validar un diccionario,
    # pero a menudo los drivers de Python esperan la representación JSON como string.
    config: Optional[Dict[str, Any]] = Field(
        default_factory=lambda: {}, description="Configuración JSONB del producto."
    )

    welcome_message: Optional[str] = Field(
        None, max_length=100, description="Mensaje de bienvenida del producto."
    )
    label: Optional[str] = Field(
        None, max_length=50, description="Etiqueta corta del producto."
    )
    label_color: Optional[str] = Field(
        None,
        max_length=20,
        description="Código de color para la etiqueta (ej: '#007bff').",
    )

    max_users: Optional[conint(ge=0)] = Field(
        100, description="Límite máximo de usuarios concurrentes."
    )

    is_active_rag: Optional[bool] = Field(
        False,
        description="Indica si la funcionalidad RAG (Recuperación Aumentada) está activa.",
    )
    is_active_alerts: Optional[bool] = Field(
        False, description="Indica si el sistema de alertas está activo."
    )
    is_active_insight: Optional[bool] = Field(
        False,
        description="Indica si la funcionalidad de insights/análisis está activa.",
    )

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "project_id": "a6f38618-4308-4dfc-83d7-4f98651649c1",
                "name": "Chatbot de Ventas",
                "description": "Bot automatizado para calificar leads.",
                "language": "en",
                "tipo": "chatbot",
                "config": {"model": "gpt-4", "prompt_version": "v2"},
                "welcome_message": "Hello, how can I help you?",
                "label": "SALES-BOT",  # <-- AÑADIDO
                "label_color": "#008000",  # <-- AÑADIDO
                "max_users": 200,
                "is_active_rag": True,
                "is_active_alerts": False,  # <-- AÑADIDO para ser completo
                "is_active_insight": False,  # <-- AÑADIDO para ser completo
            }
        }


class ProductUpdateRequest(BaseModel):
    """
    Datos necesarios para llamar a spu_minddash_app_update_product.
    Todos los campos deben ser provistos para la actualización completa.
    """

    # --- Parámetros de Identificación ---
    id: str = Field(..., description="ID del producto que se va a actualizar.")
    project_id: str = Field(
        ..., description="ID del proyecto (para reasignación o verificación de FK)."
    )

    # --- Parámetros de Actualización ---
    name: str = Field(..., max_length=200, description="Nuevo nombre del producto.")
    description: Optional[str] = Field(
        None, max_length=200, description="Nueva descripción."
    )
    language: Optional[str] = Field(None, max_length=50, description="Nuevo idioma.")
    tipo: Optional[str] = Field(
        "chatbot", max_length=20, description="Nuevo tipo de producto."
    )
    config: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Nueva configuración JSONB."
    )
    welcome_message: Optional[str] = Field(
        None, max_length=100, description="Nuevo mensaje de bienvenida."
    )
    label: Optional[str] = Field(None, max_length=50, description="Nueva etiqueta.")
    label_color: Optional[str] = Field(
        None, max_length=20, description="Nuevo color de etiqueta."
    )
    max_users: Optional[conint(ge=0)] = Field(
        100, description="Nuevo límite de usuarios."
    )

    # Se incluye para poder activar/desactivar el producto
    is_active: Optional[bool] = Field(
        True, description="Estado de actividad del producto."
    )

    is_active_rag: Optional[bool] = Field(False, description="Nuevo estado de RAG.")
    is_active_alerts: Optional[bool] = Field(
        False, description="Nuevo estado de alertas."
    )
    is_active_insight: Optional[bool] = Field(
        False, description="Nuevo estado de insights."
    )

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "1ee67952-ef83-4038-ae9d-d95d2f16c32e",
                "project_id": "a6f38618-4308-4dfc-83d7-4f98651649c1",
                "name": "Chatbot de Ventas (v1.1)",
                "description": "Bot automatizado con nueva lógica de calificación.",
                "language": "es",
                "tipo": "chatbot",
                "config": {"model": "gpt-4o", "prompt_version": "v3"},
                "welcome_message": "Bienvenido al bot de ventas actualizado.",  # <-- AÑADIDO
                "label": "SALES-V1.1",  # <-- AÑADIDO
                "label_color": "#0000FF",  # <-- AÑADIDO
                "max_users": 250,
                "is_active": True,
                "is_active_rag": True,
                "is_active_alerts": True,  # <-- AÑADIDO para ser completo
                "is_active_insight": True,  # <-- AÑADIDO para ser completo
            }
        }


class ProductDeleteRequest(BaseModel):
    """
    Datos necesarios para llamar a spu_minddash_app_delete_product.
    Solo requiere el ID.
    """

    id: str = Field(..., description="ID del producto que se va a eliminar.")

    class Config:
        from_attributes = True
        json_schema_extra = {"example": {"id": "1ee67952-ef83-4038-ae9d-d95d2f16c32e"}}


class GetProductRequest(BaseModel):
    """
    Modelo para validar el cuerpo de la solicitud que contiene el ID de usuario.
    """

    user_id: str = Field(
        ..., description="str del usuario para el cual se buscan las organizaciones."
    )


class ProductCreationResponse(BaseModel):
    id_product: str


class ProductUpdateResponse(BaseModel):
    message: str = Field(
        "Producto actualizada exitosamente.", description="Mensaje de confirmación."
    )
    product_id: str = Field(..., description="str de la Producto actualizada.")


class ProductDeleteResponse(BaseModel):
    message: str = Field(
        "Producto eliminada exitosamente.", description="Mensaje de confirmación."
    )
    product_id: str = Field(..., description="str de la Producto eliminada.")


"""
    Bloque para control de accesos de producto:
"""


class ProductRegisterAccessRequest(BaseModel):
    """
    Modelo para la entrada de datos al registrar un nuevo acceso (INSERT).
    Corresponde a los parámetros del SP: user_id, product_id, role_id.
    """

    user_id: str = Field(..., description="UUID del usuario al que se le da acceso.")
    product_id: str = Field(
        ..., description="UUID de la producto a la que se da acceso."
    )
    role_id: str = Field(..., description="UUID del rol que se asigna en esa producto.")


class ProductUpdateAccessRequest(BaseModel):
    """
    Modelo para la entrada de datos al actualizar un registro de acceso existente (UPDATE).
    Corresponde a los parámetros del SP: id, user_id, product_id, role_id.
    """

    id: str = Field(
        ...,
        description="UUID del registro de acceso a actualizar (access_user_product.id).",
    )
    user_id: str = Field(
        ..., description="Nuevo UUID del usuario (generalmente el mismo)."
    )
    product_id: str = Field(
        ..., description="Nuevo UUID de la producto (generalmente el mismo)."
    )
    role_id: str = Field(..., description="Nuevo UUID del rol que se asigna.")


class ProductDeleteAccessRequest(BaseModel):
    """
    Modelo para la entrada de datos al eliminar un registro de acceso (DELETE).
    Solo requiere el ID del registro de acceso.
    """

    id: str = Field(
        ...,
        description="UUID del registro de acceso a eliminar (access_user_product.id).",
    )


class ProductCreationAccessResponse(BaseModel):
    """Respuesta para el registro exitoso."""

    product_access_id: str = Field(
        ..., description="UUID del nuevo registro de acceso creado."
    )


class ProductAccessResponse(BaseModel):
    message: str = "Acceso a producto registrado exitosamente."
    product_access_id: str


class ProductUpdateAccessResponse(BaseModel):
    """Respuesta para la actualización exitosa."""

    message: str = "Acceso a producto actualizado exitosamente."
    product_access_id: str = Field(
        ..., description="UUID del registro de acceso actualizado."
    )


class ProductDeleteAccessResponse(BaseModel):
    """Respuesta para la eliminación exitosa."""

    message: str = "Acceso a producto eliminado exitosamente."
    product_access_id: str = Field(
        ..., description="UUID del registro de acceso eliminado."
    )
