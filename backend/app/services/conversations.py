from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.enums import Modo, Origem, Remetente
from app.database.models import Cliente, Conversa, Mensagem


async def get_active(session: AsyncSession, cliente: Cliente, now: datetime, timeout_hours: int) -> Conversa:
    # Inatividade é medida com o relógio real, o mesmo dos timestamps gravados no banco;
    # o `now` injetado serve só para a lógica de agenda.
    now = datetime.now(timezone.utc)
    last = await session.scalar(select(Conversa).where(Conversa.cliente_id == cliente.id)
                                .order_by(Conversa.atualizado_em.desc()).limit(1))
    if last and (last.modo != Modo.BOT or now - last.atualizado_em < timedelta(hours=timeout_hours)):
        return last
    conversa = Conversa(cliente_id=cliente.id, origem=Origem.DIRETO, estado_atual="INICIO", contexto={}, modo=Modo.BOT)
    session.add(conversa)
    await session.flush()
    return conversa


async def message_exists(session: AsyncSession, wa_message_id: str) -> bool:
    return (await session.scalar(select(Mensagem.id).where(Mensagem.wa_message_id == wa_message_id))) is not None


def add_message(session: AsyncSession, conversa_id: int, remetente: Remetente, tipo: str, conteudo: str,
                wa_message_id: str | None = None, midia_ref: str | None = None) -> Mensagem:
    m = Mensagem(conversa_id=conversa_id, remetente=remetente, tipo=tipo, conteudo=conteudo,
                 wa_message_id=wa_message_id, midia_ref=midia_ref)
    session.add(m)
    return m
