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

from apps.agents.model_parameter_agent.flows.propose_parameters.flow import (
    build_graph,
    to_output,
    to_state,
)
from apps.agents.model_parameter_agent.flows.propose_parameters.nodes import (
    _build_basecase_slot_options,
    _coordinate_issues,
)
from apps.agents.model_parameter_agent.mapping import (
    build_basecase_records,
    get_parameter_knowledge_base,
    match_parameter_candidates,
)
from apps.agents.model_parameter_agent.persistence.model_input_service import (
    ModelInputService,
)


REPORT_DIR = Path(__file__).resolve().parents[1] / "reports"
RAW_GRAPH = build_graph()


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
    return f"{seconds:.3f}"


@dataclass(frozen=True)
class ScenarioTarget:
    event_type_l2_id: int
    event_type_label: str
    scenario_group_id: int
    group_title: str
    scenario_ids: tuple[int, int]


CORE_TEST_TARGETS: tuple[ScenarioTarget, ...] = (
    ScenarioTarget(
        event_type_l2_id=2,
        event_type_label="터미널 Utilization 변동",
        scenario_group_id=18,
        group_title="Cameron LNG 정비 후 정상가동 유지",
        scenario_ids=(105, 106),
    ),
    ScenarioTarget(
        event_type_l2_id=9,
        event_type_label="재생에너지",
        scenario_group_id=44,
        group_title="유럽 재생에너지 약세발 가스발전·LNG 수요 시나리오",
        scenario_ids=(261, 262),
    ),
    ScenarioTarget(
        event_type_l2_id=10,
        event_type_label="석탄 발전",
        scenario_group_id=45,
        group_title="Haramachi 석탄발전 차질에 따른 일본 LNG 대체수요",
        scenario_ids=(267, 268),
    ),
    ScenarioTarget(
        event_type_l2_id=11,
        event_type_label="자연재해",
        scenario_group_id=47,
        group_title="[model_parameter_agent_test] 자연재해 routing 검증",
        scenario_ids=(279, 280),
    ),
    ScenarioTarget(
        event_type_l2_id=12,
        event_type_label="재고 수준",
        scenario_group_id=17,
        group_title="EU 가스 저장률 41%대 저위 유지",
        scenario_ids=(99, 100),
    ),
    ScenarioTarget(
        event_type_l2_id=17,
        event_type_label="지정학적 긴장 및 전쟁·군사분쟁",
        scenario_group_id=16,
        group_title="중동 군사충돌 재격화 에너지 리스크",
        scenario_ids=(92, 93),
    ),
    ScenarioTarget(
        event_type_l2_id=18,
        event_type_label="경제 제재 및 무역 제한",
        scenario_group_id=22,
        group_title="러시아 Arctic LNG 2 제재 이슈",
        scenario_ids=(129, 130),
    ),
    ScenarioTarget(
        event_type_l2_id=19,
        event_type_label="정책/규제 변화",
        scenario_group_id=48,
        group_title="[model_parameter_agent_test] 정책/규제 routing 검증",
        scenario_ids=(281, 282),
    ),
)


ADDITIONAL_TEST_TARGETS: tuple[ScenarioTarget, ...] = (
    ScenarioTarget(
        event_type_l2_id=1,
        event_type_label="Upstream Utilization 변동",
        scenario_group_id=49,
        group_title="[model_parameter_agent_test] Upstream Utilization 변동 추가 검증",
        scenario_ids=(283, 284),
    ),
    ScenarioTarget(
        event_type_l2_id=3,
        event_type_label="신규 터미널(수출·수입) COD·Ramp-up",
        scenario_group_id=21,
        group_title="Delfin FLNG 1 FID 확정",
        scenario_ids=(123, 124),
    ),
    ScenarioTarget(
        event_type_l2_id=4,
        event_type_label="파이프라인 Utilization 변동",
        scenario_group_id=50,
        group_title="[model_parameter_agent_test] 파이프라인 Utilization 변동 추가 검증",
        scenario_ids=(285, 286),
    ),
    ScenarioTarget(
        event_type_l2_id=5,
        event_type_label="발전소 Utilization 변동",
        scenario_group_id=51,
        group_title="[model_parameter_agent_test] 발전소 Utilization 변동 추가 검증",
        scenario_ids=(287, 288),
    ),
    ScenarioTarget(
        event_type_l2_id=6,
        event_type_label="겨울 한파",
        scenario_group_id=52,
        group_title="[model_parameter_agent_test] 겨울 한파 추가 검증",
        scenario_ids=(289, 290),
    ),
    ScenarioTarget(
        event_type_l2_id=7,
        event_type_label="여름 폭염",
        scenario_group_id=53,
        group_title="[model_parameter_agent_test] 여름 폭염 추가 검증",
        scenario_ids=(291, 292),
    ),
    ScenarioTarget(
        event_type_l2_id=8,
        event_type_label="원자력 발전",
        scenario_group_id=54,
        group_title="[model_parameter_agent_test] 원자력 발전 추가 검증",
        scenario_ids=(293, 294),
    ),
    ScenarioTarget(
        event_type_l2_id=13,
        event_type_label="해상 운임",
        scenario_group_id=55,
        group_title="[model_parameter_agent_test] 해상 운임 추가 검증",
        scenario_ids=(295, 296),
    ),
    ScenarioTarget(
        event_type_l2_id=14,
        event_type_label="공급망 및 화물 흐름",
        scenario_group_id=56,
        group_title="[model_parameter_agent_test] 공급망 및 화물 흐름 추가 검증",
        scenario_ids=(297, 298),
    ),
    ScenarioTarget(
        event_type_l2_id=15,
        event_type_label="거래 분쟁·헷징",
        scenario_group_id=57,
        group_title="[model_parameter_agent_test] 거래 분쟁·헷징 추가 검증",
        scenario_ids=(299, 300),
    ),
    ScenarioTarget(
        event_type_l2_id=16,
        event_type_label="인덱스 Spread",
        scenario_group_id=58,
        group_title="[model_parameter_agent_test] 인덱스 Spread 추가 검증",
        scenario_ids=(301, 302),
    ),
    ScenarioTarget(
        event_type_l2_id=20,
        event_type_label="금리 및 통화",
        scenario_group_id=59,
        group_title="[model_parameter_agent_test] 금리 및 통화 추가 검증",
        scenario_ids=(303, 304),
    ),
    ScenarioTarget(
        event_type_l2_id=21,
        event_type_label="국가별 경기",
        scenario_group_id=60,
        group_title="[model_parameter_agent_test] 국가별 경기 추가 검증",
        scenario_ids=(305, 306),
    ),
)


TEST_TARGETS_BY_SUITE: dict[str, tuple[ScenarioTarget, ...]] = {
    "core": CORE_TEST_TARGETS,
    "additional": ADDITIONAL_TEST_TARGETS,
    "all": (*CORE_TEST_TARGETS, *ADDITIONAL_TEST_TARGETS),
}


EVENT_TYPES_WITHOUT_CALL_TARGETS: tuple[tuple[int, str], ...] = (
    (1, "Upstream Utilization 변동"),
    (4, "파이프라인 Utilization 변동"),
    (5, "발전소 Utilization 변동"),
    (6, "겨울 한파"),
    (7, "여름 폭염"),
    (8, "원자력 발전"),
    (13, "해상 운임"),
    (14, "공급망 및 화물 흐름"),
    (15, "거래 분쟁·헷징"),
    (16, "인덱스 Spread"),
    (20, "금리 및 통화"),
    (21, "국가별 경기"),
)


def _normalize(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if isinstance(value, dict):
        return {str(key): _normalize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    return value


def _candidate_signature(candidate: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(candidate.get("canonical_parameter_name") or candidate.get("parameter_name") or ""),
        str(candidate.get("model_file") or ""),
        str(candidate.get("model_sheet") or ""),
    )


def _adjustment_signature(adjustment: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(adjustment.get("parameter_name") or ""),
        str(adjustment.get("model_file") or ""),
        str(adjustment.get("model_sheet") or ""),
    )


def _value_signature(adjustments: list[dict[str, Any]]) -> str:
    comparable: list[dict[str, Any]] = []
    for adjustment in sorted(adjustments, key=lambda item: str(item.get("candidate_key") or "")):
        if adjustment.get("selected", True) is False:
            continue
        comparable.append(
            {
                "candidate_key": adjustment.get("candidate_key"),
                "parameter_name": adjustment.get("parameter_name"),
                "slot_axes": adjustment.get("slot_axes") or [],
                "value_grid": [
                    {
                        "coordinates": cell.get("coordinates") or {},
                        "basecase_value": cell.get("basecase_value"),
                        "proposed_value": cell.get("proposed_value"),
                        "operation": cell.get("operation"),
                    }
                    for cell in adjustment.get("value_grid") or []
                ],
            },
        )
    return json.dumps(comparable, ensure_ascii=False, sort_keys=True, default=str)


def _json_preview(value: Any, *, max_chars: int = 500) -> str:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    return text if len(text) <= max_chars else text[:max_chars] + "..."


def _json_pretty(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, default=str)


def _llm_call_table_lines(llm_calls: list[dict[str, Any]]) -> list[str]:
    if not llm_calls:
        return ["", "- 모델 호출별 소요시간: `[]`"]
    lines = [
        "",
        "##### 모델 호출별 소요시간",
        "",
        "| step | success | model_name | 소요시간 | elapsed_seconds | prompt_tokens | completion_tokens | total_tokens |",
        "|---|---|---|---:|---:|---:|---:|---:|",
    ]
    for call in llm_calls:
        usage = call.get("usage") or {}
        elapsed = call.get("elapsed_seconds")
        lines.append(
            "| {step} | {success} | {model_name} | {duration} | {elapsed_seconds} | "
            "{prompt_tokens} | {completion_tokens} | {total_tokens} |".format(
                step=call.get("step") or "",
                success=call.get("success"),
                model_name=call.get("model_name") or "",
                duration=_format_duration(elapsed),
                elapsed_seconds=_format_seconds(elapsed),
                prompt_tokens=usage.get("prompt_tokens", ""),
                completion_tokens=usage.get("completion_tokens", ""),
                total_tokens=usage.get("total_tokens", ""),
            ),
        )
    return lines


def _selected_adjustments(result: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        adjustment
        for adjustment in result.get("parameter_adjustments", [])
        if adjustment.get("selected", True) is not False
    ]


def _proposal_parameters(final_response: dict[str, Any]) -> list[dict[str, Any]]:
    data = final_response.get("data") or {}
    return data.get("proposalParameters") or []


def _selected_slots(parameter_slots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        slot
        for slot in parameter_slots
        if slot.get("selected", True) is not False
    ]


def _slot_axis_names(slot: dict[str, Any]) -> list[str]:
    axis_names: list[str] = []
    for axis in slot.get("slot_axes") or []:
        axis_name = axis.get("axis_name")
        if axis_name:
            axis_names.append(str(axis_name))
    return axis_names


def _slot_coordinates(slot: dict[str, Any]) -> dict[str, Any]:
    coordinates: dict[str, Any] = {}
    for axis in slot.get("slot_axes") or []:
        axis_name = axis.get("axis_name")
        if axis_name:
            coordinates[str(axis_name)] = axis.get("axis_value")
    return coordinates


def _slot_issue_messages(parameter_slots: list[dict[str, Any]]) -> list[str]:
    issues: list[str] = []
    axis_sets_by_candidate: dict[str, set[tuple[str, ...]]] = defaultdict(set)
    for slot in _selected_slots(parameter_slots):
        candidate_key = str(slot.get("candidate_key") or "")
        axis_names = tuple(_slot_axis_names(slot))
        axis_sets_by_candidate[candidate_key].add(axis_names)
        for issue in _coordinate_issues(_slot_coordinates(slot)):
            issues.append(f"{candidate_key}: {issue}")
    for candidate_key, axis_sets in axis_sets_by_candidate.items():
        if len(axis_sets) > 1:
            issues.append(
                f"{candidate_key}: 같은 parameter에서 서로 다른 slot axis set 사용 {sorted(axis_sets)}",
            )
    return issues


def _value_issue_messages(adjustments: list[dict[str, Any]]) -> list[str]:
    issues: list[str] = []
    for adjustment in _selected_adjustments({"parameter_adjustments": adjustments}):
        candidate_key = str(adjustment.get("candidate_key") or "")
        axis_names = [
            str(axis.get("axis_name"))
            for axis in adjustment.get("slot_axes") or []
            if axis.get("axis_name")
        ]
        seen_coordinates: set[str] = set()
        for cell in adjustment.get("value_grid") or []:
            coordinates = cell.get("coordinates") or {}
            missing_axes = [
                axis_name
                for axis_name in axis_names
                if axis_name not in coordinates
            ]
            if missing_axes:
                issues.append(f"{candidate_key}: value_grid 좌표 누락 {missing_axes}")
            coordinate_key = json.dumps(
                {axis_name: coordinates.get(axis_name) for axis_name in axis_names},
                ensure_ascii=False,
                sort_keys=True,
                default=str,
            )
            if coordinate_key in seen_coordinates:
                issues.append(f"{candidate_key}: 중복 value_grid 좌표 {coordinate_key}")
            seen_coordinates.add(coordinate_key)
    return issues


def _slot_option_axis_value_count(slot_options: list[dict[str, Any]]) -> int:
    return sum(
        len(values or [])
        for option in slot_options
        for values in (option.get("axis_values") or {}).values()
    )


def _slot_option_axis_counts_by_candidate(slot_options: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    summary: dict[str, dict[str, int]] = {}
    for option in slot_options:
        candidate_key = str(option.get("candidate_key") or "")
        summary[candidate_key] = {
            str(axis_name): len(values or [])
            for axis_name, values in (option.get("axis_values") or {}).items()
        }
    return summary


def _build_step_summary(
    *,
    rule_candidates: list[dict[str, Any]],
    validated_candidates: list[dict[str, Any]],
    parameter_slots: list[dict[str, Any]],
    slot_basecase_records: list[dict[str, Any]],
    slot_options: list[dict[str, Any]],
    value_basecase_records: list[dict[str, Any]],
    adjustments: list[dict[str, Any]],
    final_response: dict[str, Any],
    llm_calls: list[dict[str, Any]],
    routing_status: str,
) -> dict[str, Any]:
    selected_slots = _selected_slots(parameter_slots)
    selected_adjustments = _selected_adjustments({"parameter_adjustments": adjustments})
    proposal_parameters = _proposal_parameters(final_response)
    llm_steps = [str(call.get("step") or "") for call in llm_calls]

    if not rule_candidates:
        termination_stage = "Step1 종료 - 매핑 후보 없음"
    elif not validated_candidates:
        termination_stage = "Step1.5 종료 - 후보 검증 후 selected parameter 없음"
    elif not selected_slots:
        termination_stage = "Step2 종료 - selected slot 없음"
    elif any("Step3" in step for step in llm_steps):
        termination_stage = "Step3 완료 - value proposal 산정"
    else:
        termination_stage = "Step2 이후 종료 - Step3 호출 없음"

    slot_issues = _slot_issue_messages(parameter_slots)
    value_issues = _value_issue_messages(adjustments)
    value_cell_count = sum(len(adjustment.get("value_grid") or []) for adjustment in selected_adjustments)
    value_cell_with_basecase_count = sum(
        1
        for adjustment in selected_adjustments
        for cell in adjustment.get("value_grid") or []
        if cell.get("basecase_value") is not None
    )

    if not rule_candidates:
        parameter_status = "N/A"
    elif not validated_candidates:
        parameter_status = "FAIL"
    elif routing_status == "REVIEW":
        parameter_status = "REVIEW"
    else:
        parameter_status = "PASS"

    if not validated_candidates:
        slot_status = "N/A"
    elif not selected_slots:
        slot_status = "FAIL"
    elif slot_issues:
        slot_status = "REVIEW"
    else:
        slot_status = "PASS"

    if not selected_slots:
        basecase_status = "N/A"
    elif len(value_basecase_records) > 100:
        basecase_status = "FAIL"
    elif slot_basecase_records and not value_basecase_records:
        basecase_status = "REVIEW"
    else:
        basecase_status = "PASS"

    if not proposal_parameters:
        value_status = "EMPTY"
    elif value_issues:
        value_status = "FAIL"
    else:
        value_status = "PASS"

    return {
        "termination_stage": termination_stage,
        "parameter_status": parameter_status,
        "slot_status": slot_status,
        "basecase_status": basecase_status,
        "value_status": value_status,
        "rule_candidate_count": len(rule_candidates),
        "validated_candidate_count": len(validated_candidates),
        "selected_parameter_count": len(selected_adjustments),
        "proposal_parameter_count": len(proposal_parameters),
        "slot_option_candidate_count": len(slot_options),
        "slot_option_axis_value_count": _slot_option_axis_value_count(slot_options),
        "slot_option_axis_counts_by_candidate": _slot_option_axis_counts_by_candidate(slot_options),
        "selected_slot_count": len(selected_slots),
        "slot_issue_messages": slot_issues,
        "slot_basecase_record_count": len(slot_basecase_records),
        "value_basecase_record_count": len(value_basecase_records),
        "value_cell_count": value_cell_count,
        "value_cell_with_basecase_count": value_cell_with_basecase_count,
        "value_issue_messages": value_issues,
        "llm_steps": llm_steps,
    }


def _stage_summary_table_lines(step_summary: dict[str, Any]) -> list[str]:
    if not step_summary:
        return ["", "- 단계별 실행 요약: `{}`"]
    return [
        "",
        "##### 단계별 실행 요약",
        "",
        "| 항목 | 값 | 판정 |",
        "|---|---:|---|",
        f"| 종료 단계 | {step_summary.get('termination_stage') or ''} | |",
        (
            f"| Step1/1.5 parameter 후보 | "
            f"rule={step_summary.get('rule_candidate_count', 0)}, "
            f"validated={step_summary.get('validated_candidate_count', 0)}, "
            f"final_selected={step_summary.get('selected_parameter_count', 0)}, "
            f"proposalParameters={step_summary.get('proposal_parameter_count', 0)} | "
            f"{step_summary.get('parameter_status') or ''} |"
        ),
        (
            f"| Step2 basecase raw rows | "
            f"raw_records={step_summary.get('slot_basecase_record_count', 0)} | "
            f"{step_summary.get('slot_status') or ''} |"
        ),
        (
            f"| Step2 distinct slot axis values | "
            f"slot_option_candidates={step_summary.get('slot_option_candidate_count', 0)}, "
            f"distinct_axis_values={step_summary.get('slot_option_axis_value_count', 0)} | "
            f"{step_summary.get('slot_status') or ''} |"
        ),
        (
            f"| Step2 selected slot | "
            f"{step_summary.get('selected_slot_count', 0)} | "
            f"{step_summary.get('slot_status') or ''} |"
        ),
        (
            f"| Step3 basecase 샘플 | "
            f"prompt_records={step_summary.get('value_basecase_record_count', 0)}, "
            "limit=100 | "
            f"{step_summary.get('basecase_status') or ''} |"
        ),
        (
            f"| Step3 value 결과 | "
            f"value_cells={step_summary.get('value_cell_count', 0)}, "
            f"basecaseValue_present={step_summary.get('value_cell_with_basecase_count', 0)} | "
            f"{step_summary.get('value_status') or ''} |"
        ),
        (
            f"| Step2 slot axis value 수 | "
            f"`{_json_preview(step_summary.get('slot_option_axis_counts_by_candidate') or {}, max_chars=1200)}` | |"
        ),
    ]


def _all_adjustments(result: dict[str, Any]) -> list[dict[str, Any]]:
    return result.get("parameter_adjustments", []) or []


def _compare_candidate_coverage(
    candidates: list[dict[str, Any]],
    result: dict[str, Any],
) -> tuple[bool, list[str]]:
    expected = {_candidate_signature(candidate) for candidate in candidates}
    actual = {_adjustment_signature(adjustment) for adjustment in _all_adjustments(result)}
    messages: list[str] = []
    missing = sorted(expected - actual)
    unexpected = sorted(actual - expected)
    if missing:
        messages.append(f"missing={missing}")
    if unexpected:
        messages.append(f"unexpected={unexpected}")
    return not messages, messages


def _review_selected_parameters(
    candidates: list[dict[str, Any]],
    result: dict[str, Any],
) -> tuple[bool, list[str]]:
    candidate_keys = {str(candidate.get("candidate_key") or "") for candidate in candidates}
    selected = _selected_adjustments(result)
    selected_keys = {str(adjustment.get("candidate_key") or "") for adjustment in selected}
    unknown_selected = sorted(selected_keys - candidate_keys)
    messages: list[str] = []
    if not candidates and not selected:
        return True, []
    if not selected:
        messages.append(
            "final recommendation이 없습니다. 후보는 검증됐지만 slot/value를 명확히 확정하지 못한 케이스로 기록합니다.",
        )
    if unknown_selected:
        messages.append(f"unknown_selected_candidate_keys={unknown_selected}")
    return not unknown_selected, messages


def _review_routing_selection(
    _scenario_id: int,
    candidates: list[dict[str, Any]],
    result: dict[str, Any],
) -> tuple[str, list[str]]:
    routing_candidates = [
        candidate
        for candidate in candidates
        if str(candidate.get("mapping_method") or "").lower() == "routing"
    ]
    if not routing_candidates:
        return "N/A", []

    routing_keys = {str(candidate.get("candidate_key") or "") for candidate in routing_candidates}
    selected_routing_keys = {
        str(adjustment.get("candidate_key") or "")
        for adjustment in _selected_adjustments(result)
        if str(adjustment.get("candidate_key") or "") in routing_keys
    }
    messages: list[str] = []
    if not selected_routing_keys:
        messages.append("routing 후보 중 selected parameter가 없습니다.")
    if len(routing_candidates) > 1 and len(selected_routing_keys) == len(routing_candidates):
        messages.append(
            "routing 후보가 모두 selected입니다. DB scenario dimension에 따른 선택/제외 사유 검토가 필요합니다.",
        )
    return ("PASS" if not messages else "REVIEW"), messages


def _build_group_status(
    *,
    targets: tuple[ScenarioTarget, ...],
    records: list[dict[str, Any]],
) -> dict[int, bool]:
    group_status: dict[int, bool] = {}
    for target in targets:
        group_records = [
            record
            for record in records
            if record["target"].event_type_l2_id == target.event_type_l2_id
        ]
        group_status[target.event_type_l2_id] = (
            len(group_records) == len(target.scenario_ids)
            and all(record["mapping_ok"] for record in group_records)
            and all(record["selected_ok"] for record in group_records)
            and (
                not any(record["expected_candidates"] for record in group_records)
                or len({record["value_signature"] for record in group_records}) > 1
            )
        )
    return group_status


async def _evaluate_scenario(
    scenario_id: int,
    *,
    max_candidates: int,
    allow_llm_fallback: bool,
) -> dict[str, Any]:
    context = ModelInputService().load_context(scenario_id)
    kb = get_parameter_knowledge_base()
    candidates, non_inputs, mapping_warnings = match_parameter_candidates(
        kb,
        context,
        max_candidates=max_candidates,
    )
    payload: dict[str, Any] = {
        "scenario_id": scenario_id,
        "max_candidates": max_candidates,
        "allow_llm_fallback": allow_llm_fallback,
    }
    raw_output = await RAW_GRAPH.ainvoke(to_state(payload))
    raw_state = _normalize(raw_output)
    validated_candidates = raw_state.get("candidate_mappings") or []
    slot_basecase_records, basecase_warnings = build_basecase_records(
        kb,
        validated_candidates,
        context,
    )
    slot_options = _build_basecase_slot_options(slot_basecase_records)
    parameter_slots = raw_state.get("parameter_slots") or []
    value_basecase_records = raw_state.get("basecase_records") or []
    result = {
        "parameter_adjustments": raw_state.get("parameter_adjustments") or [],
        "non_input_items": raw_state.get("non_input_items") or [],
        "validation_warnings": raw_state.get("validation_warnings") or [],
    }
    final_response = to_output(raw_state).model_dump(by_alias=True, exclude_none=True)
    llm_calls = raw_state.get("llm_calls") or []
    candidate_coverage_ok, candidate_coverage_messages = _compare_candidate_coverage(
        validated_candidates,
        result,
    )
    selected_ok, selected_messages = _review_selected_parameters(validated_candidates, result)
    routing_status, routing_messages = _review_routing_selection(
        scenario_id,
        validated_candidates,
        result,
    )
    step_summary = _build_step_summary(
        rule_candidates=candidates,
        validated_candidates=validated_candidates,
        parameter_slots=parameter_slots,
        slot_basecase_records=slot_basecase_records,
        slot_options=slot_options,
        value_basecase_records=value_basecase_records,
        adjustments=result["parameter_adjustments"],
        final_response=final_response,
        llm_calls=llm_calls,
        routing_status=routing_status,
    )
    return {
        "scenario_id": scenario_id,
        "context": context,
        "rule_candidates": candidates,
        "expected_candidates": validated_candidates,
        "non_input_items": non_inputs,
        "mapping_warnings": mapping_warnings,
        "basecase_warnings": basecase_warnings,
        "parameter_slots": parameter_slots,
        "step_summary": step_summary,
        "result": result,
        "final_response": final_response,
        "llm_calls": llm_calls,
        "mapping_ok": candidate_coverage_ok,
        "mapping_messages": candidate_coverage_messages,
        "selected_ok": selected_ok,
        "selected_messages": selected_messages,
        "routing_status": routing_status,
        "routing_messages": routing_messages,
        "value_signature": _value_signature(_selected_adjustments(result)),
    }


def _render_md(
    *,
    started_at: datetime,
    finished_at: datetime,
    iteration: int,
    suite: str,
    targets: tuple[ScenarioTarget, ...],
    skipped_event_types: tuple[tuple[int, str], ...],
    records: list[dict[str, Any]],
    errors: list[dict[str, Any]],
    max_candidates: int,
    allow_llm_fallback: bool,
    concurrency: int,
) -> str:
    lines: list[str] = [
        "# Model Parameter Proposal Evaluation",
        "",
        f"- 실행 시작: {started_at.isoformat(timespec='seconds')}",
        f"- 실행 종료: {finished_at.isoformat(timespec='seconds')}",
        f"- 반복 차수: {iteration}",
        f"- suite: {suite}",
        f"- maxCandidates: {max_candidates}",
        f"- allowLlmFallback: {allow_llm_fallback}",
        f"- concurrency: {concurrency}",
        "- 호출 방식: 내부 raw graph 실행 후 `to_output()`으로 final response 생성",
        "",
        "## 판정 기준",
        "",
        "- 매핑 후보 검증: `Dimension Parameter Mapping` 산출 후보 중 LLM 후보 검증을 통과한 parameter가 내부 `parameter_adjustments`에 포함되어야 함.",
        "- LLM 선택 검증: `selected=true` parameter가 최소 1개 이상이고 후보 밖 candidate가 selected 되면 안 됨.",
        "- 라우팅 검증: `mapping_method=routing` 후보가 있을 때 DB scenario dimension 맥락에 따라 routing 후보 중 일부가 selected 되어야 하며, 테스트용 scenario는 필수 선택/제외 candidate_key를 추가 검증함.",
        "- value 차이 검증: 같은 scenario_group의 2개 scenario 응답에서 선택 좌표 또는 제안값 signature가 달라야 함.",
        "- basecase 검증: 최종 응답의 값 항목에 `basecaseValue`가 포함되어야 함.",
        "",
        "## 호출 불가 Event Type",
        "",
    ]
    if skipped_event_types:
        for event_type_l2_id, label in skipped_event_types:
            lines.append(
                f"- event_type_l2_id={event_type_l2_id} `{label}`: 이 suite의 호출 대상에서 제외됨",
            )
    else:
        lines.append("- 없음")
    lines.extend(["", "## 호출 결과", ""])

    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[int(record["target"].event_type_l2_id)].append(record)

    for target in targets:
        group_records = grouped.get(target.event_type_l2_id, [])
        if not group_records:
            lines.extend(
                [
                    f"### event_type_l2_id={target.event_type_l2_id} {target.event_type_label}",
                    "",
                    f"- scenario_group_id: {target.scenario_group_id}",
                    "- 결과: FAIL",
                    "- 사유: 호출 결과 없음",
                    "",
                ],
            )
            continue

        value_signatures = {record["value_signature"] for record in group_records}
        has_expected_candidates = any(record["expected_candidates"] for record in group_records)
        has_selected_values = any(_selected_adjustments(record["result"]) for record in group_records)
        value_diff_ok = (
            (not has_expected_candidates)
            or (not has_selected_values)
            or len(value_signatures) > 1
        )
        value_diff_status = "N/A" if not has_expected_candidates or not has_selected_values else (
            "PASS" if value_diff_ok else "FAIL"
        )
        mapping_ok = all(record["mapping_ok"] for record in group_records)
        selected_ok = all(record["selected_ok"] for record in group_records)
        routing_statuses = {record["routing_status"] for record in group_records}
        group_ok = mapping_ok and selected_ok and value_diff_ok
        lines.extend(
            [
                f"### event_type_l2_id={target.event_type_l2_id} {target.event_type_label}",
                "",
                f"- scenario_group_id: {target.scenario_group_id}",
                f"- group_title: {target.group_title}",
                f"- 대상 scenario_ids: {list(target.scenario_ids)}",
                f"- 매핑 후보 검증: {'PASS' if mapping_ok else 'FAIL'}",
                f"- LLM selected 검증: {'PASS' if selected_ok else 'FAIL'}",
                f"- 라우팅 선택 검증: {', '.join(sorted(routing_statuses))}",
                f"- scenario별 value 차이: {value_diff_status}",
                f"- 그룹 종합: {'PASS' if group_ok else 'FAIL'}",
                "",
            ],
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
            lines.extend(
                [
                    f"#### scenario_id={record['scenario_id']} {scenario.get('title') or ''}",
                    "",
                    f"- 소요시간: {_format_duration(record.get('elapsed_seconds'))} ({_format_seconds(record.get('elapsed_seconds'))})",
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

    lines.extend(
        [
            "## 최종 요약",
            "",
            f"- ERROR_COUNT: {len(errors)}",
            f"- GROUP_STATUS: `{_json_preview(_build_group_status(targets=targets, records=records), max_chars=2000)}`",
            "",
            "## 오류 및 반복 이력",
            "",
        ],
    )
    if not errors:
        lines.append("- 오류 없음. 1회 실행으로 완료.")
    else:
        for error in errors:
            lines.append(
                f"- scenario_id={error.get('scenario_id')} "
                f"elapsed={_format_duration(error.get('elapsed_seconds'))} "
                f"({_format_seconds(error.get('elapsed_seconds'))}) "
                f"error=`{error.get('error')}`",
            )
    lines.append("")
    return "\n".join(lines)


async def run_evaluation(
    *,
    iteration: int,
    suite: str,
    max_candidates: int,
    allow_llm_fallback: bool,
    concurrency: int,
) -> tuple[Path, list[dict[str, Any]], list[dict[str, Any]]]:
    targets = TEST_TARGETS_BY_SUITE[suite]
    skipped_event_types = EVENT_TYPES_WITHOUT_CALL_TARGETS if suite == "core" else ()
    started_at = datetime.now()
    semaphore = asyncio.Semaphore(max(1, concurrency))
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / (
        f"model_parameter_proposal_evaluation_{suite}_iter{iteration}_"
        f"{started_at.strftime('%Y%m%d_%H%M%S')}.md"
    )
    records: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    completed_targets: list[tuple[int, ScenarioTarget]] = []

    def write_report(
        *,
        rendered_targets: tuple[ScenarioTarget, ...],
        finished_at: datetime | None = None,
    ) -> None:
        ordered_records = sorted(
            records,
            key=lambda record: (record["_order"], record["scenario_id"]),
        )
        ordered_errors = sorted(
            errors,
            key=lambda error: (error["_order"], error["scenario_id"]),
        )
        report_path.write_text(
            _render_md(
                started_at=started_at,
                finished_at=finished_at or datetime.now(),
                iteration=iteration,
                suite=suite,
                targets=rendered_targets,
                skipped_event_types=skipped_event_types,
                records=ordered_records,
                errors=ordered_errors,
                max_candidates=max_candidates,
                allow_llm_fallback=allow_llm_fallback,
                concurrency=concurrency,
            ),
            encoding="utf-8",
        )

    async def run_one(order: int, target: ScenarioTarget, scenario_id: int) -> dict[str, Any]:
        async with semaphore:
            scenario_started = time.perf_counter()
            try:
                result = await _evaluate_scenario(
                    scenario_id,
                    max_candidates=max_candidates,
                    allow_llm_fallback=allow_llm_fallback,
                )
                elapsed_seconds = time.perf_counter() - scenario_started
                result["target"] = target
                result["_order"] = order
                result["elapsed_seconds"] = elapsed_seconds
                print(
                    "OK",
                    target.event_type_l2_id,
                    target.scenario_group_id,
                    scenario_id,
                    "mapping=",
                    result["mapping_ok"],
                    "elapsed=",
                    _format_duration(elapsed_seconds),
                )
                return {"record": result}
            except Exception as exc:  # noqa: BLE001
                elapsed_seconds = time.perf_counter() - scenario_started
                error = {
                    "event_type_l2_id": target.event_type_l2_id,
                    "scenario_group_id": target.scenario_group_id,
                    "scenario_id": scenario_id,
                    "error": repr(exc),
                    "_order": order,
                    "elapsed_seconds": elapsed_seconds,
                }
                print(
                    "ERROR",
                    target.event_type_l2_id,
                    target.scenario_group_id,
                    scenario_id,
                    "elapsed=",
                    _format_duration(elapsed_seconds),
                    repr(exc),
                )
                return {"error": error}

    async def run_target(order: int, target: ScenarioTarget) -> dict[str, Any]:
        results = await asyncio.gather(
            *(run_one(order, target, scenario_id) for scenario_id in target.scenario_ids),
        )
        target_records = [item["record"] for item in results if "record" in item]
        target_errors = [item["error"] for item in results if "error" in item]
        print(
            "EVENT_DONE",
            target.event_type_l2_id,
            target.scenario_group_id,
            "records=",
            len(target_records),
            "errors=",
            len(target_errors),
        )
        return {
            "order": order,
            "target": target,
            "records": target_records,
            "errors": target_errors,
        }

    write_report(rendered_targets=())
    print("REPORT_IN_PROGRESS", report_path)
    target_tasks = [
        asyncio.create_task(run_target(order, target))
        for order, target in enumerate(targets)
    ]
    for target_task in asyncio.as_completed(target_tasks):
        target_result = await target_task
        records.extend(target_result["records"])
        errors.extend(target_result["errors"])
        completed_targets.append((target_result["order"], target_result["target"]))
        rendered_targets = tuple(
            target
            for _, target in sorted(completed_targets, key=lambda item: item[0])
        )
        write_report(rendered_targets=rendered_targets)
        print(
            "REPORT_UPDATED",
            report_path,
            "completed_events=",
            f"{len(completed_targets)}/{len(targets)}",
        )

    finished_at = datetime.now()
    records = sorted(
        records,
        key=lambda record: (record["_order"], record["scenario_id"]),
    )
    errors = sorted(
        errors,
        key=lambda error: (error["_order"], error["scenario_id"]),
    )
    write_report(rendered_targets=targets, finished_at=finished_at)
    return report_path, records, errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iteration", type=int, default=1)
    parser.add_argument(
        "--suite",
        choices=sorted(TEST_TARGETS_BY_SUITE),
        default="core",
    )
    parser.add_argument("--max-candidates", type=int, default=8)
    parser.add_argument("--allow-llm-fallback", action="store_true")
    parser.add_argument("--concurrency", type=int, default=1)
    args = parser.parse_args()
    report_path, records, errors = asyncio.run(
        run_evaluation(
            iteration=args.iteration,
            suite=args.suite,
            max_candidates=args.max_candidates,
            allow_llm_fallback=args.allow_llm_fallback,
            concurrency=args.concurrency,
        ),
    )
    group_status = _build_group_status(
        targets=TEST_TARGETS_BY_SUITE[args.suite],
        records=records,
    )
    print("REPORT", report_path)
    print("ERROR_COUNT", len(errors))
    print("GROUP_STATUS", json.dumps(group_status, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
