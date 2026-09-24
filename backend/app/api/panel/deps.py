import hmac
from collections.abc import AsyncIterator

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings, get_settings
from app.database.enums import Papel
from app.database.models import Atendente, Sessao
from app.services import auth


def require_proxy(request: Request, x_proxy_secret: str | None = Header(default=None),
                  settings: Settings = Depends(get_settings)) -> None:
    """O painel só aceita chamadas vindas do proxy do Next.js (segredo compartilhado)."""
    expected = settings.proxy_shared_secret.get_secret_value()
    if not x_proxy_secret or not hmac.compare_digest(x_proxy_secret, expected):
        raise HTTPException(status_code=403, detail="Origem não autorizada.")


async def db(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.session_factory() as session:
        try:
            yield session
            await session.commit()
        except BaseException:
            await session.rollback()
            raise


def client_ip(request: Request) -> str | None:
    # Só confiável porque require_proxy já validou o segredo do proxy.
    return request.headers.get("x-client-ip") or (request.client.host if request.client else None)


async def current_session(authorization: str | None = Header(default=None), session: AsyncSession = Depends(db)) -> tuple[Atendente, Sessao]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Não autenticado.")
    found = await auth.user_from_token(session, authorization[7:].strip())
    if not found:
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada.")
    return found


async def current_user(found=Depends(current_session)) -> Atendente:
    return found[0]


async def require_admin(user: Atendente = Depends(current_user)) -> Atendente:
    if user.papel != Papel.ADMIN:
        raise HTTPException(status_code=403, detail="Apenas administradores.")
    return user
