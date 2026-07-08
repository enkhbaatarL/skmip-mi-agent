"""YAML 기반 앱 설정 로더."""

from collections.abc import Mapping
import os
from pathlib import Path
import re
from typing import Any

from pydantic import BaseModel, Field, computed_field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)
import yaml


ROOT_DIR = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG_FILE = ROOT_DIR / "envs" / "config.yaml"
CONFIG_FILE_PATH = Path(os.getenv("APP_CONFIG", str(DEFAULT_CONFIG_FILE))).expanduser()
ENV_PLACEHOLDER_PATTERN = re.compile(r"\${(\w+)}")
ESCAPED_LINE_BREAK_PATTERN = re.compile(r"\\r\\n|\\n|\\r")


def _normalize_yaml_text(yaml_str: str) -> str:
    """Normalize real line breaks and single-line escaped ConfigMap blobs."""
    normalized = yaml_str.replace("\r\n", "\n").replace("\r", "\n")
    if "\n" not in normalized.strip():
        # A single-line escaped blob means the ConfigMap stored YAML line breaks
        # as text. Treat every escaped line break as a structural separator.
        normalized = ESCAPED_LINE_BREAK_PATTERN.sub("\n", normalized)
    return normalized


def _replace_env_placeholders(yaml_str: str) -> str:
    """Replace `${ENV_NAME}` placeholders with environment values when present."""
    for env_name in ENV_PLACEHOLDER_PATTERN.findall(yaml_str):
        yaml_str = yaml_str.replace(
            f"${{{env_name}}}",
            os.environ.get(env_name, f"${{{env_name}}}"),
        )
    return yaml_str


class EnvYamlConfigSettingsSource(YamlConfigSettingsSource):
    """`${ENV_NAME}` 패턴을 YAML 읽기 전에 환경변수로 치환."""

    def _read_file(self, file_path: Path) -> dict[str, Any]:
        with file_path.open(encoding=self.yaml_file_encoding) as yaml_file:
            yaml_str = _replace_env_placeholders(_normalize_yaml_text(yaml_file.read()))
            loaded = yaml.safe_load(yaml_str)
        return loaded if isinstance(loaded, dict) else {}


class AgentConfig(BaseModel):
    mlflow_experiment_name: str = Field(default="mi_agent_local")
    aip_app_id: str = Field(default="mi_agent")
    mlflow_tracing_enabled: bool = Field(default=False)


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
    create_signposts_max_concurrent_scenarios: int = Field(default=7, ge=1)

    # Agent profiles
    agents: dict[str, AgentConfig] = Field(default_factory=lambda: {"default": AgentConfig()})

    # MLflow tracing defaults and legacy fallback
    mlflow_tracing_enabled: bool = Field(default=False)
    mlflow_tracking_uri: str = Field(default="http://mlflow:5000")
    mlflow_experiment_name: dict[str, str] = Field(default_factory=lambda: {"main.py": "scenario_agent"})
    mlflow_tracking_username: str = Field(default="")
    mlflow_tracking_password: str = Field(default="")
    mlflow_langchain_run_tracer_inline: bool = Field(
        default=False,
        description=(
            "false(기본): trace를 백그라운드에 기록해 응답이 느려지지 않게 합니다. "
            "true: 요청 처리 중 바로 trace를 기록합니다."
        ),
    )

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

    def get_agent_config(self, agent_name: str | None = None) -> AgentConfig:
        if agent_name and agent_name in self.agents:
            return self.agents[agent_name]
        if "default" in self.agents:
            return self.agents["default"]

        experiment_name = (
            self.mlflow_experiment_name.get(agent_name or "")
            or self.mlflow_experiment_name.get("default")
            or self.mlflow_experiment_name.get("main.py")
            or "mi_agent_local"
        )
        legacy_aip_app_ids = {"scenario_group_agent": "scenario-group-agent"}
        return AgentConfig(
            mlflow_experiment_name=experiment_name,
            aip_app_id=legacy_aip_app_ids.get(agent_name or "", agent_name or "mi_agent"),
            mlflow_tracing_enabled=self.mlflow_tracing_enabled,
        )

    def is_mlflow_tracing_enabled(
        self,
        *,
        agent_name: str | None = None,
    ) -> bool:
        return self.get_agent_config(agent_name).mlflow_tracing_enabled

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
