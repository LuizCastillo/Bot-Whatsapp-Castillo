import logging

from app.flows.base import Ctx, handler
from app.messages import texts
from app.services import assessments

logger = logging.getLogger(__name__)


@handler("AGUARDANDO_FOTOS")
async def photos(ctx: Ctx) -> None:
    from app.flows import appointment
    if ctx.choice == "continuar" or (ctx.text and ctx.text.lower() in ("pronto", "continuar")):
        ctx.set(servico_indefinido=not ctx.data.get("servico_slug"))
        return await appointment.advance(ctx)
    if ctx.msg.type == "image" and ctx.msg.media_id:
        av = await assessments.ensure_draft(ctx.session, ctx.cliente.id, ctx.conversa.id, ctx.data.get("avaliacao_id"))
        ctx.set(avaliacao_id=av.id)
        try:
            data, mime = await ctx.deps.wa.download_media(ctx.msg.media_id)
            foto = await assessments.add_photo(ctx.session, ctx.deps.storage, av, data, mime, ctx.msg.media_id,
                                               ctx.settings.max_foto_mb * 1024 * 1024)
        except Exception:
            logger.exception("Falha ao processar foto")
            foto = None
        if foto:
            ctx.ask(texts.PHOTO_OK, [("continuar", "Continuar")])
        else:
            ctx.ask(texts.PHOTO_FAIL, [("continuar", "Continuar")])
        return
    await ctx.invalid()
