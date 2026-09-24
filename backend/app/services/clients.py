from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Cliente
from app.utils.phone import normalize_br_phone


async def get_or_create(session: AsyncSession, wa_id: str) -> tuple[Cliente, bool]:
    phone = normalize_br_phone(wa_id)
    cliente = await session.scalar(select(Cliente).where(Cliente.telefone == phone))
    if cliente:
        if cliente.wa_id != wa_id:
            cliente.wa_id = wa_id
        return cliente, False
    try:
        async with session.begin_nested():
            cliente = Cliente(telefone=phone, wa_id=wa_id)
            session.add(cliente)
            await session.flush()
        return cliente, True
    except IntegrityError:
        return await session.scalar(select(Cliente).where(Cliente.telefone == phone)), False
