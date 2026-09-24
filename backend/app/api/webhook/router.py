import hmac
import json
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse

from app.config.settings import Settings, get_settings
from app.flows.runner import handle_incoming
from app.services.whatsapp.parser import parse_webhook
from app.services.whatsapp.signature import verify_signature

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhook", tags=["webhook"])


@router.get("", response_class=PlainTextResponse)
async def verify(
    mode: str | None = Query(default=None, alias="hub.mode"),
    token: str | None = Query(default=None, alias="hub.verify_token"),
    challenge: str | None = Query(default=None, alias="hub.challenge"),
    settings: Settings = Depends(get_settings),
) -> str:
    expected = settings.whatsapp_verify_token.get_secret_value()
    if mode == "subscribe" and token and challenge and hmac.compare_digest(token, expected):
        return challenge
    raise HTTPException(status_code=403, detail="Verificação inválida.")


@router.post("")
async def receive(request: Request, background: BackgroundTasks,
                  settings: Settings = Depends(get_settings)) -> dict[str, str]:
    body = await request.body()
    if not verify_signature(body, request.headers.get("x-hub-signature-256"), settings.meta_app_secret.get_secret_value()):
        logger.warning("Webhook com assinatura inválida rejeitado.")
        raise HTTPException(status_code=403, detail="Assinatura inválida.")
    try:
        payload = json.loads(body)
    except ValueError:
        raise HTTPException(status_code=400, detail="JSON inválido.")
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Payload inválido.")
    deps = request.app.state.deps
    for msg in parse_webhook(payload, settings.whatsapp_phone_number_id):
        background.add_task(handle_incoming, deps, msg)
    return {"status": "ok"}
