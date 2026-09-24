import itertools

from app.flows import engine
from app.schemas.messaging import Incoming

_ids = itertools.count(1)


class Bot:
    """Simula um cliente conversando com o motor (sem WhatsApp real)."""

    def __init__(self, factory, deps, wa_id="5511988887777", monkeypatch=None, now=None):
        self.factory, self.deps, self.wa_id = factory, deps, wa_id
        self.last = []
        if monkeypatch and now:
            monkeypatch.setattr(engine, "utcnow", lambda: now)

    async def send(self, text=None, option=None, image_id=None, msg_id=None, type_=None):
        if image_id:
            m = Incoming(msg_id or f"wamid.{next(_ids)}", self.wa_id, "image", media_id=image_id, mime_type="image/jpeg")
        elif option:
            m = Incoming(msg_id or f"wamid.{next(_ids)}", self.wa_id, "interactive", option_id=option, text=option)
        else:
            m = Incoming(msg_id or f"wamid.{next(_ids)}", self.wa_id, type_ or "text", text=text)
        async with self.factory() as s:
            async with s.begin():
                res = await engine.process_incoming(s, self.deps, m)
        self.last = res.outbox if res else []
        return self.last

    @property
    def body(self) -> str:
        return "\n".join(o.body for o in self.last)

    @property
    def options(self) -> list[tuple[str, str]]:
        return self.last[-1].options if self.last else []
