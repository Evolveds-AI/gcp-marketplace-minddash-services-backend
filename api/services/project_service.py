import logging
from typing import Any, Dict, List

from api.models.project_models import (
    Project,
    ProjectByUser,
    ProjectDeleteAccessRequest,
    ProjectDeleteRequest,
    ProjectRegisterAccessRequest,
    ProjectRegisterRequest,
    ProjectUpdateAccessRequest,
    ProjectUpdateRequest,
)
from api.utils.db_client import execute, execute_procedure_with_out, query_all

logger = logging.getLogger(__name__)


def get_list_project() -> List[Project]:
    rows = query_all("""
        SELECT 
               user_id, user_role_name, user_name, user_phone, user_email, 
                organization_id, organization_name, 
                project_id, project_name, project_label, project_label_color, project_description
            FROM view_list_projects  -- Nombre asumido para la vista consolidada
    """)
    return [Project(**r) for r in rows]


def get_list_projects_by_user(user_id: str) -> List[ProjectByUser]:
    """
    Obtiene la lista consolidada de proyectos a los que un usuario tiene acceso
    (directo, o heredado de producto).
    """
    query_str = f"""
        SELECT 
            user_id, user_role_name, user_name, user_phone, user_email, 
            organization_id, organization_name, 
            project_id, project_name, project_label, project_label_color, project_description
        FROM view_list_projects  -- Nombre asumido para la vista consolidada
        WHERE
            user_id = '{user_id}'
    """
    print("query_str")
    print(query_str)

    rows = query_all(query_str)

    print("rows")
    print(rows)
    # Mapeo de los resultados de la DB al modelo Pydantic
    return [ProjectByUser(**r) for r in rows]


def get_list_projects_by_prj(project_id: str, user_id: str) -> List[Project]:
    """
    Obtiene la lista consolidada de proyectos a los que un usuario tiene acceso
    (directo, o heredado de producto).
    """
    query_str = f"""
        SELECT 
            user_id, user_role_name, user_name, user_phone, user_email, 
            organization_id, organization_name, 
            project_id, project_name, project_label, project_label_color, project_description
        FROM view_list_projects  -- Nombre asumido para la vista consolidada
        WHERE
                project_id = '{project_id}'
            and user_id = '{user_id}'
    """
    rows = query_all(query_str)

    # Mapeo de los resultados de la DB al modelo Pydantic
    return [Project(**r) for r in rows]


def send_register_project(project_data: ProjectRegisterRequest) -> str:
    """
    Llama al Stored Procedure para registrar una nueva proyecto y retorna el ID.
    """

    query_str = """
        CALL spu_minddash_app_insert_project(
            p_organization_id => %s,  -- NUEVO: Se requiere el project_id
            p_name => %s,
            p_label => %s,             -- NUEVO: Se requiere label
            p_label_color => %s,       -- NUEVO: Se requiere label_color
            p_description => %s,
            io_project_id => %s
        );
    """

    params = (
        project_data.organization_id,
        project_data.name,
        project_data.label,
        project_data.label_color,
        project_data.description,
        None,
    )

    # Ejecuta el CALL y obtiene el diccionario de resultados (donde estará io_project_id)
    result: Dict[str, Any] | None = execute_procedure_with_out(query_str, params=params)

    # El resultado se devuelve con el nombre del parámetro INOUT
    if result and "io_project_id" in result:
        return str(result["io_project_id"])
    else:
        # Si el SP se ejecutó pero no devolvió el ID (raro si es INOUT), asumimos fallo
        raise Exception(
            "Registro de proyecto fallido: no se pudo obtener el ID del procedimiento."
        )


def send_update_project(project_data: ProjectUpdateRequest) -> int:
    """
    Llama al Stored Procedure para actualizar una proyecto.
    Retorna el rowcount (número de filas afectadas, debería ser 1 o 0).
    """
    query_str = """
        CALL spu_minddash_app_update_project(
            p_project_id := %s,
            p_organization_id := %s,   -- NUEVO: project_id
            p_name := %s,
            p_label := %s,             -- NUEVO: label
            p_label_color := %s,       -- NUEVO: label_color
            p_description := %s
        );
    """

    # *** PARÁMETROS CORREGIDOS para coincidir con el orden del query ***
    params = (
        project_data.id,  # p_project_id
        project_data.organization_id,  # p_project_id
        project_data.name,  # p_name
        project_data.label,  # p_label
        project_data.label_color,  # p_label_color
        project_data.description,  # p_description
    )

    # Usamos execute, que está diseñada para comandos DML (como CALL sin retorno)
    # Nota: psycopg2 con CALL generalmente devuelve rowcount=1 si se ejecuta el CALL
    rowcount = execute(query_str, params=params)

    # En este caso, el SP hace la validación internamente y lanza una excepción si falla.
    # Si llega hasta aquí, asumimos que fue exitoso.
    return rowcount


def send_delete_project(project_data: ProjectDeleteRequest) -> int:
    """
    Llama al Stored Procedure para eliminar una proyecto.
    Retorna el rowcount (-1 si es exitoso con CALL).
    """
    project_id = project_data.id
    logger.info(
        "Iniciando eliminación de la proyecto ID: %s", project_id
    )  # <-- OK: %s y project_id

    query_str = """
        CALL spu_minddash_app_delete_project(
            p_project_id := %s
        );
    """

    # LA CORRECCIÓN: Agregar la coma para forzar que sea una tupla
    params = (project_id,)

    try:
        # Usamos execute. Devuelve -1 en caso de éxito con CALL.
        rowcount = execute(query_str, params=params)
        logger.info(
            "Eliminación de proyecto ID: %s completada. Filas afectadas: %d",
            project_id,
            rowcount,
        )
        return rowcount
    except Exception as e:
        # ¡OTRO PUNTO DE ERROR POTENCIAL!
        # Si tienes varios %s en logger.error, pero solo pasas project_id y str(e)
        logger.error(
            "Error al ejecutar la eliminación para ID %s: %s", project_id, str(e)
        )
        # Si esta línea da error, significa que el mensaje de error tiene placeholders ocultos

        # Re-lanza la excepción para que el router la maneje
        raise


"""
    Bloque de gestion de accesos de Proyectos:
"""


def send_register_access_project(
    access_project_data: ProjectRegisterAccessRequest,
) -> str:
    """
    Llama al Stored Procedure para registrar un nuevo acceso usuario-proyectos y retorna el ID.
    """

    # CORRECCIÓN: Agregar ::UUID al último placeholder posicional
    query_str = """
        CALL spu_minddash_app_insert_user_project_access(
            %s::UUID,            -- 1. p_user_id
            %s::UUID,            -- 2. p_project_id
            %s::UUID,            -- 3. p_role_id
            %s::UUID             -- 4. io_access_id (Ahora casteamos el NULL a UUID)
        );
    """

    # El orden en 'params' DEBE coincidir con el orden de los argumentos en el SP
    params = (
        access_project_data.user_id,
        access_project_data.project_id,
        access_project_data.role_id,
        None,  # Valor inicial (NULL) que ahora será casteado a UUID
    )

    # Ejecuta el CALL y obtiene el diccionario de resultados
    result: Dict[str, Any] | None = execute_procedure_with_out(query_str, params=params)

    if result and "io_access_id" in result:
        return str(result["io_access_id"])
    else:
        raise Exception(
            "Registro de acceso a proyectos fallido: no se pudo obtener el ID del procedimiento."
        )


def send_update_access_project(access_project_data: ProjectUpdateAccessRequest) -> int:
    """
    Llama al Stored Procedure para actualizar un registro de acceso.
    Retorna el rowcount (-1 en caso de éxito con CALL).
    """
    query_str = """
        CALL spu_minddash_app_update_user_project_access(
            p_access_id := %s,
            p_user_id := %s,
            p_project_id := %s,
            p_role_id := %s
        );
    """

    # Lista de parámetros para el Stored Procedure
    params = (
        access_project_data.id,
        access_project_data.user_id,
        access_project_data.project_id,
        access_project_data.role_id,
    )

    # Usamos execute. El SP maneja las validaciones y lanza RAISE EXCEPTION si algo falla.
    # Si llega aquí, es exitoso.
    rowcount = execute(query_str, params=params)

    return rowcount


def send_delete_access_project(access_project_data: ProjectDeleteAccessRequest) -> int:
    """
    Llama al Stored Procedure para eliminar un registro de acceso.
    Retorna el rowcount (-1 en caso de éxito con CALL).
    """
    access_id = access_project_data.id
    # logger.info("Iniciando eliminación de acceso ID: %s", aforccess_id)

    query_str = """
        CALL spu_minddash_app_delete_user_project_access(
            p_access_id := %s
        );
    """

    # Se necesita una tupla, incluso si solo hay un elemento (usamos la coma)
    params = (access_id,)

    try:
        # Usamos execute. Devuelve -1 en caso de éxito con CALL.
        rowcount = execute(query_str, params=params)
        # logger.info("Eliminación de acceso ID: %s completada. Filas afectadas: %d", access_id, rowcount)
        return rowcount
    except Exception:
        # Re-lanza la excepción para que el router la maneje (ej. capturar el 404/RAISE EXCEPTION)
        # logger.error("Error al ejecutar la eliminación para ID %s: %s", access_id, str(e))
        raise
