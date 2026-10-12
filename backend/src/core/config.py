from functools import lru_cache
from typing import Annotated, Any, Literal

from pydantic import Field, field_validator
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

    # Single admin account, configured here rather than in the DB. Generate the
    # hash with `PYTHONPATH=src uv run python -m core.hash_password`.
    admin_username: str = "admin"
    admin_password_hash: str = Field(min_length=1)

    jwt_secret_key: str = Field(min_length=32)  # e.g. `openssl rand -hex 32`
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 12 * 60  # one working day

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors_origins(cls, v: Any) -> Any:
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]  # required fields come from the environment
