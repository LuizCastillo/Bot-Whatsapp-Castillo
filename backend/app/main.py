from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health.router import router as health_router
from app.api.panel.router import router as panel_router
from app.api.webhook.router import router as webhook_router
from app.config.settings import get_settings
from app.database.session import make_session_factory
from app.services.deps import build_deps
from app.utils.logging import configure_logging


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    session_factory = make_session_factory(settings)
    deps = build_deps(settings, session_factory)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        for c in (deps.wa, deps.storage):
            close = getattr(c, "aclose", None)
            if close:
                await close()
        await session_factory.kw["bind"].dispose()

    app = FastAPI(
        title="Bot WhatsApp — Oficina Castillo",
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None,
        openapi_url=None if settings.is_production else "/openapi.json",
        lifespan=lifespan,
    )
    app.state.deps = deps
    app.state.session_factory = session_factory

    # O navegador nunca chama esta API diretamente (proxy do Next.js): CORS é só segunda camada.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.include_router(health_router)
    app.include_router(webhook_router)
    app.include_router(panel_router)
    return app


app = create_app()
