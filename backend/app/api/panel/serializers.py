from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.database.models import Agendamento, Avaliacao, Cliente, Servico, Veiculo
from app.services import vehicles

SP = aliased(Servico)
SI = aliased(Servico)


def iso(dt):
    return dt.isoformat() if dt else None


def cliente_out(c: Cliente) -> dict:
    return {"id": c.id, "nome": c.nome, "telefone": c.telefone, "criado_em": iso(c.criado_em)}


def veiculo_out(v: Veiculo | None) -> dict | None:
    if not v:
        return None
    return {"id": v.id, "marca": v.marca, "modelo": v.modelo, "ano": v.ano, "placa": v.placa, "descricao": vehicles.label(v)}


def agendamento_out(ag: Agendamento, av: Avaliacao, c: Cliente, v: Veiculo | None, sp: Servico | None, si: Servico | None) -> dict:
    return {
        "id": ag.id, "avaliacao_id": av.id, "inicio": iso(ag.data_hora_inicio), "fim": iso(ag.data_hora_fim),
        "status": ag.status.value, "criado_por": ag.criado_por,
        "cliente": {"id": c.id, "nome": c.nome, "telefone": c.telefone},
        "veiculo": veiculo_out(v),
        "servico_pretendido": sp.nome if sp else None,
        "servico_identificado": si.nome if si else None,
    }


def agendamentos_query():
    return (select(Agendamento, Avaliacao, Cliente, Veiculo, SP, SI)
            .join(Avaliacao, Avaliacao.id == Agendamento.avaliacao_id)
            .join(Cliente, Cliente.id == Avaliacao.cliente_id)
            .outerjoin(Veiculo, Veiculo.id == Avaliacao.veiculo_id)
            .outerjoin(SP, SP.id == Avaliacao.servico_pretendido_id)
            .outerjoin(SI, SI.id == Avaliacao.servico_identificado_id))


async def load_agendamentos(session: AsyncSession, *conds, order=None, limit: int | None = None) -> list[dict]:
    q = agendamentos_query().where(*conds)
    q = q.order_by(order if order is not None else Agendamento.data_hora_inicio)
    if limit:
        q = q.limit(limit)
    return [agendamento_out(*row) for row in (await session.execute(q)).all()]
