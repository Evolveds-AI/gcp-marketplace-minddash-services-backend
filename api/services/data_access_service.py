import json
import logging
from typing import Any, Dict, List

from fastapi import HTTPException, status

from api.models.data_access_models import (
    ClientDeployData,
    ClientDeployDeleteRequest,
    ClientDeployRegisterRequest,
    ClientDeployUpdateRequest,
    GetClientDeployByProductRequest,
    GetClientDeployRequest,
    GetRolesDataAccessByProductRequest,
    GetRolesDataAccessRequest,
    GetUserDataAccessByRoleRequest,
    GetUserDataAccessByUserRequest,
    GetUserDataAccessRequest,
    RoleDataAccessByProduct,
    RoleDataAccessDeleteRequest,
    RoleDataAccessRegisterRequest,
    RoleDataAccessResponse,
    RoleDataAccessUpdateRequest,
    UserDataAccessByRole,
    UserDataAccessByUser,
    UserDataAccessDeleteRequest,
    UserDataAccessRegisterRequest,
    UserDataAccessResponse,
    UserDataAccessUpdateRequest,
)
from api.utils.db_client import execute, execute_procedure_with_out, query_all

logger = logging.getLogger(__name__)


"""
    Gestion de acceso a tabla roles
"""


def send_register_role_data_access(role_data: RoleDataAccessRegisterRequest) -> str:
    """
    Llama al Stored Procedure, permitiendo que el driver maneje la conversión de listas a TEXT[].
    """

    # 1. PREPARACIÓN DE DATOS
    data_access = role_data.data_access if role_data.data_access is not None else {}
    data_access_json_str = json.dumps(data_access)

    # Aseguramos que metrics_access sea una lista, incluso si es opcional y no se envía
    # metrics_access_list = role_data.metrics_access if role_data.metrics_access is not None else []

    # 2. LLAMADA AL SP SIN CASTS PARA ARRAYS
    query_str = """
        CALL spu_minddash_app_insert_role_data_access(
            p_product_id      => %s::UUID,
            p_name           => %s::VARCHAR,
            p_table_names    => %s::TEXT[],         
            p_data_access    => %s::JSONB,   
            p_metrics_access => %s::TEXT[],        
            new_role_id       => %s             
        );
    """

    # 3. PARÁMETROS FINALES (Sin cambios aquí)
    params = (
        role_data.product_id,
        role_data.name,
        role_data.table_names,  # Pasamos la lista
        data_access_json_str,  # Pasamos la cadena JSON
        role_data.metrics_access,  # Pasamos la lista
        None,  # OUT placeholder
    )

    # Ejecuta el CALL
    result: Dict[str, Any] | None = execute_procedure_with_out(query_str, params=params)

    if result and "new_role_id" in result:
        return str(result["new_role_id"])
    else:
        raise Exception(
            "Registro de rol de acceso a datos fallido: no se pudo obtener el ID del procedimiento."
        )


def send_update_role_data_access(role_data: RoleDataAccessUpdateRequest) -> int:
    """
    Llama al Stored Procedure para actualizar un rol de acceso a datos.
    Normaliza listas opcionales y usa CASTS explícitos en SQL.
    Retorna el rowcount.
    """

    # 1. *** PREPARACIÓN DE DATOS (CON NORMALIZACIÓN) ***

    # a) data_access (JSONB): Serializa a string JSON. Usa {} si es None.
    data_access = role_data.data_access if role_data.data_access is not None else {}
    data_access_json_str = json.dumps(data_access)

    # b) metrics_access (TEXT[]): Normaliza a lista vacía [] si es None.
    metrics_access_list = (
        role_data.metrics_access if role_data.metrics_access is not None else []
    )

    # 2. *** LLAMADA AL SP CON CASTS EXPLÍCITOS Y SIN NOMBRES DE PARÁMETRO EN SQL ***
    # Asumimos que execute usa %s como placeholders posicionales.
    query_str = """
        CALL spu_minddash_app_update_role_data_access(
            %s::UUID,    -- p_id
            %s::UUID,    -- p_product_id (Asumiendo que el SP lo recibe aunque no lo use para actualizar)
            %s::VARCHAR, -- p_name
            %s::TEXT[],  -- p_table_names
            %s::JSONB,   -- p_data_access
            %s::TEXT[]   -- p_metrics_access
        );
    """

    # 3. *** PARÁMETROS FINALES (En orden posicional) ***
    params = (
        role_data.id,  # Convertido a UUID en SQL
        role_data.product_id,  # Convertido a UUID en SQL
        role_data.name,  # Convertido a VARCHAR en SQL
        role_data.table_names,  # Lista Python -> Convertida a TEXT[] por driver/cast
        data_access_json_str,  # String JSON -> Convertido a JSONB en SQL
        metrics_access_list,  # Lista Python -> Convertida a TEXT[] por driver/cast
    )

    # Ejecuta el CALL y obtiene el rowcount
    rowcount = execute(query_str, params=params)
    return rowcount


def send_delete_role_data_access(role_data: RoleDataAccessDeleteRequest) -> int:
    """
    Llama al Stored Procedure para eliminar un rol de acceso a datos.
    Retorna el rowcount (-1 si es exitoso con CALL).
    """
    role_id = role_data.id
    logger.info("Iniciando eliminación de rol de acceso a datos ID: %s", role_id)

    query_str = """
        CALL spu_minddash_app_delete_role_data_access(
            p_id := %s
        );
    """

    params = (role_id,)

    try:
        rowcount = execute(query_str, params=params)
        logger.info(
            "Eliminación de rol de acceso a datos ID: %s completada. Filas afectadas: %d",
            role_id,
            rowcount,
        )
        return rowcount
    except Exception as e:
        logger.error("Error al ejecutar la eliminación para ID %s: %s", role_id, str(e))
        raise


def get_roles_data_access_by_product(
    request_data: GetRolesDataAccessByProductRequest,
) -> List[RoleDataAccessByProduct]:
    """
    Obtiene la lista de roles de acceso a datos de un producto específico.
    """
    product_id = request_data.product_id

    query_str = f"""
        SELECT 
            role_id,
            role_name,
            role_table_names,
            role_data_access,
            role_metrics_access,
            product_id,
            product_name,
            created_at,
            updated_at
        FROM view_list_roles_data_access
        WHERE product_id = '{product_id}'
        ORDER BY role_name
    """

    rows = query_all(query_str)

    # Mapeo de los resultados de la DB al modelo Pydantic
    return [RoleDataAccessByProduct(**r) for r in rows]


def get_roles_data_access(
    request_data: GetRolesDataAccessRequest,
) -> List[RoleDataAccessResponse]:
    """
    Obtiene todos los roles de acceso a datos o uno específico por ID.
    Si se proporciona role_id, retorna solo ese rol.
    Si no se proporciona role_id, retorna todos los roles.
    """
    role_id = request_data.role_id

    if role_id:
        # Buscar rol específico por ID
        query_str = f"""
            SELECT 
                role_id,
                role_name,
                role_table_names,
                role_data_access,
                role_metrics_access,
                product_id,
                product_name,
                created_at,
                updated_at
            FROM view_list_roles_data_access
            WHERE role_id = '{role_id}'
        """
    else:
        # Buscar todos los roles
        query_str = """
            SELECT 
                role_id,
                role_name,
                role_table_names,
                role_data_access,
                role_metrics_access,
                product_id,
                product_name,
                created_at,
                updated_at
            FROM view_list_roles_data_access
            ORDER BY role_name
        """

    rows = query_all(query_str)

    # Mapeo de los resultados de la DB al modelo Pydantic
    return [RoleDataAccessResponse(**r) for r in rows]


"""
    Gestion de acceso a tabla usuario
"""


def send_register_user_data_access(user_data: UserDataAccessRegisterRequest) -> str:
    """
    Llama al Stored Procedure para registrar un nuevo acceso de datos de usuario y retorna el ID.
    """

    # 1. *** MANEJAR LOS JSONB: Serializar los diccionarios a cadenas JSON ***
    data_access = user_data.data_access if user_data.data_access is not None else {}
    data_access_json_str = json.dumps(data_access)

    # metrics_access = user_data.metrics_access if user_data.metrics_access is not None else {}
    # metrics_access_json_str = json.dumps(metrics_access)
    metrics_access_list = (
        user_data.metrics_access if user_data.metrics_access is not None else []
    )

    query_str = """
        CALL spu_minddash_app_insert_user_data_access(
            new_user_data_access_id => %s,
            p_role_data_id          => %s,
            p_user_id              => %s,
            p_table_names          => %s,
            p_data_access          => %s,
            p_metrics_access       => %s
        );
    """

    params = (
        None,
        user_data.role_data_id,
        user_data.user_id,
        user_data.table_names,
        data_access_json_str,
        metrics_access_list,
    )

    # Ejecuta el CALL y obtiene el diccionario de resultados
    result: Dict[str, Any] | None = execute_procedure_with_out(query_str, params=params)

    if result and "new_user_data_access_id" in result:
        return str(result["new_user_data_access_id"])
    else:
        raise Exception(
            "Registro de acceso de datos de usuario fallido: no se pudo obtener el ID del procedimiento."
        )


def send_update_user_data_access(user_data: UserDataAccessUpdateRequest) -> int:
    """
    Llama al Stored Procedure para actualizar un acceso de datos de usuario.
    Retorna el rowcount (número de filas afectadas, o -1 si CALL es exitoso).
    """

    # 1. *** MANEJAR LOS JSONB: Serializar los diccionarios a cadenas JSON ***
    data_access = user_data.data_access if user_data.data_access is not None else {}
    data_access_json_str = json.dumps(data_access)

    # metrics_access = user_data.metrics_access if user_data.metrics_access is not None else {}
    # metrics_access_json_str = json.dumps(metrics_access)
    metrics_access_list = (
        user_data.metrics_access if user_data.metrics_access is not None else []
    )

    query_str = """
        CALL spu_minddash_app_update_user_data_access(
            p_id             := %s,
            p_role_data_id   := %s,
            p_user_id        := %s,
            p_table_names    := %s,
            p_data_access    := %s,
            p_metrics_access := %s
        );
    """

    params = (
        user_data.id,
        user_data.role_data_id,
        user_data.user_id,
        user_data.table_names,
        data_access_json_str,
        metrics_access_list,
    )

    # Ejecuta el CALL y obtiene el rowcount
    rowcount = execute(query_str, params=params)
    return rowcount


def send_delete_user_data_access(user_data: UserDataAccessDeleteRequest) -> int:
    """
    Llama al Stored Procedure para eliminar un acceso de datos de usuario.
    Retorna el rowcount (-1 si es exitoso con CALL).
    """
    user_data_access_id = user_data.id
    logger.info(
        "Iniciando eliminación de acceso de datos de usuario ID: %s",
        user_data_access_id,
    )

    query_str = """
        CALL spu_minddash_app_delete_user_data_access(
            p_user_data_access_id := %s
        );
    """

    params = (user_data_access_id,)

    try:
        rowcount = execute(query_str, params=params)
        logger.info(
            "Eliminación de acceso de datos de usuario ID: %s completada. Filas afectadas: %d",
            user_data_access_id,
            rowcount,
        )
        return rowcount
    except Exception as e:
        logger.error(
            "Error al ejecutar la eliminación para ID %s: %s",
            user_data_access_id,
            str(e),
        )
        raise


def get_user_data_access_by_role(
    request_data: GetUserDataAccessByRoleRequest,
) -> List[UserDataAccessByRole]:
    """
    Obtiene la lista de accesos de datos de usuario de un rol específico.
    """
    role_data_id = request_data.role_data_id

    try:
        query_str = f"""
            SELECT 
                user_data_access_id,
                role_data_id,
                role_name,
                user_id,
                user_name,
                user_email,
                user_table_names,
                user_data_access,
                user_metrics_access,
                created_at,
                updated_at
            FROM view_list_user_data_access
            WHERE role_data_id = '{role_data_id}'
            ORDER BY created_at DESC
        """

        rows = query_all(query_str)

        # Si no hay resultados, devolver lista vacía
        if not rows:
            return []

        # Mapeo de los resultados de la DB al modelo Pydantic
        return [UserDataAccessByRole(**r) for r in rows]

    except Exception as e:
        # Si hay cualquier error (incluyendo UUID inválido), devolver lista vacía
        logger.warning(f"Error al obtener accesos por rol {role_data_id}: {e}")
        return []


def get_user_data_access_by_user(
    request_data: GetUserDataAccessByUserRequest,
) -> List[UserDataAccessByUser]:
    """
    Obtiene la lista de accesos de datos de usuario de un usuario específico.
    """
    user_id = request_data.user_id

    try:
        query_str = f"""
            SELECT 
                user_data_access_id,
                role_data_id,
                role_name,
                user_id,
                user_name,
                user_email,
                user_table_names,
                user_data_access,
                user_metrics_access,
                created_at,
                updated_at
            FROM view_list_user_data_access
            WHERE user_id = '{user_id}'
            ORDER BY created_at DESC
        """

        rows = query_all(query_str)

        # Si no hay resultados, devolver lista vacía
        if not rows:
            return []

        # Mapeo de los resultados de la DB al modelo Pydantic
        return [UserDataAccessByUser(**r) for r in rows]

    except Exception as e:
        # Si hay cualquier error (incluyendo UUID inválido), devolver lista vacía
        logger.warning(f"Error al obtener accesos por usuario {user_id}: {e}")
        return []


def get_user_data_access(
    request_data: GetUserDataAccessRequest,
) -> List[UserDataAccessResponse]:
    """
    Obtiene todos los accesos de datos de usuario o uno específico por ID.
    Si se proporciona user_data_access_id, retorna solo ese acceso.
    Si no se proporciona user_data_access_id, retorna todos los accesos.
    """
    user_data_access_id = request_data.user_data_access_id

    try:
        if user_data_access_id:
            # Buscar acceso específico por ID
            query_str = f"""
                SELECT 
                    user_data_access_id,
                    role_data_id,
                    role_name,
                    user_id,
                    user_name,
                    user_email,
                    user_table_names,
                    user_data_access,
                    user_metrics_access,
                    created_at,
                    updated_at
                FROM view_list_user_data_access
                WHERE user_data_access_id = '{user_data_access_id}'
            """
        else:
            # Buscar todos los accesos
            query_str = """
                SELECT 
                    user_data_access_id,
                    role_data_id,
                    role_name,
                    user_id,
                    user_name,
                    user_email,
                    user_table_names,
                    user_data_access,
                    user_metrics_access,
                    created_at,
                    updated_at
                FROM view_list_user_data_access
                ORDER BY created_at DESC
            """

        rows = query_all(query_str)

        # Si no hay resultados, devolver lista vacía
        if not rows:
            return []

        # Mapeo de los resultados de la DB al modelo Pydantic
        return [UserDataAccessResponse(**r) for r in rows]

    except Exception as e:
        # Si hay cualquier error (incluyendo UUID inválido), devolver lista vacía
        logger.warning(f"Error al obtener accesos de datos de usuario: {e}")
        return []


"""
"""


def get_client_deploys(request_data: GetClientDeployRequest) -> List[ClientDeployData]:
    """Obtiene todos los despliegues o uno específico por ID."""
    deploy_id = request_data.deploy_id

    if deploy_id:
        query_str = """
            SELECT * FROM clients_products_deploys
            WHERE id = %s;
        """
        params = (deploy_id,)
    else:
        query_str = """
            SELECT * FROM clients_products_deploys
            ORDER BY created_at DESC;
        """
        params = ()

    rows: List[Dict[str, Any]] = query_all(query_str, params)

    if deploy_id and not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Despliegue con ID {deploy_id} no encontrado.",
        )

    return [ClientDeployData(**r) for r in rows]


def get_client_deploys_by_product(
    request_data: GetClientDeployByProductRequest,
) -> List[ClientDeployData]:
    """Obtiene los despliegues filtrados por product_id."""
    product_id = request_data.product_id

    query_str = """
        SELECT * FROM clients_products_deploys
        WHERE product_id = %s
        ORDER BY created_at DESC;
    """
    params = (product_id,)

    rows: List[Dict[str, Any]] = query_all(query_str, params)
    return [ClientDeployData(**r) for r in rows]


def send_register_client_deploy(deploy_data: ClientDeployRegisterRequest) -> str:
    """Llama al SP para insertar un nuevo registro."""

    query_str = """
        CALL spu_minddash_app_insert_client_product_deploy(
            p_new_id => %s,
            p_product_id => %s,
            p_bucket_config => %s,
            p_gs_examples_agent => %s,
            p_gs_prompt_agent => %s,
            p_gs_prompt_sql => %s,
            p_gs_profiling_agent => %s,
            p_gs_metrics_config_agent => %s,
            p_client => %s
        );
    """

    params = (
        None,
        deploy_data.product_id,
        deploy_data.bucket_config,
        deploy_data.gs_examples_agent,
        deploy_data.gs_prompt_agent,
        deploy_data.gs_prompt_sql,
        deploy_data.gs_profiling_agent,
        deploy_data.gs_metrics_config_agent,
        deploy_data.client,
    )

    result: Dict[str, Any] | None = execute_procedure_with_out(query_str, params=params)

    if result and "p_new_id" in result:
        return str(result["p_new_id"])
    else:
        raise Exception(
            "Error al insertar el despliegue: no se pudo obtener el ID de respuesta."
        )


def send_update_client_deploy(deploy_data: ClientDeployUpdateRequest) -> None:
    """Llama al SP para actualizar un registro."""

    query_str = """
        CALL spu_minddash_app_update_client_product_deploy(
            p_id => %s,
            p_product_id => %s,
            p_bucket_config => %s,
            p_gs_examples_agent => %s,
            p_gs_prompt_agent => %s,
            p_gs_prompt_sql => %s,
            p_gs_profiling_agent => %s,
            p_gs_metrics_config_agent => %s,
            p_client => %s
        );
    """

    params = (
        deploy_data.id,
        deploy_data.product_id,
        deploy_data.bucket_config,
        deploy_data.gs_examples_agent,
        deploy_data.gs_prompt_agent,
        deploy_data.gs_prompt_sql,
        deploy_data.gs_profiling_agent,
        deploy_data.gs_metrics_config_agent,
        deploy_data.client,
    )

    try:
        execute(query_str, params=params)
    except Exception as e:
        error_detail = str(e)
        if "No se encontró la configuración con ID" in error_detail:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_detail.split("ERROR: ")[-1],
            )
        raise  # Re-lanza otros errores (FK, etc.)


def send_delete_client_deploy(deploy_data: ClientDeployDeleteRequest) -> None:
    """Llama al SP para eliminar un registro."""

    query_str = """
        CALL spu_minddash_app_delete_client_product_deploy(
            p_id => %s
        );
    """
    params = (deploy_data.id,)

    try:
        execute(query_str, params=params)
    except Exception as e:
        error_detail = str(e)
        if "No se encontró un registro con ID" in error_detail:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_detail.split("ERROR: ")[-1],
            )
        raise


def send_register_client_deploy_v2(deploy_data: ClientDeployRegisterRequest) -> str:
    """Llama al nuevo SP V2 para insertar un registro."""

    query_str = """
        CALL spu_minddash_app_insert_client_product_deployV2(
            p_new_id => %s,
            p_product_id => %s,
            p_bucket_config => %s,
            p_gs_semantic_config => %s,
            p_gs_metrics_config_agent => %s,
            p_gs_prompt_agent => %s,
            p_gs_examples_agent => %s,
            p_gs_prompt_sql => %s,
            p_gs_profiling_agent => %s,
            p_client => %s
        );
    """

    params = (
        None,
        deploy_data.product_id,
        deploy_data.bucket_config,
        deploy_data.gs_semantic_config,
        deploy_data.gs_metrics_config_agent,
        deploy_data.gs_prompt_agent,
        deploy_data.gs_examples_agent,
        deploy_data.gs_prompt_sql,
        deploy_data.gs_profiling_agent,
        deploy_data.client,
    )

    result: Dict[str, Any] | None = execute_procedure_with_out(query_str, params=params)

    if result and "p_new_id" in result:
        return str(result["p_new_id"])
    else:
        raise Exception(
            "Error al insertar el despliegue: no se pudo obtener el ID de respuesta."
        )
