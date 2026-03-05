FROM ghcr.io/astral-sh/uv:debian-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && update-ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*


COPY pyproject.toml uv.lock .python-version /app/
RUN uv sync --locked --compile-bytecode
ADD . .

EXPOSE 8080
CMD ["uv","run","uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]