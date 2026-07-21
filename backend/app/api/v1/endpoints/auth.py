import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select

from app.core.deps import CurrentUser, DbSession
from app.core.rate_limit import check_auth_rate_limit
from app.core.security import (
    create_access_token,
    generate_friendly_code,
    hash_password,
    normalize_code,
    verify_password,
)
from app.models.invite import InviteCode
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RecoveryCodeResponse,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserRead,
)
from app.seed.seed_data import seed_user

router = APIRouter(prefix="/auth", tags=["auth"])

# Rate limit SOLO en los endpoints sin token, que es donde un atacante puede
# iterar (fuerza bruta de contraseñas, alta masiva, adivinación de códigos).
# Importante no aplicarlo a /me: la app lo llama en cada arranque y limitarlo
# echaría sesiones válidas al compartir IP (NAT) o al recargar varias veces.
_limited = [Depends(check_auth_rate_limit)]


def _token_for(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user.id), user=UserRead.model_validate(user)
    )


@router.post("/register", response_model=TokenResponse, status_code=201, dependencies=_limited)
def register(data: RegisterRequest, db: DbSession):
    email = data.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "Ya existe una cuenta con ese email")

    # Registro cerrado por invitación. Excepción: la PRIMERA cuenta de la
    # instancia (BD sin usuarios) entra libre — es el dueño del despliegue,
    # que aún no tiene a nadie que pueda invitarle.
    invite: InviteCode | None = None
    if db.scalar(select(func.count()).select_from(User)):
        code = normalize_code(data.invite_code or "")
        invite = db.scalar(
            select(InviteCode).where(InviteCode.code == code, InviteCode.used_at.is_(None))
        )
        if invite is None:
            raise HTTPException(403, "Necesitas un código de invitación válido")

    user = User(email=email, password_hash=hash_password(data.password))
    db.add(user)
    db.commit()
    db.refresh(user)

    if invite is not None:
        invite.used_by_user_id = user.id
        invite.used_at = datetime.datetime.now(datetime.UTC)
        db.commit()

    # Cada cuenta nueva arranca con la rutina GYM 1/2/3 y los hábitos base.
    seed_user(db, user.id)

    return _token_for(user)


@router.post("/login", response_model=TokenResponse, dependencies=_limited)
def login(data: LoginRequest, db: DbSession):
    user = db.scalar(select(User).where(User.email == data.email.lower()))
    if user is None or not verify_password(data.password, user.password_hash):
        # Mismo mensaje exista o no el email: no filtramos qué cuentas existen.
        raise HTTPException(401, "Email o contraseña incorrectos")
    return _token_for(user)


@router.post("/recovery-code", response_model=RecoveryCodeResponse)
def generate_recovery_code(db: DbSession, user: CurrentUser):
    """Genera (o regenera, invalidando el anterior) el código de recuperación.

    Solo se guarda el hash bcrypt: el código en claro viaja una única vez en
    esta respuesta y no se puede volver a consultar — como una recovery key
    de 2FA. El usuario debe guardarlo en su gestor de contraseñas.
    """
    code = generate_friendly_code(groups=3)
    user.recovery_code_hash = hash_password(code)
    db.commit()
    return RecoveryCodeResponse(recovery_code=code)


@router.post("/reset-password", response_model=TokenResponse, dependencies=_limited)
def reset_password(data: ResetPasswordRequest, db: DbSession):
    """Restablece la contraseña con email + código de recuperación (un uso)."""
    user = db.scalar(select(User).where(User.email == data.email.lower()))
    code = normalize_code(data.recovery_code)
    # Un único mensaje de error para todos los fallos: no revelamos si el
    # email existe ni si tiene código de recuperación configurado.
    if (
        user is None
        or user.recovery_code_hash is None
        or not verify_password(code, user.recovery_code_hash)
    ):
        raise HTTPException(401, "Email o código de recuperación incorrectos")

    user.password_hash = hash_password(data.new_password)
    user.recovery_code_hash = None  # un solo uso: tras usarlo, se genera otro desde Ajustes
    db.commit()
    db.refresh(user)
    return _token_for(user)


@router.get("/me", response_model=UserRead)
def me(user: CurrentUser):
    return user
