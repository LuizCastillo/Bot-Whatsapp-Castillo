from app.database.enums import Modo
from app.flows.base import Ctx
from app.messages import texts


async def handoff(ctx: Ctx, message: str | None = None) -> None:
    ctx.say(message or texts.HANDOFF)
    ctx.conversa.modo = Modo.AGUARDANDO_EQUIPE
    ctx.goto("ENCAMINHADO_HUMANO")
    ctx.conversa.intencao = ctx.conversa.intencao or "ATENDENTE"
