from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

APP_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=APP_ROOT / ".env", env_prefix="", extra="ignore")

    database_url: str = "mysql+pymysql://poc:poc@mysql:3306/poc_model_parameter?charset=utf8mb4"
    agent_mode: str = "mock_deterministic"
    seed_path: Path = APP_ROOT / "sample_scenario_group.json"
    max_scenario_payload_bytes: int = 1_048_576
    worker_poll_interval_seconds: float = 5.0
    worker_batch_size: int = 20
    worker_max_attempts: int = 3
    worker_retry_max_seconds: int = 30
    api_cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    @property
    def payload_limit_bytes(self) -> int:
        return self.max_scenario_payload_bytes

    @property
    def worker_poll_seconds(self) -> float:
        return self.worker_poll_interval_seconds

    @property
    def cors_origins(self) -> list[str]:
        return self.api_cors_origins


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
