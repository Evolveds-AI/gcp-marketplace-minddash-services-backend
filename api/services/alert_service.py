from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional
import uuid
import requests

logger = logging.getLogger(__name__)
import asyncio
from datetime import datetime, timedelta, timezone, date
from uuid import UUID

import aiohttp
import pytz
from croniter import croniter
from dotenv import load_dotenv
from google.cloud import pubsub_v1

load_dotenv()


from api.models.alert_models import (
    AlertDeleteRequest,
    AlertRegisterRequest,
    AlertUpdateRequest,
    ListAlerts,
    ListAlertsDeployed,
    # Alert,
    SendAlertRequest,
)
from api.utils.db_client import execute, execute_procedure_with_out, query_all
from api.utils.gcp_utils import get_secret_value

"""
    Ejecucion del envio de las alertas: 
"""

# BREVO_API_KEY = os.environ.get("BREVO_API_KEY")
BREVO_API_KEY = os.getenv("BREVO_API_KEY")
BREVO_API_URL = os.getenv("BREVO_API_URL")
WHATSAPP_ENDPOINT_URL = os.getenv("WHATSAPP_ENDPOINT_URL")
PUBSUB_TOPIC_ID = os.getenv("PUBSUB_TOPIC_ID")
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
PUBSUB_PUBLISHER = pubsub_v1.PublisherClient()
PUBSUB_TOPIC_PATH = PUBSUB_PUBLISHER.topic_path(PROJECT_ID, PUBSUB_TOPIC_ID)
CHAT_ENDPOINT_URL = os.getenv("CHAT_ENDPOINT_URL")
# PROJECT_ID


def send_email_brevo(
    subject: str,
    html_content: str,
    to_emails: List[str],
    sender_email: str,
    sender_name: str,
    cc_emails: Optional[List[str]] = None,
    bcc_emails: Optional[List[str]] = None,
    alert_type: str = "email",
    url_path: str = "",
    secret_path: str = "",
) -> Dict:
    """
    Envía un correo electrónico transaccional usando la API de Brevo.
    """

    if not secret_path:
        return {"success": False, "message": "BREVO_API_KEY no configurada."}

    print("secret_path", secret_path)
    print("PROJECT_ID", PROJECT_ID)

    secret_value = get_secret_value(id_secreto=secret_path, id_proyecto=PROJECT_ID)

    # MANEJO DE NONE A LISTA VACÍA (Clave de robustez)
    cc_emails_safe = cc_emails or []
    bcc_emails_safe = bcc_emails or []

    # Estructuración de los destinatarios para la API de Brevo
    to_list = [{"email": email} for email in to_emails]
    cc_list = [{"email": email} for email in cc_emails_safe]
    bcc_list = [{"email": email} for email in bcc_emails_safe]

    # Payload (cuerpo) de la solicitud a Brevo
    payload = {
        "sender": {"name": sender_name, "email": sender_email},
        "to": to_list,
        "subject": subject,
        "htmlContent": html_content,
    }

    if cc_list:
        payload["cc"] = cc_list

    if bcc_list:
        payload["bcc"] = bcc_list

    # Imprimimos el JSON que va a salir para debug
    json_payload_to_send = json.dumps(payload)
    print("--- DEBUG: JSON de Salida ---")
    print(json.dumps(payload, indent=2))
    print("-----------------------------\n")

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "api-key": secret_value,
    }

    try:
        response = requests.post(url_path, headers=headers, data=json.dumps(payload))

        if response.status_code == 201:
            # RETORNO DE ÉXITO: Formato SendAlertResponse
            return {
                "status": "success",
                "message": f"Correo enviado a {len(to_emails)} destinatarios.",
                "alert_type": alert_type,
                "details": {"brevo_message_id": response.json().get("messageId")},
            }
        else:
            # RETORNO DE ERROR DE BREVO: Formato SendAlertResponse
            error_data = response.json()
            return {
                "status": "error",
                "message": f"Error Brevo: {response.status_code}",
                "alert_type": alert_type,
                "details": error_data,
            }

    except requests.exceptions.RequestException as e:
        # RETORNO DE ERROR DE CONEXIÓN: Formato SendAlertResponse
        return {
            "status": "error",
            "message": f"Error de conexión o timeout: {str(e)}",
            "alert_type": alert_type,
            "details": {},
        }


def send_message_whatsapp(
    message_content_wsp: str,
    message_sender_wsp: str,
    message_phone_number_wsp: str,
    alert_type: str = "whatsapp",
    url_path: str = "",
    secret_path: str = "",
) -> Dict[str, Any]:
    """
    Envía una alerta de WhatsApp. Ajustado para no fallar si la respuesta es asíncrona y vacía.
    """

    whatsapp_url = url_path  # WHATSAPP_ENDPOINT_URL
    if not whatsapp_url:
        return {
            "status": "error",
            "message": "WHATSAPP_ENDPOINT_URL no configurada en el entorno.",
            "alert_type": alert_type,
            "details": {},
        }

    # Estructuración del Payload
    payload = {
        "phoneNumber": message_phone_number_wsp,
        "userName": message_sender_wsp,
        "message": message_content_wsp,
    }

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        # Incluir "Authorization" si es necesario
    }

    # Imprimimos el JSON que va a salir para debug
    json_payload_to_send = json.dumps(payload)
    print("--- DEBUG: JSON de Salida ---")
    print(json.dumps(json_payload_to_send, indent=2))
    print("-----------------------------\n")

    try:
        response = requests.post(
            whatsapp_url, headers=headers, data=json.dumps(payload)
        )

        # --- Lógica de Manejo de Respuesta Ajustada ---

        # Si la solicitud fue exitosa (2xx)
        if response.status_code >= 200 and response.status_code < 300:
            # Intenta obtener los detalles solo si hay contenido para evitar el error "Expecting value"
            details = {}
            if response.content:
                try:
                    details = response.json()
                except json.JSONDecodeError:
                    # Si el endpoint responde 200/201 con texto, pero no JSON (ej: 'OK')
                    details = {"response_text": response.text.strip()}

            # RETORNO DE ÉXITO: Ideal para endpoints asíncronos.
            return {
                "status": "success",
                "message": f"Mensaje de WhatsApp enviado (código {response.status_code}).",
                "alert_type": alert_type,
                "details": details,
            }
        else:
            # Si el código de estado indica un error (4xx, 5xx)
            error_data = {
                "status_code": response.status_code,
                "response_text": response.text,
            }
            if response.content:
                try:
                    # Intenta obtener el JSON de error si existe
                    error_data.update(response.json())
                except json.JSONDecodeError:
                    pass  # Dejar response_text como detalle si no es JSON

            # RETORNO DE ERROR DEL ENDPOINT
            return {
                "status": "error",
                "message": f"Error en el Endpoint de WhatsApp (Status {response.status_code})",
                "alert_type": alert_type,
                "details": error_data,
            }

    except requests.exceptions.RequestException as e:
        # RETORNO DE ERROR DE CONEXIÓN o TIMEOUT
        return {
            "status": "error",
            "message": f"Error de conexión o timeout al enviar WhatsApp: {str(e)}",
            "alert_type": alert_type,
            "details": {},
        }


# envio de Alertas
def process_and_send_alert(alert_data: SendAlertRequest) -> Dict[str, Any]:
    """
    Lógica de servicio que procesa el tipo de alerta y llama al método de envío adecuado.
    """
    alert_type = alert_data.alert_type.lower()

    if alert_type == "email":
        # Llama a la función ajustada que devuelve el formato SendAlertResponse
        result = send_email_brevo(
            subject=alert_data.subject,
            html_content=alert_data.html_body,
            to_emails=alert_data.recipients.to,
            sender_email=alert_data.sender_email,
            sender_name=alert_data.sender_name,
            cc_emails=alert_data.recipients.cc,
            bcc_emails=alert_data.recipients.bcc,
            alert_type=alert_type,
            url_path=alert_data.url_path,
            secret_path=alert_data.secre_access_token,
        )
        return result

    elif alert_type == "whatsapp":
        # La lógica de Teams también debe devolver el formato SendAlertResponse
        result = send_message_whatsapp(
            message_content_wsp=alert_data.message_content_wsp,
            message_phone_number_wsp=alert_data.message_phone_number_wsp,
            message_sender_wsp=alert_data.message_sender_wsp,
            alert_type=alert_type,
            url_path=alert_data.url_path,
            secret_path=alert_data.secre_access_token,
        )
        return result

    elif alert_type == "teams":
        # La lógica de Teams también debe devolver el formato SendAlertResponse
        return {
            "status": "success",
            "message": "Lógica de Teams no implementada, pero la solicitud es válida.",
            "alert_type": "teams",
            "details": {},
        }

    else:
        # El manejo de error también debe devolver el formato SendAlertResponse
        return {
            "status": "error",
            "message": f"Tipo de alerta '{alert_type}' no soportado.",
            "alert_type": alert_type,
            "details": {},
        }


# Admin de datos BD
def send_register_alert(alert_data: AlertRegisterRequest) -> str:
    """
    Llama al Stored Procedure para registrar una nueva alerta.
    """

    session_id_final = (
        alert_data.session_id
        if alert_data.session_id and alert_data.session_id.strip()
        else str(uuid.uuid4())
    )

    query_str = """
        CALL spu_minddash_app_insert_alerta(
            p_product_id := %s,
            p_prompt_alerta := %s,
            p_codigo_cron := %s,
            p_user_id := %s,
            p_session_id := %s,
            p_channel_product_type := %s,
            new_alerta_id := %s, 
            p_flg_habilitado := %s,
            p_fecha_inicio := %s,
            p_fecha_fin := %s
        );
    """

    params = (
        alert_data.product_id,
        alert_data.prompt_alerta,
        alert_data.codigo_cron,
        alert_data.user_id,
        session_id_final,
        alert_data.channel_product_type,
        None,
        alert_data.flg_habilitado,
        alert_data.fecha_inicio,
        alert_data.fecha_fin,
    )

    result: Dict[str, Any] | None = execute_procedure_with_out(query_str, params=params)

    if result and "new_alerta_id" in result:
        return str(result["new_alerta_id"])
    else:
        # Si llegamos aquí, algo raro pasó pero no saltó exception de SQL.
        raise Exception("Error desconocido: El procedimiento no retornó un ID válido.")


def send_update_alert(alert_data: AlertUpdateRequest) -> int:
    """
    Llama al Stored Procedure para actualizar una alerta.
    """
    # Orden del SP: p_id, p_product_id, p_prompt_alerta, p_codigo_cron, p_flg_habilitado,
    #              p_fecha_inicio, p_fecha_fin, p_session_id, p_user_id, p_channel_product_type

    session_id_final = (
        alert_data.session_id
        if alert_data.session_id and alert_data.session_id.strip()
        else str(uuid.uuid4())
    )

    query_str = """
        CALL spu_minddash_app_update_alerta(
            p_id := %s,
            p_product_id := %s,
            p_prompt_alerta := %s,
            p_codigo_cron := %s,
            p_flg_habilitado := %s,
            p_fecha_inicio := %s,
            p_fecha_fin := %s,
            p_session_id := %s,
            p_user_id := %s,
            p_channel_product_type := %s    -- NUEVO
        );
    """

    params = (
        alert_data.id,
        alert_data.product_id,
        alert_data.prompt_alerta,
        alert_data.codigo_cron,
        alert_data.flg_habilitado,
        alert_data.fecha_inicio,
        alert_data.fecha_fin,
        session_id_final,
        alert_data.user_id,
        alert_data.channel_product_type,  # NUEVO VALOR
    )

    rowcount = execute(query_str, params=params)
    return rowcount


###
def send_delete_alert(alert_data: AlertDeleteRequest) -> int:
    """
    Llama al Stored Procedure para eliminar una alerta.
    """
    alert_id = alert_data.id

    query_str = """
        CALL spu_minddash_app_delete_alerta(
            p_id := %s
        );
    """

    params = (alert_id,)

    try:
        rowcount = execute(query_str, params=params)
        return rowcount
    except Exception:
        raise


"""
    Orquestacion de Alertas
"""


async def fetch_view_data_deploy(
    product_id: str, user_id: str = None
) -> ListAlertsDeployed:
    """
    Busca la informacion de despliegue por producto y usuario.

    NOTA: Reemplazar con tu lógica real de conexión a la BD.
    """
    query_str = f"""
        select 
            user_id
            , user_name
            , product_id
            , product_name
            , organization_name 
            , project_name 
            , name_rol_datos
            , tables_name
            , metrics_access
            , data_access 
            , bucket_config 
            , gs_examples_agent 
            , gs_profiling_agent 
            , gs_metrics_config_agent 
            , gs_semantic_config
			, gs_prompt_agent
			, gs_prompt_sql
            , client 
            , search_knowledge_config
            , config_connection
        from view_info_to_agent
        where 
                product_id = '{product_id}'::UUID
            and user_id = '{user_id}';
    """
    rows = query_all(query_str)

    # 2. CAMBIO: Procesar el resultado
    if not rows:
        # Si no hay filas, devuelve None
        return None

    elif len(rows) > 1:
        logger.warning(
            f"Se encontraron {len(rows)} configuraciones para product_id={product_id}, user_id={user_id}. Se usará la primera."
        )

    # Si hay al menos una fila, toma la primera
    first_row = rows[0]

    return ListAlertsDeployed(**first_row)


async def execute_single_alert(alert: ListAlerts, now_truncated: datetime):
    """
    Ejecuta la lógica de una alerta:
    1. Consulta la vista 'view_info_to_agent'.
    2. Construye el cuerpo (body) de la solicitud.
    3. Envía la solicitud al endpoint /chat.
    """

    alert_id = alert.id
    product_id_str = str(
        alert.product_id
    )  # Asegura que sea string para la consulta/body
    user_id_str = str(alert.user_id)
    type_alert = alert.type_alert

    if alert.configuration_alert:
        final_alert_config = alert.configuration_alert.copy()
    else:
        final_alert_config = {}
    final_alert_config["alert_type"] = alert.type_alert

    print(f"  -> Iniciando ejecución de alerta: {alert_id}")

    try:
        # --- 1. Obtener Datos de Configuración de la Vista ---
        print(
            f"  -> Consultando configuración para product_id - user_id: {product_id_str} - {user_id_str}"
        )

        view_data_obj: ListAlertsDeployed = await fetch_view_data_deploy(
            product_id_str, user_id_str
        )

        if not view_data_obj:
            print(
                f"  -> ERROR: No se encontró configuración en 'view_info_to_agent' para product_id - user_id: {product_id_str} - {user_id_str}"
            )
            return  # Termina la ejecución si no hay datos

        print(f"  -> Body view_data: {view_data_obj}")
        print(f"  -> Body alert: {alert}")
        # --- 2. Construir el Cuerpo (Body) de la Solicitud ---
        body_data = {
            "message": alert.prompt_alerta,
            "needChart": True,
            "client": view_data_obj.client,  # Usa el objeto y el punto
            "user_id": user_id_str,
            "session_id": str(alert.session_id),
            "client_id": view_data_obj.product_name,  # Usa el objeto y el punto
            "product_id": product_id_str,
            "bucket_config": view_data_obj.bucket_config,  # Usa el objeto y el punto
            "gs_examples_agent": view_data_obj.gs_examples_agent,  # Usa el objeto y el punto
            "gs_prompt_agent": view_data_obj.gs_prompt_agent,
            "gs_prompt_sql": view_data_obj.gs_prompt_sql,
            "gs_profiling_agent": None,  # Usa el objeto y el punto
            "gs_metrics_config_agent": view_data_obj.gs_metrics_config_agent,  # Usa el objeto y el punto
            "gs_semantic_config": view_data_obj.gs_semantic_config,  # Repite profiling
            "metrics_access": view_data_obj.metrics_access,  # Usa el objeto y el punto
            "role_name": view_data_obj.name_rol_datos,  # Usa el objeto y el punto
            "data_access": view_data_obj.data_access,  # Usa el objeto y el punto
            "alert_event": True,
            "alert_config": final_alert_config,
            "table_names": view_data_obj.tables_name,
            "search_knowledge_config": view_data_obj.search_knowledge_config,
            "config_connection": view_data_obj.config_connection,
        }

        print(
            f"  -> Body construido para alerta {alert_id}: {json.dumps(body_data, indent=2)}"
        )

        # --- 3. Enviar la Solicitud al Endpoint /chat ---
        async with aiohttp.ClientSession() as session:
            print(f"  -> Enviando solicitud POST a {CHAT_ENDPOINT_URL}...")
            async with session.post(CHAT_ENDPOINT_URL, json=body_data) as response:
                response_text = await response.text()
                if response.status >= 200 and response.status < 300:
                    print(
                        f"  -> Solicitud para alerta {alert_id} enviada con éxito (Status: {response.status}). Respuesta: {response_text[:200]}..."
                    )  # Muestra solo parte de la respuesta
                    # 4. Registrar Éxito (Actualizar estado_ejecucion a 'COMPLETADO')
                    # await execute_update("UPDATE alerts_prompts SET estado_ejecucion='COMPLETADO', updated_at=NOW() WHERE id = %s", (alert_id,))
                    print(f"  -> Alerta {alert_id} marcada como COMPLETA.")
                else:
                    print(
                        f"  -> ERROR al enviar solicitud para alerta {alert_id} (Status: {response.status}). Respuesta: {response_text}"
                    )
                    # 5. Registrar Fallo (Actualizar estado_ejecucion a 'ERROR')
                    # await execute_update("UPDATE alerts_prompts SET estado_ejecucion='ERROR', updated_at=NOW() WHERE id = %s", (alert_id,))
                    print(f"  -> Alerta {alert_id} marcada como ERROR.")

    except aiohttp.ClientError as http_err:
        print(
            f"  -> ERROR de conexión al llamar a {CHAT_ENDPOINT_URL} para alerta {alert_id}: {http_err}"
        )
    except Exception as e:
        print(f"  -> ERROR inesperado durante la ejecución de alerta {alert_id}: {e}")


async def check_and_execute_alerts():
    """
    Consulta la BD, valida el CRON en la zona horaria de Lima (UTC-5)
    y ejecuta las alertas coincidentes.
    """
    print("--- INICIO DEL CICLO DE ALERTA ---")
    LOCAL_TZ = pytz.timezone("America/Lima")
    # LOCAL_TZ = pytz.timezone("America/Santiago")

    # 1. Determinar el tiempo de chequeo
    now_utc = datetime.now(timezone.utc)
    now_truncated = now_utc.replace(second=0, microsecond=0)

    # 2. Conversión a la zona horaria local (Lima)
    base_local_aware = now_truncated.astimezone(LOCAL_TZ)

    # 3. Preparar la base para croniter (naive y retrocedida 1s)
    # Convertimos a naive (sin TZ) para la comparación estricta de croniter
    expected_next_run = base_local_aware.replace(tzinfo=None)

    # Retrocedemos la base 1s para asegurar que get_next devuelva el minuto actual si coincide
    base_check_naive = expected_next_run - timedelta(seconds=1)

    # 4. Obtener alertas
    alerts = get_list_alerts()  # Esto devuelve List[ListAlerts]

    # Contadores
    total_alerts_checked = len(alerts)
    alerts_to_run_count = 0
    tasks = []

    print(f"Verificando {total_alerts_checked} alertas activas en la base de datos...")
    print(f"Hora de chequeo (Lima): {base_local_aware.isoformat()}")

    for alert in alerts:
        try:
            # Validar Vigencia de alerta
            if alert.fecha_fin:
                limit_time = alert.fecha_fin
                # Paso crítico: Normalizar zona horaria
                # Si la fecha viene de la BD sin zona horaria (naive),
                # asumimos que está guardada en hora local.
                if limit_time.tzinfo is None:
                    limit_time = LOCAL_TZ.localize(limit_time)
                else:
                    # Si ya tiene zona horaria, la convertimos a Chile para comparar peras con peras
                    limit_time = limit_time.astimezone(LOCAL_TZ)

                # Comparación precisa (incluye horas, minutos, segundos)
                # Si "ahora" es mayor que el "limite", la alerta expiró.
                if base_local_aware > limit_time:
                    print(f"ALERTA VENCIDA: {alert.id}. Expiró: {limit_time}")
                    continue

            cron_schedule = alert.codigo_cron

            # Inicializamos croniter con la base local retrocedida
            c = croniter(cron_schedule, base_check_naive)

            # Obtenemos la PRÓXIMA ejecución (será naive)
            next_execution = c.get_next(datetime)

            # 5. Comparar la próxima ejecución (next_execution) con la hora actual esperada (expected_next_run)
            if next_execution == expected_next_run:
                print(f"CRON COINCIDE: Alerta {alert.id} ({alert.codigo_cron})")

                # Ejecutar la tarea pesada de forma asíncrona
                task = execute_single_alert(alert, now_truncated)
                tasks.append(task)
                alerts_to_run_count += 1
            else:
                # Log de diagnóstico: muestra qué hora esperaba y qué obtuvo croniter
                print(
                    f"CRON NO COINCIDE: Alerta {alert.id} ({alert.codigo_cron}). "
                    f"Próxima ejecución: {next_execution.isoformat()}. "
                    f"Hora esperada: {expected_next_run.isoformat()}"
                )

        except Exception as e:
            print(f"ERROR al evaluar CRON para alerta {alert.id}: {e}")

    # [2] Verificación y Ejecución de Tareas
    if tasks:
        print(f"Ejecutando {alerts_to_run_count} tareas de alertas coincidentes...")
        await asyncio.gather(*tasks)
    else:
        # Log si no hay alertas para ejecutar
        print(
            f"Finalizó la verificación de {total_alerts_checked} alertas. Ninguna coincidió con el cron actual."
        )

    print("--- FIN DEL CICLO DE ALERTA ---")


def get_list_alerts() -> List[ListAlerts]:
    """
    Busca todas las alertas habilitadas en la base de datos.

    NOTA: Reemplazar con tu lógica real de conexión a la BD.
    """
    query_str = """
        SELECT 
            id, 
            product_id, 
            prompt_alerta, 
            codigo_cron, 
            session_id, 
            user_id, 
            type_alert, 
            configuration_alert,
            fecha_fin ,
            fecha_fin 
        FROM  view_info_alerts_execute 
    """
    rows = query_all(query_str)

    # Mapeo de los resultados de la DB al modelo Pydantic
    return [ListAlerts(**r) for r in rows]


def get_list_alerts_by_id(product_id: str) -> List[ListAlerts]:
    """
    Busca todas las alertas para un id product en la BDD
    """

    query_str = """
        SELECT * 
        FROM spu_minddash_app_get_alertas_by_id(%s);
    """

    params = (product_id,)

    try:
        rows = query_all(query_str, params)  # usa tu método propio
        # Convertimos cada fila al modelo Pydantic
        return [ListAlerts.model_validate(row) for row in rows]
    except Exception as e:
        raise e


def fetch_enabled_alerts_() -> List[Dict[str, Any]]:
    """
    Busca todas las alertas habilitadas en la base de datos.

    NOTA: Reemplazar con tu lógica real de conexión a la BD.
    """
    query = """
        SELECT 
            id, product_id, prompt_alerta, codigo_cron, session_id id
        FROM 
            alerts_prompts 
        WHERE 
            flg_habilitado = TRUE;
    """
    # Asume que execute_fetch_all ejecuta la consulta y devuelve una lista de diccionarios.
    # return execute_fetch_all(query)

    # ***SIMULACIÓN DE DATOS (REEMPLAZAR)***
    return [
        {
            "id": UUID("a1b2c3d4-e5f6-4799-9b01-844172b6a3cd"),
            "product_id": UUID("b1c2d3e4-f6g7-4800-9b01-844172b6a3cd"),
            "prompt_alerta": "Verificar stock crítico en almacén principal.",
            "codigo_cron": "*/5 * * * *",  # Cada 5 minutos
        },
        {
            "id": UUID("f1a2b3c4-d5e6-4799-9b01-844172b6a3cd"),
            "product_id": UUID("g1h2i3j4-k5l6-4800-9b01-844172b6a3cd"),
            "prompt_alerta": "Generar informe de uso de recursos.",
            "codigo_cron": "0 9 * * *",  # Diariamente a las 9:00 AM
        },
    ]


def dispatch_alerts_to_pubsub() -> Dict[str, Any]:
    """
    Función central del Dispatcher.
    1. Consulta alertas activas.
    2. Valida cuáles deben ejecutarse ahora (según CRON).
    3. Envía mensajes a Pub/Sub.
    """
    now_utc = datetime.now(timezone.utc)
    # Trunca al minuto exacto para asegurar coincidencia con cron
    now_truncated = now_utc.replace(second=0, microsecond=0)

    alerts = get_list_alerts()
    dispatched_count = 0

    logger.info(
        "Iniciando despacho para el minuto: %s (UTC)", now_truncated.isoformat()
    )

    for alert in alerts:
        try:
            cron_schedule = alert["codigo_cron"]

            # Usar croniter para validar si la hora actual coincide con el CRON
            # Necesitamos encontrar la ejecución cron *más cercana* al pasado
            base = now_truncated.replace(
                tzinfo=None
            )  # Croniter trabaja con naive datetime
            c = croniter(cron_schedule, base)

            # Obtener la ejecución anterior (el minuto que acaba de pasar)
            prev_execution = c.get_prev(datetime)

            # Verificar si la ejecución CRON anterior es exactamente el minuto actual
            if prev_execution == base:
                # Prepara el mensaje con la información de la alerta
                message_data = {
                    "alert_id": str(alert["id"]),
                    "product_id": str(alert["product_id"]),
                    "prompt": alert["prompt_alerta"],
                    "scheduled_time_utc": now_truncated.isoformat(),
                }

                message_json = json.dumps(message_data).encode("utf-8")

                # Envía a Pub/Sub
                future = PUBSUB_PUBLISHER.publish(PUBSUB_TOPIC_PATH, message_json)
                future.add_done_callback(
                    lambda f: (
                        logger.info(
                            "Mensaje de alerta %s enviado con éxito.", alert["id"]
                        )
                        if not f.exception()
                        else logger.error(
                            "Fallo al enviar alerta %s: %s", alert["id"], f.exception()
                        )
                    )
                )
                dispatched_count += 1

        except Exception as e:
            logger.error(
                "Error al procesar alerta %s con CRON '%s': %s",
                alert["id"],
                alert["codigo_cron"],
                e,
            )

    return {
        "status": "success",
        "total_alerts_checked": len(alerts),
        "total_dispatched": dispatched_count,
    }


def process_alert_message(data: bytes):
    """
    Función del Worker. Se ejecuta para CADA mensaje de Pub/Sub.
    Aquí va la lógica pesada (evaluar, notificar, etc.).
    """
    try:
        alert_data = json.loads(data.decode("utf-8"))
        alert_id = alert_data.get("alert_id")

        # --- Lógica de Negocio y Bloqueo (Worker) ---

        # 1. Bloqueo en BD (Implementar lógica de bloqueo aquí usando alert_id)
        # if not attempt_db_lock(alert_id, alert_data["scheduled_time_utc"]):
        #     logger.warning("Alerta %s ya está en ejecución o fue completada.", alert_id)
        #     return # Salir si ya está bloqueada

        logger.info(
            "INICIANDO EJECUCIÓN de Alerta %s para Producto %s",
            alert_id,
            alert_data.get("product_id"),
        )

        # 2. Ejecutar Lógica
        # result = execute_alert_logic(alert_data["prompt"])

        # 3. Registrar éxito y liberar bloqueo
        # log_completion(alert_id)

        logger.info("Alerta %s completada con éxito.", alert_id)

    except Exception as e:
        logger.error("Error fatal en el Worker al procesar mensaje: %s", e)
        # IMPORTANTE: Si el Worker falla (lanza excepción), Pub/Sub intentará re-entregar.
        raise  # Re-lanzar para que Pub/Sub sepa que debe reintentar
