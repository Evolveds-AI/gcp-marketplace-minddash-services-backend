# databricks_utils.py
import pandas as pd
import requests
from databricks import sql
from databricks.sql.client import Connection
from databricks.sql.types import Row
from typing import List


class DatabricksConnector:
    """
    Maneja la conexión OAuth M2M y las consultas a Databricks.
    """

    def __init__(self, databricks_host, http_path, client_id, client_secret):
        self.databricks_host = databricks_host
        self.http_path = http_path
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token: str | None = None
        self.conn: Connection | None = None
        self.cursor = None

    def _get_oauth_token(self) -> bool:
        """Genera un token de acceso OAuth usando el Client ID y Secret."""
        token_url = f"https://{self.databricks_host}/oidc/v1/token"
        auth = (self.client_id, self.client_secret)
        data = {"grant_type": "client_credentials", "scope": "all-apis"}

        print("Generando nuevo token de acceso OAuth para Databricks...")
        try:
            response = requests.post(token_url, auth=auth, data=data)
            response.raise_for_status()
            token_data = response.json()
            self.access_token = token_data.get("access_token")
            if not self.access_token:
                print("Error: No se pudo extraer 'access_token' de la respuesta.")
                return False
            print("Token de acceso Databricks generado.")
            return True
        except Exception as e:
            print(f"Error al generar el token de Databricks: {e}")
            return False

    def connect(self):
        """Genera un token y establece la conexión."""
        if not self._get_oauth_token():
            raise ConnectionError("Falló la generación del token de Databricks.")

        try:
            self.conn = sql.connect(
                server_hostname=self.databricks_host,
                http_path=self.http_path,
                access_token=self.access_token,
            )
            self.cursor = self.conn.cursor()
            print("Conexión a Databricks exitosa (usando token).")
        except Exception as e:
            print(f"Error al conectar a Databricks con el token: {e}")
            raise

    def disconnect(self):
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        self.access_token = None
        print("Conexión a Databricks cerrada.")

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def query(self, query_string: str) -> List[Row]:
        if not self.cursor:
            self.connect()
        try:
            self.cursor.execute(query_string)
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Error al ejecutar query en Databricks: {e}")
            # Podríamos intentar reconectar si es un error de token
            raise

    def query_to_dataframe(self, query_string: str) -> pd.DataFrame:
        if not self.cursor:
            self.connect()
        try:
            print(f"Ejecutando en Databricks: {query_string[:150]}...")
            self.cursor.execute(query_string)
            results = self.cursor.fetchall()
            columns = [desc[0] for desc in self.cursor.description]
            return pd.DataFrame(results, columns=columns)
        except Exception as e:
            print(f"Error al ejecutar query_to_dataframe en Databricks: {e}")
            raise

    def get_column_info(
        self, catalog: str, schema: str, view_name: str
    ) -> pd.DataFrame:
        """Obtiene metadatos de columnas directamente de Databricks."""
        query_string = f"""
        SELECT 
            column_name, 
            data_type, 
            is_nullable
        FROM {catalog}.INFORMATION_SCHEMA.COLUMNS
        WHERE table_schema = '{schema}' AND table_name = '{view_name}'
        ORDER BY ordinal_position;
        """
        print(f"Obteniendo metadatos para: {catalog}.{schema}.{view_name}")
        return self.query_to_dataframe(query_string)
