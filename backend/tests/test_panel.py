import hashlib
import hmac
import json
from datetime import date, datetime, timedelta, timezone

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import select

from app.database.enums import Papel
from app.database.models import Atendente, Conversa, Mensagem
from app.main import create_app
from app.services import auth
from tests.bot_harness import Bot
from tests.conftest import FIXED_NOW

pytestmark = pytest.mark.asyncio
PROXY = {"X-Proxy-Secret": "proxy-secret-for-tests"}
PASSWORD = "senha-super-segura-1"


@pytest_asyncio.fixture
async def api(session_factory, deps):
    auth.limiter._fails.clear()
    app = create_app()
    app.state.session_factory, app.state.deps = session_factory, deps
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t", headers=PROXY) as c:
        yield c


async def make_user(factory, email="admin@x.com", papel=Papel.ADMIN, ativo=True):
    async with factory() as s:
        async with s.begin():
            s.add(Atendente(nome="Fulano", email=email, senha_hash=auth.hash_password(PASSWORD), papel=papel, ativo=ativo))


async def login(api, email="admin@x.com", password=PASSWORD):
    r = await api.post("/panel/auth/login", json={"email": email, "senha": password})
    return r


async def authed(api, factory, email="admin@x.com", papel=Papel.ADMIN):
    await make_user(factory, email, papel)
    token = (await login(api, email)).json()["token"]
    return {**PROXY, "Authorization": f"Bearer {token}"}


async def test_proxy_secret_required(api):
    r = await api.get("/panel/auth/me", headers={"X-Proxy-Secret": "errado"})
    assert r.status_code == 403
    r = await api.get("/panel/servicos", headers={"X-Proxy-Secret": ""})
    assert r.status_code == 403


async def test_login_flow_and_logout_revokes(api, session_factory):
    await make_user(session_factory)
    assert (await login(api, password="errada")).status_code == 401
    r = await login(api)
    assert r.status_code == 200 and r.json()["usuario"]["papel"] == "ADMIN"
    h = {**PROXY, "Authorization": f"Bearer {r.json()['token']}"}
    assert (await api.get("/panel/auth/me", headers=h)).json()["email"] == "admin@x.com"
    assert (await api.get("/panel/auth/me")).status_code == 401
    assert (await api.post("/panel/auth/logout", headers=h)).status_code == 204
    assert (await api.get("/panel/auth/me", headers=h)).status_code == 401


async def test_login_rate_limited(api, session_factory):
    await make_user(session_factory)
    for _ in range(5):
        assert (await login(api, password="x")).status_code == 401
    assert (await login(api)).status_code == 429


async def test_inactive_user_cannot_login_and_deactivation_revokes(api, session_factory):
    await make_user(session_factory, "off@x.com", ativo=False)
    assert (await login(api, "off@x.com")).status_code == 401
    admin = await authed(api, session_factory)
    await make_user(session_factory, "a@x.com", Papel.ATENDENTE)
    tok = (await login(api, "a@x.com")).json()["token"]
    h = {**PROXY, "Authorization": f"Bearer {tok}"}
    assert (await api.get("/panel/auth/me", headers=h)).status_code == 200
    users = (await api.get("/panel/equipe", headers=admin)).json()["items"]
    uid = next(u["id"] for u in users if u["email"] == "a@x.com")
    assert (await api.patch(f"/panel/equipe/{uid}", json={"ativo": False}, headers=admin)).status_code == 200
    assert (await api.get("/panel/auth/me", headers=h)).status_code == 401


async def test_authorization_by_role(api, session_factory):
    att = await authed(api, session_factory, "att@x.com", Papel.ATENDENTE)
    assert (await api.get("/panel/equipe", headers=att)).status_code == 403
    assert (await api.patch("/panel/servicos/1", json={"ativo": False}, headers=att)).status_code == 403
    assert (await api.put("/panel/agenda/config", json={"slot_minutos": 30, "antecedencia_minima_horas": 1, "janela_dias": 10}, headers=att)).status_code == 403
    assert (await api.get("/panel/servicos", headers=att)).status_code == 200


async def test_admin_manages_team(api, session_factory):
    admin = await authed(api, session_factory)
    r = await api.post("/panel/equipe", json={"nome": "Nova", "email": "nova@x.com", "senha": "12345678901", "papel": "ATENDENTE"}, headers=admin)
    assert r.status_code == 201 and "senha" not in json.dumps(r.json())
    assert (await api.post("/panel/equipe", json={"nome": "Nova", "email": "nova@x.com", "senha": "12345678901"}, headers=admin)).status_code == 409
    assert (await api.post("/panel/equipe", json={"nome": "Curta", "email": "c@x.com", "senha": "123"}, headers=admin)).status_code == 422
    me = (await api.get("/panel/auth/me", headers=admin)).json()["id"]
    assert (await api.patch(f"/panel/equipe/{me}", json={"ativo": False}, headers=admin)).status_code == 409


async def test_dashboard_shape(api, session_factory):
    h = await authed(api, session_factory)
    d = (await api.get("/panel/dashboard", headers=h)).json()
    assert set(d) == {"avaliacoes_hoje", "proximas_avaliacoes", "aguardando_acao", "novos_clientes_7d", "conversas_aguardando_equipe"}


async def test_bot_booking_visible_in_panel_and_photos_signed(api, session_factory, deps, monkeypatch):
    h = await authed(api, session_factory)
    bot = Bot(session_factory, deps, "5511988887777", monkeypatch, FIXED_NOW)
    await bot.send("oi"); await bot.send("2"); await bot.send("Ana Paula")
    await bot.send(option="nao_sei"); await bot.send(option="nao_sei"); await bot.send(option="enviar_fotos")
    await bot.send(image_id="m1"); await bot.send(option="continuar")
    await bot.send("Fiat Uno"); await bot.send("2010"); await bot.send("ABC1234"); await bot.send("Bati na traseira")
    await bot.send("1"); await bot.send("1"); await bot.send("1")

    clientes = (await api.get("/panel/clientes", params={"q": "ana"}, headers=h)).json()
    assert clientes["total"] == 1
    assert (await api.get("/panel/clientes", params={"q": "abc1234"}, headers=h)).json()["total"] == 1
    assert (await api.get("/panel/clientes", params={"q": "11988887777"}, headers=h)).json()["total"] == 1
    cid = clientes["items"][0]["id"]
    detail = (await api.get(f"/panel/clientes/{cid}", headers=h)).json()
    assert detail["veiculos"][0]["descricao"] == "Fiat Uno (ABC1234)" and len(detail["agendamentos"]) == 1

    av_id = detail["agendamentos"][0]["avaliacao_id"]
    av = (await api.get(f"/panel/avaliacoes/{av_id}", headers=h)).json()
    assert av["status"] == "PENDENTE" and av["descricao_problema"] == "Bati na traseira"
    assert len(av["fotos"]) == 1 and av["fotos"][0]["url"].startswith("memory://avaliacoes/")

    servicos = (await api.get("/panel/servicos", headers=h)).json()["items"]
    r = await api.patch(f"/panel/avaliacoes/{av_id}", headers=h, json={"servico_identificado_id": servicos[0]["id"], "observacoes_internas": "Paralama e porta"})
    assert r.json()["servico_identificado"]["nome"] == "Funilaria" and r.json()["observacoes_internas"] == "Paralama e porta"

    r = await api.patch(f"/panel/clientes/{cid}", json={"nome": "Ana Paula Souza"}, headers=h)
    assert r.json()["nome"] == "Ana Paula Souza"

    ag = av["agendamentos"][0]
    r = await api.patch(f"/panel/agenda/agendamentos/{ag['id']}", json={"status": "CONFIRMADO"}, headers=h)
    assert r.json()["status"] == "CONFIRMADO"
    r = await api.patch(f"/panel/agenda/agendamentos/{ag['id']}", json={"status": "CANCELADO", "motivo": "Cliente ligou"}, headers=h)
    assert r.json()["status"] == "CANCELADO"
    hist = (await api.get(f"/panel/avaliacoes/{av_id}", headers=h)).json()["historico"]
    assert [x["status_novo"] for x in hist][:2] == ["CANCELADO", "CONFIRMADO"]


async def test_agenda_manual_block_and_overlap(api, session_factory):
    h = await authed(api, session_factory)
    async with session_factory() as s:
        from app.database.models import Cliente
        async with s.begin():
            s.add(Cliente(telefone="5511900000001", nome="Manual"))
    cid = (await api.get("/panel/clientes", headers=h)).json()["items"][0]["id"]
    today = date.today()
    day = today + timedelta(days=(1 - today.weekday()) % 7 + 14)  # terça daqui a >=14 dias
    slots = (await api.get("/panel/agenda/slots", params={"data": day.isoformat()}, headers=h)).json()["slots"]
    assert len(slots) == 8
    first = slots[0]
    r = await api.post("/panel/agenda/agendamentos", json={"cliente_id": cid, "inicio": first}, headers=h)
    assert r.status_code == 201 and r.json()["status"] == "CONFIRMADO"
    assert (await api.post("/panel/agenda/agendamentos", json={"cliente_id": cid, "inicio": first}, headers=h)).status_code == 409
    assert (await api.post("/panel/agenda/agendamentos", json={"cliente_id": cid, "inicio": "2030-01-01T10:00:00"}, headers=h)).status_code == 422
    slots2 = (await api.get("/panel/agenda/slots", params={"data": day.isoformat()}, headers=h)).json()["slots"]
    assert first not in slots2 and len(slots2) == 7  # criado pela equipe => ocupado para o bot

    second = datetime.fromisoformat(slots2[0])
    r = await api.post("/panel/agenda/bloqueios", json={"inicio": second.isoformat(), "fim": (second + timedelta(hours=2)).isoformat(), "motivo": "Reunião"}, headers=h)
    assert r.status_code == 201
    slots3 = (await api.get("/panel/agenda/slots", params={"data": day.isoformat()}, headers=h)).json()["slots"]
    assert len(slots3) == 5
    bid = r.json()["id"]
    assert (await api.delete(f"/panel/agenda/bloqueios/{bid}", headers=h)).status_code == 204
    assert len((await api.get("/panel/agenda/slots", params={"data": day.isoformat()}, headers=h)).json()["slots"]) == 7  # liberado volta a aparecer

    agenda = (await api.get("/panel/agenda", params={"inicio": day.isoformat(), "fim": day.isoformat()}, headers=h)).json()
    assert len(agenda["agendamentos"]) == 1 and agenda["config"]["slot_minutos"] == 60 and agenda["timezone"] == "America/Sao_Paulo"


async def test_conversation_takeover_reply_and_return(api, session_factory, deps, monkeypatch):
    h = await authed(api, session_factory)
    bot = Bot(session_factory, deps, "5511955554444", monkeypatch, FIXED_NOW)
    await bot.send("oi"); await bot.send("atendente")
    convs = (await api.get("/panel/conversas", params={"modo": "AGUARDANDO_EQUIPE"}, headers=h)).json()["items"]
    assert len(convs) == 1
    cid = convs[0]["id"]
    # sem assumir não pode responder
    assert (await api.post(f"/panel/conversas/{cid}/mensagens", json={"texto": "Olá"}, headers=h)).status_code == 409
    async with session_factory() as s:
        async with s.begin():
            (await s.get(Conversa, cid)).ultima_msg_cliente_em = datetime.now(timezone.utc)
    assert (await api.post(f"/panel/conversas/{cid}/assumir", headers=h)).json()["modo"] == "HUMANO"
    r = await api.post(f"/panel/conversas/{cid}/mensagens", json={"texto": "Olá, sou o Luiz"}, headers=h)
    assert r.status_code == 201 and deps.wa.sent[-1][1].body == "Olá, sou o Luiz"
    assert await bot.send("obrigado") == []  # bot segue calado
    full = (await api.get(f"/panel/conversas/{cid}", headers=h)).json()
    assert [m["remetente"] for m in full["mensagens"]][-2:] == ["ATENDENTE", "CLIENTE"]
    # janela de 24h fechada
    async with session_factory() as s:
        async with s.begin():
            (await s.get(Conversa, cid)).ultima_msg_cliente_em = datetime.now(timezone.utc) - timedelta(hours=25)
    assert (await api.post(f"/panel/conversas/{cid}/mensagens", json={"texto": "x"}, headers=h)).status_code == 409
    # devolver ao bot
    assert (await api.post(f"/panel/conversas/{cid}/devolver", headers=h)).json()["modo"] == "BOT"
    out = await bot.send("oi")
    assert out and "Como podemos ajudar" in out[0].body


def _signed(payload: dict) -> tuple[bytes, dict]:
    body = json.dumps(payload).encode()
    sig = "sha256=" + hmac.new(b"app-secret", body, hashlib.sha256).hexdigest()
    return body, {"X-Hub-Signature-256": sig, "Content-Type": "application/json"}


def _wa_payload(text: str, mid: str, phone_id: str = "123", wa_id: str = "551133334444"):
    return {"object": "whatsapp_business_account", "entry": [{"changes": [{"value": {
        "metadata": {"phone_number_id": phone_id}, "contacts": [{"wa_id": wa_id, "profile": {"name": "Zé"}}],
        "messages": [{"from": wa_id, "id": mid, "type": "text", "text": {"body": text}}]}}]}]}


async def test_webhook_end_to_end_replies_and_dedupes(api, session_factory, deps):
    body, headers = _signed(_wa_payload("Olá", "wamid.E2E1"))
    assert (await api.post("/webhook", content=body, headers=headers)).status_code == 200
    assert len(deps.wa.sent) == 1 and deps.wa.sent[0][0] == "551133334444"
    assert len(deps.wa.sent[0][1].options) == 4
    assert (await api.post("/webhook", content=body, headers=headers)).status_code == 200  # reenvio da Meta
    assert len(deps.wa.sent) == 1
    async with session_factory() as s:
        senders = [m.remetente.value for m in (await s.scalars(select(Mensagem).order_by(Mensagem.id))).all()]
        assert senders == ["CLIENTE", "BOT"]


async def test_webhook_ignores_other_phone_number_and_bad_signature(api, deps):
    body, headers = _signed(_wa_payload("Olá", "wamid.X", phone_id="999"))
    assert (await api.post("/webhook", content=body, headers=headers)).status_code == 200
    assert deps.wa.sent == []
    body, _ = _signed(_wa_payload("Olá", "wamid.Y"))
    assert (await api.post("/webhook", content=body, headers={"X-Hub-Signature-256": "sha256=00"})).status_code == 403
