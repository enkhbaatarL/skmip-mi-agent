from __future__ import annotations

import argparse
import asyncio
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
import json
import os
from pathlib import Path
import sys
import time
from typing import Any

from sqlalchemy import func, select


ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
DEFAULT_APP_CONFIG = ROOT_DIR / "envs" / "config.yaml"
DEFAULT_DOTENV = ROOT_DIR / "envs" / ".env"
if DEFAULT_DOTENV.exists():
    from dotenv import load_dotenv

    load_dotenv(DEFAULT_DOTENV, override=False)
if "APP_CONFIG" not in os.environ and DEFAULT_APP_CONFIG.exists():
    os.environ["APP_CONFIG"] = str(DEFAULT_APP_CONFIG)

from apps.persistence.event.models import MiEventTypeL2Model
from apps.persistence.model_parameter.models import (
    MiModelParamDimensionMapModel,
    MiModelParamModel,
    MiModelParamProposalModel,
)
from apps.persistence.scenario.models import MiScenarioModel
from apps.persistence.scenario_group.models import (
    MiScenarioGroupModel,
)
from tests.manual.model_parameter_agent.evaluate_proposals import (
    _ensure_model_parameter_test_resource_runtime,
    _evaluate_scenario,
    _failure_stage_trace_table_lines,
    _failure_trace_from_exception,
    _json_pretty,
    _json_preview,
    _llm_call_table_lines,
    _selected_adjustments,
    _stage_summary_table_lines,
)


REPORT_DIR = ROOT_DIR / "tests" / "reports" / "model_parameter_agent"


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


def _timing_special_note(
    *,
    elapsed_seconds: float | None,
    attempts: int,
    failed: bool = False,
    error: str | None = None,
) -> str:
    retry_count = max(0, attempts - 1)
    if failed:
        error_summary = " ".join(str(error or "").split())[:160]
        error_suffix = f": {error_summary}" if error_summary else ""
        return f"FAIL · 최종 실패 (outer retry {retry_count}회){error_suffix}"
    if elapsed_seconds is None:
        return f"REVIEW · 소요시간 미수집 (outer retry {retry_count}회)"
    if elapsed_seconds > 180:
        return (
            f"FAIL · 180초 초과 ({_format_seconds(elapsed_seconds)}, "
            f"outer retry {retry_count}회)"
        )
    if retry_count:
        return f"REVIEW · outer retry {retry_count}회, 180초 이내"
    return "PASS · 특이사항 없음 (retry 0회, 180초 이내)"


def _timing_special_summary(
    records: list[dict[str, Any]],
    errors: list[dict[str, Any]],
) -> str:
    counts = {"PASS": 0, "REVIEW": 0, "FAIL": 0}
    attention_scenario_ids: list[int] = []
    for record in records:
        note = _timing_special_note(
            elapsed_seconds=record.get("elapsed_seconds"),
            attempts=int(record.get("attempt") or 1),
        )
        judgement = note.split(" · ", 1)[0]
        counts[judgement] += 1
        if judgement != "PASS":
            attention_scenario_ids.append(int(record["scenario_id"]))
    for error in errors:
        counts["FAIL"] += 1
        attention_scenario_ids.append(int(error["scenario_id"]))
    summary = (
        f"PASS {counts['PASS']}건, REVIEW {counts['REVIEW']}건, "
        f"FAIL {counts['FAIL']}건; 확인 필요 scenario_ids="
        f"{sorted(attention_scenario_ids)}"
    )
    elapsed_cases = [
        (int(item["scenario_id"]), float(item["elapsed_seconds"]))
        for item in [*records, *errors]
        if item.get("elapsed_seconds") is not None
    ]
    if not elapsed_cases:
        return summary
    max_scenario_id, max_elapsed_seconds = max(elapsed_cases, key=lambda item: item[1])
    return (
        f"{summary}; 최장 scenario_id={max_scenario_id} "
        f"({_format_seconds(max_elapsed_seconds)})"
    )


def _proposal_parameters(final_response: dict[str, Any]) -> list[dict[str, Any]]:
    data = final_response.get("data") or {}
    if "proposalParameters" in data:
        return data.get("proposalParameters") or []
    return final_response.get("recommendations") or []


def _summarize_text(value: Any, *, max_chars: int = 1200) -> Any:
    text = str(value or "")
    if len(text) <= max_chars:
        return text
    return {
        "text_chars": len(text),
        "text_excerpt": text[:max_chars].rstrip(),
    }


def _scenario_group_context(
    context: dict[str, Any],
    target: EventTypeTarget | None = None,
) -> dict[str, Any]:
    group = context.get("scenario_group") or {}
    return {
        "scenario_group_id": group.get("scenario_group_id")
        or (target.scenario_group_id if target else None),
        "mi_event_id": group.get("mi_event_id"),
        "event_type_l2_id": group.get("event_type_l2_id")
        or (target.event_type_l2_id if target else None),
        "request_usr_id": group.get("request_usr_id"),
        "title": group.get("title") or (target.group_title if target else None),
        "summary": _summarize_text(group.get("summary")),
        "description": _summarize_text(group.get("description")),
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
        "detail_analysis": _summarize_text(
            event.get("detail_analysis"),
            max_chars=1600,
        ),
    }


def _scenario_context(context: dict[str, Any]) -> dict[str, Any]:
    scenario = context.get("scenario") or {}
    return {
        "scenario_id": scenario.get("scenario_id"),
        "scenario_group_id": scenario.get("scenario_group_id"),
        "title": scenario.get("title"),
        "narrative": _summarize_text(scenario.get("narrative"), max_chars=1600),
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
    from apps.common.configs.database.sync_database.connection import get_sync_session

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


def _proposal_parameters_from_record(record: dict[str, Any]) -> list[dict[str, Any]]:
    runtime_parameters = _proposal_parameters(record.get("final_response") or {})
    if runtime_parameters:
        return runtime_parameters
    proposal_row = record.get("proposal_db_row") or {}
    db_parameters = proposal_row.get("proposal_parameters")
    if isinstance(db_parameters, list):
        return db_parameters
    return []


def _model_target(parameter: dict[str, Any]) -> dict[str, Any]:
    target = parameter.get("modelTarget") or parameter.get("model_target") or {}
    return target if isinstance(target, dict) else {}


def _parameter_name(parameter: dict[str, Any]) -> str:
    return str(parameter.get("parameterName") or parameter.get("parameter_name") or "")


def _normalize_parameter_name_for_report(value: Any) -> str:
    return str(value or "").strip().lower()


def _parameter_name_matches(value: Any, target_parameter: str) -> bool:
    return (
        _normalize_parameter_name_for_report(value)
        == _normalize_parameter_name_for_report(target_parameter)
    )


def _candidate_parameter_name(candidate: dict[str, Any]) -> str:
    return str(
        candidate.get("canonical_parameter_name")
        or candidate.get("parameter_name")
        or candidate.get("parameterName")
        or "",
    )


def _filter_parameters_by_name(
    parameters: list[dict[str, Any]],
    target_parameter: str | None,
) -> list[dict[str, Any]]:
    if not target_parameter:
        return parameters
    return [
        parameter
        for parameter in parameters
        if _parameter_name_matches(_parameter_name(parameter), target_parameter)
    ]


def _target_event_type_ids(
    target_event_type_l2_ids_by_parameter: dict[str, tuple[int, ...]],
    target_parameter: str,
) -> set[int]:
    for parameter, event_type_l2_ids in target_event_type_l2_ids_by_parameter.items():
        if _parameter_name_matches(parameter, target_parameter):
            return {int(item) for item in event_type_l2_ids}
    return set()


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
    return {
        axis: value.get(axis)
        for axis in _slot_axis_field_names(parameter)
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
        lines.extend([f"###### Proposed Values - {_parameter_name(parameter)}", ""])
        if not values:
            lines.extend(["- 제안 value 없음.", ""])
            continue
        lines.extend(
            [
                "| No | slot coordinates | basecaseValue | lutValue | proposedValue | rationale |",
                "|---:|---|---:|---:|---:|---|",
            ],
        )
        for index, value in enumerate(values, start=1):
            lines.append(
                "| {index} | `{coordinates}` | {basecase} | {lut} | {proposed} | {rationale} |".format(
                    index=index,
                    coordinates=_md_cell(
                        _slot_coordinates_for_value(parameter, value),
                        max_chars=500,
                    ),
                    basecase=_md_cell(value.get("basecaseValue"), max_chars=160),
                    lut=_md_cell(value.get("lutValue"), max_chars=160),
                    proposed=_md_cell(value.get("proposedValue"), max_chars=160),
                    rationale=_md_cell(value.get("rationale") or "", max_chars=620),
                ),
            )
        lines.append("")
    return lines


@dataclass(frozen=True)
class EventTypeTarget:
    event_type_l2_id: int
    event_type_label: str
    scenario_group_id: int
    group_title: str
    scenario_ids: tuple[int, ...]
    target_parameter: str | None = None


@dataclass(frozen=True)
class ParameterScenarioSelection:
    parameter_name: str
    scenario_ids: tuple[int, ...]


def _target_parameter_names_by_key(
    target_parameters: tuple[str, ...],
) -> dict[str, str]:
    target_by_key: dict[str, str] = {}
    for parameter in target_parameters:
        parameter_name = str(parameter or "").strip()
        parameter_key = _normalize_parameter_name_for_report(parameter_name)
        if not parameter_key:
            message = "--target-parameters contains an empty parameter name"
            raise ValueError(message)
        if parameter_key in target_by_key:
            message = f"duplicate --target-parameters entry: {parameter_name}"
            raise ValueError(message)
        target_by_key[parameter_key] = parameter_name
    return target_by_key


def _parse_parameter_scenario_entry(raw_value: str) -> tuple[str, str, tuple[int, ...]]:
    raw_text = str(raw_value or "").strip()
    if raw_text.count("=") != 1:
        message = (
            "invalid --parameter-scenarios entry; expected "
            f"PARAMETER=SCENARIO_ID[,SCENARIO_ID...]: {raw_text or '<empty>'}"
        )
        raise ValueError(message)
    raw_parameter, raw_scenario_ids = raw_text.split("=", 1)
    parameter_name = raw_parameter.strip()
    parameter_key = _normalize_parameter_name_for_report(parameter_name)
    if not parameter_key or not raw_scenario_ids.strip():
        message = f"invalid --parameter-scenarios entry; expected PARAMETER=SCENARIO_ID[,SCENARIO_ID...]: {raw_text}"
        raise ValueError(message)
    scenario_ids: list[int] = []
    for raw_scenario_id in raw_scenario_ids.split(","):
        try:
            scenario_id = int(raw_scenario_id.strip())
        except ValueError as exc:
            message = f"invalid scenario id in --parameter-scenarios entry: {raw_text}"
            raise ValueError(message) from exc
        if scenario_id <= 0:
            message = f"scenario id must be positive in --parameter-scenarios entry: {raw_text}"
            raise ValueError(message)
        if scenario_id in scenario_ids:
            message = f"duplicate scenario id in --parameter-scenarios entry: {scenario_id}"
            raise ValueError(message)
        scenario_ids.append(scenario_id)
    return parameter_key, parameter_name, tuple(scenario_ids)


def _parse_parameter_scenarios(
    raw_values: tuple[str, ...],
    target_parameters: tuple[str, ...],
) -> tuple[ParameterScenarioSelection, ...]:
    if not raw_values:
        return ()
    if not target_parameters:
        message = "--parameter-scenarios requires --target-parameters"
        raise ValueError(message)

    target_by_key = _target_parameter_names_by_key(target_parameters)
    scenario_ids_by_parameter: dict[str, tuple[int, ...]] = {}
    parameter_by_scenario_id: dict[int, str] = {}
    for raw_value in raw_values:
        parameter_key, parameter_name, scenario_ids = _parse_parameter_scenario_entry(raw_value)
        if parameter_key in scenario_ids_by_parameter:
            message = f"duplicate parameter in --parameter-scenarios: {parameter_name}"
            raise ValueError(message)
        for scenario_id in scenario_ids:
            if scenario_id in parameter_by_scenario_id:
                message = (
                    "duplicate scenario id in --parameter-scenarios: "
                    f"{scenario_id} ({parameter_by_scenario_id[scenario_id]}, {parameter_name})"
                )
                raise ValueError(message)
            parameter_by_scenario_id[scenario_id] = parameter_name
        scenario_ids_by_parameter[parameter_key] = scenario_ids

    expected_keys = set(target_by_key)
    actual_keys = set(scenario_ids_by_parameter)
    if actual_keys != expected_keys:
        missing = [target_by_key[key] for key in target_by_key if key not in actual_keys]
        unexpected = sorted(
            parameter
            for parameter in (str(raw_value).split("=", 1)[0].strip() for raw_value in raw_values)
            if _normalize_parameter_name_for_report(parameter) not in expected_keys
        )
        message = (
            f"--parameter-scenarios must match --target-parameters exactly: missing={missing}, unexpected={unexpected}"
        )
        raise ValueError(message)

    return tuple(
        ParameterScenarioSelection(
            parameter_name=parameter_name,
            scenario_ids=scenario_ids_by_parameter[parameter_key],
        )
        for parameter_key, parameter_name in target_by_key.items()
    )


def _build_parameter_scenario_targets(
    selections: tuple[ParameterScenarioSelection, ...],
    scenario_rows: list[tuple[int, int, int, str, str]],
) -> tuple[EventTypeTarget, ...]:
    context_by_scenario_id = {
        int(scenario_id): (
            int(event_type_l2_id),
            int(scenario_group_id),
            str(group_title or ""),
            str(event_type_label or ""),
        )
        for scenario_id, event_type_l2_id, scenario_group_id, group_title, event_type_label in scenario_rows
    }
    missing_scenario_ids = sorted(
        scenario_id
        for selection in selections
        for scenario_id in selection.scenario_ids
        if scenario_id not in context_by_scenario_id
    )
    if missing_scenario_ids:
        message = f"--parameter-scenarios references missing or deleted scenarios: {missing_scenario_ids}"
        raise ValueError(message)

    targets: list[EventTypeTarget] = []
    for selection in selections:
        selected_contexts = {context_by_scenario_id[scenario_id] for scenario_id in selection.scenario_ids}
        if len(selected_contexts) != 1:
            message = (
                "--parameter-scenarios for one parameter must belong to one scenario group: "
                f"parameter={selection.parameter_name}, scenario_ids={list(selection.scenario_ids)}"
            )
            raise ValueError(message)
        event_type_l2_id, scenario_group_id, group_title, event_type_label = next(iter(selected_contexts))
        targets.append(
            EventTypeTarget(
                event_type_l2_id=event_type_l2_id,
                event_type_label=event_type_label,
                scenario_group_id=scenario_group_id,
                group_title=group_title,
                scenario_ids=selection.scenario_ids,
                target_parameter=selection.parameter_name,
            ),
        )
    return tuple(targets)


def _discover_parameter_scenario_targets(
    selections: tuple[ParameterScenarioSelection, ...],
) -> tuple[EventTypeTarget, ...]:
    from apps.common.configs.database.sync_database.connection import get_sync_session

    scenario_ids = tuple(scenario_id for selection in selections for scenario_id in selection.scenario_ids)
    session = get_sync_session()
    try:
        stmt = (
            select(
                MiScenarioModel.scenario_id,
                MiScenarioGroupModel.event_type_l2_id,
                MiScenarioGroupModel.scenario_group_id,
                MiScenarioGroupModel.title,
                MiEventTypeL2Model.level_2_label,
            )
            .join(
                MiScenarioGroupModel,
                MiScenarioGroupModel.scenario_group_id == MiScenarioModel.scenario_group_id,
            )
            .join(
                MiEventTypeL2Model,
                MiEventTypeL2Model.event_type_l2_id == MiScenarioGroupModel.event_type_l2_id,
            )
            .where(
                MiScenarioModel.scenario_id.in_(scenario_ids),
                MiScenarioModel.del_yn == "N",
                MiScenarioGroupModel.del_yn == "N",
                MiEventTypeL2Model.del_yn == "N",
            )
            .order_by(MiScenarioModel.scenario_id)
        )
        rows = session.execute(stmt).all()
    finally:
        session.close()
    return _build_parameter_scenario_targets(selections, list(rows))


def _resolve_evaluation_scope(
    *,
    event_type_l2_ids: tuple[int, ...],
    group_title_prefix: str | None,
    groups_per_event: int | None,
    scenarios_per_group: int | None,
    target_parameters: tuple[str, ...],
    target_event_type_l2_ids_by_parameter: dict[str, tuple[int, ...]],
    resolve_event_type_l2_ids_from_parameters: bool,
    parameter_scenarios: tuple[ParameterScenarioSelection, ...],
) -> tuple[
    tuple[int, ...],
    tuple[EventTypeTarget, ...],
    tuple[ParameterScenarioSelection, ...],
]:
    if parameter_scenarios:
        validated_selections = _parse_parameter_scenarios(
            tuple(
                f"{selection.parameter_name}={','.join(str(item) for item in selection.scenario_ids)}"
                for selection in parameter_scenarios
            ),
            target_parameters,
        )
        if event_type_l2_ids:
            message = "parameter_scenarios cannot be combined with event_type_l2_ids"
            raise ValueError(message)
        if group_title_prefix or groups_per_event is not None or scenarios_per_group is not None:
            message = "parameter_scenarios cannot be combined with group/scenario discovery filters"
            raise ValueError(message)
        targets = _discover_parameter_scenario_targets(validated_selections)
        resolved_event_type_l2_ids = tuple(
            sorted({target.event_type_l2_id for target in targets}),
        )
        return resolved_event_type_l2_ids, targets, validated_selections

    resolved_event_type_l2_ids = event_type_l2_ids
    if resolve_event_type_l2_ids_from_parameters:
        resolved_event_type_l2_ids = tuple(
            sorted(
                {
                    event_type_l2_id
                    for parameter_event_type_ids in target_event_type_l2_ids_by_parameter.values()
                    for event_type_l2_id in parameter_event_type_ids
                },
            ),
        )
        if not resolved_event_type_l2_ids:
            message = f"No direct/routing event_type_l2_ids found for target parameters: {', '.join(target_parameters)}"
            raise SystemExit(message)

    targets = _discover_targets(
        resolved_event_type_l2_ids,
        group_title_prefix=group_title_prefix,
        groups_per_event=groups_per_event,
        scenarios_per_group=scenarios_per_group,
    )
    return resolved_event_type_l2_ids, targets, ()


def _discover_targets(
    event_type_l2_ids: tuple[int, ...],
    *,
    group_title_prefix: str | None = None,
    groups_per_event: int | None = None,
    scenarios_per_group: int | None = None,
) -> tuple[EventTypeTarget, ...]:
    from apps.common.configs.database.sync_database.connection import get_sync_session

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


def _discover_event_type_l2_ids_for_parameters(
    target_parameters: tuple[str, ...],
) -> dict[str, tuple[int, ...]]:
    normalized_targets = {
        _normalize_parameter_name_for_report(parameter): parameter
        for parameter in target_parameters
        if str(parameter or "").strip()
    }
    if not normalized_targets:
        return {}

    event_type_ids_by_parameter: dict[str, set[int]] = {
        parameter: set() for parameter in normalized_targets.values()
    }
    from apps.common.configs.database.sync_database.connection import get_sync_session

    session = get_sync_session()
    try:
        stmt = (
            select(
                MiModelParamModel.parameter_name,
                MiModelParamDimensionMapModel.event_type_l2_id,
            )
            .join(
                MiModelParamDimensionMapModel,
                MiModelParamDimensionMapModel.model_param_id
                == MiModelParamModel.model_param_id,
            )
            .where(
                MiModelParamModel.del_yn == "N",
                MiModelParamModel.use_yn == "Y",
                MiModelParamDimensionMapModel.del_yn == "N",
                MiModelParamDimensionMapModel.use_yn == "Y",
                MiModelParamDimensionMapModel.mapping_method.in_(("direct", "routing")),
                func.lower(MiModelParamModel.parameter_name).in_(
                    tuple(normalized_targets),
                ),
            )
            .order_by(
                MiModelParamModel.parameter_name,
                MiModelParamDimensionMapModel.event_type_l2_id,
            )
        )
        rows = session.execute(stmt).all()
    finally:
        session.close()

    for parameter_name, event_type_l2_id in rows:
        requested_parameter = normalized_targets.get(
            _normalize_parameter_name_for_report(parameter_name),
        )
        if requested_parameter is not None:
            event_type_ids_by_parameter[requested_parameter].add(int(event_type_l2_id))

    return {
        parameter: tuple(sorted(event_type_l2_ids))
        for parameter, event_type_l2_ids in event_type_ids_by_parameter.items()
    }


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


def _records_for_target(
    target: EventTypeTarget,
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if target.target_parameter is not None:
        return [record for record in records if record.get("target") == target]
    return [record for record in records if record["target"].scenario_group_id == target.scenario_group_id]


def _errors_for_target(
    target: EventTypeTarget,
    errors: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if target.target_parameter is not None:
        return [error for error in errors if error.get("target") == target]
    return [error for error in errors if error["target"].scenario_group_id == target.scenario_group_id]


def _target_status_key(target: EventTypeTarget) -> str:
    if target.target_parameter is not None:
        return f"{target.target_parameter}={target.scenario_ids[0]}"
    return str(target.scenario_group_id)


def _lut_summary_line(records: list[dict[str, Any]]) -> str:
    if not records:
        return "- LUT: N/A (아직 완료된 시나리오 없음)"

    enabled_values = {
        bool((record.get("resolved_config") or {}).get("model_parameter_lut_enabled"))
        for record in records
    }
    enabled_label = "enabled" if enabled_values == {True} else "disabled" if enabled_values == {False} else "mixed"
    versions = sorted({str(record["lut_version"]) for record in records if record.get("lut_version")})
    version_label = ", ".join(versions) if versions else "N/A"
    return f"- LUT: {enabled_label}, version={version_label}"


def _scenario_result_summary(
    *,
    record: dict[str, Any] | None = None,
    error: dict[str, Any] | None = None,
) -> str:
    if error is not None:
        error_text = " ".join(str(error.get("error") or "").split())
        if "No model parameter mapping candidates" in error_text:
            return "FAIL · 매핑 후보 없음"
        return f"FAIL · 실행 오류: {_md_cell(error_text, max_chars=120)}"

    if record is None:
        return "REVIEW · 실행 결과 미수집"
    if record.get("mapping_ok") is False:
        return "FAIL · 매핑 후보 검증 실패"
    if record.get("selected_ok") is False:
        return "FAIL · 파라미터 선정 검증 실패"

    timing_note = _timing_special_note(
        elapsed_seconds=record.get("elapsed_seconds"),
        attempts=int(record.get("attempt") or 1),
    )
    timing_judgement = timing_note.split(" · ", 1)[0]
    if timing_judgement == "FAIL":
        return f"FAIL · proposal 성공, {timing_note.split(' · ', 1)[1]}"
    if not _proposal_parameters_from_record(record):
        return "REVIEW · proposal 성공, 제안 파라미터 없음"
    if str(record.get("routing_status") or "").upper() == "REVIEW":
        return "REVIEW · proposal 성공, routing 결과 확인 필요"
    if timing_judgement == "REVIEW":
        return f"REVIEW · proposal 성공, {timing_note.split(' · ', 1)[1]}"
    return "PASS · proposal 생성 및 검증 완료"


def _scenario_result_table_lines(
    *,
    targets: tuple[EventTypeTarget, ...],
    records: list[dict[str, Any]],
    errors: list[dict[str, Any]],
    target_parameters: tuple[str, ...],
    target_event_type_l2_ids_by_parameter: dict[str, tuple[int, ...]],
) -> list[str]:
    record_by_key = {
        (record["target"], int(record["scenario_id"])): record
        for record in records
    }
    error_by_key = {
        (error["target"], int(error["scenario_id"])): error
        for error in errors
    }
    lines = [
        "### 시나리오별 결과",
        "",
        "| 시나리오그룹 | 시나리오 | 이벤트타입 | 파라미터 | 결과요약 | 소요시간 | Token (입력/출력/합계) |",
        "|---|---|---|---|---|---:|---:|",
    ]
    completed_count = 0
    for target in targets:
        mapped_parameters = [
            parameter
            for parameter in target_parameters
            if target.event_type_l2_id
            in _target_event_type_ids(
                target_event_type_l2_ids_by_parameter,
                parameter,
            )
        ]
        if target.target_parameter is not None:
            mapped_parameters = [target.target_parameter]

        for scenario_id in target.scenario_ids:
            key = (target, scenario_id)
            record = record_by_key.get(key)
            error = error_by_key.get(key)
            if record is None and error is None:
                continue

            completed_count += 1
            context = (record or error or {}).get("context") or {}
            scenario = context.get("scenario") or {}
            scenario_title = scenario.get("title") or (error or {}).get("scenario_title") or ""
            parameters = mapped_parameters
            if not parameters and record is not None:
                parameters = list(
                    dict.fromkeys(
                        _parameter_name(parameter)
                        for parameter in _proposal_parameters_from_record(record)
                        if _parameter_name(parameter)
                    ),
                )
            elapsed_seconds = (record or error or {}).get("elapsed_seconds")
            lines.append(
                "| {group} | {scenario} | {event_type} | {parameters} | {summary} | {elapsed} | {tokens} |".format(
                    group=_md_cell(
                        f"{target.scenario_group_id} · {target.group_title}",
                        max_chars=220,
                    ),
                    scenario=_md_cell(
                        f"{scenario_id} · {scenario_title}" if scenario_title else scenario_id,
                        max_chars=220,
                    ),
                    event_type=_md_cell(
                        f"{target.event_type_l2_id} · {target.event_type_label}",
                        max_chars=180,
                    ),
                    parameters=_md_cell(", ".join(parameters) if parameters else "-", max_chars=180),
                    summary=_scenario_result_summary(record=record, error=error),
                    elapsed=(
                        f"{_format_duration(elapsed_seconds)} ({_format_seconds(elapsed_seconds)})"
                    ),
                    tokens=_scenario_token_summary(record),
                ),
            )
    if completed_count == 0:
        lines.append("| - | - | - | - | 실행 완료 시나리오 없음 | - | - |")
    return lines


def _scenario_token_summary(record: dict[str, Any] | None) -> str:
    if record is None:
        return "N/A"

    llm_calls = record.get("llm_calls") or []
    if not llm_calls:
        return "0 / 0 / 0"

    totals = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    for call in llm_calls:
        if not isinstance(call, dict) or not isinstance(call.get("usage"), dict):
            return "N/A"
        usage = call["usage"]
        for field in totals:
            value = usage.get(field)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                return "N/A"
            totals[field] += value

    return (
        f"{totals['prompt_tokens']:,} / "
        f"{totals['completion_tokens']:,} / "
        f"{totals['total_tokens']:,}"
    )


def _group_context(
    records: list[dict[str, Any]],
    errors: list[dict[str, Any]],
) -> dict[str, Any]:
    for item in [*records, *errors]:
        context = item.get("context") or {}
        if context:
            return context
    return {}


def _group_scenario_contexts(
    records: list[dict[str, Any]],
    errors: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        context
        for item in [*records, *errors]
        if (context := item.get("context") or {})
    ]


def _failed_scenario_detail_lines(
    error: dict[str, Any],
    *,
    heading_level: int,
    target_parameter: str | None = None,
) -> list[str]:
    heading = "#" * heading_level
    detail_heading = "#" * min(6, heading_level + 1)
    context = error.get("context") or {}
    scenario = context.get("scenario") or {}
    scenario_title = scenario.get("title") or error.get("scenario_title") or ""
    attempts = error.get("attempt_traces") or []
    if not attempts:
        attempts = [
            {
                "attempt": error.get("attempts") or 1,
                "elapsed_seconds": error.get("elapsed_seconds"),
                "error": error.get("error"),
                "failed_stage": "unknown",
                "step_summary": error.get("step_summary") or {},
                "llm_calls": error.get("llm_calls") or [],
            },
        ]

    lines = [
        f"{heading} scenario_id={error['scenario_id']} {scenario_title}",
        "",
    ]
    if target_parameter is not None:
        lines.append(f"- target_parameter: `{target_parameter}`")
    lines.extend(
        [
            "- result: FAIL",
            f"- 소요시간: {_format_duration(error.get('elapsed_seconds'))} ({_format_seconds(error.get('elapsed_seconds'))})",
            f"- attempts: {error.get('attempts') or len(attempts)}",
            f"- 소요시간 특이사항: {_timing_special_note(elapsed_seconds=error.get('elapsed_seconds'), attempts=int(error.get('attempts') or len(attempts)), failed=True, error=error.get('error'))}",
            "- Confirmation: N/A · proposal 실패로 미수행",
            f"- final_error: `{_md_cell(error.get('error') or 'N/A', max_chars=1200)}`",
            "",
            f"{detail_heading} Scenario Major Info",
            "",
            "```json",
            _json_pretty(
                _scenario_context(context)
                if context
                else {
                    "scenario_id": error.get("scenario_id"),
                    "trace_status": "scenario context 수집 실패",
                },
            ),
            "```",
            "",
            f"{detail_heading} Attempt별 단계 Tracing",
            "",
        ],
    )

    for attempt_trace in attempts:
        trace = dict(attempt_trace)
        trace.setdefault("error", error.get("error"))
        expected_names = [
            _candidate_parameter_name(candidate)
            for candidate in (trace.get("expected_candidates") or [])
        ]
        selected_names = [
            _parameter_name(adjustment)
            for adjustment in _selected_adjustments(trace.get("result") or {})
        ]
        lines.extend(
            [
                f"**Attempt {trace.get('attempt') or 1}**",
                "",
                f"- elapsed: {_format_duration(trace.get('elapsed_seconds'))} ({_format_seconds(trace.get('elapsed_seconds'))})",
                f"- failed_stage: `{trace.get('failed_stage') or 'unknown'}`",
                f"- expected_parameters: `{_json_preview(expected_names)}`",
                f"- selected_parameters: `{_json_preview(selected_names)}`",
                f"- validation_warnings: `{_json_preview((trace.get('result') or {}).get('validation_warnings') or [], max_chars=1600)}`",
                f"- error: `{_md_cell(trace.get('error') or 'N/A', max_chars=1200)}`",
            ],
        )
        lines.extend(
            _failure_stage_trace_table_lines(
                trace,
                heading="**단계별 Failure Trace**",
            ),
        )
        lines.extend(
            _llm_call_table_lines(
                trace.get("llm_calls") or [],
                heading="**모델 호출별 소요시간 및 Token**",
            ),
        )
        lines.append("")
    return lines


def _target_parameter_present_in_record(
    record: dict[str, Any],
    target_parameter: str,
) -> bool:
    expected_present = any(
        _parameter_name_matches(_candidate_parameter_name(candidate), target_parameter)
        for candidate in record.get("expected_candidates") or []
    )
    selected_present = any(
        _parameter_name_matches(adjustment.get("parameter_name"), target_parameter)
        for adjustment in _selected_adjustments(record.get("result") or {})
    )
    return expected_present and selected_present


def _group_status(target: EventTypeTarget, records: list[dict[str, Any]], errors: list[dict[str, Any]]) -> bool:
    group_records = _records_for_target(target, records)
    group_errors = _errors_for_target(target, errors)
    has_expected = any(record["expected_candidates"] for record in group_records)
    has_selected = any(_selected_adjustments(record["result"]) for record in group_records)
    value_diff_ok = (
        len(group_records) <= 1
        or not has_expected
        or not has_selected
        or len({_signature(record) for record in group_records}) > 1
    )
    target_parameter_ok = target.target_parameter is None or (
        bool(group_records)
        and all(
            _target_parameter_present_in_record(record, target.target_parameter)
            for record in group_records
        )
    )
    return (
        not group_errors
        and len(group_records) == len(target.scenario_ids)
        and all(record["mapping_ok"] for record in group_records)
        and all(record["selected_ok"] for record in group_records)
        and target_parameter_ok
        and value_diff_ok
    )


def _parameter_scenario_status(
    targets: tuple[EventTypeTarget, ...],
    records: list[dict[str, Any]],
    errors: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    return {
        target.target_parameter: {
            "scenario_ids": list(target.scenario_ids),
            "passed": _group_status(target, records, errors),
        }
        for target in targets
        if target.target_parameter is not None
    }


def _group_has_target_parameter(
    group_records: list[dict[str, Any]],
    target_parameter: str,
) -> bool:
    for record in group_records:
        if any(
            _parameter_name_matches(_candidate_parameter_name(candidate), target_parameter)
            for candidate in record.get("expected_candidates") or []
        ):
            return True
        if any(
            _parameter_name_matches(_parameter_name(parameter), target_parameter)
            for parameter in _proposal_parameters_from_record(record)
        ):
            return True
        context = record.get("context") or {}
        mapping_context = _dimension_parameter_mapping_context(context)
        for mapping in mapping_context.get("dimension_parameter_mappings") or []:
            if _parameter_name_matches(mapping.get("parameter"), target_parameter):
                return True
    return False


def _render_parameter_ordered_result_lines(
    *,
    target_parameters: tuple[str, ...],
    targets: tuple[EventTypeTarget, ...],
    records: list[dict[str, Any]],
    errors: list[dict[str, Any]],
    target_event_type_l2_ids_by_parameter: dict[str, tuple[int, ...]],
) -> list[str]:
    lines: list[str] = []
    for target_parameter in target_parameters:
        parameter_event_type_ids = _target_event_type_ids(
            target_event_type_l2_ids_by_parameter,
            target_parameter,
        )
        matching_targets: list[EventTypeTarget] = []
        for target in targets:
            group_records = _records_for_target(target, records)
            if target.target_parameter is not None:
                if _parameter_name_matches(
                    target.target_parameter,
                    target_parameter,
                ):
                    matching_targets.append(target)
                continue
            if parameter_event_type_ids:
                if target.event_type_l2_id in parameter_event_type_ids:
                    matching_targets.append(target)
                continue
            if group_records and _group_has_target_parameter(
                group_records,
                target_parameter,
            ):
                matching_targets.append(target)

        lines.extend(
            [
                f"### Parameter: {target_parameter}",
                "",
            ],
        )
        if not matching_targets:
            lines.extend(
                [
                    "- 해당 파라미터와 매핑되거나 제안된 event_type/scenario가 없습니다.",
                    "",
                ],
            )
            continue

        for target in matching_targets:
            group_records = sorted(
                _records_for_target(target, records),
                key=lambda item: item["scenario_id"],
            )
            group_errors = _errors_for_target(target, errors)
            signatures = {_signature(record) for record in group_records}
            has_expected = any(record["expected_candidates"] for record in group_records)
            has_selected = any(
                _selected_adjustments(record["result"])
                for record in group_records
            )
            value_diff_status = "N/A"
            if len(group_records) > 1 and has_expected and has_selected:
                value_diff_status = "PASS" if len(signatures) > 1 else "FAIL"
            group_ok = _group_status(target, records, errors)
            group_context = _group_context(group_records, group_errors)

            lines.extend(
                [
                    f"#### event_type_l2_id={target.event_type_l2_id} {target.event_type_label}",
                    "",
                    "##### Scenario Group",
                    "",
                    "```json",
                    _json_pretty(_scenario_group_context(group_context, target)),
                    "```",
                    "",
                    "##### Dimension Template",
                    "",
                    "```json",
                    _json_pretty(group_context.get("dimension_template") or []),
                    "```",
                    "",
                    "##### Dimension -> Parameter Mapping",
                    "",
                    "```json",
                    _json_pretty(
                        _dimension_parameter_mapping_context(
                            group_context,
                            _group_scenario_contexts(group_records, group_errors),
                        ),
                    ),
                    "```",
                    "",
                    "##### Event",
                    "",
                    "```json",
                    _json_pretty(_event_context(group_context)),
                    "```",
                    "",
                    "##### Group Test Summary",
                    "",
                    f"- 대상 scenario_ids: {list(target.scenario_ids)}",
                    f"- scenario_count: {len(target.scenario_ids)}",
                    f"- 매핑 후보 검증: {'PASS' if all(record['mapping_ok'] for record in group_records) and not group_errors else 'FAIL'}",
                    f"- LLM selected 검증: {'PASS' if all(record['selected_ok'] for record in group_records) and not group_errors else 'FAIL'}",
                    f"- 라우팅 선택 검증: {', '.join(sorted({record['routing_status'] for record in group_records})) if group_records else 'N/A'}",
                    f"- scenario별 value 차이: {value_diff_status}",
                    f"- 그룹 종합: {'PASS' if group_ok else 'FAIL'}",
                    f"- 실패 scenario_ids: {[error['scenario_id'] for error in group_errors]}",
                    "",
                ],
            )
            for error in group_errors:
                lines.extend(
                    _failed_scenario_detail_lines(
                        error,
                        heading_level=5,
                        target_parameter=target_parameter,
                    ),
                )

            for record in group_records:
                context = record["context"]
                scenario = context.get("scenario") or {}
                expected_names = [
                    _candidate_parameter_name(candidate)
                    for candidate in record["expected_candidates"]
                ]
                target_expected_names = [
                    name
                    for name in expected_names
                    if _parameter_name_matches(name, target_parameter)
                ]
                selected = _selected_adjustments(record["result"])
                actual_names = [adjustment.get("parameter_name") for adjustment in selected]
                target_actual_names = [
                    str(name)
                    for name in actual_names
                    if _parameter_name_matches(name, target_parameter)
                ]
                proposal_parameters = _filter_parameters_by_name(
                    _proposal_parameters_from_record(record),
                    target_parameter,
                )
                timing_note = _timing_special_note(
                    elapsed_seconds=record.get("elapsed_seconds"),
                    attempts=int(record.get("attempt") or 1),
                )
                lines.extend(
                    [
                        f"##### scenario_id={record['scenario_id']} {scenario.get('title') or ''}",
                        "",
                        f"- target_parameter: `{target_parameter}`",
                        f"- target_expected_present: {'YES' if target_expected_names else 'NO'}",
                        f"- target_selected_present: {'YES' if target_actual_names else 'NO'}",
                        f"- 소요시간: {_format_duration(record.get('elapsed_seconds'))} ({_format_seconds(record.get('elapsed_seconds'))})",
                        f"- attempt: {record.get('attempt') or 1}",
                        f"- 소요시간 특이사항: {timing_note}",
                        "",
                        "###### Scenario Major Info",
                        "",
                        "```json",
                        _json_pretty(_scenario_context(context)),
                        "```",
                        "",
                        "###### Validation Summary",
                        "",
                        f"- target_expected_parameters: `{_json_preview(target_expected_names)}`",
                        f"- target_selected_parameters: `{_json_preview(target_actual_names)}`",
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
                if record.get("basecase_warnings"):
                    lines.append(f"- basecase_warnings: `{_json_preview(record['basecase_warnings'])}`")
                lines.extend(_stage_summary_table_lines(record.get("step_summary") or {}))
                lines.extend(
                    [
                        "",
                        "###### Proposed Parameter Summary",
                        "",
                        *_proposal_parameter_table_lines(proposal_parameters),
                        "",
                        "###### Proposed Parameter Values",
                        "",
                        *_proposal_value_table_lines(proposal_parameters),
                        "###### Final DB Proposal Row",
                        "",
                        "- source_table: `tmm_mi_model_param_proposal_m`",
                        "",
                        "```json",
                        _json_pretty(record.get("proposal_db_row") or {}),
                        "```",
                        "",
                    ],
                )
                lines.extend(_llm_call_table_lines(record.get("llm_calls") or []))
                lines.append("")
    return lines


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
    target_parameters: tuple[str, ...] = (),
    target_event_type_l2_ids_by_parameter: dict[str, tuple[int, ...]] | None = None,
) -> str:
    event_group_ids: dict[int, set[int]] = defaultdict(set)
    event_scenario_count: dict[int, int] = defaultdict(int)
    for target in targets:
        event_group_ids[target.event_type_l2_id].add(target.scenario_group_id)
        event_scenario_count[target.event_type_l2_id] += len(target.scenario_ids)

    report_title = (
        "# Model Parameter Proposal Evaluation - Parameters"
        if target_parameters
        else "# Model Parameter Proposal Evaluation - Event Types"
    )
    parameter_scenario_scope = {
        target.target_parameter: list(target.scenario_ids) for target in targets if target.target_parameter is not None
    }
    planned_execution_count = sum(len(target.scenario_ids) for target in targets)
    target_collection_method = (
        "명시적 parameter=scenario_id를 검증하고 midb에서 event/group context 조회"
        if parameter_scenario_scope
        else "midb의 scenario_group/scenario를 event_type_l2_id 기준으로 동적 조회"
    )
    lines: list[str] = [
        report_title,
        "",
        f"- 실행 시작: {started_at.isoformat(timespec='seconds')}",
        f"- 실행 종료: {finished_at.isoformat(timespec='seconds')}",
        f"- 총 소요시간: {_format_duration((finished_at - started_at).total_seconds())} ({_format_seconds((finished_at - started_at).total_seconds())})",
        f"- 대상 event_type_l2_ids: {list(event_type_l2_ids)}",
        f"- 대상 parameters: {list(target_parameters)}",
        f"- concurrency: {concurrency}",
        f"- retries: {retries}",
        f"- parameter_scenarios: {parameter_scenario_scope}",
        f"- planned scenario executions: {planned_execution_count}",
        f"- 대상 수집 방식: {target_collection_method}",
        "- 호출 방식: 내부 raw graph 실행 후 `to_output()`으로 final response 생성",
        _lut_summary_line(records),
        "",
        "## 소요시간 특이사항 요약",
        "",
        f"- 소요시간 특이사항: {_timing_special_summary(records, errors)}",
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
            f"scenario_group {len(event_group_ids[event_type_l2_id])}개, "
            f"scenario {event_scenario_count[event_type_l2_id]}개",
        )

    lines.extend(
        [
            "",
            *_scenario_result_table_lines(
                targets=targets,
                records=records,
                errors=errors,
                target_parameters=target_parameters,
                target_event_type_l2_ids_by_parameter=(
                    target_event_type_l2_ids_by_parameter or {}
                ),
            ),
        ],
    )
    lines.extend(["", "## 호출 결과", ""])

    records_by_group: dict[int, list[dict[str, Any]]] = defaultdict(list)
    errors_by_group: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        records_by_group[int(record["target"].scenario_group_id)].append(record)
    for error in errors:
        errors_by_group[int(error["target"].scenario_group_id)].append(error)

    target_event_type_l2_ids_by_parameter = target_event_type_l2_ids_by_parameter or {}
    if target_parameters:
        lines.extend(
            _render_parameter_ordered_result_lines(
                target_parameters=target_parameters,
                targets=targets,
                records=records,
                errors=errors,
                target_event_type_l2_ids_by_parameter=target_event_type_l2_ids_by_parameter,
            ),
        )
        targets_for_default_render: tuple[EventTypeTarget, ...] = ()
    else:
        targets_for_default_render = targets

    for target in targets_for_default_render:
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
        group_context = _group_context(group_records, group_errors)
        lines.extend(
            [
                f"### event_type_l2_id={target.event_type_l2_id} {target.event_type_label}",
                "",
                "#### Scenario Group",
                "",
                "```json",
                _json_pretty(_scenario_group_context(group_context, target)),
                "```",
                "",
                "#### Dimension Template",
                "",
                "```json",
                _json_pretty(group_context.get("dimension_template") or []),
                "```",
                "",
                "#### Dimension -> Parameter Mapping",
                "",
                "```json",
                _json_pretty(
                    _dimension_parameter_mapping_context(
                        group_context,
                        _group_scenario_contexts(group_records, group_errors),
                    ),
                ),
                "```",
                "",
                "#### Event",
                "",
                "```json",
                _json_pretty(_event_context(group_context)),
                "```",
                "",
                "#### Group Test Summary",
                "",
                f"- 대상 scenario_ids: {list(target.scenario_ids)}",
                f"- scenario_count: {len(target.scenario_ids)}",
                f"- 매핑 후보 검증: {'PASS' if all(record['mapping_ok'] for record in group_records) and not group_errors else 'FAIL'}",
                f"- LLM selected 검증: {'PASS' if all(record['selected_ok'] for record in group_records) and not group_errors else 'FAIL'}",
                f"- 라우팅 선택 검증: {', '.join(sorted({record['routing_status'] for record in group_records})) if group_records else 'N/A'}",
                f"- scenario별 value 차이: {value_diff_status}",
                f"- 그룹 종합: {'PASS' if group_ok else 'FAIL'}",
                f"- 실패 scenario_ids: {[error['scenario_id'] for error in group_errors]}",
                "",
            ],
        )
        for error in group_errors:
            lines.extend(
                _failed_scenario_detail_lines(
                    error,
                    heading_level=4,
                ),
            )

        for record in group_records:
            context = record["context"]
            scenario = context.get("scenario") or {}
            expected_names = [
                candidate.get("canonical_parameter_name") or candidate.get("parameter_name")
                for candidate in record["expected_candidates"]
            ]
            selected = _selected_adjustments(record["result"])
            actual_names = [adjustment.get("parameter_name") for adjustment in selected]
            timing_note = _timing_special_note(
                elapsed_seconds=record.get("elapsed_seconds"),
                attempts=int(record.get("attempt") or 1),
            )
            lines.extend(
                [
                    f"#### scenario_id={record['scenario_id']} {scenario.get('title') or ''}",
                    "",
                    f"- 소요시간: {_format_duration(record.get('elapsed_seconds'))} ({_format_seconds(record.get('elapsed_seconds'))})",
                    f"- attempt: {record.get('attempt') or 1}",
                    f"- 소요시간 특이사항: {timing_note}",
                    "",
                    "##### Scenario Major Info",
                    "",
                    "```json",
                    _json_pretty(_scenario_context(context)),
                    "```",
                    "",
                    "##### Validation Summary",
                    "",
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
            if record.get("basecase_warnings"):
                lines.append(f"- basecase_warnings: `{_json_preview(record['basecase_warnings'])}`")
            lines.extend(_stage_summary_table_lines(record.get("step_summary") or {}))
            proposal_parameters = _proposal_parameters_from_record(record)
            lines.extend(
                [
                    "",
                    "##### Proposed Parameter Summary",
                    "",
                    *_proposal_parameter_table_lines(proposal_parameters),
                    "",
                    "##### Proposed Parameter Values",
                    "",
                    *_proposal_value_table_lines(proposal_parameters),
                    "##### Final DB Proposal Row",
                    "",
                    "- source_table: `tmm_mi_model_param_proposal_m`",
                    "",
                    "```json",
                    _json_pretty(record.get("proposal_db_row") or {}),
                    "```",
                    "",
                ],
            )
            lines.extend(_llm_call_table_lines(record.get("llm_calls") or []))
            lines.append("")

    group_status = (
        _parameter_scenario_status(targets, records, errors)
        if parameter_scenario_scope
        else {_target_status_key(target): _group_status(target, records, errors) for target in targets}
    )
    empty_recommendation_records: list[dict[str, Any]] = []
    for record in sorted(records, key=lambda item: (item["target"].scenario_group_id, item["scenario_id"])):
        target = record["target"]
        proposal_parameters = _filter_parameters_by_name(
            _proposal_parameters(record["final_response"]),
            target.target_parameter,
        )
        if not proposal_parameters:
            empty_recommendation_records.append(
                {
                    "target_parameter": target.target_parameter,
                    "scenario_group_id": target.scenario_group_id,
                    "scenario_id": record["scenario_id"],
                    "title": (record["context"].get("scenario") or {}).get("title"),
                },
            )
    status_label = (
        "PARAMETER_SCENARIO_STATUS"
        if parameter_scenario_scope
        else "GROUP_STATUS_BY_SCENARIO_GROUP"
    )
    lines.extend(
        [
            "## 최종 요약",
            "",
            f"- ERROR_COUNT: {len(errors)}",
            f"- PLANNED_SCENARIO_EXECUTIONS: {planned_execution_count}",
            f"- COMPLETED_SCENARIO_EXECUTIONS: {len(records) + len(errors)}",
            f"- PARAMETER_SCENARIOS: `{json.dumps(parameter_scenario_scope, ensure_ascii=False, sort_keys=True)}`",
            f"- {status_label}: `{json.dumps(group_status, ensure_ascii=False, sort_keys=True)}`",
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
        lines.append("- 시나리오 단위 오류 및 재실행 없음.")
    lines.append("")
    return "\n".join(lines)


async def run_event_type_evaluation(
    *,
    event_type_l2_ids: tuple[int, ...],
    concurrency: int,
    retries: int,
    group_title_prefix: str | None = None,
    groups_per_event: int | None = None,
    scenarios_per_group: int | None = None,
    target_parameters: tuple[str, ...] = (),
    resolve_event_type_l2_ids_from_parameters: bool = False,
    parameter_scenarios: tuple[ParameterScenarioSelection, ...] = (),
) -> Path:
    await _ensure_model_parameter_test_resource_runtime()
    target_event_type_l2_ids_by_parameter = (
        _discover_event_type_l2_ids_for_parameters(target_parameters) if target_parameters else {}
    )
    resolved_event_type_l2_ids, targets, parameter_scenarios = _resolve_evaluation_scope(
        event_type_l2_ids=event_type_l2_ids,
        group_title_prefix=group_title_prefix,
        groups_per_event=groups_per_event,
        scenarios_per_group=scenarios_per_group,
        target_parameters=target_parameters,
        target_event_type_l2_ids_by_parameter=target_event_type_l2_ids_by_parameter,
        resolve_event_type_l2_ids_from_parameters=resolve_event_type_l2_ids_from_parameters,
        parameter_scenarios=parameter_scenarios,
    )
    report_event_type_l2_ids = resolved_event_type_l2_ids or tuple(
        sorted({target.event_type_l2_id for target in targets})
    )
    started_at = datetime.now()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    event_id_part = "_".join(str(item) for item in report_event_type_l2_ids) or "none"
    timestamp = started_at.strftime("%Y%m%d_%H%M%S")
    if target_parameters:
        parameter_part = "_".join(
            "".join(
                char if char.isalnum() or char in {"-", "_"} else "_"
                for char in parameter
            )
            for parameter in target_parameters
        )
        report_path = REPORT_DIR / (
            f"model_parameter_proposal_evaluation_parameters_{parameter_part}_"
            f"{timestamp}.md"
        )
    else:
        report_path = REPORT_DIR / (
            f"model_parameter_proposal_evaluation_event_types_{event_id_part}_"
            f"{timestamp}.md"
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
                target_parameters=target_parameters,
                target_event_type_l2_ids_by_parameter=target_event_type_l2_ids_by_parameter,
            ),
            encoding="utf-8",
        )

    async def run_one(target: EventTypeTarget, scenario_id: int) -> None:
        async with semaphore:
            last_error: Exception | None = None
            attempt_traces: list[dict[str, Any]] = []
            scenario_started_at = datetime.now()
            scenario_started_monotonic = time.perf_counter()
            for attempt in range(retries + 1):
                attempt_started_monotonic = time.perf_counter()
                try:
                    result = await _evaluate_scenario(scenario_id)
                    elapsed_seconds = time.perf_counter() - scenario_started_monotonic
                    result["target"] = target
                    result["attempt"] = attempt + 1
                    result["started_at"] = scenario_started_at.isoformat(timespec="seconds")
                    result["finished_at"] = datetime.now().isoformat(timespec="seconds")
                    result["elapsed_seconds"] = elapsed_seconds
                    result["proposal_db_row"] = _fetch_proposal_db_row(
                        _proposal_id(result.get("final_response") or {}),
                    )
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
                    attempt_elapsed_seconds = time.perf_counter() - attempt_started_monotonic
                    attempt_trace = {
                        **_failure_trace_from_exception(exc),
                        "attempt": attempt + 1,
                        "elapsed_seconds": attempt_elapsed_seconds,
                        "error": repr(exc),
                    }
                    attempt_traces.append(attempt_trace)
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
                    context = next(
                        (
                            trace.get("context") or {}
                            for trace in reversed(attempt_traces)
                            if trace.get("context")
                        ),
                        {},
                    )
                    scenario = context.get("scenario") or {}
                    final_trace = attempt_traces[-1] if attempt_traces else {}
                    errors.append(
                        {
                            "target": target,
                            "scenario_id": scenario_id,
                            "scenario_title": scenario.get("title") or "",
                            "context": context,
                            "error": repr(last_error),
                            "attempts": len(attempt_traces) or retries + 1,
                            "attempt_traces": attempt_traces,
                            "step_summary": final_trace.get("step_summary") or {},
                            "llm_calls": final_trace.get("llm_calls") or [],
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
    if target_parameters:
        print("TARGET_PARAMETERS", json.dumps(list(target_parameters), ensure_ascii=False))
        if parameter_scenarios:
            print(
                "PARAMETER_SCENARIOS",
                json.dumps(
                    {selection.parameter_name: list(selection.scenario_ids) for selection in parameter_scenarios},
                    ensure_ascii=False,
                ),
            )
        print(
            "TARGET_EVENT_TYPE_L2_IDS_BY_PARAMETER",
            json.dumps(
                target_event_type_l2_ids_by_parameter,
                ensure_ascii=False,
                sort_keys=True,
            ),
        )
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
    print("SCENARIO_EXECUTION_COUNT", len(records) + len(errors))
    if parameter_scenarios:
        print(
            "PARAMETER_SCENARIO_STATUS",
            json.dumps(
                _parameter_scenario_status(targets, records, errors),
                ensure_ascii=False,
                sort_keys=True,
            ),
        )
    print(
        "GROUP_STATUS_BY_SCENARIO_GROUP",
        json.dumps(
            {_target_status_key(target): _group_status(target, records, errors) for target in targets},
            ensure_ascii=False,
            sort_keys=True,
        ),
    )
    return report_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event-type-l2-ids", nargs="+", type=int, default=())
    parser.add_argument("--all-event-types", action="store_true")
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--group-title-prefix", default=None)
    parser.add_argument("--groups-per-event", type=int, default=None)
    parser.add_argument("--scenarios-per-group", type=int, default=None)
    parser.add_argument("--target-parameters", nargs="+", default=())
    parser.add_argument(
        "--parameter-scenarios",
        nargs="+",
        default=(),
        metavar="PARAMETER=SCENARIO_ID[,SCENARIO_ID...]",
    )
    args = parser.parse_args()
    if not args.all_event_types and not args.event_type_l2_ids and not args.target_parameters:
        parser.error("--event-type-l2-ids, --all-event-types, or --target-parameters is required")
    try:
        parameter_scenarios = _parse_parameter_scenarios(
            tuple(args.parameter_scenarios),
            tuple(args.target_parameters),
        )
    except ValueError as exc:
        parser.error(str(exc))
    if parameter_scenarios:
        if args.all_event_types or args.event_type_l2_ids:
            parser.error(
                "--parameter-scenarios cannot be combined with --all-event-types or --event-type-l2-ids",
            )
        if args.group_title_prefix or args.groups_per_event is not None or args.scenarios_per_group is not None:
            parser.error(
                "--parameter-scenarios cannot be combined with group/scenario discovery filters",
            )
    try:
        asyncio.run(
            run_event_type_evaluation(
                event_type_l2_ids=(() if args.all_event_types else tuple(args.event_type_l2_ids)),
                concurrency=args.concurrency,
                retries=args.retries,
                group_title_prefix=args.group_title_prefix,
                groups_per_event=args.groups_per_event,
                scenarios_per_group=args.scenarios_per_group,
                target_parameters=tuple(args.target_parameters),
                resolve_event_type_l2_ids_from_parameters=(
                    bool(args.target_parameters)
                    and not args.all_event_types
                    and not args.event_type_l2_ids
                    and not parameter_scenarios
                ),
                parameter_scenarios=parameter_scenarios,
            ),
        )
    except ValueError as exc:
        if parameter_scenarios:
            parser.error(str(exc))
        raise


if __name__ == "__main__":
    main()
