import base64
import json
import logging
import os
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
from starlette.requests import Request
from starlette.responses import JSONResponse
from api.utils.middleware_utils import run_middleware_logic
from api.routes import (
    mindsdb_router,
    semantic_router,
    user_router,
    organization_router,
    project_router,
    product_router,
    prompts_and_examples_router,
    connection_router,
    metric_router,
    data_access_router,
    chart_router,
    alert_router,
    channel_router,
    billing_router,
)

# Configurar logging para mostrar INFO y superiores en consola
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)
from google.cloud import secretmanager

from api.utils.db_client import close_pool, init_pool
from api.utils.tags_metadata import tags_metadata


def service_get_sa_credentials(id_secreto, id_proyecto):
    """
    Downloads the Service Account credentials from Secret Manager
    and saves them to a file.
    """
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{id_proyecto}/secrets/{id_secreto}/versions/latest"

    logger.info(f"Accessing secret: {name}")
    try:
        response = client.access_secret_version(name=name)

        # Decode the data from the Secret Manager response (Base64 first, then UTF-8)
        payload_bytes = base64.b64decode(response.payload.data)
        payload_string = payload_bytes.decode("utf-8")

        # Parse the decoded string as JSON
        result = json.loads(payload_string)

        # Use a temporary file path for security
        ruta_archivo = "./api/secret/sa-key.json"
        with open(ruta_archivo, "w") as archivo_json:
            json.dump(result, archivo_json, indent=4)

        logger.info(f"SA credentials downloaded and saved to {ruta_archivo}")

        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = ruta_archivo
        logger.info(f"SA key path configured: {ruta_archivo}")

        return ruta_archivo

    except Exception as e:
        logger.error(f"Error accessing the secret: {e}")
        raise  # Re-raise the exception to stop the application


path_to_sa_key = service_get_sa_credentials(
    id_secreto=os.getenv("ID_SECRETO"), id_proyecto=os.getenv("GOOGLE_CLOUD_PROJECT")
)

app = FastAPI(
    title="Evolve Semantic API",
    description="API de backends para el componente de servicio",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    openapi_tags=tags_metadata,
    swagger_ui_parameters={"docExpansion": "none"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite todos los orígenes
    allow_credentials=True,
    allow_methods=["*"],  # Permite todos los métodos (GET, POST, etc)
    allow_headers=["*"],  # Permite todos los headers
    expose_headers=["*"],  # Expone todos los headers en la respuesta
)


# Inicializar y cerrar pool de PostgreSQL
@app.on_event("startup")
def _on_startup() -> None:
    init_pool(minconn=1, maxconn=5)


@app.on_event("shutdown")
def _on_shutdown() -> None:
    close_pool()


@app.middleware("http")
async def validation_middleware(request: Request, call_next):
    path = request.url.path

    PROTECTED_ENDPOINTS = [
        "/user-data-access/sendRegistroUserDataAccess",
        "/user-data-access/sendRegistroRoleDataAccess",
        # "/projects/sendRegistroProject",
        # "/products/sendRegistroProduct",
        "/alert/sendRegistroAlerta",
        "/alert/sendRegisterRag",
    ]

    # Comprobamos si el endpoint requiere validación
    is_protected = any(path.startswith(endpoint) for endpoint in PROTECTED_ENDPOINTS)

    if is_protected:
        # Log indicando que entra al proceso de validación
        logger.info(f"Iniciando validación de cuotas para: {path}")

        error_response = await run_middleware_logic(request)

        if error_response:
            return error_response
    else:
        # Log opcional para rutas públicas o no medidas
        # logger.debug(f" Ruta libre de validación: {path}")
        pass

    return await call_next(request)


# Routers
app.include_router(mindsdb_router)
app.include_router(semantic_router)
app.include_router(user_router)
app.include_router(organization_router)
app.include_router(project_router)
app.include_router(product_router)
app.include_router(prompts_and_examples_router)
app.include_router(connection_router)
app.include_router(metric_router)
app.include_router(data_access_router)
app.include_router(chart_router)
app.include_router(alert_router)
app.include_router(channel_router)
app.include_router(billing_router)

# uvicorn main:app --host 0.0.0.0 --port 8002
# uv run uvicorn main:app --host 0.0.0.0 --port 8001

# uv run --env SSL_CERT_FILE=$(python3 -m certifi) uvicorn main:app --host 0.0.0.0 --port 8001

# uv run --native-tls  uvicorn main:app --host 0.0.0.0 --port 8001
