from typing import List

from fastapi import APIRouter, HTTPException, status

from api.models.data_access_models import (
    ClientDeployCreationResponse,
    ClientDeployDeleteRequest,
    ClientDeployDeleteResponse,
    ClientDeployListResponse,
    ClientDeployRegisterRequest,
    ClientDeployUpdateRequest,
    ClientDeployUpdateResponse,
    GetClientDeployByProductRequest,
    GetClientDeployRequest,
    GetRolesDataAccessByProductRequest,
    GetRolesDataAccessRequest,
    GetUserDataAccessByRoleRequest,
    GetUserDataAccessByUserRequest,
    GetUserDataAccessRequest,
    RoleDataAccessByProduct,
    RoleDataAccessCreationResponse,
    RoleDataAccessDeleteRequest,
    RoleDataAccessDeleteResponse,
    RoleDataAccessRegisterRequest,
    RoleDataAccessResponse,
    RoleDataAccessUpdateRequest,
    RoleDataAccessUpdateResponse,
    UserDataAccessByRole,
    UserDataAccessByUser,
    UserDataAccessCreationResponse,
    UserDataAccessDeleteRequest,
    UserDataAccessDeleteResponse,
    UserDataAccessRegisterRequest,
    UserDataAccessResponse,
    UserDataAccessUpdateRequest,
    UserDataAccessUpdateResponse,
)
from api.services.data_access_service import (
    get_client_deploys,
    get_client_deploys_by_product,
    get_roles_data_access,
    get_roles_data_access_by_product,
    get_user_data_access,
    get_user_data_access_by_role,
    get_user_data_access_by_user,
    send_delete_client_deploy,
    send_delete_role_data_access,
    send_delete_user_data_access,
    send_register_client_deploy,
    send_register_client_deploy_v2,
    send_register_role_data_access,
    send_register_user_data_access,
    send_update_client_deploy,
    send_update_role_data_access,
    send_update_user_data_access,
)

data_access_router = APIRouter(prefix="/user-data-access")

"""
    Gestion de acceso a tabla usuario
"""


@data_access_router.post(
    "/getUserDataAccess",
    response_model=List[UserDataAccessResponse],
    tags=["User Data Access"],
    summary="Listar Acceso a Datos (Todos o por ID)",
    description="Obtiene todos los registros de acceso a datos de usuario, o uno específico si se proporciona `user_data_access_id`.",
)
def getUserDataAccess(
    request_body: GetUserDataAccessRequest,
) -> List[UserDataAccessResponse]:
    """
    Obtiene todos los accesos de datos de usuario o uno específico por ID.
    Si se proporciona user_data_access_id en el body, retorna solo ese acceso.
    Si no se proporciona user_data_access_id, retorna todos los accesos.
    """
    try:
        # Llama a la función de servicio pasando el request completo
        return get_user_data_access(request_body)

    except Exception as e:
        # Manejo de errores
        raise HTTPException(
            status_code=500, detail=f"Error al obtener accesos de datos de usuario: {e}"
        )


@data_access_router.post(
    "/getUserDataAccessByRole",
    response_model=List[UserDataAccessByRole],
    tags=["User Data Access"],
    summary="Listar Acceso a Datos por Rol",
    description="Obtiene la lista de registros de acceso a datos de usuario que están asociados a un `role_id` específico.",
)
def getUserDataAccessByRole(
    request_body: GetUserDataAccessByRoleRequest,
) -> List[UserDataAccessByRole]:
    """
    Obtiene la lista de accesos de datos de usuario de un rol específico.
    """
    try:
        # Llama a la función de servicio pasando el request completo
        return get_user_data_access_by_role(request_body)

    except Exception as e:
        # Manejo de errores
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener accesos de datos de usuario por rol: {e}",
        )


@data_access_router.post(
    "/getUserDataAccessByUser",
    response_model=List[UserDataAccessByUser],
    tags=["User Data Access"],
    summary="Listar Acceso a Datos por Usuario",
    description="Obtiene la lista de registros de acceso a datos que están asociados a un `user_id` específico.",
)
def getUserDataAccessByUser(
    request_body: GetUserDataAccessByUserRequest,
) -> List[UserDataAccessByUser]:
    """
    Obtiene la lista de accesos de datos de usuario de un usuario específico.
    """
    try:
        # Llama a la función de servicio pasando el request completo
        return get_user_data_access_by_user(request_body)

    except Exception as e:
        # Manejo de errores
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener accesos de datos de usuario por usuario: {e}",
        )


@data_access_router.post(
    "/sendRegistroUserDataAccess",
    response_model=UserDataAccessCreationResponse,
    tags=["User Data Access"],
    summary="Registrar Acceso de Usuario (CREATE)",
    description="Crea un nuevo registro de acceso a datos detallado para un usuario.",
)
def sendRegistroUserDataAccess(
    request_body: UserDataAccessRegisterRequest,
) -> UserDataAccessCreationResponse:
    """
    Registra un nuevo acceso de datos de usuario.
    """
    try:
        # Llama a la función de servicio
        new_user_data_access_id = send_register_user_data_access(request_body)

        # Retorna la respuesta con el ID generado
        return UserDataAccessCreationResponse(
            id_user_data_access=new_user_data_access_id
        )

    except Exception as e:
        # Manejo de errores
        raise HTTPException(
            status_code=500,
            detail=f"Error al registrar acceso de datos de usuario: {e}",
        )


@data_access_router.put(
    "/updateUserDataAccess",
    response_model=UserDataAccessUpdateResponse,
    tags=["User Data Access"],
    summary="Actualizar Acceso de Usuario (UPDATE)",
    description="Modifica un registro de acceso a datos de usuario existente, identificado por su `id`.",
)
def updateUserDataAccess(
    request_body: UserDataAccessUpdateRequest,
) -> UserDataAccessUpdateResponse:
    """
    Actualiza un acceso de datos de usuario existente.
    """
    try:
        # Llama a la función de servicio
        send_update_user_data_access(request_body)

        # Retorna la respuesta con el ID actualizado
        return UserDataAccessUpdateResponse(user_data_access_id=request_body.id)

    except Exception as e:
        # Manejo de errores
        raise HTTPException(
            status_code=500,
            detail=f"Error interno al actualizar acceso de datos de usuario: {e}",
        )


@data_access_router.delete(
    "/deleteUserDataAccess",
    response_model=UserDataAccessDeleteResponse,
    tags=["User Data Access"],
    summary="Eliminar Acceso de Usuario (DELETE)",
    description="Elimina un registro de acceso a datos de usuario existente.",
)
def deleteUserDataAccess(
    request_body: UserDataAccessDeleteRequest,
) -> UserDataAccessDeleteResponse:
    """
    Elimina un acceso de datos de usuario.
    """
    try:
        # Llama a la función de servicio
        send_delete_user_data_access(request_body)

        # Retorna la respuesta con el ID eliminado
        return UserDataAccessDeleteResponse(user_data_access_id=request_body.id)

    except Exception as e:
        # Manejo de errores
        raise HTTPException(
            status_code=500,
            detail=f"Error interno al eliminar acceso de datos de usuario: {e}",
        )


"""
    Gestion de acceso a tabla roles
"""


@data_access_router.post(
    "/getRolesDataAccess",
    response_model=List[RoleDataAccessResponse],
    tags=["Role Data Access"],
    summary="Listar Roles de Acceso a Datos (Todos o por ID)",
    description="Obtiene todos los roles de acceso a datos o uno específico si se proporciona `role_id`.",
)
def getRolesDataAccess(
    request_body: GetRolesDataAccessRequest,
) -> List[RoleDataAccessResponse]:
    """
    Obtiene todos los roles de acceso a datos o uno específico por ID.
    Si se proporciona role_id en el body, retorna solo ese rol.
    Si no se proporciona role_id, retorna todos los roles.
    """
    try:
        # Llama a la función de servicio pasando el request completo
        return get_roles_data_access(request_body)

    except Exception as e:
        # Manejo de errores
        raise HTTPException(
            status_code=500, detail=f"Error al obtener roles de acceso a datos: {e}"
        )


@data_access_router.post(
    "/getRolesDataAccessByProduct",
    response_model=List[RoleDataAccessByProduct],
    tags=["Role Data Access"],
    summary="Listar Roles de Acceso por Producto",
    description="Obtiene la lista de roles de acceso a datos que están asociados a un `product_id` específico.",
)
def getRolesDataAccessByProduct(
    request_body: GetRolesDataAccessByProductRequest,
) -> List[RoleDataAccessByProduct]:
    """
    Obtiene la lista de roles de acceso a datos de un producto específico.
    """
    try:
        # Llama a la función de servicio pasando el request completo
        return get_roles_data_access_by_product(request_body)

    except Exception as e:
        # Manejo de errores
        raise HTTPException(
            status_code=500, detail=f"Error al obtener roles de acceso a datos: {e}"
        )


@data_access_router.post(
    "/sendRegistroRoleDataAccess",
    response_model=RoleDataAccessCreationResponse,
    tags=["Role Data Access"],
    summary="Registrar Acceso de Rol (CREATE)",
    description="Crea un nuevo rol de acceso a datos en la base de datos.",
)
def sendRegistroRoleDataAccess(
    request_body: RoleDataAccessRegisterRequest,
) -> RoleDataAccessCreationResponse:
    """
    Registra un nuevo rol de acceso a datos.
    """
    try:
        # Llama a la función de servicio
        new_role_id = send_register_role_data_access(request_body)

        # Retorna la respuesta con el ID generado
        return RoleDataAccessCreationResponse(id_role=new_role_id)

    except Exception as e:
        # Manejo de errores
        raise HTTPException(
            status_code=500, detail=f"Error al registrar rol de acceso a datos: {e}"
        )


@data_access_router.put(
    "/updateRoleDataAccess",
    response_model=RoleDataAccessUpdateResponse,
    tags=["Role Data Access"],
    summary="Actualizar Acceso de Rol (UPDATE)",
    description="Modifica un rol de acceso a datos existente, identificado por su `id`.",
)
def updateRoleDataAccess(
    request_body: RoleDataAccessUpdateRequest,
) -> RoleDataAccessUpdateResponse:
    """
    Actualiza un rol de acceso a datos existente.
    """
    try:
        # Llama a la función de servicio
        send_update_role_data_access(request_body)

        # Retorna la respuesta con el ID actualizado
        return RoleDataAccessUpdateResponse(role_id=request_body.id)

    except Exception as e:
        # Manejo de errores
        raise HTTPException(
            status_code=500,
            detail=f"Error interno al actualizar rol de acceso a datos: {e}",
        )


@data_access_router.delete(
    "/deleteRoleDataAccess",
    response_model=RoleDataAccessDeleteResponse,
    tags=["Role Data Access"],
    summary="Eliminar Acceso de Rol (DELETE)",
    description="Elimina un rol de acceso a datos existente.",
)
def deleteRoleDataAccess(
    request_body: RoleDataAccessDeleteRequest,
) -> RoleDataAccessDeleteResponse:
    """
    Elimina un rol de acceso a datos.
    """
    try:
        # Llama a la función de servicio
        send_delete_role_data_access(request_body)

        # Retorna la respuesta con el ID eliminado
        return RoleDataAccessDeleteResponse(role_id=request_body.id)

    except Exception as e:
        # Manejo de errores
        raise HTTPException(
            status_code=500,
            detail=f"Error interno al eliminar rol de acceso a datos: {e}",
        )


"""
    Gestion de despliegues
"""


@data_access_router.post(
    "/getDeployConfig",
    response_model=ClientDeployListResponse,
    tags=["Client Product Deploys"],
    summary="Obtener Configuración de Despliegue (Todos o por ID)",
    description="Obtiene todos los registros de configuración de despliegue o uno específico si se proporciona `deploy_id`.",
)
def get_deploy_config(request_body: GetClientDeployRequest) -> ClientDeployListResponse:
    """
    Obtiene todos los registros de despliegue o uno específico por ID.
    Si se proporciona deploy_id, retorna solo ese registro.
    """
    try:
        deploys = get_client_deploys(request_body)
        return ClientDeployListResponse(deploys=deploys)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener configuraciones de despliegue: {e}",
        )


# -----------------------------------------------------------------
# 2. GET (POST por Body): Obtener por product_id
# -----------------------------------------------------------------
@data_access_router.post(
    "/getDeploysByProduct",
    response_model=ClientDeployListResponse,
    tags=["Client Product Deploys"],
    summary="Listar Despliegues por Producto",
    description="Obtiene la lista de configuraciones de despliegue asociadas a un `product_id` específico.",
)
def get_deploys_by_product(
    request_body: GetClientDeployByProductRequest,
) -> ClientDeployListResponse:
    """
    Obtiene la lista de registros de despliegue de un producto específico.
    """
    try:
        deploys = get_client_deploys_by_product(request_body)
        return ClientDeployListResponse(deploys=deploys)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al obtener despliegues por producto: {e}"
        )


# -----------------------------------------------------------------
# 3. POST: Insertar (sendRegistro)
# -----------------------------------------------------------------
@data_access_router.post(
    "/sendRegisterDeployConfig",
    response_model=ClientDeployCreationResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Client Product Deploys"],
    summary="Registrar Configuración de Despliegue (CREATE)",
    description="Crea un nuevo registro de configuración de despliegue para un producto/cliente usando el SP V2 (INSERT o UPDATE).",
)
def send_register_deploy_config(
    request_body: ClientDeployRegisterRequest,
) -> ClientDeployCreationResponse:
    """
    Registra o actualiza una configuración de despliegue.
    Utiliza spu_minddash_app_insert_client_product_deployV2 (UPSERT).
    """
    try:
        new_deploy_id = send_register_client_deploy_v2(request_body)

        return ClientDeployCreationResponse(id_deploy=new_deploy_id)

    except Exception as e:
        error_detail = str(e)

        if "foreign key constraint" in error_detail:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error de clave foránea: El producto con ID {request_body.product_id} no existe.",
            )

        raise HTTPException(
            status_code=500,
            detail=f"Error al registrar la configuración de despliegue: {e}",
        )


# -----------------------------------------------------------------
# 4. PUT: Actualizar
# -----------------------------------------------------------------
@data_access_router.put(
    "/updateDeployConfig",
    response_model=ClientDeployUpdateResponse,
    tags=["Client Product Deploys"],
    summary="Actualizar Configuración de Despliegue (UPDATE)",
    description="Modifica un registro de configuración de despliegue existente.",
)
def update_deploy_config(
    request_body: ClientDeployRegisterRequest,
) -> ClientDeployUpdateResponse:
    """
    Actualiza un registro de configuración de despliegue existente mediante UPSERT.
    """
    try:
        deploy_id = send_register_client_deploy_v2(request_body)

        return ClientDeployUpdateResponse(deploy_id=deploy_id)

    except HTTPException as e:
        raise e

    except Exception as e:
        error_detail = str(e)
        if "foreign key constraint" in error_detail:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error de clave foránea: El producto con ID {request_body.product_id} no existe.",
            )
        raise HTTPException(
            status_code=500,
            detail=f"Error interno al actualizar la configuración de despliegue: {e}",
        )


# -----------------------------------------------------------------
# 5. DELETE: Eliminar
# -----------------------------------------------------------------
@data_access_router.delete(
    "/deleteDeployConfig",
    response_model=ClientDeployDeleteResponse,
    tags=["Client Product Deploys"],
    summary="Eliminar Configuración de Despliegue (DELETE)",
    description="Elimina un registro de configuración de despliegue.",
)
def delete_deploy_config(
    request_body: ClientDeployDeleteRequest,
) -> ClientDeployDeleteResponse:
    """
    Elimina un registro de configuración de despliegue.
    Llama a spu_minddash_app_delete_client_product_deploy.
    """
    try:
        send_delete_client_deploy(request_body)
        return ClientDeployDeleteResponse(deploy_id=request_body.id)

    except HTTPException as e:
        raise e  # 404 manejado en el servicio
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error interno al eliminar la configuración de despliegue: {e}",
        )
