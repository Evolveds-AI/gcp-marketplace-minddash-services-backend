import os
import re
import uuid
import logging
from io import BytesIO
from typing import Dict, Optional, Any, Tuple

import pandas as pd
from fastapi import UploadFile, HTTPException
from google.cloud import bigquery
from google.cloud.exceptions import NotFound

from api.services.gcs_client import upload_bytes_to_gcs
from api.services.mindsdb_client import connect, database_exists, create_database

logger = logging.getLogger(__name__)


def _sanitize_bigquery_name(name: str) -> str:
    """Sanitiza un nombre para que sea válido en BigQuery (solo letras, números, guiones bajos)"""
    # Reemplazar guiones y caracteres especiales con guiones bajos
    sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    # No puede empezar con número
    if sanitized and sanitized[0].isdigit():
        sanitized = "_" + sanitized
    # Máximo 1024 caracteres
    return sanitized[:1024] if len(sanitized) > 1024 else sanitized


def convert_excel_to_csv(
    file_content: bytes, sheet_name: Optional[str] = None
) -> bytes:
    """Convierte Excel a CSV usando pandas"""
    try:
        # Leer Excel desde bytes
        excel_file = BytesIO(file_content)
        excel_reader = pd.ExcelFile(excel_file)

        # Si no se especifica hoja, usar la primera
        if sheet_name:
            df = pd.read_excel(excel_reader, sheet_name=sheet_name)
        else:
            df = pd.read_excel(excel_reader, sheet_name=0)

        # Convertir a CSV
        csv_buffer = BytesIO()
        df.to_csv(csv_buffer, index=False, encoding="utf-8")
        csv_content = csv_buffer.getvalue()

        logger.info(
            f"Excel convertido a CSV: {len(df)} filas, {len(df.columns)} columnas"
        )
        return csv_content
    except Exception as e:
        logger.error(f"Error al convertir Excel a CSV: {e}")
        raise HTTPException(
            status_code=400, detail=f"Error al convertir Excel a CSV: {str(e)}"
        )


def upload_file_to_gcs(
    file: UploadFile, bucket_name: str, product_id: str, convert_excel: bool = True
) -> Dict[str, str]:
    """Sube archivo a GCS, convirtiendo Excel si es necesario"""

    # Leer contenido del archivo
    file_content = file.file.read()
    file_extension = os.path.splitext(file.filename)[1].lower()

    # Determinar formato
    file_format_map = {
        ".csv": "CSV",
        ".txt": "CSV",  # Se asume CSV con delimitador
        ".parquet": "PARQUET",
        ".avro": "AVRO",
        ".xlsx": "EXCEL",
        ".xls": "EXCEL",
    }

    format_type = file_format_map.get(file_extension, "CSV")

    # Convertir Excel a CSV si es necesario
    if format_type == "EXCEL" and convert_excel:
        file_content = convert_excel_to_csv(file_content)
        file_extension = ".csv"
        format_type = "CSV"

    # Generar path único en GCS
    file_id = str(uuid.uuid4())
    gcs_path = f"user_files/{product_id}/{file_id}{file_extension}"

    # Determinar content_type
    content_type_map = {
        ".csv": "text/csv",
        ".txt": "text/plain",
        ".parquet": "application/octet-stream",
        ".avro": "application/avro",
    }
    content_type = content_type_map.get(file_extension, "application/octet-stream")

    # Subir a GCS
    gs_uri = upload_bytes_to_gcs(
        bucket_name=bucket_name,
        destination_path=gcs_path,
        data=file_content,
        content_type=content_type,
    )

    logger.info(f"Archivo subido a GCS: {gs_uri}, tamaño: {len(file_content)} bytes")

    return {
        "gs_uri": gs_uri,
        "file_id": file_id,
        "file_name": file.filename,
        "file_size": len(file_content),
        "format": format_type,
        "extension": file_extension,
    }


def ensure_bigquery_dataset(project_id: str, product_id: str) -> str:
    """Crea dataset en BigQuery si no existe (por product_id)"""
    client = bigquery.Client(project=project_id)

    # Sanitizar product_id para nombre de dataset válido
    dataset_name = f"product_{_sanitize_bigquery_name(product_id)}"
    dataset_id = f"{project_id}.{dataset_name}"

    try:
        # Intentar obtener el dataset
        dataset_ref = client.dataset(dataset_name)
        client.get_dataset(dataset_ref)
        logger.info(f"Dataset ya existe: {dataset_id}")
    except NotFound:
        # Crear dataset si no existe
        dataset = bigquery.Dataset(dataset_ref)
        dataset.location = "US"  # O tu región preferida
        dataset.description = f"Dataset para producto {product_id}"
        dataset = client.create_dataset(dataset, exists_ok=True)
        logger.info(f"Dataset creado: {dataset_id}")

    return dataset_name


def load_file_to_bigquery_native(
    gs_uri: str,
    project_id: str,
    product_id: str,
    table_name: str,
    file_format: str = "CSV",
    skip_leading_rows: int = 1,
    field_delimiter: str = ",",
    quote_character: str = '"',
) -> Dict[str, Any]:
    """Carga archivo de GCS a BigQuery como tabla nativa (copia datos)"""

    client = bigquery.Client(project=project_id)

    # Asegurar que el dataset existe
    dataset_name = ensure_bigquery_dataset(project_id, product_id)

    # Sanitizar nombre de tabla
    sanitized_table_name = _sanitize_bigquery_name(table_name)
    table_ref = client.dataset(dataset_name).table(sanitized_table_name)

    # Configurar job de carga
    job_config = bigquery.LoadJobConfig()

    # Mapear formato de string a enum de BigQuery
    format_map = {
        "CSV": bigquery.SourceFormat.CSV,
        "PARQUET": bigquery.SourceFormat.PARQUET,
        "AVRO": bigquery.SourceFormat.AVRO,
        "JSON": bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
    }

    job_config.source_format = format_map.get(file_format, bigquery.SourceFormat.CSV)
    job_config.autodetect = True  # BigQuery infiere el esquema automáticamente

    # Configuraciones específicas para CSV
    if file_format == "CSV":
        job_config.skip_leading_rows = skip_leading_rows
        job_config.field_delimiter = field_delimiter
        job_config.quote_character = quote_character

    # Ejecutar carga
    logger.info(
        f"Cargando archivo {gs_uri} a BigQuery tabla {project_id}.{dataset_name}.{sanitized_table_name}"
    )

    load_job = client.load_table_from_uri([gs_uri], table_ref, job_config=job_config)

    # Esperar a que termine la carga
    load_job.result()

    # Obtener información de la tabla cargada
    table = client.get_table(table_ref)

    logger.info(
        f"Carga completada: {table.num_rows} filas cargadas en {project_id}.{dataset_name}.{sanitized_table_name}"
    )

    return {
        "status": "success",
        "table_reference": f"{project_id}.{dataset_name}.{sanitized_table_name}",
        "dataset_name": dataset_name,
        "table_name": sanitized_table_name,
        "row_count": table.num_rows,
        "message": f"Datos cargados exitosamente: {table.num_rows} filas",
    }


def prepare_bigquery_parameters(
    project_id: str,
    dataset_name: str,
    service_account_json: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Prepara los parámetros para crear una conexión BigQuery en MindsDB.
    Si no se proporciona service_account_json, lo lee del archivo local.

    Args:
        project_id: ID del proyecto de GCP
        dataset_name: Nombre del dataset en BigQuery
        service_account_json: Opcional. Si no se proporciona, se lee del archivo local

    Returns:
        Dict con los parámetros listos para usar en create_database
    """
    import json

    # Si no se proporciona service_account_json, leerlo del archivo local
    if service_account_json is None:
        sa_key_path = os.getenv(
            "GOOGLE_APPLICATION_CREDENTIALS", "./api/secret/sa-key.json"
        )
        sa_key_path = os.path.abspath(sa_key_path)

        if not os.path.exists(sa_key_path):
            logger.error(f"Archivo de credenciales no encontrado: {sa_key_path}")
            raise HTTPException(
                status_code=500,
                detail=f"Archivo de credenciales no encontrado: {sa_key_path}",
            )

        with open(sa_key_path, "r", encoding="utf-8") as f:
            service_account_json = json.load(f)

        logger.info(f"Credenciales cargadas desde: {sa_key_path}")

    logger.info(f"Service Account: {service_account_json.get('client_email')}")
    logger.info(
        f"Project ID desde credenciales: {service_account_json.get('project_id')}"
    )

    # Verificar que todas las credenciales necesarias están presentes
    required_fields = [
        "type",
        "project_id",
        "private_key_id",
        "private_key",
        "client_email",
    ]
    missing_fields = [
        field for field in required_fields if not service_account_json.get(field)
    ]
    if missing_fields:
        logger.error(f"Campos faltantes en credenciales: {missing_fields}")
        raise HTTPException(
            status_code=500,
            detail=f"Credenciales incompletas. Faltan campos: {missing_fields}",
        )

    # Verificar formato del private_key (debe tener \n, no \\n)
    private_key = service_account_json.get("private_key", "")
    if private_key:
        if "\\n" in private_key and "\n" not in private_key:
            logger.warning(
                "private_key tiene saltos de línea doblemente escapados, corrigiendo..."
            )
            # Corregir saltos de línea doblemente escapados
            service_account_json["private_key"] = private_key.replace("\\n", "\n")

    # Parámetros para BigQuery en MindsDB
    # Según documentación: MindsDB espera service_account_json como objeto JSON anidado
    bigquery_params = {
        "project_id": project_id,
        "dataset": dataset_name,
        "service_account_json": service_account_json,  # Objeto dict que se serializará como JSON anidado
    }

    logger.info(
        f"Parámetros BigQuery preparados: project_id={project_id}, dataset={dataset_name}"
    )
    return bigquery_params


def ensure_mindsdb_bigquery_connection(
    server_url: str, product_id: str, project_id: str, dataset_name: str
) -> Tuple[str, bool]:
    """
    Verifica si existe conexión MindsDB para el producto, si no existe la crea.
    Usa la misma lógica que el endpoint /connections para mantener consistencia.
    Retorna: (connection_name, was_created)
    """
    # Sanitizar product_id para nombre válido de conexión MindsDB
    sanitized_product_id = _sanitize_bigquery_name(product_id)
    connection_name = f"bigquery_product_{sanitized_product_id}"

    try:
        # Conectar a MindsDB
        server = connect(server_url)

        # Verificar si ya existe
        if database_exists(server, connection_name):
            logger.info(f"Conexión MindsDB ya existe: {connection_name}")
            return connection_name, False

        # Crear conexión si no existe
        logger.info(f"Creando conexión MindsDB: {connection_name}")

        # Preparar parámetros usando la función helper (misma lógica que /connections)
        bigquery_params = prepare_bigquery_parameters(
            project_id=project_id, dataset_name=dataset_name
        )

        # Usar create_database (misma función que usa el endpoint /connections)
        create_database(
            server=server,
            name=connection_name,
            engine="bigquery",
            parameters=bigquery_params,
        )

        logger.info(f"Conexión MindsDB creada exitosamente: {connection_name}")
        return connection_name, True

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al crear/verificar conexión MindsDB: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error al crear conexión MindsDB: {str(e)}"
        )
