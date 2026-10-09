from functools import lru_cache
from typing import Annotated, Any, Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    environment: Literal["local", "dev", "staging", "prod"] = "local"
    log_level: str = "INFO"

    # Async URL (asyncpg) for the app; sync URL (psycopg) for Alembic. Same DB,
    # different drivers. Local defaults match docker-compose.
    database_url: str = "postgresql+asyncpg://tasca:tasca@localhost:5432/tasca"
    sync_database_url: str = "postgresql+psycopg://tasca:tasca@localhost:5432/tasca"

    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors_origins(cls, v: Any) -> Any:
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
