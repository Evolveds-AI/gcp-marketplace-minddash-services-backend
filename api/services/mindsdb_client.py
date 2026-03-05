import json
import re
from typing import Any, Dict

import mindsdb_sdk
from fastapi import HTTPException
import time


def connect(server_url: str) -> Any:
    try:
        return mindsdb_sdk.connect(server_url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error conectando a MindsDB: {e}")


def query(server: Any, sql: str):
    try:
        return server.query(sql).fetch()
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error ejecutando consulta en MindsDB: {e}"
        )

    # def query(server, sql, max_retries=3):
    #     last_error = None
    #     for attempt in range(max_retries):
    #         try:
    #             # Intentamos la consulta
    #             return server.query(sql).fetch()
    #         except Exception as e:
    #             last_error = str(e)
    #             # Si el error es de conexión (DPY-1001 o DPI-1010)
    #             if "not connected" in last_error.lower() or "DPY-1001" in last_error:
    #                 print(f"Conexión Oracle/VPN perdida (Intento {attempt+1}/{max_retries}). Reconectando...")
    #                 time.sleep(1 * (attempt + 1)) # Espera incremental
    #                 continue
    #             else:
    #                 # Si es un error de sintaxis u otro, no reintentamos
    #                 break

    # print(f"Falló tras {max_retries} intentos. Error final: {last_error}")
    # raise HTTPException(
    #     status_code=500, detail=f"Error tras reintentos en MindsDB: {last_error}"
    # )


def create_database(
    server: Any, name: str, engine: str, parameters: Dict[str, Any]
) -> None:
    """Crea una conexión (database) en MindsDB."""
    try:
        if not name or not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name):
            raise HTTPException(
                status_code=400,
                detail="Nombre de conexión inválido. Use [A-Za-z_][A-Za-z0-9_]*",
            )

        engine_normalized = (engine or "").lower()
        if engine_normalized not in (
            "postgres",
            "mysql",
            "bigquery",
            "mariadb",
            "mssql",
            "synapsemssql",
            "redshift",
            "snowflake",
            "aurora",
            "aurorapostgres",
            "auroramysql",
            "hana",
            "oracle",
            "teradata",
            "clickhouse",
        ):
            raise HTTPException(
                status_code=400, detail=f"Engine no soportado: {engine}"
            )

        params_json = json.dumps(parameters or {}, ensure_ascii=False)
        if engine_normalized == "aurorapostgres":
            engine_normalized = "postgres"
        if engine_normalized == "auroramysql":
            engine_normalized = "mysql"
        if engine_normalized == "synapsemssql":
            engine_normalized = "mssql"
        sql = f"CREATE DATABASE {name} WITH ENGINE = '{engine_normalized}', PARAMETERS = {params_json};"
        print("sql", sql)
        server.query(sql).fetch()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error creando conexión en MindsDB: {e}"
        )


def drop_database(server: Any, name: str) -> None:
    """Elimina una conexión (database) en MindsDB."""
    try:
        # Validación de seguridad básica del nombre
        if not name or not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name):
            raise HTTPException(status_code=400, detail="Nombre de conexión inválido.")

        # SQL para borrar
        sql = f"DROP DATABASE IF EXISTS {name};"
        server.query(sql).fetch()
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error eliminando conexión en MindsDB: {e}"
        )


def update_database(
    server: Any, name: str, engine: str, parameters: Dict[str, Any]
) -> None:
    """Actualiza una conexión recreándola."""
    # 1. Eliminamos la existente
    drop_database(server, name)
    # 2. Creamos la nueva con los datos actualizados
    # Reutilizamos tu función existente create_database
    create_database(server, name, engine, parameters)


def database_exists(server: Any, name: str) -> bool:
    """Verifica si una conexión (database) existe en MindsDB"""
    try:
        db_query = "SHOW DATABASES;"
        df = query(server, db_query)

        # Buscar el nombre en las columnas comunes
        if "name" in df.columns:
            databases = df["name"].tolist()
        elif "database_name" in df.columns:
            databases = df["database_name"].tolist()
        else:
            databases = df.iloc[:, 0].tolist()

        return name in databases
    except Exception as e:
        # Si hay error al consultar, asumir que no existe
        return False
