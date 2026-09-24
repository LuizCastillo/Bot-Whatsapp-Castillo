from app.flows.base import Ctx, handler
from app.flows import appointment, human, manage, services_flow
from app.messages import texts

MENU = [("servicos", "Conhecer serviços"), ("agendar", "Agendar avaliação"),
        ("consultar", "Consultar avaliação"), ("atendente", "Falar com atendente")]


async def show_menu(ctx: Ctx, greeting: bool = True) -> None:
    ctx.reset()
    ctx.goto("MENU_PRINCIPAL")
    nome = ctx.cliente.nome
    body = texts.greet_known(nome, ctx.settings.nome_oficina) if nome else texts.greet_new(ctx.settings.nome_oficina)
    ctx.ask(body if greeting else "Como podemos ajudar?", MENU)


async def dispatch_menu_choice(ctx: Ctx, choice: str) -> None:
    if choice == "servicos":
        await services_flow.list_services(ctx)
    elif choice == "agendar":
        ctx.conversa.intencao = "AGENDAMENTO"
        await appointment.advance(ctx)
    elif choice == "consultar":
        await manage.list_appointments(ctx)
    elif choice == "atendente":
        await human.handoff(ctx)
    elif choice == "menu":
        await show_menu(ctx, greeting=False)


@handler("INICIO")
async def inicio(ctx: Ctx) -> None:
    await show_menu(ctx)


@handler("FINALIZADO")
async def finalizado(ctx: Ctx) -> None:
    await show_menu(ctx)


@handler("MENU_PRINCIPAL")
async def menu(ctx: Ctx) -> None:
    if ctx.choice:
        await dispatch_menu_choice(ctx, ctx.choice)
    else:
        await ctx.invalid()
