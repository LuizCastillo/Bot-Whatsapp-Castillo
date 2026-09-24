from functools import lru_cache

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def to_async_url(url: str) -> str:
    """Converte a URL do Supabase/Postgres para o driver asyncpg."""
    for prefix in ("postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+asyncpg://" + url[len(prefix):]
    return url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"
    timezone: str = "America/Sao_Paulo"
    cors_origins: str = ""
    proxy_shared_secret: SecretStr
    session_expire_minutes: int = 480

    database_url: str
    supabase_url: str = ""
    supabase_service_role_key: SecretStr = SecretStr("")
    supabase_storage_bucket: str = "fotos-avaliacoes"

    whatsapp_token: SecretStr
    whatsapp_phone_number_id: str
    whatsapp_verify_token: SecretStr
    whatsapp_api_version: str = "v21.0"
    meta_app_secret: SecretStr

    nome_oficina: str = "Oficina Castillo"
    endereco_oficina: str = ""
    conversa_timeout_horas: int = 12
    agendamento_status_inicial: str = "PENDENTE"
    cancelamento_antecedencia_horas: int = 2
    max_foto_mb: int = 10

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def async_database_url(self) -> str:
        return to_async_url(self.database_url)

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip().rstrip("/") for o in self.cors_origins.split(",") if o.strip()]

    @model_validator(mode="after")
    def _validate(self) -> "Settings":
        origins = self.cors_origin_list
        if "*" in origins:
            raise ValueError("CORS_ORIGINS não pode conter '*'.")
        if self.is_production and not origins:
            raise ValueError("Defina CORS_ORIGINS em produção.")
        if self.agendamento_status_inicial not in ("PENDENTE", "CONFIRMADO"):
            raise ValueError("AGENDAMENTO_STATUS_INICIAL deve ser PENDENTE ou CONFIRMADO.")
        if len(self.proxy_shared_secret.get_secret_value()) < 16 and self.is_production:
            raise ValueError("PROXY_SHARED_SECRET muito curto.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
