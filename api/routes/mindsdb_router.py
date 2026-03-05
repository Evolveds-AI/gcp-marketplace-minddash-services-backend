import os
from typing import Any, Dict, List, Literal, Optional, Union

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, ConfigDict
from api.utils.databricks_utils import DatabricksConnector
from api.services.file_upload_service import (
    prepare_bigquery_parameters,
    upload_file_to_gcs,
    load_file_to_bigquery_native,
    ensure_mindsdb_bigquery_connection,
)

from api.services.mindsdb_client import (
    connect,
    create_database,
    query,
    drop_database,
    update_database,
)

mindsdb_router = APIRouter(prefix="/mindsdb", tags=["MindsDB"])


class MindsdbMetaRequest(BaseModel):
    action: Literal[
        "listar_conexiones",
        "listar_esquemas",
        "listar_tablas",
        "listar_columnas",
        "listar_tablasv2",
    ]
    server_url: str
    client_name: Optional[str] = None
    database: Optional[str] = None
    engine: Optional[
        Literal[
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
            "databricks",
        ]
    ] = "postgres"
    schemas: Optional[List[str]] = None
    schema_name: Optional[str] = None
    table: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None

    # Configuración para la documentación (OpenAPI / Swagger)
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "summary": "Listar Conexiones",
                    "value": {
                        "action": "listar_conexiones",
                        "server_url": "http://0.0.0.0:47334/",
                        "client_name": "postgresql_conn_minddash_dev",
                    },
                },
                {
                    "summary": "Listar Esquemas",
                    "value": {
                        "action": "listar_esquemas",
                        "server_url": "http://0.0.0.0:47334/",
                        "client_name": "postgresql_conn_minddash_dev",
                        "database": "postgresql_conn_minddash_dev",
                    },
                },
                {
                    "summary": "Listar Tablas",
                    "value": {
                        "action": "listar_tablas",
                        "server_url": "http://0.0.0.0:47334/",
                        "client_name": "postgresql_conn_minddash_dev",
                        "database": "postgresql_conn_minddash_dev",
                        "schemas": ["public"],
                    },
                },
                {
                    "summary": "Listar Columnas",
                    "value": {
                        "action": "listar_columnas",
                        "server_url": "http://0.0.0.0:47334/",
                        "client_name": "postgresql_conn_minddash_dev",
                        "database": "postgresql_conn_minddash_dev",
                        "schemas": ["public"],
                        "schema_name": "public",
                        "table": "raw_base_kdm_ppt",
                    },
                },
            ]
        }
    )


class MindsdbMetaResponse(BaseModel):
    status: str
    conexiones: Optional[List[str]] = None
    esquemas: Optional[List[str]] = None
    tablas: Optional[List[Dict[str, str]]] = None
    columnas: Optional[List[Dict[str, str]]] = None
    message: Optional[str] = None


@mindsdb_router.post(
    "/meta",
    response_model=MindsdbMetaResponse,
    summary="Permite explorar y obtener metadatos de las fuentes de datos conectadas a MindsDB.",
    description=(
        "Permite explorar la estructura de las bases de datos conectadas a MindsDB, "
        "basándose en el parámetro `action`:\n\n"
        "1. **`listar_conexiones`**: Muestra las conexiones registradas, filtrables por `client_name`.\n"
        "2. **`listar_esquemas`**: Muestra los esquemas de una `database` específica.\n"
        "3. **`listar_tablas`**: Muestra las tablas para una lista de `schemas` dentro de una `database`.\n"
        "4. **`listar_columnas`**: Muestra el nombre, tipo de dato y nulabilidad de las columnas para una `schema` y `table` específicas.\n\n"
        "**Parámetros clave:** `action` (obligatorio), `database` (para esquemas/tablas/columnas), "
        "`engine` (postgres/mysql/bigquery), `schema_name` y `table`."
    ),
)
async def mindsdb_meta(req: MindsdbMetaRequest):
    if req.engine == "databricks":
        if not req.parameters:
            raise HTTPException(
                status_code=400,
                detail="Se requieren 'parameters' con credenciales para Databricks",
            )

        # 1. Instanciar el conector
        try:
            connector = DatabricksConnector(
                databricks_host=req.parameters.get("DATABRICKS_HOST"),
                http_path=req.parameters.get("DATABRICKS_HTTP_PATH"),
                client_id=req.parameters.get("DATABRICKS_CLIENT_ID"),
                client_secret=req.parameters.get(
                    "DATABRICKS_CLIENT_SECRET"
                ),  # Si tu conector lo usa
            )
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error iniciando conector Databricks: {str(e)}"
            )

        def run_databricks_query(sql):
            try:
                # Asumimos que connector.query devuelve un DataFrame de pandas
                return connector.query(sql)
            except Exception as e:
                print(f"Error query Databricks: {sql} | Error: {e}")
                raise HTTPException(
                    status_code=500, detail=f"Error en Databricks: {str(e)}"
                )

        # A. LISTAR CONEXIONES (Mapeado a CATÁLOGOS en Databricks)
        # Esto devolverá: ["planificacion_comercial", "hive_metastore", "samples", etc.]
        if req.action == "listar_conexiones":
            db_query = "SHOW CATALOGS"
            rows = run_databricks_query(db_query)

            print("rows")
            print(rows)
            # La columna suele llamarse 'catalog' en Databricks SQL
            conexiones = []
            for row in rows:
                if hasattr(row, "catalog"):
                    conexiones.append(row.catalog)
                else:
                    conexiones.append(row[0])  # Fallback por posición

            if req.client_name:
                filtro = req.client_name.lower()
                conexiones = [c for c in conexiones if filtro in str(c).lower()]

            return MindsdbMetaResponse(status="success", conexiones=sorted(conexiones))

        # B. LISTAR ESQUEMAS (Mapeado a SCHEMAS dentro de un CATÁLOGO)
        # Req: req.database = "planificacion_comercial"
        if req.action == "listar_esquemas":
            if not req.database:
                raise HTTPException(
                    status_code=400,
                    detail="Falta 'database' (Catálogo) para listar esquemas",
                )

            # Usamos el catálogo seleccionado para mostrar sus esquemas
            # Ejemplo: SHOW SCHEMAS IN planificacion_comercial
            db_query = f"SHOW SCHEMAS IN {req.database}"
            rows = run_databricks_query(db_query)

            # En Databricks SQL 'SHOW SCHEMAS', la columna suele ser 'databaseName'
            esquemas = []
            for row in rows:
                if hasattr(row, "databaseName"):
                    esquemas.append(row.databaseName)
                elif hasattr(row, "schema_name"):
                    esquemas.append(row.schema_name)
                else:
                    esquemas.append(row[0])

            return MindsdbMetaResponse(status="success", esquemas=esquemas)

        # C. LISTAR TABLAS
        if req.action == "listar_tablas":
            schemas = req.schemas or ([req.schema_name] if req.schema_name else None)
            if not schemas:
                raise HTTPException(status_code=400, detail="Faltan 'schemas'")

            catalog = req.database
            all_tables = []

            for schema in schemas:
                # Usamos information_schema para obtener nombres consistentes
                db_query = f"""
                SELECT table_schema, table_name
                FROM {catalog}.information_schema.tables
                WHERE table_schema = '{schema}'
                  AND table_type IN ('MANAGED', 'EXTERNAL', 'BASE TABLE', 'VIEW')
                """
                rows = run_databricks_query(db_query)

                for row in rows:
                    # Aquí accedemos explícitamente a los atributos del SELECT
                    all_tables.append(
                        {"schema": row.table_schema, "table": row.table_name}
                    )

            return MindsdbMetaResponse(status="success", tablas=all_tables)

        if req.action == "listar_tablasv2":
            if not req.database:
                raise HTTPException(
                    status_code=400,
                    detail="Falta 'database' (catalog) para Databricks",
                )

            schemas = req.schemas or ([req.schema_name] if req.schema_name else None)
            if not schemas:
                raise HTTPException(status_code=400, detail="Faltan 'schemas'")

            catalog = req.database
            all_tables = []

            for schema in schemas:
                # ✅ Databricks SQL nativo (no usa information_schema)
                db_query = f"SHOW TABLES IN {catalog}.{schema}"
                rows = run_databricks_query(db_query)

                for row in rows:
                    # Databricks devuelve:
                    # database | tableName | isTemporary
                    table_name = row.tableName if hasattr(row, "tableName") else row[1]

                    all_tables.append(
                        {
                            "schema": schema,
                            "table": table_name,
                        }
                    )

            return MindsdbMetaResponse(status="success", tablas=all_tables)

        # D. LISTAR COLUMNAS
        if req.action == "listar_columnas":
            if not req.schema_name or not req.table or not req.database:
                raise HTTPException(status_code=400, detail="Faltan datos")

            db_query = f"""
            SELECT column_name, data_type, is_nullable
            FROM {req.database}.information_schema.columns
            WHERE table_schema = '{req.schema_name}' 
              AND table_name = '{req.table}'
            ORDER BY ordinal_position
            """
            rows = run_databricks_query(db_query)

            columnas = [
                {
                    "name": row.column_name,
                    "data_type": row.data_type,
                    "is_nullable": row.is_nullable,
                }
                for row in rows
            ]
            return MindsdbMetaResponse(status="success", columnas=columnas)

        return MindsdbMetaResponse(
            status="error", detail="Acción desconocida Databricks"
        )

    if not req.server_url:
        raise HTTPException(
            status_code=400, detail="Falta server_url para motores MindsDB"
        )

    server = connect(req.server_url)

    if not req.engine or req.engine == "postgres":
        try:
            # Usamos tu propuesta para buscar el motor exacto de la conexión
            # Filtramos por el nombre de la base de datos que viene en el request
            engine_query = f"""
                SELECT engine 
                FROM information_schema.databases 
                WHERE name = '{req.database}'
            """
            df_engine = query(server, engine_query)

            # Normalizamos nombres de columnas por si vienen en Mayúsculas
            df_engine.columns = [c.lower() for c in df_engine.columns]

            if not df_engine.empty:
                req.engine = df_engine.iloc[0]["engine"].lower()
                print(
                    f"Motor detectado automáticamente para '{req.database}': {req.engine}"
                )
            else:
                print(f"No se encontró información para la conexión '{req.database}'")

        except Exception as e:
            print(f"Error al consultar information_schema: {e}")

    if req.action == "listar_conexiones":
        if not req.client_name or not req.client_name.strip():
            raise HTTPException(
                status_code=400, detail="Falta 'client_name' para listar conexiones"
            )
        db_query = "SHOW DATABASES;"
        df = query(server, db_query)
        if "name" in df.columns:
            conexiones = df["name"].tolist()
        elif "database_name" in df.columns:
            conexiones = df["database_name"].tolist()
        else:
            conexiones = df.iloc[:, 0].tolist()
        filtro = req.client_name.lower()
        filtradas = sorted([c for c in conexiones if filtro in str(c).lower()])
        return MindsdbMetaResponse(status="success", conexiones=filtradas)

    if not req.database:
        raise HTTPException(status_code=400, detail="Falta 'database' para esta acción")

    if req.action == "listar_esquemas":
        if req.engine in ("postgres", "mysql", "mariadb", "redshift"):
            db_query = f"""
            SELECT schema_name
            FROM {req.database}.information_schema.schemata
            WHERE schema_name NOT IN ('pg_catalog','information_schema')
            ORDER BY schema_name;
            """
        elif req.engine == "bigquery":
            # db_query = f"""
            # SELECT schema_name
            # FROM {req.database}.INFORMATION_SCHEMA.SCHEMATA
            # ORDER BY schema_name;
            # """

            db_query = f"""
                SELECT DISTINCT table_schema AS schema_name
                FROM `{req.database}`.INFORMATION_SCHEMA.TABLES
                ORDER BY schema_name;
            """

            print("db_query")
            print(db_query)
        elif req.engine in ("mssql", "synapsemssql"):
            db_query = f"""
            SELECT name
            FROM {req.database}.sys.schemas
            WHERE name NOT IN ('sys', 'INFORMATION_SCHEMA')
            ORDER BY name;
            """
        elif req.engine == "snowflake":
            db_query = f"""
            SELECT schema_name
            FROM {req.database}.information_schema.schemata
            ORDER BY schema_name;
            """
        elif req.engine in ("aurora", "aurorapostgres", "auroramysql"):
            db_query = f"""
            SELECT schema_name
            FROM {req.database}.information_schema.schemata
            WHERE schema_name NOT IN ('pg_catalog','information_schema')
            ORDER BY schema_name;
            """
        elif req.engine == "hana":
            db_query = f"""
            SELECT schema_name
            FROM {req.database}.SYS.SCHEMAS
            ORDER BY schema_name;
            """
        elif req.engine == "oracle":
            db_query = f"""
            SELECT DISTINCT owner AS schema_name
            FROM {req.database}.all_tables
            ORDER BY owner;
            """
        elif req.engine == "teradata":
            db_query = f"""
            SELECT DatabaseName
            FROM {req.database}.DBC.Databases
            ORDER BY DatabaseName;
            """
        elif req.engine == "clickhouse":
            db_query = f"""
            SELECT name
            FROM {req.database}.system.databases
            ORDER BY name;
            """
        elif req.engine == "databricks":
            pass
        else:
            db_query = f"SELECT schema_name FROM {req.database}.information_schema.schemata ORDER BY schema_name;"
        df = query(server, db_query)
        # Manejar diferentes nombres de columna según el engine
        if req.engine in ("mssql", "synapsemssql"):
            esquemas = (
                df["name"].tolist() if "name" in df.columns else df.iloc[:, 0].tolist()
            )
        elif req.engine == "teradata":
            esquemas = (
                df["DatabaseName"].tolist()
                if "DatabaseName" in df.columns
                else df.iloc[:, 0].tolist()
            )
        elif req.engine == "clickhouse":
            esquemas = (
                df["name"].tolist() if "name" in df.columns else df.iloc[:, 0].tolist()
            )
        else:
            esquemas = (
                df["schema_name"].tolist()
                if "schema_name" in df.columns
                else df.iloc[:, 0].tolist()
            )
        return MindsdbMetaResponse(status="success", esquemas=esquemas)

    if req.action == "listar_tablas":
        schemas = req.schemas or ([req.schema_name] if req.schema_name else None)
        if not schemas:
            raise HTTPException(
                status_code=400, detail="Faltan 'schemas' o 'schema' para listar tablas"
            )
        schemas_list = ",".join([f"'{s}'" for s in schemas])
        if req.engine in ("postgres", "mysql", "mariadb", "redshift"):
            db_query = f"""
            SELECT table_schema, table_name
            FROM {req.database}.information_schema.tables
            WHERE table_type in ('BASE TABLE', 'VIEW') 
              AND table_schema IN ({schemas_list})
            ORDER BY table_schema, table_name;
            """
        elif req.engine == "bigquery":
            db_query = f"""
            SELECT table_schema, table_name
            FROM {req.database}.INFORMATION_SCHEMA.TABLES
            WHERE table_schema IN ({schemas_list})
              AND table_type in ('BASE TABLE', 'VIEW') 
            ORDER BY table_schema, table_name;
            """
        elif req.engine in ("mssql", "synapsemssql"):
            db_query = f"""
            SELECT table_schema, table_name
            FROM {req.database}.INFORMATION_SCHEMA.TABLES
            WHERE table_type = 'BASE TABLE'
              AND table_schema IN ({schemas_list})
            ORDER BY table_schema, table_name;
            """
        elif req.engine == "snowflake":
            db_query = f"""
            SELECT table_schema, table_name
            FROM {req.database}.INFORMATION_SCHEMA.TABLES
            WHERE table_type = 'BASE TABLE'
              AND table_schema IN ({schemas_list})
            ORDER BY table_schema, table_name;
            """
        elif req.engine in ("aurora", "aurorapostgres", "auroramysql"):
            db_query = f"""
            SELECT table_schema, table_name
            FROM {req.database}.information_schema.tables
            WHERE table_type = 'BASE TABLE'
              AND table_schema IN ({schemas_list})
            ORDER BY table_schema, table_name;
            """
        elif req.engine == "hana":
            db_query = f"""
            SELECT schema_name AS table_schema, table_name
            FROM {req.database}.SYS.TABLES
            WHERE schema_name IN ({schemas_list})
            ORDER BY schema_name, table_name;
            """
        elif req.engine == "oracle":
            db_query = f"""
            SELECT owner AS table_schema, table_name
            FROM {req.database}.all_tables
            WHERE owner IN ({schemas_list})
            ORDER BY owner, table_name;
            """
        elif req.engine == "teradata":
            db_query = f"""
            SELECT DatabaseName AS table_schema, TableName AS table_name
            FROM {req.database}.DBC.Tables
            WHERE DatabaseName IN ({schemas_list})
            ORDER BY DatabaseName, TableName;
            """
        elif req.engine == "clickhouse":
            db_query = f"""
            SELECT database AS table_schema, name AS table_name
            FROM {req.database}.system.tables
            WHERE database IN ({schemas_list})
            ORDER BY database, name;
            """
        elif req.engine == "databricks":
            pass
        else:
            db_query = f"SELECT table_schema, table_name FROM {req.database}.information_schema.tables WHERE table_schema IN ({schemas_list});"

        print(f"db_query: {db_query}")
        df = query(server, db_query)

        df.columns = [c.lower() for c in df.columns]

        tablas = [
            {"schema": r["table_schema"], "table": r["table_name"]}
            for _, r in df.iterrows()
        ]
        return MindsdbMetaResponse(status="success", tablas=tablas)

    if req.action == "listar_columnas":
        if not req.schema_name or not req.table:
            raise HTTPException(
                status_code=400,
                detail="Faltan 'schema' y/o 'table' para listar columnas",
            )
        if req.engine in ("postgres", "mysql", "mariadb", "redshift"):
            db_query = f"""
            SELECT column_name, data_type, is_nullable
            FROM {req.database}.information_schema.columns
            WHERE table_schema = '{req.schema_name}' AND table_name = '{req.table}'
            ORDER BY ordinal_position;
            """
        elif req.engine == "bigquery":
            db_query = f"""
            SELECT column_name, data_type, is_nullable
            FROM {req.database}.INFORMATION_SCHEMA.COLUMNS
            WHERE table_schema = '{req.schema_name}' AND table_name = '{req.table}'
            ORDER BY ordinal_position;
            """
        elif req.engine in ("mssql", "synapsemssql"):
            db_query = f"""
            SELECT column_name, data_type, is_nullable
            FROM {req.database}.INFORMATION_SCHEMA.COLUMNS
            WHERE table_schema = '{req.schema_name}' AND table_name = '{req.table}'
            ORDER BY ordinal_position;
            """
        elif req.engine == "snowflake":
            db_query = f"""
            SELECT column_name, data_type, is_nullable
            FROM {req.database}.INFORMATION_SCHEMA.COLUMNS
            WHERE table_schema = '{req.schema_name}' AND table_name = '{req.table}'
            ORDER BY ordinal_position;
            """
        elif req.engine in ("aurora", "aurorapostgres", "auroramysql"):
            db_query = f"""
            SELECT column_name, data_type, is_nullable
            FROM {req.database}.information_schema.columns
            WHERE table_schema = '{req.schema_name}' AND table_name = '{req.table}'
            ORDER BY ordinal_position;
            """
        elif req.engine == "hana":
            db_query = f"""
            SELECT column_name, data_type, NULL AS is_nullable
            FROM {req.database}.SYS.COLUMNS
            WHERE schema_name = '{req.schema_name}' AND table_name = '{req.table}'
            ORDER BY position;
            """
        elif req.engine == "oracle":
            db_query = f"""
            SELECT column_name, data_type, nullable AS is_nullable
            FROM {req.database}.all_tab_columns
            WHERE owner = '{req.schema_name}' AND table_name = '{req.table}'
            ORDER BY column_id;
            """
        elif req.engine == "teradata":
            db_query = f"""
            SELECT ColumnName AS column_name, ColumnType AS data_type, Nullable AS is_nullable
            FROM {req.database}.DBC.Columns
            WHERE DatabaseName = '{req.schema_name}' AND TableName = '{req.table}'
            ORDER BY ColumnId;
            """
        elif req.engine == "clickhouse":
            db_query = f"""
            SELECT name AS column_name, type AS data_type, NULL AS is_nullable
            FROM {req.database}.system.columns
            WHERE database = '{req.schema_name}' AND table = '{req.table}'
            ORDER BY position;
            """
        elif req.engine == "databricks":
            pass
        else:
            db_query = f"SELECT column_name, data_type FROM {req.database}.information_schema.columns WHERE table_schema='{req.schema_name}' AND table_name='{req.table}';"

        print(f"db_query: {db_query}")
        df = query(server, db_query)

        df.columns = [c.lower() for c in df.columns]

        columnas = [
            {
                "name": r["column_name"],
                "data_type": r["data_type"],
                "is_nullable": r.get("is_nullable"),
            }
            for _, r in df.iterrows()
        ]
        return MindsdbMetaResponse(status="success", columnas=columnas)

    raise HTTPException(status_code=400, detail=f"Acción no soportada: {req.action}")


class CreateConnectionResponse(BaseModel):
    status: str
    message: Optional[str] = None
    # Campos adicionales cuando se sube un archivo a BigQuery
    gs_uri: Optional[str] = None
    file_id: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    format: Optional[str] = None
    table_reference: Optional[str] = None
    dataset_name: Optional[str] = None
    table_name: Optional[str] = None
    row_count: Optional[int] = None
    mindsdb_connection_name: Optional[str] = None
    mindsdb_connection_created: Optional[bool] = None


class UpdateConnectionRequest(BaseModel):
    server_url: str
    name: str
    engine: Literal[
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
    ]
    parameters: Dict[str, Any]

    class Config:
        json_schema_extra = {
            "example": {
                "server_url": "http://0.0.0.0:47334",
                "name": "postgresql_conn_minddash_demo",
                "engine": "postgres",
                "parameters": {
                    "host": "0.0.0.0",
                    "port": 5432,
                    "database": "minddash_platform",
                    "user": "nuevo_usuario",
                    "password": "nueva_password",
                },
            }
        }


class DeleteConnectionRequest(BaseModel):
    server_url: str
    name: str
    engine: Literal[
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
    ]

    class Config:
        json_schema_extra = {
            "example": {
                "server_url": "http://0.0.0.0:47334",
                "name": "postgresql_conn_minddash_demo",
                "engine": "postgres",
            }
        }


@mindsdb_router.post(
    "/connections",
    response_model=CreateConnectionResponse,
    summary="Crea una nueva conexión o base de datos dentro de MindsDB.",
    description=(
        "Endpoint centralizado para crear conexiones MindsDB. Soporta dos modos:\n\n"
        "**Modo 1: Conexión estándar** (sin archivo)\n"
        "- Crea una conexión a PostgreSQL, MySQL, BigQuery, etc.\n"
        "- Para BigQuery, si no se proporciona 'service_account_json', se lee del archivo local.\n\n"
        "**Modo 2: Flujo completo con archivo** (solo para BigQuery)\n"
        "- Si se proporciona un archivo y engine='bigquery', ejecuta el flujo completo:\n"
        "  1. Sube archivo a GCS (convierte Excel a CSV si es necesario)\n"
        "  2. Carga datos a BigQuery como tabla nativa\n"
        "  3. Crea/verifica conexión MindsDB automáticamente\n"
        "- Formatos soportados: CSV, TXT, Excel (.xlsx, .xls), Parquet, Avro\n\n"
        "**Parámetros requeridos para modo con archivo:**\n"
        "- `file`: Archivo a subir\n"
        "- `product_id`: ID del producto (para organizar datasets)\n"
        "- `bucket_name`: Nombre del bucket de GCS\n"
        "- `table_name`: Nombre de la tabla en BigQuery\n"
        "- `server_url`: URL del servidor MindsDB\n"
        "- `file_format`: CSV, PARQUET o AVRO (opcional, default: CSV)\n"
    ),
)
async def create_connection(
    # Parámetros básicos de conexión
    server_url: Optional[str] = Form(None),
    name: str = Form(...),
    engine: str = Form(...),
    # Archivo opcional (solo para BigQuery con flujo completo)
    file: Optional[Union[UploadFile, str]] = File(None),
    # Parámetros opcionales para flujo con archivo
    product_id: Optional[str] = Form(None),
    bucket_name: Optional[str] = Form(None),
    table_name: Optional[str] = Form(None),
    file_format: str = Form("CSV"),
    skip_leading_rows: int = Form(1),
    field_delimiter: str = Form(","),
    quote_character: str = Form('"'),
    sheet_name: Optional[str] = Form(None),
    # Parámetros JSON (para conexiones estándar)
    parameters: Optional[str] = Form(None),
):
    """
    Endpoint centralizado que maneja ambos casos:
    1. Conexión estándar (sin archivo)
    2. Flujo completo con archivo (solo BigQuery)
    """
    import json

    # --- LIMPIEZA DE VALORES POR DEFECTO FILE ---
    if isinstance(file, str):
        file = None

    default_url = os.getenv("MINDSDB_URL")
    if server_url is not None and server_url != "":
        active_server_url = server_url
    else:
        active_server_url = default_url
    # Validar engine
    valid_engines = [
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
    ]
    if engine.lower() not in valid_engines:
        raise HTTPException(
            status_code=400,
            detail=f"Engine no soportado: {engine}. Engines válidos: {', '.join(valid_engines)}",
        )

    # MODO 2: Flujo completo con archivo (solo para BigQuery)
    if file and file.filename:
        if engine.lower() != "bigquery":
            raise HTTPException(
                status_code=400,
                detail=f"El flujo con archivo solo está disponible para BigQuery. Engine recibido: {engine}",
            )

        # Validar parámetros requeridos para flujo con archivo
        if not product_id or not bucket_name or not table_name:
            raise HTTPException(
                status_code=400,
                detail="Para el flujo con archivo se requieren: product_id, bucket_name y table_name",
            )

        # Validar formato de archivo
        file_extension = os.path.splitext(file.filename)[1].lower()
        supported_formats = [".csv", ".txt", ".xlsx", ".xls", ".parquet", ".avro"]
        if file_extension not in supported_formats:
            raise HTTPException(
                status_code=400,
                detail=f"Formato no soportado: {file_extension}. Formatos soportados: {', '.join(supported_formats)}",
            )

        # Validar tamaño (límite de 100MB)
        MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
        file.file.seek(0, 2)
        file_size = file.file.tell()
        file.file.seek(0)
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"Archivo demasiado grande: {file_size} bytes. Máximo permitido: {MAX_FILE_SIZE} bytes",
            )

        # Validar formato
        if file_format not in ["CSV", "PARQUET", "AVRO"]:
            raise HTTPException(
                status_code=400,
                detail=f"Formato inválido: {file_format}. Use CSV, PARQUET o AVRO",
            )

        # Obtener project_id
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        if not project_id:
            try:
                sa_key_path = os.getenv(
                    "GOOGLE_APPLICATION_CREDENTIALS", "./api/secret/sa-key.json"
                )
                with open(sa_key_path, "r") as f:
                    sa_key = json.load(f)
                    project_id = sa_key.get("project_id")
            except Exception:
                pass

        if not project_id:
            raise HTTPException(
                status_code=500,
                detail="No se pudo determinar el project_id de GCP. Configure GOOGLE_CLOUD_PROJECT.",
            )

        # 1. Subir archivo a GCS
        upload_result = upload_file_to_gcs(
            file=file,
            bucket_name=bucket_name,
            product_id=product_id,
            convert_excel=True,
        )

        gs_uri = upload_result["gs_uri"]
        file_id = upload_result["file_id"]
        file_name = upload_result["file_name"]
        file_size_result = upload_result["file_size"]
        format_type = upload_result["format"]

        # Si era Excel y se convirtió, actualizar file_format
        if format_type == "CSV" and file_name.lower().endswith((".xlsx", ".xls")):
            file_format = "CSV"

        # 2. Cargar a BigQuery
        load_result = load_file_to_bigquery_native(
            gs_uri=gs_uri,
            project_id=project_id,
            product_id=product_id,
            table_name=table_name,
            file_format=file_format,
            skip_leading_rows=skip_leading_rows,
            field_delimiter=field_delimiter,
            quote_character=quote_character,
        )

        dataset_name = load_result["dataset_name"]
        table_ref_name = load_result["table_name"]
        table_reference = load_result["table_reference"]
        row_count = load_result["row_count"]

        # 3. Crear/verificar conexión MindsDB
        mindsdb_connection_name, connection_created = (
            ensure_mindsdb_bigquery_connection(
                server_url=active_server_url,
                product_id=product_id,
                project_id=project_id,
                dataset_name=dataset_name,
            )
        )

        # Retornar resultado completo
        return CreateConnectionResponse(
            status="success",
            message=f"Conexión '{name}' creada y archivo cargado exitosamente",
            gs_uri=gs_uri,
            file_id=file_id,
            file_name=file_name,
            file_size=file_size_result,
            format=format_type,
            table_reference=table_reference,
            dataset_name=dataset_name,
            table_name=table_ref_name,
            row_count=row_count,
            mindsdb_connection_name=mindsdb_connection_name,
            mindsdb_connection_created=connection_created,
        )

    # MODO 1: Conexión estándar (sin archivo)
    # Parsear parámetros JSON si vienen como string
    if parameters:
        try:
            params_dict = (
                json.loads(parameters) if isinstance(parameters, str) else parameters
            )
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=400,
                detail="El parámetro 'parameters' debe ser un JSON válido",
            )
    else:
        raise HTTPException(
            status_code=400,
            detail="Se requiere el parámetro 'parameters' cuando no se proporciona un archivo",
        )

    server = connect(active_server_url)

    # Para BigQuery, preparar parámetros automáticamente si es necesario
    final_parameters = params_dict
    if engine.lower() == "bigquery":
        service_account_json = params_dict.get("service_account_json")
        project_id = params_dict.get("project_id")
        dataset_name = params_dict.get("dataset")

        if not project_id or not dataset_name:
            raise HTTPException(
                status_code=400,
                detail="Para BigQuery se requieren los parámetros 'project_id' y 'dataset'",
            )

        # Preparar parámetros usando la misma función que usa el flujo de file upload
        final_parameters = prepare_bigquery_parameters(
            project_id=project_id,
            dataset_name=dataset_name,
            service_account_json=service_account_json,
        )

    create_database(server, name, engine, final_parameters)
    return CreateConnectionResponse(
        status="success", message=f"Conexión '{name}' creada exitosamente"
    )


@mindsdb_router.put(
    "/updateConnections",
    response_model=CreateConnectionResponse,
    summary="Actualiza una conexión existente.",
    description="Actualiza los parámetros de una conexión existente eliminándola y recreándola.",
)
async def update_connection(req: UpdateConnectionRequest):
    # 1. Conectar al servidor
    server = connect(req.server_url)

    # 2. Ejecutar lógica de actualización (Drop + Create)
    update_database(server, req.name, req.engine, req.parameters)

    return CreateConnectionResponse(
        status="success", message=f"Conexión '{req.name}' actualizada correctamente."
    )


@mindsdb_router.delete(
    "/dropConnections",
    response_model=CreateConnectionResponse,
    summary="Elimina una conexión.",
    description="Elimina una base de datos o conexión de MindsDB enviando los datos en el cuerpo de la petición.",
)
async def delete_connection(req: DeleteConnectionRequest):
    # 1. Conectar al servidor
    server = connect(req.server_url)

    # 2. (Opcional) Aquí podrías agregar lógica para validar que el 'engine'
    # coincida antes de borrar, pero para el borrado simple basta con el nombre.

    # 3. Ejecutar lógica de eliminación
    drop_database(server, req.name)

    return CreateConnectionResponse(
        status="success",
        message=f"Conexión '{req.name}' (engine: {req.engine}) eliminada correctamente.",
    )
