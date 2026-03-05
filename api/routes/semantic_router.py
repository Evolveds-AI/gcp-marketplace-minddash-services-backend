from asyncio import TaskGroup
from unittest import async_case
from api.models.data_access_models import ClientDeployRegisterRequest
from api.services.connection_service import get_data_connections
from fastapi import APIRouter, Response, HTTPException, status, Path
from pydantic import BaseModel
from typing import List, Optional, Dict, Literal, Tuple
import yaml
import logging
import numpy as np
import os
from datetime import date, datetime, time
from api.utils.databricks_utils import DatabricksConnector

from api.services.semantic_profiling import profile_table
from api.services.semantic_builder import (
    build_semantic_json,
    select_time_dimension,
    send_create_semantic_layer_config,
    send_update_semantic_layer_config,
    send_delete_semantic_layer_config,
    get_config_by_id,
    get_configs_by_product_id,
    build_semantic_json_databricks,
    profile_table_databricks,
)
from api.services.data_access_service import (
    send_register_client_deploy_v2,
)
from api.services.gcs_client import (
    upload_text_to_gcs,
    download_text_from_gcs,
    delete_gcs_object,
)
from api.utils.semantic_layer_client import SemanticLayerClient
from api.services.mindsdb_client import connect, query
from api.services.semantic_query_builder_advanced import QueryBuilderAdvanced

from api.models.semantic_models import (
    ColumnSelection,
    BuildRequest,
    QueryRunReq,
    UpdateRequest,
    DescribeResponse,
    QueryBuildAdvancedRequest,
    QueryBuildAdvancedResponse,
    QueryRunRequest,
    QueryRunResponse,
    SemanticLayerConfigData,
    SemanticLayerCreateRequest,
    SemanticLayerUpdateRequest,
    SemanticLayerDeleteRequest,
    SemanticLayerSingleResponse,
    SemanticLayerListResponse,
    SemanticLayerCreationResponse,
    SemanticLayerUpdateResponse,
    SemanticLayerDeleteResponse,
    SemanticLayerGetByIDRequest,
    SemanticLayerGetByProductRequest,
)

semantic_router = APIRouter(prefix="/semantic", tags=["Semantic Layer"])
logger = logging.getLogger("semantic_router")


def sanitize(obj):
    """Normaliza tipos numpy/datetime para serializar a YAML."""
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, (date, datetime, time)):
        return obj.isoformat()
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, dict):
        return {
            (k if isinstance(k, (str, int, float, bool)) else str(k)): sanitize(v)
            for k, v in obj.items()
        }
    if isinstance(obj, (list, tuple, set)):
        return [sanitize(v) for v in obj]
    return str(obj)


# Construir capa semántica
# @semantic_router.post(
#     "/layer/build",
#     summary="Construir capa semántica (opcional: perfilar y/o subir a GCS)",
#     description=(
#         "Genera el YAML de la capa semántica basado en las selecciones de tablas/columnas. "
#         "Opcionalmente, puede incluir el **perfilado de datos** y subir el archivo resultante a GCS, "
#         "devolviendo la URL. Si no se especifican `bucket_name` y `object_path`, "
#         "devuelve el YAML directamente en la respuesta."
#     ),
# )
# async def build_layer(req: BuildRequest):
#     logger.info(
#         "[semantic] build_layer start engine=%s include_profiling=%s",
#         req.engine,
#         req.include_profiling,
#     )
#     # Construir nueva capa semántica
#     semantic = build_semantic_json(
#         server_url=req.server_url,
#         database=req.database,
#         selections=[s.model_dump() for s in req.selections],
#         infer_types=bool(req.infer_types),
#         add_default_measures=bool(req.add_default_measures),
#         time_dimension_candidates=req.time_dimension_candidates or [],
#         engine=req.engine or "postgres",
#     )
#     logger.info(
#         "[semantic] semantic skeleton built with %d datasets",
#         len(semantic.get("datasets", {})),
#     )
#     # Incluir perfilado de datos
#     if req.include_profiling:
#         for fq_name, ds in semantic.get("datasets", {}).items():
#             schema_name = ds.get("schema")
#             table = ds.get("table")
#             # Limitar el perfilado a las columnas seleccionadas (dimensiones + medidas)
#             selected_cols = list((ds.get("dimensions") or {}).keys()) + list(
#                 (ds.get("measures") or {}).keys()
#             )
#             logger.info(
#                 "[semantic] profiling dataset=%s schema=%s table=%s cols=%s",
#                 fq_name,
#                 schema_name,
#                 table,
#                 selected_cols,
#             )
#             prof_text = profile_table(
#                 req.server_url,
#                 req.database,
#                 schema_name,
#                 table,
#                 engine=req.engine or "postgres",
#                 columns=selected_cols,
#             )
#             ds["profile"] = prof_text
#     try:
#         sanitized = sanitize(semantic)
#         yaml_text = yaml.safe_dump(sanitized, sort_keys=False, allow_unicode=True)
#         # Subir a GCS
#         if req.bucket_name and req.object_path:
#             url = upload_text_to_gcs(
#                 req.bucket_name, req.object_path, yaml_text, content_type="text/yaml"
#             )
#             logger.info(
#                 "[semantic] uploaded to gs://%s/%s", req.bucket_name, req.object_path
#             )
#             logger.info("[semantic] url: %s", url)
#             # return Response(content=yaml_text, media_type='text/yaml') # para ver el yaml en la respuesta
#             return Response(content=url, media_type="text/plain")
#         return Response(content=yaml_text, media_type="text/yaml")
#     except Exception as e:
#         logger.exception("[semantic] YAML serialization failed: %s", e)
#         fallback = {"status": "error", "message": str(e)}
#         return Response(
#             content=yaml.safe_dump(fallback, sort_keys=False, allow_unicode=True),
#             media_type="text/yaml",
#             status_code=500,
#         )


@semantic_router.post(
    "/layer/build",
    summary="Construir capa semántica (opcional: perfilar y/o subir a GCS)",
    description=(
        "Genera el YAML de la capa semántica. Maneja motores tipo MindsDB "
        "(postgres, etc.) y conexiones directas a Databricks."
    ),
)
async def build_layer_databricks(req: BuildRequest):
    logger.info(
        "[semantic] build_layer start engine=%s include_profiling=%s",
        req.engine,
        req.include_profiling,
    )
    if req.product_id is None:
        raise HTTPException(
            status_code=400,
            detail="product_id es obligatorio para registrar el deploy.",
        )

    semantic = {}

    try:
        if req.engine == "databricks":
            if not req.databricks_config:
                raise HTTPException(
                    status_code=400,
                    detail="'engine' es 'databricks' pero 'databricks_config' no fue proporcionado.",
                )

            logger.info("[semantic] Iniciando flujo Databricks...")
            semantic = build_semantic_json_databricks(
                databricks_host=req.server_url,
                databricks_config=req.databricks_config,
                catalog=req.database,
                selections=[s.model_dump() for s in req.selections],
                infer_types=bool(req.infer_types),
                add_default_measures=bool(req.add_default_measures),
                time_dimension_candidates=req.time_dimension_candidates or [],
            )

            if req.include_profiling:
                logger.info("[semantic] Profiling Databricks...")
                # Para perfilar, abrimos una nueva conexión
                # (o podríamos reestructurar para pasar el conector)
                with DatabricksConnector(
                    databricks_host=req.server_url,
                    http_path=req.databricks_config.http_path,
                    client_id=req.databricks_config.client_id,
                    client_secret=req.databricks_config.client_secret,
                ) as db:
                    for fq_name, ds in semantic.get("datasets", {}).items():
                        schema_name = ds.get("schema")
                        table = ds.get("table")
                        selected_cols = list(
                            (ds.get("dimensions") or {}).keys()
                        ) + list((ds.get("measures") or {}).keys())
                        logger.info(
                            "[semantic] profiling dataset=%s cols=%s",
                            fq_name,
                            selected_cols,
                        )

                        prof_text = profile_table_databricks(
                            db_connector=db,
                            catalog=req.database,
                            schema_name=schema_name,
                            table=table,
                            columns=selected_cols,
                        )
                        ds["profile"] = prof_text

        else:
            # --- FLUJO ORIGINAL: MINDSDB (postgres, mysql, etc.) ---
            logger.info("[semantic] Iniciando flujo MindsDB...")
            semantic = build_semantic_json(
                server_url=req.server_url,
                database=req.database,
                selections=[s.model_dump() for s in req.selections],
                infer_types=bool(req.infer_types),
                add_default_measures=bool(req.add_default_measures),
                time_dimension_candidates=req.time_dimension_candidates or [],
                engine=req.engine or "postgres",
            )

            if req.include_profiling:
                logger.info("[semantic] Profiling MindsDB...")
                for fq_name, ds in semantic.get("datasets", {}).items():
                    schema_name = ds.get("schema")
                    table = ds.get("table")
                    selected_cols = list((ds.get("dimensions") or {}).keys()) + list(
                        (ds.get("measures") or {}).keys()
                    )
                    logger.info(
                        "[semantic] profiling dataset=%s cols=%s",
                        fq_name,
                        selected_cols,
                    )

                    prof_text = profile_table(
                        server_url=req.server_url,
                        database=req.database,
                        schema_name=schema_name,
                        table=table,
                        engine=req.engine or "postgres",
                        columns=selected_cols,
                    )
                    ds["profile"] = prof_text

    except Exception as e:
        logger.exception("[semantic] Falló la construcción de la capa: %s", e)
        raise HTTPException(status_code=500, detail=f"Error al construir la capa: {e}")

    # --- LÓGICA COMÚN: Serializar y Subir a GCS ---

    try:
        sanitized = sanitize(semantic)
        yaml_text = yaml.safe_dump(sanitized, sort_keys=False, allow_unicode=True)

        if req.bucket_name and req.object_path:
            base = os.path.basename(req.object_path)
            dir_ = os.path.dirname(req.object_path) or "/"
            name, ext = os.path.splitext(base)

            new_object_path = f"{dir_}/{name}_{req.engine}{ext}"
            new_object_path = new_object_path.replace("//", "/")
            url = upload_text_to_gcs(
                req.bucket_name,
                req.object_path,
                yaml_text,
                content_type="text/yaml",
            )
            logger.info(
                "[semantic] uploaded to gs://%s/%s", req.bucket_name, req.object_path
            )
            if req.engine == "bigquery":
                gs_psql = "prompts/query_exec_prompt_bigquery.yaml"
            else:
                gs_psql = "prompts/query_exec_prompt.yaml"
            insert = ClientDeployRegisterRequest(
                product_id=req.product_id,
                bucket_config=req.bucket_name,
                gs_examples_agent=None,
                gs_prompt_agent=None,
                gs_prompt_sql=gs_psql,
                gs_profiling_agent=None,
                gs_metrics_config_agent=None,
                gs_semantic_config=req.object_path,
                client=req.database,
            )
            new_deploy_id = send_register_client_deploy_v2(insert)
            return Response(content=url, media_type="text/plain")

        return Response(content=yaml_text, media_type="text/yaml")

    except Exception as e:
        logger.exception("[semantic] YAML serialization/upload failed: %s", e)
        fallback = {"status": "error", "message": str(e)}
        return Response(
            content=yaml.safe_dump(fallback, sort_keys=False, allow_unicode=True),
            media_type="text/yaml",
            status_code=500,
        )


# Actualizar capa semántica
@semantic_router.post(
    "/layer/update",
    summary="Actualizar capa semántica (reemplazo in-place en GCS)",
    description=(
        "Reconstruye completamente la capa semántica y **reemplaza el archivo YAML anterior** "
        "en el mismo URI de GCS (`gs://bucket/object`) especificado en `previous_gs_uri`. "
        "Garantiza la actualización atómica del archivo."
    ),
)
async def update_layer(req: UpdateRequest):
    logger.info(
        "[semantic] update_layer start engine=%s include_profiling=%s",
        req.engine,
        req.include_profiling,
    )

    # Validar y parsear previous_gs_uri
    if not req.previous_gs_uri.startswith("gs://"):
        return Response(
            content=yaml.safe_dump(
                {
                    "status": "error",
                    "message": "previous_gs_uri debe comenzar con gs://",
                },
                sort_keys=False,
            ),
            media_type="text/yaml",
            status_code=400,
        )
    without_scheme = req.previous_gs_uri[len("gs://") :]
    if "/" not in without_scheme:
        return Response(
            content=yaml.safe_dump(
                {
                    "status": "error",
                    "message": "previous_gs_uri invalido: falta object path",
                },
                sort_keys=False,
            ),
            media_type="text/yaml",
            status_code=400,
        )
    bucket_name, object_path = without_scheme.split("/", 1)

    # Construir nueva capa semántica
    semantic = build_semantic_json(
        server_url=req.server_url,
        database=req.database,
        selections=[s.model_dump() for s in req.selections],
        infer_types=bool(req.infer_types),
        add_default_measures=bool(req.add_default_measures),
        time_dimension_candidates=req.time_dimension_candidates or [],
        engine=req.engine or "postgres",
        relationships=req.relationships or [],
    )
    # Incluir perfilado de datos
    if req.include_profiling:
        for fq_name, ds in semantic.get("datasets", {}).items():
            schema_name = ds.get("schema")
            table = ds.get("table")
            # Limitar el perfilado a las columnas seleccionadas (dimensiones + medidas)
            selected_cols = list((ds.get("dimensions") or {}).keys()) + list(
                (ds.get("measures") or {}).keys()
            )
            logger.info(
                "[semantic] profiling dataset=%s schema=%s table=%s cols=%s",
                fq_name,
                schema_name,
                table,
                selected_cols,
            )
            prof_text = profile_table(
                req.server_url,
                req.database,
                schema_name,
                table,
                engine=req.engine or "postgres",
                columns=selected_cols,
            )
            ds["profile"] = prof_text

    try:
        sanitized = sanitize(semantic)
        yaml_text = yaml.safe_dump(sanitized, sort_keys=False, allow_unicode=True)
        # Eliminar anterior
        try:
            delete_gcs_object(bucket_name, object_path)
            logger.info(
                "[semantic] deleted previous YAML gs://%s/%s", bucket_name, object_path
            )
        except Exception as e:
            logger.warning("[semantic] failed deleting previous YAML, continuo: %s", e)

        # Subir el nuevo YAML en la MISMA ruta
        new_url = upload_text_to_gcs(
            bucket_name, object_path, yaml_text, content_type="text/yaml"
        )
        logger.info(
            "[semantic] uploaded new YAML to gs://%s/%s", bucket_name, object_path
        )
        insert = ClientDeployRegisterRequest(
            product_id=req.product_id,
            bucket_config=None,
            gs_examples_agent=None,
            gs_prompt_agent=None,
            gs_prompt_sql=None,
            gs_profiling_agent=None,
            gs_metrics_config_agent=None,
            gs_semantic_config=object_path,
            client=req.database,
        )
        new_deploy_id = send_register_client_deploy_v2(insert)
        return Response(content=new_url, media_type="text/plain")
    except Exception as e:
        logger.exception("[semantic] update failed: %s", e)
        fallback = {"status": "error", "message": str(e)}
        return Response(
            content=yaml.safe_dump(fallback, sort_keys=False, allow_unicode=True),
            media_type="text/yaml",
            status_code=500,
        )


# Servir YAML desde GCS
@semantic_router.get(
    "/layer/fetch",
    summary="Servir YAML desde GCS (privado)",
    description=(
        "Actúa como un *proxy* para leer y servir el archivo YAML de la capa semántica desde un "
        "**objeto privado** en GCS (usando la cuenta de servicio), sin exponer su URL pública."
    ),
)
async def fetch_layer(gs_uri: str):
    """Proxy permanente: leer un objeto privado de GCS y servirlo como YAML.
    Ej: gs_uri=gs://mindash_evolve/semantic_layers/cliente_1/2025-09-04.yaml
    """
    if not gs_uri.startswith("gs://"):
        return Response(
            content=yaml.safe_dump(
                {"status": "error", "message": "gs_uri debe comenzar con gs://"},
                sort_keys=False,
            ),
            media_type="text/yaml",
            status_code=400,
        )
    without_scheme = gs_uri[len("gs://") :]
    if "/" not in without_scheme:
        return Response(
            content=yaml.safe_dump(
                {"status": "error", "message": "gs_uri invalido: falta object path"},
                sort_keys=False,
            ),
            media_type="text/yaml",
            status_code=400,
        )
    bucket_name, object_path = without_scheme.split("/", 1)
    content, _ = download_text_from_gcs(bucket_name, object_path)
    return Response(content=content, media_type="text/yaml")


# Yaml a JSON para el frontend
@semantic_router.get(
    "/layer/describe",
    summary="Describir YAML como JSON para el frontend",
    description=(
        "Carga el archivo YAML desde GCS y devuelve una **representación JSON** optimizada y parseada "
        "(solo *datasets* y sus atributos), ideal para su consumo directo por interfaces de usuario."
    ),
)
async def describe_layer(gs_uri: str):
    client = SemanticLayerClient(gs_uri, ttl_seconds=300)
    datasets: Dict[str, Dict] = {}
    for fq in client.list_tables():
        ds = client.get_dataset(fq) or {}
        datasets[fq] = ds
    return DescribeResponse(datasets=datasets).model_dump()


@semantic_router.post(
    "/query/build-advanced",
    summary="Construir SQL (Multi-datasets con Joins)",
    description=(
        "Genera la sentencia SQL subyacente a una consulta semántica compleja. Utiliza las "
        "**relaciones** y el esquema definidos en el YAML de `gs_uri` para construir el SQL "
        "con *joins*, filtros, ordenamiento y límites."
    ),
)
async def build_query_advanced(req: QueryBuildAdvancedRequest):
    client = SemanticLayerClient(req.gs_uri, ttl_seconds=300)
    # Consumir YAML completo desde el cliente
    full_yaml = client.get_semantic()
    print("full_yaml", full_yaml)
    ds_map = full_yaml.get("datasets") or {}
    semantic: Dict[str, Dict] = (
        {"datasets": ds_map} if isinstance(ds_map, dict) else {"datasets": {}}
    )
    rels = client.get_relationships()
    if rels:
        semantic["relationships"] = rels

    # Inyectar medidas derivadas inline si vienen en el body
    if req.derived_measures:
        for m in req.derived_measures:
            if not isinstance(m, dict):
                continue
            ds_key = m.get("dataset_key")
            name = m.get("name")
            expr = m.get("expression")
            if not ds_key or not name or not expr:
                continue
            ds = semantic["datasets"].get(ds_key)
            if not isinstance(ds, dict):
                # dataset inexistente en YAML
                continue
            if "measures" not in ds or not isinstance(ds["measures"], dict):
                ds["measures"] = {}
            ds["measures"][name] = {
                "expression": expr,
                "description": m.get("description") or "",
                "data_type": m.get("data_type") or "number",
            }

    qb = QueryBuilderAdvanced(semantic, engine=req.engine or "postgres")
    sql = qb.build(
        dimensions=req.dimensions or [],
        measures=req.measures or [],
        filters=req.filters or [],
        order_by=req.order_by,
        limit=req.limit,
    )
    return QueryBuildAdvancedResponse(sql=sql).model_dump()


# @semantic_router.post(
#     "/query/runV2",
#     summary="Ejecutar SQL en MindsDB (compatibilidad dashboards)",
#     description=(
#         "Ejecuta la sentencia SQL usando connection_id. "
#         "Compatibilidad con minddash-dashboards-api."
#     ),
# )
# async def run_query_via_mindsdb_v2(req: QueryRunRequest):
#     """
#     Endpoint compatible con dashboards-api que acepta connection_id
#     y lo convierte a los parámetros necesarios para MindsDB.
#     """
#     try:
#         # Para dashboards-api, usamos valores fijos ya que la query ya contiene la integración
#         server_url = "http://34.59.236.198:47334"
#         database = "mindsdb"

#         # Log detallado para depuración
#         logger.info(f"[semantic] Query recibida (runV2): {req.sql}")
#         logger.info(f"[semantic] Server URL: {server_url}")
#         logger.info(f"[semantic] Database: {database}")

#         server = connect(server_url)

#         # Si la query ya contiene referencias a integraciones de MindsDB, ejecutarla directamente
#         if "postgresql_conn_" in req.sql or "mysql_conn_" in req.sql or "bigquery_conn_" in req.sql:
#             # Ejecutar la query directamente sin crear modelos
#             wrapped = req.sql
#             logger.info(f"[semantic] Query directa (sin modelo): {wrapped}")
#         else:
#             wrapped = f"SELECT * FROM {database} (\n{req.sql}\n);"
#             logger.info(f"[semantic] Query con wrapping: {wrapped}")

#         logger.info(f"[semantic] Ejecutando query en MindsDB...")
#         df = query(server, wrapped)
#         rows = df.to_dict(orient="records") if hasattr(df, "to_dict") else []
#         logger.info(f"[semantic] Query ejecutada exitosamente. Filas devueltas: {len(rows)}")
#         return QueryRunResponse(status="success", rows=rows).model_dump()
#     except Exception as e:
#         logger.exception("[semantic] run_query error: %s", e)
#         return QueryRunResponse(status="error", message=str(e)).model_dump()


@semantic_router.post(
    "/query/run",
    summary="Ejecutar SQL en MindsDB",
    description=(
        "Ejecuta la sentencia SQL construida (o provista) contra la conexión de MindsDB especificada. "
        "La consulta es envuelta para ser ejecutada como una **consulta remota** "
        "dentro del motor de MindsDB."
    ),
)
async def run_query_via_mindsdb(req: QueryRunRequest):
    try:
        server = connect(req.server_url)

        # Log detallado para depuración
        logger.info(f"[semantic] Query recibida: {req.sql}")
        logger.info(f"[semantic] Database: {req.database}")

        # Si la query ya contiene referencias a integraciones de MindsDB, ejecutarla directamente
        if (
            "postgresql_conn_" in req.sql
            or "mysql_conn_" in req.sql
            or "bigquery_conn_" in req.sql
        ):
            # Ejecutar la query directamente sin crear modelos
            wrapped = req.sql
            logger.info(f"[semantic] Query directa (sin modelo): {wrapped}")
        else:
            wrapped = f"SELECT * FROM {req.database} (\n{req.sql}\n);"
            logger.info(f"[semantic] Query con wrapping: {wrapped}")

        logger.info("[semantic] Ejecutando query en MindsDB...")
        df = query(server, wrapped)
        rows = df.to_dict(orient="records") if hasattr(df, "to_dict") else []
        logger.info(
            f"[semantic] Query ejecutada exitosamente. Filas devueltas: {len(rows)}"
        )
        return QueryRunResponse(status="success", rows=rows).model_dump()
    except Exception as e:
        logger.exception("[semantic] run_query error: %s", e)
        return QueryRunResponse(status="error", message=str(e)).model_dump()


@semantic_router.post(
    "/query/runV2",
    summary="Ejecutar SQL en MindsDB",
    description=(
        "Ejecuta la sentencia SQL construida contra la conexión especificada. "
        "Diferencia la lógica según sea Databricks, BigQuery o conexiones estándar de MindsDB."
    ),
)
async def run_query_general(req: QueryRunReq):
    try:
        mindsdb_url = os.getenv("MINDSDB_URL")
        server = connect(mindsdb_url)
        if req.connection_name:
            wrapped = f"SELECT * FROM {req.connection_name} (\n{req.sql}\n);"
        else:
            lista = get_data_connections(req)
            if not lista:
                raise ValueError(
                    "No se encontró la conexión especificada en la base de datos interna."
                )

            conection = lista[0]

            c_type = conection.connection_type.lower()
            db_name_in_table = conection.connection_name

            if c_type == "databricks":
                print("NY")

            elif c_type == "bigquery":
                prefijo = f"{db_name_in_table}."
                inner_sql = req.sql.replace(prefijo, "")
                if req.connection_name:
                    inner_sql = inner_sql.replace(f"{req.connection_name}.", "")

                print(f"--- Lógica BigQuery para: {db_name_in_table} ---")
                wrapped = f"SELECT * FROM {db_name_in_table} (\n{inner_sql}\n);"

            elif c_type == "postgresql":
                print(
                    f"--- Lógica MindsDB Standard (Postgres) para: {db_name_in_table} ---"
                )

                prefijo = f"{db_name_in_table}."
                inner_sql = req.sql.replace(prefijo, "")
                if req.connection_name:
                    inner_sql = inner_sql.replace(f"{req.connection_name}.", "")

                wrapped = f"SELECT * FROM {db_name_in_table} (\n{inner_sql}\n);"

            else:
                print(
                    f"--- Tipo de conexión genérica ({c_type}): {db_name_in_table} ---"
                )

                prefijo = f"{db_name_in_table}."
                inner_sql = req.sql.replace(prefijo, "")
                if req.connection_name:
                    inner_sql = inner_sql.replace(f"{req.connection_name}.", "")

                wrapped = f"SELECT * FROM {db_name_in_table} (\n{inner_sql}\n);"

        # 4. Ejecución de la consulta en el servidor
        print(f"wrapped: {wrapped}")
        df = query(server, wrapped)

        if hasattr(df, "to_dict"):
            # Reemplazamos NaN por None para que sea compatible con JSON (se convertirá en null)
            df = df.replace({np.nan: None})
            rows = df.to_dict(orient="records")
        else:
            rows = []

        return QueryRunResponse(status="success", rows=rows).model_dump()

    except Exception as e:
        logger.exception("[semantic] run_query_general error: %s", e)
        return QueryRunResponse(status="error", message=str(e)).model_dump()


"""
    Bloque de Control a Semantic Layer
"""


@semantic_router.post(
    "/getConfigByID",  # Nuevo path más descriptivo
    response_model=SemanticLayerSingleResponse,
    summary="Obtener Configuración por ID",
    description="Recupera un registro de la tabla de configuraciones de capa semántica (`semantic_layer_configs`) usando el `config_id` provisto en el cuerpo de la solicitud.",
)
def get_config_by_body(
    request_data: SemanticLayerGetByIDRequest,
) -> SemanticLayerSingleResponse:
    """
    Obtiene un registro de configuración por su ID (semantic_layer_configs.id) enviado en el cuerpo.
    """
    try:
        # Pasamos el ID del modelo Pydantic
        config_data = get_config_by_id(request_data.config_id)
        return SemanticLayerSingleResponse(config=config_data)

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error al obtener configuración por ID: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al obtener la configuración: {str(e)}",
        )


@semantic_router.post(
    "/getConfigsByProduct",  # Nuevo path más descriptivo
    response_model=SemanticLayerListResponse,
    summary="Obtener Configuraciones por Producto",
    description="Recupera todos los registros de configuración asociados a un `product_id` específico, lo que permite listar las distintas versiones o *deployments* por producto.",
)
def get_configs_by_product_by_body(
    request_data: SemanticLayerGetByProductRequest,
) -> SemanticLayerListResponse:
    """
    Obtiene todos los registros de configuración asociados a un product_id enviado en el cuerpo.
    """
    try:
        # Pasamos el ID del modelo Pydantic
        configs = get_configs_by_product_id(request_data.product_id)
        return SemanticLayerListResponse(configs=configs)

    except Exception as e:
        logger.error(f"Error al obtener configuraciones por producto: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al obtener las configuraciones: {str(e)}",
        )


# -----------------------------------------------------------------
# 3. Capa Semantica en la BD
# -----------------------------------------------------------------
@semantic_router.post(
    "/createConfig",
    response_model=SemanticLayerCreationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear Nueva Configuración de Capa Semántica",
    description="Registra un nuevo metadato de configuración de capa semántica en la base de datos (Ej: un nuevo *deployment* o una versión). Devuelve el ID de la nueva configuración creada.",
)
def create_semantic_layer_config(
    config_data: SemanticLayerCreateRequest,
) -> SemanticLayerCreationResponse:
    """
    Crea un nuevo registro de configuración de capa semántica.
    Llama a spu_minddash_app_insert_role_semantic_layer.
    """
    try:
        new_config_id = send_create_semantic_layer_config(config_data)

        return SemanticLayerCreationResponse(config_id=new_config_id)

    except Exception as e:
        error_detail = str(e)

        # Manejo de errores de FK (Ej. product_id no existe)
        if "foreign key constraint" in error_detail:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error de clave foránea: El producto con ID {config_data.product_id} no existe.",
            )

        logger.error(f"Error al crear configuración: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al crear la configuración: {error_detail}",
        )


@semantic_router.put(
    "/updateConfig",
    response_model=SemanticLayerUpdateResponse,
    summary="Actualizar Configuración de Capa Semántica",
    description="Modifica un registro de configuración de capa semántica existente, identificado por su `id`.",
)
def update_semantic_layer_config(
    config_data: SemanticLayerUpdateRequest,
) -> SemanticLayerUpdateResponse:
    """
    Actualiza un registro de configuración de capa semántica existente.
    Llama a spu_minddash_app_update_role_semantic_layer.
    """
    try:
        send_update_semantic_layer_config(config_data)

        return SemanticLayerUpdateResponse(config_id=config_data.id)

    except HTTPException as e:
        # Re-lanza el 404 o 400 manejado en la capa de servicio
        raise e
    except Exception as e:
        error_detail = str(e)

        # Manejo de errores de FK (Ej. product_id no existe)
        if "foreign key constraint" in error_detail:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error de clave foránea: El producto con ID {config_data.product_id} no existe.",
            )

        logger.error(f"Error al actualizar configuración: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al actualizar la configuración: {error_detail}",
        )


@semantic_router.delete(
    "/deleteConfig",
    response_model=SemanticLayerDeleteResponse,
    summary="Eliminar Configuración de Capa Semántica",
    description="Elimina un registro de configuración de capa semántica de la base de datos usando el `id` provisto.",
)
def delete_semantic_layer_config(
    config_data: SemanticLayerDeleteRequest,
) -> SemanticLayerDeleteResponse:
    """
    Elimina un registro de configuración de capa semántica.
    Llama a spu_minddash_app_delete_role_semantic_layer.
    """
    config_id = config_data.id
    try:
        send_delete_semantic_layer_config(config_data)

        return SemanticLayerDeleteResponse(config_id=config_id)

    except HTTPException as e:
        # Re-lanza el 404 manejado en la capa de servicio
        raise e
    except Exception as e:
        error_detail = str(e)

        logger.error(f"Error al eliminar configuración: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al eliminar la configuración: {error_detail}",
        )
