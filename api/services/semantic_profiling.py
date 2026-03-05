from typing import Dict, Any, List, Optional
import logging
import numpy as np
from .mindsdb_client import connect, query


def _quote_ident(engine: str, name: str) -> str:
    if engine in ("mysql", "mariadb", "snowflake", "clickhouse"):
        return f"`{name}`"
    if engine == "bigquery":
        return f"`{name}`"
    if engine in ("mssql", "synapsemssql"):
        return f"[{name}]"
    # default postgres, redshift, aurora, aurorapostgres, auroramysql, hana, oracle, teradata
    return f'"{name}"'


def _qualified_table(engine: str, schema_name: str, table: str) -> str:
    if engine in ("mysql", "mariadb", "snowflake", "clickhouse"):
        return f"`{schema_name}`.`{table}`"
    if engine == "bigquery":
        return f"`{schema_name}.{table}`"
    if engine in ("mssql", "synapsemssql"):
        return f"[{schema_name}].[{table}]"
    # default postgres, redshift, aurora, aurorapostgres, auroramysql, hana, oracle, teradata
    return f'"{schema_name}"."{table}"'


def profile_table(
    server_url: str,
    database: str,
    schema_name: str,
    table: str,
    engine: str = "postgres",
    columns: Optional[List[str]] = None,
) -> str:
    log = logging.getLogger("semantic_profiling")
    server = connect(server_url)
    profile: Dict[str, Any] = {"columns": {}}

    # 1) Traer columnas y tipos
    if engine in (
        "postgres",
        "mysql",
        "mariadb",
        "redshift",
        "aurora",
        "aurorapostgres",
        "auroramysql",
    ):
        q_cols = f"""
        SELECT column_name, data_type
        FROM {database}.information_schema.columns
        WHERE table_schema = '{schema_name}' AND table_name = '{table}'
        ORDER BY ordinal_position;
        """
    elif engine == "bigquery":
        q_cols = f"""
        SELECT column_name, data_type, is_nullable
        FROM {database}.INFORMATION_SCHEMA.COLUMNS
        WHERE table_schema = '{schema_name}' AND table_name = '{table}'
        ORDER BY ordinal_position;
        """
    elif engine in ("mssql", "synapsemssql"):
        q_cols = f"""
        SELECT column_name, data_type, is_nullable
        FROM {database}.INFORMATION_SCHEMA.COLUMNS
        WHERE table_schema = '{schema_name}' AND table_name = '{table}'
        ORDER BY ordinal_position;
        """
    elif engine == "snowflake":
        q_cols = f"""
        SELECT column_name, data_type, is_nullable
        FROM {database}.INFORMATION_SCHEMA.COLUMNS
        WHERE table_schema = '{schema_name}' AND table_name = '{table}'
        ORDER BY ordinal_position;
        """
    elif engine == "hana":
        q_cols = f"""
        SELECT column_name, data_type
        FROM {database}.SYS.COLUMNS
        WHERE schema_name = '{schema_name}' AND table_name = '{table}'
        ORDER BY position;
        """
    elif engine == "oracle":
        q_cols = f"""
        SELECT column_name, data_type
        FROM {database}.all_tab_columns
        WHERE owner = '{schema_name}' AND table_name = '{table}'
        ORDER BY column_id;
        """
    elif engine == "teradata":
        q_cols = f"""
        SELECT ColumnName AS column_name, ColumnType AS data_type
        FROM {database}.DBC.Columns
        WHERE DatabaseName = '{schema_name}' AND TableName = '{table}'
        ORDER BY ColumnId;
        """
    elif engine == "clickhouse":
        q_cols = f"""
        SELECT name AS column_name, type AS data_type
        FROM {database}.system.columns
        WHERE database = '{schema_name}' AND table = '{table}'
        ORDER BY position;
        """
    else:
        q_cols = f"SELECT column_name, data_type FROM {database}.information_schema.columns WHERE table_schema='{schema_name}' AND table_name='{table}';"
    log.info(
        "[profiling] cols query engine=%s schema=%s table=%s",
        engine,
        schema_name,
        table,
    )
    print("q_cols!!!")
    print(q_cols)
    df_cols = query(server, q_cols)
    df_cols.columns = [c.lower() for c in df_cols.columns]
    if columns:
        wanted = set([str(c) for c in columns])
        df_cols = df_cols[df_cols["column_name"].astype(str).isin(wanted)]

    for _, r in df_cols.iterrows():
        col = str(r["column_name"])
        dtype = str(r.get("data_type") or "").lower()
        profile["columns"][col] = {"data_type": dtype}

    # 2) Para cada columna, hacer stats básicos
    for col, meta in profile["columns"].items():
        dtype = meta["data_type"]
        col_ident = _quote_ident(engine, col)
        tbl_ident = _qualified_table(engine, schema_name, table)
        if any(
            k in dtype
            for k in ["int", "numeric", "decimal", "double", "real", "float", "number"]
        ):
            inner = f"SELECT COUNT({col_ident}) AS count, MIN({col_ident}) AS min, MAX({col_ident}) AS max, AVG({col_ident}) AS avg FROM {tbl_ident}"
            q_num = f"SELECT * FROM {database} ( {inner} );"
            log.info("[profiling] numeric stats col=%s", col)
            print("q_num!!!")
            print(q_num + "\n")
            df = query(server, q_num)
            df.columns = [str(c).lower() for c in df.columns]
            row = df.iloc[0]
            meta["stats"] = {
                "count": int(row.get("count") or 0),
                "min": float(row.get("min")) if row.get("min") is not None else None,
                "max": float(row.get("max")) if row.get("max") is not None else None,
                "avg": float(row.get("avg")) if row.get("avg") is not None else None,
            }
            meta["summary"] = (
                f"Count: {meta['stats']['count']}, Min: {meta['stats']['min']}, Max: {meta['stats']['max']}, Avg: {meta['stats']['avg']}"
            )
        elif any(
            k in dtype
            for k in [
                "char",
                "character",
                "varchar",
                "varchar2",
                "text",
                "string",
                "clob",
            ]
        ):
            inner_u = (
                f"SELECT COUNT(DISTINCT {col_ident}) AS unique_count FROM {tbl_ident}"
            )
            q_text = f"SELECT * FROM {database} ( {inner_u} );"
            log.info("[profiling] text stats col=%s", col)
            df_u = query(server, q_text)
            df_u.columns = [str(c).lower() for c in df_u.columns]
            unique_count = int(df_u.iloc[0].get("unique_count") or 0)
            # limitar a 10 solo si hay más de 10
            if unique_count > 10:
                if engine == "oracle":
                    inner_f = f"SELECT * FROM (SELECT {col_ident} AS value, COUNT(*) AS freq FROM {tbl_ident} WHERE {col_ident} IS NOT NULL GROUP BY {col_ident} ORDER BY freq DESC) WHERE ROWNUM <= 10"
                elif engine in ("mssql", "synapsemssql"):
                    inner_f = f"SELECT {col_ident} AS value, COUNT(*) AS freq FROM {tbl_ident} WHERE {col_ident} IS NOT NULL GROUP BY {col_ident} ORDER BY freq DESC OFFSET 0 ROWS FETCH NEXT 10 ROWS ONLY"
                else:
                    inner_f = f"SELECT {col_ident} AS value, COUNT(*) AS freq FROM {tbl_ident} WHERE {col_ident} IS NOT NULL GROUP BY {col_ident} ORDER BY freq DESC LIMIT 10"
            else:
                inner_f = f"SELECT {col_ident} AS value, COUNT(*) AS freq FROM {tbl_ident} WHERE {col_ident} IS NOT NULL GROUP BY {col_ident} ORDER BY freq DESC"
            q_freq = f"SELECT * FROM {database} ( {inner_f} );"
            print("q_freq!!!")
            print(q_freq + "\n")
            df_f = query(server, q_freq)
            df_f.columns = [str(c).lower() for c in df_f.columns]
            top_values = []
            for _, rr in df_f.iterrows():
                val = rr.get("value")
                if isinstance(val, (np.generic,)):
                    try:
                        val = val.item()
                    except Exception:
                        val = str(val)
                top_values.append(
                    {
                        "value": val
                        if isinstance(val, (str, int, float, bool))
                        else str(val),
                        "freq": int(rr.get("freq") or 0),
                    }
                )
            note = (
                "All possible values are shown:"
                if unique_count <= 10
                else f"The 10 most frequent values are shown (out of {unique_count} unique values):"
            )
            meta["stats"] = {"unique_count": unique_count, "top_values": top_values}
            meta["note"] = note
        elif any(k in dtype for k in ["date", "time", "timestamp", "datetime"]):
            inner_t = f"SELECT COUNT({col_ident}) AS count, MIN({col_ident}) AS min, MAX({col_ident}) AS max FROM {tbl_ident} WHERE {col_ident} IS NOT NULL"
            q_time = f"SELECT * FROM {database} ( {inner_t} );"
            log.info("[profiling] time stats col=%s", col)
            df_t = query(server, q_time)
            df_t.columns = [str(c).lower() for c in df_t.columns]
            row = df_t.iloc[0]
            meta["stats"] = {
                "count": int(row.get("count") or 0),
                "min": str(row.get("min")) if row.get("min") is not None else None,
                "max": str(row.get("max")) if row.get("max") is not None else None,
            }
            meta["summary"] = (
                f"Count: {meta['stats']['count']}, Earliest: {meta['stats']['min']}, Latest: {meta['stats']['max']}"
            )
        else:
            meta["stats"] = {}

    # Construir texto final al estilo requerido
    lines: list[str] = []
    for col, meta in profile["columns"].items():
        dtype = meta.get("data_type") or ""
        lines.append(f"Column: '{col}' ({dtype})")
        stats = meta.get("stats") or {}
        if any(
            k in dtype
            for k in ["int", "numeric", "decimal", "double", "real", "float", "number"]
        ):
            lines.append(f"  Count: {stats.get('count')}")
            lines.append(f"  Min: {stats.get('min')}")
            lines.append(f"  Max: {stats.get('max')}")
            lines.append(f"  Avg: {stats.get('avg')}")
        elif any(
            k in dtype
            for k in [
                "char",
                "character",
                "varchar",
                "varchar2",
                "text",
                "string",
                "clob",
            ]
        ):
            note = meta.get("note") or ""
            lines.append(f"  {note}")
            for item in stats.get("top_values", []):
                lines.append(f"    {item.get('value')}: {item.get('freq')}")
        elif any(k in dtype for k in ["date", "time", "timestamp", "datetime"]):
            lines.append(f"  Count: {stats.get('count')}")
            lines.append(f"  Earliest: {stats.get('min')}")
            lines.append(f"  Latest: {stats.get('max')}")
        else:
            lines.append("  No profiling available for this column type.")
        lines.append("")
    return "\n".join(lines).rstrip()
