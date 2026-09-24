from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.panel.deps import current_user, db
from app.api.panel.serializers import agendamentos_query, cliente_out, iso, veiculo_out
from app.database.models import Agendamento, Avaliacao, Cliente, Conversa, Veiculo
from app.schemas.panel import ClienteUpdate, VeiculoIn, VeiculoUpdate
from app.services.vehicles import normalize_plate

router = APIRouter(tags=["painel:clientes"], dependencies=[Depends(current_user)])


def _plate(raw: str | None) -> str | None:
    if not raw:
        return None
    p = normalize_plate(raw)
    if not p:
        raise HTTPException(422, "Placa inválida (use ABC1234 ou ABC1D23).")
    return p


@router.get("/clientes")
async def list_clientes(q: str | None = None, limit: int = Query(30, ge=1, le=100), offset: int = Query(0, ge=0),
                        session: AsyncSession = Depends(db)):
    cond = []
    if q and q.strip():
        term = f"%{q.strip()}%"
        digits = "".join(ch for ch in q if ch.isdigit())
        cond.append(or_(Cliente.nome.ilike(term), *( [Cliente.telefone.like(f"%{digits}%")] if digits else [] ),
                        Cliente.id.in_(select(Veiculo.cliente_id).where(Veiculo.placa.ilike(term)))))
    total = await session.scalar(select(func.count(Cliente.id)).where(*cond))
    rows = (await session.scalars(select(Cliente).where(*cond).order_by(Cliente.criado_em.desc()).limit(limit).offset(offset))).all()
    return {"total": total or 0, "items": [cliente_out(c) for c in rows]}


@router.get("/clientes/{cliente_id}")
async def get_cliente(cliente_id: int, session: AsyncSession = Depends(db)):
    c = await session.get(Cliente, cliente_id)
    if not c:
        raise HTTPException(404, "Cliente não encontrado.")
    vs = (await session.scalars(select(Veiculo).where(Veiculo.cliente_id == c.id).order_by(Veiculo.id))).all()
    from app.api.panel.serializers import agendamento_out
    rows = (await session.execute(agendamentos_query().where(Avaliacao.cliente_id == c.id).order_by(Agendamento.data_hora_inicio.desc()))).all()
    conv = (await session.scalars(select(Conversa).where(Conversa.cliente_id == c.id).order_by(Conversa.id.desc()).limit(20))).all()
    return {
        **cliente_out(c),
        "veiculos": [veiculo_out(v) for v in vs],
        "agendamentos": [agendamento_out(*r) for r in rows],
        "conversas": [{"id": x.id, "modo": x.modo.value, "origem": x.origem.value, "estado": x.estado_atual, "atualizado_em": iso(x.atualizado_em)} for x in conv],
    }


@router.patch("/clientes/{cliente_id}")
async def update_cliente(cliente_id: int, body: ClienteUpdate, session: AsyncSession = Depends(db)):
    c = await session.get(Cliente, cliente_id)
    if not c:
        raise HTTPException(404, "Cliente não encontrado.")
    c.nome = body.nome.strip()
    return cliente_out(c)


@router.post("/clientes/{cliente_id}/veiculos", status_code=201)
async def add_veiculo(cliente_id: int, body: VeiculoIn, session: AsyncSession = Depends(db)):
    if not await session.get(Cliente, cliente_id):
        raise HTTPException(404, "Cliente não encontrado.")
    v = Veiculo(cliente_id=cliente_id, marca=body.marca.strip().title(), modelo=body.modelo.strip().title(), ano=body.ano, placa=_plate(body.placa))
    try:
        async with session.begin_nested():
            session.add(v)
            await session.flush()
    except IntegrityError:
        raise HTTPException(409, "Este cliente já tem um veículo com essa placa.")
    return veiculo_out(v)


@router.patch("/veiculos/{veiculo_id}")
async def update_veiculo(veiculo_id: int, body: VeiculoUpdate, session: AsyncSession = Depends(db)):
    v = await session.get(Veiculo, veiculo_id)
    if not v:
        raise HTTPException(404, "Veículo não encontrado.")
    data = body.model_dump(exclude_unset=True)
    if "placa" in data:
        data["placa"] = _plate(data["placa"])
    for k, val in data.items():
        setattr(v, k, val)
    try:
        async with session.begin_nested():
            await session.flush()
    except IntegrityError:
        raise HTTPException(409, "Este cliente já tem um veículo com essa placa.")
    return veiculo_out(v)


@router.delete("/veiculos/{veiculo_id}", status_code=204)
async def delete_veiculo(veiculo_id: int, session: AsyncSession = Depends(db)):
    v = await session.get(Veiculo, veiculo_id)
    if not v:
        raise HTTPException(404, "Veículo não encontrado.")
    await session.delete(v)
