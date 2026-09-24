import logging
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.panel.deps import current_user, db
from app.api.panel.serializers import iso
from app.database.enums import Modo, Remetente
from app.database.models import Atendente, Cliente, Conversa, Mensagem
from app.schemas.messaging import Out
from app.schemas.panel import MensagemIn
from app.services import conversations
from app.utils.timezone import utcnow

logger = logging.getLogger(__name__)
router = APIRouter(tags=["painel:conversas"], dependencies=[Depends(current_user)])


def _conv(c: Conversa, cl: Cliente) -> dict:
    return {"id": c.id, "modo": c.modo.value, "origem": c.origem.value, "intencao": c.intencao, "estado": c.estado_atual,
            "atendente_id": c.atendente_id, "atualizado_em": iso(c.atualizado_em), "criado_em": iso(c.criado_em),
            "janela_24h_aberta": bool(c.ultima_msg_cliente_em and utcnow() - c.ultima_msg_cliente_em < timedelta(hours=24)),
            "cliente": {"id": cl.id, "nome": cl.nome, "telefone": cl.telefone}}


async def _get(session: AsyncSession, conversa_id: int) -> tuple[Conversa, Cliente]:
    row = (await session.execute(select(Conversa, Cliente).join(Cliente, Cliente.id == Conversa.cliente_id).where(Conversa.id == conversa_id))).first()
    if not row:
        raise HTTPException(404, "Conversa não encontrada.")
    return row


@router.get("/conversas")
async def list_conversas(modo: Modo | None = None, limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0),
                         session: AsyncSession = Depends(db)):
    q = select(Conversa, Cliente).join(Cliente, Cliente.id == Conversa.cliente_id)
    if modo:
        q = q.where(Conversa.modo == modo)
    rows = (await session.execute(q.order_by(Conversa.atualizado_em.desc()).limit(limit).offset(offset))).all()
    items = []
    for c, cl in rows:
        last = await session.scalar(select(Mensagem).where(Mensagem.conversa_id == c.id).order_by(Mensagem.id.desc()).limit(1))
        items.append({**_conv(c, cl), "ultima_mensagem": (last.conteudo[:120] if last else None)})
    return {"items": items}


@router.get("/conversas/{conversa_id}")
async def get_conversa(conversa_id: int, session: AsyncSession = Depends(db)):
    c, cl = await _get(session, conversa_id)
    msgs = (await session.scalars(select(Mensagem).where(Mensagem.conversa_id == c.id).order_by(Mensagem.id).limit(500))).all()
    return {**_conv(c, cl), "mensagens": [{"id": m.id, "remetente": m.remetente.value, "tipo": m.tipo, "conteudo": m.conteudo, "criado_em": iso(m.criado_em)} for m in msgs]}


@router.post("/conversas/{conversa_id}/assumir")
async def assumir(conversa_id: int, user: Atendente = Depends(current_user), session: AsyncSession = Depends(db)):
    c, cl = await _get(session, conversa_id)
    c.modo, c.atendente_id = Modo.HUMANO, user.id
    return _conv(c, cl)


@router.post("/conversas/{conversa_id}/devolver")
async def devolver(conversa_id: int, session: AsyncSession = Depends(db)):
    """Retomar atendimento automático: o bot volta a responder na próxima mensagem do cliente."""
    c, cl = await _get(session, conversa_id)
    c.modo, c.atendente_id, c.estado_atual, c.contexto = Modo.BOT, None, "INICIO", {}
    return _conv(c, cl)


@router.post("/conversas/{conversa_id}/mensagens", status_code=201)
async def enviar(conversa_id: int, body: MensagemIn, request: Request, user: Atendente = Depends(current_user),
                 session: AsyncSession = Depends(db)):
    c, cl = await _get(session, conversa_id)
    if c.modo != Modo.HUMANO:
        raise HTTPException(409, "Assuma a conversa antes de responder.")
    if not c.ultima_msg_cliente_em or utcnow() - c.ultima_msg_cliente_em >= timedelta(hours=24):
        raise HTTPException(409, "Fora da janela de 24h do WhatsApp: só é possível enviar templates aprovados pela Meta.")
    try:
        await request.app.state.deps.wa.send(cl.wa_id or cl.telefone, Out(body.texto))
    except Exception:
        logger.exception("Falha ao enviar mensagem do painel")
        raise HTTPException(502, "Não foi possível enviar pelo WhatsApp.")
    m = conversations.add_message(session, c.id, Remetente.ATENDENTE, "TEXT", body.texto)
    await session.flush()
    return {"id": m.id, "remetente": "ATENDENTE", "tipo": "TEXT", "conteudo": m.conteudo, "criado_em": iso(m.criado_em)}
