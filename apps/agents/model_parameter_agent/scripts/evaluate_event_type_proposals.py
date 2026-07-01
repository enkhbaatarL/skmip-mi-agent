from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select

ROOT_DIR = Path(__file__).resolve().parents[4]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
DEFAULT_APP_CONFIG = ROOT_DIR / "envs" / "config.yaml"
DEFAULT_DOTENV = ROOT_DIR / "envs" / ".env"
if DEFAULT_DOTENV.exists():
    from dotenv import load_dotenv

    load_dotenv(DEFAULT_DOTENV, override=False)
if "APP_CONFIG" not in os.environ and DEFAULT_APP_CONFIG.exists():
    os.environ["APP_CONFIG"] = str(DEFAULT_APP_CONFIG)

from apps.agents.event_flow_agent.models.mi_event_models_orm import MiEventTypeL2Model
from apps.agents.model_parameter_agent.scripts.evaluate_proposals import (
    _evaluate_scenario,
    _json_pretty,
    _json_preview,
    _llm_call_table_lines,
    _selected_adjustments,
)
from apps.agents.scenario_group_agent.persistence.scenario.models import MiScenarioModel
from apps.agents.scenario_group_agent.persistence.scenario_group.models import (
    MiScenarioGroupModel,
)
from apps.common.configs.database.sync_database.connection import get_sync_session


REPORT_DIR = Path(__file__).resolve().parents[1] / "reports"


def _format_duration(seconds: float | None) -> str:
    if seconds is None:
        return "N/A"
    total_ms = int(round(max(0.0, seconds) * 1000))
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    whole_seconds, milliseconds = divmod(remainder, 1000)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{whole_seconds:02d}.{milliseconds:03d}"
    return f"{minutes:02d}:{whole_seconds:02d}.{milliseconds:03d}"


def _format_seconds(seconds: float | None) -> str:
    if seconds is None:
        return "N/A"
    return f"{seconds:.3f}s"


def _proposal_parameters(final_response: dict[str, Any]) -> list[dict[str, Any]]:
    data = final_response.get("data") or {}
    if "proposalParameters" in data:
        return data.get("proposalParameters") or []
    return final_response.get("recommendations") or []


@dataclass(frozen=True)
class EventTypeTarget:
    event_type_l2_id: int
    event_type_label: str
    scenario_group_id: int
    group_title: str
    scenario_ids: tuple[int, ...]


def _discover_targets(
    event_type_l2_ids: tuple[int, ...],
    *,
    group_title_prefix: str | None = None,
    groups_per_event: int | None = None,
    scenarios_per_group: int | None = None,
) -> tuple[EventTypeTarget, ...]:
    session = get_sync_session()
    try:
        label_stmt = select(
            MiEventTypeL2Model.event_type_l2_id,
            MiEventTypeL2Model.level_2_label,
        ).where(MiEventTypeL2Model.del_yn == "N")
        if event_type_l2_ids:
            label_stmt = label_stmt.where(
                MiEventTypeL2Model.event_type_l2_id.in_(event_type_l2_ids),
            )
        label_rows = session.execute(
            label_stmt.order_by(MiEventTypeL2Model.event_type_l2_id),
        ).all()
        labels = {int(row[0]): str(row[1] or "") for row in label_rows}
        selected_event_type_l2_ids = tuple(sorted(labels))

        group_stmt = (
            select(
                MiScenarioGroupModel.event_type_l2_id,
                MiScenarioGroupModel.scenario_group_id,
                MiScenarioGroupModel.title,
            )
            .where(
                MiScenarioGroupModel.del_yn == "N",
            )
        )
        if selected_event_type_l2_ids:
            group_stmt = group_stmt.where(
                MiScenarioGroupModel.event_type_l2_id.in_(selected_event_type_l2_ids),
            )
        if group_title_prefix:
            group_stmt = group_stmt.where(
                MiScenarioGroupModel.title.like(f"{group_title_prefix}%"),
            )
        groups = session.execute(
            group_stmt.order_by(
                MiScenarioGroupModel.event_type_l2_id,
                MiScenarioGroupModel.scenario_group_id,
            ),
        ).all()

        scenario_stmt = (
            select(
                MiScenarioModel.scenario_group_id,
                MiScenarioModel.scenario_id,
            )
            .join(
                MiScenarioGroupModel,
                MiScenarioGroupModel.scenario_group_id == MiScenarioModel.scenario_group_id,
            )
            .where(
                MiScenarioGroupModel.del_yn == "N",
                MiScenarioModel.del_yn == "N",
            )
        )
        if selected_event_type_l2_ids:
            scenario_stmt = scenario_stmt.where(
                MiScenarioGroupModel.event_type_l2_id.in_(selected_event_type_l2_ids),
            )
        if group_title_prefix:
            scenario_stmt = scenario_stmt.where(
                MiScenarioGroupModel.title.like(f"{group_title_prefix}%"),
            )
        scenario_rows = session.execute(
            scenario_stmt.order_by(
                MiScenarioModel.scenario_group_id,
                MiScenarioModel.display_order,
                MiScenarioModel.scenario_id,
            ),
        ).all()
    finally:
        session.close()

    scenario_ids_by_group: dict[int, list[int]] = defaultdict(list)
    for scenario_group_id, scenario_id in scenario_rows:
        scenario_ids_by_group[int(scenario_group_id)].append(int(scenario_id))

    targets: list[EventTypeTarget] = []
    selected_group_count_by_event: dict[int, int] = defaultdict(int)
    for event_type_l2_id, scenario_group_id, title in groups:
        event_type_l2_id = int(event_type_l2_id)
        scenario_group_id = int(scenario_group_id)
        scenario_ids = tuple(scenario_ids_by_group.get(scenario_group_id, []))
        if scenarios_per_group is not None and len(scenario_ids) < scenarios_per_group:
            continue
        if groups_per_event is not None and selected_group_count_by_event[event_type_l2_id] >= groups_per_event:
            continue
        if scenarios_per_group is not None:
            scenario_ids = scenario_ids[:scenarios_per_group]
        targets.append(
            EventTypeTarget(
                event_type_l2_id=event_type_l2_id,
                event_type_label=labels.get(event_type_l2_id, ""),
                scenario_group_id=scenario_group_id,
                group_title=str(title or ""),
                scenario_ids=scenario_ids,
            ),
        )
        selected_group_count_by_event[event_type_l2_id] += 1
    return tuple(targets)


def _signature(record: dict[str, Any]) -> str:
    selected = _selected_adjustments(record["result"])
    comparable: list[dict[str, Any]] = []
    for adjustment in selected:
        comparable.append(
            {
                "candidate_key": adjustment.get("candidate_key"),
                "parameter_name": adjustment.get("parameter_name"),
                "value_grid": [
                    {
                        "coordinates": cell.get("coordinates") or {},
                        "proposed_value": cell.get("proposed_value"),
                        "operation": cell.get("operation"),
                    }
                    for cell in adjustment.get("value_grid") or []
                ],
            },
        )
    return json.dumps(comparable, ensure_ascii=False, sort_keys=True, default=str)


def _db_load_summary(context: dict[str, Any]) -> dict[str, Any]:
    scenario = context.get("scenario") or {}
    group = context.get("scenario_group") or {}
    event = context.get("event") or {}
    event_type = context.get("event_type") or {}
    dimension_template = context.get("dimension_template") or []
    return {
        "scenario": {
            "scenario_id": scenario.get("scenario_id"),
            "scenario_group_id": scenario.get("scenario_group_id"),
            "title": scenario.get("title"),
            "probability_score": scenario.get("probability_score"),
            "impact": scenario.get("impact"),
            "baseline_yn": scenario.get("baseline_yn"),
        },
        "scenario_group": {
            "scenario_group_id": group.get("scenario_group_id"),
            "mi_event_id": group.get("mi_event_id"),
            "event_type_l2_id": group.get("event_type_l2_id"),
            "title": group.get("title"),
            "dimension_selected": group.get("dimension_selected"),
            "scenario_count": group.get("scenario_count"),
            "status": group.get("status"),
            "stage": group.get("stage"),
        },
        "event": {
            "mi_event_id": event.get("mi_event_id"),
            "event_type_l2_id": event.get("event_type_l2_id"),
            "event_title_ko": event.get("event_title_ko"),
            "one_line_summary": event.get("one_line_summary"),
            "occurred_at": event.get("occurred_at"),
            "created_at": event.get("created_at"),
            "latest_record_first_created": event.get("latest_record_first_created"),
            "oldest_record_first_created": event.get("oldest_record_first_created"),
            "source_mi_record_ids": event.get("source_mi_record_ids"),
            "key_bullets": event.get("key_bullets"),
            "detail_analysis_preview": str(event.get("detail_analysis") or "")[:500],
            "detail_analysis_chars": len(str(event.get("detail_analysis") or "")),
            "key_bullet_count": len(event.get("key_bullets") or []),
            "tag_count": len(event.get("tags") or []),
        },
        "event_type": event_type,
        "dimension_template": [
            {
                "dim_key": item.get("dim_key"),
                "label": item.get("label"),
                "required": item.get("required"),
                "value_count": len(item.get("value_enums") or []),
            }
            for item in dimension_template
            if isinstance(item, dict)
        ],
    }


def _group_status(target: EventTypeTarget, records: list[dict[str, Any]], errors: list[dict[str, Any]]) -> bool:
    group_records = [
        record
        for record in records
        if record["target"].scenario_group_id == target.scenario_group_id
    ]
    group_errors = [
        error
        for error in errors
        if error["target"].scenario_group_id == target.scenario_group_id
    ]
    has_expected = any(record["expected_candidates"] for record in group_records)
    has_selected = any(_selected_adjustments(record["result"]) for record in group_records)
    value_diff_ok = (
        len(group_records) <= 1
        or not has_expected
        or not has_selected
        or len({_signature(record) for record in group_records}) > 1
    )
    return (
        not group_errors
        and len(group_records) == len(target.scenario_ids)
        and all(record["mapping_ok"] for record in group_records)
        and all(record["selected_ok"] for record in group_records)
        and all(record["routing_status"] != "REVIEW" for record in group_records)
        and value_diff_ok
    )


def _render_report(
    *,
    started_at: datetime,
    finished_at: datetime,
    event_type_l2_ids: tuple[int, ...],
    targets: tuple[EventTypeTarget, ...],
    records: list[dict[str, Any]],
    errors: list[dict[str, Any]],
    concurrency: int,
    retries: int,
) -> str:
    event_group_count: dict[int, int] = defaultdict(int)
    event_scenario_count: dict[int, int] = defaultdict(int)
    for target in targets:
        event_group_count[target.event_type_l2_id] += 1
        event_scenario_count[target.event_type_l2_id] += len(target.scenario_ids)

    lines: list[str] = [
        "# Model Parameter Proposal Evaluation - Event Types",
        "",
        f"- 실행 시작: {started_at.isoformat(timespec='seconds')}",
        f"- 실행 종료: {finished_at.isoformat(timespec='seconds')}",
        f"- 총 소요시간: {_format_duration((finished_at - started_at).total_seconds())} ({_format_seconds((finished_at - started_at).total_seconds())})",
        f"- 대상 event_type_l2_ids: {list(event_type_l2_ids)}",
        f"- concurrency: {concurrency}",
        f"- retries: {retries}",
        "- 대상 수집 방식: midb의 scenario_group/scenario를 event_type_l2_id 기준으로 동적 조회",
        "- 호출 방식: 내부 raw graph 실행 후 `to_output()`으로 final response 생성",
        "",
        "## 대상 요약",
        "",
    ]
    for event_type_l2_id in event_type_l2_ids:
        label = next(
            (target.event_type_label for target in targets if target.event_type_l2_id == event_type_l2_id),
            "",
        )
        lines.append(
            f"- event_type_l2_id={event_type_l2_id} {label}: "
            f"scenario_group {event_group_count[event_type_l2_id]}개, "
            f"scenario {event_scenario_count[event_type_l2_id]}개",
        )

    elapsed_rows: list[tuple[int, int, int, str, int | str, float | None]] = []
    for record in records:
        target = record["target"]
        elapsed_rows.append(
            (
                int(target.event_type_l2_id),
                int(target.scenario_group_id),
                int(record["scenario_id"]),
                "OK",
                int(record.get("attempt") or 1),
                record.get("elapsed_seconds"),
            ),
        )
    for error in errors:
        target = error["target"]
        elapsed_rows.append(
            (
                int(target.event_type_l2_id),
                int(target.scenario_group_id),
                int(error["scenario_id"]),
                "ERROR",
                int(error.get("attempts") or retries + 1),
                error.get("elapsed_seconds"),
            ),
        )
    if elapsed_rows:
        lines.extend(
            [
                "",
                "## 시나리오별 소요시간",
                "",
                "| event_type_l2_id | scenario_group_id | scenario_id | status | attempts | 소요시간 | elapsed_seconds |",
                "|---:|---:|---:|---|---:|---:|---:|",
            ],
        )
        for event_type_l2_id, scenario_group_id, scenario_id, status, attempts, elapsed_seconds in sorted(
            elapsed_rows,
            key=lambda item: (item[0], item[1], item[2]),
        ):
            lines.append(
                f"| {event_type_l2_id} | {scenario_group_id} | {scenario_id} | {status} | "
                f"{attempts} | {_format_duration(elapsed_seconds)} | {_format_seconds(elapsed_seconds)} |",
            )

    lines.extend(["", "## 호출 결과", ""])

    records_by_group: dict[int, list[dict[str, Any]]] = defaultdict(list)
    errors_by_group: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        records_by_group[int(record["target"].scenario_group_id)].append(record)
    for error in errors:
        errors_by_group[int(error["target"].scenario_group_id)].append(error)

    for target in targets:
        group_records = sorted(
            records_by_group.get(target.scenario_group_id, []),
            key=lambda item: item["scenario_id"],
        )
        group_errors = errors_by_group.get(target.scenario_group_id, [])
        signatures = {_signature(record) for record in group_records}
        has_expected = any(record["expected_candidates"] for record in group_records)
        has_selected = any(_selected_adjustments(record["result"]) for record in group_records)
        value_diff_status = "N/A"
        if len(group_records) > 1 and has_expected and has_selected:
            value_diff_status = "PASS" if len(signatures) > 1 else "FAIL"
        group_ok = _group_status(target, records, errors)
        lines.extend(
            [
                f"### event_type_l2_id={target.event_type_l2_id} {target.event_type_label}",
                "",
                f"- scenario_group_id: {target.scenario_group_id}",
                f"- group_title: {target.group_title}",
                f"- 대상 scenario_ids: {list(target.scenario_ids)}",
                f"- scenario_count: {len(target.scenario_ids)}",
                f"- 매핑 후보 검증: {'PASS' if all(record['mapping_ok'] for record in group_records) and not group_errors else 'FAIL'}",
                f"- LLM selected 검증: {'PASS' if all(record['selected_ok'] for record in group_records) and not group_errors else 'FAIL'}",
                f"- 라우팅 선택 검증: {', '.join(sorted({record['routing_status'] for record in group_records})) if group_records else 'N/A'}",
                f"- scenario별 value 차이: {value_diff_status}",
                f"- 그룹 종합: {'PASS' if group_ok else 'FAIL'}",
                "",
            ],
        )
        for error in group_errors:
            lines.append(
                f"- ERROR scenario_id={error['scenario_id']} "
                f"elapsed={_format_duration(error.get('elapsed_seconds'))} "
                f"({_format_seconds(error.get('elapsed_seconds'))}): `{error['error']}`",
            )
        if group_errors:
            lines.append("")

        for record in group_records:
            context = record["context"]
            scenario = context.get("scenario") or {}
            expected_names = [
                candidate.get("canonical_parameter_name") or candidate.get("parameter_name")
                for candidate in record["expected_candidates"]
            ]
            selected = _selected_adjustments(record["result"])
            actual_names = [adjustment.get("parameter_name") for adjustment in selected]
            lines.extend(
                [
                    f"#### scenario_id={record['scenario_id']} {scenario.get('title') or ''}",
                    "",
                    f"- 소요시간: {_format_duration(record.get('elapsed_seconds'))} ({_format_seconds(record.get('elapsed_seconds'))})",
                    f"- attempt: {record.get('attempt') or 1}",
                    f"- db_loaded_context: `{_json_preview(_db_load_summary(context), max_chars=1400)}`",
                    f"- dimension_values: `{_json_preview(scenario.get('dimension_values') or {})}`",
                    f"- expected_parameters: `{_json_preview(expected_names)}`",
                    f"- selected_parameters: `{_json_preview(actual_names)}`",
                    f"- mapping_candidate_coverage: {'PASS' if record['mapping_ok'] else 'FAIL'}",
                    f"- selected_result: {'PASS' if record['selected_ok'] else 'FAIL'}",
                    f"- routing_result: {record['routing_status']}",
                ],
            )
            if record["mapping_messages"]:
                lines.append(f"- mapping_messages: `{_json_preview(record['mapping_messages'])}`")
            if record["selected_messages"]:
                lines.append(f"- selected_messages: `{_json_preview(record['selected_messages'])}`")
            if record["routing_messages"]:
                lines.append(f"- routing_messages: `{_json_preview(record['routing_messages'])}`")
            if record["mapping_warnings"]:
                lines.append(f"- mapping_warnings: `{_json_preview(record['mapping_warnings'])}`")
            lines.extend(_llm_call_table_lines(record.get("llm_calls") or []))
            lines.extend(
                [
                    "<details>",
                    "<summary>final response JSON</summary>",
                    "",
                    "```json",
                    _json_pretty(record["final_response"]),
                    "```",
                    "",
                    "</details>",
                    "",
                ],
            )

    group_status = {
        str(target.scenario_group_id): _group_status(target, records, errors)
        for target in targets
    }
    empty_recommendation_records = [
        {
            "scenario_group_id": record["target"].scenario_group_id,
            "scenario_id": record["scenario_id"],
            "title": (record["context"].get("scenario") or {}).get("title"),
        }
        for record in sorted(records, key=lambda item: (item["target"].scenario_group_id, item["scenario_id"]))
        if not _proposal_parameters(record["final_response"])
    ]
    lines.extend(
        [
            "## 최종 요약",
            "",
            f"- ERROR_COUNT: {len(errors)}",
            f"- GROUP_STATUS_BY_SCENARIO_GROUP: `{json.dumps(group_status, ensure_ascii=False, sort_keys=True)}`",
            f"- EMPTY_RECOMMENDATIONS: {len(empty_recommendation_records)}",
            f"- EMPTY_RECOMMENDATION_SCENARIOS: `{_json_preview(empty_recommendation_records, max_chars=1200)}`",
            "",
            "## 오류 및 반복 이력",
            "",
        ],
    )
    if errors:
        for error in errors:
            lines.append(
                f"- scenario_id={error['scenario_id']} "
                f"elapsed={_format_duration(error.get('elapsed_seconds'))} "
                f"({_format_seconds(error.get('elapsed_seconds'))}) "
                f"attempts={error.get('attempts')} error=`{error['error']}`",
            )
    else:
        lines.append("- 오류 없음. 1회 실행으로 완료.")
    lines.append("")
    return "\n".join(lines)


async def run_event_type_evaluation(
    *,
    event_type_l2_ids: tuple[int, ...],
    max_candidates: int,
    allow_llm_fallback: bool,
    concurrency: int,
    retries: int,
    group_title_prefix: str | None = None,
    groups_per_event: int | None = None,
    scenarios_per_group: int | None = None,
) -> Path:
    targets = _discover_targets(
        event_type_l2_ids,
        group_title_prefix=group_title_prefix,
        groups_per_event=groups_per_event,
        scenarios_per_group=scenarios_per_group,
    )
    report_event_type_l2_ids = (
        event_type_l2_ids
        or tuple(sorted({target.event_type_l2_id for target in targets}))
    )
    started_at = datetime.now()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    event_id_part = "_".join(str(item) for item in report_event_type_l2_ids) or "none"
    report_path = REPORT_DIR / (
        f"model_parameter_proposal_evaluation_event_types_{event_id_part}_"
        f"{started_at.strftime('%Y%m%d_%H%M%S')}.md"
    )
    records: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    semaphore = asyncio.Semaphore(max(1, concurrency))

    def write_report(finished_at: datetime | None = None) -> None:
        report_path.write_text(
            _render_report(
                started_at=started_at,
                finished_at=finished_at or datetime.now(),
                event_type_l2_ids=report_event_type_l2_ids,
                targets=targets,
                records=sorted(records, key=lambda item: (item["target"].scenario_group_id, item["scenario_id"])),
                errors=sorted(errors, key=lambda item: (item["target"].scenario_group_id, item["scenario_id"])),
                concurrency=concurrency,
                retries=retries,
            ),
            encoding="utf-8",
        )

    async def run_one(target: EventTypeTarget, scenario_id: int) -> None:
        async with semaphore:
            last_error: Exception | None = None
            scenario_started_at = datetime.now()
            scenario_started_monotonic = time.perf_counter()
            for attempt in range(retries + 1):
                try:
                    result = await _evaluate_scenario(
                        scenario_id,
                        max_candidates=max_candidates,
                        allow_llm_fallback=allow_llm_fallback,
                    )
                    elapsed_seconds = time.perf_counter() - scenario_started_monotonic
                    result["target"] = target
                    result["attempt"] = attempt + 1
                    result["started_at"] = scenario_started_at.isoformat(timespec="seconds")
                    result["finished_at"] = datetime.now().isoformat(timespec="seconds")
                    result["elapsed_seconds"] = elapsed_seconds
                    records.append(result)
                    print(
                        "OK",
                        target.event_type_l2_id,
                        target.scenario_group_id,
                        scenario_id,
                        "attempt=",
                        attempt + 1,
                        "elapsed=",
                        _format_duration(elapsed_seconds),
                    )
                    break
                except Exception as exc:  # noqa: BLE001
                    last_error = exc
                    if attempt < retries:
                        delay = 2.0 * (attempt + 1)
                        print(
                            "RETRY",
                            target.event_type_l2_id,
                            target.scenario_group_id,
                            scenario_id,
                            "attempt=",
                            attempt + 1,
                            "delay_sec=",
                            delay,
                            repr(exc),
                        )
                        await asyncio.sleep(delay)
                        continue
                    elapsed_seconds = time.perf_counter() - scenario_started_monotonic
                    errors.append(
                        {
                            "target": target,
                            "scenario_id": scenario_id,
                            "error": repr(last_error),
                            "attempts": retries + 1,
                            "started_at": scenario_started_at.isoformat(timespec="seconds"),
                            "finished_at": datetime.now().isoformat(timespec="seconds"),
                            "elapsed_seconds": elapsed_seconds,
                        },
                    )
                    print(
                        "ERROR",
                        target.event_type_l2_id,
                        target.scenario_group_id,
                        scenario_id,
                        "elapsed=",
                        _format_duration(elapsed_seconds),
                        repr(last_error),
                    )
            write_report()
            print(
                "REPORT_UPDATED",
                report_path,
                "records=",
                len(records),
                "errors=",
                len(errors),
            )

    write_report()
    print("REPORT_IN_PROGRESS", report_path)
    await asyncio.gather(
        *(
            run_one(target, scenario_id)
            for target in targets
            for scenario_id in target.scenario_ids
        ),
    )
    write_report(finished_at=datetime.now())
    print("REPORT", report_path)
    print("ERROR_COUNT", len(errors))
    print(
        "GROUP_STATUS_BY_SCENARIO_GROUP",
        json.dumps(
            {
                str(target.scenario_group_id): _group_status(target, records, errors)
                for target in targets
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
    )
    return report_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event-type-l2-ids", nargs="+", type=int, default=())
    parser.add_argument("--all-event-types", action="store_true")
    parser.add_argument("--max-candidates", type=int, default=30)
    parser.add_argument("--allow-llm-fallback", action="store_true")
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--group-title-prefix", default=None)
    parser.add_argument("--groups-per-event", type=int, default=None)
    parser.add_argument("--scenarios-per-group", type=int, default=None)
    args = parser.parse_args()
    if not args.all_event_types and not args.event_type_l2_ids:
        parser.error("--event-type-l2-ids or --all-event-types is required")
    asyncio.run(
        run_event_type_evaluation(
            event_type_l2_ids=() if args.all_event_types else tuple(args.event_type_l2_ids),
            max_candidates=args.max_candidates,
            allow_llm_fallback=args.allow_llm_fallback,
            concurrency=args.concurrency,
            retries=args.retries,
            group_title_prefix=args.group_title_prefix,
            groups_per_event=args.groups_per_event,
            scenarios_per_group=args.scenarios_per_group,
        ),
    )


if __name__ == "__main__":
    main()
