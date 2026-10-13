# Copyright (c) 2026 SK Innovation E&S.

from __future__ import annotations

# YAML 기반 앱 설정 로더.
from collections.abc import Mapping
from functools import lru_cache
import json
import os
from pathlib import Path
import re
from typing import Annotated, Any, Literal

from pydantic import AliasChoices, BaseModel, Field, SecretStr, field_validator, model_validator
from pydantic_settings import (
    BaseSettings,
    NoDecode,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)
import yaml

from apps.common.utils.yaml_utils import normalize_yaml_text


ROOT_DIR = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG_FILE = ROOT_DIR / "envs" / "config.yaml"
CONFIG_FILE_PATH = Path(os.getenv("APP_CONFIG", str(DEFAULT_CONFIG_FILE))).expanduser()
ENV_PLACEHOLDER_PATTERN = re.compile(r"\${(\w+)}")


def _decode_cors_allowed_origins(value: object) -> list[object]:
    if not isinstance(value, str):
        if isinstance(value, (list, tuple)):
            return list(value)
        message = "cors_allowed_origins must be a list or comma-separated origins"
        raise ValueError(message)

    stripped = value.strip()
    if not stripped:
        return []
    if not stripped.startswith("["):
        return stripped.split(",")
    try:
        decoded = json.loads(stripped)
    except json.JSONDecodeError as exc:
        message = "cors_allowed_origins must be a JSON list or comma-separated origins"
        raise ValueError(message) from exc
    if not isinstance(decoded, list):
        message = "cors_allowed_origins JSON value must be a list"
        raise ValueError(message)  # noqa: TRY004
    return decoded


def _normalize_cors_allowed_origins(raw_origins: list[object]) -> list[str]:
    origins: list[str] = []
    for raw_origin in raw_origins:
        if not isinstance(raw_origin, str):
            message = "cors_allowed_origins entries must be strings"
            raise ValueError(message)  # noqa: TRY004
        origin = raw_origin.strip().rstrip("/")
        if not origin:
            continue
        if origin == "*":
            message = "cors_allowed_origins must contain explicit origins, not '*'"
            raise ValueError(message)
        if origin not in origins:
            origins.append(origin)
    return origins


def _replace_env_placeholders(value: Any) -> Any:  # noqa: ANN401
    """Replace placeholders after YAML parsing so environment values stay YAML-safe."""
    if isinstance(value, str):
        return ENV_PLACEHOLDER_PATTERN.sub(
            lambda match: os.environ.get(match.group(1), match.group(0)),
            value,
        )
    if isinstance(value, list):
        return [_replace_env_placeholders(item) for item in value]
    if isinstance(value, dict):
        return {_replace_env_placeholders(key): _replace_env_placeholders(item) for key, item in value.items()}
    return value


class EnvYamlConfigSettingsSource(YamlConfigSettingsSource):
    """`${ENV_NAME}` 패턴을 YAML 파싱 후 환경변수로 치환."""

    def _read_file(self, file_path: Path) -> dict[str, Any]:
        with file_path.open(encoding=self.yaml_file_encoding) as yaml_file:
            loaded = yaml.safe_load(normalize_yaml_text(yaml_file.read()))
            loaded = _replace_env_placeholders(loaded)
        return loaded if isinstance(loaded, dict) else {}


class AgentConfig(BaseModel):
    mlflow_experiment_name: str = Field(default="mi_agent_local")
    aip_app_id: str = Field(default="mi_agent")
    mlflow_tracing_enabled: bool = Field(default=False)


class ModelParameterResourceStorageConfig(BaseModel):
    """Model Parameter Agent의 S3-compatible 리소스 접속 설정."""

    enabled: bool = Field(default=False)
    endpoint_url: str = Field(default="https://kr.object.ncloudstorage.com")
    region_name: str = Field(default="kr-standard")
    signature_version: str = Field(default="s3v4")
    bucket: str = Field(default="")
    access_key_id: SecretStr = Field(default=SecretStr(""))
    secret_access_key: SecretStr = Field(default=SecretStr(""))
    local_root: str = Field(default="/tmp/skmip/model-parameter-resources")  # noqa: S108
    connect_timeout_seconds: float = Field(default=50.0, gt=0)
    read_timeout_seconds: float = Field(default=60.0, gt=0)
    max_attempts: int = Field(default=3, ge=1)
    bootstrap_timeout_seconds: float = Field(default=420.0, gt=0)
    lock_timeout_seconds: float = Field(default=500.0, gt=0)
    download_chunk_size_bytes: int = Field(default=1024 * 1024, ge=64 * 1024)


class ModelParameterMiBaseFallbackConfig(BaseModel):
    """요청별 MI Base 입력을 준비하지 못했을 때 허용할 fallback 경계."""

    no_active_case_mode: Literal["fail", "configured_fallback"] = "fail"
    active_case_unavailable_mode: Literal[
        "fail",
        "verified_cache",
        "configured_fallback",
    ] = "verified_cache"


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
    llm_max_retries: int = Field(default=1, ge=0)
    llm_stream_enabled: bool = Field(default=False)
    llm_reasoning_effort: Literal[
        "default",
        "none",
        "minimal",
        "low",
        "medium",
        "high",
        "xhigh",
    ] = "default"
    # v4 Event·Interaction analysis stages keep a lighter effort than the global default.
    llm_v4_analysis_reasoning_effort: Literal[
        "default",
        "none",
        "minimal",
        "low",
        "medium",
        "high",
        "xhigh",
    ] = "low"
    # v4 group title is a short headline written after scenarios; it runs on the SPEED model with low reasoning.
    llm_v4_group_title_reasoning_effort: Literal[
        "default",
        "none",
        "minimal",
        "low",
        "medium",
        "high",
        "xhigh",
    ] = "low"
    llm_verbosity: Literal["default", "low", "medium", "high"] = "default"
    llm_structured_output_strict: bool = Field(default=False)

    # Web search
    # 활성 provider. WebSearchProviderFactory 의 분기 키이며, 콤마로 여러 개를 나열하면
    # 같은 질의를 provider 전부로 검색하고 결과를 합친다. 예: "responses,tavily"
    web_search_provider: str = Field(default="responses")

    # 비워두면 model_endpoint / model_api_key / model_api_deployment_name 를 그대로 사용한다.
    # base_url 은 envs/.env 의 WEB_SEARCH_API 로도 주입한다.
    web_search_base_url: str = Field(
        default="",
        validation_alias=AliasChoices("web_search_base_url", "web_search_api"),
    )
    web_search_api_key: str = Field(default="")
    web_search_model: str = Field(default="")
    web_search_context_size: Literal["low", "medium", "high"] = "medium"
    web_search_max_results: int = Field(default=1, ge=0)
    web_search_include_domains: list[str] = Field(default_factory=list)
    web_search_exclude_domains: list[str] = Field(default_factory=list)
    web_search_score_threshold: float = Field(default=0.0)
    web_search_reasoning_effort: (
        Literal[
            "none",
            "minimal",
            "low",
            "medium",
            "high",
            "xhigh",
        ]
        | None
    ) = "medium"
    web_search_tool_choice: Literal["auto", "required"] = "required"
    web_search_max_tool_calls: int | None = Field(default=None, ge=1)
    # 미설정 시 llm_timeout_sec
    web_search_timeout_sec: float | None = Field(default=None, gt=0)
    web_search_max_retries: int = Field(default=2, ge=0)

    # Tavily
    tavily_api_key: str = Field(default="")
    tavily_search_depth: Literal["basic", "advanced"] = "advanced"
    tavily_max_results: int = Field(default=1, ge=1)
    tavily_include_domains: list[str] = Field(default_factory=list)
    tavily_exclude_domains: list[str] = Field(default_factory=list)
    tavily_score_threshold: float = Field(default=0.5)

    # MI MCP server
    # MI Platform next-gen API 를 MCP tool 로 감싼 `mi-next-gen-mcp-server` 의 엔드포인트.
    # 비워 두면 MCP 기반 이벤트 조회(search_existing_events)가 호출 단계에서 실패한다.
    mi_mcp_base_url: str = Field(default="")
    mi_mcp_timeout_sec: float = Field(default=60.0, gt=0)

    # Model parameter proposal
    model_parameter_proposal_flow_release: str = Field(default="v4.1.7", min_length=1)
    model_parameter_transient_retry_max_attempts: int = Field(default=2, ge=1, le=5)
    model_parameter_transient_retry_base_delay_seconds: float = Field(default=0.5, ge=0.0, le=30.0)
    model_parameter_transient_retry_max_jitter_seconds: float = Field(default=0.25, ge=0.0, le=30.0)
    model_parameter_lut_enabled: bool = Field(default=False)
    model_parameter_lut_horizon_start_year: int = Field(default=2026)
    model_parameter_lut_horizon_end_year: int = Field(default=2030)
    model_parameter_basecase_value_max_decimal_places: int = Field(default=5, ge=-1)
    model_parameter_basecase_value_precision_mode: Literal["trunc", "ceil", "round"] = "trunc"
    model_parameter_proposed_value_max_decimal_places: int = Field(default=5, ge=-1)
    model_parameter_proposed_value_precision_mode: Literal["trunc", "ceil", "round"] = "trunc"
    model_parameter_max_parameter_slots: int = Field(default=100, ge=1)
    model_parameter_max_value_prompt_basecase_records: int = Field(default=100, ge=1)
    model_parameter_max_total_selected_slots: int = Field(default=300, ge=1)
    model_parameter_max_step2_prompt_bytes: int = Field(default=262_144, ge=1)
    model_parameter_max_step3_prompt_bytes: int = Field(default=262_144, ge=1)
    model_parameter_max_routing_candidates_per_dimension: int = Field(default=2, ge=1)
    model_parameter_v4_max_routing_candidates_per_dimension: int = Field(
        default=3,
        ge=1,
    )
    model_parameter_max_conditional_parameters_per_scenario: int = Field(
        default=4,
        ge=1,
    )
    model_parameter_variation_mode: Literal[
        "strict",
        "balanced",
        "exploratory",
    ] = "balanced"
    model_parameter_variation_profile_enabled: bool = Field(default=True)
    model_parameter_grounded_slot_recovery_enabled: bool = Field(default=True)
    model_parameter_resource_storage: ModelParameterResourceStorageConfig = Field(
        default_factory=ModelParameterResourceStorageConfig,
    )
    model_parameter_mi_base_fallback: ModelParameterMiBaseFallbackConfig = Field(
        default_factory=ModelParameterMiBaseFallbackConfig,
    )
    # Agent 전용 parser가 업무 스키마를 검증한다. common 설정 계층은 YAML 구조만 보존한다.
    model_parameter_resources: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_model_parameter_lut_horizon(self) -> Settings:
        if self.model_parameter_lut_horizon_start_year > self.model_parameter_lut_horizon_end_year:
            message = (
                "model_parameter_lut_horizon_start_year must be less than or equal to "
                "model_parameter_lut_horizon_end_year"
            )
            raise ValueError(message)
        return self

    http_max_concurrency: int

    # Scenario group admin/test APIs
    cors_allowed_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: [
            "http://127.0.0.1:5173",
            "http://localhost:5173",
        ],
    )
    scenario_group_admin_bearer_tokens: list[str] = Field(default_factory=list)
    create_signposts_max_concurrent_scenarios: int = Field(default=10, ge=1)
    scenario_group_operation_heartbeat_interval_seconds: float = Field(default=30.0, gt=0)
    scenario_group_operation_stale_after_seconds: float = Field(default=120.0, gt=0)
    scenario_group_operation_reaper_interval_seconds: float = Field(default=30.0, gt=0)
    additional_dimension_stale_after_seconds: float = Field(default=240.0, gt=0)
    hide_price_pressure: bool = True
    scenario_group_v4_impact_catalog_version: str = Field(default="v4.1", min_length=1)

    @model_validator(mode="after")
    def validate_scenario_group_operation_timing(self) -> Settings:
        minimum_stale_after = self.scenario_group_operation_heartbeat_interval_seconds * 3
        if self.scenario_group_operation_stale_after_seconds < minimum_stale_after:
            msg = (
                "scenario_group_operation_stale_after_seconds must be at least three times "
                "scenario_group_operation_heartbeat_interval_seconds"
            )
            raise ValueError(msg)
        return self

    @field_validator("scenario_group_v4_impact_catalog_version")
    @classmethod
    def validate_v4_impact_catalog_version(cls, value: str) -> str:
        normalized = value.strip()
        if re.fullmatch(r"v\d+(?:\.\d+)?", normalized) is None:
            message = "scenario_group_v4_impact_catalog_version must look like v4 or v4.1"
            raise ValueError(message)
        return normalized

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def parse_cors_allowed_origins(cls, value: object) -> list[str]:
        """JSON 배열과 쉼표 구분 문자열을 명시적 origin 목록으로 정규화한다."""
        return _normalize_cors_allowed_origins(_decode_cors_allowed_origins(value))

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
    callback_price_interpretations_path: str = Field(default="")
    callback_model_parameter_proposals_path: str = Field(default="")
    skip_callback: bool = Field(default=False)

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


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Process 시작 후 동일한 설정 snapshot을 재사용한다."""
    return Settings()


settings: Settings = get_settings()
