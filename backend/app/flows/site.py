import re

from app.database.models import Servico
from app.flows.base import norm

_REF = re.compile(r"\(ref:\s*([a-z0-9\-]+)\)", re.I)


def detect_site_service(text: str | None, servicos: list[Servico]) -> Servico | None:
    """Identifica o serviço enviado pelo site: primeiro pelo slug estável, depois pelo nome."""
    if not text:
        return None
    m = _REF.search(text)
    if m:
        slug = m.group(1).lower()
        return next((s for s in servicos if s.slug == slug), None)
    t = norm(text)
    if "vim pelo site" in t:
        # nomes mais longos primeiro (ex.: "pintura localizada" antes de "pintura")
        for s in sorted(servicos, key=lambda s: -len(s.nome)):
            base = norm(s.nome.split("/")[0])
            if base in t:
                return s
    return None
