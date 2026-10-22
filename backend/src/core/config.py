from functools import lru_cache
from typing import Annotated, Any, Literal

from argon2 import extract_parameters
from argon2.exceptions import InvalidHashError
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        # Never echo values in validation errors: they may be secrets (or a password
        # pasted into ADMIN_PASSWORD_HASH by mistake) and would end up in logs.
        hide_input_in_errors=True,
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

    # Shared secret the voice agent (ElevenLabs) sends in the X-Agent-Secret header.
    # Optional so the app still starts without it; while unset, every /agent route
    # answers 401. Generate with `openssl rand -hex 32`.
    agent_api_secret: str | None = Field(default=None, min_length=32)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors_origins(cls, v: Any) -> Any:
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @field_validator("admin_password_hash")
    @classmethod
    def _check_argon2_hash(cls, v: str) -> str:
        # Fail at startup rather than with a 500 on every login. The usual cause is
        # pasting the hash into .env without single quotes, which mangles the `$`s.
        try:
            extract_parameters(v)
        except InvalidHashError:
            raise ValueError(
                "ADMIN_PASSWORD_HASH is not a valid argon2 hash. Generate one with "
                "`PYTHONPATH=src uv run python -m core.hash_password` and keep it in "
                "single quotes in .env."
            ) from None
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]  # required fields come from the environment
