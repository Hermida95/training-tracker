import datetime
import secrets

import bcrypt
import jwt

from app.core.config import get_settings

ALGORITHM = "HS256"

# Alfabeto sin caracteres ambiguos (sin 0/O, 1/I/L...) para códigos que la
# gente va a leer en voz alta o copiar de un pantallazo.
_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def generate_friendly_code(groups: int, group_len: int = 4) -> str:
    """Código legible tipo XXXX-XXXX. Con alfabeto de 31 símbolos, 8 caracteres
    ya son ~1.5e12 combinaciones: de sobra contra fuerza bruta, que además está
    frenada por el rate limit de /auth."""
    parts = [
        "".join(secrets.choice(_CODE_ALPHABET) for _ in range(group_len)) for _ in range(groups)
    ]
    return "-".join(parts)


def normalize_code(raw: str, group_len: int = 4) -> str:
    """Tolera minúsculas, espacios y guiones perdidos al teclear el código,
    devolviéndolo en el formato canónico XXXX-XXXX con el que se guardó."""
    clean = "".join(ch for ch in raw.upper() if ch in _CODE_ALPHABET)
    return "-".join(clean[i : i + group_len] for i in range(0, len(clean), group_len))


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:
        return False


def create_access_token(user_id: int) -> str:
    settings = get_settings()
    expires = datetime.datetime.now(datetime.UTC) + datetime.timedelta(
        days=settings.access_token_days
    )
    payload = {"sub": str(user_id), "exp": expires}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> int | None:
    """Devuelve el user_id del token o None si es inválido/expirado."""
    try:
        payload = jwt.decode(token, get_settings().secret_key, algorithms=[ALGORITHM])
        return int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None
