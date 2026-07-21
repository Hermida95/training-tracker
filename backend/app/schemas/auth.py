import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    created_at: datetime.datetime


class RegisterRequest(BaseModel):
    email: EmailStr
    # max 72: bcrypt solo usa los primeros 72 bytes; limitar aquí evita la
    # sorpresa de que dos contraseñas largas distintas validen igual.
    password: str = Field(min_length=8, max_length=72)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead
