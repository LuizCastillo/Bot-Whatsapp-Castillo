import pytest

from app.flows.runner import handle_incoming
from app.schemas.messaging import Incoming
from sqlalchemy import select

from app.database.enums import Modo, StatusAgendamento
from app.database.models import Agendamento, Avaliacao, Cliente, Conversa, FotoAvaliacao, HistoricoAgendamento, Veiculo

WA = "551199999999"  # sem o 9º dígito, como a Meta às vezes envia
_n = 0


async def say(app, text=None, option=None, image=None, wa=WA):
    global _n
    _n += 1
    deps = app.state.deps
    before = len(deps.wa.sent)
    if image:
        m = Incoming(wa_message_id=f"m{_n}", wa_id=wa, type="image", media_id=image, mime_type="image/jpeg")
    elif option:
        m = Incoming(wa_message_id=f"m{_n}", wa_id=wa, type="interactive", option_id=option, text=option)
    else:
        m = Incoming(wa_message_id=f"m{_n}", wa_id=wa, type="text", text=text)
    await handle_incoming(deps, m)
    return [o for _, o in deps.wa.sent[before:]]


def last(outs):
    return outs[-1]


def ids(out):
    return [o[0] for o in out.options]


async def book(app, first_msg, name="joão silva"):
    """Percorre o fluxo até a confirmação; devolve a saída final da confirmação."""
    outs = await say(app, first_msg)
    if "AGUARDANDO_NOME" and "qual é o seu nome" in last(outs).body:
        outs = await say(app, name)
    assert "marca e o modelo" in last(outs).body
    outs = await say(app, "Honda Civic")
    outs = await say(app, "2019")
    outs = await say(app, "ABC1D23")
    outs = await say(app, option="pular")  # descrição
    day = ids(last(outs))[0]
    outs = await say(app, option=day)
    slot = ids(last(outs))[0]
    outs = await say(app, option=slot)
    assert "avaliação presencial" in last(outs).body
    return await say(app, option="confirmar")


async def test_site_flow_books_assessment(app):
    outs = await book(app, "Olá! Vim pelo site e gostaria de agendar o serviço de Funilaria. (ref: funilaria)")
    assert "Sua avaliação ficou agendada" in last(outs).body
    assert "Rua Teste, 100" in last(outs).body
    assert "serviço será realizado" not in last(outs).body
    async with app.state.session_factory() as s:
        cli = await s.scalar(select(Cliente))
        assert cli.telefone == "5511999999999" and cli.nome == "João Silva"
        av = await s.scalar(select(Avaliacao))
        assert av.servico_pretendido_id is not None and av.veiculo_id is not None
        ag = await s.scalar(select(Agendamento))
        assert ag.status == StatusAgendamento.PENDENTE
        conv = await s.scalar(select(Conversa))
        assert conv.origem.value == "SITE"
        assert (await s.scalar(select(Veiculo))).placa == "ABC1D23"


async def test_site_flow_fallback_by_name(app):
    outs = await say(app, "Olá! Vim pelo site e gostaria de agendar o serviço de Polimento de Faróis.")
    assert "Polimento de Faróis" in outs[0].body


async def test_direct_menu_and_invalid_option(app):
    outs = await say(app, "oi")
    assert ids(last(outs)) == ["servicos", "agendar", "consultar", "atendente"]
    outs = await say(app, "9")
    assert "não consegui identificar" in last(outs).body


async def test_services_browse(app):
    await say(app, "oi")
    outs = await say(app, "1")
    assert len(last(outs).options) == 10
    outs = await say(app, "1")
    assert "Funilaria" in outs[0].body and "agendar" in ids(last(outs))


async def test_triage_then_photos_then_booking(app):
    app.state.deps.wa.media["img1"] = (b"\xff\xd8fake", "image/jpeg")
    await say(app, "oi")
    outs = await say(app, "2")            # agendar -> nome
    assert "seu nome" in last(outs).body
    outs = await say(app, "Maria")        # -> escolher serviço
    outs = await say(app, option="nao_sei")
    outs = await say(app, option="nao_sei")  # triagem: não sei explicar -> fotos
    assert "📸" in last(outs).body and "orçamento" in last(outs).body
    outs = await say(app, option="enviar_fotos")
    outs = await say(app, image="img1")
    assert "Recebi a foto" in last(outs).body
    outs = await say(app, option="continuar")
    assert "marca e o modelo" in last(outs).body
    async with app.state.session_factory() as s:
        assert (await s.scalar(select(FotoAvaliacao))) is not None
    assert list(app.state.deps.storage.files)


async def test_triage_suggestion_uses_may(app):
    await say(app, "oi")
    await say(app, "2")
    await say(app, "Maria")
    await say(app, option="nao_sei")
    outs = await say(app, option="amassado")
    assert "pode" in last(outs).body and "Funilaria" in last(outs).body
    outs = await say(app, option="continuar")
    assert "marca e o modelo" in last(outs).body


async def test_second_booking_reuses_vehicle_and_slot_disappears(app):
    await book(app, "Olá! Vim pelo site. (ref: funilaria)")
    outs = await say(app, "Olá! Vim pelo site. (ref: pintura-geral)")
    assert "Para qual veículo" in last(outs).body        # veículo já cadastrado
    outs = await say(app, option=ids(last(outs))[0])
    outs = await say(app, option="pular")
    day = ids(last(outs))[0]
    outs = await say(app, option=day)
    first_slots = ids(last(outs))
    async with app.state.session_factory() as s:
        ag = await s.scalar(select(Agendamento))
    from app.utils.timezone import to_local
    taken = to_local(ag.data_hora_inicio, "America/Sao_Paulo").strftime("%H:%M")
    if to_local(ag.data_hora_inicio, "America/Sao_Paulo").date().isoformat() == day:
        assert taken not in first_slots


async def test_double_booking_blocked_for_other_customer(app):
    await book(app, "Olá! Vim pelo site. (ref: funilaria)")
    async with app.state.session_factory() as s:
        ag = await s.scalar(select(Agendamento))
    from app.utils.timezone import to_local
    l = to_local(ag.data_hora_inicio, "America/Sao_Paulo")
    other = "5521988887777"
    await say(app, "Olá! Vim pelo site. (ref: funilaria)", wa=other)
    await say(app, "Pedro", wa=other)
    await say(app, "Fiat Uno", wa=other)
    await say(app, "2015", wa=other)
    await say(app, "pular", wa=other)
    outs = await say(app, option="pular", wa=other)
    days = ids(last(outs))
    outs = await say(app, option=l.date().isoformat(), wa=other) if l.date().isoformat() in days else outs
    if l.date().isoformat() in days:
        assert l.strftime("%H:%M") not in ids(last(outs))


async def test_cancel_keeps_record_and_history(app):
    await book(app, "Olá! Vim pelo site. (ref: funilaria)")
    await say(app, "oi")                       # FINALIZADO -> menu
    outs = await say(app, "3")                 # consultar
    outs = await say(app, "1")                 # primeira avaliação
    assert "Sua avaliação" in last(outs).body
    outs = await say(app, option="cancelar")
    outs = await say(app, option="sim")
    assert "cancelada" in last(outs).body
    async with app.state.session_factory() as s:
        ag = await s.scalar(select(Agendamento))
        assert ag.status == StatusAgendamento.CANCELADO
        hist = (await s.scalars(select(HistoricoAgendamento).order_by(HistoricoAgendamento.id))).all()
        assert [h.status_novo for h in hist] == ["PENDENTE", "CANCELADO"]


async def test_reschedule_records_history(app):
    await book(app, "Olá! Vim pelo site. (ref: funilaria)")
    await say(app, "oi")
    await say(app, "3")
    await say(app, "1")
    outs = await say(app, option="reagendar")
    days = ids(last(outs))
    outs = await say(app, option=days[-1])
    slot = ids(last(outs))[0]
    outs = await say(app, option=slot)
    outs = await say(app, option="confirmar")
    assert "reagendada" in last(outs).body
    async with app.state.session_factory() as s:
        ag = await s.scalar(select(Agendamento))
        assert ag.status == StatusAgendamento.REAGENDADO
        hist = (await s.scalars(select(HistoricoAgendamento))).all()
        assert any(h.inicio_anterior and h.inicio_anterior != h.inicio_novo for h in hist)


async def test_human_handoff_silences_bot(app):
    await say(app, "oi")
    outs = await say(app, "4")
    assert "equipe" in last(outs).body
    outs = await say(app, "alguém aí?")
    assert outs == []
    async with app.state.session_factory() as s:
        c = await s.scalar(select(Conversa))
        assert c.modo == Modo.AGUARDANDO_EQUIPE


async def test_duplicate_webhook_message_is_ignored(app):
    deps = app.state.deps
    m = Incoming(wa_message_id="dup1", wa_id=WA, type="text", text="oi")
    await handle_incoming(deps, m)
    n = len(deps.wa.sent)
    await handle_incoming(deps, m)
    assert len(deps.wa.sent) == n


async def test_menu_command_resets(app):
    await say(app, "oi")
    await say(app, "2")
    outs = await say(app, "menu")
    assert ids(last(outs))[0] == "servicos"
