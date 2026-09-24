import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.database.models import Avaliacao, FotoAvaliacao

ALLOWED_MIME = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}


async def ensure_draft(session: AsyncSession, cliente_id: int, conversa_id: int, avaliacao_id: int | None) -> Avaliacao:
    if avaliacao_id:
        a = await session.get(Avaliacao, avaliacao_id)
        if a:
            return a
    a = Avaliacao(cliente_id=cliente_id, conversa_id=conversa_id)
    session.add(a)
    await session.flush()
    return a


async def add_photo(session: AsyncSession, storage, avaliacao: Avaliacao, data: bytes, mime: str,
                    wa_media_id: str | None, max_bytes: int) -> FotoAvaliacao | None:
    """Valida e salva a foto. Retorna None se rejeitada."""
    mime = (mime or "").split(";")[0].strip().lower()
    if mime not in ALLOWED_MIME or not data or len(data) > max_bytes:
        return None
    path = f"avaliacoes/{avaliacao.id}/{uuid.uuid4().hex}.{ALLOWED_MIME[mime]}"
    await storage.upload(path, data, mime)
    foto = FotoAvaliacao(avaliacao_id=avaliacao.id, storage_path=path, mime_type=mime, tamanho=len(data),
                         wa_media_id=wa_media_id)
    try:
        async with session.begin_nested():
            session.add(foto)
            await session.flush()
    except IntegrityError:
        return None
    return foto
