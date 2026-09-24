import asyncio
import logging

from app.database.enums import Remetente
from app.flows.engine import process_incoming
from app.schemas.messaging import Incoming
from app.services import conversations
from app.services.deps import Deps
from app.services.whatsapp.payloads import message_type

logger = logging.getLogger(__name__)
_locks: dict[str, asyncio.Lock] = {}


async def handle_incoming(deps: Deps, msg: Incoming) -> None:
    """Processa uma mensagem com lock por número (evita estados embaralhados)."""
    lock = _locks.setdefault(msg.wa_id, asyncio.Lock())
    async with lock:
        try:
            async with deps.session_factory() as session:
                async with session.begin():
                    res = await process_incoming(session, deps, msg)
            for out in res.outbox:
                await deps.wa.send(res.wa_id, out)
                async with deps.session_factory() as session:
                    async with session.begin():
                        conversations.add_message(session, res.conversa_id, Remetente.BOT, message_type(out), out.body)
        except Exception:
            logger.exception("Erro ao processar mensagem %s", msg.wa_message_id)
