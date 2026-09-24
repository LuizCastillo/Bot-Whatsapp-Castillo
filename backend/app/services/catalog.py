from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Servico


async def list_active(session: AsyncSession) -> list[Servico]:
    return list((await session.scalars(select(Servico).where(Servico.ativo.is_(True)).order_by(Servico.ordem))).all())


async def by_slug(session: AsyncSession, slug: str) -> Servico | None:
    return await session.scalar(select(Servico).where(Servico.slug == slug, Servico.ativo.is_(True)))
