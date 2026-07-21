"""Rate limiting en memoria para los endpoints de autenticación.

Objetivo: frenar fuerza bruta de contraseñas y registro masivo de cuentas sin
añadir dependencias ni infraestructura (Redis). Es un límite POR INSTANCIA:
en Cloud Run con varias instancias cada una lleva su propio contador, así que
el límite efectivo es N x límite. Para una app personal con 0-1 instancias
activas es más que suficiente; si esto creciera, el salto natural es un
limiter compartido en Redis (p. ej. slowapi + Memorystore).
"""

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

_WINDOW_SECONDS = 60
_MAX_ATTEMPTS = 10  # por IP y por minuto, compartido entre login y register

_attempts: dict[str, deque[float]] = defaultdict(deque)


def _client_ip(request: Request) -> str:
    # En Cloud Run el balanceador pone la IP real del cliente en
    # X-Forwarded-For (primer valor). En local no existe y usamos el peer.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def check_auth_rate_limit(request: Request) -> None:
    """Dependency de FastAPI: lanza 429 si la IP supera el límite."""
    now = time.monotonic()
    bucket = _attempts[_client_ip(request)]

    while bucket and now - bucket[0] > _WINDOW_SECONDS:
        bucket.popleft()

    if len(bucket) >= _MAX_ATTEMPTS:
        raise HTTPException(429, "Demasiados intentos. Espera un minuto y vuelve a probar.")
    bucket.append(now)

    # Poda ocasional para que el dict no crezca sin límite con IPs efímeras.
    if len(_attempts) > 10_000:
        for ip in [ip for ip, dq in _attempts.items() if not dq]:
            del _attempts[ip]


def reset_rate_limit_state() -> None:
    """Solo para tests."""
    _attempts.clear()
