"""event_generate_agent 전용 ASGI 엔트리포인트(로컬 디버깅용).

interpret.py 와 동일한 구성을 따르되, 아직 구현 중인 flow를 로컬에서 단독으로
띄워 breakpoint를 걸 수 있도록 DB 스키마 검증 실패를 치명적으로 다루지 않는다.

VSCode 디버그 구성이 주입하던 envs/.env, envs/config.yaml 을 직접 실행할 때도 그대로
쓰도록 부트스트랩한다. 터미널에서 띄우면 uvicorn 의 --reload 가 정상 동작한다.

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

    # 이벤트 생성 flow는 아직 DB 접근이 연결되지 않았으므로, 로컬 디버깅 시
    # DB가 없더라도 서버가 뜨도록 검증 실패를 WARNING으로만 남긴다.
    logger.info("Validating ORM models against the database schema")
    try:
        await asyncio.to_thread(validate_schema, get_sync_engine(), APPLICATION_TABLES)
        logger.info("ORM/DB schema validation completed")
    except Exception as exc:
        logger.warning(f"ORM/DB schema validation skipped | error={exc!r}")

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
