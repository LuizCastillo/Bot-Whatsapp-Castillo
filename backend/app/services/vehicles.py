import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Veiculo

_OLD = re.compile(r"^[A-Z]{3}\d{4}$")
_MERCOSUL = re.compile(r"^[A-Z]{3}\d[A-Z]\d{2}$")


def normalize_plate(raw: str) -> str | None:
    p = re.sub(r"[\s\-]", "", raw or "").upper()
    return p if (_OLD.match(p) or _MERCOSUL.match(p)) else None


async def list_for_client(session: AsyncSession, cliente_id: int, limit: int = 9) -> list[Veiculo]:
    q = select(Veiculo).where(Veiculo.cliente_id == cliente_id).order_by(Veiculo.atualizado_em.desc()).limit(limit)
    return list((await session.scalars(q)).all())


async def create_or_reuse(session: AsyncSession, cliente_id: int, marca: str, modelo: str,
                          ano: int | None, placa: str | None) -> Veiculo:
    if placa:
        existing = await session.scalar(select(Veiculo).where(Veiculo.cliente_id == cliente_id, Veiculo.placa == placa))
        if existing:
            return existing
    v = Veiculo(cliente_id=cliente_id, marca=marca, modelo=modelo, ano=ano, placa=placa)
    session.add(v)
    await session.flush()
    return v


def label(v: Veiculo) -> str:
    return f"{v.marca} {v.modelo}" + (f" ({v.placa})" if v.placa else "")
