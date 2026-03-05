from typing import List

from fastapi import APIRouter, HTTPException

from api.models.user_models import GetUserRequest, UserBaseInfoResponse
from api.services.user_service import get_list_info_by_user

user_router = APIRouter(prefix="/users")


@user_router.post(
    "/getInfoByUser",
    response_model=List[UserBaseInfoResponse],
    tags=["Users Management"],
    summary="Obtener Información Base de Usuario por ID",
    description="Recupera la información general de un usuario (incluyendo detalles de acceso o *metadata* básica) utilizando su `user_id` proporcionado en el cuerpo de la solicitud.",
)
def getListProjectByUser(request_body: GetUserRequest) -> List[UserBaseInfoResponse]:
    """
    Obtiene la informacion General de los usuarios
    """
    try:
        # Extrae y valida el user_id del cuerpo
        user_id = request_body.user_id

        # Llama a la función de servicio
        return get_list_info_by_user(user_id=user_id)

    except Exception as e:
        # Manejo de errores
        raise HTTPException(
            status_code=500, detail=f"Error al obtener informacion del usuario: {e}"
        )
