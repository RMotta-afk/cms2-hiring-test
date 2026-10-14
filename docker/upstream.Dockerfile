# syntax=docker/dockerfile:1
ARG UV_VERSION=0.12.10
FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

FROM python:3.12-slim-bookworm AS build
COPY --from=uv /uv /uvx /bin/

WORKDIR /app
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY upstream/pyproject.toml upstream/uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-project

COPY upstream/records_api ./records_api
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-editable

FROM python:3.12-slim-bookworm AS runtime
ENV PATH="/opt/venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app
COPY --from=build /opt/venv /opt/venv

USER 10001:10001
EXPOSE 8081
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=5 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8081/projects', headers={'X-Api-Key': 'local-dev-key'}), timeout=2)"]
CMD ["uvicorn", "records_api.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8081"]
