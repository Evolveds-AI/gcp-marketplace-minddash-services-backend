from fastapi import APIRouter, HTTPException, status
from dotenv import load_dotenv
import os

from api.models.channel_models import (
    ChannelCreationResponse,
    ChannelDeleteRequest,
    ChannelDeleteResponse,
    ChannelProductCreationResponse,
    ChannelProductDeleteRequest,
    ChannelProductDeleteResponse,
    ChannelProductRegisterRequest,
    ChannelProductUpdateRequest,
    ChannelProductUpdateResponse,
    ChannelRegisterRequest,
    ChannelUpdateRequest,
    ChannelUpdateResponse,
)
from api.services.channel_service import (
    send_delete_channel,
    send_delete_channel_product,
    send_register_channel,
    send_register_channel_product,
    send_update_channel,
    send_update_channel_product,
)

load_dotenv()

channel_router = APIRouter(prefix="/Channels")

# --- Rutas de FastAPI para Channel ---


# CREATE: Registrar Nuevo Canal
@channel_router.post(
    "/sendRegistroChannel",
    response_model=ChannelCreationResponse,
    tags=["Channel Management"],
    summary="Registrar Nuevo Canal (CREATE)",
    description="Crea un nuevo registro de canal en la base de datos.",
)
def sendRegistroChannel(
    channel_data: ChannelRegisterRequest,
) -> ChannelCreationResponse:
    try:
        # Llama a la función de servicio con los datos de registro
        result_message = send_register_channel(channel_data)

        # Construir y retornar la respuesta
        return ChannelCreationResponse(id_channel=result_message)

    except Exception as e:
        # Manejo de errores
        print(f"Error en sendRegistroChannel: {e}")
        # Puedes añadir un manejo específico si el error es de violación de restricción, etc.
        raise HTTPException(status_code=500, detail=f"Error al registrar el canal: {e}")


URL_CHANNELS = os.environ.get(
    "ENV_URL_CHANNELS",
    "https://webhook-msteams-dev-minddash-294493969622.us-central1.run.app",
)


##channel
# UPDATE: Actualizar Canal
@channel_router.put(
    "/SendUpdateChannel",
    response_model=ChannelUpdateResponse,
    tags=["Channel Management"],
    summary="Actualizar Canal (UPDATE)",
    description="Modifica los datos de un canal existente. Devuelve error 404 si el canal no existe.",
)
def updateChannel(channel_data: ChannelUpdateRequest) -> ChannelUpdateResponse:
    try:
        # 1. Ejecutar el servicio. Si el SP encuentra que el ID NO existe,
        #    lanza una excepción (RAISE EXCEPTION).
        rows_affected = send_update_channel(channel_data)

        # 2. Si llegamos hasta aquí, NO hubo una excepción.
        return ChannelUpdateResponse(channel_id=channel_data.id)

    except Exception as e:
        error_detail = str(e)

        # 3. Capturar el error del RAISE EXCEPTION del SP y convertirlo en 404
        if "ERROR: No se puede actualizar. El canal con ID" in error_detail:
            # Aquí usamos el 404. El error_detail contiene el mensaje que generó el SP
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_detail.split("ERROR: ")[-1],  # Extrae solo el mensaje
            )

        # 4. Cualquier otro error no manejado
        print(f"Error al actualizar el canal: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al actualizar el canal: {error_detail}",
        )


# DELETE: Eliminar Canal
@channel_router.delete(
    "/SendDeleteChannel",
    response_model=ChannelDeleteResponse,
    tags=["Channel Management"],
    summary="Eliminar Canal (DELETE)",
    description="Elimina un canal del sistema usando su `id`. Devuelve error 404 si el canal no existe.",
)
def deleteChannel(channel_data: ChannelDeleteRequest) -> ChannelDeleteResponse:
    chn_id = channel_data.id
    try:
        # Llama al servicio. Si el ID no existe, el SP lanza una excepción.
        send_delete_channel(channel_data)

        # Si llegamos aquí, NO hubo una excepción, la eliminación fue exitosa.
        return ChannelDeleteResponse(channel_id=chn_id)

    except Exception as e:
        error_detail = str(e)

        # 1. Capturar el error del RAISE EXCEPTION del SP y convertirlo en 404
        if "ERROR: No se puede eliminar. El canal con ID" in error_detail:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No se encontró el canal con ID: {chn_id} para eliminar.",
            )

        # 2. Cualquier otro error no manejado
        print(f"Error al eliminar el canal: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al eliminar el canal: {error_detail}",
        )


# CREATE: Registrar Nueva Relación
@channel_router.post(
    "/sendRegistroChannelProduct",
    response_model=ChannelProductCreationResponse,
    tags=["Channel Management"],
    summary="Registrar Nueva Relación Canal-Producto (CREATE)",
    description="Crea un nuevo registro de relación en la base de datos.",
)
def sendRegistroChannelProduct(
    cp_data: ChannelProductRegisterRequest,
) -> ChannelProductCreationResponse:
    try:
        result_id = send_register_channel_product(cp_data)

        if cp_data.channel_id == "cd816a77-d19b-4467-9809-d7dd646a3da8":
            url_channel = f"{URL_CHANNELS}/api/messages"
            url_webhook_channel = f"{url_channel}?id_channel_product={result_id}"
        elif cp_data.channel_id == "a00b0952-5bf6-4d8c-82cc-4111722d344f":
            url_channel = f"{URL_CHANNELS}/slack/events"
            url_webhook_channel = f"{url_channel}?id_channel_product={result_id}"
        else:
            url_channel = f"{URL_CHANNELS}/api/messages"
            url_webhook_channel = f"{url_channel}?id_channel_product={result_id}"

        return ChannelProductCreationResponse(
            id_channel_product=result_id, url_webhook_channel=url_webhook_channel
        )

    except Exception as e:
        error_detail = str(e)

        # Manejar errores de validación de FK o unicidad lanzados por el SP
        if (
            "ERROR: El producto con ID" in error_detail
            or "ERROR: El canal con ID" in error_detail
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error de validación de IDs: {error_detail.split('ERROR: ')[-1].strip()}",
            )
        if "ERROR: La relación entre el canal" in error_detail:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,  # 409 Conflict para duplicados
                detail=f"Relación ya existe: {error_detail.split('ERROR: ')[-1].strip()}",
            )

        print(f"Error en sendRegistroChannelProduct: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error al registrar la relación: {error_detail}"
        )


# UPDATE: Actualizar Relación
@channel_router.put(
    "/updateChannelProduct",
    response_model=ChannelProductUpdateResponse,
    tags=["Channel Management"],
    summary="Actualizar Relación Canal-Producto (UPDATE)",
    description="Modifica un registro de relación existente. Devuelve error 404 si el ID no existe.",
)
def updateChannelProduct(
    cp_data: ChannelProductUpdateRequest,
) -> ChannelProductUpdateResponse:
    try:
        send_update_channel_product(cp_data)

        if cp_data.channel_id == "cd816a77-d19b-4467-9809-d7dd646a3da8":
            url_channel = f"{URL_CHANNELS}/api/messages"
            url_webhook_channel = f"{url_channel}?id_channel_product={cp_data.id}"
        elif cp_data.channel_id == "a00b0952-5bf6-4d8c-82cc-4111722d344f":
            url_channel = f"{URL_CHANNELS}/slack/events"
            url_webhook_channel = f"{url_channel}?id_channel_product={cp_data.id}"
        else:
            url_channel = f"{URL_CHANNELS}/api/messages"
            url_webhook_channel = f"{url_channel}?id_channel_product={cp_data.id}"

        return ChannelProductUpdateResponse(
            channel_product_id=cp_data.id, url_webhook_channel=url_webhook_channel
        )

    except Exception as e:
        error_detail = str(e)

        # Capturar el error del RAISE EXCEPTION del SP y convertirlo en 404
        if "ERROR: El registro de relación con ID" in error_detail:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_detail.split("ERROR: ")[-1].strip(),
            )

        # Manejar errores de validación de FK o unicidad
        if (
            "ERROR: El producto con ID" in error_detail
            or "ERROR: El canal con ID" in error_detail
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error de validación de IDs: {error_detail.split('ERROR: ')[-1].strip()}",
            )

        print(f"Error al actualizar la relación: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al actualizar la relación: {error_detail}",
        )


# DELETE: Eliminar Relación
@channel_router.delete(
    "/deleteChannelProduct",
    response_model=ChannelProductDeleteResponse,
    tags=["Channel Management"],
    summary="Eliminar Relación Canal-Producto (DELETE)",
    description="Elimina un registro de relación usando su `id`. Devuelve error 404 si el ID no existe.",
)
def deleteChannelProduct(
    cp_data: ChannelProductDeleteRequest,
) -> ChannelProductDeleteResponse:
    cp_id = cp_data.id
    try:
        send_delete_channel_product(cp_data)

        return ChannelProductDeleteResponse(channel_product_id=cp_id)

    except Exception as e:
        error_detail = str(e)

        # Capturar el error del RAISE EXCEPTION del SP y convertirlo en 404
        if (
            "ERROR: No se puede eliminar. El registro de relación con ID"
            in error_detail
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No se encontró la relación con ID: {cp_id} para eliminar.",
            )

        print(f"Error al eliminar la relación: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al eliminar la relación: {error_detail}",
        )
