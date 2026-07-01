from __future__ import annotations

import re
import time
from datetime import date
from typing import Any

from apps.agents.model_parameter_agent.mapping import (
    build_basecase_records,
    build_llm_prompt_packet,
    get_parameter_knowledge_base,
    get_parameter_knowledge_base_from_resources,
    ParameterKnowledgeBase,
    match_parameter_candidates,
    to_compact_json,
)
from apps.agents.model_parameter_agent.persistence.model_input.service import (
    ModelInputService,
)
from apps.agents.model_parameter_agent.schemas.propose_parameters import (
    LLMCandidateValidationResponse,
    LLMSlotProposalResponse,
    LLMValueProposalResponse,
    ParameterAdjustment,
    ParameterCandidateDecision,
    ParameterSlotProposal,
    ParameterSlotAxis,
    ParameterValueCell,
)
from apps.agents.model_parameter_agent.state import ModelParameterProposalState
from apps.common.exceptions.custom import MIBaseError
from apps.common.logging.logger_config import logger
from apps.common.values.enums import ModelPreference
from apps.common.values.error_codes import ErrorCode

MAX_PARAMETER_SLOTS = 100

CANDIDATE_VALIDATION_SYSTEM = """\
당신은 LNG 수급모델 Input Parameter 제안 agent입니다.

목표:
- Step1.5: DB mapping rule로 추출된 direct/routing parameter 후보를
  scenario/event 맥락 기준으로 검증합니다.
- 이 단계는 basecase row/value 추출 전 후보 gate입니다.
- 후보 밖의 parameter, workbook, sheet, candidate_key를 만들지 마십시오.

판단 기준:
- direct 후보는 DB 매핑에서 명시적으로 지정된 모델 input이므로 반드시 selected=true로 유지합니다.
- routing 후보는 scenario/event/dimension 맥락에 맞는 후보만 선택합니다.
- 하나의 dimension에서 복수 parameter가 실제로 동시에 필요하면 복수 선택할 수 있습니다.
- 단순히 가능성이 있거나 근거가 약한 후보는 제외합니다.
- scenario/event가 정량 값 산정까지 보장하지 않아도, 이후 slot/value 단계에서 명확한 값 산정 가능성이 있으면 후보로 유지할 수 있습니다.
- basecase row 존재 여부는 이 단계의 선택/제외 근거가 아닙니다.
- 후보 밖으로 벗어나지 않는 범위에서는 가능한 parameter를 누락하지 말고 최대한 다음 단계로 넘기십시오.

출력 규칙:
- candidate_decisions는 candidate_mappings의 candidate_key만 사용합니다.
- 모든 candidate_mappings에 대해 decision을 하나씩 반환합니다.
- selected=true는 다음 basecase/slot/value 단계로 넘길 후보입니다.
- selected=false는 제외 후보입니다.
- rationale_ko에는 선택/제외 근거를 한국어로 작성하고, 어떤 scenario dimension 또는 event 근거를 사용했는지 명시합니다.
- rationale_ko에는 내부 개발 단계나 평가 목적을 드러내는 표현을 쓰지 마십시오.
  사용자에게 설명 가능한 시나리오/이벤트/모델 근거만 작성하십시오.
"""


SLOT_PROPOSAL_SYSTEM = """\
당신은 LNG 수급모델 Input Parameter 제안 agent입니다.

목표:
- Step2: scenario_id로 조회된 시나리오 가정과 원 이벤트 맥락을 바탕으로
  후보 parameter의 slot 축만 결정합니다.
- Step1 후보 parameter는 DB 매핑으로 이미 제한되어 있습니다.
  후보 밖의 parameter, workbook, sheet를 만들지 마십시오.
- basecase_slot_options는 매핑된 시트의 Base Case 영역에서 candidate별 축 이름과
  각 축의 distinct 값만 모은 참고 목록입니다. Step2에서는 raw value row가 제공되지 않습니다.
- basecase_slot_options는 slot 후보를 찾는 참고 자료일 뿐입니다.
  여기에 값이 없거나 빈 목록이어도 scenario/event/dimension에 명확한 모델 input 축 값이 있으면
  반드시 그 값을 사용해 slot을 선택하십시오.
- slot_selection_limits.maxParameterSlots는 전체 selected slot 상한입니다.
  basecase_slot_options에 있는 값 중 scenario/event 의미와 가장 잘 맞는 slot을 우선 선택하고,
  basecase에 없더라도 scenario/event에 명확하거나 의미론적으로 타당한 실제 모델 input 값은 추가할 수 있습니다.
  단, 상한을 넘길 때는 영향이 큰 대표 slot을 우선 선택하십시오.

출력 규칙:
- parameter_slots는 candidate_mappings의 candidate_key만 사용합니다.
- slot_axes에는 지역/국가/시설/연/월/계약/route 등 해당 sheet에 필요한 축을 넣습니다.
- 값을 산정하지 마십시오. 값 산정은 Step3에서 수행합니다.
- slot_axes의 축 이름과 축 값은 basecase_slot_options의 axis_names/axis_values를 우선 사용합니다.
- basecase_slot_options에 없어도 scenario/event에 명확히 명시된 모델 input 축 값은 사용할 수 있습니다.
- basecase_slot_options가 비어 있거나 특정 축 값이 없다는 이유만으로 selected=false를 반환하지 마십시오.
- basecase에 있는 축 값 중 scenario/event 의미와 일치하는 값을 먼저 선택하고,
  basecase에 없는 값은 의미론적으로 실제 모델 input에 적합할 때만 추가하십시오.
- selected=true slot 총수는 slot_selection_limits.maxParameterSlots를 넘기지 마십시오.
- 해당 parameter가 scalar 입력이거나 축을 특정할 필요가 없으면 selected=true와 빈 slot_axes를 반환하십시오.
- 기간 표현은 period_resolution_policy를 기준으로 Year/Month/Period로 변환합니다.
- `YYYY-MM`, `YYYY년 M월`, `occurred_at`처럼 연월이 명확하면 현재 기준월과 무관하게 그대로 사용합니다.
- 연도 없이 월만 명시되면 현재 월 이후의 가장 가까운 해당 월로 변환합니다.
- 명확한 연월/월 근거가 없으면 추론상 현재 월 이후부터 period를 전개합니다.
- 미정, 후보, 추정, 또는(or), 일부, 대체 공급국, '?' 같은 모호한 slot 값은 절대 사용하지 마십시오.
- 여러 값이 명확하면 "A; B"처럼 한 축 값에 합치지 말고 parameter_slots를 여러 개 반환하십시오.
- 축을 명확한 실제 모델 input 값으로 특정할 수 없으면 selected=false,
  needs_user_review=true와 warning을 남기고 slot_axes는 비워 두십시오.
- 단, scenario/event/dimension에서 축이나 기간을 합리적으로 자동 변환할 수 있으면 selected=true로 유지하십시오.
- 근거는 한국어로 작성하고, 어떤 scenario dimension과
  basecase_slot_options를 썼는지 명시합니다.
- 근거에는 내부 개발 단계나 평가 목적을 드러내는 표현을 쓰지 마십시오.
  사용자에게 설명 가능한 slot 선택 근거만 작성하십시오.
"""


VALUE_PROPOSAL_SYSTEM = """\
당신은 LNG 수급모델 Input Parameter 제안 agent입니다.

목표:
- Step3: Step2에서 결정된 slot 축과 basecase_records를 근거로 slot별 입력 값을 제안합니다.
- Step1 후보 parameter와 Step2 slot 축은 이미 제한되어 있습니다.
  후보 밖의 parameter, workbook, sheet, candidate_key를 만들지 마십시오.
- basecase_records는 Step2에서 선택된 slot 축에 매칭되는 row/value record만 포함합니다.
  전달된 record는 해당 slot에 대해 사용 가능한 basecase value 전체이므로 누락 없이 참고하십시오.
- basecase_records는 참고 자료입니다. 비어 있거나 일치 row/value가 없더라도
  scenario/event/dimension에 명확한 수치, 기간, 방향, 강도가 있으면 반드시 proposed_value를 산정하십시오.

출력 규칙:
- parameter_adjustments는 candidate_mappings의 candidate_key만 사용합니다.
- 모든 candidate_mappings에 대해 parameter_adjustments를 하나씩 반환합니다.
- model_file, model_sheet, parameter_name은 candidate_mappings의 값을 그대로 사용합니다.
- slot_axes는 Step2 parameter_slots를 유지하거나 더 구체화한 값만 사용합니다.
- Step2 parameter_slots가 비어 있거나 selected=false였더라도,
  scenario/event/dimension으로 slot/value를 명확히 산정할 수 있으면 selected=true로 반환하십시오.
- parameter_selection_rationale_ko에는 해당 parameter를 선택한 근거를 적습니다.
- value_grid에는 slot별 basecase_value, proposed_value와 operation을 넣습니다.
- value_grid.coordinates에는 실제 모델 input으로 넣을 수 있는 명확한 값만 넣습니다.
  미정, 후보, 추정, 또는(or), 일부, 대체 공급국, '?' 같은 모호한 값은 금지입니다.
- value_grid.coordinates의 Year/Month는 period_resolution_policy를 따라 확정합니다.
  명시 연월은 현재 기준월과 무관하게 그대로 사용합니다.
  월만 명시되면 현재 월 이후의 가장 가까운 해당 월을 사용합니다.
- 여러 좌표가 필요하면 하나의 문자열로 합치지 말고 value_grid 항목을 여러 개 반환하십시오.
- 같은 candidate_key 안에서 같은 value_grid.coordinates 조합은 정확히 하나의 cell로만 반환하십시오.
  같은 slot에 여러 operation 또는 여러 proposed_value를 동시에 반환하지 마십시오.
  여러 해석이 가능하지만 하나로 확정할 수 없으면 selected=false, needs_user_review=true로 반환하십시오.
- parameter_selection_rationale_ko에는 이 parameter를 선택한 이유만 적습니다.
  slot 좌표, basecase row, proposed_value 산식은 반복하지 마십시오.
- value_grid의 value_selection_rationale_ko에는 해당 value_grid 좌표/record를 선택한 근거만 적습니다.
  parameter 선택 이유나 proposed_value 산식은 반복하지 마십시오.
- value_grid의 proposed_value_rationale_ko에는 operation과 proposed_value 산정 근거만 적습니다.
  parameter 선택 이유나 slot 선택 근거는 반복하지 마십시오.
- basecase_records를 사용했다면 value_grid.basecase_reference_ids에 reference_id를 넣습니다.
- basecase_records에 일치 row/value가 있으면 basecase_value를 기준으로 scenario/event 충격을 조정합니다.
- basecase_records에 일치 row/value가 없어도 scenario/event/dimension에 명확한 수치와 산정 근거가 있으면
  basecase_value=null로 두고 proposed_value를 산정합니다.
- basecase_value가 null이라는 이유만으로 selected=false를 반환하지 마십시오.
- 후보 parameter가 입력 가능한 것으로 판단되면 가능한 많은 명확한 좌표/value_grid를 반환하십시오.
- 범위형 scenario dimension은 자동 변환해 proposed_value를 산정합니다.
  예: <5%는 3%, ±25% 이내는 방향이 명확하면 25%, +300% 초과는 300% 최소 충격값입니다.
- 방향이 명확하지 않거나 정성 값만 있어 proposed_value를 숫자/명확한 값으로 확정할 수 없으면
  selected=false, proposed_value=null, needs_user_review=true로 반환하십시오.
- selected=true인 value_grid는 proposed_value가 반드시 실제 모델 input으로 사용할 수 있는 명확한 값이어야 하고,
  operation도 absolute, delta, percent_change, overwrite 중 하나여야 합니다.
- 근거는 한국어로 작성하되, 각 rationale 필드의 역할을 넘지 않는 범위에서 사용한
  scenario dimension 또는 basecase_records만 명시합니다.
- 모든 rationale에는 내부 개발 단계나 평가 목적을 드러내는 표현을 쓰지 마십시오.
  사용자에게 설명 가능한 시나리오/이벤트/모델 근거만 작성하십시오.
"""


def load_scenario_context(state: ModelParameterProposalState) -> dict[str, Any]:
    context = ModelInputService().load_context(state.scenario_id)
    scenario = context.get("scenario") or {}
    kb = _knowledge_base_from_context(state, context)
    logger.info(
        "[model-parameter] loaded scenario context | scenario_id={} title={} dimension_keys={} parameter_count={} mapping_rule_count={}",
        state.scenario_id,
        scenario.get("title"),
        sorted((scenario.get("dimension_values") or {}).keys()),
        len(kb.parameter_definitions),
        len(kb.mapping_rules),
    )
    return {"scenario_context": context, "parameter_knowledge_base": kb}


def _knowledge_base_from_context(
    state: ModelParameterProposalState,
    context: dict[str, Any],
) -> ParameterKnowledgeBase:
    if state.mapping_excel_path:
        return get_parameter_knowledge_base(
            state.mapping_excel_path,
            state.basecase_dir_path,
            max_sample_rows=state.max_basecase_sample_rows,
            max_sample_cols=state.max_basecase_cols,
        )
    resources = context.get("parameter_mapping_resources") or {}
    return get_parameter_knowledge_base_from_resources(
        mapping_rows=resources.get("mapping_rules") or [],
        parameter_rows=resources.get("parameter_definitions") or [],
        basecase_dir_path=state.basecase_dir_path,
        max_sample_rows=state.max_basecase_sample_rows,
        max_sample_cols=state.max_basecase_cols,
    )


def resolve_event_type_l2_id(scenario_context: dict[str, Any] | None) -> int | None:
    context = scenario_context or {}
    group = context.get("scenario_group") or {}
    event_type = context.get("event_type") or {}
    for raw in (
        group.get("event_type_l2_id"),
        event_type.get("event_type_l2_id"),
        event_type.get("id"),
    ):
        try:
            return int(raw)
        except (TypeError, ValueError):
            continue
    return None


def select_parameter_candidates(state: ModelParameterProposalState) -> dict[str, Any]:
    if not state.scenario_context:
        raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="scenario_context is required")
    if state.parameter_knowledge_base is None:
        raise MIBaseError(
            ErrorCode.INVALID_REQUEST,
            detail="parameter_knowledge_base is required",
        )
    candidates, non_inputs, warnings = match_parameter_candidates(
        state.parameter_knowledge_base,
        state.scenario_context,
        max_candidates=state.max_candidates,
    )
    logger.info(
        "[model-parameter] selected candidate mappings | scenario_id={} candidate_count={} candidate_keys={} non_input_count={} warning_count={}",
        state.scenario_id,
        len(candidates),
        [candidate.get("candidate_key") for candidate in candidates],
        len(non_inputs),
        len(warnings),
    )
    return {
        "candidate_mappings": candidates,
        "non_input_items": non_inputs,
        "validation_warnings": [*state.validation_warnings, *warnings],
    }


async def validate_parameter_candidates(state: ModelParameterProposalState) -> dict[str, Any]:
    if not state.candidate_mappings:
        return {
            "candidate_mappings": [],
            "validation_warnings": state.validation_warnings,
        }

    packet = build_llm_prompt_packet(
        state.scenario_context or {},
        state.candidate_mappings,
        state.non_input_items,
        [],
    )
    messages = [
        {"role": "system", "content": CANDIDATE_VALIDATION_SYSTEM},
        {
            "role": "user",
            "content": (
                "아래 JSON만 근거로 Step1.5 수급모델 parameter 후보를 검증하십시오.\n"
                f"{to_compact_json(packet)}"
            ),
        },
    ]

    llm_started = time.perf_counter()
    try:
        result = await _invoke_structured(
            output_schema=LLMCandidateValidationResponse,
            messages=messages,
            model_name=state.model_name,
        )
        llm_payload = result.result
        usage = result.usage.model_dump() if result.usage is not None else None
        llm_call = _llm_call_trace(
            step="Step1.5 candidate validation",
            model_name=state.model_name,
            elapsed_seconds=time.perf_counter() - llm_started,
            usage=usage,
            success=True,
        )
    except Exception as exc:
        llm_call = _llm_call_trace(
            step="Step1.5 candidate validation",
            model_name=state.model_name,
            elapsed_seconds=time.perf_counter() - llm_started,
            usage=None,
            success=False,
            error=repr(exc),
        )
        if not state.allow_llm_fallback:
            raise
        logger.warning(
            "[model-parameter] Step1.5 LLM call failed, using fallback | scenario_id={} error={}",
            state.scenario_id,
            repr(exc),
        )
        llm_payload = _fallback_candidate_validation_response(
            "Step1.5 LLM 후보 검증 실패로 rule-based 후보를 유지했습니다.",
            state.candidate_mappings,
        )
        usage = None

    candidates, validation_warnings = _sanitize_candidate_decisions(
        llm_payload.candidate_decisions,
        state.candidate_mappings,
    )
    candidates, routing_warnings = _apply_routing_comment_overrides(
        state.candidate_mappings,
        candidates,
    )
    logger.info(
        "[model-parameter] validated candidate mappings | scenario_id={} before_count={} after_count={} selected_candidate_keys={} warning_count={}",
        state.scenario_id,
        len(state.candidate_mappings),
        len(candidates),
        [candidate.get("candidate_key") for candidate in candidates],
        len(llm_payload.validation_warnings) + len(validation_warnings) + len(routing_warnings),
    )
    return {
        "candidate_mappings": candidates,
        "validation_warnings": [
            *state.validation_warnings,
            *llm_payload.validation_warnings,
            *validation_warnings,
            *routing_warnings,
        ],
        "llm_usage": usage,
        "llm_calls": [*state.llm_calls, llm_call],
    }


def load_basecase_samples(state: ModelParameterProposalState) -> dict[str, Any]:
    if state.parameter_knowledge_base is None:
        raise MIBaseError(
            ErrorCode.INVALID_REQUEST,
            detail="parameter_knowledge_base is required",
        )
    records, warnings = build_basecase_records(
        state.parameter_knowledge_base,
        state.candidate_mappings,
        state.scenario_context or {},
    )
    counts_by_candidate: dict[str, int] = {}
    for record in records:
        key = str(record.get("candidate_key") or "")
        counts_by_candidate[key] = counts_by_candidate.get(key, 0) + 1
    logger.info(
        "[model-parameter] loaded basecase records | scenario_id={} record_count={} counts_by_candidate={} warning_count={}",
        state.scenario_id,
        len(records),
        counts_by_candidate,
        len(warnings),
    )
    return {
        "basecase_records": records,
        "validation_warnings": [*state.validation_warnings, *warnings],
    }


def filter_basecase_records_by_slots(state: ModelParameterProposalState) -> dict[str, Any]:
    records = state.basecase_records or []
    filtered = _filter_records_by_selected_slots(records, state.parameter_slots)
    logger.info(
        "[model-parameter] filtered basecase records by slots | scenario_id={} before_count={} after_count={}",
        state.scenario_id,
        len(records),
        len(filtered),
    )
    return {
        "basecase_records": filtered,
        "validation_warnings": state.validation_warnings,
    }


async def propose_parameter_values(state: ModelParameterProposalState) -> dict[str, Any]:
    if not state.candidate_mappings:
        return {
            "parameter_adjustments": [],
            "validation_warnings": [
                *state.validation_warnings,
                "Step1.5 candidate 결과가 없어 Step3 value 산정을 수행하지 않았습니다.",
            ],
        }

    packet = build_llm_prompt_packet(
        state.scenario_context or {},
        state.candidate_mappings,
        state.non_input_items,
        state.basecase_records,
    )
    packet["period_resolution_policy"] = _period_resolution_policy()
    packet["parameter_slots"] = state.parameter_slots
    messages = [
        {"role": "system", "content": VALUE_PROPOSAL_SYSTEM},
        {
            "role": "user",
            "content": (
                "아래 JSON만 근거로 Step3 수급모델 parameter value_grid를 제안하십시오.\n"
                f"{to_compact_json(packet)}"
            ),
        },
    ]

    llm_started = time.perf_counter()
    try:
        result = await _invoke_structured(
            output_schema=LLMValueProposalResponse,
            messages=messages,
            model_name=state.model_name,
        )
        llm_payload = result.result
        usage = result.usage.model_dump() if result.usage is not None else None
        llm_call = _llm_call_trace(
            step="Step3 value proposal",
            model_name=state.model_name,
            elapsed_seconds=time.perf_counter() - llm_started,
            usage=usage,
            success=True,
        )
    except Exception as exc:
        llm_call = _llm_call_trace(
            step="Step3 value proposal",
            model_name=state.model_name,
            elapsed_seconds=time.perf_counter() - llm_started,
            usage=None,
            success=False,
            error=repr(exc),
        )
        if not state.allow_llm_fallback:
            raise
        logger.warning(
            "[model-parameter] Step3 LLM call failed, using fallback | scenario_id={} error={}",
            state.scenario_id,
            repr(exc),
        )
        llm_payload = _fallback_value_response(
            "Step3 LLM 호출 실패로 Step2 slot 기반의 검토 필요 응답을 생성했습니다.",
            state.candidate_mappings,
            state.parameter_slots,
        )
        usage = None

    adjustments, validation_warnings = _sanitize_llm_adjustments(
        llm_payload.parameter_adjustments,
        state.candidate_mappings,
        state.parameter_slots,
        state.basecase_records,
        state.scenario_context or {},
    )
    logger.info(
        "[model-parameter] proposed parameter values | scenario_id={} adjustment_count={} selected_count={} warning_count={}",
        state.scenario_id,
        len(adjustments),
        len([adjustment for adjustment in adjustments if adjustment.get("selected", True)]),
        len(llm_payload.validation_warnings) + len(validation_warnings),
    )
    return {
        "parameter_adjustments": adjustments,
        "validation_warnings": [
            *state.validation_warnings,
            *llm_payload.validation_warnings,
            *validation_warnings,
        ],
        "llm_usage": usage,
        "llm_calls": [*state.llm_calls, llm_call],
    }


async def propose_parameter_slots(state: ModelParameterProposalState) -> dict[str, Any]:
    if not state.candidate_mappings:
        return {
            "parameter_slots": [],
            "validation_warnings": state.validation_warnings,
        }

    packet = build_llm_prompt_packet(
        state.scenario_context or {},
        state.candidate_mappings,
        state.non_input_items,
        [],
    )
    packet["period_resolution_policy"] = _period_resolution_policy()
    packet["slot_selection_limits"] = {
        "maxParameterSlots": MAX_PARAMETER_SLOTS,
        "priority": [
            "basecase_slot_options에 존재하고 scenario/event 의미와 일치하는 slot",
            "basecase에는 없지만 scenario/event에 명확하거나 의미론적으로 타당한 실제 모델 input slot",
        ],
    }
    packet["basecase_slot_options"] = _build_basecase_slot_options(
        state.basecase_records,
    )
    logger.info(
        "[model-parameter] built basecase slot options | scenario_id={} candidate_count={} record_count={}",
        state.scenario_id,
        len(packet["basecase_slot_options"]),
        len(state.basecase_records),
    )
    messages = [
        {"role": "system", "content": SLOT_PROPOSAL_SYSTEM},
        {
            "role": "user",
            "content": (
                "아래 JSON만 근거로 Step2 수급모델 parameter slot 축을 제안하십시오.\n"
                f"{to_compact_json(packet)}"
            ),
        },
    ]

    llm_started = time.perf_counter()
    try:
        result = await _invoke_structured(
            output_schema=LLMSlotProposalResponse,
            messages=messages,
            model_name=state.model_name,
        )
        llm_payload = result.result
        usage = result.usage.model_dump() if result.usage is not None else None
        llm_call = _llm_call_trace(
            step="Step2 slot proposal",
            model_name=state.model_name,
            elapsed_seconds=time.perf_counter() - llm_started,
            usage=usage,
            success=True,
        )
    except Exception as exc:
        llm_call = _llm_call_trace(
            step="Step2 slot proposal",
            model_name=state.model_name,
            elapsed_seconds=time.perf_counter() - llm_started,
            usage=None,
            success=False,
            error=repr(exc),
        )
        if not state.allow_llm_fallback:
            raise
        logger.warning(
            "[model-parameter] Step2 LLM call failed, using fallback | scenario_id={} error={}",
            state.scenario_id,
            repr(exc),
        )
        llm_payload = _fallback_slot_response(
            "Step2 LLM 호출 실패로 후보 parameter와 basecase records 기반의 "
            "검토 필요 응답을 생성했습니다.",
            state.candidate_mappings,
        )
        usage = None

    slots, validation_warnings = _sanitize_llm_slots(
        llm_payload.parameter_slots,
        state.candidate_mappings,
        max_selected_slots=MAX_PARAMETER_SLOTS,
    )
    non_inputs = [
        item.model_dump()
        for item in llm_payload.non_input_items
    ] or state.non_input_items
    logger.info(
        "[model-parameter] proposed parameter slots | scenario_id={} slot_count={} selected_count={} warning_count={}",
        state.scenario_id,
        len(slots),
        len([slot for slot in slots if slot.get("selected", True)]),
        len(llm_payload.validation_warnings) + len(validation_warnings),
    )
    return {
        "parameter_slots": slots,
        "non_input_items": non_inputs,
        "validation_warnings": [
            *state.validation_warnings,
            *llm_payload.validation_warnings,
            *validation_warnings,
        ],
        "llm_usage": usage,
        "llm_calls": [*state.llm_calls, llm_call],
    }


def _llm_call_trace(
    *,
    step: str,
    model_name: str | None,
    elapsed_seconds: float,
    usage: dict[str, Any] | None,
    success: bool,
    error: str | None = None,
) -> dict[str, Any]:
    trace: dict[str, Any] = {
        "step": step,
        "success": success,
        "model_name": model_name,
        "elapsed_seconds": round(max(0.0, elapsed_seconds), 3),
    }
    if usage is not None:
        trace["usage"] = usage
    if error:
        trace["error"] = error
    logger.info(
        "[model-parameter] LLM call timing | step={} model_name={} success={} elapsed_seconds={} total_tokens={}",
        step,
        model_name,
        success,
        trace["elapsed_seconds"],
        (usage or {}).get("total_tokens"),
    )
    return trace


async def _invoke_structured(
    *,
    output_schema: type[Any],
    messages: list[dict[str, str]],
    model_name: str | None,
) -> Any:
    from apps.connectors.llm.llm_client import invoke_llm_structured_output

    return await invoke_llm_structured_output(
        output_schema=output_schema,
        messages=messages,
        model_name=model_name,
        preference=ModelPreference.QUALITY,
        temperature=0.0,
        max_retries=2,
    )


AMBIGUOUS_AXIS_TOKENS = (
    "미정",
    "후보",
    "추정",
    "불명",
    "미상",
    "일부",
    "대체 공급국",
    "확정 불가",
    "unknown",
    "unspecified",
    "not specified",
    "tbd",
    "n/a",
)
MULTI_VALUE_AXIS_MARKERS = (";", "；", " 또는 ", " or ")


def _axis_value_issue(axis_name: Any, axis_value: Any) -> str | None:
    if axis_value is None:
        return "빈 축 값"
    text = str(axis_value).strip()
    if not text:
        return "빈 축 값"
    normalized = " ".join(text.lower().split())
    if "?" in text:
        return "불확실성 표기 포함"
    for token in AMBIGUOUS_AXIS_TOKENS:
        if token in normalized:
            return f"모호한 축 값 포함: {token}"
    for marker in MULTI_VALUE_AXIS_MARKERS:
        if marker in normalized:
            return f"여러 축 값을 하나의 문자열로 결합함: {marker.strip()}"
    axis_name_text = str(axis_name or "").lower()
    if axis_name_text in {"year", "month", "period"} and "향후" in normalized:
        return "기간 표현을 명확한 Year/Month/Period 값으로 변환하지 않음"
    return None


def _slot_axis_issues(slot_axes: list[ParameterSlotAxis]) -> list[str]:
    issues: list[str] = []
    for axis in slot_axes:
        issue = _axis_value_issue(axis.axis_name, axis.axis_value)
        if issue:
            issues.append(f"{axis.axis_name}={axis.axis_value}: {issue}")
    return issues


def _coordinate_issues(coordinates: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for axis_name, axis_value in coordinates.items():
        issue = _axis_value_issue(axis_name, axis_value)
        if issue:
            issues.append(f"{axis_name}={axis_value}: {issue}")
    period_issue = _year_month_coordinate_issue(coordinates)
    if period_issue:
        issues.append(period_issue)
    return issues


def _int_axis_value(value: Any) -> int | None:
    try:
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return None
            return int(float(text))
        return int(value)
    except (TypeError, ValueError):
        return None


def _year_month_coordinate_issue(coordinates: dict[str, Any]) -> str | None:
    year = _int_axis_value(coordinates.get("Year"))
    month = _int_axis_value(coordinates.get("Month"))
    if year is None or month is None:
        return None
    if not 1 <= month <= 12:
        return f"Year/Month 좌표의 Month가 유효하지 않음: {month}"
    return None


def _normalize_axis_value(value: Any) -> str:
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return " ".join(str(value).strip().lower().split())


def _record_matches_slot(record: dict[str, Any], slot: dict[str, Any]) -> bool:
    record_axes = record.get("axes") or {}
    slot_axes = slot.get("slot_axes") or []
    if not slot_axes:
        return True
    matched_axis_count = 0
    for axis in slot_axes:
        axis_name = axis.get("axis_name")
        if axis_name not in record_axes:
            continue
        matched_axis_count += 1
        if _normalize_axis_value(record_axes.get(axis_name)) != _normalize_axis_value(
            axis.get("axis_value"),
        ):
            return False
    return matched_axis_count > 0


def _filter_records_by_selected_slots(
    records: list[dict[str, Any]],
    slots: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    slots_by_candidate: dict[str, list[dict[str, Any]]] = {}
    for slot in slots:
        if slot.get("selected", True) is False:
            continue
        candidate_key = str(slot.get("candidate_key") or "")
        if not candidate_key:
            continue
        slots_by_candidate.setdefault(candidate_key, []).append(slot)

    filtered: list[dict[str, Any]] = []
    for record in records:
        candidate_key = str(record.get("candidate_key") or "")
        candidate_slots = slots_by_candidate.get(candidate_key) or []
        if any(_record_matches_slot(record, slot) for slot in candidate_slots):
            filtered.append(record)
    return filtered


def _slot_option_value(value: Any) -> Any:
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def _build_basecase_slot_options(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    options: dict[str, dict[str, Any]] = {}
    axis_values_by_candidate: dict[str, dict[str, dict[str, Any]]] = {}
    value_names_by_candidate: dict[str, set[str]] = {}
    for record in records:
        candidate_key = str(record.get("candidate_key") or "")
        option = options.setdefault(
            candidate_key,
            {
                "candidate_key": candidate_key,
                "model_file": record.get("model_file"),
                "sheet_name": record.get("sheet_name"),
                "parameter_name": record.get("parameter_name"),
                "record_count": 0,
                "axis_names": [],
                "axis_values": {},
                "value_names": [],
            },
        )
        option["record_count"] += 1
        axis_values = axis_values_by_candidate.setdefault(candidate_key, {})
        for axis_name, axis_value in (record.get("axes") or {}).items():
            axis_name_text = str(axis_name)
            if axis_name_text not in option["axis_names"]:
                option["axis_names"].append(axis_name_text)
            values = axis_values.setdefault(axis_name_text, {})
            display_value = _slot_option_value(axis_value)
            values.setdefault(_normalize_axis_value(display_value), display_value)
        value_name = record.get("value_name")
        if value_name is not None:
            value_names_by_candidate.setdefault(candidate_key, set()).add(str(value_name))

    for candidate_key, option in options.items():
        axis_values = axis_values_by_candidate.get(candidate_key) or {}
        option["axis_values"] = {
            axis_name: [
                value
                for _, value in sorted(values.items(), key=lambda item: str(item[1]))
            ]
            for axis_name, values in axis_values.items()
        }
        option["value_names"] = sorted(value_names_by_candidate.get(candidate_key) or set())
    return list(options.values())


def _sanitize_candidate_decisions(
    decisions: list[ParameterCandidateDecision],
    candidates: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    candidate_by_key = {str(candidate["candidate_key"]): candidate for candidate in candidates}
    decision_by_key: dict[str, ParameterCandidateDecision] = {}
    selected_candidates: list[dict[str, Any]] = []
    warnings: list[str] = []
    returned_keys: set[str] = set()
    selected_keys: set[str] = set()

    for decision in decisions:
        candidate = candidate_by_key.get(decision.candidate_key)
        if candidate is None:
            warnings.append(
                "LLM이 알 수 없는 candidate_key를 반환해 후보 검증 결과에서 제외했습니다: "
                f"{decision.candidate_key}",
            )
            continue
        returned_keys.add(decision.candidate_key)
        decision_by_key[decision.candidate_key] = decision

    for candidate in candidates:
        candidate_key = str(candidate.get("candidate_key") or "")
        decision = decision_by_key.get(candidate_key)
        mapping_method = str(candidate.get("mapping_method") or "").lower()

        if mapping_method == "direct":
            if candidate_key in selected_keys:
                continue
            enriched = dict(candidate)
            if decision is None:
                enriched["candidate_validation_rationale_ko"] = (
                    "DB 매핑에서 direct로 지정된 모델 input이므로 LLM 응답 누락과 무관하게 "
                    "selected=true로 유지했습니다."
                )
                enriched["candidate_validation_confidence"] = 1.0
                warnings.append(
                    "LLM 후보 검증 응답에 누락된 direct candidate_key는 유지했습니다: "
                    f"{candidate_key}",
                )
            elif decision.selected:
                enriched["candidate_validation_rationale_ko"] = decision.rationale_ko
                enriched["candidate_validation_confidence"] = decision.confidence_overall
            else:
                enriched["candidate_validation_rationale_ko"] = (
                    "DB 매핑에서 direct로 지정된 모델 input이므로 LLM selected=false와 "
                    f"무관하게 유지했습니다. LLM 제외 사유: {decision.rationale_ko}"
                )
                enriched["candidate_validation_confidence"] = 1.0
                warnings.append(
                    "direct 후보는 LLM selected=false와 무관하게 유지했습니다: "
                    f"{candidate_key}",
                )
            selected_keys.add(candidate_key)
            selected_candidates.append(enriched)
            continue

        if decision is None or not decision.selected:
            continue
        if candidate_key in selected_keys:
            continue
        selected_keys.add(candidate_key)
        enriched = dict(candidate)
        enriched["candidate_validation_rationale_ko"] = decision.rationale_ko
        enriched["candidate_validation_confidence"] = decision.confidence_overall
        selected_candidates.append(enriched)

    missing_keys = sorted(
        key
        for key in set(candidate_by_key) - returned_keys
        if str(candidate_by_key[key].get("mapping_method") or "").lower() != "direct"
    )
    if missing_keys:
        warnings.append(
            "LLM 후보 검증 응답에 누락된 candidate_key는 제외했습니다: "
            f"{missing_keys}",
        )
    if candidates and not selected_candidates:
        warnings.append("LLM 후보 검증 결과 selected=true candidate가 없습니다.")
    return selected_candidates, warnings


ROUTING_COMMENT_GENERIC_TOKENS = {
    "경우",
    "시설",
    "시",
    "영향",
    "유형",
    "피해",
    "facility",
    "impact",
    "type",
    "when",
}


def _routing_match_tokens(value: Any) -> list[str]:
    tokens = re.findall(r"[0-9a-zA-Z가-힣]+", str(value or "").lower())
    return [
        token
        for token in tokens
        if len(token) >= 2 and token not in ROUTING_COMMENT_GENERIC_TOKENS
    ]


def _routing_comment_matches_dimension_value(value: Any, comment: Any) -> bool:
    value_tokens = _routing_match_tokens(value)
    comment_tokens = _routing_match_tokens(comment)
    if not value_tokens or not comment_tokens:
        return False
    comment_text = " ".join(comment_tokens)
    return all(token in comment_text for token in value_tokens)


def _apply_routing_comment_overrides(
    all_candidates: list[dict[str, Any]],
    selected_candidates: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Use bridge-sheet routing comments as deterministic tiebreakers.

    LLM still performs the candidate gate, but when the DB dimension value
    clearly matches a routing row comment such as "생산 시설 피해 시", that row is
    the authoritative route for the dimension.
    """

    selected_by_key = {
        str(candidate.get("candidate_key") or ""): dict(candidate)
        for candidate in selected_candidates
    }
    warnings: list[str] = []
    routing_groups: dict[tuple[Any, str], list[dict[str, Any]]] = {}
    for candidate in all_candidates:
        if str(candidate.get("mapping_method") or "").lower() != "routing":
            continue
        group_key = (
            candidate.get("event_type_l2_id"),
            str(candidate.get("dimension_key") or candidate.get("source_dimension_id") or ""),
        )
        routing_groups.setdefault(group_key, []).append(candidate)

    for group_candidates in routing_groups.values():
        matched = [
            candidate
            for candidate in group_candidates
            if _routing_comment_matches_dimension_value(
                candidate.get("source_dimension_value"),
                candidate.get("mapping_comment"),
            )
        ]
        if not matched:
            continue
        matched_keys = {str(candidate.get("candidate_key") or "") for candidate in matched}
        for candidate in group_candidates:
            candidate_key = str(candidate.get("candidate_key") or "")
            if candidate_key in matched_keys:
                if candidate_key not in selected_by_key:
                    enriched = dict(candidate)
                    enriched["candidate_validation_rationale_ko"] = (
                        "DB 매핑 comment가 scenario dimension 값과 명확히 일치하여 "
                        "LLM 후보 검증 결과를 보정했습니다."
                    )
                    enriched["candidate_validation_confidence"] = 1.0
                    selected_by_key[candidate_key] = enriched
                    warnings.append(
                        "routing 후보를 DB 매핑 comment 기준으로 selected=true 보정했습니다: "
                        f"{candidate_key}",
                    )
                continue
            if candidate_key in selected_by_key:
                selected_by_key.pop(candidate_key, None)
                warnings.append(
                    "routing 후보를 DB 매핑 comment 기준으로 selected=false 보정했습니다: "
                    f"{candidate_key}",
                )

    ordered = [
        selected_by_key[str(candidate.get("candidate_key") or "")]
        for candidate in all_candidates
        if str(candidate.get("candidate_key") or "") in selected_by_key
    ]
    return ordered, warnings


def _sanitize_llm_slots(
    slots: list[ParameterSlotProposal],
    candidates: list[dict[str, Any]],
    *,
    max_selected_slots: int = MAX_PARAMETER_SLOTS,
) -> tuple[list[dict[str, Any]], list[str]]:
    candidate_by_key = {str(candidate["candidate_key"]): candidate for candidate in candidates}
    sanitized: list[dict[str, Any]] = []
    warnings: list[str] = []
    selected_slot_count = 0
    for slot in slots:
        if slot.candidate_key not in candidate_by_key:
            warnings.append(
                "LLM이 알 수 없는 candidate_key를 반환해 slot을 제외했습니다: "
                f"{slot.candidate_key}",
            )
            continue
        issues = _slot_axis_issues(slot.slot_axes)
        if issues:
            reason = (
                "LLM이 실제 모델 input으로 사용할 수 없는 모호한 slot 값을 반환해 "
                f"selected=false로 보정했습니다: {', '.join(issues)}"
            )
            warnings.append(f"{reason}: {slot.candidate_key}")
            patched = slot.model_copy(
                update={
                    "selected": False,
                    "slot_axes": [],
                    "needs_user_review": True,
                    "warnings": [*slot.warnings, reason],
                },
            )
            sanitized.append(patched.model_dump())
            continue
        if slot.selected is not False:
            selected_slot_count += 1
            if selected_slot_count > max_selected_slots:
                reason = (
                    "LLM이 slot_selection_limits.maxParameterSlots를 초과해 반환하여 "
                    "초과 slot을 selected=false로 보정했습니다."
                )
                warnings.append(f"{reason}: {slot.candidate_key}")
                patched = slot.model_copy(
                    update={
                        "selected": False,
                        "needs_user_review": True,
                        "warnings": [*slot.warnings, reason],
                    },
                )
                sanitized.append(patched.model_dump())
                continue
        sanitized.append(slot.model_dump())
    return sanitized, warnings


def _group_selected_slots_by_candidate(
    slots: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for slot in slots:
        if slot.get("selected", True) is False:
            continue
        candidate_key = str(slot.get("candidate_key") or "")
        if not candidate_key:
            continue
        grouped.setdefault(candidate_key, []).append(slot)
    return grouped


def _slot_axis_value(axis_name: str, axis_value: Any) -> Any:
    if axis_name.lower() in {"year", "month"}:
        parsed = _int_axis_value(axis_value)
        if parsed is not None:
            return parsed
    return axis_value


def _slot_axes_for_candidate(slots: list[dict[str, Any]]) -> list[ParameterSlotAxis]:
    slot_axes: list[ParameterSlotAxis] = []
    seen: set[tuple[str, str]] = set()
    for slot in slots:
        for axis in slot.get("slot_axes") or []:
            axis_name = str(axis.get("axis_name") or "").strip()
            if not axis_name:
                continue
            axis_value = _slot_axis_value(axis_name, axis.get("axis_value"))
            key = (axis_name, _normalize_axis_value(axis_value))
            if key in seen:
                continue
            seen.add(key)
            slot_axes.append(
                ParameterSlotAxis(
                    axis_name=axis_name,
                    axis_value=str(axis_value),
                    rationale=axis.get("rationale"),
                ),
            )
    return slot_axes


def _slot_coordinates_for_candidate(slots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    coordinates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for slot in slots:
        coordinate: dict[str, Any] = {}
        for axis in slot.get("slot_axes") or []:
            axis_name = str(axis.get("axis_name") or "").strip()
            if not axis_name:
                continue
            axis_value = _slot_axis_value(axis_name, axis.get("axis_value"))
            if _axis_value_issue(axis_name, axis_value):
                continue
            coordinate[axis_name] = axis_value
        if not coordinate:
            continue
        key = to_compact_json(coordinate)
        if key in seen:
            continue
        seen.add(key)
        coordinates.append(coordinate)
    return coordinates


def _apply_slot_coordinates_to_cells(
    cells: list[ParameterValueCell],
    slot_coordinates: list[dict[str, Any]],
) -> list[ParameterValueCell]:
    if not slot_coordinates:
        return cells

    patched: list[ParameterValueCell] = []
    for cell in cells:
        for coordinate in slot_coordinates:
            patched.append(
                cell.model_copy(
                    update={
                        "coordinates": {
                            **(cell.coordinates or {}),
                            **coordinate,
                        },
                    },
                ),
            )
    return patched


def _canonical_coordinate_key(coordinates: dict[str, Any]) -> str:
    normalized = {
        axis_name: _normalize_axis_value(_slot_axis_value(axis_name, axis_value))
        for axis_name, axis_value in sorted(
            (
                (str(raw_axis_name).strip(), axis_value)
                for raw_axis_name, axis_value in (coordinates or {}).items()
                if str(raw_axis_name).strip()
            ),
            key=lambda item: item[0],
        )
    }
    return to_compact_json(normalized)


def _value_cell_signature(cell: ParameterValueCell) -> str:
    return to_compact_json(
        {
            "basecase_value": cell.basecase_value,
            "operation": cell.operation,
            "proposed_value": cell.proposed_value,
            "unit": cell.unit,
        },
    )


def _dedupe_value_grid_by_slot(
    cells: list[ParameterValueCell],
) -> tuple[list[ParameterValueCell], list[str]]:
    deduped: list[ParameterValueCell] = []
    seen_by_slot: dict[str, tuple[str, ParameterValueCell]] = {}
    conflicts: list[str] = []

    for cell in cells:
        slot_key = _canonical_coordinate_key(cell.coordinates)
        signature = _value_cell_signature(cell)
        existing = seen_by_slot.get(slot_key)
        if existing is None:
            seen_by_slot[slot_key] = (signature, cell)
            deduped.append(cell)
            continue
        if existing[0] == signature:
            continue
        conflicts.append(
            "동일 slot 좌표에 서로 다른 value 제안이 반환되었습니다: "
            f"slot={slot_key}, existingOperation={existing[1].operation}, "
            f"newOperation={cell.operation}",
        )

    return deduped, conflicts


def _sanitize_llm_adjustments(
    adjustments: list[ParameterAdjustment],
    candidates: list[dict[str, Any]],
    slots: list[dict[str, Any]],
    basecase_records: list[dict[str, Any]],
    scenario_context: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[str]]:
    candidate_by_key = {str(candidate["candidate_key"]): candidate for candidate in candidates}
    slots_by_key = _group_selected_slots_by_candidate(slots)
    basecase_by_reference_id = {
        str(record["reference_id"]): record
        for record in basecase_records
        if record.get("reference_id") is not None
    }
    sanitized: list[dict[str, Any]] = []
    warnings: list[str] = []
    returned_candidate_keys: set[str] = set()
    for adjustment in adjustments:
        candidate = candidate_by_key.get(adjustment.candidate_key)
        if candidate is None:
            warnings.append(
                "LLM이 알 수 없는 candidate_key를 반환해 제외했습니다: "
                f"{adjustment.candidate_key}",
            )
            continue
        returned_candidate_keys.add(adjustment.candidate_key)
        slot_axes = adjustment.slot_axes or _slot_axes_for_candidate(
            slots_by_key.get(adjustment.candidate_key, []),
        )
        selected = adjustment.selected
        local_warnings = list(adjustment.warnings)
        slot_issues = _slot_axis_issues(slot_axes)
        if slot_issues and selected:
            reason = (
                "Step3 응답 slot_axes에 실제 모델 input으로 사용할 수 없는 값이 있어 "
                f"selected=false로 보정했습니다: {', '.join(slot_issues)}"
            )
            local_warnings.append(reason)
            warnings.append(f"{reason}: {adjustment.candidate_key}")
            selected = False

        value_grid: list[ParameterValueCell] = []
        for cell in adjustment.value_grid:
            coordinate_issues = _coordinate_issues(cell.coordinates)
            if coordinate_issues:
                reason = (
                    "Step3 응답 value_grid.coordinates에 모호한 값이 있어 "
                    f"cell을 제외했습니다: {', '.join(coordinate_issues)}"
                )
                local_warnings.append(reason)
                warnings.append(f"{reason}: {adjustment.candidate_key}")
                continue
            if cell.proposed_value is None:
                reason = (
                    "Step3 응답 value_grid.proposed_value가 null이라 "
                    "cell을 제외했습니다. 범위형 dimension은 자동 변환해야 합니다."
                )
                local_warnings.append(reason)
                warnings.append(f"{reason}: {adjustment.candidate_key}")
                continue
            if cell.operation in {"unknown", "not_applicable"}:
                reason = (
                    "Step3 응답 value_grid.operation이 실제 모델 input 적용 방식으로 "
                    f"사용할 수 없어 cell을 제외했습니다: {cell.operation}"
                )
                local_warnings.append(reason)
                warnings.append(f"{reason}: {adjustment.candidate_key}")
                continue
            value_grid.append(_patch_basecase_value(cell, basecase_by_reference_id))

        value_grid, slot_conflicts = _dedupe_value_grid_by_slot(value_grid)
        if slot_conflicts and selected:
            reason = (
                "Step3 응답 value_grid에 동일 slot 좌표의 value type/value 충돌이 있어 "
                "selected=false로 보정했습니다."
            )
            local_warnings.extend([reason, *slot_conflicts])
            warnings.append(f"{reason}: {adjustment.candidate_key}")
            warnings.extend(f"{conflict}: {adjustment.candidate_key}" for conflict in slot_conflicts)
            selected = False

        if selected and not value_grid:
            reason = "명확한 value_grid 좌표/제안값이 없어 selected=false로 보정했습니다."
            local_warnings.append(reason)
            warnings.append(f"{reason}: {adjustment.candidate_key}")
            selected = False

        patched = adjustment.model_copy(
            update={
                "model_file": str(candidate.get("model_file") or adjustment.model_file),
                "model_sheet": str(candidate.get("model_sheet") or adjustment.model_sheet),
                "parameter_name": str(
                    candidate.get("canonical_parameter_name") or adjustment.parameter_name,
                ),
                "selected": selected,
                "slot_axes": slot_axes,
                "value_grid": value_grid if selected else [],
                "needs_user_review": adjustment.needs_user_review or not selected,
                "warnings": local_warnings,
            },
        )
        sanitized.append(patched.model_dump())

    missing_candidate_keys = sorted(set(candidate_by_key) - returned_candidate_keys)
    for candidate_key in missing_candidate_keys:
        candidate = candidate_by_key[candidate_key]
        reason = (
            "LLM Step3 응답에 candidate_key가 누락되어 서버가 selected=false "
            "검토 항목으로 보강했습니다."
        )
        slot_axes = [
            *_slot_axes_for_candidate(slots_by_key.get(candidate_key, [])),
        ]
        sanitized.append(
            ParameterAdjustment(
                candidate_key=candidate_key,
                model_file=str(candidate.get("model_file") or ""),
                model_sheet=str(candidate.get("model_sheet") or ""),
                parameter_name=str(
                    candidate.get("canonical_parameter_name")
                    or candidate.get("parameter_name")
                    or "",
                ),
                selected=False,
                slot_axes=slot_axes,
                value_grid=[],
                parameter_selection_rationale_ko=reason,
                confidence_overall=0.0,
                needs_user_review=True,
                warnings=[reason],
            ).model_dump(),
        )
        warnings.append(f"{reason}: {candidate_key}")
    sanitized = _backfill_rule_based_adjustments(
        sanitized,
        candidates,
        slots_by_key,
        scenario_context,
        warnings,
    )
    return sanitized, warnings


def _backfill_rule_based_adjustments(
    adjustments: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    slots_by_key: dict[str, list[dict[str, Any]]],
    scenario_context: dict[str, Any],
    warnings: list[str],
) -> list[dict[str, Any]]:
    candidate_by_key = {str(candidate.get("candidate_key") or ""): candidate for candidate in candidates}
    patched: list[dict[str, Any]] = []
    backfilled_count = 0
    for adjustment in adjustments:
        candidate_key = str(adjustment.get("candidate_key") or "")
        candidate = candidate_by_key.get(candidate_key)
        if candidate is None:
            patched.append(adjustment)
            continue
        if adjustment.get("selected", True) is not False and adjustment.get("value_grid"):
            patched.append(adjustment)
            continue
        fallback = _build_rule_based_adjustment(
            candidate,
            slots_by_key.get(candidate_key) or [],
            scenario_context,
        )
        if fallback is None:
            patched.append(adjustment)
            continue
        patched.append(fallback.model_dump())
        backfilled_count += 1
        warnings.append(
            "LLM Step3가 명확한 value_grid를 만들지 못해 scenario dimension 기반 "
            f"규칙 보정값을 생성했습니다: {candidate_key}",
        )
    if backfilled_count:
        logger.info(
            "[model-parameter] backfilled rule-based values | scenario_id={} backfilled_count={}",
            (scenario_context.get("scenario") or {}).get("scenario_id"),
            backfilled_count,
        )
    return patched


def _build_rule_based_adjustment(
    candidate: dict[str, Any],
    slots: list[dict[str, Any]],
    scenario_context: dict[str, Any],
) -> ParameterAdjustment | None:
    scenario = scenario_context.get("scenario") or {}
    dimensions = scenario.get("dimension_values") or {}
    canonical = str(candidate.get("canonical_parameter_name") or candidate.get("parameter_name") or "")
    canonical_key = normalize_text(canonical)
    slot_coordinates = _slot_coordinates_for_candidate(slots)
    cells: list[ParameterValueCell] = []
    rationale = (
        "LLM이 최종 value_grid를 확정하지 못했으나, scenario dimension에 모델 input으로 "
        "변환 가능한 명확한 값이 있어 규칙 기반 보정으로 선택했습니다."
    )

    if canonical_key == "supplydisruption":
        cells = _supply_disruption_fallback_cells(
            dimensions,
            scenario_context,
            allow_slot_coordinates=bool(slot_coordinates),
        )
    elif canonical_key == "volumecancelled":
        cells = _volume_cancelled_fallback_cells(dimensions)
    elif canonical_key == "shippingcost":
        cells = _shipping_cost_fallback_cells(dimensions)
    elif canonical_key == "regasadjustment":
        cells = _regas_fallback_cells(
            dimensions,
            scenario_context,
            allow_slot_coordinates=bool(slot_coordinates),
        )
    elif canonical_key in {"liqutiladjustment", "liqprodadjustment"}:
        cells = _liquefaction_fallback_cells(
            canonical,
            dimensions,
            scenario_context,
            allow_slot_coordinates=bool(slot_coordinates),
        )
    elif canonical_key == "useradjustedgasdemand":
        cells = _gas_demand_fallback_cells(
            dimensions,
            scenario_context,
            allow_slot_coordinates=bool(slot_coordinates),
        )

    if not cells:
        return None
    cells = _apply_slot_coordinates_to_cells(cells, slot_coordinates)

    slot_axes = _slot_axes_for_candidate(slots) or [
        ParameterSlotAxis(
            axis_name=str(axis_name),
            axis_value=str(axis_value),
            rationale="규칙 기반 value backfill에서 확정한 slot입니다.",
        )
        for axis_name, axis_value in (cells[0].coordinates or {}).items()
    ]
    return ParameterAdjustment(
        candidate_key=str(candidate.get("candidate_key") or ""),
        model_file=str(candidate.get("model_file") or ""),
        model_sheet=str(candidate.get("model_sheet") or ""),
        parameter_name=canonical,
        selected=True,
        slot_axes=slot_axes,
        value_grid=cells,
        parameter_selection_rationale_ko=rationale,
        confidence_overall=0.55,
        needs_user_review=False,
        warnings=["LLM value 단계 보정을 위해 규칙 기반 value_grid를 생성했습니다."],
    )


def normalize_text(value: Any) -> str:
    return re.sub(r"[^0-9a-zA-Z가-힣]+", "", str(value or "")).lower()


def _dimension_text(dimensions: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = dimensions.get(key)
        if value is not None:
            return str(value)
    return ""


def _numeric_from_text(value: Any) -> float | None:
    text = str(value or "")
    matches = re.findall(r"[+-]?\d+(?:\.\d+)?", text)
    if not matches:
        return None
    numbers = [float(item) for item in matches]
    if len(numbers) >= 2 and ("~" in text or "〜" in text):
        return sum(numbers[:2]) / 2
    number = numbers[0]
    if any(marker in text for marker in ("<", "미만", "이내")):
        if "%" in text and number == 5:
            return 3.0
        return number / 2
    return number


def _percent_from_dimension(dimensions: dict[str, Any], *keys: str) -> float | None:
    return _numeric_from_text(_dimension_text(dimensions, *keys))


def _intensity_percent(value: Any) -> float | None:
    text = str(value or "").lower()
    if any(token in text for token in ("낮", "약", "소규모", "경미")):
        return 5.0
    if any(token in text for token in ("중간", "보통", "중")):
        return 15.0
    if any(token in text for token in ("높", "강", "큼", "대규모", "급격")):
        return 25.0
    return _numeric_from_text(value)


def _current_year_month() -> tuple[int, int]:
    today = date.today()
    return today.year, today.month


def _period_resolution_policy() -> dict[str, Any]:
    year, month = _current_year_month()
    return {
        "current_date": date.today().isoformat(),
        "current_year": year,
        "current_month": month,
        "rules": [
            "scenario/event에 YYYY-MM 또는 YYYY년 M월처럼 연월이 명확하면 현재 기준월과 무관하게 그대로 사용합니다.",
            "연도 없이 월만 명시되면 current_year/current_month 이후의 가장 가까운 해당 월로 변환합니다.",
            "명확한 연월/월 근거가 없으면 추론상 current_year/current_month 이후부터 period를 전개합니다.",
        ],
    }


def _is_current_or_future_year_month(year: int, month: int) -> bool:
    current_year, current_month = _current_year_month()
    return (year, month) >= (current_year, current_month)


def _first_explicit_year_month(text: str) -> tuple[int, int] | None:
    patterns = (
        r"(20\d{2})\s*년\s*(1[0-2]|0?[1-9])\s*월",
        r"(20\d{2})[-./](1[0-2]|0?[1-9])(?:[-./]\d{1,2})?",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return int(match.group(1)), int(match.group(2))
    return None


def _month_only_candidates(text: str) -> list[int]:
    months: list[int] = []
    for match in re.finditer(r"(?<!\d)(1[0-2]|0?[1-9])\s*월", text):
        month = int(match.group(1))
        if month not in months:
            months.append(month)
    return months


def _nearest_current_or_future_month(months: list[int]) -> tuple[int, int] | None:
    if not months:
        return None
    current_year, current_month = _current_year_month()
    candidates = [
        (current_year if month >= current_month else current_year + 1, month)
        for month in months
    ]
    return min(candidates)


def _scenario_period_text(dimensions: dict[str, Any], scenario_context: dict[str, Any]) -> str:
    scenario = scenario_context.get("scenario") or {}
    return "\n".join(
        str(item or "")
        for item in (
            scenario.get("title"),
            scenario.get("narrative"),
            *dimensions.values(),
        )
    )


def _event_period_text(scenario_context: dict[str, Any]) -> str:
    group = scenario_context.get("scenario_group") or {}
    event = scenario_context.get("event") or {}
    return "\n".join(
        str(item or "")
        for item in (
            group.get("title"),
            group.get("summary"),
            group.get("description"),
            event.get("occurred_at"),
            event.get("latest_record_first_created"),
            event.get("oldest_record_first_created"),
            event.get("event_title_ko"),
            event.get("one_line_summary"),
            event.get("detail_analysis"),
        )
    )


def _period_start_year_month(
    dimensions: dict[str, Any],
    scenario_context: dict[str, Any],
) -> tuple[int, int, str]:
    scenario_text = _scenario_period_text(dimensions, scenario_context)
    scenario_explicit = _first_explicit_year_month(scenario_text)
    if scenario_explicit is not None:
        return (*scenario_explicit, "scenario에 명시된 연월")

    event_text = _event_period_text(scenario_context)
    event_explicit = _first_explicit_year_month(event_text)
    if event_explicit is not None:
        return (*event_explicit, "event에 명시된 연월")

    scenario_month = (
        _nearest_current_or_future_month(_month_only_candidates(scenario_text))
        if scenario_explicit is None
        else None
    )
    if scenario_month is not None:
        return (*scenario_month, "scenario에 명시된 월-only를 현재 이후 연월로 변환")

    event_month = (
        _nearest_current_or_future_month(_month_only_candidates(event_text))
        if event_explicit is None
        else None
    )
    if event_month is not None:
        return (*event_month, "event에 명시된 월-only를 현재 이후 연월로 변환")

    current_year, current_month = _current_year_month()
    return current_year, current_month, "명확한 연월 근거가 없어 현재 월부터 전개"


def _context_text(scenario_context: dict[str, Any]) -> str:
    scenario = scenario_context.get("scenario") or {}
    group = scenario_context.get("scenario_group") or {}
    event = scenario_context.get("event") or {}
    return "\n".join(
        str(item or "")
        for item in (
            scenario.get("title"),
            scenario.get("narrative"),
            group.get("title"),
            group.get("summary"),
            event.get("event_title_ko"),
            event.get("one_line_summary"),
            event.get("detail_analysis"),
        )
    )


COUNTRY_PATTERNS: tuple[tuple[str, str], ...] = (
    ("노르웨이", "Norway"),
    ("norway", "Norway"),
    ("미국", "United States"),
    ("united states", "United States"),
    ("u.s.", "United States"),
    ("일본", "Japan"),
    ("japan", "Japan"),
    ("중국", "China"),
    ("china", "China"),
    ("한국", "South Korea"),
    ("korea", "South Korea"),
    ("카타르", "Qatar"),
    ("qatar", "Qatar"),
    ("호주", "Australia"),
    ("australia", "Australia"),
    ("아랍에미리트", "United Arab Emirates"),
    ("uae", "United Arab Emirates"),
    ("이란", "Iran"),
    ("iran", "Iran"),
    ("유럽", "Europe"),
    ("europe", "Europe"),
    ("러시아", "Russia"),
    ("russia", "Russia"),
)


def _infer_countries(
    scenario_context: dict[str, Any],
    *,
    max_count: int | None = None,
) -> list[str]:
    text = _context_text(scenario_context).lower()
    first_positions: dict[str, int] = {}
    for pattern, country in COUNTRY_PATTERNS:
        position = text.find(pattern.lower())
        if position >= 0:
            first_positions[country] = min(position, first_positions.get(country, position))
    countries = [
        country
        for country, _ in sorted(first_positions.items(), key=lambda item: item[1])
    ]
    if max_count is not None:
        return countries[:max_count]
    return countries


def _supply_disruption_fallback_cells(
    dimensions: dict[str, Any],
    scenario_context: dict[str, Any],
    *,
    allow_slot_coordinates: bool = False,
) -> list[ParameterValueCell]:
    utilization = _percent_from_dimension(dimensions, "utilization_change_amount")
    if utilization is None:
        return []
    alternative = _percent_from_dimension(
        dimensions,
        "alt_gas_supply_availability",
        "alt_supply_availability",
    )
    residual = utilization * (1 - ((alternative or 0.0) / 100.0))
    countries = _infer_countries(scenario_context)
    if not countries and allow_slot_coordinates:
        countries = [None]
    return [
        ParameterValueCell(
            coordinates={
                **{"Year": 2026},
                **({"Province Country": country} if country else {}),
            },
            basecase_value=None,
            proposed_value=round(-residual, 6),
            unit="%",
            operation="percent_change",
            value_selection_rationale_ko=(
                "SupplyDisruption은 upstream 생산 차질을 국가/연 단위로 반영하므로 "
                "event 문맥의 공급국과 2026년을 slot으로 사용했습니다."
            ),
            proposed_value_rationale_ko=(
                f"utilization 변화 {utilization:g}%에서 대체 공급 가능성 "
                f"{alternative or 0:g}%를 차감해 순차질 {residual:g}%를 산정했습니다."
            ),
        )
        for country in countries
    ]


def _volume_cancelled_fallback_cells(dimensions: dict[str, Any]) -> list[ParameterValueCell]:
    scale_text = _dimension_text(dimensions, "transaction_scale")
    scale = _intensity_percent(scale_text)
    if scale is None:
        return []
    mtpa = 1.0 if scale <= 5 else 3.0 if scale <= 15 else 5.0
    return [
        ParameterValueCell(
            coordinates={"Year": 2026},
            basecase_value=None,
            proposed_value=mtpa,
            unit="MTPA",
            operation="absolute",
            value_selection_rationale_ko=(
                "거래 분쟁 scenario에서 특정 거래 상대국은 확정되지 않아 명확한 Year 축만 사용했습니다."
            ),
            proposed_value_rationale_ko=(
                f"transaction_scale `{scale_text}`를 규모 변환 규칙에 따라 {mtpa:g} MTPA "
                "취소 물량으로 변환했습니다."
            ),
        ),
    ]


def _shipping_cost_fallback_cells(dimensions: dict[str, Any]) -> list[ParameterValueCell]:
    intensity = _intensity_percent(
        _dimension_text(dimensions, "transport_disruption", "impact_intensity"),
    )
    if intensity is None:
        return []
    return [
        ParameterValueCell(
            coordinates={"Year": 2026},
            basecase_value=None,
            proposed_value=round(intensity, 6),
            unit="%",
            operation="percent_change",
            value_selection_rationale_ko=(
                "ShippingCost는 운송 차질/규제 강도에 직접 연결되므로 2026년 비용 조정으로 반영했습니다."
            ),
            proposed_value_rationale_ko=(
                f"운송 차질 또는 규제 강도를 {intensity:g}% ShippingCost 상승률로 변환했습니다."
            ),
        ),
    ]


def _regas_fallback_cells(
    dimensions: dict[str, Any],
    scenario_context: dict[str, Any],
    *,
    allow_slot_coordinates: bool = False,
) -> list[ParameterValueCell]:
    affected_facility_type = _dimension_text(dimensions, "affected_facility_type")
    if "수입" not in affected_facility_type and "regas" not in affected_facility_type.lower():
        return []
    intensity = _intensity_percent(_dimension_text(dimensions, "supply_disruption_intensity"))
    if intensity is None:
        return []
    alternative = _percent_from_dimension(dimensions, "alt_lng_supply_availability")
    residual = intensity * (1 - ((alternative or 0.0) / 100.0))
    countries = _infer_countries(scenario_context)
    if not countries and allow_slot_coordinates:
        countries = [None]
    return [
        ParameterValueCell(
            coordinates={
                **{"Year": 2026},
                **({"Country": country} if country else {}),
            },
            basecase_value=None,
            proposed_value=round(-residual, 6),
            unit="%",
            operation="percent_change",
            value_selection_rationale_ko=(
                "affected_facility_type이 수입 시설이므로 재기화 처리 여력 조정 slot으로 "
                "event 문맥의 국가와 2026년을 사용했습니다."
            ),
            proposed_value_rationale_ko=(
                f"supply_disruption_intensity를 {intensity:g}% 처리 여력 차질로 변환하고, "
                f"대체 LNG 공급 가능성 {alternative or 0:g}%를 차감해 순차질 {residual:g}%로 산정했습니다."
            ),
        )
        for country in countries
    ]


def _liquefaction_fallback_cells(
    canonical: str,
    dimensions: dict[str, Any],
    scenario_context: dict[str, Any],
    *,
    allow_slot_coordinates: bool = False,
) -> list[ParameterValueCell]:
    countries = _infer_countries(scenario_context)
    if not countries and allow_slot_coordinates:
        countries = [None]
    target_utilization = _percent_from_dimension(dimensions, "target_utilization_at_ramp_up")
    if target_utilization is not None:
        proposed = target_utilization / 100 if target_utilization > 1 else target_utilization
        return [
            ParameterValueCell(
                coordinates={
                    **{"Year": 2026},
                    **({"Country": country} if country else {}),
                },
                basecase_value=None,
                proposed_value=round(proposed, 6),
                unit="%",
                operation="absolute",
                value_selection_rationale_ko=(
                    f"{canonical}은 ramp-up 목표 가동률을 액화 설비 입력에 반영하므로 "
                    "event 문맥의 공급국과 2026년을 사용했습니다."
                ),
                proposed_value_rationale_ko=(
                    f"target_utilization_at_ramp_up {target_utilization:g}%를 "
                    f"모델 입력 절대값 {proposed:g}로 변환했습니다."
                ),
            )
            for country in countries
        ]

    utilization = _percent_from_dimension(dimensions, "utilization_change_amount")
    if utilization is not None:
        direction = _utilization_direction(scenario_context)
        return [
            ParameterValueCell(
                coordinates={
                    **{"Year": 2026},
                    **({"Country": country} if country else {}),
                },
                basecase_value=None,
                proposed_value=round(direction * utilization, 6),
                unit="%",
                operation="percent_change",
                value_selection_rationale_ko=(
                    f"{canonical}은 terminal/upstream utilization 변화 폭을 액화 설비 입력에 "
                    "반영하므로 event 문맥의 공급국과 2026년을 사용했습니다."
                ),
                proposed_value_rationale_ko=(
                    f"utilization_change_amount를 {utilization:g}%로 변환하고, "
                    f"scenario/event 문맥의 방향성을 반영해 {direction * utilization:g}%로 산정했습니다."
                ),
            )
            for country in countries
        ]

    intensity = _intensity_percent(_dimension_text(dimensions, "supply_disruption_intensity"))
    if intensity is None:
        return []
    return [
        ParameterValueCell(
            coordinates={
                **{"Year": 2026},
                **({"Country": country} if country else {}),
            },
            basecase_value=None,
            proposed_value=round(-intensity, 6),
            unit="%",
            operation="percent_change",
            value_selection_rationale_ko=(
                f"{canonical}은 공급 차질 강도를 액화 설비 입력에 반영하므로 event 문맥의 "
                "공급국과 2026년을 사용했습니다."
            ),
            proposed_value_rationale_ko=(
                f"supply_disruption_intensity를 {intensity:g}% 감산 충격으로 변환했습니다."
            ),
        )
        for country in countries
    ]


def _utilization_direction(scenario_context: dict[str, Any]) -> int:
    text = _context_text(scenario_context)
    if any(token in text for token in ("감산", "감소", "차질", "지연", "손실", "하향", "제한")):
        return -1
    return 1


def _gas_demand_fallback_cells(
    dimensions: dict[str, Any],
    scenario_context: dict[str, Any],
    *,
    allow_slot_coordinates: bool = False,
) -> list[ParameterValueCell]:
    response = _percent_from_dimension(
        dimensions,
        "demand_response_alternative_lng",
        "demand_response_powermix_reduction",
        "alt_energy_absorption",
    )
    if response is None:
        return []
    residual = max(0.0, min(100.0, 100.0 - response))
    countries = _infer_countries(scenario_context)
    if not countries and allow_slot_coordinates:
        countries = [None]
    return [
        ParameterValueCell(
            coordinates={
                **{"Year": 2026},
                **({"Country": country} if country else {}),
            },
            basecase_value=None,
            proposed_value=round(residual, 6),
            unit="%",
            operation="percent_change",
            value_selection_rationale_ko=(
                "User-Adjusted Gas Demand는 국가/연 단위 수요 보정으로 사용했습니다."
            ),
            proposed_value_rationale_ko=(
                f"대체 수요 반응 {response:g}%를 제외한 잔여 {residual:g}%를 가스 수요 "
                "증가율로 변환했습니다."
            ),
        )
        for country in countries
    ]


def _patch_basecase_value(
    cell: ParameterValueCell,
    basecase_by_reference_id: dict[str, dict[str, Any]],
) -> ParameterValueCell:
    if cell.basecase_value is not None or not cell.basecase_reference_ids:
        return cell
    matched_values = [
        basecase_by_reference_id[reference_id].get("value")
        for reference_id in cell.basecase_reference_ids
        if reference_id in basecase_by_reference_id
    ]
    if not matched_values:
        return cell
    basecase_value: Any = matched_values[0] if len(matched_values) == 1 else matched_values
    return cell.model_copy(update={"basecase_value": basecase_value})


def _fallback_candidate_validation_response(
    reason: str,
    candidates: list[dict[str, Any]],
) -> LLMCandidateValidationResponse:
    return LLMCandidateValidationResponse(
        candidate_decisions=[
            ParameterCandidateDecision(
                candidate_key=str(candidate["candidate_key"]),
                selected=True,
                rationale_ko=reason,
                confidence_overall=0.2,
                warnings=[reason],
            )
            for candidate in candidates
        ],
        validation_warnings=[reason],
    )


def _fallback_slot_response(reason: str, candidates: list[dict[str, Any]]) -> LLMSlotProposalResponse:
    return LLMSlotProposalResponse(
        parameter_slots=[
            ParameterSlotProposal(
                candidate_key=str(candidate["candidate_key"]),
                selected=True,
                slot_axes=[
                    ParameterSlotAxis(
                        axis_name=str(
                            candidate.get("source_dimension_label") or "scenario_dimension",
                        ),
                        axis_value=str(candidate.get("source_dimension_value") or ""),
                        rationale="시나리오 dimension 값을 우선 slot 힌트로 사용했습니다.",
                    ),
                ],
                rationale_ko_overall=reason,
                confidence_overall=0.2,
                needs_user_review=True,
                warnings=[reason],
            )
            for candidate in candidates
        ],
        validation_warnings=[reason],
    )


def _fallback_value_response(
    reason: str,
    candidates: list[dict[str, Any]],
    slots: list[dict[str, Any]],
) -> LLMValueProposalResponse:
    slots_by_key = {str(slot["candidate_key"]): slot for slot in slots if "candidate_key" in slot}
    return LLMValueProposalResponse(
        parameter_adjustments=[
            ParameterAdjustment(
                candidate_key=str(candidate["candidate_key"]),
                model_file=str(candidate.get("model_file") or ""),
                model_sheet=str(candidate.get("model_sheet") or ""),
                parameter_name=str(
                    candidate.get("canonical_parameter_name")
                    or candidate.get("parameter_name")
                    or "",
                ),
                selected=True,
                slot_axes=[
                    ParameterSlotAxis.model_validate(axis)
                    for axis in (
                        slots_by_key.get(str(candidate["candidate_key"]), {}).get("slot_axes")
                        or []
                    )
                ],
                value_grid=[
                    ParameterValueCell(
                        coordinates={},
                        basecase_value=None,
                        proposed_value=None,
                        operation="unknown",
                        value_selection_rationale_ko=reason,
                        proposed_value_rationale_ko=reason,
                    ),
                ],
                parameter_selection_rationale_ko=reason,
                confidence_overall=0.2,
                needs_user_review=True,
                warnings=[reason],
            )
            for candidate in candidates
        ],
        validation_warnings=[reason],
    )
