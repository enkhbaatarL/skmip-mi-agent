from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.agents.scenario_group_agent.api import router as scenario_group_router
from apps.common.configs.database.application_tables import APPLICATION_TABLES
from apps.common.configs.database.schema_validation import validate_schema
from apps.common.configs.database.sync_database.connection import get_sync_engine
from apps.common.logging.logger_config import logger, setup_logging
from apps.common.middleware.exception_handler import register_exception_handlers
from apps.common.middleware.request_logging import RequestLoggingMiddleware
from apps.common.openapi.local_docs import register_local_openapi_docs


INGRESS_PREFIX = os.getenv("OPENAPI_PREFIX", "").rstrip("/")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    from apps.common.configs.config import get_settings
    from apps.connectors.callback.oauth2_token_manager import get_token_manager
    from apps.connectors.mlflow.tracing import setup_mlflow_tracing

    cfg = get_settings()
    setup_logging(cfg.log_level)
    logger.info(f"Logging configured from settings | level={cfg.log_level.upper()}")
    setup_mlflow_tracing(cfg, entrypoint_name=Path(__file__).name)

    logger.info("Validating ORM models against the database schema")
    await asyncio.to_thread(validate_schema, get_sync_engine(), APPLICATION_TABLES)
    logger.info("ORM/DB schema validation completed")
    if cfg.callback_oauth2_token_url:
        logger.info("Pre-fetching callback OAuth2 token")
        try:
            await get_token_manager().get_token()
            logger.info("Callback OAuth2 token pre-fetched successfully")
        except Exception:
            logger.exception(
                "Callback OAuth2 token pre-fetch failed, continuing startup without pre-fetched token"
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
    scenario_group_router,
    prefix="",
    tags=["scenario-group"],
)

app = register_exception_handlers(app)
