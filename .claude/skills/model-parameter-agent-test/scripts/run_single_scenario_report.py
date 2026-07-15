#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_REPO_ROOT = Path("/Users/messiah/skg-mi/skmip-mi-agent")


def _status(record: dict[str, Any] | None, error: str | None) -> str:
    if error:
        return "ERROR"
    if not record:
        return "ERROR"
    if not record.get("mapping_ok") or not record.get("selected_ok"):
        return "FAIL"
    if record.get("routing_status") == "REVIEW":
        return "REVIEW"
    return "PASS"


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, default=str)


def _json_preview(value: Any, *, max_chars: int = 1200) -> str:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    return text if len(text) <= max_chars else text[:max_chars] + "..."


def _names(items: list[dict[str, Any]], *, selected_only: bool = False) -> list[str]:
    result: list[str] = []
    for item in items:
        if selected_only and item.get("selected", True) is False:
            continue
        name = (
            item.get("canonical_parameter_name")
            or item.get("parameter_name")
            or item.get("parameterName")
        )
        if name:
            result.append(str(name))
    return result


def _summarize_long_text(value: str, *, max_chars: int = 1200) -> str | dict[str, Any]:
    if len(value) <= max_chars:
        return value
    return {
        "text_chars": len(value),
        "text_excerpt": value[:max_chars].rstrip(),
    }


def _summarize_large_text_fields(value: Any, *, max_chars: int = 1200) -> Any:
    if isinstance(value, str):
        return _summarize_long_text(value, max_chars=max_chars)
    if isinstance(value, list):
        return [
            _summarize_large_text_fields(item, max_chars=max_chars)
            for item in value
        ]
    if isinstance(value, dict):
        return {
            str(key): _summarize_large_text_fields(item, max_chars=max_chars)
            for key, item in value.items()
        }
    return value


def _prompt_source_context(context: dict[str, Any]) -> dict[str, Any]:
    from apps.agents.model_parameter_agent.flows.propose_parameters.nodes import (  # noqa: PLC0415
        _scenario_brief_for_value_prompt,
    )

    return _scenario_brief_for_value_prompt(context)


def _dimension_context(context: dict[str, Any]) -> dict[str, Any]:
    scenario = context.get("scenario") or {}
    event = context.get("event") or {}
    event_type = context.get("event_type") or {}
    group = context.get("scenario_group") or {}
    return {
        "db_loaded_context": {
            "scenario": {
                "scenario_id": scenario.get("scenario_id"),
                "scenario_group_id": scenario.get("scenario_group_id"),
                "title": scenario.get("title"),
                "narrative": _summarize_large_text_fields(scenario.get("narrative")),
                "status": scenario.get("status"),
                "dimension_values": scenario.get("dimension_values") or {},
                "probability_score": scenario.get("probability_score"),
                "probability_delta": scenario.get("probability_delta"),
                "impact": scenario.get("impact"),
                "baseline_yn": scenario.get("baseline_yn"),
            },
            "scenario_group": {
                "scenario_group_id": group.get("scenario_group_id"),
                "mi_event_id": group.get("mi_event_id"),
                "event_type_l2_id": group.get("event_type_l2_id"),
                "title": group.get("title"),
                "summary": _summarize_large_text_fields(group.get("summary")),
                "description": _summarize_large_text_fields(group.get("description")),
                "dimension_selected": group.get("dimension_selected") or [],
                "scenario_count": group.get("scenario_count"),
                "status": group.get("status"),
                "stage": group.get("stage"),
            },
            "event_type": event_type,
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
                "key_bullets": event.get("key_bullets") or [],
                "tags": event.get("tags") or [],
                "detail_analysis": _summarize_large_text_fields(
                    event.get("detail_analysis") or "",
                ),
            },
            "dimension_template": context.get("dimension_template") or [],
        },
        "prompt_source_context": _summarize_large_text_fields(
            _prompt_source_context(context),
        ),
    }


def _scenario_group_context(context: dict[str, Any]) -> dict[str, Any]:
    group = context.get("scenario_group") or {}
    return {
        "scenario_group_id": group.get("scenario_group_id"),
        "mi_event_id": group.get("mi_event_id"),
        "event_type_l2_id": group.get("event_type_l2_id"),
        "request_usr_id": group.get("request_usr_id"),
        "title": group.get("title"),
        "summary": _summarize_large_text_fields(group.get("summary")),
        "description": _summarize_large_text_fields(group.get("description")),
        "dimension_selected": group.get("dimension_selected") or [],
        "scenario_count": group.get("scenario_count"),
        "status": group.get("status"),
        "stage": group.get("stage"),
        "event_type": context.get("event_type") or {},
    }


def _event_type_l2_id(context: dict[str, Any]) -> int | None:
    group = context.get("scenario_group") or {}
    event = context.get("event") or {}
    event_type = context.get("event_type") or {}
    for raw in (
        group.get("event_type_l2_id"),
        event.get("event_type_l2_id"),
        event_type.get("event_type_l2_id"),
    ):
        if raw is None:
            continue
        try:
            return int(raw)
        except (TypeError, ValueError):
            continue
    return None


def _parameter_definitions_by_name(context: dict[str, Any]) -> dict[str, dict[str, Any]]:
    resources = context.get("parameter_mapping_resources") or {}
    definitions = resources.get("parameter_definitions") or []
    by_name: dict[str, dict[str, Any]] = {}
    for definition in definitions:
        if not isinstance(definition, dict):
            continue
        name = str(
            definition.get("canonical_parameter_name")
            or definition.get("parameter_name")
            or "",
        ).strip()
        if name:
            by_name[name] = definition
    return by_name


def _mapping_usage_policy(mapping_method: Any) -> str:
    method = str(mapping_method or "").lower()
    if method in {"direct", "routing"}:
        return "direct_parameter_candidate_context"
    if method == "indirect":
        return "supporting_context_only_when_allowed"
    if method == "na":
        return "excluded_from_parameter_slot_value_prompt"
    return "unknown"


def _scenario_dimension_values_by_scenario(
    scenario_contexts: list[dict[str, Any]],
    dimension_key: str,
) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    for scenario_context in scenario_contexts:
        scenario = scenario_context.get("scenario") or {}
        dimension_values = scenario.get("dimension_values") or {}
        values.append(
            {
                "scenario_id": scenario.get("scenario_id"),
                "dimension_value": dimension_values.get(dimension_key),
                "selected_in_scenario": dimension_key in dimension_values,
            },
        )
    return values


def _dimension_parameter_mapping_context(
    context: dict[str, Any],
    _scenario_contexts: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    event_type_l2_id = _event_type_l2_id(context)
    resources = context.get("parameter_mapping_resources") or {}
    mapping_rules = resources.get("mapping_rules") or []

    rows: list[dict[str, Any]] = []
    for rule in mapping_rules:
        if not isinstance(rule, dict):
            continue
        try:
            rule_event_type_l2_id = int(rule.get("event_type_l2_id"))
        except (TypeError, ValueError):
            continue
        if event_type_l2_id is not None and rule_event_type_l2_id != event_type_l2_id:
            continue

        parameter_name = str(rule.get("canonical_parameter_name") or "").strip()
        dimension_key = str(rule.get("dimension_key") or "")
        dimension_label = str(rule.get("dimension_label") or "").strip()
        dimension = (
            f"{dimension_key} ({dimension_label})"
            if dimension_label and dimension_label != dimension_key
            else dimension_key
        )
        rows.append(
            {
                "dimension": dimension,
                "mapping_method": rule.get("mapping_method"),
                "parameter": parameter_name or None,
                "comment": rule.get("comment"),
            },
        )

    rows.sort(
        key=lambda item: (
            str(item.get("dimension") or ""),
            str(item.get("mapping_method") or ""),
            str(item.get("parameter") or ""),
        ),
    )
    return {
        "source_tables": [
            "tmm_mi_model_param_dimension_map",
            "tmm_mi_model_param_m",
        ],
        "event_type_l2_id": event_type_l2_id,
        "mapping_count": len(rows),
        "dimension_parameter_mappings": rows,
    }


def _event_context(context: dict[str, Any]) -> dict[str, Any]:
    event = context.get("event") or {}
    return {
        "mi_event_id": event.get("mi_event_id"),
        "event_type_l2_id": event.get("event_type_l2_id"),
        "event_title_ko": event.get("event_title_ko"),
        "one_line_summary": event.get("one_line_summary"),
        "occurred_at": event.get("occurred_at"),
        "created_at": event.get("created_at"),
        "latest_record_first_created": event.get("latest_record_first_created"),
        "oldest_record_first_created": event.get("oldest_record_first_created"),
        "source_mi_record_ids": event.get("source_mi_record_ids"),
        "key_bullets": event.get("key_bullets") or [],
        "tags": event.get("tags") or [],
        "detail_analysis": _summarize_large_text_fields(
            event.get("detail_analysis") or "",
            max_chars=1600,
        ),
    }


def _scenario_context(context: dict[str, Any]) -> dict[str, Any]:
    scenario = context.get("scenario") or {}
    return {
        "scenario_id": scenario.get("scenario_id"),
        "scenario_group_id": scenario.get("scenario_group_id"),
        "title": scenario.get("title"),
        "narrative": _summarize_large_text_fields(
            scenario.get("narrative") or "",
            max_chars=1600,
        ),
        "status": scenario.get("status"),
        "dimension_values": scenario.get("dimension_values") or {},
        "probability_score": scenario.get("probability_score"),
        "probability_delta": scenario.get("probability_delta"),
        "impact": scenario.get("impact"),
        "baseline_yn": scenario.get("baseline_yn"),
    }


def _proposal_id(final_response: dict[str, Any]) -> int | None:
    data = final_response.get("data") or {}
    raw = data.get("modelParamProposalId") or data.get("model_param_proposal_id")
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _fetch_proposal_db_row(model_param_proposal_id: int | None) -> dict[str, Any]:
    if model_param_proposal_id is None:
        return {}
    from sqlalchemy import select  # noqa: PLC0415

    from apps.common.configs.database.sync_database.connection import (  # noqa: PLC0415
        get_sync_session,
    )
    from apps.persistence.model_parameter.models import (  # noqa: PLC0415
        MiModelParamProposalModel,
    )

    session = get_sync_session()
    try:
        stmt = select(MiModelParamProposalModel).where(
            MiModelParamProposalModel.model_param_proposal_id == model_param_proposal_id,
            MiModelParamProposalModel.del_yn == "N",
        )
        proposal = session.execute(stmt).scalars().one_or_none()
        if proposal is None:
            return {
                "model_param_proposal_id": model_param_proposal_id,
                "fetch_status": "NOT_FOUND",
            }
        return {
            "model_param_proposal_id": int(proposal.model_param_proposal_id),
            "scenario_id": int(proposal.scenario_id),
            "scenario_group_id": int(proposal.scenario_group_id),
            "mi_event_id": int(proposal.mi_event_id),
            "request_usr_id": (
                int(proposal.request_usr_id)
                if proposal.request_usr_id is not None
                else None
            ),
            "status": proposal.status,
            "callback_status": proposal.callback_status,
            "proposal_completed_dtm": proposal.proposal_completed_dtm,
            "callback_sent_dtm": proposal.callback_sent_dtm,
            "confirmed_dtm": proposal.confirmed_dtm,
            "error_code": proposal.error_code,
            "error_message": proposal.error_message,
            "proposal_parameters": proposal.proposal_parameters or [],
            "confirmation_parameters": proposal.confirmation_parameters,
        }
    finally:
        session.close()


def _proposal_parameters_for_report(
    proposal_row: dict[str, Any],
    final_response: dict[str, Any],
) -> list[dict[str, Any]]:
    db_parameters = proposal_row.get("proposal_parameters")
    if isinstance(db_parameters, list):
        return db_parameters
    data = final_response.get("data") or {}
    parameters = data.get("proposalParameters") or data.get("proposal_parameters") or []
    return parameters if isinstance(parameters, list) else []


def _model_target(parameter: dict[str, Any]) -> dict[str, Any]:
    target = parameter.get("modelTarget") or parameter.get("model_target") or {}
    return target if isinstance(target, dict) else {}


def _parameter_name(parameter: dict[str, Any]) -> str:
    return str(parameter.get("parameterName") or parameter.get("parameter_name") or "")


def _parameter_values(parameter: dict[str, Any]) -> list[dict[str, Any]]:
    values = parameter.get("values") or []
    return values if isinstance(values, list) else []


def _slot_axis_field_names(parameter: dict[str, Any]) -> list[str]:
    target = _model_target(parameter)
    raw = (
        target.get("slotAxesFieldNames")
        or target.get("slot_axes_field_names")
        or []
    )
    return [str(item) for item in raw] if isinstance(raw, list) else []


def _value_field_names(parameter: dict[str, Any]) -> list[str]:
    target = _model_target(parameter)
    raw = target.get("valueFieldNames") or target.get("value_field_names") or []
    return [str(item) for item in raw] if isinstance(raw, list) else []


def _slot_coordinates_for_value(
    parameter: dict[str, Any],
    value: dict[str, Any],
) -> dict[str, Any]:
    axes = _slot_axis_field_names(parameter)
    return {
        axis: value.get(axis)
        for axis in axes
        if axis in value
    }


def _md_cell(value: Any, *, max_chars: int = 500) -> str:
    if isinstance(value, str):
        text = value
    else:
        text = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    if len(text) > max_chars:
        text = text[:max_chars].rstrip() + "..."
    return text.replace("\n", "<br>").replace("|", "\\|")


def _proposal_parameter_table_lines(parameters: list[dict[str, Any]]) -> list[str]:
    if not parameters:
        return ["- 제안 파라미터 없음."]
    lines = [
        "| No | parameterName | modelTarget | slot axes | value fields | values | rationale |",
        "|---:|---|---|---|---|---:|---|",
    ]
    for index, parameter in enumerate(parameters, start=1):
        target = _model_target(parameter)
        target_summary = {
            "modelFile": target.get("modelFile") or target.get("model_file"),
            "modelSheet": target.get("modelSheet") or target.get("model_sheet"),
            "tableName": target.get("tableName") or target.get("table_name"),
        }
        lines.append(
            "| {index} | {name} | `{target}` | `{slot_axes}` | `{value_fields}` | {value_count} | {rationale} |".format(
                index=index,
                name=_md_cell(_parameter_name(parameter), max_chars=120),
                target=_md_cell(target_summary, max_chars=260),
                slot_axes=_md_cell(_slot_axis_field_names(parameter), max_chars=220),
                value_fields=_md_cell(_value_field_names(parameter), max_chars=220),
                value_count=len(_parameter_values(parameter)),
                rationale=_md_cell(parameter.get("rationale") or "", max_chars=420),
            ),
        )
    return lines


def _proposal_value_table_lines(parameters: list[dict[str, Any]]) -> list[str]:
    if not parameters:
        return ["- 제안 value 없음.", ""]
    lines: list[str] = []
    for parameter in parameters:
        values = _parameter_values(parameter)
        lines.extend(
            [
                f"#### Proposed Values - {_parameter_name(parameter)}",
                "",
            ],
        )
        if not values:
            lines.extend(["- 제안 value 없음.", ""])
            continue
        lines.extend(
            [
                "| No | slot coordinates | basecaseValue | proposedValue | rationale |",
                "|---:|---|---:|---:|---|",
            ],
        )
        for index, value in enumerate(values, start=1):
            lines.append(
                "| {index} | `{coordinates}` | {basecase} | {proposed} | {rationale} |".format(
                    index=index,
                    coordinates=_md_cell(
                        _slot_coordinates_for_value(parameter, value),
                        max_chars=500,
                    ),
                    basecase=_md_cell(value.get("basecaseValue"), max_chars=160),
                    proposed=_md_cell(value.get("proposedValue"), max_chars=160),
                    rationale=_md_cell(value.get("rationale") or "", max_chars=620),
                ),
            )
        lines.append("")
    return lines


def _flatten_hierarchy_sample(nodes: list[Any], *, limit: int = 5) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []

    def visit(items: list[Any], path: list[Any]) -> None:
        if len(samples) >= limit:
            return
        for item in items:
            if len(samples) >= limit:
                return
            if not isinstance(item, dict):
                continue
            value = item.get("value")
            next_path = [*path, value]
            children = item.get("children") or []
            if children:
                visit(children, next_path)
            else:
                samples.append({"path": next_path})

    visit(nodes, [])
    return samples


def _hierarchy_path_count(nodes: list[Any]) -> int:
    count = 0

    def visit(items: list[Any]) -> None:
        nonlocal count
        for item in items:
            if not isinstance(item, dict):
                continue
            children = item.get("children") or []
            if children:
                visit(children)
            else:
                count += 1

    visit(nodes)
    return count


def _summarize_slot_option(option: dict[str, Any]) -> dict[str, Any]:
    axis_values = option.get("axis_values") or {}
    hierarchy = option.get("slot_hierarchy") or []
    return {
        "axis_names": option.get("axis_names") or [],
        "axis_values": {
            str(axis_name): values
            for axis_name, values in axis_values.items()
        },
        "axis_value_counts": {
            str(axis_name): len(values or [])
            for axis_name, values in axis_values.items()
        },
        "slot_hierarchy_axes": option.get("slot_hierarchy_axes") or [],
        "slot_hierarchy_path_count": _hierarchy_path_count(hierarchy),
        "slot_hierarchy_sample": _flatten_hierarchy_sample(hierarchy),
    }


def _summarize_value_group(group: dict[str, Any]) -> dict[str, Any]:
    cells = group.get("cells") or []
    return {
        "value_name": group.get("value_name"),
        "fixed_axes": group.get("fixed_axes") or {},
        "variable_axis_names": group.get("variable_axis_names") or [],
        "cell_count": len(cells),
        "cell_sample": cells[:8],
    }


def _summarize_prompt_packet(step: str, packet: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "inserted_top_level_fields": list(packet.keys()),
        "scenario_brief": _summarize_large_text_fields(
            packet.get("scenario_brief") or {},
        ),
    }
    if "candidate_validation_tasks" in packet:
        summary["candidate_validation_tasks"] = packet.get("candidate_validation_tasks") or []
        return summary
    if "period_resolution_policy" in packet:
        summary["period_resolution_policy"] = packet.get("period_resolution_policy") or {}
    if "slot_selection_limits" in packet:
        summary["slot_selection_limits"] = packet.get("slot_selection_limits") or {}
    if "parameter_slot_tasks" in packet:
        tasks = []
        for task in packet.get("parameter_slot_tasks") or []:
            tasks.append(
                {
                    "inserted_task_fields": list(task.keys()),
                    "parameter": task.get("parameter") or {},
                    "selection_dimensions": task.get("selection_dimensions") or [],
                    "supporting_dimensions": task.get("supporting_dimensions") or [],
                    "basecase_slot_options": [
                        _summarize_slot_option(option)
                        for option in task.get("basecase_slot_options") or []
                    ],
                },
            )
        summary["parameter_slot_tasks"] = tasks
        return summary
    if "basecase_record_selection_policy" in packet:
        summary["basecase_record_selection_policy"] = (
            packet.get("basecase_record_selection_policy") or {}
        )
    if "parameter_value_tasks" in packet:
        tasks = []
        for task in packet.get("parameter_value_tasks") or []:
            tasks.append(
                {
                    "inserted_task_fields": list(task.keys()),
                    "parameter": task.get("parameter") or {},
                    "selection_dimensions": task.get("selection_dimensions") or [],
                    "supporting_dimensions": task.get("supporting_dimensions") or [],
                    "selected_slot_axes_field_names": (
                        task.get("selected_slot_axes_field_names") or []
                    ),
                    "selected_slots": task.get("selected_slots") or [],
                    "basecase_value_groups": [
                        _summarize_value_group(group)
                        for group in task.get("basecase_value_groups") or []
                    ],
                },
            )
        summary["parameter_value_tasks"] = tasks
        return summary
    summary["note"] = f"Unhandled prompt packet shape for {step}"
    return summary


def _prompt_input_packets(record: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    # Prompt packets are already represented by the stage/result trace. Rebuilding
    # them here depended on removed internal helpers and could fail after a
    # successful proposal was persisted.
    return []


async def _run(args: argparse.Namespace) -> tuple[Path, str]:
    repo_root = Path(args.repo_root).expanduser().resolve()
    if not repo_root.exists():
        raise SystemExit(f"repo root not found: {repo_root}")
    sys.path.insert(0, str(repo_root))

    from tests.manual.model_parameter_agent.evaluate_proposals import (  # noqa: PLC0415
        _ensure_model_parameter_test_resource_runtime,
        _evaluate_scenario,
        _failure_stage_trace_table_lines,
        _failure_trace_from_exception,
        _format_duration,
        _format_seconds,
        _llm_call_table_lines,
        _selected_adjustments,
        _stage_summary_table_lines,
    )

    await _ensure_model_parameter_test_resource_runtime()

    report_dir = repo_root / "tests" / "reports" / "model_parameter_agent"
    report_dir.mkdir(parents=True, exist_ok=True)
    started_at = datetime.now()
    started_monotonic = time.perf_counter()
    timestamp = started_at.strftime("%Y%m%d_%H%M%S")
    report_path = report_dir / f"model_parameter_single_scenario_{args.scenario_id}_{timestamp}.md"

    record: dict[str, Any] | None = None
    error: str | None = None
    failure_trace: dict[str, Any] = {}
    try:
        record = await _evaluate_scenario(args.scenario_id)
    except Exception as exc:  # noqa: BLE001 - report the failure to markdown for test traceability.
        error = repr(exc)
        failure_trace = _failure_trace_from_exception(exc)

    finished_at = datetime.now()
    elapsed_seconds = time.perf_counter() - started_monotonic
    status = _status(record, error)
    if failure_trace:
        failure_trace.update(
            {
                "attempt": 1,
                "elapsed_seconds": elapsed_seconds,
                "error": error,
            },
        )

    lines: list[str] = [
        "# Model Parameter Proposal Evaluation - Single Scenario",
        "",
        f"- 실행 시작: {started_at.isoformat(timespec='seconds')}",
        f"- 실행 종료: {finished_at.isoformat(timespec='seconds')}",
        f"- 시나리오 실행시간: {_format_duration(elapsed_seconds)} ({_format_seconds(elapsed_seconds)})",
        f"- scenario_id: {args.scenario_id}",
        f"- maxCandidates: {args.max_candidates}",
        f"- allowLlmFallback: {args.allow_llm_fallback}",
        f"- status: {status}",
        "",
    ]

    if error:
        context = failure_trace.get("context") or {}
        lines.extend(
            [
                "## Error",
                "",
                "```text",
                error,
                "```",
                "",
                "## Scenario Group",
                "",
                "```json",
                _json(_scenario_group_context(context)),
                "```",
                "",
                "## Event",
                "",
                "```json",
                _json(_event_context(context)),
                "```",
                "",
                f"## Scenario {args.scenario_id} Failure Result",
                "",
                "### Scenario Major Info",
                "",
                "```json",
                _json(
                    _scenario_context(context)
                    if context
                    else {
                        "scenario_id": args.scenario_id,
                        "trace_status": "scenario context 수집 실패",
                    },
                ),
                "```",
                "",
                "### Attempt별 단계 Tracing",
                "",
                "**Attempt 1**",
                "",
                f"- failed_stage: `{failure_trace.get('failed_stage') or 'unknown'}`",
                f"- elapsed: {_format_duration(elapsed_seconds)} ({_format_seconds(elapsed_seconds)})",
                f"- error: `{error}`",
            ],
        )
        lines.extend(
            _failure_stage_trace_table_lines(
                failure_trace,
                heading="**단계별 Failure Trace**",
            ),
        )
        lines.extend(
            _llm_call_table_lines(
                failure_trace.get("llm_calls") or [],
                heading="**모델 호출별 소요시간 및 Token**",
            ),
        )
        lines.append("")
    elif record:
        context = record.get("context") or {}
        scenario = context.get("scenario") or {}
        final_response = record.get("final_response") or {}
        proposal_row = _fetch_proposal_db_row(_proposal_id(final_response))
        proposal_parameters = _proposal_parameters_for_report(proposal_row, final_response)
        selected = _selected_adjustments(record.get("result") or {})
        response_warnings = (record.get("final_response") or {}).get("warnings") or []
        lines.extend(
            [
                "## Scenario Group",
                "",
                "```json",
                _json(_scenario_group_context(context)),
                "```",
                "",
                "## Dimension Template",
                "",
                "```json",
                _json(context.get("dimension_template") or []),
                "```",
                "",
                "## Dimension -> Parameter Mapping",
                "",
                "```json",
                _json(_dimension_parameter_mapping_context(context)),
                "```",
                "",
                "## Event",
                "",
                "```json",
                _json(_event_context(context)),
                "```",
                "",
                f"## Scenario {args.scenario_id} Proposal Result",
                "",
                "### Scenario Major Info",
                "",
                "```json",
                _json(_scenario_context(context)),
                "```",
                "",
                "### Validation Summary",
                "",
                f"- expected_parameters: `{_json_preview(_names(record.get('expected_candidates') or []), max_chars=1200)}`",
                f"- selected_parameters: `{_json_preview(_names(selected, selected_only=True), max_chars=1200)}`",
                f"- mapping_candidate_coverage: {'PASS' if record.get('mapping_ok') else 'FAIL'}",
                f"- selected_result: {'PASS' if record.get('selected_ok') else 'FAIL'}",
                f"- routing_result: {record.get('routing_status')}",
                f"- response_warnings: `{_json_preview(response_warnings, max_chars=1600)}`",
                "",
            ],
        )
        for label, key in (
            ("mapping_messages", "mapping_messages"),
            ("selected_messages", "selected_messages"),
            ("routing_messages", "routing_messages"),
            ("mapping_warnings", "mapping_warnings"),
            ("basecase_warnings", "basecase_warnings"),
        ):
            values = record.get(key) or []
            if values:
                lines.append(f"- {label}: `{_json_preview(values, max_chars=1600)}`")
        lines.extend(_stage_summary_table_lines(record.get("step_summary") or {}))
        lines.extend(
            [
                "",
                "### Proposed Parameter Summary",
                "",
                *_proposal_parameter_table_lines(proposal_parameters),
                "",
                "### Proposed Parameter Values",
                "",
                *_proposal_value_table_lines(proposal_parameters),
                "### Final DB Proposal Row",
                "",
                "- source_table: `tmm_mi_model_param_proposal_m`",
                "",
                "```json",
                _json(proposal_row),
                "```",
                "",
            ],
        )
        lines.extend(_llm_call_table_lines(record.get("llm_calls") or []))
        lines.extend(
            [
                "",
                "<details>",
                "<summary>Prompt input field summary</summary>",
                "",
                (
                    "각 섹션은 실제 Step별 prompt packet에 삽입되는 top-level field와 "
                    "task field를 요약합니다. basecase hierarchy/cells는 리포트 과대화를 "
                    "막기 위해 count와 sample을 함께 표시합니다."
                ),
                "",
            ],
        )
        for step, packet in _prompt_input_packets(record):
            lines.extend(
                [
                    f"#### {step}",
                    "",
                    "```json",
                    _json(_summarize_prompt_packet(step, packet)),
                    "```",
                    "",
                ],
            )
        lines.extend(
            [
                "</details>",
                "",
            ],
        )

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path, status


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario-id", type=int, required=True)
    parser.add_argument("--repo-root", default=str(DEFAULT_REPO_ROOT))
    parser.add_argument("--max-candidates", type=int, default=30)
    parser.add_argument("--allow-llm-fallback", action="store_true")
    args = parser.parse_args()
    report_path, status = asyncio.run(_run(args))
    print("REPORT", report_path)
    print("STATUS", status)
    print("ERROR_COUNT", 1 if status == "ERROR" else 0)


if __name__ == "__main__":
    main()
