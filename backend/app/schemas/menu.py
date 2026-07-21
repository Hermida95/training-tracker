import datetime

from pydantic import BaseModel, ConfigDict


class MenuRead(BaseModel):
    """Metadatos del menú. El binario NUNCA viaja en el listado: se sirve
    aparte en GET /menu/{id}/file para no inflar cada respuesta."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    content_type: str | None = None
    file_size: int
    text_content: str | None = None
    created_at: datetime.datetime

    @property
    def has_file(self) -> bool:  # pragma: no cover - conveniencia
        return self.content_type is not None
