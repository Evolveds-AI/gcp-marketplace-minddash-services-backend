import os
import time
import json
from google.cloud import secretmanager
from fastapi import HTTPException
from typing import Any, Dict
from google.api_core import exceptions


def create_connection_secret(name: str, parameters: dict) -> str:
    try:
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        if not project_id:
            raise ValueError("Environment GOOGLE_CLOUD_PROJECT not set")

        client = secretmanager.SecretManagerServiceClient()

        hash_value = str(int(time.time() * 1000))
        secret_id = f"{name}{hash_value}"
        parent = f"projects/{project_id}"

        client.create_secret(
            parent=parent,
            secret_id=secret_id,
            secret=secretmanager.Secret(
                replication=secretmanager.Replication(
                    automatic=secretmanager.Replication.Automatic()
                )
            ),
        )

        payload_json = json.dumps(parameters).encode("utf-8")
        client.add_secret_version(
            parent=f"{parent}/secrets/{secret_id}",
            payload=secretmanager.SecretPayload(data=payload_json),
        )

        return secret_id

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def create_connection_secret_text(secret_id: str, secret_value: str) -> str:
    """
    Crea una nueva versión del secreto y deshabilita todas las versiones anteriores.
    No elimina ninguna versión, solo las deja inactivas.
    """
    client = secretmanager.SecretManagerServiceClient()
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    parent = f"projects/{project_id}"
    secret_name = f"{parent}/secrets/{secret_id}"

    # 1. Verificar/Crear el contenedor del secreto
    try:
        client.create_secret(
            parent=parent,
            secret_id=secret_id,
            secret=secretmanager.Secret(
                replication=secretmanager.Replication(
                    automatic=secretmanager.Replication.Automatic()
                )
            ),
        )
    except exceptions.AlreadyExists:
        pass

    # 2. Crear la NUEVA versión (Texto plano)
    payload = secret_value.encode("utf-8")
    new_version = client.add_secret_version(
        parent=secret_name,
        payload={"data": payload},
    )
    new_version_id = new_version.name

    # 3. Deshabilitar versiones anteriores
    # Listamos todas las versiones para encontrar las que estén habilitadas y no sean la nueva
    for version in client.list_secret_versions(parent=secret_name):
        if (
            version.name != new_version_id
            and version.state == secretmanager.SecretVersion.State.ENABLED
        ):
            client.disable_secret_version(request={"name": version.name})
            print(f"Versión previa deshabilitada: {version.name}")

    return secret_id


def get_connection_secret(secret_id: str) -> dict:
    try:
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        if not project_id:
            raise ValueError("Environment GOOGLE_CLOUD_PROJECT not set")

        client = secretmanager.SecretManagerServiceClient()

        secret_path = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
        response = client.access_secret_version(name=secret_path)

        payload = response.payload.data.decode("utf-8")
        print(f"\n RAW PAYLOAD: '{payload}'\n")
        return json.loads(payload)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def resolve_secret_config(raw_config: Any) -> Dict[str, Any]:
    """
    Recibe la configuración desde DB (str o dict),
    extrae el secret_id y trae el contenido real desde Secret Manager.
    """

    if not raw_config:
        return {}

    if isinstance(raw_config, str):
        try:
            config_dict = json.loads(raw_config)
        except json.JSONDecodeError:
            return {}
    else:
        config_dict = raw_config

    secret_id = config_dict.get("secret_id")
    if not secret_id:
        return {}

    try:
        return get_connection_secret(secret_id)
    except Exception as e:
        print(f" Error leyendo  {secret_id}: {e}")
        return {}


def update_secret(secret_id: str, secret_value: str) -> None:
    """
    Actualiza (agrega una nueva versión) el secreto en Google Secret Manager.
    """
    client = secretmanager.SecretManagerServiceClient()

    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        raise RuntimeError("GOOGLE_CLOUD_PROJECT no esta configurado")

    secret_name = f"projects/{project_id}/secrets/{secret_id}"

    payload = secret_value.encode("UTF-8")

    try:
        response = client.add_secret_version(
            request={
                "parent": secret_name,
                "payload": {"data": payload},
            }
        )
        print(f"Secret actualizado correctamente: {response.name}")
    except Exception as e:
        print(f"Error actualizando secreto {secret_id}: {str(e)}")
        raise


if __name__ == "__main__":
    mode = input("Action (create/read): ").strip().lower()

    if mode == "create":
        name = input("Base name for secret: ").strip()

        params = {
            "database": "minddash_demo",
            "host": "localhost",
            "port": 5432,
            "user": "test_user",
            "password": "super_secret",
        }

        print("CREATING SECRET...")
        try:
            secret_id = create_connection_secret(name=name, parameters=params)
            print(f" Secret Created: {secret_id}")
        except Exception as e:
            print(f"Error creating secret: {e}")

    elif mode == "read":
        secret_id = input("Secret ID: ").strip()
        print("READING SECRET...")
        try:
            secret_value = get_connection_secret(secret_id)
            print(f" Secret value: {secret_value}")
        except Exception as e:
            print(f"Error reading secret: {e}")

    else:
        print("Invalid mode. Use 'create' or 'read'.")
