from typing import List, Dict, Optional, Any
from fastapi import HTTPException, status
from .mindsdb_client import connect, query
from api.utils.db_client import query_all, execute_procedure_with_out, execute
from api.utils.databricks_utils import DatabricksConnector

import logging
import numpy as np
import pandas as pd


from api.models.semantic_models import (
    SemanticLayerConfigData,
    SemanticLayerCreateRequest,
    SemanticLayerUpdateRequest,
    SemanticLayerDeleteRequest,
    SemanticLayerSingleResponse,
    SemanticLayerListResponse,
    SemanticLayerCreationResponse,
    SemanticLayerUpdateResponse,
    SemanticLayerDeleteResponse,
    UpdateRequest,
    DatabricksConfig,
    SemanticLayerGetByIDRequest,
    SemanticLayerGetByProductRequest,
)


# Obtiene los tipos de columnas de una tabla
def fetch_column_types(
    server_url: str,
    database: str,
    schema_name: str,
    table: str,
    wanted_cols: List[str],
    engine: str = "postgres",
) -> Dict[str, str]:

    server = connect(server_url)

    if engine in ("postgres", "mysql", "mariadb", "redshift"):
        q = f"""
        SELECT column_name, data_type
        FROM {database}.information_schema.columns
        WHERE table_schema = '{schema_name}' AND table_name = '{table}'
        """
    elif engine == "bigquery":
        q = f"""
        SELECT column_name, data_type, is_nullable
        FROM {database}.INFORMATION_SCHEMA.COLUMNS
        WHERE table_schema = '{schema_name}' AND table_name = '{table}'
        """
    elif engine in ("mssql", "synapsemssql"):
        q = f"""
        SELECT column_name, data_type, is_nullable
        FROM {database}.INFORMATION_SCHEMA.COLUMNS
        WHERE table_schema = '{schema_name}' AND table_name = '{table}'
        """
    elif engine == "snowflake":
        q = f"""
        SELECT column_name, data_type, is_nullable
        FROM {database}.INFORMATION_SCHEMA.COLUMNS
        WHERE table_schema = '{schema_name}' AND table_name = '{table}'
        """
    elif engine in ("aurora", "aurorapostgres", "auroramysql"):
        q = f"""
        SELECT column_name, data_type
        FROM {database}.information_schema.columns
        WHERE table_schema = '{schema_name}' AND table_name = '{table}'
        """
    elif engine == "hana":
        q = f"""
        SELECT column_name, data_type
        FROM {database}.SYS.COLUMNS
        WHERE schema_name = '{schema_name}' AND table_name = '{table}'
        """
    elif engine == "oracle":
        q = f"""
        SELECT column_name, data_type
        FROM {database}.all_tab_columns
        WHERE owner = '{schema_name}' AND table_name = '{table}'
        """
    elif engine == "teradata":
        q = f"""
        SELECT ColumnName AS column_name, ColumnType AS data_type
        FROM {database}.DBC.Columns
        WHERE DatabaseName = '{schema_name}' AND TableName = '{table}'
        """
    elif engine == "clickhouse":
        q = f"""
        SELECT name AS column_name, type AS data_type
        FROM {database}.system.columns
        WHERE database = '{schema_name}' AND table = '{table}'
        """
    else:
        q = f"SELECT column_name, data_type FROM {database}.information_schema.columns WHERE table_schema='{schema_name}' AND table_name='{table}';"
    df = query(server, q)
    mapping: Dict[str, str] = {}
    for _, r in df.iterrows():
        col = str(r["column_name"])
        if col in wanted_cols:
            mapping[col] = str(r["data_type"]).lower()
    return mapping


# Verifica si un tipo de dato es numérico, para agregar medidas por defecto en la capa semántica
def is_numeric(dtype: str) -> bool:
    if not dtype:
        return False
    dtype = dtype.lower()
    return any(
        key in dtype
        for key in [
            "int",
            "int64",
            "numeric",
            "bignumeric",
            "decimal",
            "double",
            "real",
            "float",
            "float64",
            "number",
        ]
    )


# Verifica si un tipo de dato es de fecha, para seleccionar la columna para time_dimension
def is_datetime(dtype: str) -> bool:
    if not dtype:
        return False
    dtype = dtype.lower()
    return any(key in dtype for key in ["date", "time", "timestamp", "datetime"])


# Mapea tipos nativos del motor a tipos semánticos uniformes
def to_semantic_type(native_type: str) -> str:
    if not native_type:
        return "string"
    t = native_type.lower()
    # boolean
    if "bool" in t:
        return "boolean"
    # numéricos
    if any(
        k in t
        for k in [
            "int",
            "int64",
            "float",
            "float64",
            "double",
            "real",
            "numeric",
            "decimal",
            "bignumeric",
            "number",
        ]
    ):
        return "number"
    # fecha/hora
    if "timestamp" in t or "datetime" in t:
        return "datetime"
    if "date" in t:
        return "date"
    if "time" in t:
        return "time"
    # texto
    if any(k in t for k in ["char", "character", "varchar", "text", "string"]):
        return "string"
    # default
    return "string"


# Selecciona la columna para time_dimension
def select_time_dimension(
    cols: List[str],
    col_types: Dict[str, str],
    candidates: List[str],
    override: Optional[str],
) -> Optional[str]:
    if override and override in cols:
        return override
    # 1) por tipo
    for col in cols:
        if is_datetime(col_types.get(col, "")):
            return col
    # 2) por nombre (heurística)
    lowered = [c.lower() for c in cols]
    for cand in candidates or []:
        if cand:
            for i, name in enumerate(lowered):
                if cand in name:
                    return cols[i]
    return None


def _quote_identifier(engine: str, name: str) -> str:
    """Helper para citar identificadores según el engine."""
    if engine in ("databricks", "mysql", "mariadb", "snowflake", "clickhouse"):
        return f"`{name}`"
    elif engine in ("mssql", "synapsemssql"):
        return f"[{name}]"
    else:
        return f'"{name}"'  # postgres, redshift, aurora, aurorapostgres, auroramysql, hana, oracle, teradata


# Construye el JSON de la capa semántica
def build_semantic_json(
    server_url: str,
    database: str,
    selections: List[dict],
    infer_types: bool,
    add_default_measures: bool,
    time_dimension_candidates: List[str],
    engine: str = "postgres",
    relationships: Optional[List[Dict[str, str]]] = None,
) -> Dict:
    semantic: Dict = {"version": "0.1", "connection": database, "datasets": {}}
    for sel in selections:
        schema_name = sel["schema_name"]
        table = sel["table"]
        # Soporta input simple (columns) o detallado (column_specs)
        column_specs = sel.get("column_specs") or []
        cols = sel.get("columns") or [
            c.get("name") for c in column_specs if c.get("name")
        ]
        td_override = sel.get("time_dimension")
        pk_name = sel.get("primary_key")

        col_types: Dict[str, str] = {c: "" for c in cols}
        if infer_types:
            try:
                col_types = fetch_column_types(
                    server_url, database, schema_name, table, cols, engine=engine
                )
            except Exception:
                pass

        dimensions: Dict[str, Dict[str, Optional[str]]] = {}
        measures: Dict[str, Dict[str, Optional[str]]] = {}
        # Construcción basada en especificaciones del usuario si existen
        if column_specs:
            for spec in column_specs:
                name = spec.get("name")
                if not name:
                    continue
                description = spec.get("description")
                explicit_type = (spec.get("data_type") or "").lower()
                role = (spec.get("role") or "").lower()  # 'dimension' | 'measure'
                aggregation = (
                    spec.get("aggregation") or ""
                ).lower()  # sum|count|avg|min|max
                # Preferir el tipo provisto; si no, usar el inferido
                dtype = explicit_type or col_types.get(name, "")
                semantic_type = to_semantic_type(dtype)
                quoted_name = _quote_identifier(engine, name)
                if role == "measure" and aggregation in (
                    "sum",
                    "count",
                    "avg",
                    "min",
                    "max",
                ):
                    agg_sql = {
                        "sum": f"SUM({quoted_name})",
                        "count": f"COUNT({quoted_name})",
                        "avg": f"AVG({quoted_name})",
                        "min": f"MIN({quoted_name})",
                        "max": f"MAX({quoted_name})",
                    }[aggregation]
                    measures[name] = {
                        "expression": agg_sql,
                        "description": description,
                        "data_type": semantic_type,
                    }
                else:
                    dimensions[name] = {
                        "expression": quoted_name,
                        "description": description,
                        "data_type": semantic_type,
                    }
        else:
            # Fallback a inferencia automática si no hay especificaciones
            for col in cols:
                dtype = col_types.get(col, "")
                semantic_type = to_semantic_type(dtype)
                quoted_col = _quote_identifier(engine, col)
                if add_default_measures and is_numeric(dtype):
                    measures[col] = {
                        "expression": f"SUM({quoted_col})",
                        "description": None,
                        "data_type": semantic_type,
                    }
                else:
                    dimensions[col] = {
                        "expression": quoted_col,
                        "description": None,
                        "data_type": semantic_type,
                    }

        td = select_time_dimension(
            cols, col_types, time_dimension_candidates or [], td_override
        )

        fq_name = f"{schema_name}.{table}"
        dataset_entry = {
            "table": table,
            "schema": schema_name,
            "connection": database,
            "time_dimension": td,
            "dimensions": dimensions,
            "measures": measures,
        }
        if pk_name:
            dataset_entry["primary_key"] = pk_name
        semantic["datasets"][fq_name] = dataset_entry

    # Agregar relaciones entre datasets si fueron provistas
    rels = relationships or []
    valid_keys = set(semantic["datasets"].keys())
    normalized: List[Dict[str, str]] = []
    for r in rels:
        left_ds = (r.get("left_dataset") or "").strip()
        right_ds = (r.get("right_dataset") or "").strip()
        left_key = (r.get("left_key") or "").strip()
        right_key = (r.get("right_key") or "").strip()
        join_type = (r.get("join_type") or "inner").lower()
        cardinality = (r.get("cardinality") or "many_to_one").lower()
        if not left_ds or not right_ds or not left_key or not right_key:
            continue
        if left_ds not in valid_keys or right_ds not in valid_keys:
            continue
        normalized.append(
            {
                "left_dataset": left_ds,
                "left_key": left_key,
                "right_dataset": right_ds,
                "right_key": right_key,
                "join_type": join_type,
                "cardinality": cardinality,
            }
        )
    if normalized:
        semantic["relationships"] = normalized

    return semantic


"""
    Bloque para capa semantica de databricks
"""


def is_string(dtype: str) -> bool:
    if not dtype:
        return True  # Asumir string si no hay tipo
    dtype = dtype.lower()
    return any(key in dtype for key in ["char", "varchar", "text", "string"])


def _build_dims_and_measures(
    cols: List[str],
    col_types: Dict[str, str],
    column_specs: List[Dict],
    add_default_measures: bool,
    engine: str,
):
    """Lógica de construcción de dimensiones/medidas, separada."""
    dimensions: Dict[str, Dict[str, Optional[str]]] = {}
    measures: Dict[str, Dict[str, Optional[str]]] = {}

    if column_specs:
        for spec in column_specs:
            name = spec.get("name")
            if not name:
                continue
            description = spec.get("description")
            explicit_type = (spec.get("data_type") or "").lower()
            role = (spec.get("role") or "").lower()
            aggregation = (spec.get("aggregation") or "").lower()
            dtype = explicit_type or col_types.get(name, "")
            semantic_type = to_semantic_type(dtype)
            quoted_name = _quote_identifier(engine, name)

            if role == "measure" and aggregation in (
                "sum",
                "count",
                "avg",
                "min",
                "max",
            ):
                agg_sql = {
                    "sum": f"SUM({quoted_name})",
                    "count": f"COUNT({quoted_name})",
                    "avg": f"AVG({quoted_name})",
                    "min": f"MIN({quoted_name})",
                    "max": f"MAX({quoted_name})",
                }[aggregation]
                measures[name] = {
                    "expression": agg_sql,
                    "description": description,
                    "data_type": semantic_type,
                }
            else:
                dimensions[name] = {
                    "expression": quoted_name,
                    "description": description,
                    "data_type": semantic_type,
                }
    else:
        for col in cols:
            dtype = col_types.get(col, "")
            semantic_type = to_semantic_type(dtype)
            quoted_col = _quote_identifier(engine, col)
            if add_default_measures and is_numeric(dtype):
                measures[col] = {
                    "expression": f"SUM({quoted_col})",
                    "description": None,
                    "data_type": semantic_type,
                }
            else:
                dimensions[col] = {
                    "expression": quoted_col,
                    "description": None,
                    "data_type": semantic_type,
                }

    return dimensions, measures


def _sanitize_np_value(val: Any) -> Any:
    """Convierte valores de numpy a tipos nativos de Python."""
    if isinstance(val, (np.generic,)):
        try:
            return val.item()
        except Exception:
            return str(val)
    if isinstance(val, (str, int, float, bool)) or val is None:
        return val
    return str(val)


def _format_profile_output(profile: Dict[str, Any]) -> str:
    """Formatea el diccionario de perfil en un texto legible."""
    lines: list[str] = []
    for col, meta in profile["columns"].items():
        dtype = meta.get("data_type") or ""
        lines.append(f"Column: '{col}' ({dtype})")

        if meta.get("error"):
            lines.append(f"  Error profiling: {meta['error']}")
            lines.append("")
            continue

        stats = meta.get("stats") or {}
        if not stats:
            lines.append("  No profiling stats available for this column type.")
            lines.append("")
            continue

        if is_numeric(dtype):
            lines.append(f"  Count: {stats.get('count')}")
            lines.append(f"  Min: {stats.get('min')}")
            lines.append(f"  Max: {stats.get('max')}")
            lines.append(f"  Avg: {stats.get('avg')}")
        elif is_string(dtype):
            note = meta.get("note") or ""
            lines.append(f"  {note}")
            for item in stats.get("top_values", []):
                lines.append(f"    {item.get('value')}: {item.get('freq')}")
        elif is_datetime(dtype):
            lines.append(f"  Count: {stats.get('count')}")
            lines.append(f"  Earliest: {stats.get('min')}")
            lines.append(f"  Latest: {stats.get('max')}")

        lines.append("")
    return "\n".join(lines).rstrip()


def build_semantic_json_databricks(
    databricks_host: str,
    databricks_config: DatabricksConfig,
    catalog: str,
    selections: List[dict],
    infer_types: bool,
    add_default_measures: bool,
    time_dimension_candidates: List[str],
) -> Dict:
    """Construye el JSON de la capa semántica usando una conexión Databricks directa."""

    semantic: Dict = {"version": "0.1", "connection": catalog, "datasets": {}}

    try:
        # Usamos 'with' para que el conector maneje la conexión y el token
        with DatabricksConnector(
            databricks_host=databricks_host,
            http_path=databricks_config.http_path,
            client_id=databricks_config.client_id,
            client_secret=databricks_config.client_secret,
        ) as db:
            for sel in selections:
                schema_name = sel["schema_name"]
                table = sel["table"]
                column_specs = sel.get("column_specs") or []
                cols = sel.get("columns") or [
                    c.get("name") for c in column_specs if c.get("name")
                ]
                td_override = sel.get("time_dimension")
                pk_name = sel.get("primary_key")

                col_types: Dict[str, str] = {c: "" for c in cols}
                if infer_types:
                    try:
                        print(f"Obteniendo tipos de {catalog}.{schema_name}.{table}")
                        df_types = db.get_column_info(catalog, schema_name, table)
                        df_filtered = df_types[df_types["column_name"].isin(cols)]
                        col_types_map = pd.Series(
                            df_filtered.data_type.values, index=df_filtered.column_name
                        ).to_dict()
                        for col in cols:
                            if col in col_types_map:
                                col_types[col] = col_types_map[col].lower()
                    except Exception as e:
                        print(f"Error al inferir tipos de Databricks: {e}")
                        pass

                # Usamos backticks (`) para Databricks
                dimensions, measures = _build_dims_and_measures(
                    cols,
                    col_types,
                    column_specs,
                    add_default_measures,
                    engine="databricks",
                )

                td = select_time_dimension(
                    cols, col_types, time_dimension_candidates or [], td_override
                )
                fq_name = f"{schema_name}.{table}"
                dataset_entry = {
                    "table": table,
                    "schema": schema_name,
                    "connection": catalog,
                    "time_dimension": td,
                    "dimensions": dimensions,
                    "measures": measures,
                }
                if pk_name:
                    dataset_entry["primary_key"] = pk_name
                semantic["datasets"][fq_name] = dataset_entry

    except Exception as e:
        print(f"Fallo total en build_semantic_json_databricks: {e}")
        # Re-lanzar la excepción para que el endpoint la maneje
        raise

    return semantic


def profile_table_databricks(
    db_connector: DatabricksConnector,
    catalog: str,
    schema_name: str,
    table: str,
    columns: Optional[List[str]] = None,
) -> str:
    """
    Genera un perfil de tabla usando la conexión DatabricksConnector.
    Esta es la reimplementación de 'profile_table' para Databricks.
    """
    log = logging.getLogger("semantic_profiling")
    profile: Dict[str, Any] = {"columns": {}}
    tbl_ident = f"`{catalog}`.`{schema_name}`.`{table}`"

    # 1) Traer columnas y tipos
    log.info(
        "[profiling_dbx] cols query catalog=%s schema=%s table=%s",
        catalog,
        schema_name,
        table,
    )
    df_cols = db_connector.get_column_info(catalog, schema_name, table)

    if columns:
        wanted = set([str(c) for c in columns])
        df_cols = df_cols[df_cols["column_name"].astype(str).isin(wanted)]

    for _, r in df_cols.iterrows():
        col = str(r["column_name"])
        dtype = str(r.get("data_type") or "").lower()
        profile["columns"][col] = {"data_type": dtype}

    # 2) Stats (Usando Spark SQL directo, SIN la sintaxis 'inner' de MindsDB)
    for col, meta in profile["columns"].items():
        dtype = meta["data_type"]
        col_ident = f"`{col}`"  # Usar backticks para Databricks

        try:
            if is_numeric(dtype):
                q_num = f"SELECT COUNT({col_ident}) AS count, MIN({col_ident}) AS min, MAX({col_ident}) AS max, AVG({col_ident}) AS avg FROM {tbl_ident}"
                log.info("[profiling_dbx] numeric stats col=%s", col)
                df = db_connector.query_to_dataframe(q_num)
                row = df.iloc[0]
                meta["stats"] = {
                    "count": int(row.get("count") or 0),
                    "min": float(row.get("min"))
                    if row.get("min") is not None
                    else None,
                    "max": float(row.get("max"))
                    if row.get("max") is not None
                    else None,
                    "avg": float(row.get("avg"))
                    if row.get("avg") is not None
                    else None,
                }
            elif is_string(dtype):
                q_text_u = f"SELECT COUNT(DISTINCT {col_ident}) AS unique_count FROM {tbl_ident}"
                log.info("[profiling_dbx] text stats (unique) col=%s", col)
                df_u = db_connector.query_to_dataframe(q_text_u)
                unique_count = int(df_u.iloc[0].get("unique_count") or 0)

                limit_clause = " LIMIT 10" if unique_count > 10 else ""
                q_freq = f"SELECT {col_ident} AS value, COUNT(*) AS freq FROM {tbl_ident} WHERE {col_ident} IS NOT NULL GROUP BY {col_ident} ORDER BY freq DESC{limit_clause}"
                log.info("[profiling_dbx] text stats (freq) col=%s", col)
                df_f = db_connector.query_to_dataframe(q_freq)

                top_values = []
                for _, rr in df_f.iterrows():
                    val = rr.get("value")
                    top_values.append(
                        {
                            "value": _sanitize_np_value(val),
                            "freq": int(rr.get("freq") or 0),
                        }
                    )
                meta["note"] = (
                    "All possible values are shown:"
                    if unique_count <= 10
                    else f"The 10 most frequent values are shown (out of {unique_count} unique values):"
                )
                meta["stats"] = {"unique_count": unique_count, "top_values": top_values}
            elif is_datetime(dtype):
                q_time = f"SELECT COUNT({col_ident}) AS count, MIN({col_ident}) AS min, MAX({col_ident}) AS max FROM {tbl_ident} WHERE {col_ident} IS NOT NULL"
                log.info("[profiling_dbx] time stats col=%s", col)
                df_t = db_connector.query_to_dataframe(q_time)
                row = df_t.iloc[0]
                meta["stats"] = {
                    "count": int(row.get("count") or 0),
                    "min": str(row.get("min")) if row.get("min") is not None else None,
                    "max": str(row.get("max")) if row.get("max") is not None else None,
                }
            else:
                meta["stats"] = {}
        except Exception as e:
            log.error(f"[profiling_dbx] Failed to profile col '{col}': {e}")
            meta["stats"] = {}
            meta["error"] = str(e)

    return _format_profile_output(profile)  # Reusamos el helper de formato


"""
    Bloque de Control a Semantic Layer
"""


def get_config_by_id(config_id: str) -> SemanticLayerConfigData:
    """Obtiene una configuración por su ID único."""
    query = """
        SELECT 
            id, product_id, object_path_saved, bucket_name_saved, 
            object_path_deployed, bucket_name_deployed, created_at, updated_at
        FROM semantic_layer_configs
        WHERE id = %s;
    """
    params = (config_id,)

    # Llama a query_all. Aunque solo esperemos uno, devuelve una lista.
    results: List[Dict[str, Any]] = query_all(query, params)

    if not results:
        # Si la lista está vacía, el registro no existe.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuración de capa semántica con ID {config_id} no encontrada.",
        )

    # Mapea el primer (y único) resultado a tu modelo Pydantic
    return SemanticLayerConfigData(**results[0])


def get_configs_by_product_id(product_id: str) -> List[SemanticLayerConfigData]:
    """Obtiene todas las configuraciones asociadas a un product_id."""
    query = """
        SELECT 
            id, product_id, object_path_saved, bucket_name_saved, 
            object_path_deployed, bucket_name_deployed, created_at, updated_at
        FROM semantic_layer_configs
        WHERE product_id = %s
        ORDER BY created_at DESC;
    """
    params = (product_id,)

    # Llama a query_all, que ya devuelve la lista completa de diccionarios.
    results: List[Dict[str, Any]] = query_all(query, params)

    # Itera sobre la lista de diccionarios y crea la lista de modelos Pydantic
    return [SemanticLayerConfigData(**config) for config in results]


def send_create_semantic_layer_config(config_data: SemanticLayerCreateRequest) -> str:
    """Llama al SP para insertar una nueva configuración."""

    query_str = """
        CALL spu_minddash_app_insert_role_semantic_layer(
            p_new_id => %s, 
            p_product_id => %s,
            p_object_path_saved => %s,
            p_bucket_name_saved => %s,
            p_object_path_deployed => %s,
            p_bucket_name_deployed => %s
        );
    """

    # El primer elemento de 'params' debe ser None para el OUT p_new_id
    params = (
        None,
        config_data.product_id,
        config_data.object_path_saved,
        config_data.bucket_name_saved,
        config_data.object_path_deployed,
        config_data.bucket_name_deployed,
    )

    result: Dict[str, Any] | None = execute_procedure_with_out(query_str, params=params)

    if result and "p_new_id" in result:
        return str(str(result["p_new_id"]))
    else:
        # Error genérico si el SP no devuelve el ID
        raise Exception(
            "Error al insertar la configuración: no se pudo obtener el ID de respuesta."
        )


def send_update_semantic_layer_config(config_data: SemanticLayerUpdateRequest) -> None:
    """Llama al SP para actualizar una configuración."""

    query_str = """
        CALL spu_minddash_app_update_role_semantic_layer(
            p_id => %s,
            p_product_id => %s,
            p_object_path_saved => %s,
            p_bucket_name_saved => %s,
            p_object_path_deployed => %s,
            p_bucket_name_deployed => %s
        );
    """

    params = (
        config_data.id,
        config_data.product_id,
        config_data.object_path_saved,
        config_data.bucket_name_saved,
        config_data.object_path_deployed,
        config_data.bucket_name_deployed,
    )

    try:
        # execute se usa para CALL sin OUTs
        execute(query_str, params=params)
    except Exception as e:
        error_detail = str(e)

        # El SP lanza WARNING si el ID no existe. Necesitamos manejo si el SP lanza una EXCEPTION real
        # Si el SP de update lanza una EXCEPTION (no solo WARNING) por ID no encontrado, la capturamos aquí.
        if "No se encontró la configuración con ID" in error_detail:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_detail.split("ERROR: ")[-1],
            )

        # Re-lanza cualquier otro error (como FK inválida)
        raise


def send_delete_semantic_layer_config(config_data: SemanticLayerDeleteRequest) -> None:
    """Llama al SP para eliminar una configuración."""

    query_str = """
        CALL spu_minddash_app_delete_role_semantic_layer(
            p_id => %s
        );
    """
    params = (config_data.id,)

    try:
        execute(query_str, params=params)

        # NOTA: Si el SP lanza un WARNING (y no una EXCEPTION) al no encontrar el ID,
        # la ejecución llega hasta aquí. Idealmente, el SP de DELETE debería lanzar
        # una EXCEPTION si el ID no existe para que el servicio pueda retornar un 404.

    except Exception as e:
        error_detail = str(e)

        # Asume que si el SP lanza una EXCEPTION (y no solo WARNING) por ID no encontrado, la capturamos aquí.
        if "No se encontró un registro con ID" in error_detail:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_detail.split("ERROR: ")[-1],
            )

        raise
