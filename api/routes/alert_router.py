import asyncio
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from api.models.alert_models import (
    AlertCreationResponse,
    AlertDeleteRequest,
    AlertDeleteResponse,
    AlertListResponse,
    AlertRegisterRequest,
    AlertUpdateRequest,
    AlertUpdateResponse,
    # Alert,
    SendAlertRequest,
    SendAlertResponse,
)
from api.services.alert_service import (
    check_and_execute_alerts,
    get_list_alerts_by_id,
    process_and_send_alert,
    send_delete_alert,
    send_register_alert,
    send_update_alert,
)

logger = logging.getLogger(__name__)

alert_router = APIRouter(prefix="/alert", tags=["Alertas y Monitoreo"])


class CreateAlertResponse(BaseModel):
    id: str


"""
    Ejecucion del envio de las alertas: 
"""


@alert_router.post(
    "/sendAlerts",
    response_model=SendAlertResponse,
    tags=["Alertas y Monitoreo"],
    summary="Enviar las alertas via canales de notificación",
    description=(
        """Envia las alertas via el canal configurado en la alerta. 
        Devuelve el identificador único (`id`) de la alerta creada."""
    ),
)
def post_send_alert(alert_data: SendAlertRequest) -> SendAlertResponse:
    """
    Endpoint para recibir la solicitud de alerta y delegar el envío.
    """
    try:
        # 1. Llama al servicio. El servicio devuelve un Dict compatible con SendAlertResponse.
        response_data = process_and_send_alert(alert_data)

        # 2. El endpoint retorna el Dict. Pydantic lo valida y lo mapea a SendAlertResponse.
        return response_data

    except Exception as e:
        # 3. Manejo de errores de tiempo de ejecución no esperados (ej. Base de Datos, conexión)
        # Es mejor devolver un HTTP 500 para errores internos
        raise HTTPException(
            status_code=500,
            detail=f"Error interno del servidor no controlado durante el envío de alerta: {str(e)}",
        )


"""
    Ejecucion de la alerta 
"""


@alert_router.post(
    "/sendAlerts",
    response_model=SendAlertResponse,
    tags=["Alertas y Monitoreo"],
    summary="Crear Nueva Alerta via canales de notificación",
    description=(
        """Envia la informacion a la BD para crear la instancia de la alerta. 
        Devuelve el identificador único (`id`) de la alerta creada"""
    ),
)
def post_create_alert(alert_data: SendAlertRequest) -> SendAlertResponse:
    """
    Endpoint para recibir la solicitud de alerta y delegar el envío.
    """
    try:
        # 1. Llama al servicio. El servicio devuelve un Dict compatible con SendAlertResponse.
        response_data = process_and_send_alert(alert_data)

        # 2. El endpoint retorna el Dict. Pydantic lo valida y lo mapea a SendAlertResponse.
        return response_data

    except Exception as e:
        # 3. Manejo de errores de tiempo de ejecución no esperados (ej. Base de Datos, conexión)
        # Es mejor devolver un HTTP 500 para errores internos
        raise HTTPException(
            status_code=500,
            detail=f"Error interno del servidor no controlado durante el envío de alerta: {str(e)}",
        )


"""
    Registro y Actualizacion de datos alertas
"""


@alert_router.post(
    "/executeAlerts",
    tags=["Runner"],
    summary="Ejecutar todas las alertas programadas",
    description="Endpoint llamado por Cloud Scheduler. Inicia la ejecución de alertas en segundo plano.",
)
async def execute_all_alerts_endpoint():
    """
    Recibe la llamada del Scheduler, inicia la lógica de alertas en segundo plano,
    y devuelve una respuesta 200 OK inmediatamente.
    """
    try:
        # Crea una tarea asíncrona para ejecutar la lógica principal en el fondo
        asyncio.create_task(check_and_execute_alerts())

        # Responde inmediatamente para evitar el timeout del Scheduler
        return {
            "status": "PROCESSING",
            "message": "La ejecución de alertas ha sido iniciada en segundo plano.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.error("Error al iniciar el proceso de ejecución de alertas: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al iniciar el proceso de alertas: {str(e)}",
        )


"""
    Registro y Actualizacion de datos alertas Alt1
"""
# --- 1. REGISTRO (POST) ---
# @alert_router.post(
#     '/sendRegistroAlerta',
#     response_model=AlertCreationResponse,
#     summary="Registrar Nueva Alerta (CREATE)",
#     description="Crea un nuevo registro de alerta en la base de datos."
# )
# def sendRegistroAlerta(alert_data: AlertRegisterRequest) -> AlertCreationResponse:
#     try:
#         # Llama a la función de servicio con los datos de registro
#         result_id = send_register_alert(alert_data)

#         # Construir y retornar la respuesta
#         return AlertCreationResponse(id_alerta=result_id)

#     except Exception as e:
#         print(f"Error en sendRegistroAlerta: {e}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Error al registrar la alerta: {e}"
#         )


@alert_router.post(
    "/sendRegistroAlerta",
    response_model=AlertCreationResponse,
    summary="Registrar Nueva Alerta (CREATE)",
    description="Crea un nuevo registro de alerta en la base de datos.",
)
def sendRegistroAlerta(alert_data: AlertRegisterRequest) -> AlertCreationResponse:
    try:
        # Llama a la función de servicio
        result_id = send_register_alert(alert_data)

        return AlertCreationResponse(id_alerta=result_id)

    except Exception as e:
        error_message = str(e)
        print(f"Error en sendRegistroAlerta: {error_message}")

        # --- VALIDACIÓN DE ERRORES DE NEGOCIO (Base de Datos) ---

        # Detectar el mensaje específico que pusimos en el Stored Procedure
        if "Límite alcanzado" in error_message:
            # Opción A: Extraer el mensaje limpio (quitando ruido técnico de la BD si es necesario)
            # O simplemente devolver un mensaje amigable fijo.
            user_msg = "No se pudo registrar: Has superado el límite máximo de 3 alertas para este producto."

            # Lanzamos un 400 Bad Request (o 409 Conflict)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=user_msg
            )

        # --- ERRORES NO CONTROLADOS ---
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al registrar la alerta: {error_message}",
        )


# --- 2. ACTUALIZACIÓN (PUT) ---
@alert_router.put(
    "/updateAlerta",
    response_model=AlertUpdateResponse,
    summary="Actualizar Alerta (UPDATE)",
    description="Modifica los datos de una alerta existente.",
)
def updateAlerta(alert_data: AlertUpdateRequest) -> AlertUpdateResponse:
    try:
        # El servicio ejecuta el SP. El SP lanzaría una excepción si el ID no existe.
        send_update_alert(alert_data)

        # Si no hay excepción, es exitoso.
        return AlertUpdateResponse(id_alerta=str(alert_data.id))

    except Exception as e:
        error_detail = str(e)

        # Capturar el error del RAISE EXCEPTION del SP
        # (Ajusta la cadena a lo que realmente devuelve tu SP en caso de no encontrar el ID)
        if "No se puede actualizar. La alerta con ID" in error_detail:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_detail.split("ERROR: ")[-1],
            )

        print(f"Error al actualizar la alerta: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al actualizar la alerta: {error_detail}",
        )


# --- 3. ELIMINACIÓN (DELETE) ---
@alert_router.delete(
    "/deleteAlerta",
    response_model=AlertDeleteResponse,
    summary="Eliminar Alerta (DELETE)",
    description="Elimina una alerta del sistema usando su `id`.",
)
def deleteAlerta(alert_data: AlertDeleteRequest) -> AlertDeleteResponse:
    alert_id = alert_data.id
    try:
        # Llama al servicio. El SP lanzaría una excepción si el ID no existe.
        send_delete_alert(alert_data)

        # Si llega aquí, la eliminación fue exitosa.
        return AlertDeleteResponse(id_alerta=str(alert_id))

    except Exception as e:
        error_detail = str(e)

        # Capturar el error del RAISE EXCEPTION del SP
        if "No se puede eliminar. La alerta con ID" in error_detail:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No se encontró la alerta con ID: {alert_id} para eliminar.",
            )

        print(f"Error al eliminar la alerta: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al eliminar la alerta: {error_detail}",
        )


@alert_router.post(
    "/getAlertsByProduct",
    response_model=AlertListResponse,
    summary="Trae alertas en base a un id producto",
)
def get_alerts(product_id: str) -> AlertListResponse:
    try:
        alerts = get_list_alerts_by_id(product_id)

        if not alerts:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No se encontraron alertas con product_id={product_id}",
            )

        return AlertListResponse(alerts=alerts)

    except Exception as e:
        error_detail = str(e)
        print(f"Error al traer alertas: {error_detail}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al traer alertas: {error_detail}",
        )


# # Este es el endpoint que Pub/Sub llama por default
# @alert_router.post(
#     '/sendEjecucionAlertas',
#     response_model=AlertDeleteResponse,
#     summary="Eliminar Alerta (DELETE)",
#     description="Recibe los mensajes del pubsub y envia al agente la instruccion para ejecutar la alerta."
# )
# def pubsub_worker_handler():
#     # 1. Verifica si la solicitud proviene de Pub/Sub
#     if 'X-Goog-Pubsub-Subscription' not in request.headers:
#         logger.warning("Llamada no autorizada o no proveniente de Pub/Sub.")
#         return ('Bad Request: Not a Pub/Sub message', 400)

#     # 2. Desempaqueta el mensaje de Pub/Sub
#     envelope = request.get_json()
#     if not envelope or 'message' not in envelope:
#         return ('No Pub/Sub message received', 204) # No hacer nada

#     pubsub_message = envelope['message']

#     # El cuerpo del mensaje de Pub/Sub está codificado en Base64
#     if 'data' in pubsub_message:
#         message_data_b64 = pubsub_message['data']
#         message_data = base64.b64decode(message_data_b64)

#         # 3. Llama a la lógica del procesador
#         process_alert_message(message_data)

#         # 4. Éxito (Importante: Pub/Sub requiere 200 OK para saber que el mensaje fue procesado)
#         return ('', 204)

#     return ('No data in message', 204)


# @alert_router.post(
#     '/sendMessagePubSubAlert',
#     tags=['Orchestration'],
#     summary="Disparar la Orquestación de Alertas",
#     description="Endpoint llamado por Cloud Scheduler para validar y enviar alertas a Pub/Sub."
# )
# def dispatch_alerts_endpoint():
# """
# Este endpoint se ejecuta de forma síncrona, llama al servicio Dispatcher
# y retorna inmediatamente.
# """
# try:
#     # Llama a la lógica central de despacho
#     # Nota: La librería de Pub/Sub maneja el envío de forma asíncrona,
#     # pero esta función se mantiene síncrona para ser llamada directamente.
#     result = dispatch_alerts_to_pubsub()

#     return {
#         "status": "OK",
#         "message": f"Despacho iniciado. Se enviaron {result['total_dispatched']} mensajes a Pub/Sub.",
#         "details": result
#     }

# except Exception as e:
#     logger.error("Error en el endpoint de despacho: %s", e)
#     raise HTTPException(
#         status_code=500,
#         detail=f"Error interno al iniciar el despacho de alertas: {str(e)}"
#     )
