from google.cloud import secretmanager


def get_secret_value(id_secreto: str, id_proyecto: str) -> str:
    """
    Accede a un secreto en GCP Secret Manager y devuelve
    su valor de texto plano.
    """
    try:
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{id_proyecto}/secrets/{id_secreto}/versions/latest"

        # logger.info(f"Accediendo al valor del secreto: {name}")

        # 1. Acceder al secreto
        response = client.access_secret_version(name=name)

        # 'response.payload.data' YA CONTIENE los bytes crudos (ej: b'xkeysib-...')
        # La biblioteca cliente YA HIZO el b64decode por ti.

        # 2. Solo necesitas convertir los bytes a un string
        secret_value_string = response.payload.data.decode("utf-8")

        # 3. Devolver el string
        return secret_value_string

    except Exception as e:
        # logger.error(f"Error crítico al acceder al secreto {id_secreto}: {e}")
        raise Exception(f"No se pudo obtener el secreto {id_secreto}: {e}")
