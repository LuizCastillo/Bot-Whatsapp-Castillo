from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.panel.deps import current_user, db, require_admin
from app.database.models import Servico
from app.schemas.panel import ServicoUpdate

router = APIRouter(tags=["painel:servicos"], dependencies=[Depends(current_user)])


def _out(s: Servico) -> dict:
    return {"id": s.id, "slug": s.slug, "nome": s.nome, "descricao": s.descricao, "ativo": s.ativo, "ordem": s.ordem}


@router.get("/servicos")
async def list_servicos(session: AsyncSession = Depends(db)):
    return {"items": [_out(s) for s in (await session.scalars(select(Servico).order_by(Servico.ordem))).all()]}


@router.patch("/servicos/{servico_id}", dependencies=[Depends(require_admin)])
async def update_servico(servico_id: int, body: ServicoUpdate, session: AsyncSession = Depends(db)):
    s = await session.get(Servico, servico_id)
    if not s:
        raise HTTPException(404, "Serviço não encontrado.")
    for k, v in body.model_dump(exclude_unset=True).items():
        if v is not None:
            setattr(s, k, v)
    return _out(s)
