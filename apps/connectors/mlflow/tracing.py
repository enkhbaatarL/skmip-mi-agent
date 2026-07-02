from __future__ import annotations

from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

from apps.common.logging.logger_config import logger


def _tracking_uri_with_credentials(
    tracking_uri: str,
    username: str,
    password: str,
) -> str:
    if not username:
        return tracking_uri
    parts = urlsplit(tracking_uri)
    if not parts.scheme or not parts.netloc:
        return tracking_uri
    host = parts.hostname or ""
    port = f":{parts.port}" if parts.port is not None else ""
    auth = quote(username, safe="")
    if password:
        auth += f":{quote(password, safe='')}"
    netloc = f"{auth}@{host}{port}"
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


def _sanitized_tracking_uri(tracking_uri: str) -> str:
    parts = urlsplit(tracking_uri)
    if "@" not in parts.netloc:
        return tracking_uri
    netloc = parts.netloc.rsplit("@", 1)[-1]
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


def setup_mlflow_tracing(cfg: Any) -> None:
    if not getattr(cfg, "mlflow_tracing_enabled", False):
        logger.info("MLflow tracing disabled")
        return

    try:
        import mlflow
    except Exception as exc:
        logger.warning(f"MLflow tracing disabled because mlflow import failed | error={exc!r}")
        return

    tracking_uri = str(getattr(cfg, "mlflow_tracking_uri", "") or "")
    experiment_name = str(getattr(cfg, "mlflow_experiment_name", "") or "mi-agent-local")
    username = str(getattr(cfg, "mlflow_tracking_username", "") or "")
    password = str(getattr(cfg, "mlflow_tracking_password", "") or "")

    try:
        if tracking_uri:
            mlflow.set_tracking_uri(_tracking_uri_with_credentials(tracking_uri, username, password))
        mlflow.set_experiment(experiment_name)
        mlflow.langchain.autolog(
            run_tracer_inline=bool(getattr(cfg, "mlflow_langchain_run_tracer_inline", False)),
        )
        if bool(getattr(cfg, "mlflow_openai_autolog_enabled", True)):
            mlflow.openai.autolog()
        logger.info(
            "MLflow tracing enabled | tracking_uri={} | experiment={}",
            _sanitized_tracking_uri(tracking_uri),
            experiment_name,
        )
    except Exception as exc:
        logger.warning(f"MLflow tracing setup failed, continuing without tracing | error={exc!r}")
