from __future__ import annotations

"""Local-only target and MLflow configuration for manual quality evaluation."""

from dataclasses import dataclass
from pathlib import Path


DEFAULT_USER_ID = 10603
AGENT_ALIASES = {
    "mi-vm": "http://40.82.137.178:8001",
    "local": "http://localhost:8000",
}
DEFAULT_TEST_INFO_PATH = Path(__file__).resolve().parents[3] / ".claude/skills/scenario-quality-eval/test_info.local"


@dataclass(frozen=True)
class RuntimeTarget:
    base_url: str | None
    user_id: int
    mlflow_uri: str | None
    mlflow_username: str | None
    mlflow_password: str | None


def load_runtime_target(
    *,
    agent: str | None = None,
    base_url: str | None = None,
    user_id: int | None = None,
    mlflow_uri: str | None = None,
    test_info_path: Path | None = None,
) -> RuntimeTarget:
    """Resolve explicit CLI values before ignored local configuration and defaults."""
    values = _load_key_values(test_info_path or DEFAULT_TEST_INFO_PATH)
    configured_alias = _value(values, "agent", "agent_alias", "agent_url_alias")
    configured_url = _value(values, "base_url", "agent_url")
    resolved_url = base_url or (_alias_url(agent) if agent else None) or configured_url or _alias_url(configured_alias)
    resolved_user_id = user_id if user_id is not None else _parse_user_id(_value(values, "user_id", "userid"))
    return RuntimeTarget(
        base_url=_normalize_url(resolved_url),
        user_id=resolved_user_id if resolved_user_id is not None else DEFAULT_USER_ID,
        mlflow_uri=_normalize_url(mlflow_uri or _value(values, "mlflow_uri", "mlflow_url")),
        mlflow_username=_value(values, "mlflow_username", "mlflow_user", "mlflow_id"),
        mlflow_password=_value(values, "mlflow_password", "mlflow_pw", "mlflow_pass"),
    )


def _load_key_values(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip().lower()] = value.strip().strip('"').strip("'")
    return values


def _value(values: dict[str, str], *names: str) -> str | None:
    return next((values[name] for name in names if values.get(name)), None)


def _alias_url(alias: str | None) -> str | None:
    if alias is None:
        return None
    normalized = alias.strip().lower()
    if normalized not in AGENT_ALIASES:
        raise ValueError(f"Unknown agent alias {alias!r}; use one of: {', '.join(AGENT_ALIASES)}")
    return AGENT_ALIASES[normalized]


def _normalize_url(value: str | None) -> str | None:
    return value.rstrip("/") if value else None


def _parse_user_id(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"user_id must be an integer, got {value!r}") from exc
