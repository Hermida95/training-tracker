from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession
from app.core.rate_limit import check_auth_rate_limit
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserRead
from app.seed.seed_data import seed_user

# Rate limit solo en auth: son los únicos endpoints sin token donde un
# atacante puede iterar (fuerza bruta de contraseñas, alta masiva de cuentas).
router = APIRouter(prefix="/auth", tags=["auth"], dependencies=[Depends(check_auth_rate_limit)])


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(data: RegisterRequest, db: DbSession):
    email = data.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "Ya existe una cuenta con ese email")

    user = User(email=email, password_hash=hash_password(data.password))
    db.add(user)
    db.commit()
    db.refresh(user)

    # Cada cuenta nueva arranca con la rutina GYM 1/2/3 y los hábitos base.
    seed_user(db, user.id)

    return TokenResponse(
        access_token=create_access_token(user.id), user=UserRead.model_validate(user)
    )


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: DbSession):
    user = db.scalar(select(User).where(User.email == data.email.lower()))
    if user is None or not verify_password(data.password, user.password_hash):
        # Mismo mensaje exista o no el email: no filtramos qué cuentas existen.
        raise HTTPException(401, "Email o contraseña incorrectos")
    return TokenResponse(
        access_token=create_access_token(user.id), user=UserRead.model_validate(user)
    )


@router.get("/me", response_model=UserRead)
def me(user: CurrentUser):
    return user
