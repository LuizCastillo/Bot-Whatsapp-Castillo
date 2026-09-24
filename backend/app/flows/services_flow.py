from app.flows.base import Ctx, handler
from app.messages import texts
from app.services import catalog


async def list_services(ctx: Ctx) -> None:
    servs = await catalog.list_active(ctx.session)
    ctx.goto("LISTANDO_SERVICOS")
    ctx.ask(texts.SERVICES_TITLE.format(oficina=ctx.settings.nome_oficina),
            [(s.slug, s.nome) for s in servs] + [("menu", "Voltar ao menu")])


@handler("LISTANDO_SERVICOS")
async def listing(ctx: Ctx) -> None:
    from app.flows.main_menu import show_menu
    if ctx.choice == "menu":
        return await show_menu(ctx, greeting=False)
    serv = await catalog.by_slug(ctx.session, ctx.choice) if ctx.choice else None
    if not serv:
        return await ctx.invalid()
    ctx.set(servico_detalhe=serv.slug)
    ctx.goto("DETALHE_SERVICO")
    ctx.say(f"*{serv.nome}*\n{serv.descricao}")
    ctx.ask(texts.SERVICE_DETAIL_ASK, [("agendar", "Agendar avaliação"), ("outros", "Ver outros serviços"),
                                         ("menu", "Menu principal")])


@handler("DETALHE_SERVICO")
async def detail(ctx: Ctx) -> None:
    from app.flows import appointment
    from app.flows.main_menu import show_menu
    if ctx.choice == "agendar":
        slug = ctx.data.get("servico_detalhe")
        ctx.reset()
        ctx.set(servico_slug=slug)
        ctx.conversa.intencao = "AGENDAMENTO"
        await appointment.advance(ctx)
    elif ctx.choice == "outros":
        await list_services(ctx)
    elif ctx.choice == "menu":
        await show_menu(ctx, greeting=False)
    else:
        await ctx.invalid()
