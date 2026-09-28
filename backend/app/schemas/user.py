from pydantic import BaseModel, Field, field_validator


class TelegramLinkIn(BaseModel):
    """`chat_id` tal cual lo devuelve @userinfobot (numérico en texto).

    None desvincula la cuenta (deja de recibir recordatorios).
    """

    chat_id: str | None = Field(default=None, max_length=32)

    @field_validator("chat_id")
    @classmethod
    def _digits_only(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value.lstrip("-").isdigit():
            raise ValueError("El chat_id de Telegram solo contiene dígitos")
        return value
