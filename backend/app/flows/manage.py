from datetime import timedelta

from sqlalchemy import select

from app.database.enums import ACTIVE_STATUSES, StatusAgendamento
from app.database.models import Agendamento, Avaliacao, Servico, Veiculo
from app.flows.base import Ctx, handler
from app.flows import human
from app.messages import texts
from app.services import appointments
from app.utils.timezone import fmt_data_extenso, fmt_data_curta, fmt_hora, to_local

STATUS_LABEL = {"PENDENTE": "Aguardando confirmação", "CONFIRMADO": "Confirmada", "REAGENDADO": "Reagendada"}


async def get_owned(ctx: Ctx, ag_id: int) -> Agendamento | None:
    q = (select(Agendamento).join(Avaliacao, Avaliacao.id == Agendamento.avaliacao_id)
         .where(Agendamento.id == ag_id, Avaliacao.cliente_id == ctx.cliente.id,
                Agendamento.status.in_(ACTIVE_STATUSES)))
    return await ctx.session.scalar(q)


async def list_appointments(ctx: Ctx) -> None:
    q = (select(Agendamento).join(Avaliacao, Avaliacao.id == Agendamento.avaliacao_id)
         .where(Avaliacao.cliente_id == ctx.cliente.id, Agendamento.status.in_(ACTIVE_STATUSES),
                Agendamento.data_hora_inicio >= ctx.now)
         .order_by(Agendamento.data_hora_inicio).limit(8))
    ags = (await ctx.session.scalars(q)).all()
    if not ags:
        ctx.goto("MENU_PRINCIPAL")
        return ctx.ask(texts.NO_APPOINTMENTS, [("agendar", "Agendar avaliação"), ("menu", "Menu principal")])
    ctx.goto("CONSULTANDO_AVALIACAO")
    opts = []
    for a in ags:
        l = to_local(a.data_hora_inicio, ctx.settings.timezone)
        opts.append((f"ag:{a.id}", f"{fmt_data_curta(l)} às {fmt_hora(l)}"))
    ctx.ask(texts.LIST_APPOINTMENTS, opts + [("menu", "Menu principal")])


@handler("CONSULTANDO_AVALIACAO")
async def choose(ctx: Ctx) -> None:
    from app.flows.main_menu import show_menu
    if ctx.choice == "menu":
        return await show_menu(ctx, greeting=False)
    ag = await get_owned(ctx, int(ctx.choice[3:])) if ctx.choice and ctx.choice.startswith("ag:") else None
    if not ag:
        return await ctx.invalid()
    av = await ctx.session.get(Avaliacao, ag.avaliacao_id)
    serv = await ctx.session.get(Servico, av.servico_pretendido_id) if av.servico_pretendido_id else None
    v = await ctx.session.get(Veiculo, av.veiculo_id) if av.veiculo_id else None
    l = to_local(ag.data_hora_inicio, ctx.settings.timezone)
    ctx.set(ag_id=ag.id)
    ctx.goto("DETALHE_AVALIACAO")
    ctx.ask(texts.appointment_detail(fmt_data_extenso(l), fmt_hora(l), serv.nome if serv else "A definir na avaliação",
                                     f"{v.marca} {v.modelo}" if v else "—", STATUS_LABEL.get(ag.status.value, ag.status.value)),
            [("reagendar", "Reagendar"), ("cancelar", "Cancelar avaliação"), ("menu", "Menu principal")])


@handler("DETALHE_AVALIACAO")
async def detail(ctx: Ctx) -> None:
    from app.flows import appointment
    from app.flows.main_menu import show_menu
    if ctx.choice == "menu":
        return await show_menu(ctx, greeting=False)
    if ctx.choice not in ("reagendar", "cancelar"):
        return await ctx.invalid()
    ag = await get_owned(ctx, ctx.data.get("ag_id", 0))
    if not ag:
        return await human.handoff(ctx)
    if ag.data_hora_inicio - ctx.now < timedelta(hours=ctx.settings.cancelamento_antecedencia_horas):
        return await human.handoff(ctx, texts.TOO_LATE)
    if ctx.choice == "reagendar":
        ctx.set(reagendando_id=ag.id)
        return await appointment.advance(ctx)
    ctx.goto("CANCELANDO_CONFIRMA")
    ctx.ask(texts.CANCEL_ASK, [("sim", "Sim, cancelar"), ("nao", "Não, manter")])


@handler("CANCELANDO_CONFIRMA")
async def cancel(ctx: Ctx) -> None:
    if ctx.choice == "sim":
        ag = await get_owned(ctx, ctx.data.get("ag_id", 0))
        if ag:
            await appointments.change_status(ctx.session, ag, StatusAgendamento.CANCELADO, "BOT", "Cancelado pelo cliente")
        ctx.say(texts.CANCELED)
    elif ctx.choice == "nao":
        ctx.say(texts.KEPT)
    else:
        return await ctx.invalid()
    ctx.reset()
    ctx.goto("FINALIZADO")
