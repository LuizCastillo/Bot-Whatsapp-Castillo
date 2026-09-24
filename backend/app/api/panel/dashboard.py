from datetime import timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.panel.deps import current_user, db
from app.api.panel.serializers import load_agendamentos
from app.config.settings import Settings, get_settings
from app.database.enums import ACTIVE_STATUSES, Modo, StatusAgendamento
from app.database.models import Agendamento, Cliente, Conversa
from app.utils.timezone import local_day_range, to_local, utcnow

router = APIRouter(tags=["painel:dashboard"], dependencies=[Depends(current_user)])


@router.get("/dashboard")
async def dashboard(session: AsyncSession = Depends(db), settings: Settings = Depends(get_settings)):
    now = utcnow()
    day_start, day_end = local_day_range(to_local(now, settings.timezone).date(), settings.timezone)
    hoje = await load_agendamentos(session, Agendamento.data_hora_inicio >= day_start, Agendamento.data_hora_inicio < day_end,
                                   Agendamento.status != StatusAgendamento.CANCELADO)
    proximas = await load_agendamentos(session, Agendamento.data_hora_inicio >= now, Agendamento.data_hora_inicio < now + timedelta(days=7),
                                       Agendamento.status.in_(ACTIVE_STATUSES), limit=8)
    pendentes = await load_agendamentos(session, Agendamento.status == StatusAgendamento.PENDENTE,
                                        Agendamento.data_hora_inicio >= now, limit=10)
    novos = await session.scalar(select(func.count(Cliente.id)).where(Cliente.criado_em >= now - timedelta(days=7)))
    aguardando = (await session.execute(
        select(Conversa, Cliente).join(Cliente, Cliente.id == Conversa.cliente_id)
        .where(Conversa.modo == Modo.AGUARDANDO_EQUIPE).order_by(Conversa.atualizado_em).limit(10))).all()
    return {
        "avaliacoes_hoje": hoje,
        "proximas_avaliacoes": proximas,
        "aguardando_acao": pendentes,
        "novos_clientes_7d": novos or 0,
        "conversas_aguardando_equipe": [
            {"id": c.id, "cliente": {"id": cl.id, "nome": cl.nome, "telefone": cl.telefone}, "desde": c.atualizado_em.isoformat()}
            for c, cl in aguardando],
    }
