from fastapi import APIRouter, Depends

from app.api.panel import agenda, auth, avaliacoes, clientes, conversas, dashboard, equipe, servicos
from app.api.panel.deps import require_proxy

router = APIRouter(prefix="/panel", dependencies=[Depends(require_proxy)])
for module in (auth, dashboard, clientes, agenda, conversas, avaliacoes, servicos, equipe):
    router.include_router(module.router)
