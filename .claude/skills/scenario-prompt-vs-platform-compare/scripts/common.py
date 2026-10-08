"""Shared helpers for the prompt-vs-platform comparison scripts.

Credentials are read from the repository env files (``env.txt`` then ``envs/env.txt``) or the
process environment. Secret values are never printed.
"""

from __future__ import annotations

import json
import os
import unicodedata
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[4]
ENV_FILES = (REPO_ROOT / "env.txt", REPO_ROOT / "envs" / "env.txt")
DEFAULT_MLFLOW_URI = "http://40.82.137.178:8005"


def load_env() -> dict[str, str]:
    values: dict[str, str] = {}
    for path in ENV_FILES:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            values.setdefault(key.strip(), value.strip().strip('"').strip("'"))
    for key, value in os.environ.items():
        values[key] = value
    return values


def db_connect() -> Any:
    import pymysql

    env = load_env()
    return pymysql.connect(
        host=env["METADATA_DB_HOST"],
        port=int(env["METADATA_DB_PORT"]),
        user=env["METADATA_DB_USERNAME"],
        password=env["METADATA_DB_PASSWORD"],
        database=env["METADATA_DB_NAME"],
        charset="utf8mb4",
        connect_timeout=10,
    )


def db_target() -> str:
    env = load_env()
    return f"{env.get('METADATA_DB_HOST')}:{env.get('METADATA_DB_PORT')}/{env.get('METADATA_DB_NAME')}"


def query(sql: str, params: tuple[Any, ...] | None = None) -> list[dict[str, Any]]:
    import pymysql

    conn = db_connect()
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cur:
            cur.execute(sql, params)
            return list(cur.fetchall())
    finally:
        conn.close()


def mlflow_client(tracking_uri: str | None = None) -> Any:
    env = load_env()
    for key in ("MLFLOW_TRACKING_USERNAME", "MLFLOW_TRACKING_PASSWORD"):
        if env.get(key):
            os.environ[key] = env[key]
    from mlflow import MlflowClient

    return MlflowClient(tracking_uri=tracking_uri or env.get("MLFLOW_TRACKING_URI") or DEFAULT_MLFLOW_URI)


def nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def as_json(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (TypeError, ValueError):
            return value
    return value


def dump_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
