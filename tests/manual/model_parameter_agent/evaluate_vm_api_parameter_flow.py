from __future__ import annotations

import argparse
import asyncio
from datetime import datetime
import json
import os
from pathlib import Path
import sys
import time
from typing import Any

import httpx


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

from apps.agents.model_parameter_agent.persistence.model_parameter_service import (  # noqa: E402
    ModelParameterService,
)
from apps.agents.model_parameter_agent.utils.parameter_mapping import (  # noqa: E402
    get_parameter_knowledge_base,
    match_parameter_candidates,
    partition_proposal_parameter_candidates,
)
from tests.manual.model_parameter_agent.evaluate_event_type_proposals import (  # noqa: E402
    REPORT_DIR,
    EventTypeTarget,
    _candidate_parameter_name,
    _discover_event_type_l2_ids_for_parameters,
    _discover_targets,
    _fetch_proposal_db_row,
    _filter_parameters_by_name,
    _format_duration,
    _format_seconds,
    _parameter_name,
    _parameter_name_matches,
    _parameter_values,
    _proposal_parameters_from_record,
    _render_report,
    _slot_axis_field_names,
    _slot_coordinates_for_value,
)
from tests.manual.model_parameter_agent.evaluate_proposals import (  # noqa: E402
    _selected_adjustments,
    _value_signature,
)


DEFAULT_TARGET_PARAMETERS = (
    "GDP",
    "PMI",
    "PowerMix",
    "Temperature",
    "LiqUtilAdjustment",
)


def _md_cell(value: Any, *, max_chars: int = 700) -> str:
    if isinstance(value, str):
        text = value
    else:
        text = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    if len(text) > max_chars:
        text = text[:max_chars].rstrip() + "..."
    return text.replace("\n", "<br>").replace("|", "\\|")


def _normalize_name(value: Any) -> str:
    return str(value or "").strip().lower()


def _model_target(parameter: dict[str, Any]) -> dict[str, Any]:
    target = parameter.get("modelTarget") or parameter.get("model_target") or {}
    return target if isinstance(target, dict) else {}


def _target_value(target: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in target:
            return target.get(key)
    return None


def _proposal_to_adjustments(
    proposal_parameters: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    candidate_by_name: dict[str, list[dict[str, Any]]] = {}
    for candidate in candidates:
        candidate_by_name.setdefault(
            _normalize_name(_candidate_parameter_name(candidate)),
            [],
        ).append(candidate)

    adjustments: list[dict[str, Any]] = []
    used_candidate_keys: set[str] = set()
    for parameter in proposal_parameters:
        parameter_name = _parameter_name(parameter)
        target = _model_target(parameter)
        model_file = str(_target_value(target, "modelFile", "model_file") or "")
        model_sheet = str(_target_value(target, "modelSheet", "model_sheet") or "")
        matching_candidates = candidate_by_name.get(_normalize_name(parameter_name), [])
        selected_candidate = next(
            (
                candidate
                for candidate in matching_candidates
                if str(candidate.get("model_file") or "") == model_file
                and str(candidate.get("model_sheet") or "") == model_sheet
                and str(candidate.get("candidate_key") or "") not in used_candidate_keys
            ),
            None,
        )
        if selected_candidate is None and matching_candidates:
            selected_candidate = next(
                (
                    candidate
                    for candidate in matching_candidates
                    if str(candidate.get("candidate_key") or "") not in used_candidate_keys
                ),
                matching_candidates[0],
            )
        candidate_key = (
            str(selected_candidate.get("candidate_key"))
            if selected_candidate is not None
            else f"api-response|{parameter_name}|{model_file}|{model_sheet}"
        )
        used_candidate_keys.add(candidate_key)
        slot_axes = [{"axis_name": axis} for axis in _slot_axis_field_names(parameter)]
        value_grid = []
        for value in _parameter_values(parameter):
            value_grid.append(
                {
                    "coordinates": _slot_coordinates_for_value(parameter, value),
                    "basecase_value": value.get("basecaseValue"),
                    "proposed_value": value.get("proposedValue"),
                    "operation": "set",
                    "rationale": value.get("rationale"),
                },
            )
        adjustments.append(
            {
                "candidate_key": candidate_key,
                "parameter_name": parameter_name,
                "model_file": model_file,
                "model_sheet": model_sheet,
                "selected": True,
                "rationale": parameter.get("rationale"),
                "slot_axes": slot_axes,
                "value_grid": value_grid,
            },
        )
    return adjustments


def _selected_parameter_names(result: dict[str, Any]) -> set[str]:
    return {
        _normalize_name(adjustment.get("parameter_name"))
        for adjustment in _selected_adjustments(result)
        if str(adjustment.get("parameter_name") or "").strip()
    }


def _review_api_selection(
    candidates: list[dict[str, Any]],
    result: dict[str, Any],
) -> tuple[bool, list[str], bool, list[str], str, list[str]]:
    candidate_names = {
        _normalize_name(_candidate_parameter_name(candidate))
        for candidate in candidates
        if _candidate_parameter_name(candidate)
    }
    direct_names = {
        _normalize_name(_candidate_parameter_name(candidate))
        for candidate in candidates
        if str(candidate.get("mapping_method") or "").lower() == "direct"
        and _candidate_parameter_name(candidate)
    }
    routing_names = {
        _normalize_name(_candidate_parameter_name(candidate))
        for candidate in candidates
        if str(candidate.get("mapping_method") or "").lower() == "routing"
        and _candidate_parameter_name(candidate)
    }
    selected_names = _selected_parameter_names(result)
    unknown_selected = sorted(selected_names - candidate_names)
    direct_missing = sorted(direct_names - selected_names)

    mapping_messages: list[str] = []
    if unknown_selected:
        mapping_messages.append(f"unknown_selected_parameters={unknown_selected}")
    if direct_missing:
        mapping_messages.append(f"direct_mapping_parameters_not_selected={direct_missing}")
    mapping_ok = not mapping_messages

    selected_messages: list[str] = []
    if candidates and not selected_names:
        selected_messages.append("proposal_parameters가 비어 있습니다.")
    if unknown_selected:
        selected_messages.append(f"후보 밖 parameter가 최종 proposal에 포함됐습니다: {unknown_selected}")
    selected_ok = not selected_messages

    routing_messages: list[str] = []
    routing_status = "N/A"
    if routing_names:
        selected_routing = sorted(routing_names & selected_names)
        if not selected_routing:
            routing_messages.append("routing 후보군 중 선택된 parameter가 없습니다.")
        if len(routing_names) > 1 and routing_names.issubset(selected_names):
            routing_messages.append("routing 후보군이 모두 선택되어 라우팅 구분 근거 검토가 필요합니다.")
        routing_status = "PASS" if not routing_messages else "REVIEW"

    return mapping_ok, mapping_messages, selected_ok, selected_messages, routing_status, routing_messages


def _build_api_step_summary(
    *,
    candidates: list[dict[str, Any]],
    proposal_parameters: list[dict[str, Any]],
    result: dict[str, Any],
    routing_status: str,
    api_calls: list[dict[str, Any]],
) -> dict[str, Any]:
    value_count = sum(len(_parameter_values(parameter)) for parameter in proposal_parameters)
    value_with_basecase_count = sum(
        1
        for parameter in proposal_parameters
        for value in _parameter_values(parameter)
        if value.get("basecaseValue") is not None
    )
    selected_parameter_count = len(_selected_adjustments(result))
    if not candidates:
        parameter_status = "N/A"
        termination_stage = "Step1 종료 - VM DB 매핑 후보 없음"
    elif not proposal_parameters:
        parameter_status = "FAIL"
        termination_stage = "비동기 proposal 종료 - 최종 proposalParameters 없음"
    elif routing_status == "REVIEW":
        parameter_status = "REVIEW"
        termination_stage = "비동기 proposal 완료 - routing 검토 필요"
    else:
        parameter_status = "PASS"
        termination_stage = "비동기 proposal 완료 - DB proposal row 저장"
    return {
        "termination_stage": termination_stage,
        "parameter_status": parameter_status,
        "slot_status": "PASS" if value_count else "N/A",
        "basecase_status": "PASS" if value_with_basecase_count else "N/A",
        "value_status": "PASS" if proposal_parameters else "EMPTY",
        "rule_candidate_count": len(candidates),
        "validated_candidate_count": len(candidates),
        "selected_parameter_count": selected_parameter_count,
        "proposal_parameter_count": len(proposal_parameters),
        "slot_option_candidate_count": 0,
        "slot_option_axis_value_count": 0,
        "slot_option_axis_counts_by_candidate": {},
        "selected_slot_count": value_count,
        "slot_issue_messages": [],
        "slot_basecase_record_count": 0,
        "value_reference_record_count": value_with_basecase_count,
        "value_reference_counts_by_candidate": {},
        "value_cell_count": value_count,
        "value_cell_with_basecase_count": value_with_basecase_count,
        "value_issue_messages": [],
        "llm_steps": [],
        "api_calls": api_calls,
    }


async def _post_json(
    client: httpx.AsyncClient,
    url: str,
    payload: dict[str, Any],
) -> tuple[dict[str, Any], float, int]:
    started = time.perf_counter()
    response = await client.post(url, json=payload)
    elapsed = time.perf_counter() - started
    if response.is_error:
        try:
            error_body = response.json()
        except ValueError:
            error_body = response.text
        message = (
            f"HTTP {response.status_code} for {url}: "
            f"{_md_cell(error_body, max_chars=1200)}"
        )
        raise RuntimeError(message)
    return response.json(), elapsed, response.status_code


async def _poll_proposal_row(
    *,
    model_param_proposal_id: int,
    poll_interval: float,
    poll_timeout: float,
) -> tuple[dict[str, Any], float]:
    started = time.perf_counter()
    while True:
        row = _fetch_proposal_db_row(model_param_proposal_id)
        status = str(row.get("status") or "")
        if status in {"PROPOSED", "CONFIRMED", "FAILED"}:
            return row, time.perf_counter() - started
        elapsed = time.perf_counter() - started
        if elapsed > poll_timeout:
            message = (
                "proposal polling timed out: "
                f"model_param_proposal_id={model_param_proposal_id}, "
                f"last_status={status or row.get('fetch_status')}"
            )
            raise TimeoutError(message)
        await asyncio.sleep(poll_interval)


async def _evaluate_scenario_via_vm_api(
    *,
    client: httpx.AsyncClient,
    base_url: str,
    scenario_id: int,
    user_id: int | None,
    poll_interval: float,
    poll_timeout: float,
) -> dict[str, Any]:
    context = ModelParameterService().load_context(scenario_id)
    kb = get_parameter_knowledge_base()
    raw_candidates, non_inputs, mapping_warnings = match_parameter_candidates(kb, context)
    candidates, scope_exclusions = partition_proposal_parameter_candidates(
        raw_candidates,
    )
    non_inputs = [*non_inputs, *scope_exclusions]

    api_calls: list[dict[str, Any]] = []
    proposal_payload = {"userId": user_id} if user_id is not None else {}
    proposal_response, proposal_elapsed, proposal_status_code = await _post_json(
        client,
        f"{base_url}/model-parameters/scenarios/{scenario_id}/proposals",
        proposal_payload,
    )
    api_calls.append(
        {
            "step": "POST /model-parameters/scenarios/{scenario_id}/proposals",
            "status_code": proposal_status_code,
            "elapsed_seconds": round(proposal_elapsed, 3),
        },
    )
    data = proposal_response.get("data") or {}
    model_param_proposal_id = data.get("modelParamProposalId") or data.get("model_param_proposal_id")
    if model_param_proposal_id is None:
        message = f"proposal response missing modelParamProposalId: {proposal_response}"
        raise RuntimeError(message)
    model_param_proposal_id = int(model_param_proposal_id)

    proposal_db_row, poll_elapsed = await _poll_proposal_row(
        model_param_proposal_id=model_param_proposal_id,
        poll_interval=poll_interval,
        poll_timeout=poll_timeout,
    )
    api_calls.append(
        {
            "step": "VM DB poll until PROPOSED",
            "status_code": None,
            "elapsed_seconds": round(poll_elapsed, 3),
        },
    )
    if proposal_db_row.get("status") == "FAILED":
        message = (
            "proposal row failed: "
            f"model_param_proposal_id={model_param_proposal_id}, "
            f"error_code={proposal_db_row.get('error_code')}, "
            f"error_message={proposal_db_row.get('error_message')}"
        )
        raise RuntimeError(message)

    proposal_parameters = proposal_db_row.get("proposal_parameters") or []
    confirmation_payload = {
        "userId": user_id,
        "data": {
            "confirmationParameters": proposal_parameters,
        },
    }
    confirmation_response, confirmation_elapsed, confirmation_status_code = await _post_json(
        client,
        f"{base_url}/model-parameters/proposals/{model_param_proposal_id}/confirmation",
        confirmation_payload,
    )
    api_calls.append(
        {
            "step": "POST /model-parameters/proposals/{modelParamProposalId}/confirmation",
            "status_code": confirmation_status_code,
            "elapsed_seconds": round(confirmation_elapsed, 3),
        },
    )
    confirmed_db_row = _fetch_proposal_db_row(model_param_proposal_id)
    final_response = {
        "status": "success",
        "message": "model parameter proposal completed via async VM API",
        "data": {
            "modelParamProposalId": model_param_proposal_id,
            "scenarioId": scenario_id,
            "scenarioGroupId": confirmed_db_row.get("scenario_group_id"),
            "eventId": confirmed_db_row.get("mi_event_id"),
            "proposalParameters": proposal_parameters,
        },
    }
    adjustments = _proposal_to_adjustments(proposal_parameters, candidates)
    result = {
        "parameter_adjustments": adjustments,
        "non_input_items": non_inputs,
        "validation_warnings": [],
    }
    (
        mapping_ok,
        mapping_messages,
        selected_ok,
        selected_messages,
        routing_status,
        routing_messages,
    ) = _review_api_selection(candidates, result)
    return {
        "scenario_id": scenario_id,
        "context": context,
        "rule_candidates": candidates,
        "expected_candidates": candidates,
        "non_input_items": non_inputs,
        "mapping_warnings": mapping_warnings,
        "basecase_warnings": [
            "VM API 비동기 black-box 실행이라 내부 basecase prompt/reference raw state는 API 응답에서 노출되지 않습니다.",
        ],
        "parameter_slots": [],
        "step_summary": _build_api_step_summary(
            candidates=candidates,
            proposal_parameters=proposal_parameters,
            result=result,
            routing_status=routing_status,
            api_calls=api_calls,
        ),
        "result": result,
        "final_response": final_response,
        "confirmation_response": confirmation_response,
        "llm_calls": [],
        "api_calls": api_calls,
        "resolved_config": {
            "execution_mode": "vm_api_async_proposal_poll_confirmation",
            "api_base_url": base_url,
            "db_source": "vmdb",
            "proposal_endpoint": "/model-parameters/scenarios/{scenario_id}/proposals",
            "confirmation_endpoint": "/model-parameters/proposals/{modelParamProposalId}/confirmation",
            "sync_endpoint_used": False,
        },
        "lut_version": None,
        "proposal_db_row": confirmed_db_row,
        "mapping_ok": mapping_ok,
        "mapping_messages": mapping_messages,
        "selected_ok": selected_ok,
        "selected_messages": selected_messages,
        "routing_status": routing_status,
        "routing_messages": routing_messages,
        "value_signature": _value_signature(adjustments),
    }


def _record_sort_key(record: dict[str, Any]) -> tuple[int, int, int]:
    target = record["target"]
    return (
        int(target.event_type_l2_id),
        int(target.scenario_group_id),
        int(record["scenario_id"]),
    )


def _render_api_call_summary(
    records: list[dict[str, Any]],
    errors: list[dict[str, Any]],
) -> list[str]:
    lines = [
        "",
        "## VM API 호출별 소요시간",
        "",
        "| event_type_l2_id | scenario_group_id | scenario_id | proposal_id | proposal_accept | db_poll | confirmation | total_api_wait | confirmation_status |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for record in sorted(records, key=_record_sort_key):
        target = record["target"]
        calls = record.get("api_calls") or []
        elapsed_by_step = {str(call.get("step")): call.get("elapsed_seconds") for call in calls}
        proposal_elapsed = elapsed_by_step.get("POST /model-parameters/scenarios/{scenario_id}/proposals")
        poll_elapsed = elapsed_by_step.get("VM DB poll until PROPOSED")
        confirmation_elapsed = elapsed_by_step.get(
            "POST /model-parameters/proposals/{modelParamProposalId}/confirmation",
        )
        total = sum(float(value or 0) for value in (proposal_elapsed, poll_elapsed, confirmation_elapsed))
        proposal_id = (record.get("proposal_db_row") or {}).get("model_param_proposal_id")
        confirmation_status = (record.get("proposal_db_row") or {}).get("status")
        lines.append(
            f"| {target.event_type_l2_id} | {target.scenario_group_id} | {record['scenario_id']} | "
            f"{proposal_id or ''} | {_format_seconds(proposal_elapsed)} | {_format_seconds(poll_elapsed)} | "
            f"{_format_seconds(confirmation_elapsed)} | {_format_seconds(total)} | {confirmation_status or ''} |",
        )
    if errors:
        lines.extend(
            [
                "",
                "### VM API 오류",
                "",
                "| event_type_l2_id | scenario_group_id | scenario_id | attempts | elapsed | error |",
                "|---:|---:|---:|---:|---:|---|",
            ],
        )
        for error in errors:
            target = error["target"]
            lines.append(
                f"| {target.event_type_l2_id} | {target.scenario_group_id} | {error['scenario_id']} | "
                f"{error.get('attempts') or 1} | {_format_seconds(error.get('elapsed_seconds'))} | "
                f"{_md_cell(error.get('error'), max_chars=500)} |",
            )
    lines.append("")
    return lines


def _target_expected_candidates(record: dict[str, Any], parameter_name: str) -> list[dict[str, Any]]:
    return [
        candidate
        for candidate in record.get("expected_candidates") or []
        if _parameter_name_matches(_candidate_parameter_name(candidate), parameter_name)
    ]


def _target_proposal_parameters(record: dict[str, Any], parameter_name: str) -> list[dict[str, Any]]:
    return _filter_parameters_by_name(
        _proposal_parameters_from_record(record),
        parameter_name,
    )


def _has_any_rationale(values: list[dict[str, Any]]) -> bool:
    return all(str(value.get("rationale") or "").strip() for value in values)


def _is_number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _value_signature_for_parameter(record: dict[str, Any], parameter_name: str) -> str:
    comparable: list[dict[str, Any]] = []
    for parameter in _target_proposal_parameters(record, parameter_name):
        comparable.append(
            {
                "parameterName": _parameter_name(parameter),
                "values": [
                    {
                        "coordinates": _slot_coordinates_for_value(parameter, value),
                        "proposedValue": value.get("proposedValue"),
                    }
                    for value in _parameter_values(parameter)
                ],
            },
        )
    return json.dumps(comparable, ensure_ascii=False, sort_keys=True, default=str)


def _render_quality_rows_for_parameter(
    parameter_name: str,
    records: list[dict[str, Any]],
    parameter_event_type_ids: tuple[int, ...],
) -> list[str]:
    scoped_records = [
        record
        for record in records
        if int(record["target"].event_type_l2_id) in set(parameter_event_type_ids)
    ]
    expected_records = [
        record for record in scoped_records if _target_expected_candidates(record, parameter_name)
    ]
    selected_records = [
        record for record in scoped_records if _target_proposal_parameters(record, parameter_name)
    ]
    all_target_parameters = [
        parameter
        for record in selected_records
        for parameter in _target_proposal_parameters(record, parameter_name)
    ]
    all_values = [
        value
        for parameter in all_target_parameters
        for value in _parameter_values(parameter)
    ]
    values_with_basecase = [value for value in all_values if value.get("basecaseValue") is not None]
    values_without_basecase = [value for value in all_values if value.get("basecaseValue") is None]

    direct_missing: list[int] = []
    routing_without_group_selection: list[int] = []
    for record in expected_records:
        target_candidates = _target_expected_candidates(record, parameter_name)
        target_selected = bool(_target_proposal_parameters(record, parameter_name))
        if any(str(candidate.get("mapping_method") or "").lower() == "direct" for candidate in target_candidates):
            if not target_selected:
                direct_missing.append(int(record["scenario_id"]))
        if any(str(candidate.get("mapping_method") or "").lower() == "routing" for candidate in target_candidates):
            routing_names = {
                _normalize_name(_candidate_parameter_name(candidate))
                for candidate in record.get("expected_candidates") or []
                if str(candidate.get("mapping_method") or "").lower() == "routing"
            }
            selected_names = {
                _normalize_name(_parameter_name(parameter))
                for parameter in _proposal_parameters_from_record(record)
            }
            if not routing_names.intersection(selected_names):
                routing_without_group_selection.append(int(record["scenario_id"]))

    rows: list[tuple[int, str, str, str, str]] = []
    if not expected_records:
        judgement = "N/A"
    elif direct_missing or routing_without_group_selection:
        judgement = "FAIL"
    elif len(selected_records) < len(expected_records):
        judgement = "REVIEW"
    else:
        judgement = "PASS"
    rows.append(
        (
            1,
            "파라미터가 정확히 선정되었나",
            judgement,
            (
                f"mapped_event_types={list(parameter_event_type_ids)}, "
                f"expected_scenarios={len(expected_records)}, selected_scenarios={len(selected_records)}, "
                f"direct_missing={direct_missing[:10]}, routing_without_group_selection={routing_without_group_selection[:10]}"
            ),
            "FAIL/REVIEW인 경우 direct/routing 매핑 후보와 Step1.5 후보 검증 결과를 비교해 누락 사유를 분리합니다.",
        ),
    )

    missing_slot_rows: list[dict[str, Any]] = []
    for record in selected_records:
        for parameter in _target_proposal_parameters(record, parameter_name):
            axes = _slot_axis_field_names(parameter)
            for value in _parameter_values(parameter):
                missing_axes = [axis for axis in axes if axis not in value or value.get(axis) in (None, "")]
                if missing_axes:
                    missing_slot_rows.append(
                        {
                            "scenario_id": record["scenario_id"],
                            "missing_axes": missing_axes,
                        },
                    )
    rows.append(
        (
            2,
            "slot이 정확히 선정되고 slot의 값이나 범위가 유효한 값인가",
            "N/A" if not all_values else ("PASS" if not missing_slot_rows else "FAIL"),
            (
                f"value_rows={len(all_values)}, missing_slot_rows={missing_slot_rows[:10]}, "
                f"sample_slot={_slot_coordinates_for_value(all_target_parameters[0], all_values[0]) if all_target_parameters and all_values else {}}"
            ),
            "slot 축 누락이 있으면 modelTarget.slotAxesFieldNames와 values row key를 일치시킵니다.",
        ),
    )

    rows.append(
        (
            3,
            "slot이 basecase 기반으로 선정된 경우 개연성이 있는가",
            "N/A" if not values_with_basecase else ("PASS" if _has_any_rationale(values_with_basecase) else "REVIEW"),
            f"basecase_value_rows={len(values_with_basecase)}, sample={values_with_basecase[:2]}",
            "basecaseValue가 있는 row는 scenario/event 근거와 기준값 대비 변경 방향을 rationale에 명시합니다.",
        ),
    )

    rows.append(
        (
            4,
            "slot이 basecase에 없지만 시나리오/이벤트 정보를 활용해 추가 선정된 경우 개연성이 있는가",
            "N/A" if not values_without_basecase else ("REVIEW" if _has_any_rationale(values_without_basecase) else "FAIL"),
            f"non_basecase_value_rows={len(values_without_basecase)}, sample={values_without_basecase[:2]}",
            "basecase 없는 신규 slot은 이벤트 본문에 명시된 국가/설비/기간 근거가 있는지 사람이 확인해야 합니다.",
        ),
    )

    rows.append(
        (
            5,
            "slot이 basecase에 없는 경우를 선정하지 못했다면 선정해도 될 가능성이 없었는가",
            "N/A",
            "비동기 VM API response와 proposal DB row에는 미선정 slot 후보 universe가 노출되지 않습니다.",
            "이 항목을 자동 판정하려면 Step2 raw slot catalog 또는 selected=false slot trace를 API/report에 노출해야 합니다.",
        ),
    )

    invalid_value_rows: list[dict[str, Any]] = []
    for record in selected_records:
        for parameter in _target_proposal_parameters(record, parameter_name):
            for value in _parameter_values(parameter):
                base_value = value.get("basecaseValue")
                proposed_value = value.get("proposedValue")
                if proposed_value is None:
                    invalid_value_rows.append({"scenario_id": record["scenario_id"], "reason": "proposedValue is null"})
                elif _is_number(base_value) and not _is_number(proposed_value):
                    invalid_value_rows.append(
                        {
                            "scenario_id": record["scenario_id"],
                            "reason": "numeric basecase but non-numeric proposedValue",
                        },
                    )
    rows.append(
        (
            6,
            "value가 지정된 범위나 형식으로 선정되었나",
            "N/A" if not all_values else ("PASS" if not invalid_value_rows else "FAIL"),
            f"value_rows={len(all_values)}, invalid_value_rows={invalid_value_rows[:10]}",
            "proposedValue 누락 또는 비유한 숫자는 confirmation 전에 차단하되 유효 숫자에는 설정 기반 양자화를 적용하지 않아야 합니다.",
        ),
    )

    rows.append(
        (
            7,
            "value가 basecase에 있는 경우 적절하게 변경되었나",
            "N/A" if not values_with_basecase else ("PASS" if _has_any_rationale(values_with_basecase) else "REVIEW"),
            f"basecase_value_rows={len(values_with_basecase)}, sample={values_with_basecase[:2]}",
            "기준값 대비 증감 방향이 scenario dimension value와 맞는지 REVIEW row를 우선 검토합니다.",
        ),
    )

    rows.append(
        (
            8,
            "value가 basecase에 없었던 경우 개연성 있게 선정되었나",
            "N/A" if not values_without_basecase else ("REVIEW" if _has_any_rationale(values_without_basecase) else "FAIL"),
            f"non_basecase_value_rows={len(values_without_basecase)}, sample={values_without_basecase[:2]}",
            "basecase 없는 value는 source event에 명시된 좌표인지, LUT/authoritative record가 있는지 추가 확인합니다.",
        ),
    )

    comparable_groups: dict[int, set[str]] = {}
    for record in selected_records:
        group_id = int(record["target"].scenario_group_id)
        comparable_groups.setdefault(group_id, set()).add(_value_signature_for_parameter(record, parameter_name))
    multi_record_groups = {
        group_id: signatures
        for group_id, signatures in comparable_groups.items()
        if len(
            [
                record
                for record in selected_records
                if int(record["target"].scenario_group_id) == group_id
            ],
        )
        > 1
    }
    same_signature_groups = sorted(
        group_id for group_id, signatures in multi_record_groups.items() if len(signatures) <= 1
    )
    rows.append(
        (
            9,
            "동일 그룹의 시나리오 사이에 dimension value에 따라 해당 value가 적절한 차이를 보이는가",
            "N/A" if not multi_record_groups else ("PASS" if not same_signature_groups else "REVIEW"),
            (
                f"multi_scenario_groups={len(multi_record_groups)}, "
                f"same_signature_groups={same_signature_groups[:10]}, "
                f"signature_counts={{{', '.join(f'{gid}: {len(sigs)}' for gid, sigs in list(multi_record_groups.items())[:10])}}}"
            ),
            "같은 그룹 내 signature가 같으면 scenario.dimension_values별 차이를 반영해야 하는지 검토합니다.",
        ),
    )

    return [
        f"| {no} | {_md_cell(criteria, max_chars=220)} | {judgement} | {_md_cell(evidence)} | {_md_cell(improvement)} |"
        for no, criteria, judgement, evidence, improvement in rows
    ]


def _render_quality_evaluation(
    *,
    target_parameters: tuple[str, ...],
    records: list[dict[str, Any]],
    target_event_type_l2_ids_by_parameter: dict[str, tuple[int, ...]],
) -> list[str]:
    lines = [
        "",
        "## Parameter Quality Evaluation",
        "",
        "- 기준: VM DB direct/routing 매핑 후보, VM API proposal 결과, confirmation 후 최종 DB row.",
        "- 한계: 비동기 API는 내부 Step1.5/Step2/Step3 raw state와 미선정 slot universe를 노출하지 않으므로 일부 항목은 REVIEW/N/A로 남깁니다.",
        "",
    ]
    for parameter_name in target_parameters:
        lines.extend(
            [
                f"### {parameter_name}",
                "",
                "| No | Criteria | Judgement | Evidence | Improvement |",
                "|---:|---|---|---|---|",
                *_render_quality_rows_for_parameter(
                    parameter_name,
                    records,
                    target_event_type_l2_ids_by_parameter.get(parameter_name, ()),
                ),
                "",
            ],
        )
    return lines


async def run_vm_api_evaluation(
    *,
    base_url: str,
    target_parameters: tuple[str, ...],
    groups_per_event: int,
    scenarios_per_group: int,
    concurrency: int,
    retries: int,
    user_id: int | None,
    poll_interval: float,
    poll_timeout: float,
    request_timeout: float,
) -> Path:
    target_event_type_l2_ids_by_parameter = _discover_event_type_l2_ids_for_parameters(target_parameters)
    event_type_l2_ids = tuple(
        sorted(
            {
                event_type_l2_id
                for event_type_ids in target_event_type_l2_ids_by_parameter.values()
                for event_type_l2_id in event_type_ids
            },
        ),
    )
    targets = _discover_targets(
        event_type_l2_ids,
        groups_per_event=groups_per_event,
        scenarios_per_group=scenarios_per_group,
    )
    started_at = datetime.now()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    parameter_part = "_".join(target_parameters)
    report_path = REPORT_DIR / (
        f"model_parameter_vm_api_async_proposal_confirmation_{parameter_part}_"
        f"{started_at.strftime('%Y%m%d_%H%M%S')}.md"
    )
    records: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    completed_targets: set[int] = set()
    semaphore = asyncio.Semaphore(max(1, concurrency))

    def write_report(finished_at: datetime | None = None) -> None:
        rendered_targets = tuple(
            target for index, target in enumerate(targets) if index in completed_targets
        )
        if not rendered_targets and len(records) + len(errors) == sum(len(target.scenario_ids) for target in targets):
            rendered_targets = targets
        report_text = _render_report(
            started_at=started_at,
            finished_at=finished_at or datetime.now(),
            event_type_l2_ids=event_type_l2_ids,
            targets=rendered_targets or targets,
            records=sorted(records, key=_record_sort_key),
            errors=sorted(errors, key=lambda item: (item["target"].scenario_group_id, item["scenario_id"])),
            concurrency=concurrency,
            retries=retries,
            target_parameters=target_parameters,
            target_event_type_l2_ids_by_parameter=target_event_type_l2_ids_by_parameter,
        )
        report_text = report_text.replace(
            "- 호출 방식: 내부 raw graph 실행 후 `to_output()`으로 final response 생성",
            "- 호출 방식: VM API 비동기 proposal 접수 -> VM DB poll -> confirmation API 호출. `/proposals/sync`는 사용하지 않음.",
            1,
        )
        report_text += "\n".join(_render_api_call_summary(records, errors))
        report_text += "\n".join(
            _render_quality_evaluation(
                target_parameters=target_parameters,
                records=records,
                target_event_type_l2_ids_by_parameter=target_event_type_l2_ids_by_parameter,
            ),
        )
        report_path.write_text(report_text, encoding="utf-8")

    async def run_one(target_index: int, target: EventTypeTarget, scenario_id: int) -> None:
        async with semaphore:
            scenario_started_at = datetime.now()
            scenario_started_monotonic = time.perf_counter()
            last_error: Exception | None = None
            async with httpx.AsyncClient(timeout=request_timeout) as client:
                for attempt in range(retries + 1):
                    try:
                        result = await _evaluate_scenario_via_vm_api(
                            client=client,
                            base_url=base_url.rstrip("/"),
                            scenario_id=scenario_id,
                            user_id=user_id,
                            poll_interval=poll_interval,
                            poll_timeout=poll_timeout,
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
                            "proposal_id=",
                            (result.get("proposal_db_row") or {}).get("model_param_proposal_id"),
                            "elapsed=",
                            _format_duration(elapsed_seconds),
                            flush=True,
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
                                flush=True,
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
                            flush=True,
                        )
            target_scenario_ids = set(target.scenario_ids)
            completed_scenario_ids = {
                int(record["scenario_id"])
                for record in records
                if record["target"].scenario_group_id == target.scenario_group_id
            } | {
                int(error["scenario_id"])
                for error in errors
                if error["target"].scenario_group_id == target.scenario_group_id
            }
            if target_scenario_ids.issubset(completed_scenario_ids):
                completed_targets.add(target_index)
            write_report()
            print(
                "REPORT_UPDATED",
                report_path,
                "records=",
                len(records),
                "errors=",
                len(errors),
                flush=True,
            )

    write_report()
    print("REPORT_IN_PROGRESS", report_path, flush=True)
    print("BASE_URL", base_url, flush=True)
    print("TARGET_PARAMETERS", json.dumps(list(target_parameters), ensure_ascii=False), flush=True)
    print(
        "TARGET_EVENT_TYPE_L2_IDS_BY_PARAMETER",
        json.dumps(target_event_type_l2_ids_by_parameter, ensure_ascii=False, sort_keys=True),
        flush=True,
    )
    print("TARGET_GROUP_COUNT", len(targets), flush=True)
    print("SCENARIO_EXECUTION_COUNT", sum(len(target.scenario_ids) for target in targets), flush=True)

    await asyncio.gather(
        *(
            run_one(target_index, target, scenario_id)
            for target_index, target in enumerate(targets)
            for scenario_id in target.scenario_ids
        ),
    )
    write_report(finished_at=datetime.now())
    print("REPORT", report_path, flush=True)
    print("ERROR_COUNT", len(errors), flush=True)
    return report_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://40.82.137.178:8002")
    parser.add_argument("--target-parameters", nargs="+", default=DEFAULT_TARGET_PARAMETERS)
    parser.add_argument("--groups-per-event", type=int, default=2)
    parser.add_argument("--scenarios-per-group", type=int, default=3)
    parser.add_argument("--concurrency", type=int, default=3)
    parser.add_argument("--retries", type=int, default=1)
    parser.add_argument("--user-id", type=int, default=1)
    parser.add_argument("--poll-interval", type=float, default=5.0)
    parser.add_argument("--poll-timeout", type=float, default=900.0)
    parser.add_argument("--request-timeout", type=float, default=60.0)
    args = parser.parse_args()
    asyncio.run(
        run_vm_api_evaluation(
            base_url=args.base_url,
            target_parameters=tuple(args.target_parameters),
            groups_per_event=args.groups_per_event,
            scenarios_per_group=args.scenarios_per_group,
            concurrency=args.concurrency,
            retries=args.retries,
            user_id=args.user_id,
            poll_interval=args.poll_interval,
            poll_timeout=args.poll_timeout,
            request_timeout=args.request_timeout,
        ),
    )


if __name__ == "__main__":
    main()
