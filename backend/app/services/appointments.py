from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.enums import ACTIVE_STATUSES, StatusAgendamento
from app.database.models import Agendamento, HistoricoAgendamento
from app.services.availability import get_config


class SlotTaken(Exception):
    pass


class InvalidTransition(Exception):
    pass


_TERMINAL = {StatusAgendamento.CONCLUIDO, StatusAgendamento.NAO_COMPARECEU}


async def _overlaps(session: AsyncSession, inicio: datetime, fim: datetime, exclude_id: int | None = None) -> bool:
    q = select(Agendamento.id).where(Agendamento.status.in_(ACTIVE_STATUSES),
                                     Agendamento.data_hora_inicio < fim, Agendamento.data_hora_fim > inicio)
    if exclude_id:
        q = q.where(Agendamento.id != exclude_id)
    return (await session.scalar(q.limit(1))) is not None


def _hist(ag: Agendamento, old_status, old_inicio, motivo, autor) -> HistoricoAgendamento:
    return HistoricoAgendamento(agendamento_id=ag.id, status_anterior=old_status.value if old_status else None,
                                status_novo=ag.status.value, inicio_anterior=old_inicio, inicio_novo=ag.data_hora_inicio,
                                motivo=motivo, autor=autor)


async def create(session: AsyncSession, avaliacao, inicio: datetime, autor: str,
                 status: StatusAgendamento) -> Agendamento:
    avaliacao_id = getattr(avaliacao, "id", avaliacao)  # aceita o objeto ou o id
    cfg = await get_config(session)
    fim = inicio + timedelta(minutes=cfg.slot_minutos)
    if await _overlaps(session, inicio, fim):
        raise SlotTaken()
    ag = Agendamento(avaliacao_id=avaliacao_id, data_hora_inicio=inicio, data_hora_fim=fim, status=status, criado_por=autor)
    try:
        async with session.begin_nested():
            session.add(ag)
            await session.flush()
    except IntegrityError:
        raise SlotTaken()
    session.add(_hist(ag, None, None, "Criado", autor))
    await session.flush()
    return ag


async def change_status(session: AsyncSession, ag: Agendamento, new: StatusAgendamento, autor: str,
                        motivo: str | None = None) -> None:
    old = ag.status
    if old == new:
        return
    if old in _TERMINAL and new not in _TERMINAL:
        raise InvalidTransition("Agendamento já encerrado.")
    if new in ACTIVE_STATUSES and old not in ACTIVE_STATUSES:
        if await _overlaps(session, ag.data_hora_inicio, ag.data_hora_fim, ag.id):
            raise SlotTaken()
    ag.status = new
    try:
        async with session.begin_nested():
            await session.flush()
    except IntegrityError:
        raise SlotTaken()
    session.add(_hist(ag, old, ag.data_hora_inicio, motivo, autor))
    await session.flush()


async def reschedule(session: AsyncSession, ag: Agendamento, new_inicio: datetime, autor: str,
                     motivo: str | None = None) -> None:
    cfg = await get_config(session)
    new_fim = new_inicio + timedelta(minutes=cfg.slot_minutos)
    if await _overlaps(session, new_inicio, new_fim, ag.id):
        raise SlotTaken()
    old_status, old_inicio = ag.status, ag.data_hora_inicio
    ag.data_hora_inicio, ag.data_hora_fim, ag.status = new_inicio, new_fim, StatusAgendamento.REAGENDADO
    try:
        async with session.begin_nested():
            await session.flush()
    except IntegrityError:
        raise SlotTaken()
    session.add(_hist(ag, old_status, old_inicio, motivo or "Reagendado", autor))
    await session.flush()
