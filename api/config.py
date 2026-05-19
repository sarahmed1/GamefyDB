from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="GAMEFYDB_", extra="ignore")

    secret: str = "dev-secret-change-me"
    database_url: str = "sqlite+aiosqlite:///./api/gamefydb.sqlite"
    cookie_name: str = "gamefydb_session"
    cookie_max_age: int = 60 * 60 * 24  # 24h
    cookie_secure: bool = False
    cors_origins: list[str] = ["http://localhost:5173"]
    excel_dir: str = str(Path(__file__).resolve().parents[1] / "excel")


@lru_cache
def get_settings() -> Settings:
    return Settings()
