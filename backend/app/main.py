from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings

settings = get_settings()

# Fail-fast: arrancar en producción con la clave de firma por defecto dejaría
# a cualquiera fabricar tokens válidos. Mejor no arrancar que arrancar abierto.
if settings.environment == "production" and settings.secret_key == "dev-secret-change-me":
    raise RuntimeError(
        "SECRET_KEY no configurada: en producción debe venir de Secret Manager "
        "(ver infra/terraform/secrets.tf). Aborto el arranque."
    )

app = FastAPI(
    title="Training & Habits Tracker API",
    description="API para seguimiento de entrenamiento, hábitos diarios y pausas activas.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    """Cabeceras defensivas mínimas para una API JSON.

    - nosniff: el navegador no reinterpreta respuestas como otro tipo.
    - DENY frames: la API nunca debe renderizarse embebida (clickjacking).
    - no-referrer: no filtramos URLs internas a terceros.
    """
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    return response


app.include_router(api_router)


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}
