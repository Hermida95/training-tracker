# syntax=docker/dockerfile:1

# ---------- base: capa común con dependencias del sistema ----------
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /app
# libpq no hace falta: psycopg[binary] trae su propio libpq embebido.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ---------- deps: instala dependencias en una capa cacheable ----------
FROM base AS deps
COPY requirements.txt .
RUN pip install -r requirements.txt

# ---------- dev: hot-reload para docker-compose local ----------
FROM deps AS dev
COPY requirements-dev.txt .
RUN pip install -r requirements-dev.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ---------- production: imagen final mínima para Cloud Run ----------
FROM base AS production
COPY --from=deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin
COPY . .

RUN useradd --create-home --uid 1000 appuser
USER appuser

# Cloud Run inyecta PORT; por defecto 8080 si se corre suelto.
ENV PORT=8080
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Aplica migraciones y siembra datos antes de arrancar. Alembic es idempotente
# (upgrade head no hace nada si ya está al día) y el seed comprueba conteos
# antes de insertar, así que es seguro en cada reinicio del contenedor.
CMD alembic upgrade head && \
    python -m app.seed.seed_data && \
    uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
