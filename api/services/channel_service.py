import json
import logging
from typing import Any, Dict

from api.models.channel_models import (
    ChannelDeleteRequest,
    ChannelProductDeleteRequest,
    ChannelProductRegisterRequest,
    ChannelProductUpdateRequest,
    ChannelRegisterRequest,
    ChannelUpdateRequest,
)
from api.utils.db_client import execute, execute_procedure_with_out
from api.utils.secrets_util import (
    create_connection_secret,
    create_connection_secret_text,
)

logger = logging.getLogger(__name__)

# --- Funciones de Servicio - Channel ---


def send_register_channel(channel_data: ChannelRegisterRequest) -> str:
    """
    Llama al Stored Procedure para registrar un nuevo canal y retorna el ID.
    """
    query_str = """
        CALL spu_minddash_app_insert_channel(
            p_name          => %s,
            p_description   => %s,
            io_result_id    => %s
        );
    """

    params = (
        channel_data.name,
        channel_data.description,
        None,  # Placeholder para el parámetro INOUT
    )

    # Ejecuta el CALL y obtiene el diccionario de resultados
    # Se espera que 'io_result_id' contenga el str del nuevo canal.
    result: Dict[str, Any] | None = execute_procedure_with_out(query_str, params=params)

    if result and "io_result_id" in result:
        return str(result["io_result_id"])
    else:
        raise Exception(
            "Registro de canal fallido: no se pudo obtener el ID del procedimiento."
        )


def send_update_channel(channel_data: ChannelUpdateRequest) -> int:
    """
    Llama al Stored Procedure para actualizar un canal.
    Retorna el rowcount (o -1 si CALL es exitoso).
    """
    query_str = """
        CALL spu_minddash_app_update_channel(
            p_id            := %s,
            p_name          := %s,
            p_description   := %s
        );
    """

    params = (
        channel_data.id,
        channel_data.name,
        channel_data.description,
    )

    rowcount = execute(query_str, params=params)
    return rowcount


def send_delete_channel(channel_data: ChannelDeleteRequest) -> int:
    """
    Llama al Stored Procedure para eliminar un canal.
    Retorna el rowcount (o -1 si CALL es exitoso).
    """
    channel_id = channel_data.id
    # logger.info("Iniciando eliminación de canal ID: %s", channel_id) # Usar si logger está disponible

    query_str = """
        CALL spu_minddash_app_delete_channel(
            p_id := %s
        );
    """

    params = (channel_id,)

    try:
        rowcount = execute(query_str, params=params)
        # logger.info("Eliminación de canal ID: %s completada...", channel_id) # Usar si logger está disponible
        return rowcount
    except Exception:
        # logger.error("Error al ejecutar la eliminación para ID %s: %s", channel_id, str(e)) # Usar si logger está disponible
        raise


# --- Funciones de Servicio - Channel/Product ---

SENSITIVE_KEYS = ["secret_password_id", "app_pswd_slack", "jwtToken"]


def send_register_channel_product(cp_data: ChannelProductRegisterRequest) -> str:
    """
    Llama al Stored Procedure para registrar una nueva relación Canal-Producto.
    """
    config = cp_data.configuration.copy()
    keys_to_secure = ["app_pswd_slack", "secret_pasword_id", "jwtToken"]

    for key in keys_to_secure:
        if key in config:
            raw_value = config[key]

            # Solo procesamos si detectamos que es un valor real (no un ID md-...)
            if raw_value and not str(raw_value).startswith("md-"):
                # Generamos el nombre único para este canal/producto/llave
                deterministic_id = f"md-{cp_data.channel_id[:8]}-{cp_data.product_id[:8]}-{key.replace('_', '-')}"

                # Invocamos la lógica de nueva versión + deshabilitar antiguas
                secret_id = create_connection_secret_text(
                    secret_id=deterministic_id, secret_value=raw_value
                )

                # Guardamos el nombre del secreto en el JSON que va a la DB
                config[key] = secret_id

    # El resto del proceso sigue igual para insertar en la base de datos
    config_json_str = json.dumps(config)

    query_str = """
        CALL spu_minddash_app_insert_channel_product(
            p_channel_id          => %s,
            p_product_id          => %s,
            p_channel_product_type=> %s,  -- NUEVO CAMPO
            p_configuration       => %s,
            io_result_id          => %s
        );
    """

    params = (
        cp_data.channel_id,
        cp_data.product_id,
        cp_data.channel_product_type,  # NUEVO VALOR
        config_json_str,
        None,
    )

    result: Dict[str, Any] | None = execute_procedure_with_out(query_str, params=params)

    if result and "io_result_id" in result:
        return str(str(result["io_result_id"]))
    else:
        raise Exception(
            "Registro de relación Canal-Producto fallido: no se pudo obtener el ID del procedimiento."
        )


def send_update_channel_product(cp_data: ChannelProductUpdateRequest) -> int:
    """
    Llama al Stored Procedure para actualizar una relación Canal-Producto.
    """
    config = cp_data.configuration.copy()
    keys_to_secure = ["app_pswd_slack", "secret_pasword_id", "jwtToken"]

    for key in keys_to_secure:
        if key in config:
            raw_value = config[key]

            # Solo procesamos si detectamos que es un valor real (no un ID md-...)
            if raw_value and not str(raw_value).startswith("md-"):
                # Generamos el nombre único para este canal/producto/llave
                deterministic_id = f"md-{cp_data.channel_id[:8]}-{cp_data.product_id[:8]}-{key.replace('_', '-')}"

                # Invocamos la lógica de nueva versión + deshabilitar antiguas
                secret_id = create_connection_secret_text(
                    secret_id=deterministic_id, secret_value=raw_value
                )

                # Guardamos el nombre del secreto en el JSON que va a la DB
                config[key] = secret_id

    # El resto del proceso sigue igual para insertar en la base de datos
    config_json_str = json.dumps(config)

    # config_data = cp_data.configuration if cp_data.configuration is not None else {}
    # config_json_str = json.dumps(config_data)

    query_str = """
        CALL spu_minddash_app_update_channel_product(
            p_id                  := %s,
            p_channel_id          := %s,
            p_product_id          := %s,
            p_channel_product_type:= %s,  -- NUEVO CAMPO
            p_configuration       := %s
        );
    """

    params = (
        cp_data.id,
        cp_data.channel_id,
        cp_data.product_id,
        cp_data.channel_product_type,  # NUEVO VALOR
        config_json_str,
    )

    rowcount = execute(query_str, params=params)
    return rowcount


def send_delete_channel_product(cp_data: ChannelProductDeleteRequest) -> int:
    """
    Llama al Stored Procedure para eliminar una relación Canal-Producto. (Sin cambios)
    """
    cp_id = cp_data.id

    query_str = """
        CALL spu_minddash_app_delete_channel_product(
            p_id := %s
        );
    """

    params = (cp_id,)

    try:
        rowcount = execute(query_str, params=params)
        return rowcount
    except Exception:
        raise
