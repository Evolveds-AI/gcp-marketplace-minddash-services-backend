import json
import logging
from api.utils.secrets_util import get_connection_secret, resolve_secret_config
from api.utils.secrets_util import update_secret
from typing import Any, Dict, List

from api.models.connection_models import (
    DataConnectionByOrganization,
    DataConnectionDeleteRequest,
    DataConnectionRegisterRequest,
    DataConnectionResponse,
    DataConnectionUpdateRequest,
    GetDataConnectionsByOrganizationRequest,
    GetDataConnectionsRequest,
)
from api.utils.db_client import execute, execute_procedure_with_out, query_all
from api.utils.secrets_util import create_connection_secret

logger = logging.getLogger(__name__)


def send_register_data_connection(
    connection_data: DataConnectionRegisterRequest,
) -> str:
    """
    Llama al Stored Procedure para registrar una nueva conexión de datos y retorna el ID.
    """

    # 1. *** MANEJAR EL JSONB: Serializar el diccionario a una cadena JSON ***
    config_data = (
        connection_data.configuration
        if connection_data.configuration is not None
        else {}
    )
    secret_id = create_connection_secret(
        name=connection_data.name, parameters=connection_data.configuration
    )
    config_json_str = json.dumps({"secret_id": secret_id})
    query_str = """
        CALL spu_minddash_app_insert_data_connection(
            p_organization_id    => %s,
            p_name              => %s,
            p_type              => %s,
            p_configuration     => %s,
            io_connection_id    => %s
        );
    """

    params = (
        connection_data.organization_id,
        connection_data.name,
        connection_data.type,
        config_json_str,
        None,  # io_connection_id se llena automáticamente
    )

    # Ejecuta el CALL y obtiene el diccionario de resultados
    result: Dict[str, Any] | None = execute_procedure_with_out(query_str, params=params)

    if result and "io_connection_id" in result:
        return str(result["io_connection_id"])
    else:
        raise Exception(
            "Registro de conexión de datos fallido: no se pudo obtener el ID del procedimiento."
        )


def send_update_data_connection(connection_data: DataConnectionUpdateRequest) -> int:
    """
    Llama al Stored Procedure para actualizar una conexión de datos.
    Actualiza también el Secret en Google Secret Manager si corresponde.
    """
    config_data = connection_data.configuration or {}

    secret_id = config_data.get("secret_id")

    if not secret_id:
        raise ValueError("No se encontró 'secret_id' en configuration")

    secret_payload = json.dumps(config_data)

    update_secret(secret_id, secret_payload)

    # config_json_str = json.dumps(config_data)
    config_json_str = json.dumps({"secret_id": secret_id})

    query_str = """
        CALL spu_minddash_app_update_data_connection(
            p_connection_id     := %s,
            p_organization_id   := %s,
            p_name              := %s,
            p_type              := %s,
            p_configuration     := %s
        );
    """

    params = (
        connection_data.id,
        connection_data.organization_id,
        connection_data.name,
        connection_data.type,
        config_json_str,
    )

    rowcount = execute(query_str, params=params)
    return rowcount


def send_delete_data_connection(connection_data: DataConnectionDeleteRequest) -> int:
    """
    Llama al Stored Procedure para eliminar una conexión de datos.
    Retorna el rowcount (-1 si es exitoso con CALL).
    """
    connection_id = connection_data.id
    logger.info("Iniciando eliminación de conexión ID: %s", connection_id)

    query_str = """
        CALL spu_minddash_app_delete_data_connection(
            p_connection_id := %s
        );
    """

    params = (connection_id,)

    try:
        rowcount = execute(query_str, params=params)
        logger.info(
            "Eliminación de conexión ID: %s completada. Filas afectadas: %d",
            connection_id,
            rowcount,
        )
        return rowcount
    except Exception as e:
        logger.error(
            "Error al ejecutar la eliminación para ID %s: %s", connection_id, str(e)
        )
        raise


def get_data_connections_by_organization(
    request_data: GetDataConnectionsByOrganizationRequest,
) -> List[DataConnectionByOrganization]:
    """
    Obtiene la lista de conexiones de datos de una organización específica.
    """
    organization_id = request_data.organization_id

    query_str = f"""
        SELECT 
            connection_id,
            connection_name,
            connection_type,
            connection_configuration,
            organization_id,
            organization_name,
            organization_company_name,
            organization_country
        FROM view_list_data_connections
        WHERE organization_id = '{organization_id}'
        ORDER BY connection_name
    """

    rows = query_all(query_str)
    results = []
    # Mapeo de los resultados de la DB al modelo Pydantic
    for r in rows:
        config_resolved = resolve_secret_config(r.get("connection_configuration"))

        r["connection_configuration"] = config_resolved

        results.append(DataConnectionByOrganization(**r))
    return results


def get_data_connections(
    request_data: GetDataConnectionsRequest,
) -> List[DataConnectionResponse]:
    """
    Obtiene todas las conexiones de datos o una específica por ID.
    Si se proporciona connection_id, retorna solo esa conexión.
    Si no se proporciona connection_id, retorna todas las conexiones.
    """
    connection_id = request_data.connection_id

    if connection_id:
        query_str = f"""
            SELECT 
                connection_id,
                connection_name,
                connection_type,
                connection_configuration,
                organization_id,
                organization_name,
                organization_company_name,
                organization_country
            FROM view_list_data_connections
            WHERE connection_id = '{connection_id}'
        """
    else:
        query_str = """
            SELECT 
                connection_id,
                connection_name,
                connection_type,
                connection_configuration,
                organization_id,
                organization_name,
                organization_company_name,
                organization_country
            FROM view_list_data_connections
            ORDER BY connection_name
        """

    rows = query_all(query_str)

    results = []
    for r in rows:
        config_resolved = resolve_secret_config(r.get("connection_configuration"))
        r["connection_configuration"] = config_resolved

        results.append(DataConnectionResponse(**r))

    return results
