from __future__ import annotations

"""Best-effort MLflow trace collection for manual quality evaluation.

Trace availability is an infrastructure concern.  Every public function here
therefore returns a skip/error result instead of making an absent MLflow server
look like a quality failure.
"""

from dataclasses import asdict, dataclass, field
import os
from typing import Any


@dataclass(frozen=True)
class SpanSummary:
    name: str
    span_type: str | None
    status: str | None
    duration_ms: float | None
    inputs_excerpt: str | None = None
    outputs_excerpt: str | None = None


@dataclass(frozen=True)
class TraceSummary:
    scenario_group_id: int
    trace_id: str | None
    status: str
    detail: str
    spans: list[SpanSummary] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def collect_trace_summary(
    scenario_group_id: int | None,
    *,
    tracking_uri: str | None = None,
    tracking_username: str | None = None,
    tracking_password: str | None = None,
    max_excerpt_chars: int = 800,
) -> TraceSummary:
    """Return the newest trace for a scenario group, or an explicit SKIP result."""
    if scenario_group_id is None:
        return TraceSummary(0, None, "SKIP", "scenario_group_id 없음")
    try:
        import mlflow
        from mlflow import MlflowClient
    except ImportError:
        return TraceSummary(scenario_group_id, None, "SKIP", "MLflow 패키지 미설치")

    try:
        if tracking_uri:
            mlflow.set_tracking_uri(tracking_uri)
        with _mlflow_credentials(tracking_username, tracking_password):
            traces = mlflow.search_traces(
                filter_string=f'tag.scenario_group_id = "{scenario_group_id}"',
                include_spans=False,
            )
            candidates = _as_records(traces)
            if not candidates:
                return TraceSummary(scenario_group_id, None, "SKIP", "trace 없음: 원인 국소화 불가")
            latest = max(candidates, key=_trace_timestamp)
            trace_id = _value(latest, "trace_id", "traceId", "request_id")
            if not trace_id:
                return TraceSummary(scenario_group_id, None, "SKIP", "trace 검색 결과에 trace_id 없음")
            trace = MlflowClient().get_trace(str(trace_id))
            spans = [_summarize_span(span, max_excerpt_chars) for span in _trace_spans(trace)]
            return TraceSummary(scenario_group_id, str(trace_id), "PASS", "trace 수집 완료", spans)
    except Exception as exc:  # External server/API compatibility boundary.
        return TraceSummary(scenario_group_id, None, "INFRA_ERROR", f"MLflow trace 조회 실패: {exc}")


def collect_traces(
    scenario_group_ids: list[int | None],
    *,
    tracking_uri: str | None = None,
    tracking_username: str | None = None,
    tracking_password: str | None = None,
) -> dict[int, TraceSummary]:
    """Collect each group independently so one bad trace cannot hide others."""
    return {
        group_id: collect_trace_summary(
            group_id,
            tracking_uri=tracking_uri,
            tracking_username=tracking_username,
            tracking_password=tracking_password,
        )
        for group_id in scenario_group_ids
        if group_id is not None
    }


class _mlflow_credentials:
    """Temporarily expose Basic-auth credentials only to the MLflow client."""

    def __init__(self, username: str | None, password: str | None) -> None:
        self.values = {
            "MLFLOW_TRACKING_USERNAME": username,
            "MLFLOW_TRACKING_PASSWORD": password,
        }
        self.previous: dict[str, str | None] = {}

    def __enter__(self) -> None:
        for key, value in self.values.items():
            self.previous[key] = os.environ.get(key)
            if value:
                os.environ[key] = value

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        for key, previous in self.previous.items():
            if previous is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = previous


def _as_records(value: Any) -> list[Any]:
    if value is None:
        return []
    if hasattr(value, "to_dict"):
        records = value.to_dict("records")
        return records if isinstance(records, list) else []
    return list(value) if isinstance(value, (list, tuple)) else []


def _trace_timestamp(record: Any) -> float:
    value = _value(record, "timestamp_ms", "timestamp", "request_time", "start_time_ms")
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _trace_spans(trace: Any) -> list[Any]:
    data = getattr(trace, "data", None)
    spans = getattr(data, "spans", None) if data is not None else None
    if spans is None and isinstance(trace, dict):
        spans = trace.get("data", {}).get("spans", trace.get("spans", []))
    return list(spans or [])


def _summarize_span(span: Any, max_excerpt_chars: int) -> SpanSummary:
    start = _value(span, "start_time_ns", "start_time_ms", "start_time")
    end = _value(span, "end_time_ns", "end_time_ms", "end_time")
    duration_ms = _duration_ms(start, end)
    attributes = _value(span, "attributes") or {}
    span_type = _value(span, "span_type", "spanType") or attributes.get("mlflow.spanType")
    status = _value(span, "status", "status_code")
    return SpanSummary(
        name=str(_value(span, "name") or "unnamed"),
        span_type=str(span_type) if span_type is not None else None,
        status=str(status) if status is not None else None,
        duration_ms=duration_ms,
        inputs_excerpt=_excerpt(_value(span, "inputs"), max_excerpt_chars),
        outputs_excerpt=_excerpt(_value(span, "outputs"), max_excerpt_chars),
    )


def _duration_ms(start: Any, end: Any) -> float | None:
    try:
        difference = float(end) - float(start)
    except (TypeError, ValueError):
        return None
    # MLflow span timestamps are normally nanoseconds; tolerate milliseconds.
    return difference / 1_000_000 if abs(difference) > 1_000_000 else difference


def _value(source: Any, *names: str) -> Any:
    for name in names:
        if isinstance(source, dict) and name in source:
            return source[name]
        value = getattr(source, name, None)
        if value is not None:
            return value
    return None


def _excerpt(value: Any, max_chars: int) -> str | None:
    if value is None:
        return None
    text = str(value).replace("\n", " ")
    return text[:max_chars] + ("…" if len(text) > max_chars else "")
