# mindash-services-backend


Este proyecto utiliza FastAPI y se ejecuta mediante uv junto con uvicorn como servidor ASGI.
-- Requisitos
Asegurate de tener instalado:

Python 3.10+

uv → https://github.com/astral-sh/uv

Podés instalar uv con:

pip install uv

-- Ejecución de la aplicación

Para levantar el servidor, utilizá el siguiente comando:

uv run uvicorn main:app --host 0.0.0.0 --port 8001

uv run: ejecuta el comando dentro del entorno gestionado por uv.

uvicorn main:app: inicia Uvicorn utilizando el objeto app definido en main.py.

--host 0.0.0.0: expone la API para que pueda ser accedida desde fuera del host local.

--port 8001: define el puerto donde correrá el servidor.

-- Acceder a la API

Una vez ejecutado, la API estará disponible en:

http://localhost:8001


Y la documentación interactiva de FastAPI:

Swagger UI → http://localhost:8001/docs

Redoc → http://localhost:8001/redoc

