"""event_generate_agent 전용 ASGI 엔트리포인트.

interpret.py 와 동일하게 Agent 단위로 별도 이미지(Dockerfile_event_generate)로 배포한다.
이미지 안에서는 이 파일이 main.py 로 복사되어 `gunicorn main:app` 으로 실행된다.

로컬에서 터미널로 직접 띄울 때도 envs/.env, envs/config.yaml 을 쓰도록 부트스트랩한다.
컨테이너에는 envs/.env 가 포함되지 않으므로(dockerignore) 운영에서는 영향이 없다.

    uvicorn event_generate:app --reload --port 8003
"""
# ruff: noqa: E402 - 환경 부트스트랩이 apps.* import 보다 먼저 실행되어야 한다.

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import os
from pathlib import Path


# Settings 는 import 시점에 인스턴스화되므로, apps.* import 보다 먼저 환경을 갖춰야 한다.
# 이미 주입된 환경변수(k8s, docker, VSCode envFile)가 항상 우선한다.
_ROOT_DIR = Path(__file__).resolve().parent
_DOTENV_PATH = _ROOT_DIR / "envs" / ".env"
_APP_CONFIG_PATH = _ROOT_DIR / "envs" / "config.yaml"
if _DOTENV_PATH.exists():
    from dotenv import load_dotenv

    load_dotenv(_DOTENV_PATH, override=False)
if "APP_CONFIG" not in os.environ and _APP_CONFIG_PATH.exists():
    os.environ["APP_CONFIG"] = str(_APP_CONFIG_PATH)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.agents.event_generate_agent.api import router as event_generate_router
from apps.agents.event_generate_agent.constants import AGENT_NAME
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
    from apps.connectors.mlflow.tracing import setup_mlflow_tracing

    cfg = get_settings()
    setup_logging(cfg.log_level)
    logger.info(f"Logging configured from settings | level={cfg.log_level.upper()}")
    setup_mlflow_tracing(cfg, agent_name=AGENT_NAME)

    logger.info("Validating ORM models against the database schema")
    await asyncio.to_thread(validate_schema, get_sync_engine(), APPLICATION_TABLES)
    logger.info("ORM/DB schema validation completed")

    yield


app = FastAPI(
    title="SKMIP MI Agent API (event-generate)",
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
    event_generate_router,
    prefix="",
    tags=["event-generate"],
)

app = register_exception_handlers(app)
