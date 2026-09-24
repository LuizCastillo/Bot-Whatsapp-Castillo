from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.panel.deps import db, require_admin
from app.api.panel.serializers import iso
from app.database.enums import Papel
from app.database.models import Atendente
from app.schemas.panel import AtendenteCreate, AtendenteUpdate
from app.services import auth

router = APIRouter(prefix="/equipe", tags=["painel:equipe"])


def _out(a: Atendente) -> dict:
    return {"id": a.id, "nome": a.nome, "email": a.email, "papel": a.papel.value, "ativo": a.ativo, "criado_em": iso(a.criado_em)}


@router.get("")
async def list_equipe(session: AsyncSession = Depends(db), _=Depends(require_admin)):
    return {"items": [_out(a) for a in (await session.scalars(select(Atendente).order_by(Atendente.nome))).all()]}


@router.post("", status_code=201)
async def create_atendente(body: AtendenteCreate, session: AsyncSession = Depends(db), _=Depends(require_admin)):
    a = Atendente(nome=body.nome.strip(), email=body.email.lower(), senha_hash=auth.hash_password(body.senha), papel=body.papel)
    try:
        async with session.begin_nested():
            session.add(a)
            await session.flush()
    except IntegrityError:
        raise HTTPException(409, "Já existe um usuário com esse e-mail.")
    return _out(a)


@router.patch("/{atendente_id}")
async def update_atendente(atendente_id: int, body: AtendenteUpdate, session: AsyncSession = Depends(db), me: Atendente = Depends(require_admin)):
    a = await session.get(Atendente, atendente_id)
    if not a:
        raise HTTPException(404, "Usuário não encontrado.")
    data = body.model_dump(exclude_unset=True)
    if a.id == me.id and (data.get("ativo") is False or data.get("papel") == Papel.ATENDENTE):
        raise HTTPException(409, "Você não pode desativar ou rebaixar a si mesmo.")
    if "senha" in data and data["senha"]:
        a.senha_hash = auth.hash_password(data.pop("senha"))
        await auth.revoke_all(session, a.id)
    data.pop("senha", None)
    if data.get("ativo") is False:
        await auth.revoke_all(session, a.id)
    for k, v in data.items():
        if v is not None:
            setattr(a, k, v)
    return _out(a)
