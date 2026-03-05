import logging
import os
from contextlib import contextmanager
from typing import Any, Dict, Iterable, List, Optional

from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool  # , SimpleConnectionPool

logger = logging.getLogger(__name__)
load_dotenv()


_POOL: Optional[ThreadedConnectionPool] = None


def _build_dsn_from_env() -> str:
    dsn = os.getenv("DB_URL")
    if dsn:
        return dsn
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "postgres")
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    options = os.getenv("POSTGRES_OPTIONS", "")  # ej: sslmode=require
    parts: List[str] = [
        f"host={host}",
        f"port={port}",
        f"dbname={db}",
        f"user={user}",
        f"password={password}",
    ]
    if options:
        parts.append(options)
    return " ".join(parts)


def init_pool(minconn: int = 1, maxconn: int = 5, dsn: Optional[str] = None) -> None:
    global _POOL
    if _POOL is not None:
        return
    dsn_final = dsn or _build_dsn_from_env()
    _POOL = ThreadedConnectionPool(minconn, maxconn, dsn=dsn_final)
    # Probar conexión de inicio y establecer autocommit
    conn = _POOL.getconn()
    try:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
    finally:
        _POOL.putconn(conn)
    logger.info("PostgreSQL pool inicializado (%s..%s)", minconn, maxconn)


def close_pool() -> None:
    global _POOL
    if _POOL is None:
        return
    _POOL.closeall()
    _POOL = None
    logger.info("PostgreSQL pool cerrado")


@contextmanager
def get_connection():
    if _POOL is None:
        raise RuntimeError("Pool no inicializado. Llama a init_pool() en startup.")
    conn = _POOL.getconn()
    try:
        yield conn
    finally:
        _POOL.putconn(conn)


def query_all(sql: str, params: Optional[Iterable[Any]] = None) -> List[Dict[str, Any]]:
    """Ejecuta un SELECT y devuelve lista de dicts."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params or tuple())
            rows = cur.fetchall()
            # RealDictRow no es estrictamente dict, casteamos explícitamente
            return [dict(r) for r in rows]


def query_one(
    sql: str, params: Optional[Iterable[Any]] = None
) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params or tuple())
            row = cur.fetchone()
            return dict(row) if row else None


def execute(sql: str, params: Optional[Iterable[Any]] = None) -> int:
    """Ejecuta un comando DML (INSERT/UPDATE/DELETE). Devuelve rowcount."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or tuple())
            rowcount = cur.rowcount
            conn.commit()
            return rowcount


def execute_procedure_with_out(
    sql: str, params: Optional[Iterable[Any]] = None
) -> Optional[Dict[str, Any]]:
    """
    Ejecuta un CALL a un Stored Procedure que devuelve valores OUT/INOUT
    y retorna los resultados como un diccionario.
    """
    if _POOL is None:
        raise RuntimeError("Pool no inicializado. Llama a init_pool() en startup.")

    with get_connection() as conn:
        # como un conjunto de filas si tienen parámetros OUT/INOUT
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params or tuple())

            # Intentar obtener la única fila devuelta por el CALL
            row = cur.fetchone()

            conn.commit()
            # El cursor puede estar vacío si el SP no devuelve nada (solo DML sin OUT/INOUT)
            return dict(row) if row else None
