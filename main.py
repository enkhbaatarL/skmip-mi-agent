from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.agents.scenario_group_agent.api import router as scenario_group_router
from apps.common.configs.database.application_tables import APPLICATION_TABLES
from apps.common.configs.database.schema_validation import validate_schema
from apps.common.configs.database.sync_database.connection import get_sync_engine
from apps.common.logging.logger_config import logger
from apps.common.middleware.exception_handler import register_exception_handlers


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    logger.info("Validating ORM models against the database schema")
    await asyncio.to_thread(validate_schema, get_sync_engine(), APPLICATION_TABLES)
    logger.info("ORM/DB schema validation completed")
    yield


app = FastAPI(title="SKMIP MI Agent API", lifespan=lifespan)

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(
    scenario_group_router,
    prefix="",
    tags=["scenario-group"],
)

app = register_exception_handlers(app)
