from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import json
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.agents.model_parameter_agent.api import router as model_parameter_router
from apps.agents.model_parameter_agent.constants import AGENT_NAME
from apps.common.configs.database.application_tables import (
    APPLICATION_TABLES,
    MODEL_PARAMETER_TABLES,
)
from apps.common.configs.database.schema_validation import validate_schema
from apps.common.configs.database.sync_database.connection import get_sync_engine
from apps.common.logging.logger_config import logger, setup_logging
from apps.common.middleware.exception_handler import register_exception_handlers
from apps.common.middleware.request_logging import RequestLoggingMiddleware
from apps.common.openapi.local_docs import register_local_openapi_docs


INGRESS_PREFIX = os.getenv("OPENAPI_PREFIX", "").rstrip("/")


def _lut_catalog_debug_json(lut_catalog: Any) -> str:
    if lut_catalog is None:
        payload = {
            "version": None,
            "record_count": 0,
            "record_counts_by_parameter": {},
        }
    else:
        counts_by_parameter: dict[str, int] = {}
        for record in lut_catalog.records:
            counts_by_parameter[record.parameter_name] = (
                counts_by_parameter.get(record.parameter_name, 0) + 1
            )
        payload = {
            "version": lut_catalog.version,
            "policy": {
                "start_year": lut_catalog.policy.start_year,
                "end_year": lut_catalog.policy.end_year,
            },
            "record_count": len(lut_catalog.records),
            "record_counts_by_parameter": counts_by_parameter,
        }
    return json.dumps(
        payload,
        ensure_ascii=False,
        default=str,
        indent=2,
    )


def _basecase_cache_debug_json(summary: Any) -> str:
    payload = {
        "parameter_count": summary.parameter_count,
        "profile_count": summary.profile_count,
        "sheet_available_count": summary.sheet_available_count,
        "record_count": summary.record_count,
        "warning_count": summary.warning_count,
        "warnings": list(summary.warnings),
    }
    return json.dumps(
        payload,
        ensure_ascii=False,
        default=str,
        indent=2,
    )


_SENSITIVE_CONFIG_KEY_PARTS = (
    "access_key",
    "api_key",
    "bearer",
    "credential",
    "password",
    "secret",
)


def _is_sensitive_config_key(key: str) -> bool:
    normalized_key = key.casefold()
    if any(part in normalized_key for part in _SENSITIVE_CONFIG_KEY_PARTS):
        return True
    return "token" in normalized_key and not normalized_key.endswith("token_url")


def _redact_config_value(value: Any, *, key: str = "") -> Any:
    if _is_sensitive_config_key(key):
        return "**********"
    if isinstance(value, dict):
        return {
            str(item_key): _redact_config_value(item_value, key=str(item_key))
            for item_key, item_value in value.items()
        }
    if isinstance(value, list):
        return [_redact_config_value(item) for item in value]
    return value


def _config_debug_json(cfg: Any, *, source_path: Path) -> str:
    payload = {
        "source_path": str(source_path),
        "settings": _redact_config_value(cfg.model_dump(mode="json")),
    }
    return json.dumps(
        payload,
        ensure_ascii=False,
        default=str,
        indent=2,
    )


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    from apps.agents.model_parameter_agent.utils.basecase import (
        preload_basecase_runtime_cache,
    )
    from apps.agents.model_parameter_agent.utils.lut import (
        LutLoadPolicy,
        validate_lut_startup,
    )
    from apps.agents.model_parameter_agent.utils.resource_bootstrap import (
        ensure_model_parameter_resource_runtime,
    )
    from apps.agents.model_parameter_agent.utils.resource_manifest import (
        load_model_parameter_resource_manifest,
    )
    from apps.agents.model_parameter_agent.utils.resource_runtime import (
        clear_model_parameter_resource_runtime,
    )
    from apps.common.configs.config import CONFIG_FILE_PATH, get_settings
    from apps.connectors.callback.oauth2_token_manager import get_token_manager
    from apps.connectors.mlflow.tracing import setup_mlflow_tracing

    cfg = get_settings()
    setup_logging(cfg.log_level)
    logger.info(f"Logging configured from settings | level={cfg.log_level.upper()}")
    logger.opt(lazy=True).debug(
        "[model-parameter][config] loaded_once=\n{}",
        lambda: _config_debug_json(cfg, source_path=CONFIG_FILE_PATH),
    )
    setup_mlflow_tracing(cfg, agent_name=AGENT_NAME)

    logger.info("Validating ORM models against the database schema")
    await asyncio.to_thread(
        validate_schema,
        get_sync_engine(),
        APPLICATION_TABLES + MODEL_PARAMETER_TABLES,
    )
    logger.info("ORM/DB schema validation completed")

    lut_policy = LutLoadPolicy(
        start_year=cfg.model_parameter_lut_horizon_start_year,
        end_year=cfg.model_parameter_lut_horizon_end_year,
    )
    resource_manifest = load_model_parameter_resource_manifest(
        cfg.model_parameter_resources,
        source_path=CONFIG_FILE_PATH,
    )
    resource_paths = await ensure_model_parameter_resource_runtime(
        cfg.model_parameter_resource_storage,
        manifest=resource_manifest,
        lut_enabled=cfg.model_parameter_lut_enabled,
        lut_policy=lut_policy,
    )
    logger.info(
        "Model Parameter resource source resolved | source={} fingerprint={} fallback_active={}",
        resource_paths.source,
        resource_paths.resource_fingerprint,
        resource_paths.fallback_reason is not None,
    )
    _, lut_catalog = await asyncio.to_thread(
        validate_lut_startup,
        cfg.model_parameter_lut_enabled,
        lut_policy,
        registry=resource_paths.lut_registry,
    )
    logger.info(
        "Model Parameter LUT startup validation completed | enabled={} version={}",
        cfg.model_parameter_lut_enabled,
        lut_catalog.version if lut_catalog is not None else None,
    )
    logger.opt(lazy=True).debug(
        "[model-parameter][lut][summary] startup_catalog=\n{}",
        lambda: _lut_catalog_debug_json(lut_catalog),
    )

    basecase_summary = await asyncio.to_thread(
        preload_basecase_runtime_cache,
        str(resource_paths.basecase_dir),
        registry=resource_paths.lut_registry,
    )
    logger.info(
        "Model Parameter Basecase startup preload completed | parameters={} profiles={} "
        "available_sheets={} records={} warnings={}",
        basecase_summary.parameter_count,
        basecase_summary.profile_count,
        basecase_summary.sheet_available_count,
        basecase_summary.record_count,
        basecase_summary.warning_count,
    )
    logger.opt(lazy=True).debug(
        "[model-parameter][basecase][summary] startup_cache=\n{}",
        lambda: _basecase_cache_debug_json(basecase_summary),
    )

    if cfg.callback_oauth2_token_url:
        logger.info("Pre-fetching callback OAuth2 token")
        try:
            await get_token_manager().get_token()
            logger.info("Callback OAuth2 token pre-fetched successfully")
        except Exception:
            logger.exception(
                "Callback OAuth2 token pre-fetch failed, continuing startup without pre-fetched token",
            )
    else:
        logger.error("callback_oauth2_token_url not configured, skipping token pre-fetch")

    try:
        yield
    finally:
        clear_model_parameter_resource_runtime()


app = FastAPI(
    title="SKMIP MI Agent API",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    servers=[{"url": INGRESS_PREFIX}] if INGRESS_PREFIX else None,
)

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)
register_local_openapi_docs(app, INGRESS_PREFIX)


app.include_router(
    model_parameter_router,
    prefix="",
    tags=["model-parameter"],
)

app = register_exception_handlers(app)
