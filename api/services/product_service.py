from typing import List, Dict, Any
import json
from api.models.product_models import (
    Product,
    ProductByUser,
    ProductCreationResponse,
    ProductDeleteRequest,
    ProductDeleteResponse,
    ProductRegisterRequest,
    ProductUpdateRequest,
    ProductUpdateResponse,
    ProductRegisterAccessRequest,
    ProductUpdateAccessRequest,
    ProductDeleteAccessRequest,
)
from api.utils.db_client import query_all, execute_procedure_with_out, execute

import logging

logger = logging.getLogger(__name__)


def get_list_product() -> List[Product]:
    rows = query_all("""
            select
                user_id, user_role_name, user_name,
                user_phone, user_email, organization_id, organization_name,
                project_id, project_name, product_id, product_name, product_description
            from view_list_products
            
        """)
    return [Product(**r) for r in rows]


def get_list_products_by_user(user_id: str) -> List[ProductByUser]:
    """
    Obtiene la lista consolidada de productos a los que un usuario tiene acceso
    (directo, o heredado de producto).
    """
    query_str = f"""
        select
            user_id, user_role_name, user_name,
            user_phone, user_email, organization_id, organization_name,
            project_id, project_name, product_id, product_name, product_description
        from view_list_products
        WHERE
            user_id = '{user_id}'
    """
    rows = query_all(query_str)

    # Mapeo de los resultados de la DB al modelo Pydantic
    return [ProductByUser(**r) for r in rows]


def get_list_products_by_prd(product_id: str, user_id: str) -> List[Product]:
    """
    Obtiene la lista consolidada de productos a los que un usuario tiene acceso
    (directo, o heredado de producto).
    """
    query_str = f"""
        select
            user_id, user_role_name, user_name,
            user_phone, user_email, organization_id, organization_name,
            project_id, project_name, product_id, product_name, product_description
        from view_list_products
        WHERE
                product_id = '{product_id}'
            and user_id = '{user_id}'
    """

    rows = query_all(query_str)

    # Mapeo de los resultados de la DB al modelo Pydantic
    return [Product(**r) for r in rows]


def send_register_product(product_data: ProductRegisterRequest) -> str:
    """
    Llama al Stored Procedure para registrar un nuevo producto y retorna el ID.
    """

    # 1. *** MANEJAR EL JSONB: Serializar el diccionario a una cadena JSON ***
    # Si product_data.config es None o un dict vacío, json.dumps({}) funciona bien.
    # Si es None, usamos un dict vacío '{}' para que el SP use su default o acepte la cadena.
    config_data = product_data.config if product_data.config is not None else {}
    config_json_str = json.dumps(config_data)

    query_str = """
        CALL spu_minddash_app_insert_product(
            p_project_id          => %s,
            p_name                => %s,
            p_description         => %s,
            p_language            => %s,
            p_tipo                => %s,
            p_config              => %s, 
            p_welcome_message     => %s,
            p_label               => %s,
            p_label_color         => %s,
            p_max_users           => %s,
            p_is_active_rag       => %s,
            p_is_active_alerts    => %s,
            p_is_active_insight   => %s,
            io_product_id         => %s
        );
    """

    params = (
        product_data.project_id,
        product_data.name,
        product_data.description,
        product_data.language,
        product_data.tipo,
        config_json_str,
        product_data.welcome_message,
        product_data.label,
        product_data.label_color,
        product_data.max_users,
        product_data.is_active_rag,
        product_data.is_active_alerts,
        product_data.is_active_insight,
        None,
    )

    # Ejecuta el CALL y obtiene el diccionario de resultados
    result: Dict[str, Any] | None = execute_procedure_with_out(query_str, params=params)

    if result and "io_product_id" in result:
        return str(result["io_product_id"])
    else:
        # Nota: He cambiado el mensaje de error para reflejar que es un producto, no una organización.
        raise Exception(
            "Registro de producto fallido: no se pudo obtener el ID del procedimiento."
        )


def send_update_product(product_data: ProductUpdateRequest) -> int:
    """
    Llama al Stored Procedure para actualizar un producto.
    Retorna el rowcount (número de filas afectadas, o -1 si CALL es exitoso).
    """
    # 1. *** MANEJAR EL JSONB: Serializar el diccionario a una cadena JSON ***
    # Serializa el diccionario 'config' a una cadena JSON para evitar "can't adapt type 'dict'".
    config_data = product_data.config if product_data.config is not None else {}
    config_json_str = json.dumps(config_data)  # Serializa a string

    query_str = """
        CALL spu_minddash_app_update_product(
            p_product_id          := %s,
            p_project_id          := %s,
            p_name                := %s,
            p_description         := %s,
            p_language            := %s,
            p_tipo                := %s,
            p_config              := %s, 
            p_welcome_message     := %s,
            p_label               := %s,
            p_label_color         := %s,
            p_max_users           := %s,
            p_is_active           := %s,
            p_is_active_rag       := %s,
            p_is_active_alerts    := %s,
            p_is_active_insight   := %s  
        );
    """

    # 2. PARÁMETROS: DEBE HABER 15
    params = (
        product_data.id,
        product_data.project_id,
        product_data.name,
        product_data.description,
        product_data.language,
        product_data.tipo,
        config_json_str,  # <--- (7) La cadena serializada
        product_data.welcome_message,
        product_data.label,
        product_data.label_color,
        product_data.max_users,
        product_data.is_active,
        product_data.is_active_rag,
        product_data.is_active_alerts,
        product_data.is_active_insight,  # (15)
    )

    # ... resto de la función ...
    rowcount = execute(query_str, params=params)
    return rowcount


def send_delete_product(product_data: ProductDeleteRequest) -> int:
    """
    Llama al Stored Procedure para eliminar un producto.
    Retorna el rowcount (-1 si es exitoso con CALL).
    """
    # 1. *** NOMBRE DE VARIABLE Y FUNCIÓN CORREGIDO ***
    product_id = product_data.id
    logger.info("Iniciando eliminación de producto ID: %s", product_id)

    # 2. *** QUERY CORREGIDO para spu_minddash_app_delete_product ***
    query_str = """
        CALL spu_minddash_app_delete_product(
            p_product_id := %s
        );
    """

    params = (product_id,)

    try:
        rowcount = execute(query_str, params=params)
        logger.info(
            "Eliminación de producto ID: %s completada. Filas afectadas: %d",
            product_id,
            rowcount,
        )
        return rowcount
    except Exception as e:
        logger.error(
            "Error al ejecutar la eliminación para ID %s: %s", product_id, str(e)
        )
        raise


"""
    Bloque de gestion de accesos de Productos:
"""


def send_register_access_product(
    access_product_data: ProductRegisterAccessRequest,
) -> str:
    """
    Llama al Stored Procedure para registrar un nuevo acceso usuario-productos y retorna el ID.
    """

    # CORRECCIÓN: Agregar ::UUID al último placeholder posicional
    query_str = """
        CALL spu_minddash_app_insert_user_prd_access(
            %s::UUID,            -- 1. p_user_id
            %s::UUID,            -- 2. p_product_id
            %s::UUID,            -- 3. p_role_id
            %s::UUID             -- 4. io_access_id (Ahora casteamos el NULL a UUID)
        );
    """

    # El orden en 'params' DEBE coincidir con el orden de los argumentos en el SP
    params = (
        access_product_data.user_id,
        access_product_data.product_id,
        access_product_data.role_id,
        None,  # Valor inicial (NULL) que ahora será casteado a UUID
    )

    # Ejecuta el CALL y obtiene el diccionario de resultados
    result: Dict[str, Any] | None = execute_procedure_with_out(query_str, params=params)

    if result and "io_access_id" in result:
        return str(result["io_access_id"])
    else:
        raise Exception(
            "Registro de acceso a productos fallido: no se pudo obtener el ID del procedimiento."
        )


def send_update_access_product(access_product_data: ProductUpdateAccessRequest) -> int:
    """
    Llama al Stored Procedure para actualizar un registro de acceso.
    Retorna el rowcount (-1 en caso de éxito con CALL).
    """
    query_str = """
        CALL spu_minddash_app_update_user_prd_access(
            p_access_id := %s,
            p_user_id := %s,
            p_product_id := %s,
            p_role_id := %s
        );
    """

    # Lista de parámetros para el Stored Procedure
    params = (
        access_product_data.id,
        access_product_data.user_id,
        access_product_data.product_id,
        access_product_data.role_id,
    )

    # Usamos execute. El SP maneja las validaciones y lanza RAISE EXCEPTION si algo falla.
    # Si llega aquí, es exitoso.
    rowcount = execute(query_str, params=params)

    return rowcount


def send_delete_access_product(access_product_data: ProductDeleteAccessRequest) -> int:
    """
    Llama al Stored Procedure para eliminar un registro de acceso.
    Retorna el rowcount (-1 en caso de éxito con CALL).
    """
    access_id = access_product_data.id
    # logger.info("Iniciando eliminación de acceso ID: %s", aforccess_id)

    query_str = """
        CALL spu_minddash_app_delete_user_prd_access(
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
    except Exception as e:
        # Re-lanza la excepción para que el router la maneje (ej. capturar el 404/RAISE EXCEPTION)
        # logger.error("Error al ejecutar la eliminación para ID %s: %s", access_id, str(e))
        raise
