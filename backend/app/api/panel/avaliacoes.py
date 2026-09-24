import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.panel.deps import current_user, db
from app.api.panel.serializers import agendamento_out, agendamentos_query, cliente_out, iso, load_agendamentos, veiculo_out
from app.config.settings import Settings, get_settings
from app.database.enums import StatusAgendamento
from app.database.models import Agendamento, Avaliacao, Cliente, FotoAvaliacao, HistoricoAgendamento, Servico, Veiculo
from app.schemas.panel import AvaliacaoUpdate
from app.utils.timezone import local_day_range

logger = logging.getLogger(__name__)
router = APIRouter(tags=["painel:avaliacoes"], dependencies=[Depends(current_user)])


@router.get("/avaliacoes")
async def list_avaliacoes(status: StatusAgendamento | None = None, data: date | None = None,
                          limit: int = Query(50, ge=1, le=100), session: AsyncSession = Depends(db),
                          settings: Settings = Depends(get_settings)):
    conds = []
    if status:
        conds.append(Agendamento.status == status)
    if data:
        s, e = local_day_range(data, settings.timezone)
        conds += [Agendamento.data_hora_inicio >= s, Agendamento.data_hora_inicio < e]
    return {"items": await load_agendamentos(session, *conds, order=Agendamento.data_hora_inicio.desc(), limit=limit)}


async def _detail(av: Avaliacao, session: AsyncSession, storage) -> dict:
    cliente = await session.get(Cliente, av.cliente_id)
    veiculo = await session.get(Veiculo, av.veiculo_id) if av.veiculo_id else None
    sp = await session.get(Servico, av.servico_pretendido_id) if av.servico_pretendido_id else None
    si = await session.get(Servico, av.servico_identificado_id) if av.servico_identificado_id else None
    rows = (await session.execute(agendamentos_query().where(Avaliacao.id == av.id).order_by(Agendamento.id.desc()))).all()
    ags = [agendamento_out(*r) for r in rows]
    ag_ids = [a["id"] for a in ags]
    hist = []
    if ag_ids:
        hist = (await session.scalars(select(HistoricoAgendamento).where(HistoricoAgendamento.agendamento_id.in_(ag_ids))
                                      .order_by(HistoricoAgendamento.id.desc()))).all()
    fotos = []
    for f in (await session.scalars(select(FotoAvaliacao).where(FotoAvaliacao.avaliacao_id == av.id).order_by(FotoAvaliacao.id))).all():
        try:
            url = await storage.signed_url(f.storage_path, 300)  # URL assinada de curta duração
        except Exception:
            logger.exception("Falha ao assinar URL da foto %s", f.id)
            url = None
        fotos.append({"id": f.id, "url": url, "mime_type": f.mime_type, "tamanho": f.tamanho, "criado_em": iso(f.criado_em)})
    return {
        "id": av.id,
        "status": ags[0]["status"] if ags else "RASCUNHO",  # sem agendamento = avaliação iniciada e não concluída
        "cliente": cliente_out(cliente), "veiculo": veiculo_out(veiculo),
        "servico_pretendido": {"id": sp.id, "nome": sp.nome} if sp else None,
        "servico_identificado": {"id": si.id, "nome": si.nome} if si else None,
        "descricao_problema": av.descricao_problema, "observacoes_internas": av.observacoes_internas,
        "conversa_id": av.conversa_id, "criado_em": iso(av.criado_em),
        "agendamentos": ags, "fotos": fotos,
        "historico": [{"agendamento_id": h.agendamento_id, "status_anterior": h.status_anterior, "status_novo": h.status_novo,
                       "inicio_anterior": iso(h.inicio_anterior), "inicio_novo": iso(h.inicio_novo), "motivo": h.motivo,
                       "autor": h.autor, "criado_em": iso(h.criado_em)} for h in hist],
    }


@router.get("/avaliacoes/{av_id}")
async def get_avaliacao(av_id: int, request: Request, session: AsyncSession = Depends(db)):
    av = await session.get(Avaliacao, av_id)
    if not av:
        raise HTTPException(404, "Avaliação não encontrada.")
    return await _detail(av, session, request.app.state.deps.storage)


@router.patch("/avaliacoes/{av_id}")
async def update_avaliacao(av_id: int, body: AvaliacaoUpdate, request: Request, session: AsyncSession = Depends(db)):
    """'Serviço identificado' é só a classificação interna do atendimento — não é orçamento."""
    av = await session.get(Avaliacao, av_id)
    if not av:
        raise HTTPException(404, "Avaliação não encontrada.")
    data = body.model_dump(exclude_unset=True)
    if data.get("servico_identificado_id") and not await session.get(Servico, data["servico_identificado_id"]):
        raise HTTPException(422, "Serviço inválido.")
    for k, v in data.items():
        setattr(av, k, v)
    await session.flush()
    return await _detail(av, session, request.app.state.deps.storage)
