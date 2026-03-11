#!/usr/bin/env python3
"""
MindDash Marketplace - DB Initialization Script
================================================
Ejecuta api/db_ddl/db_init_marketplace.sql contra la base de datos configurada.

Uso:
    DATABASE_URL=postgresql://user:pass@host/db python scripts/db_init.py

El script es idempotente: usa CREATE OR REPLACE y DROP IF EXISTS, por lo que
puede ejecutarse múltiples veces sin efectos negativos.

Contexto de ejecución:
    - Se corre como Cloud Run Job antes del deploy del backend.
    - El Job tiene VPC connector y acceso al Cloud SQL privado.
    - Las credenciales se inyectan via Secret Manager (DATABASE_URL).
"""

import os
import sys
import logging

import psycopg2

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [db-init] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

SQL_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "api", "db_ddl", "db_init_marketplace.sql",
)


def split_sql_statements(sql: str) -> list[str]:
    """
    Divide el SQL en statements individuales, respetando bloques $$ (PL/pgSQL).

    Regla: un statement termina con ';' pero solo si NO estamos dentro de un
    bloque delimitado por $$ ... $$.
    """
    statements = []
    current_lines: list[str] = []
    in_dollar_block = False

    for line in sql.splitlines():
        stripped = line.strip()

        # Ignorar líneas vacías y comentarios fuera de un statement en curso
        if not stripped and not current_lines:
            continue
        if stripped.startswith("--") and not current_lines:
            continue

        current_lines.append(line)

        # Detectar apertura/cierre de bloques $$
        if "$$" in stripped:
            # Contar ocurrencias de $$ en la línea
            if stripped.count("$$") % 2 == 1:
                in_dollar_block = not in_dollar_block

        # Un statement termina en ';' cuando no estamos dentro de un bloque $$
        if not in_dollar_block and stripped.endswith(";"):
            stmt = "\n".join(current_lines).strip()
            if stmt:
                statements.append(stmt)
            current_lines = []

    # Capturar cualquier remanente (sin ';' final)
    if current_lines:
        stmt = "\n".join(current_lines).strip()
        if stmt and not stmt.startswith("--"):
            statements.append(stmt)

    return statements


def run_init(db_url: str) -> None:
    if not os.path.exists(SQL_FILE):
        logger.error("SQL init file not found: %s", SQL_FILE)
        sys.exit(1)

    with open(SQL_FILE, encoding="utf-8") as f:
        sql_content = f.read()

    statements = split_sql_statements(sql_content)
    logger.info("Parsed %d SQL statements from init file.", len(statements))

    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    cur = conn.cursor()

    success_count = 0
    error_count = 0

    for i, stmt in enumerate(statements, 1):
        preview = stmt[:80].replace("\n", " ")
        try:
            cur.execute(stmt)
            logger.info("[%d/%d] OK: %s...", i, len(statements), preview)
            success_count += 1
        except Exception as exc:
            logger.warning("[%d/%d] SKIP/ERR: %s | %s", i, len(statements), preview, exc)
            error_count += 1

    cur.close()
    conn.close()

    logger.info(
        "DB init completed. Success: %d | Skipped/Errors: %d",
        success_count,
        error_count,
    )

    # Solo fallamos si hay 0 statements ejecutados correctamente (algo muy malo)
    if success_count == 0:
        logger.error("No statements executed successfully. Aborting.")
        sys.exit(1)


if __name__ == "__main__":
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL environment variable not set.")
        sys.exit(1)

    logger.info("Starting DB initialization against: %s", db_url.split("@")[-1])
    run_init(db_url)
