import logging
from typing import List

from fastapi import APIRouter, HTTPException, status

logger = logging.getLogger(__name__)
from api.models.organization_models import (
    GetOrganizationRequest,
    GetOrganizationRequestByOrg,
    Organization,
    OrganizationByUser,
    OrganizationCreationAccessResponse,
    OrganizationCreationResponse,
    OrganizationDeleteAccessRequest,
    OrganizationDeleteAccessResponse,
    OrganizationDeleteRequest,
    OrganizationDeleteResponse,
    OrganizationRegisterAccessRequest,
    OrganizationRegisterRequest,
    OrganizationUpdateAccessRequest,
    OrganizationUpdateAccessResponse,
    OrganizationUpdateRequest,
    OrganizationUpdateResponse,
)
from api.services.organization_service import (
    get_list_organization,
    get_list_organization_by_org,
    get_list_organization_by_user,
    send_delete_access_organization,
    send_delete_organization,
    send_register_access_organization,
    send_register_organization,
    send_update_access_organization,
    send_update_organization,
)

organization_router = APIRouter(prefix="/organizations")


@organization_router.get(
    "/getListOrganization",
    response_model=List[Organization],
    tags=["Organization Management"],
    summary="Listar Todas las Organizaciones",
    description="Obtiene una lista completa de todas las organizaciones registradas en el sistema.",
)
def getListOrganization() -> List[Organization]:
    try:
        return get_list_organization()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@organization_router.post(
    "/getListOrganizationByOrg",
    response_model=List[Organization],
    tags=["Organization Management"],
    summary="Obtener Organización por ID",
    description="Recupera los detalles de una organización específica utilizando su `organization_id`. Puede incluir validación de acceso por `user_id`.",
)
def getListOrganizationByOrg(
    request_body: GetOrganizationRequestByOrg,
) -> List[Organization]:
    try:
        # Extrae el user_id validado del cuerpo
        organization_id = request_body.organization_id
        user_id = request_body.user_id

        # Llama a la función de servicio con el ID extraído
        return get_list_organization_by_org(
            organization_id=organization_id, user_id=user_id
        )

    except Exception as e:
        # Manejo de errores
        raise HTTPException(
            status_code=500, detail=f"Error al obtener organizaciones: {e}"
        )


@organization_router.post(
    "/getListOrganizationByUser",
    response_model=List[OrganizationByUser],
    tags=["Organization Management"],
    summary="Listar Organizaciones por Usuario",
    description="Obtiene la lista de organizaciones a las que tiene acceso un `user_id` específico.",
)
def getListOrganizationByUser(
    request_body: GetOrganizationRequest,
) -> List[OrganizationByUser]:
    try:
        # Extrae el user_id validado del cuerpo
        user_id = request_body.user_id

        # Llama a la función de servicio con el ID extraído
        return get_list_organization_by_user(user_id=user_id)

    except Exception as e:
        # Manejo de errores
        raise HTTPException(
            status_code=500, detail=f"Error al obtener organizaciones: {e}"
        )


@organization_router.post(
    "/sendRegisterOrganization",
    response_model=OrganizationCreationResponse,
    tags=["Organization Management"],
    summary="Registrar Nueva Organización (CREATE)",
    description="Crea un nuevo registro de organización en la base de datos.",
)
def sendRegisterOrganization(
    organization_data: OrganizationRegisterRequest,
) -> OrganizationCreationResponse:
    try:
        # Llama a la función de servicio con los datos de registro
        result_message = send_register_organization(organization_data)

        # Construir y retornar la respuesta
        return OrganizationCreationResponse(id_organization=result_message)

    except Exception as e:
        # Manejo de errores
        print(f"Error en sendRegistroOrganization: {e}")
        # Puedes añadir un manejo específico si el error es de violación de restricción, etc.
        raise HTTPException(
            status_code=500, detail=f"Error al registrar la organización: {e}"
        )


@organization_router.put(
    "/updateOrganization",
    response_model=OrganizationUpdateResponse,
    tags=["Organization Management"],
    summary="Actualizar Organización (UPDATE)",
    description="Modifica los datos de una organización existente. Devuelve error 404 si la organización no existe.",
)
def updateOrganization(
    organization_data: OrganizationUpdateRequest,
) -> OrganizationUpdateResponse:
    try:
        # 1. Ejecutar el servicio. Si el SP encuentra que el ID NO existe,
        #    lanza una excepción (RAISE EXCEPTION).
        #    Si el ID SÍ existe, devuelve -1 (rowcount).
        rows_affected = send_update_organization(organization_data)

        # 2. Si llegamos hasta aquí, NO hubo una excepción, por lo que la operación fue exitosa.
        #    No importa si rows_affected es 1 o -1.
        return OrganizationUpdateResponse(organization_id=organization_data.id)

    except Exception as e:
        error_detail = str(e)

        # 3. Capturar el error del RAISE EXCEPTION del SP y convertirlo en 404
        # Esto sucede cuando el ID no existe en la BD.
        if "No se puede actualizar. La organización con ID" in error_detail:
            # Aquí usamos el 404. El error_detail contiene el mensaje que generó el SP
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_detail.split("ERROR: ")[-1],  # Extrae solo el mensaje
            )

        # 4. Cualquier otro error no manejado
        print(f"Error al actualizar la organización: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al actualizar la organización: {error_detail}",
        )


@organization_router.delete(
    "/deleteOrganization",
    response_model=OrganizationDeleteResponse,
    tags=["Organization Management"],
    summary="Eliminar Organización (DELETE)",
    description="Elimina una organización del sistema usando su `id`. Devuelve error 404 si la organización no existe.",
)
def deleteOrganization(
    organization_data: OrganizationDeleteRequest,
) -> OrganizationDeleteResponse:
    org_id = organization_data.id
    try:
        # Llama al servicio. Si el ID no existe, el SP lanza una excepción.
        send_delete_organization(organization_data)

        # Si llegamos aquí, NO hubo una excepción, la eliminación fue exitosa (rowcount = -1).
        return OrganizationDeleteResponse(organization_id=org_id)

    except Exception as e:
        error_detail = str(e)

        # 1. Capturar el error del RAISE EXCEPTION del SP y convertirlo en 404
        if "No se puede eliminar. La organización con ID" in error_detail:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No se encontró la organización con ID: {org_id} para eliminar.",
            )

        # 2. Cualquier otro error no manejado
        print(f"Error al eliminar la organización: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al eliminar la organización: {error_detail}",
        )


"""
    Bloque de Control a accesos de organizacion:
"""


@organization_router.post(
    "/sendAccessOrganization",
    response_model=OrganizationCreationAccessResponse,
    tags=["Organization Access"],
    summary="Otorgar Acceso a Organización (CREATE Permission)",
    description="Registra el acceso de un `user_id` a una `organization_id` específica, asignándole un `role_id`.",
)
def sendAccessOrganization(
    access_organization_data: OrganizationRegisterAccessRequest,
) -> OrganizationCreationAccessResponse:
    """
    Registra el acceso de un usuario a una organización con un rol específico.
    Llama a spu_minddash_app_insert_user_org_access.
    """
    try:
        # Llama a la función de servicio. Esta devuelve el nuevo UUID del registro.
        organization_access_id = send_register_access_organization(
            access_organization_data
        )

        # Construir y retornar la respuesta exitosa
        return OrganizationCreationAccessResponse(
            organization_access_id=organization_access_id
        )

    except Exception as e:
        error_detail = str(e)

        # Manejo de errores específicos lanzados por el SP (ej. duplicados o FK inválidas)
        if (
            "El usuario con ID" in error_detail
            or "La organización con ID" in error_detail
            or "El rol con ID" in error_detail
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_detail.split("ERROR: ")[-1],
            )
        if (
            "Este usuario ya tiene el rol especificado en esta organización"
            in error_detail
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,  # Conflicto (ya existe)
                detail=error_detail.split("ERROR: ")[-1],
            )

        # Error genérico
        print(f"Error en sendAccessOrganization: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al registrar el accesso a la organización: {error_detail}",
        )


@organization_router.put(
    "/updateAccessOrganization",
    response_model=OrganizationUpdateAccessResponse,
    tags=["Organization Access"],
    summary="Actualizar Acceso a Organización (UPDATE Permission)",
    description="Modifica un registro de acceso existente, permitiendo cambiar el rol (`role_id`) o reasignar el acceso a otro usuario/organización. Devuelve error 404 si el registro de acceso no existe.",
)
def updateAccessOrganization(
    access_organization_data: OrganizationUpdateAccessRequest,
) -> OrganizationUpdateAccessResponse:
    """
    Actualiza el user_id, organization_id y/o role_id de un registro de acceso existente.
    Llama a spu_minddash_app_update_user_org_access.
    """
    try:
        # 1. Ejecutar el servicio. Si el SP encuentra que el ID NO existe, lanza una excepción.
        rows_affected = send_update_access_organization(access_organization_data)

        # 2. Si llegamos hasta aquí, la operación fue exitosa.
        return OrganizationUpdateAccessResponse(
            organization_access_id=access_organization_data.id
        )

    except Exception as e:
        error_detail = str(e)

        # 3. Capturar el error del RAISE EXCEPTION del SP (ID no existe o FK inválida)
        if "No se puede actualizar. El registro de acceso con ID" in error_detail:
            # El registro de acceso a actualizar no existe (404)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_detail.split("ERROR: ")[-1],
            )
        elif (
            "El usuario con ID" in error_detail
            or "La organización con ID" in error_detail
            or "El nuevo rol con ID" in error_detail
        ):
            # FK inválida (400)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_detail.split("ERROR: ")[-1],
            )

        # 4. Cualquier otro error no manejado
        print(f"Error al actualizar el acceso a la organización: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al actualizar el acceso a la organización: {error_detail}",
        )


@organization_router.delete(
    "/deleteAccessOrganization",
    response_model=OrganizationDeleteAccessResponse,
    tags=["Organization Access"],
    summary="Revocar Acceso a Organización (DELETE Permission)",
    description="Elimina el registro de acceso, revocando los permisos del usuario para la organización específica. Devuelve error 404 si el registro de acceso no existe.",
)
def deleteAccessOrganization(
    access_organization_data: OrganizationDeleteAccessRequest,
) -> OrganizationDeleteAccessResponse:
    """
    Elimina un registro de acceso de usuario a organización.
    Llama a spu_minddash_app_delete_user_org_access.
    """
    org_access_id = access_organization_data.id
    try:
        # Llama al servicio. Si el ID no existe, el SP lanza una excepción.
        send_delete_access_organization(access_organization_data)

        # Si llegamos aquí, la eliminación fue exitosa.
        return OrganizationDeleteAccessResponse(organization_access_id=org_access_id)

    except Exception as e:
        error_detail = str(e)

        # 1. Capturar el error del RAISE EXCEPTION del SP (Registro no existe)
        if "No se puede eliminar. El registro de acceso con ID" in error_detail:
            # Aquí usamos 404. El error_detail contiene el mensaje que generó el SP.
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_detail.split("ERROR: ")[-1],
            )
        # Nota: Adapté el string de búsqueda al mensaje de error del SP de DELETE proporcionado.

        # 2. Cualquier otro error no manejado
        print(f"Error al eliminar el acceso a la organización: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al eliminar el acceso a la organización: {error_detail}",
        )
