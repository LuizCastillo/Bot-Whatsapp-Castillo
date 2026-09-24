import logging
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.enums import Modo, Origem, Remetente
from app.flows import appointment, human, main_menu, manage, photos, services_flow, triage  # noqa: F401 (registra handlers)
from app.flows.base import HANDLERS, Ctx, norm
from app.flows.site import detect_site_service
from app.schemas.messaging import Incoming, Out
from app.services import catalog, clients, conversations
from app.services.deps import Deps
from app.utils.timezone import utcnow

logger = logging.getLogger(__name__)

@dataclass
class Result:
    wa_id: str
    conversa_id: int
    outbox: list[Out] = field(default_factory=list)


MENU_WORDS = {"menu", "inicio", "voltar ao menu"}
HUMAN_WORDS = {"atendente", "humano", "falar com atendente"}


def resolve_choice(msg: Incoming, option_ids: list[str], prompt_options: list) -> str | None:
    if msg.option_id and msg.option_id in option_ids:
        return msg.option_id
    text = (msg.text or "").strip()
    if not text:
        return None
    if text.isdigit() and 1 <= int(text) <= len(option_ids):
        return option_ids[int(text) - 1]
    for oid, title in prompt_options:
        if norm(title) == norm(text):
            return oid
    return None


def _content(msg: Incoming) -> tuple[str, str]:
    if msg.type == "image":
        return "IMAGE", msg.text or "[imagem]"
    if msg.type == "interactive":
        return "BUTTON", msg.text or msg.option_id or ""
    if msg.type == "text":
        return "TEXT", msg.text or ""
    return "OTHER", "[mensagem não suportada]"


async def process_incoming(session: AsyncSession, deps: Deps, msg: Incoming) -> Result:
    """Processa uma mensagem e devolve as respostas a enviar."""
    now = utcnow()
    cliente, _ = await clients.get_or_create(session, msg.wa_id)
    conversa = await conversations.get_active(session, cliente, now, deps.settings.conversa_timeout_horas)
    if await conversations.message_exists(session, msg.wa_message_id):
        return Result(msg.wa_id, conversa.id)  # reenvio da Meta: idempotência
    tipo, conteudo = _content(msg)
    conversations.add_message(session, conversa.id, Remetente.CLIENTE, tipo, conteudo, msg.wa_message_id,
                              msg.media_id)
    conversa.ultima_msg_cliente_em = now
    if conversa.modo != Modo.BOT:
        return Result(msg.wa_id, conversa.id)  # equipe no controle: só registra

    data = conversa.contexto or {}
    ctx = Ctx(session=session, deps=deps, cliente=cliente, conversa=conversa, msg=msg, now=now)
    ctx.choice = resolve_choice(msg, data.get("options", []), data.get("last_prompt", {}).get("options", []))
    ctx.set(options=[])
    text_norm = norm(msg.text) if msg.type == "text" else ""

    servs = await catalog.list_active(session)
    site_serv = detect_site_service(msg.text, servs) if msg.type == "text" else None

    if site_serv:
        conversa.origem = Origem.SITE
        await appointment.start_from_site(ctx, site_serv)
    elif text_norm in HUMAN_WORDS:
        await human.handoff(ctx)
    elif text_norm in MENU_WORDS:
        await main_menu.show_menu(ctx, greeting=False)
    else:
        h = HANDLERS.get(conversa.estado_atual)
        if h is None:
            logger.error("Estado sem handler: %s", conversa.estado_atual)
            await main_menu.show_menu(ctx)
        else:
            await h(ctx)
    return Result(msg.wa_id, conversa.id, ctx.outbox)
