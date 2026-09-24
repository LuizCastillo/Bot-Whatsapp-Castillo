import logging

import httpx

from app.schemas.messaging import Out
from app.services.whatsapp.payloads import build_payload

logger = logging.getLogger(__name__)


class WhatsAppClient:
    def __init__(self, token: str, phone_number_id: str, api_version: str, http: httpx.AsyncClient | None = None):
        self._token = token
        self._phone_id = phone_number_id
        self._base = f"https://graph.facebook.com/{api_version}"
        self._http = http or httpx.AsyncClient(timeout=20)

    @property
    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._token}"}

    async def send(self, to: str, out: Out) -> None:
        r = await self._http.post(f"{self._base}/{self._phone_id}/messages", json=build_payload(to, out),
                                  headers=self._headers)
        if r.status_code >= 400:
            logger.error("Falha ao enviar mensagem (status=%s): %s", r.status_code, r.text[:300])
            r.raise_for_status()

    async def download_media(self, media_id: str) -> tuple[bytes, str]:
        meta = await self._http.get(f"{self._base}/{media_id}", headers=self._headers)
        meta.raise_for_status()
        info = meta.json()
        data = await self._http.get(info["url"], headers=self._headers)
        data.raise_for_status()
        return data.content, info.get("mime_type", "application/octet-stream")

    async def aclose(self) -> None:
        await self._http.aclose()
