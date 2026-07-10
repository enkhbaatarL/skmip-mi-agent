from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import json
import os
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.agents.model_parameter_agent.api import router as model_parameter_router
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


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    from apps.agents.model_parameter_agent.utils.lut import (
        LutLoadPolicy,
        validate_lut_startup,
    )
    from apps.common.configs.config import get_settings
    from apps.connectors.callback.oauth2_token_manager import get_token_manager

    cfg = get_settings()
    setup_logging(cfg.log_level)
    logger.info(f"Logging configured from settings | level={cfg.log_level.upper()}")

    lut_policy = LutLoadPolicy(
        start_year=cfg.model_parameter_lut_horizon_start_year,
        end_year=cfg.model_parameter_lut_horizon_end_year,
    )
    _, lut_catalog = await asyncio.to_thread(
        validate_lut_startup,
        cfg.model_parameter_lut_enabled,
        lut_policy,
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

    logger.info("Validating ORM models against the database schema")
    await asyncio.to_thread(
        validate_schema,
        get_sync_engine(),
        APPLICATION_TABLES + MODEL_PARAMETER_TABLES,
    )
    logger.info("ORM/DB schema validation completed")
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

    yield


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
