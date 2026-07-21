import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    created_at: datetime.datetime
    has_recovery_code: bool = False
    is_admin: bool = False


class RegisterRequest(BaseModel):
    email: EmailStr
    # max 72: bcrypt solo usa los primeros 72 bytes; limitar aquí evita la
    # sorpresa de que dos contraseñas largas distintas validen igual.
    password: str = Field(min_length=8, max_length=72)
    # Obligatorio salvo para el primer usuario de la instancia (BD sin usuarios).
    invite_code: str | None = None


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    recovery_code: str = Field(min_length=8, max_length=32)
    new_password: str = Field(min_length=8, max_length=72)


class RecoveryCodeResponse(BaseModel):
    """El código en claro se devuelve UNA sola vez, al generarlo."""

    recovery_code: str


class InviteCodeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    created_at: datetime.datetime
    used_at: datetime.datetime | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead
