import re
import unicodedata
from dataclasses import dataclass, field
from typing import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Cliente, Conversa
from app.messages import texts
from app.schemas.messaging import Incoming, Out
from app.services.deps import Deps


def norm(s: str | None) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    return re.sub(r"\s+", " ", "".join(c for c in s if not unicodedata.combining(c))).strip().lower()


@dataclass
class Ctx:
    session: AsyncSession
    deps: Deps
    cliente: Cliente
    conversa: Conversa
    msg: Incoming
    now: "object"
    choice: str | None = None
    outbox: list[Out] = field(default_factory=list)

    @property
    def data(self) -> dict:
        return self.conversa.contexto or {}

    @property
    def text(self) -> str | None:
        return self.msg.text.strip() if self.msg.type == "text" and self.msg.text else None

    @property
    def settings(self):
        return self.deps.settings

    def set(self, **kw) -> None:
        self.conversa.contexto = {**self.data, **kw}

    def unset(self, *keys: str) -> None:
        self.conversa.contexto = {k: v for k, v in self.data.items() if k not in keys}

    def reset(self) -> None:
        self.conversa.contexto = {}

    def goto(self, state: str) -> None:
        self.conversa.estado_atual = state

    def say(self, body: str) -> None:
        self.outbox.append(Out(body))

    def ask(self, body: str, options: list[tuple[str, str]] | None = None) -> None:
        options = options or []
        self.outbox.append(Out(body, options))
        self.set(options=[o[0] for o in options], last_prompt={"body": body, "options": options}, invalid=0)

    async def invalid(self, text_state: bool = False) -> None:
        n = self.data.get("invalid", 0) + 1
        lp = self.data.get("last_prompt") or {}
        body = lp.get("body", "")
        options = [tuple(o) for o in lp.get("options", [])]
        prefix = texts.INVALID_TEXT if text_state else texts.INVALID
        text = f"{prefix}\n\n{body}" if body else prefix
        if n >= 3:
            text += texts.INVALID_HINT
        self.outbox.append(Out(text, options))
        self.set(invalid=n, options=[o[0] for o in options])


Handler = Callable[[Ctx], Awaitable[None]]
HANDLERS: dict[str, Handler] = {}


def handler(state: str):
    def deco(fn: Handler) -> Handler:
        HANDLERS[state] = fn
        return fn
    return deco
