from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config.settings import Settings


def make_session_factory(settings: Settings) -> async_sessionmaker[AsyncSession]:
    url = settings.async_database_url
    kwargs: dict = {}
    if url.startswith("postgresql+asyncpg"):
        # Pooler do Supabase (pgbouncer, modo transaction): sem prepared statements.
        kwargs["connect_args"] = {"statement_cache_size": 0, "prepared_statement_cache_size": 0}
        kwargs["poolclass"] = NullPool
    elif url.startswith("sqlite"):
        kwargs["poolclass"] = NullPool
    engine = create_async_engine(url, **kwargs)
    return async_sessionmaker(engine, expire_on_commit=False)
