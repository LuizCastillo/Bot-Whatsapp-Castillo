from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config.settings import Settings
from app.services.storage import SupabaseStorage
from app.services.whatsapp.client import WhatsAppClient


@dataclass
class Deps:
    settings: Settings
    session_factory: async_sessionmaker[AsyncSession]
    wa: Any
    storage: Any


def build_deps(settings: Settings, session_factory) -> Deps:
    return Deps(
        settings=settings,
        session_factory=session_factory,
        wa=WhatsAppClient(settings.whatsapp_token.get_secret_value(), settings.whatsapp_phone_number_id,
                          settings.whatsapp_api_version),
        storage=SupabaseStorage(settings.supabase_url, settings.supabase_service_role_key.get_secret_value(),
                                settings.supabase_storage_bucket),
    )
