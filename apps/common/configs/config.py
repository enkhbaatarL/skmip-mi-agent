"""YAML 기반 앱 설정 로더."""

from collections.abc import Mapping
import json
import os
from pathlib import Path
import re
from typing import Any
from uuid import UUID

import yaml
from pydantic import Field, computed_field, field_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)


ROOT_DIR = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG_FILE = ROOT_DIR / "config.yaml"
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

    # MCP
    mcp_pool_urls: dict[str, str] = Field(default_factory=dict, alias="MCP_POOL_URLS")
    company_mcp_map: dict[str, str] = Field(
        default_factory=dict,
        alias="COMPANY_MCP_MAP",
    )
    mcp_pool_size: int
    mcp_per_session_limit: int
    mcp_client_timeout: float
    mcp_client_sse_read_timeout: float

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
    vdb_document_repo_ids_by_provider: dict[str, dict[str, str]] = Field(
        default_factory=dict,
        alias="DOCUMENT_SEARCH_REPOS_BY_PROVIDER",
        description="content_provider -> {meta_repo_id, chunk_repo_id} mapping",
    )
    rdb_search_metadata_repo_id: UUID

    # LLM
    llm_concurrency: int
    llm_timeout_sec: float = Field(default=90.0)
    analyze_records_max_parallel: int = Field(default=4, alias="MAX_PARALLEL_REQUESTS")

    # WEB
    bing_endpoint: str = Field(default="")
    bing_api_key: str = Field(default="")
    web_search_provider: str = Field(default="tavily")

    # Tavily Search Provider
    tavily_api_key: str = Field(default="")
    tavily_search_depth: str = Field(default="advanced")
    tavily_max_results: int = Field(default=5)
    tavily_include_domains: list[str] = Field(default_factory=list)
    tavily_exclude_domains: list[str] = Field(default_factory=list)
    tavily_score_threshold: float = Field(default=0.5)

    # CONCURRENCY
    mcp_max_concurrency: int
    http_max_concurrency: int
    rdb_exec_max_parallel: int
    web_search_max_concurrent: int = Field(default=5)

    # SEARCH
    search_sources: list[str] = Field(default_factory=lambda: ["web", "rdb", "vdb"])
    search_exec_fanout_deadline_sec: float = Field(default=240.0)
    search_strict_required: bool = Field(default=True)

    # Scenario group admin/test APIs
    scenario_group_admin_bearer_tokens: list[str] = Field(default_factory=list)

    @field_validator("search_sources", mode="before")
    @classmethod
    def parse_search_sources(cls, v: Any) -> list[str]:
        """Allow JSON or comma-delimited strings for env overrides."""
        if isinstance(v, list):
            return v
        if v is None:
            return []
        if isinstance(v, str):
            raw = v.strip().strip("'\"")
            if raw.startswith("["):
                return json.loads(raw)
            return [x.strip() for x in raw.split(",") if x.strip()]
        return list(v)

    search_rdb_exec_timeout_sec: float = 240.0
    search_vdb_exec_timeout_sec: float = 240.0
    search_web_exec_timeout_sec: float = 240.0

    # STREAMING
    streaming_mode: list[str] = Field(default_factory=lambda: ["custom"])

    # MCP
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
