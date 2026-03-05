from typing import List

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from api.models.project_models import (
    Project,
    ProjectByUser,
    ProjectCreationAccessResponse,
    ProjectCreationResponse,
    ProjectDeleteAccessRequest,
    ProjectDeleteAccessResponse,
    ProjectDeleteRequest,
    ProjectDeleteResponse,
    ProjectRegisterAccessRequest,
    ProjectRegisterRequest,
    ProjectUpdateAccessRequest,
    ProjectUpdateAccessResponse,
    ProjectUpdateRequest,
    ProjectUpdateResponse,
)
from api.services.project_service import (
    get_list_project,
    get_list_projects_by_prj,
    get_list_projects_by_user,
    send_delete_project,
    send_register_access_project,
    send_register_project,
    send_update_access_project,
    send_update_project,
    send_delete_access_project,
)

project_router = APIRouter(prefix="/projects")


class GetProjectRequest(BaseModel):
    """
    Modelo para validar el cuerpo de la solicitud que contiene el ID de usuario.
    """

    user_id: str = Field(
        ..., description="UUID del usuario para el cual se buscan las proyectos."
    )


class GetProjectRequestByPrj(BaseModel):
    """
    Modelo para validar el cuerpo de la solicitud que contiene el ID de usuario.
    """

    user_id: str = Field(
        ..., description="UUID del usuario para el cual se buscan las proyectos."
    )
    project_id: str = Field(
        ..., description="UUID del usuario para el cual se buscan las proyectos."
    )


@project_router.get(
    "/getListProject",
    response_model=List[Project],
    tags=["Project Management"],
    summary="Listar Todos los Proyectos",
    description="Obtiene una lista completa de todos los proyectos registrados en el sistema.",
)
def getListProject() -> List[Project]:
    try:
        return get_list_project()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@project_router.post(
    "/getListProjectByUser",
    response_model=List[ProjectByUser],
    tags=["Project Management"],
    summary="Listar Proyectos por Usuario",
    description="Obtiene la lista de proyectos a los que un `user_id` específico tiene acceso (directo o heredado), filtrando por el ID de usuario proporcionado en el cuerpo de la solicitud.",
)
def getListProjectByUser(request_body: GetProjectRequest) -> List[ProjectByUser]:
    """
    Obtiene todos los proyectos a los que un usuario tiene acceso (directo o heredado),
    filtrando por el user_id proporcionado en el cuerpo de la solicitud.
    """
    try:
        # Extrae y valida el user_id del cuerpo
        user_id = request_body.user_id

        # Llama a la función de servicio
        return get_list_projects_by_user(user_id=user_id)

    except Exception as e:
        # Manejo de errores
        raise HTTPException(status_code=500, detail=f"Error al obtener proyectos: {e}")


@project_router.post(
    "/getListProjectByPrj",
    response_model=List[Project],
    tags=["Project Management"],
    summary="Obtener Proyecto por ID",
    description="Recupera los detalles de un proyecto específico utilizando su `project_id`. Incluye validación de acceso por `user_id`.",
)
def getListProjectByPrj(request_body: GetProjectRequestByPrj) -> List[Project]:
    """
    Obtiene todos los proyectos a los que un usuario tiene acceso (directo o heredado),
    filtrando por el user_id proporcionado en el cuerpo de la solicitud.
    """
    try:
        # Extrae y valida el user_id del cuerpo
        project_id = request_body.project_id
        user_id = request_body.user_id

        # Llama a la función de servicio
        return get_list_projects_by_prj(project_id=project_id, user_id=user_id)

    except Exception as e:
        # Manejo de errores
        raise HTTPException(status_code=500, detail=f"Error al obtener proyectos: {e}")


@project_router.post(
    "/sendRegistroProject",
    response_model=ProjectCreationResponse,
    tags=["Project Management"],
    summary="Registrar Nuevo Proyecto (CREATE)",
    description="Crea un nuevo registro de proyecto en la base de datos.",
)
def sendRegistroProject(
    project_data: ProjectRegisterRequest,
) -> ProjectCreationResponse:
    try:
        # Llama a la función de servicio con los datos de registro
        result_message = send_register_project(project_data)

        # Construir y retornar la respuesta
        return ProjectCreationResponse(id_project=result_message)

    except Exception as e:
        # Manejo de errores
        print(f"Error en sendRegistroProject: {e}")
        # Puedes añadir un manejo específico si el error es de violación de restricción, etc.
        raise HTTPException(
            status_code=500, detail=f"Error al registrar la proyectos: {e}"
        )


@project_router.put(
    "/updateProject",
    response_model=ProjectUpdateResponse,
    tags=["Project Management"],
    summary="Actualizar Proyecto (UPDATE)",
    description="Modifica los datos de un proyecto existente. Devuelve error 404 si el proyecto no existe.",
)
def updateProject(project_data: ProjectUpdateRequest) -> ProjectUpdateResponse:
    try:
        # 1. Ejecutar el servicio. Si el SP encuentra que el ID NO existe,
        #    lanza una excepción (RAISE EXCEPTION).
        #    Si el ID SÍ existe, devuelve -1 (rowcount).
        rows_affected = send_update_project(project_data)

        # 2. Si llegamos hasta aquí, NO hubo una excepción, por lo que la operación fue exitosa.
        #    No importa si rows_affected es 1 o -1.
        return ProjectUpdateResponse(project_id=project_data.id)

    except Exception as e:
        error_detail = str(e)

        # 3. Capturar el error del RAISE EXCEPTION del SP y convertirlo en 404
        # Esto sucede cuando el ID no existe en la BD.
        if "No se puede actualizar. La proyectos con ID" in error_detail:
            # Aquí usamos el 404. El error_detail contiene el mensaje que generó el SP
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_detail.split("ERROR: ")[-1],  # Extrae solo el mensaje
            )

        # 4. Cualquier otro error no manejado
        print(f"Error al actualizar la proyectos: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al actualizar la proyectos: {error_detail}",
        )


@project_router.delete(
    "/deleteProject",
    response_model=ProjectDeleteResponse,
    tags=["Project Management"],
    summary="Eliminar Proyecto (DELETE)",
    description="Elimina un proyecto del sistema usando su `id`. Devuelve error 404 si el proyecto no existe.",
)
def deleteProject(project_data: ProjectDeleteRequest) -> ProjectDeleteResponse:
    org_id = project_data.id
    try:
        # Llama al servicio. Si el ID no existe, el SP lanza una excepción.
        send_delete_project(project_data)

        # Si llegamos aquí, NO hubo una excepción, la eliminación fue exitosa (rowcount = -1).
        return ProjectDeleteResponse(project_id=org_id)

    except Exception as e:
        error_detail = str(e)

        # 1. Capturar el error del RAISE EXCEPTION del SP y convertirlo en 404
        if "No se puede eliminar. La proyectos con ID" in error_detail:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No se encontró la proyectos con ID: {org_id} para eliminar.",
            )

        # 2. Cualquier otro error no manejado
        print(f"Error al eliminar la proyectos: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al eliminar la proyectos: {error_detail}",
        )


"""
    Bloque de Control a accesos de Proyectos:
"""


@project_router.post(
    "/sendAccessProject",
    response_model=ProjectCreationAccessResponse,
    tags=["Project Access"],
    summary="Otorgar Acceso a Proyecto (CREATE Permission)",
    description="Registra el acceso de un `user_id` a un `project_id` específico, asignándole un `role_id`.",
)
def sendAccessProject(
    access_project_data: ProjectRegisterAccessRequest,
) -> ProjectCreationAccessResponse:
    """
    Registra el acceso de un usuario a una proyectos con un rol específico.
    Llama a spu_minddash_app_insert_user_org_access.
    """
    try:
        # Llama a la función de servicio. Esta devuelve el nuevo UUID del registro.
        project_access_id = send_register_access_project(access_project_data)

        # Construir y retornar la respuesta exitosa
        return ProjectCreationAccessResponse(project_access_id=project_access_id)

    except Exception as e:
        error_detail = str(e)

        # Manejo de errores específicos lanzados por el SP (ej. duplicados o FK inválidas)
        if (
            "El usuario con ID" in error_detail
            or "La proyectos con ID" in error_detail
            or "El rol con ID" in error_detail
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_detail.split("ERROR: ")[-1],
            )
        if (
            "Este usuario ya tiene el rol especificado en esta proyectos"
            in error_detail
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,  # Conflicto (ya existe)
                detail=error_detail.split("ERROR: ")[-1],
            )

        # Error genérico
        print(f"Error en sendAccessProject: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al registrar el accesso a la proyectos: {error_detail}",
        )


@project_router.put(
    "/updateAccessProject",
    response_model=ProjectUpdateAccessResponse,
    tags=["Project Access"],
    summary="Actualizar Acceso a Proyecto (UPDATE Permission)",
    description="Modifica un registro de acceso existente, permitiendo cambiar el rol (`role_id`) o reasignar el acceso. Devuelve error 404 si el registro de acceso no existe.",
)
def updateAccessProject(
    access_project_data: ProjectUpdateAccessRequest,
) -> ProjectUpdateAccessResponse:
    """
    Actualiza el user_id, project_id y/o role_id de un registro de acceso existente.
    Llama a spu_minddash_app_update_user_org_access.
    """
    try:
        # 1. Ejecutar el servicio. Si el SP encuentra que el ID NO existe, lanza una excepción.
        rows_affected = send_update_access_project(access_project_data)

        # 2. Si llegamos hasta aquí, la operación fue exitosa.
        return ProjectUpdateAccessResponse(project_access_id=access_project_data.id)

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
            or "La proyectos con ID" in error_detail
            or "El nuevo rol con ID" in error_detail
        ):
            # FK inválida (400)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_detail.split("ERROR: ")[-1],
            )

        # 4. Cualquier otro error no manejado
        print(f"Error al actualizar el acceso a la proyectos: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al actualizar el acceso a la proyectos: {error_detail}",
        )


@project_router.delete(
    "/deleteAccessProject",
    response_model=ProjectDeleteAccessResponse,
    tags=["Project Access"],
    summary="Revocar Acceso a Proyecto (DELETE Permission)",
    description="Elimina el registro de acceso, revocando los permisos del usuario para el proyecto específico. Devuelve error 404 si el registro de acceso no existe.",
)
def deleteAccessProject(
    access_project_data: ProjectDeleteAccessRequest,
) -> ProjectDeleteAccessResponse:
    """
    Elimina un registro de acceso de usuario a proyectos.
    Llama a spu_minddash_app_delete_user_org_access.
    """
    org_access_id = access_project_data.id
    try:
        # Llama al servicio. Si el ID no existe, el SP lanza una excepción.
        send_delete_access_project(access_project_data)

        # Si llegamos aquí, la eliminación fue exitosa.
        return ProjectDeleteAccessResponse(project_access_id=org_access_id)

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
        print(f"Error al eliminar el acceso a la proyectos: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al eliminar el acceso a la proyectos: {error_detail}",
        )
