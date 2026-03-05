import logging
from typing import Any, Dict, List

from api.models.organization_models import (
    Organization,
    OrganizationByUser,
    OrganizationDeleteAccessRequest,
    OrganizationDeleteRequest,
    OrganizationRegisterAccessRequest,
    OrganizationRegisterRequest,
    OrganizationUpdateAccessRequest,
    OrganizationUpdateRequest,
)
from api.utils.db_client import execute, execute_procedure_with_out, query_all

logger = logging.getLogger(__name__)


def get_list_organization() -> List[Organization]:
    query_str = """
        SELECT 
            user_id, user_role_name, user_name,
            user_phone, user_email, organization_id,
            organization_name, organization_company_name, organization_country
        FROM view_list_organizations
    """
    rows = query_all(query_str)
    return [Organization(**r) for r in rows]


def get_list_organization_by_user(user_id: str) -> List[OrganizationByUser]:
    query_str = f"""
        SELECT 
            user_id, user_role_name, user_name,
            user_phone, user_email, organization_id,
            organization_name, organization_company_name, organization_country
        FROM view_list_organizations
        where
		    user_id = '{user_id}'
    """
    rows = query_all(query_str)
    return [OrganizationByUser(**r) for r in rows]


def get_list_organization_by_org(
    organization_id: str, user_id: str
) -> List[Organization]:
    query_str = f"""
        SELECT 
            user_id, user_role_name, user_name,
            user_phone, user_email, organization_id,
            organization_name, organization_company_name, organization_country
        FROM view_list_organizations
        where
		        organization_id = '{organization_id}'
            and user_id = '{user_id}'
    """
    rows = query_all(query_str)
    return [Organization(**r) for r in rows]


def send_register_organization(organization_data: OrganizationRegisterRequest) -> str:
    """
    Llama al Stored Procedure para registrar una nueva organización y retorna el ID.
    """

    query_str = """
        CALL spu_minddash_app_insert_organization(
            p_name => %s,
            p_company_name => %s,
            p_description => %s,
            p_country => %s,
            io_organization_id => %s
        );
    """

    params = (
        organization_data.name,
        organization_data.company_name,
        organization_data.description,
        organization_data.country,
        None,
    )

    # Ejecuta el CALL y obtiene el diccionario de resultados (donde estará io_organization_id)
    result: Dict[str, Any] | None = execute_procedure_with_out(query_str, params=params)

    # El resultado se devuelve con el nombre del parámetro INOUT
    if result and "io_organization_id" in result:
        return str(result["io_organization_id"])
    else:
        # Si el SP se ejecutó pero no devolvió el ID (raro si es INOUT), asumimos fallo
        raise Exception(
            "Registro de organización fallido: no se pudo obtener el ID del procedimiento."
        )


def send_update_organization(organization_data: OrganizationUpdateRequest) -> int:
    """
    Llama al Stored Procedure para actualizar una organización.
    Retorna el rowcount (número de filas afectadas, debería ser 1 o 0).
    """
    query_str = """
        CALL spu_minddash_app_update_organization(
            p_organization_id := %s,
            p_name := %s,
            p_company_name := %s,
            p_description := %s,
            p_country := %s
        );
    """

    # Lista de parámetros para el Stored Procedure
    params = (
        organization_data.id,
        organization_data.name,
        organization_data.company_name,
        organization_data.description,
        organization_data.country,
    )

    # Usamos execute, que está diseñada para comandos DML (como CALL sin retorno)
    # Nota: psycopg2 con CALL generalmente devuelve rowcount=1 si se ejecuta el CALL
    rowcount = execute(query_str, params=params)

    # En este caso, el SP hace la validación internamente y lanza una excepción si falla.
    # Si llega hasta aquí, asumimos que fue exitoso.
    return rowcount


def send_delete_organization(organization_data: OrganizationDeleteRequest) -> int:
    """
    Llama al Stored Procedure para eliminar una organización.
    Retorna el rowcount (-1 si es exitoso con CALL).
    """
    org_id = organization_data.id
    logger.info(
        "Iniciando eliminación de la organización ID: %s", org_id
    )  # <-- OK: %s y org_id

    query_str = """
        CALL spu_minddash_app_delete_organization(
            p_organization_id := %s
        );
    """

    # LA CORRECCIÓN: Agregar la coma para forzar que sea una tupla
    params = (org_id,)

    try:
        # Usamos execute. Devuelve -1 en caso de éxito con CALL.
        rowcount = execute(query_str, params=params)
        logger.info(
            "Eliminación de organización ID: %s completada. Filas afectadas: %d",
            org_id,
            rowcount,
        )
        return rowcount
    except Exception as e:
        # ¡OTRO PUNTO DE ERROR POTENCIAL!
        # Si tienes varios %s en logger.error, pero solo pasas org_id y str(e)
        logger.error("Error al ejecutar la eliminación para ID %s: %s", org_id, str(e))
        # Si esta línea da error, significa que el mensaje de error tiene placeholders ocultos

        # Re-lanza la excepción para que el router la maneje
        raise


"""
    Bloque de gestion de accesos de organizacion:
"""


def send_register_access_organization(
    access_organization_data: OrganizationRegisterAccessRequest,
) -> str:
    """
    Llama al Stored Procedure para registrar un nuevo acceso usuario-organización y retorna el ID.
    """

    # CORRECCIÓN: Agregar ::UUID al último placeholder posicional
    query_str = """
        CALL spu_minddash_app_insert_user_org_access(
            %s::UUID,            -- 1. p_user_id
            %s::UUID,            -- 2. p_organization_id
            %s::UUID,            -- 3. p_role_id
            %s::UUID             -- 4. io_access_id (Ahora casteamos el NULL a UUID)
        );
    """

    # El orden en 'params' DEBE coincidir con el orden de los argumentos en el SP
    params = (
        access_organization_data.user_id,
        access_organization_data.organization_id,
        access_organization_data.role_id,
        None,  # Valor inicial (NULL) que ahora será casteado a UUID
    )

    # Ejecuta el CALL y obtiene el diccionario de resultados
    result: Dict[str, Any] | None = execute_procedure_with_out(query_str, params=params)

    if result and "io_access_id" in result:
        return str(result["io_access_id"])
    else:
        raise Exception(
            "Registro de acceso a organización fallido: no se pudo obtener el ID del procedimiento."
        )


def send_update_access_organization(
    access_organization_data: OrganizationUpdateAccessRequest,
) -> int:
    """
    Llama al Stored Procedure para actualizar un registro de acceso.
    Retorna el rowcount (-1 en caso de éxito con CALL).
    """
    query_str = """
        CALL spu_minddash_app_update_user_org_access(
            p_access_id := %s,
            p_user_id := %s,
            p_organization_id := %s,
            p_role_id := %s
        );
    """

    # Lista de parámetros para el Stored Procedure
    params = (
        access_organization_data.id,
        access_organization_data.user_id,
        access_organization_data.organization_id,
        access_organization_data.role_id,
    )

    # Usamos execute. El SP maneja las validaciones y lanza RAISE EXCEPTION si algo falla.
    # Si llega aquí, es exitoso.
    rowcount = execute(query_str, params=params)

    return rowcount


def send_delete_access_organization(
    access_organization_data: OrganizationDeleteAccessRequest,
) -> int:
    """
    Llama al Stored Procedure para eliminar un registro de acceso.
    Retorna el rowcount (-1 en caso de éxito con CALL).
    """
    access_id = access_organization_data.id
    # logger.info("Iniciando eliminación de acceso ID: %s", access_id)

    query_str = """
        CALL spu_minddash_app_delete_user_org_access(
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
