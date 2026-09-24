from app.flows.base import Ctx, handler
from app.messages import texts
from app.services import catalog

TRIAGE = [
    ("colisao", "Sofreu uma colisão", "recuperacao-de-colisoes"),
    ("amassado", "Está amassado", "funilaria"),
    ("pintura", "A pintura está danificada", "pintura-localizada"),
    ("riscos", "Possui riscos ou marcas", "polimento-automotivo"),
    ("acabamento", "Quero melhorar o acabamento", "polimento-automotivo"),
    ("peca", "Preciso trocar uma peça", "substituicao-de-pecas"),
    ("nao_sei", "Não sei explicar", None),
]


async def start(ctx: Ctx) -> None:
    ctx.goto("TRIAGEM")
    ctx.ask(texts.TRIAGE_ASK, [(k, t) for k, t, _ in TRIAGE])


@handler("TRIAGEM")
async def triage(ctx: Ctx) -> None:
    item = next((t for t in TRIAGE if t[0] == ctx.choice), None)
    if not item:
        return await ctx.invalid()
    key, label, slug = item
    if slug is None:
        return await offer_photos(ctx)
    serv = await catalog.by_slug(ctx.session, slug)
    if not serv:
        return await offer_photos(ctx)
    ctx.set(sugestao_slug=slug, triagem_label=label)
    ctx.goto("CONFIRMANDO_SUGESTAO")
    ctx.ask(texts.TRIAGE_SUGGEST.format(servico=serv.nome),
            [("continuar", "Continuar"), ("incerto", "Não tenho certeza")])


@handler("CONFIRMANDO_SUGESTAO")
async def suggestion(ctx: Ctx) -> None:
    from app.flows import appointment
    if ctx.choice == "continuar":
        ctx.set(servico_slug=ctx.data["sugestao_slug"])
        await appointment.advance(ctx)
    elif ctx.choice == "incerto":
        await offer_photos(ctx)
    else:
        await ctx.invalid()


async def offer_photos(ctx: Ctx) -> None:
    ctx.goto("OFERECENDO_FOTOS")
    ctx.ask(texts.PHOTOS_OFFER, [("enviar_fotos", "Enviar fotos"), ("sem_fotos", "Continuar sem fotos")])


@handler("OFERECENDO_FOTOS")
async def photos_offer(ctx: Ctx) -> None:
    from app.flows import appointment
    if ctx.choice == "enviar_fotos":
        ctx.goto("AGUARDANDO_FOTOS")
        ctx.ask(texts.PHOTOS_WAIT, [("continuar", "Continuar")])
    elif ctx.choice == "sem_fotos":
        ctx.set(servico_indefinido=True)
        await appointment.advance(ctx)
    else:
        await ctx.invalid()
