from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.panel.deps import current_user, db, require_admin
from app.api.panel.serializers import iso, load_agendamentos
from app.config.settings import Settings, get_settings
from app.database.enums import StatusAgendamento
from app.database.models import Agendamento, Avaliacao, Bloqueio, Cliente, HorarioFuncionamento, Servico, Veiculo
from app.schemas.panel import AgendamentoCreate, AgendamentoUpdate, BloqueioIn, ConfigAgendaIn, HorarioIn
from app.services import appointments, availability
from app.utils.timezone import UTC, local_day_range, utcnow
from zoneinfo import ZoneInfo

router = APIRouter(tags=["painel:agenda"], dependencies=[Depends(current_user)])


def _horario(h: HorarioFuncionamento) -> dict:
    return {"id": h.id, "dia_semana": h.dia_semana, "abre": h.abre.strftime("%H:%M"), "fecha": h.fecha.strftime("%H:%M")}


def _config(c) -> dict:
    return {"slot_minutos": c.slot_minutos, "antecedencia_minima_horas": c.antecedencia_minima_horas, "janela_dias": c.janela_dias}


@router.get("/agenda")
async def get_agenda(inicio: date, fim: date, session: AsyncSession = Depends(db), settings: Settings = Depends(get_settings)):
    if fim < inicio or (fim - inicio).days > 62:
        raise HTTPException(422, "Intervalo inválido (máximo 62 dias).")
    start, _ = local_day_range(inicio, settings.timezone)
    _, end = local_day_range(fim, settings.timezone)
    ags = await load_agendamentos(session, Agendamento.data_hora_inicio >= start, Agendamento.data_hora_inicio < end)
    blocks = (await session.scalars(select(Bloqueio).where(Bloqueio.inicio < end, Bloqueio.fim > start).order_by(Bloqueio.inicio))).all()
    horarios = (await session.scalars(select(HorarioFuncionamento).order_by(HorarioFuncionamento.dia_semana, HorarioFuncionamento.abre))).all()
    cfg = await availability.get_config(session)
    return {
        "agendamentos": ags,
        "bloqueios": [{"id": b.id, "inicio": iso(b.inicio), "fim": iso(b.fim), "motivo": b.motivo} for b in blocks],
        "horarios": [_horario(h) for h in horarios],
        "config": _config(cfg),
        "timezone": settings.timezone,
    }


@router.get("/agenda/slots")
async def get_slots(data: date, excluir: int | None = None, session: AsyncSession = Depends(db), settings: Settings = Depends(get_settings)):
    slots = await availability.slots_for_day(session, settings.timezone, data, utcnow(), excluir)
    return {"slots": [iso(s) for s in slots]}


@router.post("/agenda/agendamentos", status_code=201)
async def create_agendamento(body: AgendamentoCreate, user=Depends(current_user), session: AsyncSession = Depends(db)):
    """Criação manual pela equipe (a equipe pode ignorar bloqueios, mas nunca sobrepor outra avaliação)."""
    cliente = await session.get(Cliente, body.cliente_id)
    if not cliente:
        raise HTTPException(404, "Cliente não encontrado.")
    if body.veiculo_id:
        v = await session.get(Veiculo, body.veiculo_id)
        if not v or v.cliente_id != cliente.id:
            raise HTTPException(422, "Veículo não pertence ao cliente.")
    if body.servico_id and not await session.get(Servico, body.servico_id):
        raise HTTPException(422, "Serviço inválido.")
    if body.status not in (StatusAgendamento.PENDENTE, StatusAgendamento.CONFIRMADO):
        raise HTTPException(422, "Status inicial deve ser PENDENTE ou CONFIRMADO.")
    av = Avaliacao(cliente_id=cliente.id, veiculo_id=body.veiculo_id, servico_pretendido_id=body.servico_id, descricao_problema=body.descricao)
    session.add(av)
    await session.flush()
    try:
        ag = await appointments.create(session, av, body.inicio.astimezone(UTC), f"atendente:{user.id}", body.status)
    except appointments.SlotTaken:
        raise HTTPException(409, "Já existe uma avaliação nesse horário.")
    return (await load_agendamentos(session, Agendamento.id == ag.id))[0]


@router.patch("/agenda/agendamentos/{ag_id}")
async def update_agendamento(ag_id: int, body: AgendamentoUpdate, user=Depends(current_user), session: AsyncSession = Depends(db)):
    ag = await session.get(Agendamento, ag_id)
    if not ag:
        raise HTTPException(404, "Agendamento não encontrado.")
    autor = f"atendente:{user.id}"
    try:
        if body.inicio:
            await appointments.reschedule(session, ag, body.inicio.astimezone(UTC), autor, body.motivo)
        if body.status:
            await appointments.change_status(session, ag, body.status, autor, body.motivo)
    except appointments.SlotTaken:
        raise HTTPException(409, "Já existe uma avaliação nesse horário.")
    except appointments.InvalidTransition as e:
        raise HTTPException(409, str(e))
    return (await load_agendamentos(session, Agendamento.id == ag.id))[0]


@router.post("/agenda/bloqueios", status_code=201)
async def create_bloqueio(body: BloqueioIn, user=Depends(current_user), session: AsyncSession = Depends(db)):
    if body.fim <= body.inicio:
        raise HTTPException(422, "O fim deve ser depois do início.")
    b = Bloqueio(inicio=body.inicio.astimezone(UTC), fim=body.fim.astimezone(UTC), motivo=body.motivo, criado_por=user.id)
    session.add(b)
    await session.flush()
    return {"id": b.id, "inicio": iso(b.inicio), "fim": iso(b.fim), "motivo": b.motivo}


@router.delete("/agenda/bloqueios/{bloqueio_id}", status_code=204)
async def delete_bloqueio(bloqueio_id: int, session: AsyncSession = Depends(db)):
    if not await session.get(Bloqueio, bloqueio_id):
        raise HTTPException(404, "Bloqueio não encontrado.")
    await session.execute(delete(Bloqueio).where(Bloqueio.id == bloqueio_id))


@router.get("/agenda/config")
async def get_config(session: AsyncSession = Depends(db)):
    return _config(await availability.get_config(session))


@router.put("/agenda/config", dependencies=[Depends(require_admin)])
async def put_config(body: ConfigAgendaIn, session: AsyncSession = Depends(db)):
    cfg = await availability.get_config(session)
    for k, v in body.model_dump().items():
        setattr(cfg, k, v)
    return _config(cfg)


@router.put("/agenda/horarios", dependencies=[Depends(require_admin)])
async def put_horarios(body: list[HorarioIn], session: AsyncSession = Depends(db)):
    for h in body:
        if h.abre >= h.fecha:
            raise HTTPException(422, "O horário de abertura deve ser antes do fechamento.")
    await session.execute(delete(HorarioFuncionamento))
    for h in body:
        session.add(HorarioFuncionamento(dia_semana=h.dia_semana, abre=h.abre, fecha=h.fecha))
    await session.flush()
    rows = (await session.scalars(select(HorarioFuncionamento).order_by(HorarioFuncionamento.dia_semana, HorarioFuncionamento.abre))).all()
    return [_horario(h) for h in rows]
