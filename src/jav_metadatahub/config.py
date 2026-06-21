from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    log_level: str = "INFO"

    database_url: str = "postgresql+psycopg://javhub:javhub@localhost:5432/javhub"

    fanza_base_url: str = "https://api.dmm.com/affiliate/v3"
    fanza_api_id: str = Field(default="", repr=False)
    fanza_affiliate_id: str = Field(default="", repr=False)

    collector_default_rate_limit_per_second: float = 1.0
    collector_max_retries: int = 3
    collector_timeout_seconds: float = 30.0

    export_dir: Path = Path("./exports")

    api_host: str = "0.0.0.0"
    api_port: int = 8000


@lru_cache
def get_settings() -> Settings:
    return Settings()
