from __future__ import annotations

"""Standalone Markdown report rendering and SQLite-backed run statistics."""

import json
import math
import sqlite3
from collections import defaultdict
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from tests.manual.quality_eval.artifacts import BatchArtifacts
    from tests.manual.quality_eval.judge import JudgeResult
    from tests.manual.quality_eval.layer1_checks import CheckResult


def collect_performance_stats(db_path: Path, batch_id: str, *, top_n: int = 10) -> dict[str, Any]:
    """Recalculate report statistics from pipeline SQLite, never from LLM output."""
    if not db_path.exists():
        return {"available": False, "reason": f"SQLite 없음: {db_path}"}
    try:
        connection = sqlite3.connect(db_path)
        connection.row_factory = sqlite3.Row
        api_rows = connection.execute(
            """
            SELECT m.step, m.elapsed_ms, m.ok, m.status_code, m.reason, r.mi_event_id,
                   r.scenario_group_id, r.retried_create, r.pre_deleted
              FROM api_call_metrics m JOIN pipeline_runs r ON r.run_id = m.run_id
             WHERE r.batch_id = ? ORDER BY m.id
            """,
            (batch_id,),
        ).fetchall()
        failures = connection.execute(
            """
            SELECT r.mi_event_id, r.event_type_l2_id, r.initial_action_state, r.scenario_group_id,
                   r.error_step, r.error_reason, r.status,
                   (SELECT m.status_code FROM api_call_metrics m WHERE m.run_id = r.run_id
                    AND (r.error_step IS NULL OR m.step = r.error_step) ORDER BY m.id DESC LIMIT 1) AS status_code
              FROM pipeline_runs r WHERE r.batch_id = ? AND r.status != 'success' ORDER BY r.started_at
            """,
            (batch_id,),
        ).fetchall()
        all_runs = connection.execute(
            "SELECT status, mi_event_id, scenario_group_id FROM pipeline_runs WHERE batch_id = ? ORDER BY started_at",
            (batch_id,),
        ).fetchall()
    except sqlite3.Error as exc:
        return {"available": False, "reason": f"SQLite 조회 실패: {exc}"}
    finally:
        if "connection" in locals():
            connection.close()

    grouped: dict[str, list[sqlite3.Row]] = defaultdict(list)
    for row in api_rows:
        grouped[str(row["step"])].append(row)
    api_stats = []
    for step, rows in grouped.items():
        elapsed = [int(row["elapsed_ms"]) for row in rows]
        api_stats.append(
            {
                "step": step,
                "calls": len(rows),
                "failures": sum(not bool(row["ok"]) for row in rows),
                "avg_ms": sum(elapsed) / len(elapsed),
                "min_ms": min(elapsed),
                "max_ms": max(elapsed),
                "p95_ms": _percentile(elapsed, 0.95),
            },
        )
    slowest = sorted((dict(row) for row in api_rows), key=lambda row: int(row["elapsed_ms"]), reverse=True)[:top_n]
    return {
        "available": True,
        "api_stats": api_stats,
        "slowest": slowest,
        "failures": [dict(row) for row in failures],
        "runs": [dict(row) for row in all_runs],
    }


def render_quality_report(
    batch: BatchArtifacts,
    layer1: Mapping[int, Iterable[CheckResult]] | None = None,
    judge: Mapping[int, Iterable[JudgeResult] | JudgeResult] | None = None,
    perf: Mapping[str, Any] | None = None,
    probe: Iterable[Mapping[str, Any]] | None = None,
    golden_notice: str | Iterable[str] | None = None,
    *,
    trace: Mapping[int, Any] | None = None,
) -> str:
    """Render a self-contained report; absent layers are explicitly reported as skips."""
    layer1 = layer1 or {}
    judge = judge or {}
    perf = perf or {"available": False, "reason": "성능 지표 미수집"}
    probes = list(probe or [])
    successful = [run for run in batch.runs if run.status == "success"]
    failed = [run for run in batch.runs if run.status != "success"]
    all_checks = [check for checks in layer1.values() for check in checks]
    all_scores = [item for result in judge.values() for item in _judge_items(result)]
    verdict = _batch_verdict(all_checks, all_scores)

    lines = [
        f"# Scenario Quality Report — {batch.batch_id}",
        "",
        "## 전체 verdict 요약",
        "",
        f"- **{verdict}** · 성공 평가 대상 {len(successful)}건 · pipeline 실패/제외 {len(failed)}건",
        f"- Layer 1: FAIL {sum(c.status == 'FAIL' for c in all_checks)}, WARN {sum(c.status == 'WARN' for c in all_checks)}, SKIP {sum(c.status == 'SKIP' for c in all_checks)}",
        f"- Layer 2: 평균 {_average([_get(item, 'score') for item in all_scores])} / 5 · NEEDS_FACT {sum(_has_external_fact(item) for item in all_scores)}건",
        "",
        "## 품질 대상 / 제외 대상",
        "",
        "| miEventId | scenarioGroupId | pipeline status | 평가 여부 |",
        "| --- | --- | --- | --- |",
    ]
    for run in batch.runs:
        lines.append(
            f"| {run.mi_event_id} | {run.scenario_group_id or '-'} | {run.status} | {'대상' if run.status == 'success' else 'pipeline 실패로 제외'} |",
        )

    lines.extend(["", "## Layer 1 결정적 규칙 검사", "", "| miEventId | Check | Status | Detail | Offenders |", "| --- | --- | --- | --- | --- |"])
    if all_checks:
        for event_id, checks in layer1.items():
            for check in checks:
                lines.append(
                    f"| {event_id} | {check.check_id} | {check.status} | {_cell(check.detail)} | {_cell(', '.join(check.offenders) or '-')} |",
                )
    else:
        lines.append("| - | - | SKIP | Layer 1 결과 없음 | - |")

    lines.extend(["", "## Layer 2 Judge 점수 및 violation", "", "| miEventId | Rubric | Score | Verdict |", "| --- | --- | --- | --- |"])
    if all_scores:
        for event_id, result in judge.items():
            for item in _judge_items(result):
                lines.append(f"| {event_id} | {_get(item, 'judge_id')} | {_get(item, 'score')} | {_get(item, 'verdict')} |")
        lines.extend(["", "### Violation 상세", ""])
        violations = [(event_id, violation) for event_id, result in judge.items() for item in _judge_items(result) for violation in _get(item, "violations", [])]
        if violations:
            for event_id, violation in violations:
                lines.extend(
                    [
                        f"- **miEventId={event_id} · {_get(violation, 'target_type')}:{_get(violation, 'target_id')}**",
                        f"  - evidence: {_get(violation, 'evidence')}",
                        f"  - reason: {_get(violation, 'reason')}",
                        f"  - suggested fix: {_get(violation, 'suggested_fix')}",
                        f"  - fact dependency: {_get(violation, 'fact_dependency')}",
                        f"  - trace link: {_trace_link(trace, event_id, _get(violation, 'target_type'))}",
                    ],
                )
        else:
            lines.append("- violation 없음")
    else:
        lines.append("| - | - | - | SKIP: judge 미실행 또는 인프라 실패 |")

    lines.extend(_render_probe_section(probes))
    lines.extend(_render_golden_section(golden_notice))
    lines.extend(_render_performance_section(perf, trace))
    lines.extend(_render_trace_section(trace))
    lines.extend(
        [
            "",
            "## 관측성 개선 제안",
            "",
            "- validation callback에 `checks[]`, `validationMode`, `reviewSkipped`, `llmInvoked`, `traceId`를 노출하면 probe를 check-id 단위로 판정할 수 있습니다.",
            "- event detail 또는 trace가 없으면 event grounding과 stage 원인 국소화는 SKIP/추정 불가로 분리해야 합니다.",
        ],
    )
    return "\n".join(lines) + "\n"


def _render_probe_section(probes: list[Mapping[str, Any]]) -> list[str]:
    lines = ["", "## Validation mutation probe", "", "| Mutation | Expected | Observed | Verdict | Detail |", "| --- | --- | --- | --- | --- |"]
    if not probes:
        return lines + ["| - | - | SKIP: probe 미실행 | - | - |"]
    for item in probes:
        lines.append(
            f"| {_get(item, 'mutation_id')} | {_cell(_get(item, 'expected'))} | {_cell(_get(item, 'observed'))} | {_get(item, 'verdict')} | {_cell(_get(item, 'detail'))} |",
        )
    seeded = [item for item in probes if _get(item, "mutation_id") in {"V-01", "V-02", "V-03", "V-04"}]
    clean = [item for item in probes if _get(item, "mutation_id") in {"V-00", "V-07"}]
    generated = [item for item in probes if _get(item, "mutation_id") == "V-05"]
    input_validation = [item for item in probes if _get(item, "mutation_id") == "V-06"]
    lines.extend(
        [
            "",
            f"- seeded-defect recall (V-01~V-04): {_rate(seeded)}",
            f"- clean-pass rate (V-00/V-07): {_rate(clean)}",
            f"- auto-generation validity (V-05): {_rate(generated)}",
            f"- input validation behavior (V-06): {_rate(input_validation)}",
        ],
    )
    return lines


def _render_golden_section(notice: str | Iterable[str] | None) -> list[str]:
    notices = [notice] if isinstance(notice, str) else list(notice or [])
    lines = ["", "## Golden case recall", ""]
    if notices:
        return lines + [f"- {item}" for item in notices]
    return lines + ["- 정식 채점은 `--golden` 실행 시에만 수행됩니다."]


def _render_performance_section(perf: Mapping[str, Any], trace: Mapping[int, Any] | None) -> list[str]:
    lines = ["", "## 성능 및 실행 통계", ""]
    if not perf.get("available"):
        return lines + [f"- SKIP: {perf.get('reason', '성능 지표 없음')}"]
    lines.extend(["### API별 수행시간", "", "| API step | Calls | Failures | Avg ms | Min ms | Max ms | P95 ms |", "| --- | --- | --- | --- | --- | --- | --- |"])
    for stat in perf.get("api_stats", []):
        lines.append(
            f"| {stat['step']} | {stat['calls']} | {stat['failures']} | {stat['avg_ms']:.1f} | {stat['min_ms']} | {stat['max_ms']} | {stat['p95_ms']:.1f} |",
        )
    lines.extend(
        [
            "",
            "### 최장 API 호출 top-N",
            "",
            "| miEventId | scenarioGroupId | step | elapsed ms | retry | pre-delete | trace 병목 stage |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ],
    )
    for row in perf.get("slowest", []):
        lines.append(
            f"| {row['mi_event_id']} | {row['scenario_group_id'] or '-'} | {row['step']} | {row['elapsed_ms']} | "
            f"{row['retried_create']} | {row['pre_deleted']} | {_bottleneck_stage(trace, int(row['mi_event_id']))} |",
        )
    lines.extend(["", "### Pipeline 실패 케이스", "", "| miEventId | eventTypeL2Id | action state | failed step | status code | reason |", "| --- | --- | --- | --- | --- | --- |"])
    failures = perf.get("failures", [])
    if failures:
        for row in failures:
            lines.append(f"| {row['mi_event_id']} | {row['event_type_l2_id']} | {row['initial_action_state'] or '-'} | {row['error_step'] or '-'} | {row['status_code'] or '-'} | {_cell(row['error_reason'] or '-')} |")
    else:
        lines.append("| - | - | - | - | - | 없음 |")
    return lines


def _render_trace_section(trace: Mapping[int, Any] | None) -> list[str]:
    lines = ["", "## Layer 3 MLflow trace 진단", ""]
    if not trace:
        return lines + ["- trace 없음: 원인 국소화 불가(trace 미수집 또는 tracing 비활성)"]
    for event_id, summary in trace.items():
        status = _get(summary, "status")
        detail = _get(summary, "detail")
        trace_id = _get(summary, "trace_id", None)
        lines.append(f"- miEventId={event_id}: **{status}** — {detail} (trace={trace_id or '-'})")
        spans = _get(summary, "spans", [])
        if not spans:
            continue
        lines.extend(
            [
                "",
                "| Span/stage | Type | Status | Latency ms | Prompt input excerpt | Output excerpt |",
                "| --- | --- | --- | --- | --- | --- |",
            ],
        )
        for span in spans:
            lines.append(
                "| "
                f"{_cell(_get(span, 'name'))} | {_cell(_get(span, 'span_type'))} | {_cell(_get(span, 'status'))} | "
                f"{_cell(_get(span, 'duration_ms'))} | {_cell(_get(span, 'inputs_excerpt', '-'))} | "
                f"{_cell(_get(span, 'outputs_excerpt', '-'))} |",
            )
    return lines


def _trace_link(trace: Mapping[int, Any] | None, event_id: int, target_type: Any) -> str:
    """Link a violation to the most relevant observed stage without claiming causality."""
    summary = (trace or {}).get(event_id)
    if summary is None:
        return "trace unavailable"
    if _get(summary, "status") != "PASS":
        return str(_get(summary, "detail"))
    target = str(target_type).lower()
    keywords = ("signpost",) if "signpost" in target else ("scenario", "validation", "create")
    spans = _get(summary, "spans", [])
    selected = next((span for span in spans if any(word in str(_get(span, "name", "")).lower() for word in keywords)), None)
    if selected is None:
        selected = next(iter(spans), None)
    if selected is None:
        return "trace has no spans"
    return f"observed stage={_get(selected, 'name')}; prompt/output excerpts in Layer 3 table (association, not proven cause)"


def _bottleneck_stage(trace: Mapping[int, Any] | None, event_id: int) -> str:
    """State only the largest observed span; trace absence is never a performance inference."""
    summary = (trace or {}).get(event_id)
    if summary is None:
        return "trace 없음: 원인 국소화 불가"
    if _get(summary, "status") != "PASS":
        return _cell(_get(summary, "detail"))
    spans = _get(summary, "spans", [])
    durations = [span for span in spans if isinstance(_get(span, "duration_ms", None), (int, float))]
    if not durations:
        return "trace spans에 latency 없음"
    span = max(durations, key=lambda item: float(_get(item, "duration_ms")))
    return f"{_get(span, 'name')} ({float(_get(span, 'duration_ms')):.1f}ms)"


def _batch_verdict(checks: list[Any], scores: list[Any]) -> str:
    if any(_get(check, "status") == "FAIL" for check in checks):
        return "FAIL"
    if any(_has_external_fact(score) for score in scores):
        return "NEEDS_FACT"
    average = _average([_get(score, "score") for score in scores], numeric=True)
    if average is not None and average < 3:
        return "FAIL"
    if any(_get(check, "status") == "WARN" for check in checks) or any(_get(score, "verdict") == "WARN" for score in scores):
        return "WARN"
    return "PASS" if checks or scores else "INFRA_FAIL"


def _judge_items(value: Any) -> list[Any]:
    values = value if isinstance(value, Iterable) and not isinstance(value, (str, bytes, Mapping)) else [value]
    return [item for result in values for item in _get(result, "items", [])]


def _has_external_fact(item: Any) -> bool:
    return any(_get(violation, "fact_dependency") == "EXTERNAL_FACT_REQUIRED" for violation in _get(item, "violations", []))


def _get(value: Any, name: str, default: Any = "-") -> Any:
    if isinstance(value, Mapping):
        return value.get(name, default)
    return getattr(value, name, default)


def _cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", "<br>")


def _percentile(values: list[int], quantile: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower, upper = math.floor(position), math.ceil(position)
    return float(ordered[lower] if lower == upper else ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower))


def _average(values: list[Any], *, numeric: bool = False) -> str | float | None:
    numbers = [float(value) for value in values if isinstance(value, (int, float))]
    if not numbers:
        return None if numeric else "N/A"
    average = sum(numbers) / len(numbers)
    return average if numeric else f"{average:.2f}"


def _rate(items: list[Mapping[str, Any]]) -> str:
    if not items:
        return "N/A"
    return f"{sum(_get(item, 'verdict') == 'PASS' for item in items)}/{len(items)} ({sum(_get(item, 'verdict') == 'PASS' for item in items) / len(items):.0%})"
