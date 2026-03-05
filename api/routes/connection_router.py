from typing import List

from fastapi import APIRouter, HTTPException, status

from api.models.connection_models import (
    DataConnectionByOrganization,
    DataConnectionCreationResponse,
    DataConnectionDeleteRequest,
    DataConnectionDeleteResponse,
    DataConnectionRegisterRequest,
    DataConnectionResponse,
    DataConnectionUpdateRequest,
    DataConnectionUpdateResponse,
    GetDataConnectionsByOrganizationRequest,
    GetDataConnectionsRequest,
)
from api.services.connection_service import (
    get_data_connections,
    get_data_connections_by_organization,
    send_delete_data_connection,
    send_register_data_connection,
    send_update_data_connection,
)

connection_router = APIRouter(prefix="/connections")


@connection_router.post(
    "/getDataConnectionsByOrganization",
    response_model=List[DataConnectionByOrganization],
    tags=["Connections Management"],
    summary="Listar Conexiones por Organización",
    description="Obtiene todas las conexiones de datos que han sido asociadas a una **organización** específica, filtrando por el `organization_id` provisto.",
)
def getDataConnectionsByOrganization(
    request_body: GetDataConnectionsByOrganizationRequest,
) -> List[DataConnectionByOrganization]:
    """
    Obtiene todas las conexiones de datos de una organización específica,
    filtrando por el organization_id proporcionado en el cuerpo de la solicitud.
    """
    try:
        # Llama a la función de servicio pasando el request completo
        return get_data_connections_by_organization(request_body)

    except Exception as e:
        # Manejo de errores
        raise HTTPException(status_code=500, detail=f"Error al obtener conexiones: {e}")


@connection_router.post(
    "/getDataConnections",
    response_model=List[DataConnectionResponse],
    tags=["Connections Management"],
    summary="Listar Conexiones (Todas o por ID)",
    description="Obtiene una lista de todas las conexiones registradas. Opcionalmente, si se proporciona un `connection_id` en el cuerpo, devuelve solo los detalles de esa conexión específica.",
)
def getDataConnections(
    request_body: GetDataConnectionsRequest,
) -> List[DataConnectionResponse]:
    """
    Obtiene todas las conexiones de datos o una específica por ID.
    Si se proporciona connection_id en el body, retorna solo esa conexión.
    Si no se proporciona connection_id, retorna todas las conexiones.
    """
    try:
        # Llama a la función de servicio pasando el request completo
        return get_data_connections(request_body)

    except Exception as e:
        # Manejo de errores
        raise HTTPException(status_code=500, detail=f"Error al obtener conexiones: {e}")


@connection_router.post(
    "/sendRegistroConnection",
    response_model=DataConnectionCreationResponse,
    tags=["Connections Management"],
    summary="Registrar Nueva Conexión (CREATE)",
    description="Crea y registra una nueva conexión a una fuente de datos en la base de datos.",
)
def sendRegistroConnection(
    connection_data: DataConnectionRegisterRequest,
) -> DataConnectionCreationResponse:
    """
    Endpoint para registrar una nueva conexión de datos.
    """
    try:
        # Llama a la función de servicio con los datos de registro
        result_message = send_register_data_connection(connection_data)

        # Construir y retornar la respuesta
        return DataConnectionCreationResponse(id_connection=result_message)

    except Exception as e:
        # Manejo de errores
        print(f"Error en sendRegistroConnection: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error al registrar la conexión: {e}"
        )


@connection_router.put(
    "/updateConnection",
    response_model=DataConnectionUpdateResponse,
    tags=["Connections Management"],
    summary="Actualizar Conexión (UPDATE)",
    description="Modifica los detalles de una conexión de datos existente. Devuelve error 404 si el `id` de la conexión no existe.",
)
def updateConnection(
    connection_data: DataConnectionUpdateRequest,
) -> DataConnectionUpdateResponse:
    """
    Endpoint para actualizar una conexión de datos existente.
    """
    try:
        # 1. Ejecutar el servicio. Si el SP encuentra que el ID NO existe,
        #    lanza una excepción (RAISE EXCEPTION).
        #    Si el ID SÍ existe, devuelve -1 (rowcount).
        rows_affected = send_update_data_connection(connection_data)

        # 2. Si llegamos hasta aquí, NO hubo una excepción, por lo que la operación fue exitosa.
        #    No importa si rows_affected es 1 o -1.
        return DataConnectionUpdateResponse(connection_id=connection_data.id)

    except Exception as e:
        error_detail = str(e)

        # 3. Capturar el error del RAISE EXCEPTION del SP y convertirlo en 404
        # Esto sucede cuando el ID no existe en la BD.
        if "No se puede actualizar. La conexión con ID" in error_detail:
            # Aquí usamos el 404. El error_detail contiene el mensaje que generó el SP
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_detail.split("ERROR: ")[-1],  # Extrae solo el mensaje
            )

        # 4. Cualquier otro error no manejado
        print(f"Error al actualizar la conexión: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al actualizar la conexión: {error_detail}",
        )


@connection_router.delete(
    "/deleteConnection",
    response_model=DataConnectionDeleteResponse,
    tags=["Connections Management"],
    summary="Eliminar Conexión (DELETE)",
    description="Elimina una conexión de datos del sistema. Devuelve error 404 si el `id` de la conexión no existe.",
)
def deleteConnection(
    connection_data: DataConnectionDeleteRequest,
) -> DataConnectionDeleteResponse:
    """
    Endpoint para eliminar una conexión de datos existente.
    """
    connection_id = connection_data.id
    try:
        # Llama al servicio. Si el ID no existe, el SP lanza una excepción.
        send_delete_data_connection(connection_data)

        # Si llegamos aquí, NO hubo una excepción, la eliminación fue exitosa (rowcount = -1).
        return DataConnectionDeleteResponse(connection_id=connection_id)

    except Exception as e:
        error_detail = str(e)

        # 1. Capturar el error del RAISE EXCEPTION del SP y convertirlo en 404
        if "No se puede eliminar. La conexión con ID" in error_detail:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No se encontró la conexión con ID: {connection_id} para eliminar.",
            )

        # 2. Cualquier otro error no manejado
        print(f"Error al eliminar la conexión: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al eliminar la conexión: {error_detail}",
        )
