from collections import defaultdict
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.enums import ACTIVE_STATUSES
from app.database.models import Agendamento, Bloqueio, ConfiguracaoAgenda, HorarioFuncionamento
from app.utils.timezone import UTC


async def get_config(session: AsyncSession) -> ConfiguracaoAgenda:
    cfg = await session.get(ConfiguracaoAgenda, 1)
    if cfg is None:
        cfg = ConfiguracaoAgenda(id=1, slot_minutos=60, antecedencia_minima_horas=2, janela_dias=14)
        session.add(cfg)
        await session.flush()
    return cfg


async def slots_by_day(session: AsyncSession, tzname: str, start_day: date, end_day: date, now: datetime,
                       exclude_agendamento_id: int | None = None) -> dict[date, list[datetime]]:
    """Fonte única de disponibilidade: funcionamento − bloqueios − agendamentos ativos."""
    cfg = await get_config(session)
    tz = ZoneInfo(tzname)
    by_wd: dict[int, list[HorarioFuncionamento]] = defaultdict(list)
    for h in (await session.scalars(select(HorarioFuncionamento).order_by(HorarioFuncionamento.abre))).all():
        by_wd[h.dia_semana].append(h)

    range_start = datetime.combine(start_day, time.min, tz).astimezone(UTC)
    range_end = datetime.combine(end_day + timedelta(days=1), time.min, tz).astimezone(UTC)
    blocks = (await session.scalars(select(Bloqueio).where(Bloqueio.inicio < range_end, Bloqueio.fim > range_start))).all()
    q = select(Agendamento).where(Agendamento.status.in_(ACTIVE_STATUSES),
                                  Agendamento.data_hora_inicio < range_end, Agendamento.data_hora_fim > range_start)
    if exclude_agendamento_id:
        q = q.where(Agendamento.id != exclude_agendamento_id)
    taken = (await session.scalars(q)).all()

    earliest = now + timedelta(hours=cfg.antecedencia_minima_horas)
    slot = timedelta(minutes=cfg.slot_minutos)
    out: dict[date, list[datetime]] = {}
    d = start_day
    while d <= end_day:
        items: list[datetime] = []
        for h in by_wd.get(d.weekday(), []):
            cur = datetime.combine(d, h.abre, tz)
            end = datetime.combine(d, h.fecha, tz)
            while cur + slot <= end:
                s, e = cur.astimezone(UTC), (cur + slot).astimezone(UTC)
                if (s >= earliest
                        and not any(b.inicio < e and b.fim > s for b in blocks)
                        and not any(a.data_hora_inicio < e and a.data_hora_fim > s for a in taken)):
                    items.append(s)
                cur += slot
        out[d] = items
        d += timedelta(days=1)
    return out


async def available_days(session: AsyncSession, tzname: str, now: datetime, limit: int = 10,
                         exclude_agendamento_id: int | None = None) -> list[date]:
    cfg = await get_config(session)
    today = now.astimezone(ZoneInfo(tzname)).date()
    data = await slots_by_day(session, tzname, today, today + timedelta(days=cfg.janela_dias), now, exclude_agendamento_id)
    return [d for d, s in data.items() if s][:limit]


async def slots_for_day(session: AsyncSession, tzname: str, day: date, now: datetime,
                        exclude_agendamento_id: int | None = None) -> list[datetime]:
    return (await slots_by_day(session, tzname, day, day, now, exclude_agendamento_id))[day]
