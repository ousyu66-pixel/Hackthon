from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Sentinel-X"
    app_version: str = "0.1.0-phase1"
    knowledge_dir: Path = Field(default=Path("sentinel_x/knowledge"))
    audit_log_path: Path = Field(default=Path("sentinel_x/logs/incidents.json"))
    confidence_threshold: float = 0.85

    model_config = SettingsConfigDict(env_prefix="SENTINEL_X_")


@lru_cache
def get_settings() -> Settings:
    return Settings()
