from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

ConnectionType = Literal["Email", "Wsp", "Teams"]
AlertType = Literal["reporte", "alerta"]


# ----------------------------------------------------------------------
# ESTRUCTURA INTERNA DE DESTINATARIOS
# ----------------------------------------------------------------------
class EmailRecipients(BaseModel):
    """Define las listas de destinatarios para un correo electrónico."""

    to: List[str] = Field(
        ..., description="Lista de correos electrónicos principales (To)."
    )
    cc: Optional[List[str]] = Field(
        None, description="Lista de correos electrónicos con copia (Cc)."
    )
    bcc: Optional[List[str]] = Field(
        None, description="Lista de correos electrónicos con copia oculta (Bcc)."
    )

    class Config:
        json_schema_extra = {
            "example": {
                "to": ["operador_critico@miempresa.com"],
                "cc": ["manager@miempresa.com"],
                "bcc": ["logs_seguridad@miempresa.com"],
            }
        }


# ----------------------------------------------------------------------
# MODELO DE SOLICITUD (INPUT)
# ----------------------------------------------------------------------
class SendAlertRequest(BaseModel):
    """Modelo principal de datos para la solicitud de envío de alerta."""

    # Datos del contenido
    subject: Optional[str] = Field(
        None, description="Asunto o título del mensaje de alerta."
    )
    html_body: Optional[str] = Field(
        None,
        description="Cuerpo del mensaje en formato HTML (puede contener el texto enriquecido del LLM).",
    )

    # Datos del emisor
    sender_email: Optional[str] = Field(
        None,
        description="El correo del remitente (debe estar verificado en el servicio SMTP, ej. Brevo).",
    )
    sender_name: Optional[str] = Field(
        None, description="Nombre amigable del remitente (ej. 'Sistema de Alertas AI')."
    )

    # Destinatarios
    recipients: Optional[EmailRecipients] = None

    # Parámetro extra para manejar distintos tipos de alerta
    # Usamos Literal para restringir los valores posibles.
    alert_type: Literal["email", "teams", "slack", "whatsapp"] = Field(
        "email", description="El tipo de canal de notificación a usar."
    )

    message_content_wsp: Optional[str] = Field(
        None, description="El mensaje completo de envio al webhook de alertas"
    )
    message_sender_wsp: Optional[str] = Field(
        None, description="El Nombre de la persona al que se dirige el mensaje."
    )
    message_phone_number_wsp: Optional[str] = Field(
        None, description="El numero Telefonico de Envio del Mensaje."
    )

    secre_access_token: Optional[str] = Field(
        None, description="El Nombre del creto que contiene el access Token"
    )
    url_path: Optional[str] = Field(
        None, description="El link del servicio para envio de alertas."
    )

    class Config:
        json_schema_extra = {
            "example": {
                "alert_type": "email",
                "subject": "ALERTA DE VENTAS: Caída del 10% Mensual",
                "sender_email": "cesarcondor2013@gmail.com",
                "sender_name": "Agente AI | Monitoreo de Negocio",
                "recipients": {
                    "to": ["cesarcondor2013@gmail.com"],
                    "cc": ["cesarcondor2013@gmail.com"],
                    "bcc": [],
                },
                "html_body": '<div style="font-family: Arial, sans-serif; padding: 20px; border: 1px solid #ddd; max-width: 600px; margin: auto;"><h2 style="color: #e6b200; border-bottom: 2px solid #e6b200; padding-bottom: 10px;">\u26a0\ufe0f Alerta de Tendencia Cr\u00edtica: Ca\u00edda de Ventas \u26a0\ufe0f</h2><p style="font-size: 14px; color: #555;">El an\u00e1lisis del Agente AI muestra una disminuci\u00f3n significativa en las ventas totales del mes. Se recomienda revisar la ejecuci\u00f3n de la \u00faltima campa\u00f1a.</p><h3 style="color: #333;">Resumen Comparativo (Mensual):</h3><table style="width: 100%; border-collapse: collapse; margin-top: 15px;"><thead style="background-color: #fce8e8;"><tr><th style="padding: 10px; border: 1px solid #ddd; text-align: left;">Per\u00edodo</th><th style="padding: 10px; border: 1px solid #ddd; text-align: left;">Ventas Totales</th><th style="padding: 10px; border: 1px solid #ddd; text-align: left;">Diferencia vs. Mes Anterior</th></tr></thead><tbody><tr style="background-color: #fff;"><td style="padding: 10px; border: 1px solid #ddd;">Mes Anterior</td><td style="padding: 10px; border: 1px solid #ddd;"><b>$500,000 USD</b></td><td style="padding: 10px; border: 1px solid #ddd;">-</td></tr><tr style="background-color: #ffe0e0;"><td style="padding: 10px; border: 1px solid #ddd;">Mes Actual</td><td style="padding: 10px; border: 1px solid #ddd;"><b>$450,000 USD</b></td><td style="padding: 10px; border: 1px solid #ddd; color: #cc0000; font-weight: bold;">-10% \u2b07\ufe0f</td></tr></tbody></table><h3 style="color: #111; margin-top: 30px;">Recomendaci\u00f3n:</h3><p style="background-color: #fffaf0; padding: 15px; border-left: 5px solid #ff9900; font-size: 14px;">El Agente AI sugiere priorizar una reuni\u00f3n inmediata con el equipo de Marketing para revisar la segmentaci\u00f3n y el presupuesto de la pr\u00f3xima semana.</p><p style="font-size: 12px; color: #888; margin-top: 20px;">Este mensaje de alerta fue enviado correctamente por el Sistema AI.</p></div>',
                "message_content_wsp": "Es una prueba de mensaje by Alerts API",
                "message_sender_wsp": "Cesar Condor",
                "message_phone_number_wsp": "+51939275711",
                "secre_access_token": "tttt-xxxx-tt",
                "url_path": "www.linkgalert.com",
            }
        }


# ----------------------------------------------------------------------
# MODELO DE RESPUESTA (OUTPUT)
# ----------------------------------------------------------------------
class SendAlertResponse(BaseModel):
    """
    Estructura de la respuesta estándar del endpoint de envío de alertas.
    """

    # Restringimos el status a 'success' o 'error'
    status: Literal["success", "error"] = Field(..., description="Resultado general...")
    message: str = Field(..., description="Mensaje conciso...")
    alert_type: str = Field(..., description="El tipo de notificación procesado.")
    details: Optional[Dict[str, Any]] = Field(
        None, description="Contiene datos específicos del proveedor o errores."
    )

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "status": "success",
                    "message": "Correo enviado exitosamente. ID de Brevo: 12345ABC",
                    "alert_type": "email",
                    "details": {
                        "brevo_message_id": "b6a71e72-d5e8-42f1-a1b7-d1a2f3e4d5c6"
                    },
                },
                {
                    "status": "error",
                    "message": "Fallo en la autenticación con Brevo.",
                    "alert_type": "email",
                    "details": {
                        "error_code": 401,
                        "provider_message": "Invalid API Key",
                    },
                },
            ]
        }


# ----------------------------------------------------------------------
# GENERACION Y ACTUALIZACION DE DATOS ALERTAS
# ----------------------------------------------------------------------
class ListAlerts(BaseModel):
    """
    Datos para registrar una nueva alerta.
    """

    id: str = Field(..., description="ID de la alerta.")
    product_id: str = Field(
        ..., description="str del producto al que pertenece la alerta."
    )
    prompt_alerta: str = Field(
        ..., max_length=1500, description="El contenido o lógica de la alerta."
    )
    codigo_cron: str = Field(
        ..., max_length=100, description="Frecuencia de ejecución en formato CRON."
    )
    user_id: str = Field(
        ..., max_length=250, description="ID del usuario que creó la alerta."
    )
    session_id: Optional[str] = Field(
        None,
        max_length=150,
        description="ID de la sesión de usuario que creó la alerta.",
    )
    flg_habilitado: Optional[bool] = Field(
        True, description="Estado de habilitación de la alerta."
    )
    fecha_inicio: Optional[datetime] = Field(
        None, description="Fecha y hora opcional de inicio de la alerta."
    )
    fecha_fin: Optional[datetime] = Field(
        None, description="Fecha y hora opcional de fin de la alerta."
    )
    type_alert: Optional[str] = Field(
        None, max_length=250, description="Tipo de Alerta Enviado."
    )
    configuration_alert: Optional[Dict[str, Any]] = Field(
        default_factory=lambda: {}, description="Configuración JSONB específica."
    )

    class Config:
        from_attributes = True


class AlertRegisterRequest(BaseModel):
    """
    Datos para registrar una nueva alerta.
    """

    product_id: str = Field(
        ..., description="UUID del producto al que pertenece la alerta."
    )
    prompt_alerta: str = Field(
        ..., max_length=1500, description="El contenido o lógica de la alerta."
    )
    codigo_cron: str = Field(
        ..., max_length=100, description="Frecuencia de ejecución en formato CRON."
    )
    user_id: str = Field(
        ..., max_length=150, description="ID del usuario que creó la alerta."
    )
    session_id: Optional[str] = Field(
        None,
        max_length=150,
        description="ID de la sesión de usuario que creó la alerta.",
    )

    # --- CAMPO NUEVO ---
    channel_product_type: Optional[str] = Field(
        None,
        max_length=100,
        description="Tipo de relación del producto/canal (ej: 'whatsapp', 'email').",
    )
    # ---------------------

    flg_habilitado: Optional[bool] = Field(
        True, description="Estado de habilitación de la alerta."
    )
    fecha_inicio: Optional[datetime] = Field(
        None, description="Fecha y hora opcional de inicio de la alerta."
    )
    fecha_fin: Optional[datetime] = Field(
        None, description="Fecha y hora opcional de fin de la alerta."
    )

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "product_id": "a6f38618-4308-4dfc-83d7-4f98651649c1",
                "prompt_alerta": "dame el top 5 de ventas por mes",
                "codigo_cron": "0 8 * * *",
                "user_id": "user-abc-123",
                "session_id": "sess-xyz-456",
                "channel_product_type": "whatsapp",  # NUEVO
                "flg_habilitado": True,
            }
        }


class AlertUpdateRequest(BaseModel):
    """
    Datos para actualizar una alerta existente.
    """

    id: str = Field(..., description="ID de la alerta que se va a actualizar.")
    product_id: Optional[str] = Field(None, description="Nuevo UUID del producto.")
    prompt_alerta: Optional[str] = Field(
        None, max_length=1500, description="Nuevo contenido o lógica de la alerta."
    )
    codigo_cron: Optional[str] = Field(
        None, max_length=100, description="Nueva frecuencia CRON."
    )
    user_id: Optional[str] = Field(
        None, max_length=150, description="ID del usuario que realiza la actualización."
    )
    session_id: Optional[str] = Field(
        None,
        max_length=150,
        description="ID de la sesión de usuario que creó la alerta.",
    )

    # --- CAMPO NUEVO ---
    channel_product_type: Optional[str] = Field(
        None, max_length=100, description="Nuevo tipo de relación del producto/canal."
    )
    # ---------------------

    flg_habilitado: Optional[bool] = Field(
        None, description="Nuevo estado de habilitación."
    )
    fecha_inicio: Optional[datetime] = Field(None, description="Nueva fecha de inicio.")
    fecha_fin: Optional[datetime] = Field(None, description="Nueva fecha de fin.")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "1ee67952-ef83-4038-ae9d-d95d2f16c32e",
                "product_id": "a6f38618-4308-4dfc-83d7-4f98651649c1",
                "prompt_alerta": "dame el top 10 de ventas por mes",
                "codigo_cron": "0 9 * * *",
                "user_id": "user-abc-123",
                "session_id": "sess-xyz-456",
                "channel_product_type": "email",  # NUEVO
                "flg_habilitado": False,
            }
        }


class AlertDeleteRequest(BaseModel):
    """
    Datos para eliminar una alerta.
    """

    id: str = Field(..., description="ID de la alerta que se va a eliminar.")


# === RESPUESTAS ===


class AlertCreationResponse(BaseModel):
    id_alerta: str = Field(..., description="ID de la alerta recién creada.")


class AlertUpdateResponse(BaseModel):
    id_alerta: str = Field(..., description="ID de la alerta actualizada.")


class AlertDeleteResponse(BaseModel):
    id_alerta: str = Field(..., description="ID de la alerta eliminada.")


class ListAlertsDeployed(BaseModel):
    """
    Representa la información combinada necesaria para ejecutar una alerta,
    obtenida de la vista view_info_to_agent.
    """

    # Campos de la vista view_list_products (vlp)
    user_id: str = Field(..., description="ID del usuario (como string).")
    user_name: str = Field(..., description="Nombre del usuario.")
    product_id: str = Field(..., description="ID del producto (como string).")
    product_name: str = Field(..., description="Nombre del producto.")  # <<< AÑADIDO
    organization_name: str = Field(..., description="Nombre de la organización.")
    project_name: str = Field(..., description="Nombre del proyecto.")

    # Campos de roles_data_access (rda)
    name_rol_datos: Optional[str] = Field(
        None, description="Nombre del rol de acceso a datos."
    )

    # Campos combinados (uda + rda)
    tables_name: Optional[List[str]] = Field(
        None, description="Lista combinada de nombres de tablas permitidas."
    )
    metrics_access: Optional[List[str]] = Field(
        None, description="Lista combinada de métricas permitidas."
    )
    data_access: Dict[str, Any] = Field(
        ..., description="Configuración JSONB combinada de acceso a datos."
    )

    # Campos de clients_products_deploys (cpd)
    bucket_config: Optional[str] = Field(
        None, description="Ruta base del bucket de configuración."
    )
    gs_examples_agent: Optional[str] = Field(
        None, description="Ruta GCS a los ejemplos del agente."
    )
    gs_prompt_agent: Optional[str] = Field(
        None, description="Ruta GCS del prompt del agente."
    )  # <<< YA ESTABA, ORDENADO
    gs_prompt_sql: Optional[str] = Field(
        None, description="Ruta GCS del prompt SQL del agente."
    )  # <<< YA ESTABA, ORDENADO
    gs_profiling_agent: Optional[str] = Field(
        None, description="Ruta GCS a la configuración de perfiles."
    )
    gs_metrics_config_agent: Optional[str] = Field(
        None, description="Ruta GCS a la configuración de métricas."
    )
    gs_semantic_config: Optional[str] = Field(
        None, description="Ruta GCS a la configuración de capa semantica."
    )
    client: Optional[str] = Field(
        None, description="Identificador del cliente o conexión."
    )  # <<< DEFINIDO UNA SOLA VEZ

    config_connection: Dict[str, Any] = Field(
        ..., description="Configuración de conexión."
    )

    search_knowledge_config: Optional[Dict[str, Any]] = Field(
        ..., description="Configuración de RAG."
    )

    class Config:
        from_attributes = True


class AlertListResponse(BaseModel):
    alerts: List[ListAlerts]
