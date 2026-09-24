import hashlib
import secrets
import time
from datetime import timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Atendente, Sessao
from app.utils.timezone import utcnow

_ph = PasswordHasher()
_DUMMY = _ph.hash("senha-inexistente-para-tempo-constante")
MIN_PASSWORD = 10


def hash_password(p: str) -> str:
    return _ph.hash(p)


def verify_password(hashed: str, p: str) -> bool:
    try:
        return _ph.verify(hashed, p)
    except (VerifyMismatchError, InvalidHashError):
        return False


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class LoginLimiter:
    """Limite simples em memória (1 instância). 5 falhas por IP/e-mail em 15 min."""

    def __init__(self, max_fail: int = 5, window: int = 900):
        self.max_fail, self.window, self._fails = max_fail, window, {}

    def _prune(self, key: str) -> list[float]:
        now = time.monotonic()
        self._fails[key] = [t for t in self._fails.get(key, []) if now - t < self.window]
        return self._fails[key]

    def blocked(self, *keys: str) -> bool:
        return any(len(self._prune(k)) >= self.max_fail for k in keys)

    def fail(self, *keys: str) -> None:
        for k in keys:
            self._prune(k).append(time.monotonic())

    def reset(self, *keys: str) -> None:
        for k in keys:
            self._fails.pop(k, None)


limiter = LoginLimiter()


async def login(session: AsyncSession, email: str, senha: str, ip: str | None, expire_minutes: int) -> tuple[str, Sessao, Atendente] | None:
    user = await session.scalar(select(Atendente).where(Atendente.email == email.lower().strip()))
    ok = verify_password(user.senha_hash if user else _DUMMY, senha)  # tempo constante
    if not user or not ok or not user.ativo:
        return None
    token = secrets.token_urlsafe(32)
    now = utcnow()
    sess = Sessao(atendente_id=user.id, token_hash=_digest(token), expira_em=now + timedelta(minutes=expire_minutes), ultimo_uso=now, ip=ip)
    session.add(sess)
    await session.flush()
    return token, sess, user


async def user_from_token(session: AsyncSession, token: str) -> tuple[Atendente, Sessao] | None:
    sess = await session.scalar(select(Sessao).where(Sessao.token_hash == _digest(token)))
    if not sess or sess.revogada or sess.expira_em <= utcnow():
        return None
    user = await session.get(Atendente, sess.atendente_id)
    if not user or not user.ativo:
        return None
    sess.ultimo_uso = utcnow()
    return user, sess


async def revoke_all(session: AsyncSession, atendente_id: int) -> None:
    await session.execute(update(Sessao).where(Sessao.atendente_id == atendente_id).values(revogada=True))
