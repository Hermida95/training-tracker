from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession
from app.models.menu import MenuDocument
from app.schemas.menu import MenuRead

router = APIRouter(prefix="/menu", tags=["menu"])

# Lista blanca cerrada. Nada de SVG (puede ejecutar scripts al renderizarse
# inline) ni tipos "genéricos" como octet-stream: solo formatos que el
# navegador muestra de forma inerte.
ALLOWED_MENU_TYPES = {"image/jpeg", "image/png", "image/webp", "application/pdf"}
MAX_FILE_BYTES = 8 * 1024 * 1024  # 8MB: foto de móvil o PDF de nutricionista sobrado


def _get_owned(db, user_id: int, menu_id: int) -> MenuDocument:
    doc = db.get(MenuDocument, menu_id)
    if doc is None or doc.user_id != user_id:
        raise HTTPException(404, "Menú no encontrado")
    return doc


@router.get("", response_model=list[MenuRead])
def list_menus(db: DbSession, user: CurrentUser):
    return list(
        db.scalars(
            select(MenuDocument)
            .where(MenuDocument.user_id == user.id)
            .order_by(MenuDocument.created_at.desc())
        )
    )


@router.post("", response_model=MenuRead, status_code=201)
async def upload_menu(
    db: DbSession,
    user: CurrentUser,
    title: str = Form(min_length=1, max_length=120),
    text_content: str | None = Form(default=None, max_length=20_000),
    file: UploadFile | None = File(default=None),
):
    """Sube el menú: una foto/PDF, texto pegado, o ambos."""
    if file is None and not (text_content and text_content.strip()):
        raise HTTPException(422, "Sube un fichero o pega el menú como texto")

    file_data: bytes | None = None
    content_type: str | None = None
    if file is not None:
        if file.content_type not in ALLOWED_MENU_TYPES:
            raise HTTPException(415, "Formato no soportado: usa JPG, PNG, WebP o PDF")
        # +1 para detectar el desbordamiento sin cargar más de lo necesario.
        file_data = await file.read(MAX_FILE_BYTES + 1)
        if len(file_data) > MAX_FILE_BYTES:
            raise HTTPException(413, "El fichero supera el máximo de 8MB")
        content_type = file.content_type

    doc = MenuDocument(
        user_id=user.id,
        title=title.strip(),
        content_type=content_type,
        file_data=file_data,
        file_size=len(file_data) if file_data else 0,
        text_content=text_content.strip() if text_content else None,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


@router.get("/{menu_id}/file")
def get_menu_file(menu_id: int, db: DbSession, user: CurrentUser):
    doc = _get_owned(db, user.id, menu_id)
    if doc.file_data is None:
        raise HTTPException(404, "Este menú no tiene fichero adjunto")
    return Response(
        content=doc.file_data,
        media_type=doc.content_type,
        headers={
            # inline para que la imagen/PDF se muestre; nosniff evita que el
            # navegador "adivine" otro tipo distinto al declarado.
            "Content-Disposition": f'inline; filename="menu-{doc.id}"',
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, max-age=3600",
        },
    )


@router.delete("/{menu_id}", status_code=204)
def delete_menu(menu_id: int, db: DbSession, user: CurrentUser):
    doc = _get_owned(db, user.id, menu_id)
    db.delete(doc)
    db.commit()
