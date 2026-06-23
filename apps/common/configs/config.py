"""YAML 기반 앱 설정 로더."""

from collections.abc import Mapping
import os
from pathlib import Path
import re
from typing import Any

import yaml
from pydantic import Field, computed_field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)


ROOT_DIR = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG_FILE = ROOT_DIR / "envs" / "config.yaml"
CONFIG_FILE_PATH = Path(os.getenv("APP_CONFIG", str(DEFAULT_CONFIG_FILE))).expanduser()


class EnvYamlConfigSettingsSource(YamlConfigSettingsSource):
    """`${ENV_NAME}` 패턴을 YAML 읽기 전에 환경변수로 치환."""

    def _read_file(self, file_path: Path) -> dict[str, Any]:
        with open(file_path, encoding=self.yaml_file_encoding) as yaml_file:
            yaml_str = yaml_file.read()
            env_pattern = re.compile(r".*?\${(\w+)}.*?")
            for env_name in env_pattern.findall(yaml_str):
                yaml_str = yaml_str.replace(
                    f"${{{env_name}}}",
                    os.environ.get(env_name, f"${{{env_name}}}"),
                )
            loaded = yaml.safe_load(yaml_str)
        return loaded if isinstance(loaded, dict) else {}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="",
        env_nested_delimiter="__",
        yaml_file=str(CONFIG_FILE_PATH),
        case_sensitive=False,
        extra="ignore",
        env_parse_none_str="null",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            file_secret_settings,
            EnvYamlConfigSettingsSource(settings_cls),
        )

    # DB
    METADATA_DB_TYPE: str
    METADATA_DB_HOST: str
    METADATA_DB_PORT: int
    METADATA_DB_NAME: str
    METADATA_DB_USERNAME: str
    METADATA_DB_PASSWORD: str

    DB_CONNECTION_TIMEOUT_SECONDS: int = Field(default=10)
    READ_TIMEOUT_SECONDS: int = Field(default=30)
    IS_DB_ECHO_LOG: bool = Field(default=False)
    DB_POOL_SIZE: int = Field(default=5)
    DB_POOL_OVERFLOW: int = Field(default=10)
    DB_POOL_TIMEOUT_SECONDS: int = Field(default=30)
    POOL_RECYCLE_SECONDS: int = Field(default=1800)
    POOL_PRE_PING: bool = Field(default=True)
    IS_DB_EXPIRE_ON_COMMIT: bool = Field(default=False)

    # A.X Platform
    ai_platform_host_url: str
    api_key: str

    # MODEL
    model_endpoint: str
    model_api_key: str
    model_api_deployment_name: str
    lightly_thinking_model_api_deployment_name: str
    deeply_thinking_model_api_deployment_name: str

    # HTTP
    http_timeout: float
    http_connect_timeout: float
    http_verify: bool
    http2: bool
    http_max_connection: int
    http_max_keepalive: int
    http_request_max_retries: int = Field(default=3)
    http_retry_backoff_base: float = Field(default=1.0)

    # VDB
    # LLM
    llm_concurrency: int
    llm_timeout_sec: float = Field(default=90.0)

    http_max_concurrency: int

    # Scenario group admin/test APIs
    scenario_group_admin_bearer_tokens: list[str] = Field(default_factory=list)

    # Callback OAuth2 (client_credentials)
    callback_oauth2_token_url: str = Field(default="")
    callback_oauth2_client_id: str = Field(default="")
    callback_oauth2_client_secret: str = Field(default="")

    # Callback 엔드포인트 (base_url + path 조합)
    callback_base_url: str = Field(default="")
    callback_create_scenarios_path: str = Field(default="")
    callback_validate_scenarios_path: str = Field(default="")
    callback_create_signposts_path: str = Field(default="")
    skip_callback: bool = Field(default=False)

    # STREAMING
    streaming_mode: list[str] = Field(default_factory=lambda: ["custom"])

    mcp_database_base: str = "mimcp://database"

    @computed_field
    @property
    def mcp_metadata_uri(self) -> str:
        return self.mcp_database_base + "/metas"

    @computed_field
    @property
    def mcp_table_schema_uri(self) -> str:
        return self.mcp_database_base + "/schemas/midb/tables"

    @computed_field
    @property
    def mcp_table_codes_uri(self) -> str:
        return self.mcp_database_base + "/metas/codes"

    # Swagger
    title: str = "Query Knowledge Base Builder"
    version: str = "v0.0.1"
    time_zone: str = "Asia/Seoul"
    openapi_version: str = "/v1"
    openapi_prefix: str = "/api" + openapi_version
    openapi_doc_url: str = openapi_prefix + "/openapi.json"
    openapi_doc_description: str = "skmip-query-pilot App의 REST API는 다음의 OpenAPI Spec을 따른다."
    openapi_docs_url: str = openapi_prefix + "/docs"
    openapi_redoc_url: str = openapi_prefix + "/redoc"
    openapi_metadata_hub_path: str = openapi_prefix + "/metadata_hub"
    openapi_curation_path: str = openapi_metadata_hub_path + "/curation"

    # LOG
    log_level: str
    debug: bool = Field(default=False)

    @property
    def set_backend_app_attributes(self) -> Mapping[str, Any]:
        return {
            "title": self.title,
            "version": self.version,
            "debug": self.debug,
            "description": self.openapi_doc_description,
            "docs_url": self.openapi_docs_url,
            "openapi_url": self.openapi_doc_url,
            "redoc_url": self.openapi_redoc_url,
        }


def get_settings() -> Settings:
    return Settings()


settings: Settings = get_settings()
