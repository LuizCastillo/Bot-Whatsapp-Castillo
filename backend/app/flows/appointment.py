from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from app.database.enums import StatusAgendamento
from app.database.models import Veiculo
from app.flows.base import Ctx, handler
from app.flows import human, triage
from app.messages import texts
from app.services import appointments, assessments, availability, catalog, vehicles
from app.utils.timezone import UTC, fmt_data_curta, fmt_data_extenso, fmt_hora, to_local


def _tz(ctx: Ctx) -> ZoneInfo:
    return ZoneInfo(ctx.settings.timezone)


async def advance(ctx: Ctx) -> None:
    """Pede a próxima informação que ainda falta (cadastro progressivo)."""
    d = ctx.data
    if d.get("reagendando_id"):
        if not d.get("data"):
            return await ask_date(ctx)
        if not d.get("horario"):
            return await ask_time(ctx)
        return await ask_confirm(ctx)
    if not ctx.cliente.nome:
        ctx.goto("AGUARDANDO_NOME")
        return ctx.ask(texts.ASK_NAME)
    if not d.get("servico_slug") and not d.get("servico_indefinido"):
        servs = await catalog.list_active(ctx.session)
        ctx.goto("ESCOLHENDO_SERVICO")
        return ctx.ask(texts.ASK_SERVICE, [(s.slug, s.nome) for s in servs] + [("nao_sei", "Não sei qual serviço")])
    if not d.get("veiculo_id"):
        return await ask_vehicle(ctx)
    if not d.get("descricao_feita"):
        ctx.goto("AGUARDANDO_DESCRICAO")
        return ctx.ask(texts.ASK_DESCRIPTION, [("pular", "Pular")])
    if not d.get("data"):
        return await ask_date(ctx)
    if not d.get("horario"):
        return await ask_time(ctx)
    await ask_confirm(ctx)


async def start_from_site(ctx: Ctx, servico) -> None:
    ctx.reset()
    ctx.set(servico_slug=servico.slug)
    ctx.conversa.intencao = "AGENDAMENTO"
    from app.database.enums import Origem
    ctx.conversa.origem = Origem.SITE
    nome = ctx.cliente.nome
    ctx.say(texts.site_greeting_known(nome, servico.nome) if nome else texts.site_greeting(servico.nome))
    await advance(ctx)


@handler("AGUARDANDO_NOME")
async def name(ctx: Ctx) -> None:
    t = ctx.text
    if not t or not (2 <= len(t) <= 80) or t.isdigit():
        return await ctx.invalid(text_state=True)
    ctx.cliente.nome = t.title() if t.islower() else t
    ctx.say(texts.NAME_OK.format(nome=ctx.cliente.nome))
    await advance(ctx)


@handler("ESCOLHENDO_SERVICO")
async def choose_service(ctx: Ctx) -> None:
    if ctx.choice == "nao_sei":
        return await triage.start(ctx)
    serv = await catalog.by_slug(ctx.session, ctx.choice) if ctx.choice else None
    if not serv:
        return await ctx.invalid()
    ctx.set(servico_slug=serv.slug)
    await advance(ctx)


# ---- veículo
async def ask_vehicle(ctx: Ctx) -> None:
    vs = await vehicles.list_for_client(ctx.session, ctx.cliente.id)
    if vs:
        ctx.goto("ESCOLHENDO_VEICULO")
        opts = [(f"v:{v.id}", f"{v.marca} {v.modelo}" + (f" ({v.placa})" if v.placa else "")) for v in vs]
        return ctx.ask(texts.ASK_VEHICLE_CHOOSE, opts + [("novo", "Cadastrar outro veículo")])
    ctx.goto("AGUARDANDO_MARCA_MODELO")
    ctx.ask(texts.ASK_MAKE_MODEL)


@handler("ESCOLHENDO_VEICULO")
async def choose_vehicle(ctx: Ctx) -> None:
    if ctx.choice == "novo":
        ctx.goto("AGUARDANDO_MARCA_MODELO")
        return ctx.ask(texts.ASK_MAKE_MODEL)
    if ctx.choice and ctx.choice.startswith("v:"):
        vid = int(ctx.choice[2:])
        v = await ctx.session.get(Veiculo, vid)
        if v and v.cliente_id == ctx.cliente.id:
            ctx.set(veiculo_id=v.id)
            return await advance(ctx)
    await ctx.invalid()


@handler("AGUARDANDO_MARCA_MODELO")
async def make_model(ctx: Ctx) -> None:
    parts = (ctx.text or "").split()
    if len(parts) < 2 or len(ctx.text) > 100:
        return await ctx.invalid(text_state=True)
    ctx.set(veiculo_tmp={"marca": parts[0].title(), "modelo": " ".join(parts[1:])})
    ctx.goto("AGUARDANDO_ANO")
    ctx.ask(texts.ASK_YEAR, [("pular", "Pular")])


@handler("AGUARDANDO_ANO")
async def year(ctx: Ctx) -> None:
    tmp = dict(ctx.data.get("veiculo_tmp") or {})
    if ctx.choice == "pular":
        tmp["ano"] = None
    else:
        t = ctx.text or ""
        if not (t.isdigit() and len(t) == 4 and 1950 <= int(t) <= ctx.now.year + 1):
            return await ctx.invalid(text_state=True)
        tmp["ano"] = int(t)
    ctx.set(veiculo_tmp=tmp)
    ctx.goto("AGUARDANDO_PLACA")
    ctx.ask(texts.ASK_PLATE, [("pular", "Pular")])


@handler("AGUARDANDO_PLACA")
async def plate(ctx: Ctx) -> None:
    tmp = ctx.data.get("veiculo_tmp") or {}
    placa = None
    if ctx.choice != "pular":
        placa = vehicles.normalize_plate(ctx.text or "")
        if not placa:
            return await ctx.invalid(text_state=True)
    v = await vehicles.create_or_reuse(ctx.session, ctx.cliente.id, tmp.get("marca", ""), tmp.get("modelo", ""),
                                       tmp.get("ano"), placa)
    ctx.unset("veiculo_tmp")
    ctx.set(veiculo_id=v.id)
    await advance(ctx)


@handler("AGUARDANDO_DESCRICAO")
async def description(ctx: Ctx) -> None:
    if ctx.choice == "pular":
        label = ctx.data.get("triagem_label")
        ctx.set(descricao_feita=True, descricao=f"Triagem: {label}" if label else None)
    elif ctx.text:
        ctx.set(descricao_feita=True, descricao=ctx.text[:1000])
    else:
        return await ctx.invalid(text_state=True)
    await advance(ctx)


# ---- data / horário
async def ask_date(ctx: Ctx) -> None:
    days = await availability.available_days(ctx.session, ctx.settings.timezone, ctx.now,
                                             exclude_agendamento_id=ctx.data.get("reagendando_id"))
    if not days:
        return await human.handoff(ctx, texts.NO_DAYS)
    ctx.goto("ESCOLHENDO_DATA")
    ctx.ask(texts.ASK_DATE, [(d.isoformat(), fmt_data_curta(datetime(d.year, d.month, d.day))) for d in days])


@handler("ESCOLHENDO_DATA")
async def choose_date(ctx: Ctx) -> None:
    try:
        d = date.fromisoformat(ctx.choice or "")
    except ValueError:
        return await ctx.invalid()
    ctx.set(data=d.isoformat())
    ctx.unset("horario")
    await advance(ctx)


async def ask_time(ctx: Ctx) -> None:
    day = date.fromisoformat(ctx.data["data"])
    slots = await availability.slots_for_day(ctx.session, ctx.settings.timezone, day, ctx.now,
                                             exclude_agendamento_id=ctx.data.get("reagendando_id"))
    if not slots:
        ctx.unset("data", "horario")
        ctx.say(texts.SLOT_TAKEN)
        return await ask_date(ctx)
    local = [to_local(s, ctx.settings.timezone) for s in slots]
    ctx.goto("ESCOLHENDO_HORARIO")
    ctx.ask(texts.ASK_TIME.format(data=fmt_data_extenso(local[0])),
            [(l.strftime("%H:%M"), l.strftime("%H:%M")) for l in local] + [("outra_data", "Escolher outra data")])


@handler("ESCOLHENDO_HORARIO")
async def choose_time(ctx: Ctx) -> None:
    if ctx.choice == "outra_data":
        ctx.unset("data", "horario")
        return await advance(ctx)
    try:
        time.fromisoformat(ctx.choice or "")
    except ValueError:
        return await ctx.invalid()
    ctx.set(horario=ctx.choice)
    await advance(ctx)


def _chosen_utc(ctx: Ctx) -> datetime:
    day = date.fromisoformat(ctx.data["data"])
    return datetime.combine(day, time.fromisoformat(ctx.data["horario"]), _tz(ctx)).astimezone(UTC)


# ---- confirmação
async def ask_confirm(ctx: Ctx) -> None:
    loc = to_local(_chosen_utc(ctx), ctx.settings.timezone)
    ctx.goto("CONFIRMANDO_AGENDAMENTO")
    buttons = [("confirmar", "Confirmar"), ("trocar", "Trocar horário"), ("cancelar", "Cancelar")]
    if ctx.data.get("reagendando_id"):
        return ctx.ask(f"Vou reagendar sua avaliação para {fmt_data_extenso(loc)}, às {fmt_hora(loc)}. Posso confirmar?", buttons)
    slug = ctx.data.get("servico_slug")
    serv = await catalog.by_slug(ctx.session, slug) if slug else None
    v = await ctx.session.get(Veiculo, ctx.data["veiculo_id"])
    veic = f"{v.marca} {v.modelo}" + (f" — {v.placa}" if v.placa else "")
    ctx.ask(texts.confirm_summary(ctx.cliente.nome, serv.nome if serv else "A definir na avaliação", veic,
                                  fmt_data_extenso(loc), fmt_hora(loc)), buttons)


@handler("CONFIRMANDO_AGENDAMENTO")
async def confirm(ctx: Ctx) -> None:
    from app.flows.manage import get_owned
    if ctx.choice == "trocar":
        ctx.unset("data", "horario")
        return await advance(ctx)
    if ctx.choice == "cancelar":
        ctx.say(texts.FLOW_CANCELED)
        ctx.reset()
        return ctx.goto("FINALIZADO")
    if ctx.choice != "confirmar":
        return await ctx.invalid()

    inicio = _chosen_utc(ctx)
    loc = to_local(inicio, ctx.settings.timezone)
    try:
        if ctx.data.get("reagendando_id"):
            ag = await get_owned(ctx, ctx.data["reagendando_id"])
            if not ag:
                return await human.handoff(ctx)
            await appointments.reschedule(ctx.session, ag, inicio, "BOT", "Reagendado pelo cliente")
            ctx.say(texts.rescheduled(ctx.cliente.nome, fmt_data_extenso(loc), fmt_hora(loc)))
        else:
            d = ctx.data
            av = await assessments.ensure_draft(ctx.session, ctx.cliente.id, ctx.conversa.id, d.get("avaliacao_id"))
            serv = await catalog.by_slug(ctx.session, d["servico_slug"]) if d.get("servico_slug") else None
            av.veiculo_id = d["veiculo_id"]
            av.servico_pretendido_id = serv.id if serv else None
            av.descricao_problema = d.get("descricao")
            status = StatusAgendamento(ctx.settings.agendamento_status_inicial)
            await appointments.create(ctx.session, av.id, inicio, "BOT", status)
            ctx.say(texts.scheduled(ctx.cliente.nome, fmt_data_extenso(loc), fmt_hora(loc), ctx.settings.endereco_oficina))
    except appointments.SlotTaken:
        ctx.say(texts.SLOT_TAKEN)
        ctx.unset("horario")
        return await advance(ctx)
    ctx.reset()
    ctx.goto("FINALIZADO")
