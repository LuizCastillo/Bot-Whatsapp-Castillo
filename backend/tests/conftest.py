import os
import tempfile
from datetime import datetime, timezone

import pytest
from alembic import command
from alembic.config import Config

_TMP = tempfile.mkdtemp()
os.environ.update(
    APP_ENV="development",
    CORS_ORIGINS="http://localhost:3000",
    PROXY_SHARED_SECRET="proxy-secret-for-tests",
    DATABASE_URL=f"sqlite+aiosqlite:///{_TMP}/boot.db",
    WHATSAPP_TOKEN="test-token",
    WHATSAPP_PHONE_NUMBER_ID="123",
    WHATSAPP_VERIFY_TOKEN="verify-me",
    META_APP_SECRET="app-secret",
    ENDERECO_OFICINA="Rua Teste, 100",
)

from app.config.settings import get_settings  # noqa: E402
from app.database.session import make_session_factory  # noqa: E402
from app.main import create_app  # noqa: E402
from app.services.deps import Deps  # noqa: E402
from app.services.storage import InMemoryStorage  # noqa: E402

# Segunda-feira, 09:00 no horário de Brasília: há horários comerciais disponíveis logo em seguida.
FIXED_NOW = datetime(2026, 9, 28, 12, 0, tzinfo=timezone.utc)


class FakeWA:
    def __init__(self):
        self.sent: list = []
        self.media: dict[str, tuple[bytes, str]] = {"m1": (b"\xff\xd8fake-jpeg", "image/jpeg")}

    async def send(self, to, out):
        self.sent.append((to, out))

    async def download_media(self, media_id):
        return self.media[media_id]


@pytest.fixture
def session_factory(tmp_path):
    """Banco SQLite temporário criado pelas migrations reais (testa também o seed)."""
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{tmp_path}/test.db"
    base = os.path.join(os.path.dirname(__file__), "..")
    cfg = Config(os.path.join(base, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(base, "migrations"))
    command.upgrade(cfg, "head")
    get_settings.cache_clear()
    return make_session_factory(get_settings())


@pytest.fixture
def deps(session_factory):
    return Deps(settings=get_settings(), session_factory=session_factory, wa=FakeWA(), storage=InMemoryStorage())


@pytest.fixture
def app(session_factory, deps):
    application = create_app()
    application.state.session_factory = session_factory
    application.state.deps = deps
    return application


@pytest.fixture
def client(app):
    from fastapi.testclient import TestClient
    return TestClient(app)
