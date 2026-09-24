from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.panel.deps import client_ip, current_session, current_user, db
from app.config.settings import Settings, get_settings
from app.schemas.panel import LoginIn
from app.services import auth

router = APIRouter(prefix="/auth", tags=["painel:auth"])


def _user(u) -> dict:
    return {"id": u.id, "nome": u.nome, "email": u.email, "papel": u.papel.value}


@router.post("/login")
async def login(body: LoginIn, request: Request, session: AsyncSession = Depends(db), settings: Settings = Depends(get_settings)):
    ip = client_ip(request) or "?"
    keys = (f"ip:{ip}", f"email:{body.email.lower()}")
    if auth.limiter.blocked(*keys):
        raise HTTPException(status_code=429, detail="Muitas tentativas. Aguarde alguns minutos.")
    result = await auth.login(session, body.email, body.senha, ip, settings.session_expire_minutes)
    if not result:
        auth.limiter.fail(*keys)
        raise HTTPException(status_code=401, detail="E-mail ou senha inválidos.")
    auth.limiter.reset(*keys)
    token, sess, user = result
    # O token vai apenas ao proxy do Next.js, que o guarda em cookie HttpOnly.
    return {"token": token, "expira_em": sess.expira_em.isoformat(), "usuario": _user(user)}


@router.post("/logout", status_code=204)
async def logout(found=Depends(current_session)):
    found[1].revogada = True


@router.get("/me")
async def me(user=Depends(current_user)):
    return _user(user)
