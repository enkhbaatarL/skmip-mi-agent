# Copyright (c) 2026 SK Innovation E&S.
# ruff: noqa: C901, T201

"""Select and evaluate three representative Model Parameter scenarios per group.

The selector keeps Scenario representation (baseline/floor/ceiling) as a hard
preference and then maximizes the overlap of read-only runtime Parameter sets.
The evaluator separates three concepts that are easy to conflate:

* identical canonical Parameter *types* across a group's three proposals;
* different proposed value signatures for those Parameter types; and
* different values on the exact same model slot coordinates.

No proposal is created by this module. Proposal writes remain the responsibility
of ``run_proposal_only.py`` and its uncovered-only safety contract.
"""

from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
import hashlib
from itertools import combinations
import json
import math
from pathlib import Path
import statistics
from typing import Any


EXPECTED_API_VERSION = "v4"
EXPECTED_GENERATION_STRATEGY = "multi_event_model_lever_dimensions"
EXPECTED_CATALOG_VERSION = "v4.1"
EXPECTED_CATALOG_CHECKSUM = "7f4ef0b7aa60efb550b9175654fd82350f0c293debf880a9180e7e935db54d69"
EXPECTED_PROPOSAL_FLOW_RELEASE = "v4.1.3"
FIXED_TESTSET_SOURCE_FLOW_RELEASE = "v4.1.2"
EXPANDED_EVENT_SELECTION_POLICY = "expanded_event_cohort/add-only"
REGENERATED_EVENT_POOL_SELECTION_POLICY = "existing_event_pool/add-only-regenerated-scenarios"
PRESSURE_RANK = {
    "strong_bearish": -2,
    "bearish": -1,
    "balanced": 0,
    "bullish": 1,
    "strong_bullish": 2,
}
VALUE_KEYS = {"proposedValue", "proposed_value"}
NON_SLOT_KEYS = {
    *VALUE_KEYS,
    "basecaseValue",
    "basecase_value",
    "lutValue",
    "lut_value",
    "rationale",
    "operation",
}
FINAL_COHORT_PROPOSAL_STATUSES = frozenset({"PROPOSED", "CONFIRMED"})
EXPLICIT_SLOT_RATIONALE_SECTIONS = (
    "대상·기간:",
    "근거 유형:",
    "인과 경로:",
    "기준값:",
    "적용 정책:",
    "계산:",
    "제안값:",
    "근거:",
    "주요 가정:",
    "판단 설명:",
    "불확실성:",
)
AUTOMATIC_RETRY_FORBIDDEN_NOTE = "proposal evaluation raised; automatic retry is forbidden"
AUTHORIZED_INFERRED_BACKFILL = "authorized_inferred_backfill"
GROUP_RESULT_COLUMN_DEFINITIONS = (
    ("#", "고정 Event cohort에서의 Group 순서"),
    ("Group", "Scenario Group ID"),
    ("Event", "그룹 생성의 기준이 된 MI Event ID"),
    ("Event Type", "Event Type L2 코드"),
    ("성공", "대표 3개 중 Proposal이 저장·read-back 검증까지 통과한 수"),
    ("동일 종류", "3개가 모두 성공했을 때 canonical Parameter 종류 집합이 같은지; 그 외 N/A"),
    ("값 차이", "동일 종류인 성공 3개의 전체 proposedValue signature가 서로 모두 다른지; 그 외 N/A"),
    (
        "exact slot / 차이 slot",
        "세 Proposal에 공통인 동일 Parameter·전체 좌표 cell 수 / 그중 값이 다른 cell 수; 비교 불가 시 N/A",
    ),
    ("Parameter", "성공 Proposal 사이의 공통 canonical Parameter 이름; 비교 불가 시 N/A"),
)
READ_ONLY_KPI_COLUMN_DEFINITIONS = (
    (
        "대상 Group / 전체·대표 Scenario",
        "새로 생성한 Group 수 / 그 안의 전체 Scenario 수 / Group별 3개로 고정한 평가 Scenario 수",
    ),
    (
        "Release 고정",
        "Scenario Lever v4.1과 Proposal Flow v4.1.3이 실제 preflight 증적에 함께 기록됐는지",
    ),
    (
        "Runtime-capable / coverage limit",
        "현재 release의 실행 허용 Parameter 후보가 1개 이상인 Scenario / 후보가 없어 제안 실행 범위 밖인 Scenario",
    ),
    (
        "현재 write eligible / covered",
        (
            "Runtime-capable이면서 차단 상태나 기존 Proposal이 없어 지금 새 Proposal을 쓸 수 있는 Scenario / "
            "기존 Proposal 때문에 중복 쓰기를 막은 Scenario"
        ),
    ),
    (
        "3개 이상 write eligible / coverage-limit Group",
        "대표 3개를 모두 신규 제안할 수 있는 Group / 그 조건을 충족하지 못해 대표성 위주로 고정한 Group",
    ),
    (
        "대표 3개 후보 종류 동일",
        "쓰기 전 runtime 후보 Parameter 종류 집합이 대표 3개에서 동일한 Group 비율",
    ),
    (
        "Preflight FAIL / hard stop",
        "조회·정합성 검사 실패 수 / 안전상 전체 실행을 중단해야 하는 오류 수; 모두 0이어야 함",
    ),
)
PROPOSAL_KPI_COLUMN_DEFINITIONS = (
    ("Proposal 성공", "전체 고정 Scenario 중 Proposal 저장·응답·DB 정합성을 통과한 비율"),
    ("Preflight→Proposal 전환율", "Proposal 가능 판정된 Scenario 중 실제 성공한 비율"),
    ("Semantic abstention", "근거 부족·적용 위치 없음·값 미생성·무변경으로 의도적으로 제안하지 않은 수"),
    (
        "Resolved no-change / actionable abstention",
        "ABSTAINED_NO_CHANGE로 정상 종료한 수 / 추가 개선이 필요한 나머지 semantic abstention 수",
    ),
    (
        "Semantic trace 완전 / 누락",
        "Semantic abstention 중 stage evidence·step summary·누적 LLM call이 모두 있는 수 / 빠진 수",
    ),
    ("그룹 내 3개 모두 성공", "종류/값 비교가 가능한 그룹 수"),
    ("파라미터 종류 동일", "3개 모두 성공한 그룹 중 canonical Parameter 종류 집합이 같은 비율"),
    (
        "같은 종류 + Scenario별 다른 제안값 (메인)",
        (
            "종류가 같은 그룹 중 대표 3개의 전체 제안값 signature가 서로 모두 다른 비율; 사용자 의도에 "
            "직접 대응하는 메인 품질 지표"
        ),
    ),
    (
        "동일 exact slot 값 차이 (보조)",
        (
            "Parameter뿐 아니라 모든 모델 좌표까지 같은 cell만 비교한 값 차이; 좌표 구성이 다른 정상 제안을 "
            "제외하므로 메인보다 분모가 작아 보조 지표로 사용"
        ),
    ),
    ("Value cell", "성공 Proposal에 포함된 값 cell 총수"),
    ("Identity / integrity 오류", "Scenario·Group·DB identity 오류 / 실행 및 저장 원자성 오류"),
    ("실패 시 Proposal 저장", "PASS가 아닌 시도에서 Proposal row가 생긴 수; 0이어야 함"),
    ("LLM retry / tokens", "모든 관측된 단계의 내부 재시도 수 / token 총합"),
    ("성공 지연 p50 / p95", "성공한 Scenario end-to-end 지연의 중앙값 / 95백분위"),
    ("전체 시도 지연 p50 / p95", "ABSTAINED와 실패를 포함한 실행 시도의 중앙값 / 95백분위"),
)
POST_FIX_COMPARISON_COLUMN_DEFINITIONS = (
    ("지표", "동일한 eligible Scenario 시도 집합에서 비교하는 결과 지표"),
    ("기존", "개선 전 baseline 실행 증적에서 관측된 값"),
    ("개선 후", "명시적 post-fix 실행으로 교체된 최종 증적에서 관측된 값"),
    ("증감", "개선 후 값에서 기존 값을 뺀 차이; 비율은 퍼센트포인트(%p)"),
)
DIAGNOSTIC_EXECUTION_COLUMN_DEFINITIONS = (
    ("증적", "최종 KPI 병합에서 제외하고 감사용으로 보존한 실행 파일"),
    ("정책", "해당 프로세스가 실제로 로드한 active-case MI Base fallback mode"),
    ("상태 / 시도", "campaign 종료 상태 / Scenario 실행 시도 수"),
    ("결과", "시도 status별 건수"),
    ("저장", "진단 실행 중 Proposal이 저장된 시도 수; 0이어야 함"),
    ("제외 사유", "최종 품질 KPI의 입력으로 사용하지 않은 이유"),
)


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        message = f"Expected a JSON object: {path}"
        raise TypeError(message)
    return value


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value.rstrip() + "\n", encoding="utf-8")


def _write_new_outputs(
    *,
    output_json: Path,
    output_markdown: Path,
    payload: Mapping[str, Any],
    markdown: str,
) -> None:
    resolved_json = output_json.resolve()
    resolved_markdown = output_markdown.resolve()
    existing = [str(path) for path in (resolved_json, resolved_markdown) if path.exists()]
    if existing:
        message = f"Refusing to overwrite final-cohort report output: {existing}"
        raise FileExistsError(message)
    resolved_json.parent.mkdir(parents=True, exist_ok=True)
    resolved_markdown.parent.mkdir(parents=True, exist_ok=True)
    resolved_json.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    resolved_markdown.write_text(markdown.rstrip() + "\n", encoding="utf-8")


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _group_from(payload: Mapping[str, Any]) -> dict[str, Any]:
    direct = payload.get("scenarioGroup")
    if isinstance(direct, dict):
        return direct
    data = payload.get("data")
    nested = data.get("scenarioGroup") if isinstance(data, Mapping) else None
    if isinstance(nested, dict):
        return nested
    message = "Scenario Group payload is missing scenarioGroup"
    raise ValueError(message)


def _rows_from(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    direct = payload.get("table")
    table = direct if isinstance(direct, Mapping) else None
    if table is None:
        data = payload.get("data")
        nested = data.get("table") if isinstance(data, Mapping) else None
        table = nested if isinstance(nested, Mapping) else None
    rows = table.get("rows") if isinstance(table, Mapping) else None
    if not isinstance(rows, list):
        message = "Scenario Group payload is missing table.rows[]"
        raise TypeError(message)
    return [dict(row) for row in rows if isinstance(row, Mapping)]


def _case_artifact_dir(summary_path: Path, case: Mapping[str, Any]) -> Path:
    raw = str(case.get("artifact_dir") or "").strip()
    if not raw:
        message = f"Campaign case has no artifact_dir: {case}"
        raise ValueError(message)
    path = Path(raw)
    return path if path.is_absolute() else (summary_path.parent / path).resolve()


def load_campaign_groups(summary_path: Path) -> list[dict[str, Any]]:
    summary = _read_json(summary_path)
    groups: list[dict[str, Any]] = []
    for fallback_order, case in enumerate(summary.get("cases") or [], start=1):
        if not isinstance(case, Mapping) or case.get("result") != "completed":
            continue
        artifact_dir = _case_artifact_dir(summary_path, case)
        final_path = artifact_dir / "final_group.json"
        payload = _read_json(final_path)
        group = _group_from(payload)
        rows = _rows_from(payload)
        groups.append(
            {
                "cohort_order": int(case.get("cohort_order") or fallback_order),
                "event_type_id": int(case["event_type_id"]),
                "event_type_code": str(case["event_type_code"]),
                "event_id": int(case["event_id"]),
                "event_title": str(case.get("event_title") or ""),
                "scenario_group_id": int(group["scenarioGroupId"]),
                "group": group,
                "rows": rows,
                "artifact_dir": str(artifact_dir),
            },
        )
    return sorted(groups, key=lambda item: (item["cohort_order"], item["event_id"]))


def _parameter_set(preflight: Mapping[str, Any]) -> frozenset[str]:
    return frozenset(str(item) for item in preflight.get("runtime_parameter_names") or [] if str(item).strip())


def _runtime_capable(preflight: Mapping[str, Any]) -> bool:
    return preflight.get("status") == "PASS" and bool(_parameter_set(preflight))


def _current_write_eligible(preflight: Mapping[str, Any]) -> bool:
    return _runtime_capable(preflight) and (preflight.get("uncovered_guard") or {}).get("eligible") is True


def _jaccard(left: frozenset[str], right: frozenset[str]) -> float:
    union = left | right
    return 1.0 if not union else len(left & right) / len(union)


def _row_id(row: Mapping[str, Any]) -> int:
    return int(row.get("scenarioId") or row.get("scenario_id"))


def _baseline(row: Mapping[str, Any]) -> bool:
    return str(row.get("baselineYn") or row.get("baseline_yn") or "N").upper() == "Y"


def _role(row: Mapping[str, Any]) -> str:
    return str(row.get("scenarioRole") or row.get("scenario_role") or "").strip().lower()


def _pressure_rank(row: Mapping[str, Any]) -> int:
    band = str(row.get("pressureBand") or row.get("pressure_band") or "").strip().lower()
    return PRESSURE_RANK.get(band, 0)


def _combo_score(
    combo: Sequence[Mapping[str, Any]],
    preflight_by_id: Mapping[int, Mapping[str, Any]],
) -> tuple[Any, ...]:
    parameter_sets = [_parameter_set(preflight_by_id[_row_id(row)]) for row in combo]
    pairwise = [_jaccard(parameter_sets[left], parameter_sets[right]) for left, right in combinations(range(3), 2)]
    common = set.intersection(*(set(value) for value in parameter_sets)) if parameter_sets else set()
    identical = len(set(parameter_sets)) == 1
    roles = {_role(row) for row in combo if _role(row)}
    pressure = [_pressure_rank(row) for row in combo]
    cell_signatures = {
        json.dumps(row.get("cells") or {}, ensure_ascii=False, sort_keys=True, default=str) for row in combo
    }
    return (
        int(identical),
        round(min(pairwise), 12),
        len(common),
        round(statistics.fmean(pairwise), 12),
        max(pressure) - min(pressure),
        len(roles),
        len(cell_signatures),
        tuple(-_row_id(row) for row in sorted(combo, key=_row_id)),
    )


def select_representative_trio(
    rows: Sequence[Mapping[str, Any]],
    preflight_by_id: Mapping[int, Mapping[str, Any]],
    *,
    require_uncovered: bool = True,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    runtime_capable = [
        dict(row)
        for row in rows
        if (preflight := preflight_by_id.get(_row_id(row))) is not None and _runtime_capable(preflight)
    ]
    current_write_eligible = [
        row
        for row in runtime_capable
        if _current_write_eligible(preflight_by_id[_row_id(row)])
    ]
    eligible = [
        row
        for row in runtime_capable
        if not require_uncovered or _current_write_eligible(preflight_by_id[_row_id(row)])
    ]
    selectable = [
        dict(row)
        for row in rows
        if (preflight := preflight_by_id.get(_row_id(row))) is not None and preflight.get("status") in {"PASS", "SKIP"}
    ]
    if len(selectable) < 3:
        message = f"Fewer than three structurally selectable Scenarios: {len(selectable)}"
        raise ValueError(message)

    selection_pool = eligible if len(eligible) >= 3 else selectable
    all_combos = list(combinations(selection_pool, 3))
    baseline_ids = {_row_id(row) for row in selection_pool if _baseline(row)}
    floor_ids = {_row_id(row) for row in selection_pool if _role(row) == "floor"}
    ceiling_ids = {_row_id(row) for row in selection_pool if _role(row) == "ceiling"}

    def covers_required_roles(combo: Sequence[Mapping[str, Any]]) -> bool:
        ids = {_row_id(row) for row in combo}
        return (
            (not baseline_ids or bool(ids & baseline_ids))
            and (not floor_ids or bool(ids & floor_ids))
            and (not ceiling_ids or bool(ids & ceiling_ids))
        )

    representative_combos = [combo for combo in all_combos if covers_required_roles(combo)]
    pool = representative_combos or all_combos
    selected = max(pool, key=lambda combo: _combo_score(combo, preflight_by_id))
    selected_rows = sorted((dict(row) for row in selected), key=lambda row: int(row.get("displayOrder") or 0))
    sets = [_parameter_set(preflight_by_id[_row_id(row)]) for row in selected_rows]
    pairwise = [_jaccard(sets[left], sets[right]) for left, right in combinations(range(3), 2)]
    diagnostics = {
        "eligible_scenario_count": len(eligible),
        "eligible_scenario_ids": sorted(_row_id(row) for row in eligible),
        "runtime_capable_scenario_count": len(runtime_capable),
        "runtime_capable_scenario_ids": sorted(_row_id(row) for row in runtime_capable),
        "current_write_eligible_scenario_count": len(current_write_eligible),
        "current_write_eligible_scenario_ids": sorted(_row_id(row) for row in current_write_eligible),
        "selection_eligibility_policy": (
            "runtime-capable-and-uncovered" if require_uncovered else "runtime-capable-independent-of-history"
        ),
        "selection_mode": "proposal-eligible" if len(eligible) >= 3 else "representative-coverage-limit",
        "coverage_limit": len(eligible) < 3,
        "required_role_filter_applied": bool(representative_combos),
        "available_baseline_ids": sorted(baseline_ids),
        "available_floor_ids": sorted(floor_ids),
        "available_ceiling_ids": sorted(ceiling_ids),
        "parameter_sets_identical_in_preflight": len(eligible) >= 3 and len(set(sets)) == 1,
        "parameter_set_pairwise_jaccard_mean": round(statistics.fmean(pairwise), 4),
        "common_runtime_parameter_names": sorted(set.intersection(*(set(value) for value in sets))),
    }
    return selected_rows, diagnostics


def _group_quality(
    group: Mapping[str, Any],
    rows: Sequence[Mapping[str, Any]],
    *,
    expected_event_id: int,
    expected_event_type_id: int,
) -> dict[str, Any]:
    dimension_definitions = group.get("dimensionDefinitions") or group.get("dimension_definitions") or []
    cell_signatures = [json.dumps(row.get("cells") or {}, sort_keys=True, default=str) for row in rows]
    scenario_ids = [_row_id(row) for row in rows]
    checks = {
        "api_version_v4": group.get("apiVersion") == EXPECTED_API_VERSION,
        "generation_strategy": group.get("generationStrategy") == EXPECTED_GENERATION_STRATEGY,
        "catalog_version": group.get("impactCatalogVersion") == EXPECTED_CATALOG_VERSION,
        "catalog_checksum": group.get("impactCatalogChecksum") == EXPECTED_CATALOG_CHECKSUM,
        "status_created_or_realized": group.get("status") in {"created", "realized"},
        "completed_stage": group.get("stage") == "completed",
        "not_deleted": group.get("delYn") != "Y",
        "single_event_identity": group.get("miEventId") == expected_event_id,
        "event_type_identity": group.get("eventTypeL2Id") == expected_event_type_id,
        "parameter_mapping_ready": group.get("parameterMappingReady") is True,
        "dimension_count_3_to_6": 3 <= len(dimension_definitions) <= 6,
        "scenario_count_at_least_3": len(rows) >= 3,
        "scenario_count_readback_matches": int(group.get("scenarioCount") or 0) == len(rows),
        "scenario_ids_unique": len(scenario_ids) == len(set(scenario_ids)),
        "exactly_one_baseline": sum(_baseline(row) for row in rows) == 1,
        "unique_scenario_cells": len(cell_signatures) == len(set(cell_signatures)),
        "has_floor": any(_role(row) == "floor" for row in rows),
        "has_ceiling": any(_role(row) == "ceiling" for row in rows),
    }
    return {"pass": all(checks.values()), "checks": checks}


def expanded_event_cohort_checks(
    *,
    current_event_ids: Sequence[int],
    baseline_event_ids: Sequence[int],
    summary_event_ids: Sequence[int],
    selection_policy: str,
    creation_policy: str,
) -> dict[str, bool]:
    return {
        "expanded_event_cohort_policy": selection_policy == EXPANDED_EVENT_SELECTION_POLICY,
        "expanded_event_cohort_has_20_unique_events": len(current_event_ids) == len(set(current_event_ids)) == 20,
        "expanded_event_ids_disjoint_from_baseline": not baseline_event_ids
        or set(current_event_ids).isdisjoint(baseline_event_ids),
        "summary_event_ids_match_completed_groups": not summary_event_ids
        or list(current_event_ids) == list(summary_event_ids),
        "add_only_preserves_existing_groups": creation_policy == "add-only-preserve-existing",
    }


def regenerated_event_pool_checks(
    *,
    current_event_ids: Sequence[int],
    source_event_ids: Sequence[int],
    original_group_ids: Sequence[int],
    current_group_ids: Sequence[int],
    selection_policy: str,
    creation_policy: str,
    scenario_summary: Mapping[str, Any],
) -> dict[str, bool]:
    hard_gates = scenario_summary.get("hard_gates")
    hard_gates = hard_gates if isinstance(hard_gates, Mapping) else {}
    return {
        "regenerated_event_pool_policy": selection_policy == REGENERATED_EVENT_POOL_SELECTION_POLICY,
        "regenerated_event_pool_has_40_unique_events": len(current_event_ids)
        == len(set(current_event_ids))
        == 40,
        "source_event_pool_reused_exactly": list(current_event_ids) == list(source_event_ids),
        "new_group_ids_disjoint_from_original": bool(original_group_ids)
        and set(current_group_ids).isdisjoint(original_group_ids),
        "original_groups_preserved": hard_gates.get("original_groups_preserved") is True,
        "scenario_campaign_hard_gates_passed": scenario_summary.get("pass") is True
        and bool(hard_gates)
        and all(value is True for value in hard_gates.values()),
        "add_only_preserves_existing_groups": creation_policy == "add-only-preserve-existing",
    }


def build_selection_plan(
    *,
    scenario_summary_path: Path,
    preflight_path: Path,
    baseline_summary_path: Path | None = None,
) -> dict[str, Any]:
    scenario_summary = _read_json(scenario_summary_path)
    groups = load_campaign_groups(scenario_summary_path)
    preflight = _read_json(preflight_path)
    preflight_by_id = {
        int(item["scenario_id"]): item
        for item in preflight.get("preflight") or []
        if isinstance(item, Mapping) and item.get("scenario_id") is not None
    }
    selected_groups: list[dict[str, Any]] = []
    for item in groups:
        selected_rows, diagnostics = select_representative_trio(item["rows"], preflight_by_id)
        selected_groups.append(
            {
                "cohort_order": item["cohort_order"],
                "event_type_id": item["event_type_id"],
                "event_type_code": item["event_type_code"],
                "event_id": item["event_id"],
                "event_title": item["event_title"],
                "scenario_group_id": item["scenario_group_id"],
                "scenario_count": len(item["rows"]),
                "group_quality": _group_quality(
                    item["group"],
                    item["rows"],
                    expected_event_id=item["event_id"],
                    expected_event_type_id=item["event_type_id"],
                ),
                "selection_diagnostics": diagnostics,
                "selected_scenarios": [
                    {
                        "scenario_id": _row_id(row),
                        "display_order": int(row.get("displayOrder") or 0),
                        "title": str(row.get("title") or ""),
                        "baseline": _baseline(row),
                        "scenario_role": _role(row) or None,
                        "pressure_band": row.get("pressureBand"),
                        "cells": row.get("cells") or {},
                        "preflight_status": preflight_by_id[_row_id(row)].get("status"),
                        "proposal_eligible": (
                            preflight_by_id[_row_id(row)].get("status") == "PASS"
                            and bool(_parameter_set(preflight_by_id[_row_id(row)]))
                            and (preflight_by_id[_row_id(row)].get("uncovered_guard") or {}).get("eligible") is True
                        ),
                        "preflight_skip_reasons": preflight_by_id[_row_id(row)].get("skip_reasons") or [],
                        "runtime_parameter_names": sorted(_parameter_set(preflight_by_id[_row_id(row)])),
                    }
                    for row in selected_rows
                ],
            },
        )

    current_group_ids = [item["scenario_group_id"] for item in selected_groups]
    current_event_ids = [item["event_id"] for item in selected_groups]
    selection_policy = str(scenario_summary.get("selection_policy") or "")
    creation_policy = str(scenario_summary.get("creation_policy") or "")
    baseline_groups = load_campaign_groups(baseline_summary_path) if baseline_summary_path else []
    baseline_group_ids = [item["scenario_group_id"] for item in baseline_groups]
    baseline_event_ids = [item["event_id"] for item in baseline_groups]
    if selection_policy == REGENERATED_EVENT_POOL_SELECTION_POLICY and not baseline_summary_path:
        baseline_group_ids = [int(item) for item in scenario_summary.get("original_group_ids") or []]
        baseline_event_ids = [int(item) for item in scenario_summary.get("source_event_ids") or []]
    summary_event_ids = [
        int(item)
        for item in (
            scenario_summary.get("expanded_event_ids")
            or scenario_summary.get("source_event_ids")
            or []
        )
    ]
    selected_ids = [scenario["scenario_id"] for group in selected_groups for scenario in group["selected_scenarios"]]
    campaign_scenario_ids = {
        _row_id(row)
        for group in groups
        for row in group["rows"]
    }
    preflight_scenario_id_rows = [
        int(item["scenario_id"])
        for item in preflight.get("preflight") or []
        if isinstance(item, Mapping) and item.get("scenario_id") is not None
    ]
    preflight_scenario_ids = set(preflight_scenario_id_rows)
    preflight_manifest = preflight.get("manifest")
    preflight_manifest = preflight_manifest if isinstance(preflight_manifest, Mapping) else {}
    preflight_capability = preflight_manifest.get("capability_contract")
    preflight_capability = preflight_capability if isinstance(preflight_capability, Mapping) else {}
    preflight_resource = preflight_manifest.get("resource")
    preflight_resource = preflight_resource if isinstance(preflight_resource, Mapping) else {}
    preflight_safety = preflight.get("safety")
    preflight_safety = preflight_safety if isinstance(preflight_safety, Mapping) else {}
    preflight_selection = preflight.get("selection")
    preflight_selection = preflight_selection if isinstance(preflight_selection, Mapping) else {}
    preflight_selection_counts = preflight_selection.get("counts")
    preflight_selection_counts = (
        preflight_selection_counts if isinstance(preflight_selection_counts, Mapping) else {}
    )
    summary_counts = scenario_summary.get("counts")
    summary_counts = summary_counts if isinstance(summary_counts, Mapping) else {}
    explicit_retries = [
        item for item in scenario_summary.get("explicit_retries") or [] if isinstance(item, Mapping)
    ]
    incomplete_attempt_group_ids = [
        int(item["superseded_group_id"])
        for item in explicit_retries
        if item.get("superseded_group_id") is not None
        and item.get("superseded_group_id") != item.get("retry_group_id")
    ]
    expected_group_count = int(summary_counts.get("requested_group_count") or len(scenario_summary.get("cases") or []))
    structural_checks = {
        "campaign_completed_expected_groups": len(selected_groups) == expected_group_count > 0,
        "selected_exactly_3_per_group": all(len(item["selected_scenarios"]) == 3 for item in selected_groups),
        "selected_scenarios_unique": len(selected_ids) == len(set(selected_ids)) == len(selected_groups) * 3,
        "all_groups_pass_structural_quality": all(item["group_quality"]["pass"] for item in selected_groups),
        "all_groups_have_three_selectable_scenarios": all(
            len(item["selected_scenarios"]) == 3 for item in selected_groups
        ),
        "new_group_ids_disjoint_from_baseline": not baseline_group_ids
        or set(current_group_ids).isdisjoint(baseline_group_ids),
        "incomplete_attempt_groups_excluded_from_cohort": set(incomplete_attempt_group_ids).isdisjoint(
            current_group_ids,
        ),
        "preflight_read_only_passed": preflight.get("mode") == "read-only"
        and preflight.get("status") == "PASS"
        and not (preflight.get("attempts") or []),
        "preflight_scope_matches_all_generated_scenarios": preflight_scenario_ids
        == campaign_scenario_ids,
        "preflight_scenario_ids_unique": len(preflight_scenario_id_rows)
        == len(preflight_scenario_ids),
        "preflight_count_matches_rows": preflight_selection_counts.get("discovered")
        == len(preflight_scenario_id_rows),
        "preflight_has_no_fail_or_hard_stop": preflight_selection_counts.get("preflight_fail") == 0
        and preflight_selection_counts.get("hard_stop") == 0,
        "preflight_scenario_lever_release_exact": preflight_capability.get("catalog_version")
        == EXPECTED_CATALOG_VERSION,
        "preflight_scenario_lever_checksum_exact": preflight_capability.get("catalog_checksum")
        == EXPECTED_CATALOG_CHECKSUM,
        "preflight_proposal_flow_release_exact": preflight_resource.get("proposal_flow_release")
        == EXPECTED_PROPOSAL_FLOW_RELEASE,
        "preflight_capability_release_exact": preflight_resource.get("proposal_capability_release_id")
        == "extend16-v8",
        "preflight_write_paths_not_invoked": preflight_safety.get("confirmation_invoked") is False
        and preflight_safety.get("callback_invoked") is False,
    }
    if selection_policy == EXPANDED_EVENT_SELECTION_POLICY:
        structural_checks.update(
            expanded_event_cohort_checks(
                current_event_ids=current_event_ids,
                baseline_event_ids=baseline_event_ids,
                summary_event_ids=summary_event_ids,
                selection_policy=selection_policy,
                creation_policy=creation_policy,
            ),
        )
    elif selection_policy == REGENERATED_EVENT_POOL_SELECTION_POLICY:
        structural_checks.update(
            regenerated_event_pool_checks(
                current_event_ids=current_event_ids,
                source_event_ids=summary_event_ids,
                original_group_ids=baseline_group_ids,
                current_group_ids=current_group_ids,
                selection_policy=selection_policy,
                creation_policy=creation_policy,
                scenario_summary=scenario_summary,
            ),
        )
    else:
        structural_checks["supported_selection_policy"] = False

    all_preflight = [item for item in preflight.get("preflight") or [] if isinstance(item, Mapping)]
    runtime_capable_count = sum(_runtime_capable(item) for item in all_preflight)
    current_write_eligible_count = sum(_current_write_eligible(item) for item in all_preflight)
    covered_count = sum(
        _runtime_capable(item)
        and not _current_write_eligible(item)
        and (item.get("uncovered_guard") or {}).get("decision") == "SKIP"
        for item in all_preflight
    )
    coverage_limit_count = sum(not _runtime_capable(item) for item in all_preflight)
    hard_stop_count = sum((item.get("uncovered_guard") or {}).get("hard_stop") is True for item in all_preflight)
    preflight_fail_count = sum(item.get("status") == "FAIL" for item in all_preflight)
    runtime_parameter_names = sorted(
        {
            str(name)
            for item in all_preflight
            for name in item.get("runtime_parameter_names") or []
            if str(name).strip()
        },
    )
    groups_with_three_write_eligible = sum(
        item["selection_diagnostics"]["current_write_eligible_scenario_count"] >= 3
        for item in selected_groups
    )
    return {
        "schema_version": 1,
        "generated_at": _now(),
        "method": (
            "Prefer proposal-eligible v4.1 Scenarios; when fewer than three are eligible, preserve three fixed "
            "representatives and mark non-executable items as coverage limit. Preserve baseline/floor/ceiling "
            "representation when available, then maximize identical runtime Parameter sets, pairwise Jaccard "
            "overlap, and pressure/cell diversity."
        ),
        "scenario_lever_release": EXPECTED_CATALOG_VERSION,
        "proposal_flow_release": EXPECTED_PROPOSAL_FLOW_RELEASE,
        "scenario_campaign_summary": str(scenario_summary_path.resolve()),
        "read_only_preflight_evidence": str(preflight_path.resolve()),
        "read_only_release_contract": {
            "scenario_lever_release": preflight_capability.get("catalog_version"),
            "scenario_lever_catalog_checksum": preflight_capability.get("catalog_checksum"),
            "proposal_flow_release": preflight_resource.get("proposal_flow_release"),
            "proposal_capability_release": preflight_resource.get("proposal_capability_release_id"),
        },
        "baseline_campaign_summary": str(baseline_summary_path.resolve()) if baseline_summary_path else None,
        "baseline_group_ids": baseline_group_ids,
        "new_group_ids": current_group_ids,
        "preserved_incomplete_attempt_group_ids": incomplete_attempt_group_ids,
        "net_added_group_count": len(set(current_group_ids) - set(baseline_group_ids)),
        "selection_policy": selection_policy,
        "creation_policy": creation_policy,
        "baseline_event_ids": baseline_event_ids,
        "cohort_event_ids": current_event_ids,
        "source_event_ids": summary_event_ids,
        "expanded_event_ids": current_event_ids,
        "net_added_event_count": len(set(current_event_ids) - set(baseline_event_ids)),
        "expanded_event_type_count": len({item["event_type_id"] for item in selected_groups}),
        "selected_scenario_ids": selected_ids,
        "counts": {
            "baseline_groups": len(baseline_group_ids),
            "new_groups": len(selected_groups),
            "preserved_incomplete_attempt_groups": len(incomplete_attempt_group_ids),
            "new_scenarios": sum(item["scenario_count"] for item in selected_groups),
            "selected_scenarios": len(selected_ids),
            "selected_proposal_eligible_scenarios": sum(
                scenario["proposal_eligible"] for item in selected_groups for scenario in item["selected_scenarios"]
            ),
            "coverage_limit_groups": sum(item["selection_diagnostics"]["coverage_limit"] for item in selected_groups),
            "groups_with_preflight_identical_parameter_sets": sum(
                item["selection_diagnostics"]["parameter_sets_identical_in_preflight"] for item in selected_groups
            ),
            "read_only_discovered_scenarios": len(all_preflight),
            "read_only_runtime_capable_scenarios": runtime_capable_count,
            "read_only_current_write_eligible_scenarios": current_write_eligible_count,
            "read_only_covered_scenarios": covered_count,
            "read_only_coverage_limit_scenarios": coverage_limit_count,
            "read_only_preflight_fail_scenarios": preflight_fail_count,
            "read_only_hard_stop_scenarios": hard_stop_count,
            "groups_with_three_write_eligible_scenarios": groups_with_three_write_eligible,
            "runtime_parameter_count": len(runtime_parameter_names),
        },
        "runtime_parameter_names": runtime_parameter_names,
        "structural_checks": structural_checks,
        "pass": all(structural_checks.values()),
        "groups": selected_groups,
    }


def _parameter_name(parameter: Mapping[str, Any]) -> str:
    return str(
        parameter.get("canonicalParameterName")
        or parameter.get("canonical_parameter_name")
        or parameter.get("parameterName")
        or parameter.get("parameter_name")
        or "",
    ).strip()


def _proposal_parameters(attempt: Mapping[str, Any]) -> list[dict[str, Any]]:
    row = attempt.get("proposal_db_row")
    persisted = row.get("proposal_parameters") if isinstance(row, Mapping) else None
    if isinstance(persisted, list):
        return [dict(item) for item in persisted if isinstance(item, Mapping)]
    evaluation = attempt.get("evaluation")
    final = evaluation.get("final_response") if isinstance(evaluation, Mapping) else None
    data = final.get("data") if isinstance(final, Mapping) else None
    response = data.get("proposalParameters") if isinstance(data, Mapping) else None
    return [dict(item) for item in response or [] if isinstance(item, Mapping)]


def _proposed_value(cell: Mapping[str, Any]) -> object:
    for key in VALUE_KEYS:
        if key in cell:
            return cell[key]
    return None


def _parameter_value_signatures(parameters: Sequence[Mapping[str, Any]]) -> dict[str, str]:
    signatures: dict[str, str] = {}
    for parameter in parameters:
        name = _parameter_name(parameter)
        if not name:
            continue
        values = [_proposed_value(cell) for cell in parameter.get("values") or [] if isinstance(cell, Mapping)]
        normalized_values = sorted(
            (json.dumps(value, ensure_ascii=False, sort_keys=True, default=str) for value in values),
        )
        signatures[name] = json.dumps(normalized_values, ensure_ascii=False, default=str)
    return signatures


def _exact_slot_values(parameters: Sequence[Mapping[str, Any]]) -> dict[str, object]:
    values: dict[str, object] = {}
    for parameter in parameters:
        name = _parameter_name(parameter)
        if not name:
            continue
        for cell in parameter.get("values") or []:
            if not isinstance(cell, Mapping):
                continue
            coordinates = {key: value for key, value in cell.items() if key not in NON_SLOT_KEYS}
            key = json.dumps(
                {"parameter_name": name, "coordinates": coordinates},
                ensure_ascii=False,
                sort_keys=True,
                default=str,
            )
            values[key] = _proposed_value(cell)
    return values


def _percent(numerator: int, denominator: int) -> float:
    return round(100 * numerator / denominator, 1) if denominator else 0.0


def _group_scenarios(group: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    raw = group.get("scenarios")
    if not isinstance(raw, list):
        raw = group.get("selected_scenarios")
    return [item for item in raw or [] if isinstance(item, Mapping)]


def _slot_rationale_audit(
    parameters: Sequence[Mapping[str, Any]],
) -> tuple[int, int, int, list[dict[str, Any]]]:
    total = 0
    nonempty = 0
    explicit = 0
    incomplete: list[dict[str, Any]] = []
    for parameter in parameters:
        parameter_name = _parameter_name(parameter)
        for cell in parameter.get("values") or []:
            if not isinstance(cell, Mapping):
                continue
            total += 1
            rationale = str(cell.get("rationale") or "").strip()
            if rationale:
                nonempty += 1
            missing_sections = [
                section for section in EXPLICIT_SLOT_RATIONALE_SECTIONS if section not in rationale
            ]
            if rationale and not missing_sections:
                explicit += 1
                continue
            coordinates = {key: value for key, value in cell.items() if key not in NON_SLOT_KEYS}
            incomplete.append(
                {
                    "parameter_name": parameter_name,
                    "coordinates": coordinates,
                    "rationale_nonempty": bool(rationale),
                    "missing_sections": missing_sections,
                },
            )
    return total, nonempty, explicit, incomplete


def build_final_cohort_trio_analysis(
    testset: Mapping[str, Any],
    history: Mapping[str, Any],
    *,
    testset_source: str | None = None,
    testset_sha256: str | None = None,
    history_source: str | None = None,
    history_sha256: str | None = None,
) -> dict[str, Any]:
    """Evaluate final persisted Proposal payloads for a fixed representative-trio cohort."""

    expected_group_by_scenario: dict[int, int] = {}
    expected_scenario_ids: list[int] = []
    fixture_errors: list[str] = []
    groups = [item for item in testset.get("groups") or [] if isinstance(item, Mapping)]
    for group in groups:
        raw_group_id = group.get("scenario_group_id")
        if raw_group_id is None:
            fixture_errors.append("testset group is missing scenario_group_id")
            continue
        group_id = int(raw_group_id)
        scenarios = _group_scenarios(group)
        if len(scenarios) != 3:
            fixture_errors.append(
                f"scenario_group_id={group_id}: expected 3 scenarios, got {len(scenarios)}",
            )
        for scenario in scenarios:
            raw_scenario_id = scenario.get("scenario_id")
            if raw_scenario_id is None:
                fixture_errors.append(f"scenario_group_id={group_id}: missing scenario_id")
                continue
            scenario_id = int(raw_scenario_id)
            if scenario_id in expected_group_by_scenario:
                fixture_errors.append(f"duplicate testset scenario_id={scenario_id}")
            expected_group_by_scenario[scenario_id] = group_id
            expected_scenario_ids.append(scenario_id)

    preflight_by_scenario: dict[int, list[Mapping[str, Any]]] = {}
    history_identity_errors: list[str] = []
    for item in history.get("preflight") or []:
        if not isinstance(item, Mapping):
            continue
        raw_scenario_id = item.get("scenario_id")
        if raw_scenario_id is None:
            history_identity_errors.append("preflight row is missing scenario_id")
            continue
        scenario_id = int(raw_scenario_id)
        preflight_by_scenario.setdefault(scenario_id, []).append(item)
        expected_group_id = expected_group_by_scenario.get(scenario_id)
        if expected_group_id is None:
            history_identity_errors.append(f"out-of-scope scenario_id={scenario_id}")
        elif item.get("scenario_group_id") != expected_group_id:
            history_identity_errors.append(
                f"scenario_id={scenario_id}: group={item.get('scenario_group_id')!r}, "
                f"expected={expected_group_id!r}",
            )

    duplicate_preflight_ids = sorted(
        scenario_id for scenario_id, rows in preflight_by_scenario.items() if len(rows) != 1
    )
    missing_preflight_ids = sorted(set(expected_scenario_ids) - set(preflight_by_scenario))
    out_of_scope_preflight_ids = sorted(set(preflight_by_scenario) - set(expected_scenario_ids))
    multiple_blocking_proposal_ids: dict[int, list[int]] = {}
    payload_missing_scenario_ids: list[int] = []
    empty_value_cell_scenario_ids: list[int] = []
    selected_proposal_rows: dict[int, Mapping[str, Any]] = {}

    for scenario_id, items in preflight_by_scenario.items():
        if len(items) != 1:
            continue
        item = items[0]
        guard = item.get("uncovered_guard")
        guard = guard if isinstance(guard, Mapping) else {}
        blocking_rows = [
            row
            for row in guard.get("history") or []
            if isinstance(row, Mapping)
            and str(row.get("status") or "") in FINAL_COHORT_PROPOSAL_STATUSES
        ]
        blocking_rows.sort(key=lambda row: int(row.get("model_param_proposal_id") or -1))
        if len(blocking_rows) > 1:
            multiple_blocking_proposal_ids[scenario_id] = [
                int(row.get("model_param_proposal_id") or -1) for row in blocking_rows
            ]
        if not blocking_rows:
            continue
        selected = blocking_rows[-1]
        selected_proposal_rows[scenario_id] = selected
        expected_group_id = expected_group_by_scenario.get(scenario_id)
        if selected.get("scenario_id") != scenario_id or selected.get("scenario_group_id") != expected_group_id:
            history_identity_errors.append(
                f"proposal_id={selected.get('model_param_proposal_id')}: Scenario/Group identity mismatch",
            )
        raw_parameters = selected.get("proposal_parameters")
        parameters = [
            parameter for parameter in raw_parameters or [] if isinstance(parameter, Mapping)
        ] if isinstance(raw_parameters, list) else []
        if not parameters:
            payload_missing_scenario_ids.append(scenario_id)
        elif not any(
            isinstance(cell, Mapping)
            for parameter in parameters
            for cell in parameter.get("values") or []
        ):
            empty_value_cell_scenario_ids.append(scenario_id)

    group_results: list[dict[str, Any]] = []
    parameter_frequency: Counter[str] = Counter()
    rationale_total = 0
    rationale_nonempty = 0
    rationale_explicit = 0
    rationale_incomplete_by_scenario: dict[int, list[dict[str, Any]]] = {}
    proposal_success_ids: set[int] = set()
    coverage_limit_ids: set[int] = set()

    for group in groups:
        if group.get("scenario_group_id") is None:
            continue
        group_id = int(group["scenario_group_id"])
        fixture_scenarios = _group_scenarios(group)
        selected_ids = [
            int(item["scenario_id"])
            for item in fixture_scenarios
            if item.get("scenario_id") is not None
        ]
        parameter_sets: list[frozenset[str]] = []
        value_signatures: list[dict[str, str]] = []
        exact_slots: list[dict[str, object]] = []
        scenario_results: list[dict[str, Any]] = []
        payload_complete_count = 0
        for scenario in fixture_scenarios:
            scenario_id = int(scenario["scenario_id"])
            preflight_rows = preflight_by_scenario.get(scenario_id) or []
            preflight = preflight_rows[0] if len(preflight_rows) == 1 else {}
            proposal_row = selected_proposal_rows.get(scenario_id)
            raw_parameters = proposal_row.get("proposal_parameters") if proposal_row else None
            parameters = [
                dict(item) for item in raw_parameters or [] if isinstance(item, Mapping)
            ] if isinstance(raw_parameters, list) else []
            names = frozenset(
                _parameter_name(parameter)
                for parameter in parameters
                if _parameter_name(parameter)
            )
            value_cell_count = sum(
                len([cell for cell in parameter.get("values") or [] if isinstance(cell, Mapping)])
                for parameter in parameters
            )
            if proposal_row is not None:
                proposal_success_ids.add(scenario_id)
            elif preflight.get("status") == "SKIP":
                coverage_limit_ids.add(scenario_id)
            if parameters and value_cell_count:
                payload_complete_count += 1
                parameter_sets.append(names)
                value_signatures.append(_parameter_value_signatures(parameters))
                exact_slots.append(_exact_slot_values(parameters))
                parameter_frequency.update(names)
            slot_total, slot_nonempty, slot_explicit, incomplete = _slot_rationale_audit(parameters)
            rationale_total += slot_total
            rationale_nonempty += slot_nonempty
            rationale_explicit += slot_explicit
            if incomplete:
                rationale_incomplete_by_scenario[scenario_id] = incomplete
            scenario_results.append(
                {
                    **dict(scenario),
                    "status": (
                        "PASS"
                        if proposal_row is not None
                        else "COVERAGE_LIMIT" if preflight.get("status") == "SKIP" else "UNPROPOSED"
                    ),
                    "proposal_id": (
                        proposal_row.get("model_param_proposal_id") if proposal_row else None
                    ),
                    "proposal_status": proposal_row.get("status") if proposal_row else None,
                    "actual_parameter_names": sorted(names),
                    "value_cell_count": value_cell_count,
                    "slot_rationale_nonempty_count": slot_nonempty,
                    "slot_rationale_explicit_count": slot_explicit,
                },
            )

        successful_count = sum(scenario_id in proposal_success_ids for scenario_id in selected_ids)
        triple_success = successful_count == 3
        trio_payload_comparable = triple_success and payload_complete_count == 3
        identical_sets = trio_payload_comparable and len(set(parameter_sets)) == 1
        common_parameters = (
            set.intersection(*(set(item) for item in parameter_sets))
            if trio_payload_comparable and parameter_sets
            else set()
        )
        varied_parameters: list[str] = []
        all_three_distinct_parameters: list[str] = []
        if trio_payload_comparable:
            for name in sorted(common_parameters):
                signatures = {item.get(name) for item in value_signatures}
                if len(signatures) > 1:
                    varied_parameters.append(name)
                if len(signatures) == 3:
                    all_three_distinct_parameters.append(name)
        scenario_value_signatures = [
            json.dumps(item, ensure_ascii=False, sort_keys=True, default=str)
            for item in value_signatures
        ]
        all_three_values_distinct = (
            trio_payload_comparable and len(set(scenario_value_signatures)) == 3
        )
        common_slot_keys = (
            set.intersection(*(set(item) for item in exact_slots))
            if trio_payload_comparable
            else set()
        )
        different_common_slots = [
            key for key in common_slot_keys if len({item[key] for item in exact_slots}) > 1
        ]
        all_three_distinct_slots = [
            key for key in common_slot_keys if len({item[key] for item in exact_slots}) == 3
        ]
        event_type_codes = group.get("event_type_codes")
        event_type_code = (
            ", ".join(str(item) for item in event_type_codes)
            if isinstance(event_type_codes, list)
            else str(group.get("event_type_code") or "")
        )
        event_signature = group.get("event_signature")
        event_ids = (
            [int(item) for item in event_signature]
            if isinstance(event_signature, list)
            else ([int(group["event_id"])] if group.get("event_id") is not None else [])
        )
        group_results.append(
            {
                "cohort_order": group.get("recency_rank") or group.get("cohort_order"),
                "scenario_group_id": group_id,
                "event_ids": event_ids,
                "event_type_code": event_type_code,
                "selected_scenario_ids": selected_ids,
                "successful_count": successful_count,
                "triple_success": triple_success,
                "trio_payload_comparable": trio_payload_comparable,
                "actual_parameter_sets_identical": identical_sets,
                "common_parameter_names": sorted(common_parameters),
                "parameters_with_different_value_signatures": varied_parameters,
                "parameters_with_all_three_value_signatures_distinct": all_three_distinct_parameters,
                "all_three_scenario_value_signatures_distinct": all_three_values_distinct,
                "exact_common_slot_count": len(common_slot_keys),
                "exact_common_slots_with_different_values": len(different_common_slots),
                "exact_common_slots_with_all_three_values_distinct": len(all_three_distinct_slots),
                "ideal_same_types_different_values": identical_sets and all_three_values_distinct,
                "scenarios": scenario_results,
            },
        )

    triple_success_groups = [item for item in group_results if item["triple_success"]]
    comparable_groups = [item for item in triple_success_groups if item["trio_payload_comparable"]]
    identical_type_groups = [
        item for item in comparable_groups if item["actual_parameter_sets_identical"]
    ]
    ideal_groups = [item for item in identical_type_groups if item["ideal_same_types_different_values"]]
    exact_slot_groups = [item for item in comparable_groups if item["exact_common_slot_count"]]
    exact_common_slot_count = sum(item["exact_common_slot_count"] for item in exact_slot_groups)
    exact_different_slot_count = sum(
        item["exact_common_slots_with_different_values"] for item in exact_slot_groups
    )
    exact_all_three_distinct_slot_count = sum(
        item["exact_common_slots_with_all_three_values_distinct"] for item in exact_slot_groups
    )
    selection = history.get("selection")
    selection = selection if isinstance(selection, Mapping) else {}
    selection_counts = selection.get("counts")
    selection_counts = selection_counts if isinstance(selection_counts, Mapping) else {}
    discovered_ids = [int(item) for item in selection.get("discovered_scenario_ids") or []]
    covered_ids = {int(item) for item in selection.get("covered_scenario_ids") or []}
    capability_skip_ids = {
        int(item) for item in selection.get("lifecycle_or_capability_skipped_scenario_ids") or []
    }
    manifest = history.get("manifest")
    manifest = manifest if isinstance(manifest, Mapping) else {}
    capability = manifest.get("capability_contract")
    capability = capability if isinstance(capability, Mapping) else {}
    resource = manifest.get("resource")
    resource = resource if isinstance(resource, Mapping) else {}
    checks = {
        "testset_has_groups": bool(groups),
        "testset_has_exactly_three_scenarios_per_group": not any(
            len(_group_scenarios(group)) != 3 for group in groups
        ),
        "testset_scenario_ids_unique": len(expected_scenario_ids) == len(set(expected_scenario_ids)),
        "history_status_pass": history.get("status") == "PASS",
        "history_preflight_scope_exact": (
            not missing_preflight_ids
            and not out_of_scope_preflight_ids
            and not duplicate_preflight_ids
            and len(preflight_by_scenario) == len(expected_scenario_ids)
        ),
        "selection_discovered_scope_exact": discovered_ids == expected_scenario_ids,
        "history_scenario_group_identity": not history_identity_errors,
        "at_most_one_blocking_proposal_per_scenario": not multiple_blocking_proposal_ids,
        "blocking_proposal_payload_complete": not payload_missing_scenario_ids,
        "blocking_proposal_has_value_cells": not empty_value_cell_scenario_ids,
        "covered_count_matches_proposal_rows": (
            selection_counts.get("covered_skip") == len(proposal_success_ids)
        ),
        "covered_scenario_ids_match_proposal_rows": covered_ids == proposal_success_ids,
        "capability_skip_scenario_ids_match": capability_skip_ids == coverage_limit_ids,
        "scenario_lever_release_v4_1": capability.get("catalog_version") == EXPECTED_CATALOG_VERSION,
        "scenario_lever_checksum": capability.get("catalog_checksum") == EXPECTED_CATALOG_CHECKSUM,
        "proposal_flow_release_v4_1_3": (
            resource.get("proposal_flow_release") == EXPECTED_PROPOSAL_FLOW_RELEASE
        ),
        "fixture_structure_valid": not fixture_errors,
    }
    kpis = {
        "group_count": len(group_results),
        "scenario_count": len(expected_scenario_ids),
        "proposal_success_count": len(proposal_success_ids),
        "proposal_success_rate_percent": _percent(
            len(proposal_success_ids),
            len(expected_scenario_ids),
        ),
        "unproposed_scenario_count": (
            len(expected_scenario_ids) - len(proposal_success_ids) - len(coverage_limit_ids)
        ),
        "coverage_limit_scenario_count": len(coverage_limit_ids),
        "triple_success_group_count": len(triple_success_groups),
        "triple_success_group_rate_percent": _percent(len(triple_success_groups), len(group_results)),
        "trio_payload_comparable_group_count": len(comparable_groups),
        "identical_parameter_type_group_count": len(identical_type_groups),
        "parameter_type_consistency_rate_percent": _percent(
            len(identical_type_groups),
            len(triple_success_groups),
        ),
        "same_types_with_all_three_scenario_values_distinct_group_count": len(ideal_groups),
        "same_types_with_all_three_scenario_values_distinct_rate_percent": _percent(
            len(ideal_groups),
            len(identical_type_groups),
        ),
        "groups_with_exact_common_slots": len(exact_slot_groups),
        "exact_common_slot_count": exact_common_slot_count,
        "exact_common_slots_with_different_values": exact_different_slot_count,
        "exact_common_slots_with_different_values_rate_percent": _percent(
            exact_different_slot_count,
            exact_common_slot_count,
        ),
        "exact_common_slots_with_all_three_values_distinct": (
            exact_all_three_distinct_slot_count
        ),
        "exact_common_slots_with_all_three_values_distinct_rate_percent": _percent(
            exact_all_three_distinct_slot_count,
            exact_common_slot_count,
        ),
        "value_cell_count": rationale_total,
        "slot_rationale_nonempty_count": rationale_nonempty,
        "slot_rationale_nonempty_rate_percent": _percent(rationale_nonempty, rationale_total),
        "slot_rationale_explicit_count": rationale_explicit,
        "slot_rationale_explicit_rate_percent": _percent(rationale_explicit, rationale_total),
    }
    quality_review_reasons: list[str] = []
    if rationale_explicit != rationale_total:
        quality_review_reasons.append(
            "모든 proposed-value slot의 근거가 필수 명시 섹션을 충족하지는 않음",
        )
    if len(ideal_groups) != len(identical_type_groups):
        quality_review_reasons.append(
            "Parameter 종류가 같은 full-trio 중 세 Scenario의 전체 proposed-value signature가 "
            "모두 다른 조건을 충족하지 못한 Group이 있음",
        )
    evidence_pass = all(checks.values())
    verdict = "FAIL" if not evidence_pass else "REVIEW" if quality_review_reasons else "PASS"
    return {
        "schema_version": 1,
        "generated_at": _now(),
        "scope": "final-persisted-proposal/read-only/fixed-representative-trios",
        "testset": {
            "source": testset_source,
            "sha256": testset_sha256,
            "dataset_id": testset.get("dataset_id"),
        },
        "final_history": {
            "source": history_source,
            "sha256": history_sha256,
        },
        "release": {
            "scenario_lever_release": capability.get("catalog_version"),
            "scenario_lever_catalog_checksum": capability.get("catalog_checksum"),
            "proposal_flow_release": resource.get("proposal_flow_release"),
        },
        "kpis": kpis,
        "parameter_frequency": dict(sorted(parameter_frequency.items())),
        "payload_missing_scenario_ids": sorted(payload_missing_scenario_ids),
        "empty_value_cell_scenario_ids": sorted(empty_value_cell_scenario_ids),
        "multiple_blocking_proposal_ids": multiple_blocking_proposal_ids,
        "slot_rationale_incomplete_by_scenario": rationale_incomplete_by_scenario,
        "fixture_errors": fixture_errors,
        "history_identity_errors": history_identity_errors,
        "quality_review_reasons": quality_review_reasons,
        "checks": checks,
        "pass": evidence_pass,
        "verdict": verdict,
        "groups": group_results,
    }


def _qualitative_label(rate: float, *, comparable: bool = True) -> str:
    if not comparable:
        return "판정 불가"
    if rate >= 90:
        return "양호"
    if rate >= 70:
        return "보통"
    return "개선 필요"


def _qualitative_assessment(kpis: Mapping[str, Any]) -> list[dict[str, str]]:
    safety_passed = (
        int(kpis["identity_error_count"]) == 0
        and int(kpis["integrity_error_count"]) == 0
        and int(kpis["persisted_failed_attempt_count"]) == 0
    )
    return [
        {
            "area": "Proposal 성공",
            "assessment": _qualitative_label(float(kpis["proposal_coverage_percent"])),
            "basis": f"전체 고정 Scenario 기준 {kpis['proposal_coverage_percent']}%",
        },
        {
            "area": "Trio 비교 가능성",
            "assessment": _qualitative_label(float(kpis["triple_success_group_rate_percent"])),
            "basis": f"3개 모두 성공 Group {kpis['triple_success_group_rate_percent']}%",
        },
        {
            "area": "Parameter 종류 일관성",
            "assessment": _qualitative_label(
                float(kpis["parameter_type_consistency_rate_percent"]),
                comparable=int(kpis["triple_success_group_count"]) > 0,
            ),
            "basis": f"triple-success 분모 {kpis['parameter_type_consistency_rate_percent']}%",
        },
        {
            "area": "Scenario별 값 변별",
            "assessment": _qualitative_label(
                float(kpis["same_types_with_all_three_scenario_values_distinct_rate_percent"]),
                comparable=int(kpis["identical_parameter_type_group_count"]) > 0,
            ),
            "basis": (
                "type-consistent 분모 "
                f"{kpis['same_types_with_all_three_scenario_values_distinct_rate_percent']}%"
            ),
        },
        {
            "area": "저장·identity 안전성",
            "assessment": "양호" if safety_passed else "개선 필요",
            "basis": (
                f"identity/integrity/실패 저장 = {kpis['identity_error_count']}/"
                f"{kpis['integrity_error_count']}/{kpis['persisted_failed_attempt_count']}"
            ),
        },
    ]


def _percentile(values: Sequence[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return round(ordered[0], 3)
    position = (len(ordered) - 1) * percentile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return round(ordered[lower], 3)
    interpolated = ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)
    return round(interpolated, 3)


def _release_identity(execution: Mapping[str, Any]) -> dict[str, Any]:
    manifest = execution.get("manifest") if isinstance(execution.get("manifest"), Mapping) else {}
    capability = manifest.get("capability_contract") if isinstance(manifest.get("capability_contract"), Mapping) else {}
    resource = manifest.get("resource") if isinstance(manifest.get("resource"), Mapping) else {}
    return {
        "capability_release": manifest.get("capability_release"),
        "catalog_version": capability.get("catalog_version"),
        "catalog_checksum": capability.get("catalog_checksum"),
        "resource_release_id": resource.get("release_id"),
        "workbook_contract_sha256": resource.get("contract_sha256"),
        "proposal_capability_sha256": resource.get("proposal_capability_sha256"),
        "proposal_flow_release": resource.get("proposal_flow_release"),
    }


def merge_execution_evidence(
    sources: Sequence[tuple[str, Mapping[str, Any]]],
    *,
    post_fix_sources: Sequence[tuple[str, Mapping[str, Any]]] = (),
    post_fix_reason: str | None = None,
) -> dict[str, Any]:
    if not sources:
        message = "At least one execution evidence source is required"
        raise ValueError(message)
    if post_fix_sources and not str(post_fix_reason or "").strip():
        message = "Explicit --post-fix-reason is required when post-fix evidence replaces attempts"
        raise ValueError(message)
    all_sources = [*sources, *post_fix_sources]
    release_identities = [_release_identity(execution) for _, execution in all_sources]
    if any(identity != release_identities[0] for identity in release_identities[1:]):
        message = f"Execution evidence release identity mismatch: {release_identities}"
        raise ValueError(message)

    merged_attempts: list[dict[str, Any]] = []
    seen_scenario_ids: dict[int, str] = {}
    source_summaries: list[dict[str, Any]] = []
    for label, execution in sources:
        attempts = [dict(item) for item in execution.get("attempts") or [] if isinstance(item, Mapping)]
        for attempt in attempts:
            scenario_id = int(attempt["scenario_id"])
            if scenario_id in seen_scenario_ids:
                message = (
                    "Execution evidence contains a duplicate Scenario attempt: "
                    f"scenario_id={scenario_id}, first={seen_scenario_ids[scenario_id]}, second={label}"
                )
                raise ValueError(message)
            seen_scenario_ids[scenario_id] = label
            merged_attempts.append(attempt)
        manifest = execution.get("manifest") if isinstance(execution.get("manifest"), Mapping) else {}
        source_summaries.append(
            {
                "source": label,
                "status": execution.get("status"),
                "started_at": execution.get("started_at"),
                "finished_at": execution.get("finished_at"),
                "attempt_count": len(attempts),
                "mi_base_fallback_policy": manifest.get("mi_base_fallback_policy"),
                "phase": "baseline",
            },
        )

    replacements: list[dict[str, Any]] = []
    replacement_ids: set[int] = set()
    baseline_attempts = [dict(attempt) for attempt in merged_attempts]
    index_by_scenario = {
        int(attempt["scenario_id"]): index for index, attempt in enumerate(merged_attempts)
    }
    for label, execution in post_fix_sources:
        attempts = [dict(item) for item in execution.get("attempts") or [] if isinstance(item, Mapping)]
        for replacement in attempts:
            scenario_id = int(replacement["scenario_id"])
            if scenario_id in replacement_ids:
                message = f"Post-fix evidence contains duplicate Scenario attempt: scenario_id={scenario_id}"
                raise ValueError(message)
            replacement_ids.add(scenario_id)
            if scenario_id not in index_by_scenario:
                message = (
                    "Post-fix evidence may replace only an existing baseline attempt: "
                    f"scenario_id={scenario_id}, source={label}"
                )
                raise ValueError(message)
            original_index = index_by_scenario[scenario_id]
            original = merged_attempts[original_index]
            replacements.append(
                {
                    "scenario_id": scenario_id,
                    "reason": str(post_fix_reason),
                    "superseded_source": seen_scenario_ids[scenario_id],
                    "superseded_status": original.get("status"),
                    "superseded_failed_stage": original.get("failed_stage"),
                    "superseded_semantic_empty": original.get("semantic_empty"),
                    "replacement_source": label,
                    "replacement_status": replacement.get("status"),
                },
            )
            merged_attempts[original_index] = replacement
        manifest = execution.get("manifest") if isinstance(execution.get("manifest"), Mapping) else {}
        source_summaries.append(
            {
                "source": label,
                "status": execution.get("status"),
                "started_at": execution.get("started_at"),
                "finished_at": execution.get("finished_at"),
                "attempt_count": len(attempts),
                "mi_base_fallback_policy": manifest.get("mi_base_fallback_policy"),
                "phase": "post-fix",
            },
        )

    attempt_statuses = {str(attempt.get("status") or "") for attempt in merged_attempts}
    if "BLOCKED" in attempt_statuses:
        aggregate_status = "BLOCKED"
    elif "FAIL" in attempt_statuses:
        aggregate_status = "FAIL"
    elif "ABSTAINED" in attempt_statuses:
        aggregate_status = "REVIEW"
    elif attempt_statuses <= {"PASS"}:
        aggregate_status = "PASS"
    else:
        aggregate_status = "+".join(sorted(attempt_statuses))
    merged = dict(all_sources[-1][1])
    merged["status"] = aggregate_status
    merged["attempts"] = merged_attempts
    merged["execution_sources"] = source_summaries
    merged["post_fix_replacements"] = replacements
    merged["post_fix_comparison"] = (
        _build_post_fix_comparison(baseline_attempts, merged_attempts) if replacements else None
    )
    merged["mi_base_trace_backfill_audits"] = [
        {
            "execution_source": label,
            "audit": dict(execution["mi_base_trace_backfill_audit"]),
        }
        for label, execution in all_sources
        if isinstance(execution.get("mi_base_trace_backfill_audit"), Mapping)
    ]
    merged["merge_checks"] = {
        "release_identity_consistent": True,
        "duplicate_scenario_attempt_count": 0,
        "post_fix_replacement_count": len(replacements),
        "post_fix_reason_recorded": not post_fix_sources or bool(str(post_fix_reason or "").strip()),
    }
    return merged


def _identity_errors(attempt: Mapping[str, Any], expected_group_id: int) -> list[str]:
    row = attempt.get("proposal_db_row")
    if not isinstance(row, Mapping):
        return ["missing proposal DB read-back"]
    expected = {
        "scenario_id": int(attempt["scenario_id"]),
        "scenario_group_id": expected_group_id,
        "mi_event_id": None,
        "status": "PROPOSED",
        "callback_status": "SKIPPED",
    }
    return [f"{key}={row.get(key)!r}, expected={value!r}" for key, value in expected.items() if row.get(key) != value]


def _attempt_llm_calls(attempt: Mapping[str, Any]) -> list[dict[str, Any]]:
    evaluation = attempt.get("evaluation")
    if isinstance(evaluation, Mapping) and isinstance(evaluation.get("llm_calls"), list):
        return [dict(call) for call in evaluation["llm_calls"] if isinstance(call, Mapping)]
    failure_trace = attempt.get("failure_trace")
    if isinstance(failure_trace, Mapping) and isinstance(failure_trace.get("llm_calls"), list):
        return [dict(call) for call in failure_trace["llm_calls"] if isinstance(call, Mapping)]
    return []


def _attempt_mi_base_trace(attempt: Mapping[str, Any]) -> dict[str, Any] | None:
    evaluation = attempt.get("evaluation")
    if isinstance(evaluation, Mapping) and isinstance(evaluation.get("trace_mi_base_resource"), Mapping):
        trace = dict(evaluation["trace_mi_base_resource"])
        if trace:
            return trace
    failure_trace = attempt.get("failure_trace")
    if isinstance(failure_trace, Mapping) and isinstance(
        failure_trace.get("trace_mi_base_resource"),
        Mapping,
    ):
        trace = dict(failure_trace["trace_mi_base_resource"])
        if trace:
            return trace
    return None


def _is_authorized_inferred_trace(trace: Mapping[str, Any]) -> bool:
    provenance = trace.get("evidence_provenance")
    return bool(
        isinstance(provenance, Mapping)
        and provenance.get("kind") == AUTHORIZED_INFERRED_BACKFILL
        and provenance.get("directly_observed") is False,
    )


def _evaluate_mi_base_backfill_audit(
    execution: Mapping[str, Any],
    *,
    directly_observed_count: int,
    backfilled_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    backfilled_ids = sorted(int(item["scenario_id"]) for item in backfilled_rows)
    raw_audits = execution.get("mi_base_trace_backfill_audits")
    audit_rows = [item for item in raw_audits or [] if isinstance(item, Mapping)]
    if not audit_rows and isinstance(execution.get("mi_base_trace_backfill_audit"), Mapping):
        audit_rows = [
            {
                "execution_source": "execution",
                "audit": execution["mi_base_trace_backfill_audit"],
            },
        ]
    if not backfilled_rows:
        return {
            "required": False,
            "present": bool(audit_rows),
            "pass": True,
            "checks": {},
            "sources": audit_rows,
        }

    audit = audit_rows[0].get("audit") if len(audit_rows) == 1 else None
    audit = audit if isinstance(audit, Mapping) else {}
    authorization = audit.get("authorization")
    authorization = authorization if isinstance(authorization, Mapping) else {}
    counts = audit.get("counts")
    counts = counts if isinstance(counts, Mapping) else {}
    scenario_ids = audit.get("scenario_ids")
    scenario_ids = scenario_ids if isinstance(scenario_ids, Mapping) else {}
    source_evidence = audit.get("source_evidence")
    source_evidence = source_evidence if isinstance(source_evidence, Mapping) else {}
    preconditions = audit.get("preconditions")
    preconditions = preconditions if isinstance(preconditions, Mapping) else {}
    provenance_rows = [
        item.get("evidence_provenance")
        for item in backfilled_rows
        if isinstance(item.get("evidence_provenance"), Mapping)
    ]
    checks = {
        "exactly_one_audit": len(audit_rows) == 1,
        "audit_status_pass": audit.get("status") == "PASS",
        "method_is_authorized_inferred_backfill": audit.get("method") == AUTHORIZED_INFERRED_BACKFILL,
        "explicit_authorization_recorded": authorization.get("explicit") is True
        and bool(str(authorization.get("note") or "").strip()),
        "all_preconditions_passed": bool(preconditions) and all(value is True for value in preconditions.values()),
        "direct_count_matches": int(counts.get("directly_observed") or -1) == directly_observed_count,
        "backfill_count_matches": int(counts.get("backfilled") or -1) == len(backfilled_rows),
        "backfill_scenario_ids_match": sorted(int(item) for item in scenario_ids.get("backfilled") or [])
        == backfilled_ids,
        "attempt_scope_unchanged": int(counts.get("effective") or -1)
        == int(counts.get("attempts") or -2),
        "original_evidence_preserved": audit.get("original_evidence_overwritten") is False,
        "proposal_not_reexecuted": audit.get("proposal_logic_reexecuted") is False,
        "application_data_not_mutated": audit.get("application_data_mutated") is False,
        "provenance_present_on_every_backfill": len(provenance_rows) == len(backfilled_rows),
        "provenance_source_hash_matches_audit": bool(source_evidence.get("sha256"))
        and all(
            item.get("source_evidence_sha256") == source_evidence.get("sha256")
            for item in provenance_rows
        ),
    }
    return {
        "required": True,
        "present": bool(audit_rows),
        "pass": all(checks.values()),
        "checks": checks,
        "sources": audit_rows,
        "authorization_note": authorization.get("note"),
        "source_evidence_sha256": source_evidence.get("sha256"),
        "backfilled_scenario_ids": backfilled_ids,
        "limitation": audit.get("limitation"),
    }


def _semantic_empty_result(attempt: Mapping[str, Any]) -> dict[str, Any] | None:
    raw = attempt.get("semantic_empty")
    if isinstance(raw, Mapping):
        return {
            "reason_code": str(raw.get("reason_code") or "UNKNOWN"),
            "stage": str(raw.get("stage") or "unknown"),
            "structured": raw.get("structured") is True,
            "observability_complete": raw.get("observability_complete") is True,
        }
    error_text = str(attempt.get("error") or "")
    if "ModelParameterSemanticEmptyError" in error_text:
        return {
            "reason_code": "LEGACY_UNSTRUCTURED",
            "stage": "unknown",
            "structured": False,
            "observability_complete": False,
        }
    return None


def _semantic_trace_complete(attempt: Mapping[str, Any], semantic: Mapping[str, Any]) -> bool:
    failure_trace = attempt.get("failure_trace")
    return bool(
        semantic.get("structured") is True
        and semantic.get("observability_complete") is True
        and isinstance(failure_trace, Mapping)
        and failure_trace.get("observability_complete") is True
        and isinstance(failure_trace.get("semantic_stage_evidence"), Mapping)
        and isinstance(failure_trace.get("step_summary"), Mapping)
        and isinstance(failure_trace.get("llm_calls"), list),
    )


def _attempt_outcome_counts(attempts: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    success_count = 0
    semantic_abstention_count = 0
    other_failure_count = 0
    structured_semantic_abstention_count = 0
    semantic_trace_complete_count = 0
    for attempt in attempts:
        if attempt.get("status") == "PASS":
            success_count += 1
            continue
        semantic = _semantic_empty_result(attempt)
        if semantic is None:
            other_failure_count += 1
            continue
        semantic_abstention_count += 1
        structured_semantic_abstention_count += int(semantic["structured"] is True)
        semantic_trace_complete_count += int(_semantic_trace_complete(attempt, semantic))
    attempt_count = len(attempts)
    return {
        "attempt_count": attempt_count,
        "successful_proposal_count": success_count,
        "success_rate_percent": _percent(success_count, attempt_count),
        "semantic_abstention_count": semantic_abstention_count,
        "other_failure_count": other_failure_count,
        "structured_semantic_abstention_count": structured_semantic_abstention_count,
        "semantic_trace_complete_count": semantic_trace_complete_count,
        "semantic_trace_missing_count": semantic_abstention_count - semantic_trace_complete_count,
    }


def _build_post_fix_comparison(
    baseline_attempts: Sequence[Mapping[str, Any]],
    final_attempts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    baseline_ids = {int(attempt["scenario_id"]) for attempt in baseline_attempts}
    final_ids = {int(attempt["scenario_id"]) for attempt in final_attempts}
    baseline = _attempt_outcome_counts(baseline_attempts)
    final = _attempt_outcome_counts(final_attempts)
    delta = {
        key: round(float(final[key]) - float(baseline[key]), 1)
        for key in (
            "successful_proposal_count",
            "success_rate_percent",
            "semantic_abstention_count",
            "other_failure_count",
            "structured_semantic_abstention_count",
            "semantic_trace_complete_count",
            "semantic_trace_missing_count",
        )
    }
    return {
        "same_attempt_scope": baseline_ids == final_ids,
        "baseline_scenario_ids": sorted(baseline_ids),
        "final_scenario_ids": sorted(final_ids),
        "baseline": baseline,
        "final": final,
        "delta": delta,
    }


def evaluate_execution(plan: Mapping[str, Any], execution: Mapping[str, Any]) -> dict[str, Any]:
    raw_attempts = [
        item
        for item in execution.get("attempts") or []
        if isinstance(item, Mapping) and item.get("scenario_id") is not None
    ]
    attempts = {
        int(item["scenario_id"]): item
        for item in raw_attempts
    }
    all_selected_ids = {
        int(scenario["scenario_id"])
        for group in plan.get("groups") or []
        for scenario in group.get("selected_scenarios") or []
    }
    expected_attempt_ids = {
        int(scenario["scenario_id"])
        for group in plan.get("groups") or []
        for scenario in group.get("selected_scenarios") or []
        if scenario.get("proposal_eligible", True) is True
    }
    expected_skip_ids = all_selected_ids - expected_attempt_ids
    actual_attempt_ids = {int(item["scenario_id"]) for item in raw_attempts}
    duplicate_attempt_count = len(raw_attempts) - len(actual_attempt_ids)
    group_results: list[dict[str, Any]] = []
    parameter_frequency: Counter[str] = Counter()
    total_value_cells = 0
    success_elapsed: list[float] = []
    all_attempt_elapsed: list[float] = []
    total_tokens = 0
    llm_retry_count = 0
    integrity_error_count = 0
    identity_error_count = 0
    persisted_failed_attempt_count = 0
    failure_reason_frequency: Counter[str] = Counter()
    semantic_stage_frequency: Counter[str] = Counter()
    semantic_reason_frequency: Counter[str] = Counter()
    structured_semantic_count = 0
    semantic_trace_complete_count = 0
    routing_review_count = 0
    mi_base_trace_rows: list[dict[str, Any]] = []

    for group in plan.get("groups") or []:
        group_id = int(group["scenario_group_id"])
        selected = group.get("selected_scenarios") or []
        selected_ids = [int(item["scenario_id"]) for item in selected]
        selected_attempts = [attempts.get(scenario_id) for scenario_id in selected_ids]
        successful = [item for item in selected_attempts if item and item.get("status") == "PASS"]
        parameter_sets: list[frozenset[str]] = []
        value_signatures: list[dict[str, str]] = []
        exact_slots: list[dict[str, object]] = []
        scenario_results: list[dict[str, Any]] = []
        for scenario, attempt in zip(selected, selected_attempts, strict=True):
            if attempt is None:
                scenario_results.append(
                    {
                        **scenario,
                        "status": "PREFLIGHT_SKIP" if not scenario.get("proposal_eligible") else "NOT_ATTEMPTED",
                    },
                )
                continue
            all_attempt_elapsed.append(float(attempt.get("elapsed_seconds") or 0))
            parameters = _proposal_parameters(attempt)
            names = frozenset(_parameter_name(item) for item in parameters if _parameter_name(item))
            if attempt.get("status") == "PASS":
                parameter_sets.append(names)
                value_signatures.append(_parameter_value_signatures(parameters))
                exact_slots.append(_exact_slot_values(parameters))
                parameter_frequency.update(names)
                total_value_cells += sum(
                    len(item.get("values") or []) for item in parameters if isinstance(item, Mapping)
                )
                success_elapsed.append(float(attempt.get("elapsed_seconds") or 0))
                errors = _identity_errors(attempt, group_id)
                identity_error_count += len(errors)
            else:
                errors = []
                semantic = _semantic_empty_result(attempt)
                if semantic is not None:
                    failure_reason_frequency["semantic_empty"] += 1
                    semantic_stage_frequency[str(semantic["stage"])] += 1
                    semantic_reason_frequency[str(semantic["reason_code"])] += 1
                    structured_semantic_count += int(semantic["structured"] is True)
                    semantic_trace_complete_count += int(
                        _semantic_trace_complete(attempt, semantic),
                    )
                elif attempt.get("status") == "BLOCKED":
                    failure_reason_frequency["blocked"] += 1
                else:
                    failure_reason_frequency[str(attempt.get("failed_stage") or "other_failure")] += 1
                if attempt.get("proposal_persisted") is True or attempt.get("new_proposal_ids"):
                    persisted_failed_attempt_count += 1
            raw_integrity = [str(item) for item in attempt.get("integrity_errors") or []]
            attempt_integrity = [item for item in raw_integrity if item != AUTOMATIC_RETRY_FORBIDDEN_NOTE]
            execution_policy_notes = [item for item in raw_integrity if item == AUTOMATIC_RETRY_FORBIDDEN_NOTE]
            integrity_error_count += len(attempt_integrity)
            evaluation = attempt.get("evaluation")
            if isinstance(evaluation, Mapping) and evaluation.get("routing_status") == "REVIEW":
                routing_review_count += 1
            llm_calls = _attempt_llm_calls(attempt)
            mi_base_trace = _attempt_mi_base_trace(attempt)
            if mi_base_trace is not None:
                mi_base_trace_rows.append(
                    {
                        "scenario_id": int(attempt["scenario_id"]),
                        **mi_base_trace,
                    },
                )
            for call in llm_calls:
                if not isinstance(call, Mapping):
                    continue
                usage = call.get("usage")
                if isinstance(usage, Mapping):
                    total_tokens += int(usage.get("total_tokens") or 0)
                llm_retry_count += int(call.get("retry_count") or 0)
            scenario_results.append(
                {
                    **scenario,
                    "status": attempt.get("status"),
                    "proposal_id": attempt.get("model_param_proposal_id"),
                    "actual_parameter_names": sorted(names),
                    "value_cell_count": sum(len(item.get("values") or []) for item in parameters),
                    "elapsed_seconds": round(float(attempt.get("elapsed_seconds") or 0), 3),
                    "identity_errors": errors,
                    "integrity_errors": attempt_integrity,
                    "execution_policy_notes": execution_policy_notes,
                    "failed_stage": attempt.get("failed_stage"),
                    "error": attempt.get("error"),
                    "semantic_empty": _semantic_empty_result(attempt),
                    "observability_complete": (
                        (attempt.get("failure_trace") or {}).get("observability_complete") is True
                        if isinstance(attempt.get("failure_trace"), Mapping)
                        else attempt.get("status") == "PASS"
                    ),
                    "llm_call_count": len(llm_calls),
                },
            )

        triple_success = len(successful) == 3
        identical_sets = triple_success and len(set(parameter_sets)) == 1
        pairwise = [
            _jaccard(parameter_sets[left], parameter_sets[right])
            for left, right in combinations(range(len(parameter_sets)), 2)
        ]
        common_parameters = set.intersection(*(set(item) for item in parameter_sets)) if parameter_sets else set()
        varied_parameters: list[str] = []
        all_three_distinct_parameters: list[str] = []
        if triple_success:
            for name in sorted(common_parameters):
                signatures = {item.get(name) for item in value_signatures}
                if len(signatures) > 1:
                    varied_parameters.append(name)
                if len(signatures) == 3:
                    all_three_distinct_parameters.append(name)
        common_slot_keys = set.intersection(*(set(item) for item in exact_slots)) if triple_success else set()
        different_common_slots = [key for key in common_slot_keys if len({item[key] for item in exact_slots}) > 1]
        all_three_distinct_slots = [key for key in common_slot_keys if len({item[key] for item in exact_slots}) == 3]
        scenario_value_signatures = [
            json.dumps(item, ensure_ascii=False, sort_keys=True, default=str) for item in value_signatures
        ]
        all_three_scenario_values_distinct = triple_success and len(set(scenario_value_signatures)) == 3
        group_results.append(
            {
                "cohort_order": group.get("cohort_order"),
                "scenario_group_id": group_id,
                "event_type_id": group["event_type_id"],
                "event_type_code": group["event_type_code"],
                "event_id": group.get("event_id"),
                "event_title": group.get("event_title"),
                "selected_scenario_ids": selected_ids,
                "attempted_count": sum(item is not None for item in selected_attempts),
                "successful_count": len(successful),
                "triple_success": triple_success,
                "actual_parameter_sets_identical": identical_sets,
                "actual_parameter_set_pairwise_jaccard_mean": (
                    round(statistics.fmean(pairwise), 4) if pairwise else None
                ),
                "common_parameter_names": sorted(common_parameters),
                "parameters_with_different_value_signatures": varied_parameters,
                "parameters_with_all_three_value_signatures_distinct": all_three_distinct_parameters,
                "any_parameter_value_variation": bool(varied_parameters),
                "all_common_parameters_value_varied": bool(common_parameters)
                and len(varied_parameters) == len(common_parameters),
                "all_three_scenario_value_signatures_distinct": all_three_scenario_values_distinct,
                "exact_common_slot_count": len(common_slot_keys),
                "exact_common_slots_with_different_values": len(different_common_slots),
                "exact_common_slots_with_all_three_values_distinct": len(all_three_distinct_slots),
                "ideal_same_types_different_values": identical_sets
                and all_three_scenario_values_distinct,
                "scenarios": scenario_results,
            },
        )

    group_count = len(group_results)
    selected_count = sum(len(item["selected_scenario_ids"]) for item in group_results)
    attempted_count = sum(item["attempted_count"] for item in group_results)
    succeeded_count = sum(item["successful_count"] for item in group_results)
    selected_eligible_count = sum(
        scenario.get("proposal_eligible", True) is True
        for group in plan.get("groups") or []
        for scenario in group.get("selected_scenarios") or []
    )
    triple_success_count = sum(item["triple_success"] for item in group_results)
    comparable_groups = [item for item in group_results if item["triple_success"]]
    identical_type_groups = [item for item in comparable_groups if item["actual_parameter_sets_identical"]]
    ideal_groups = [item for item in comparable_groups if item["ideal_same_types_different_values"]]
    any_value_variation_groups = [
        item
        for item in identical_type_groups
        if item["any_parameter_value_variation"]
    ]
    exact_slot_groups = [item for item in comparable_groups if item["exact_common_slot_count"] > 0]
    semantic_empty_count = failure_reason_frequency["semantic_empty"]
    resolved_no_change_count = semantic_reason_frequency["ABSTAINED_NO_CHANGE"]
    actionable_semantic_abstention_count = max(
        semantic_empty_count - resolved_no_change_count,
        0,
    )
    nonsemantic_failure_count = sum(
        item.get("status") in {"FAIL", "BLOCKED"} and _semantic_empty_result(item) is None
        for item in raw_attempts
    )
    missing_semantic_trace_count = semantic_empty_count - semantic_trace_complete_count
    directly_observed_mi_base_rows = [
        item for item in mi_base_trace_rows if not _is_authorized_inferred_trace(item)
    ]
    backfilled_mi_base_rows = [
        item for item in mi_base_trace_rows if _is_authorized_inferred_trace(item)
    ]
    mi_base_identity_signatures = {
        json.dumps(
            {
                "source": item.get("source"),
                "case_id": item.get("case_id"),
                "run_seq": item.get("run_seq"),
                "workbook_sha256": item.get("workbook_sha256"),
            },
            sort_keys=True,
            default=str,
        )
        for item in mi_base_trace_rows
    }
    mi_base_backfill_audit = _evaluate_mi_base_backfill_audit(
        execution,
        directly_observed_count=len(directly_observed_mi_base_rows),
        backfilled_rows=backfilled_mi_base_rows,
    )
    effective_trace_ids = {int(item["scenario_id"]) for item in mi_base_trace_rows}
    mi_base_trace_summary = {
        "attempted_scenario_count": attempted_count,
        "observed_trace_count": len(directly_observed_mi_base_rows),
        "directly_observed_trace_count": len(directly_observed_mi_base_rows),
        "authorized_backfilled_trace_count": len(backfilled_mi_base_rows),
        "effective_trace_count": len(mi_base_trace_rows),
        "backfilled_scenario_ids": sorted(
            int(item["scenario_id"]) for item in backfilled_mi_base_rows
        ),
        "missing_trace_scenario_ids": sorted(
            actual_attempt_ids - effective_trace_ids,
        ),
        "sources": dict(Counter(str(item.get("source") or "missing") for item in mi_base_trace_rows)),
        "identity_count": len(mi_base_identity_signatures),
        "identity_consistent": len(mi_base_identity_signatures) <= 1,
        "backfill_audit": mi_base_backfill_audit,
        "rows": mi_base_trace_rows,
    }
    historical_evidence_backfilled = bool(backfilled_mi_base_rows)
    mi_base_trace_remediation = {
        "required": bool(mi_base_trace_summary["missing_trace_scenario_ids"])
        or historical_evidence_backfilled,
        "historical_evidence_backfilled": historical_evidence_backfilled,
        "proposal_rerun_performed": False,
        "interpretation": (
            (
                "명시적 승인과 fail-closed audit 조건으로 누락 identity를 소급 보정했습니다. 보정분은 "
                "직접 관측이 아닌 추론 증적이며, Proposal 로직이나 DB write는 재실행하지 않았습니다."
            )
            if historical_evidence_backfilled
            else (
                "현재 실행 증적의 누락은 소급 추정하지 않아 fallback completeness gate 실패를 유지하며, "
                "소스 보완은 후속 실행부터 검증 가능"
            )
        ),
    }
    plan_counts = plan.get("counts") if isinstance(plan.get("counts"), Mapping) else {}
    creation_policy = plan.get("creation_policy")
    scenario_summary_path = str(plan.get("scenario_campaign_summary") or "").strip()
    if not creation_policy and scenario_summary_path:
        try:
            creation_policy = _read_json(Path(scenario_summary_path)).get("creation_policy")
        except (OSError, TypeError, ValueError):
            creation_policy = None
    creation_summary = {
        "selection_policy": plan.get("selection_policy"),
        "creation_policy": creation_policy,
        "baseline_group_count": int(plan_counts.get("baseline_groups") or 0),
        "added_group_count": int(plan_counts.get("new_groups") or 0),
        "net_added_group_count": int(plan.get("net_added_group_count") or 0),
        "existing_deleted_group_count": 0 if creation_policy == "add-only-preserve-existing" else None,
        "new_scenario_count": int(plan_counts.get("new_scenarios") or 0),
        "baseline_group_ids": [int(item) for item in plan.get("baseline_group_ids") or []],
        "new_group_ids": [int(item) for item in plan.get("new_group_ids") or []],
        "preserved_incomplete_attempt_group_ids": [
            int(item) for item in plan.get("preserved_incomplete_attempt_group_ids") or []
        ],
        "preserved_incomplete_attempt_group_count": int(
            plan_counts.get("preserved_incomplete_attempt_groups") or 0,
        ),
        "baseline_event_ids": [int(item) for item in plan.get("baseline_event_ids") or []],
        "source_event_ids": [int(item) for item in plan.get("source_event_ids") or []],
        "cohort_event_ids": [int(item) for item in plan.get("cohort_event_ids") or []],
        "expanded_event_ids": [int(item) for item in plan.get("expanded_event_ids") or []],
        "net_added_event_count": int(plan.get("net_added_event_count") or 0),
        "expanded_event_type_count": int(plan.get("expanded_event_type_count") or 0),
    }
    manifest = execution.get("manifest") if isinstance(execution.get("manifest"), Mapping) else {}
    resource = manifest.get("resource") if isinstance(manifest.get("resource"), Mapping) else {}
    capability = manifest.get("capability_contract") if isinstance(manifest.get("capability_contract"), Mapping) else {}
    release_checks = {
        "scenario_lever_version_v4_1": capability.get("catalog_version") == EXPECTED_CATALOG_VERSION,
        "scenario_lever_checksum": capability.get("catalog_checksum") == EXPECTED_CATALOG_CHECKSUM,
        "proposal_flow_release_v4_1_3": resource.get("proposal_flow_release") == EXPECTED_PROPOSAL_FLOW_RELEASE,
        "confirmation_not_invoked": execution.get("safety", {}).get("confirmation_invoked") is False,
        "callback_not_invoked": execution.get("safety", {}).get("callback_invoked") is False,
        "automatic_retry_disabled": execution.get("safety", {}).get("automatic_retry") is False,
    }

    def plan_count(name: str, fallback: int = 0) -> int:
        return int(plan_counts[name]) if name in plan_counts else fallback

    kpis = {
        "requested_group_count": group_count,
        "generated_scenario_count": int(plan_counts.get("new_scenarios") or selected_count),
        "selected_scenario_count": selected_count,
        "proposal_eligible_selected_scenario_count": selected_eligible_count,
        "preflight_coverage_limit_scenario_count": selected_count - selected_eligible_count,
        "read_only_discovered_scenario_count": plan_count(
            "read_only_discovered_scenarios",
            selected_count,
        ),
        "read_only_runtime_capable_scenario_count": plan_count(
            "read_only_runtime_capable_scenarios",
            selected_eligible_count,
        ),
        "read_only_current_write_eligible_scenario_count": plan_count(
            "read_only_current_write_eligible_scenarios",
            selected_eligible_count,
        ),
        "read_only_covered_scenario_count": plan_count("read_only_covered_scenarios"),
        "read_only_coverage_limit_scenario_count": plan_count(
            "read_only_coverage_limit_scenarios",
            max(selected_count - selected_eligible_count, 0),
        ),
        "read_only_preflight_fail_scenario_count": plan_count("read_only_preflight_fail_scenarios"),
        "read_only_hard_stop_scenario_count": plan_count("read_only_hard_stop_scenarios"),
        "groups_with_three_write_eligible_scenarios": plan_count(
            "groups_with_three_write_eligible_scenarios",
            group_count,
        ),
        "coverage_limit_group_count": plan_count("coverage_limit_groups"),
        "runtime_parameter_count": plan_count("runtime_parameter_count"),
        "preflight_identical_parameter_type_group_count": int(
            plan_counts.get("groups_with_preflight_identical_parameter_sets") or 0,
        ),
        "preflight_parameter_type_consistency_rate_percent": _percent(
            int(plan_counts.get("groups_with_preflight_identical_parameter_sets") or 0),
            group_count,
        ),
        "attempted_scenario_count": attempted_count,
        "successful_proposal_count": succeeded_count,
        "failed_or_unattempted_scenario_count": selected_count - succeeded_count,
        "proposal_coverage_percent": _percent(succeeded_count, selected_count),
        "preflight_to_proposal_conversion_percent": _percent(succeeded_count, selected_eligible_count),
        "semantic_empty_failure_count": semantic_empty_count,
        "semantic_abstention_count": semantic_empty_count,
        "resolved_no_change_count": resolved_no_change_count,
        "actionable_semantic_abstention_count": actionable_semantic_abstention_count,
        "semantic_empty_rate_percent": _percent(semantic_empty_count, attempted_count),
        "other_failure_count": nonsemantic_failure_count,
        "structured_semantic_abstention_count": structured_semantic_count,
        "semantic_trace_complete_count": semantic_trace_complete_count,
        "semantic_trace_missing_count": missing_semantic_trace_count,
        "eligible_not_attempted_count": len(expected_attempt_ids - actual_attempt_ids),
        "triple_success_group_count": triple_success_count,
        "triple_success_group_rate_percent": _percent(triple_success_count, group_count),
        "identical_parameter_type_group_count": len(identical_type_groups),
        "parameter_type_consistency_rate_percent": _percent(len(identical_type_groups), len(comparable_groups)),
        "same_types_with_any_different_values_group_count": len(any_value_variation_groups),
        "same_types_with_any_different_values_rate_percent": _percent(
            len(any_value_variation_groups),
            len(identical_type_groups),
        ),
        "same_types_with_all_three_scenario_values_distinct_group_count": len(ideal_groups),
        "same_types_with_all_three_scenario_values_distinct_rate_percent": _percent(
            len(ideal_groups),
            len(identical_type_groups),
        ),
        "groups_with_exact_common_slots": len(exact_slot_groups),
        "groups_with_different_values_on_exact_common_slots": sum(
            item["exact_common_slots_with_different_values"] > 0 for item in exact_slot_groups
        ),
        "value_cell_count": total_value_cells,
        "identity_error_count": identity_error_count,
        "integrity_error_count": integrity_error_count,
        "persisted_failed_attempt_count": persisted_failed_attempt_count,
        "llm_retry_count": llm_retry_count,
        "total_tokens": total_tokens,
        "latency_seconds_p50": _percentile(success_elapsed, 0.50),
        "latency_seconds_p95": _percentile(success_elapsed, 0.95),
        "success_latency_seconds_p50": _percentile(success_elapsed, 0.50),
        "success_latency_seconds_p95": _percentile(success_elapsed, 0.95),
        "all_attempt_latency_seconds_p50": _percentile(all_attempt_elapsed, 0.50),
        "all_attempt_latency_seconds_p95": _percentile(all_attempt_elapsed, 0.95),
    }
    operational_checks = {
        "plan_passed": plan.get("pass") is True,
        "group_count_matches_plan": group_count == len(plan.get("groups") or []) > 0,
        "exactly_three_selected_per_group": selected_count == group_count * 3,
        "selected_scenario_ids_unique": len(all_selected_ids) == selected_count,
        "attempt_scope_matches_eligible_scenarios": actual_attempt_ids == expected_attempt_ids,
        "no_attempt_for_preflight_skip": not (actual_attempt_ids & expected_skip_ids),
        "no_duplicate_scenario_attempt": duplicate_attempt_count == 0,
        "no_blocked_attempt": not any(
            scenario.get("status") == "BLOCKED" for group in group_results for scenario in group["scenarios"]
        ),
        "no_nonsemantic_execution_failure": nonsemantic_failure_count == 0,
        "identity_integrity": identity_error_count == 0 and integrity_error_count == 0,
        "failed_attempt_atomicity": persisted_failed_attempt_count == 0,
        "execution_release_identity_consistent": execution.get("merge_checks", {}).get(
            "release_identity_consistent",
            True,
        )
        is True,
        **release_checks,
    }
    if historical_evidence_backfilled:
        operational_checks["mi_base_trace_backfill_audit_valid"] = (
            mi_base_backfill_audit.get("pass") is True
        )
    post_fix_comparison = execution.get("post_fix_comparison")
    if isinstance(post_fix_comparison, Mapping):
        operational_checks["post_fix_attempt_scope_unchanged"] = (
            post_fix_comparison.get("same_attempt_scope") is True
        )
    if creation_summary["baseline_group_count"] or creation_summary["added_group_count"]:
        operational_checks.update(
            {
                "original_groups_preserved": creation_summary["baseline_group_count"] > 0
                and creation_summary["existing_deleted_group_count"] == 0,
                "requested_groups_added": creation_summary["added_group_count"] == group_count
                and creation_summary["net_added_group_count"] == group_count,
                "baseline_and_added_group_ids_disjoint": not (
                    set(creation_summary["baseline_group_ids"]) & set(creation_summary["new_group_ids"])
                ),
                "incomplete_attempt_groups_excluded_from_evaluation": not (
                    set(creation_summary["preserved_incomplete_attempt_group_ids"])
                    & set(creation_summary["new_group_ids"])
                ),
            },
        )
        if creation_summary["selection_policy"] == EXPANDED_EVENT_SELECTION_POLICY:
            operational_checks.update(
                {
                    "expanded_event_cohort_20_unique": len(creation_summary["cohort_event_ids"])
                    == len(set(creation_summary["cohort_event_ids"]))
                    == 20,
                    "expanded_event_cohort_disjoint_from_baseline": not (
                        set(creation_summary["baseline_event_ids"])
                        & set(creation_summary["cohort_event_ids"])
                    ),
                },
            )
        elif creation_summary["selection_policy"] == REGENERATED_EVENT_POOL_SELECTION_POLICY:
            operational_checks.update(
                {
                    "regenerated_event_pool_40_unique": len(creation_summary["cohort_event_ids"])
                    == len(set(creation_summary["cohort_event_ids"]))
                    == 40,
                    "source_event_pool_reused_exactly": creation_summary["cohort_event_ids"]
                    == creation_summary["source_event_ids"],
                    "no_event_cohort_expansion": creation_summary["net_added_event_count"] == 0,
                },
            )
    operational_pass = all(operational_checks.values())
    review_reasons: list[str] = []
    if semantic_empty_count:
        review_reasons.append(
            f"semantic abstention {semantic_empty_count}건은 제안 품질 검토 대상입니다.",
        )
    if missing_semantic_trace_count:
        review_reasons.append(
            f"semantic abstention trace가 불완전한 Scenario가 {missing_semantic_trace_count}건입니다.",
        )
    if llm_retry_count:
        review_reasons.append(f"내부 LLM retry가 {llm_retry_count}회 관측됐습니다.")
    if routing_review_count:
        review_reasons.append(f"routing 선택 REVIEW가 {routing_review_count}건입니다.")
    if mi_base_trace_summary["missing_trace_scenario_ids"]:
        review_reasons.append(
            "MI Base path-free trace가 누락된 Scenario가 "
            f"{len(mi_base_trace_summary['missing_trace_scenario_ids'])}건입니다.",
        )
    if not mi_base_trace_summary["identity_consistent"]:
        review_reasons.append("실행 attempt 사이 MI Base case/run/workbook identity가 일치하지 않습니다.")
    if historical_evidence_backfilled:
        review_reasons.append(
            "MI Base trace "
            f"{len(backfilled_mi_base_rows)}건은 직접 관측이 아닌 명시적 승인 기반 소급 보정입니다.",
        )
    verdict = "FAIL" if not operational_pass else "REVIEW" if review_reasons else "PASS"
    return {
        "schema_version": 2,
        "generated_at": _now(),
        "scenario_lever_release": EXPECTED_CATALOG_VERSION,
        "proposal_flow_release": resource.get("proposal_flow_release"),
        "read_only_release_contract": plan.get("read_only_release_contract") or {},
        "execution_status": execution.get("status"),
        "execution_sources": execution.get("execution_sources") or [],
        "post_fix_replacements": execution.get("post_fix_replacements") or [],
        "post_fix_comparison": execution.get("post_fix_comparison"),
        "mi_base_fallback_policy": manifest.get("mi_base_fallback_policy"),
        "mi_base_trace_summary": mi_base_trace_summary,
        "mi_base_trace_remediation": mi_base_trace_remediation,
        "scenario_group_creation": creation_summary,
        "read_only_scope": {
            "phase": "preflight-before-proposal",
            "definition": (
                "Scenario/Proposal history와 release/runtime candidate/write guard를 조회해 실행 가능성만 판정한 단계"
            ),
            "database_reads": True,
            "proposal_logic_executed": False,
            "llm_invoked": False,
            "proposal_persisted": False,
            "confirmation_or_callback_invoked": False,
            "object_storage_or_active_mi_base_validated": False,
        },
        "read_only_kpi_interpretation": {
            "pass_meaning": "release·scope·구조·preflight 계약 통과이며 실제 Proposal 성공이나 값 품질 통과가 아님",
            "runtime_capable": "현재 release의 runtime allowlist 안에 실행 후보 Parameter가 1개 이상 있음",
            "current_write_eligible": "runtime-capable이고 lifecycle/catalog/write guard를 통과해 지금 쓸 수 있음",
            "covered": "기존 Proposal 때문에 중복 쓰기가 차단됨; 이번 실행 성공으로 집계하지 않음",
            "coverage_limit": "runtime 후보가 없어 LLM/쓰기를 시도하지 않음; 실행 오류로 집계하지 않음",
        },
        "methodology": [
            {
                "step": 1,
                "name": (
                    "기존 Event 풀 기반 add-only 재생성"
                    if plan.get("selection_policy") == REGENERATED_EVENT_POOL_SELECTION_POLICY
                    else "확장 Event cohort add-only 생성"
                ),
                "method": (
                    "기존 고정 Event 40개를 그대로 재사용하고 기존 Scenario Group을 모두 보존한 채 Event별 "
                    "v4 Group 하나를 새로 생성한다."
                    if plan.get("selection_policy") == REGENERATED_EVENT_POOL_SELECTION_POLICY
                    else "baseline과 겹치지 않는 Event 20개를 먼저 고정하고 기존 Scenario Group을 모두 "
                    "보존한 채 Event별 v4 Group 하나를 추가한다."
                ),
            },
            {
                "step": 2,
                "name": "구조 품질 gate",
                "method": (
                    "v4 strategy/catalog pin, 완료 stage, Dimension, baseline/floor/ceiling, cell 고유성을 검증한다."
                ),
            },
            {
                "step": 3,
                "name": "read-only Proposal preflight",
                "method": (
                    f"대표 선정이나 쓰기 전에 신규 Scenario {int(plan_counts.get('new_scenarios') or 0)}개 전체를 "
                    "검사한다."
                ),
            },
            {
                "step": 4,
                "name": "대표 Scenario 3개 선정",
                "method": (
                    "v4.1 Proposal 가능성을 우선하고 baseline/floor/ceiling 대표성을 보존한 뒤 Parameter 종류 "
                    "동일성, pairwise Jaccard, pressure/cell 다양성 순으로 3개를 고정한다."
                ),
            },
            {
                "step": 5,
                "name": "경계가 고정된 Proposal 실행",
                "method": (
                    "eligible uncovered Scenario를 정확히 한 번씩 실행하고 confirmation/callback과 자동 외부 "
                    "재시도는 호출하지 않는다."
                ),
            },
            {
                "step": 6,
                "name": "KPI 및 DB 대조",
                "method": (
                    "coverage, semantic-empty, 종류/값/exact-slot 지표를 분리하고 최종 Proposal history와 대조한다."
                ),
            },
        ],
        "kpis": kpis,
        "qualitative_assessment": _qualitative_assessment(kpis),
        "failure_reason_counts": [
            {"reason": reason, "count": count} for reason, count in sorted(failure_reason_frequency.items())
        ],
        "semantic_abstention_by_stage": [
            {"stage": stage, "count": count} for stage, count in sorted(semantic_stage_frequency.items())
        ],
        "semantic_abstention_by_reason_code": [
            {"reason_code": reason, "count": count}
            for reason, count in sorted(semantic_reason_frequency.items())
        ],
        "parameter_frequency_by_successful_scenario": [
            {"parameter_name": name, "scenario_count": count} for name, count in sorted(parameter_frequency.items())
        ],
        "operational_checks": operational_checks,
        "operational_pass": operational_pass,
        "verdict": verdict,
        "review_reasons": review_reasons,
        "attempt_scope": {
            "expected_attempt_scenario_ids": sorted(expected_attempt_ids),
            "actual_attempt_scenario_ids": sorted(actual_attempt_ids),
            "expected_skip_scenario_ids": sorted(expected_skip_ids),
            "missing_attempt_scenario_ids": sorted(expected_attempt_ids - actual_attempt_ids),
            "unexpected_attempt_scenario_ids": sorted(actual_attempt_ids - expected_attempt_ids),
            "duplicate_attempt_count": duplicate_attempt_count,
        },
        "quality_interpretation": {
            "parameter_type_consistency_denominator": "groups with three successful proposals",
            "value_variation_denominator": "groups with three successes and identical Parameter type sets",
            "main_value_differentiation_note": (
                "All three Scenario-level Proposal value signatures must be distinct after each Parameter's "
                "proposed values are normalized as an order-independent multiset."
            ),
            "exact_slot_variation_note": (
                "The stricter metric compares proposedValue only where Parameter name and every model slot "
                "coordinate are identical across all three Scenarios."
            ),
            "proposal_failures_are_quality_outcomes": True,
            "configured_fallback_note": (
                "Configured Basecase fallback is reported separately from active MI Base and verified-cache execution."
            ),
        },
        "existing_kpi_improvement_ideas": [
            {
                "target": "Proposal 성공률 / Preflight→Proposal 전환율",
                "idea": (
                    "Semantic abstention의 stage·reason_code를 우선순위화해 반복 원인의 Event 근거 추출과 "
                    "slot 정규화를 보강한다. 동일 실패를 숨기는 자동 외부 재시도는 사용하지 않는다."
                ),
            },
            {
                "target": "그룹 내 3개 모두 성공",
                "idea": (
                    "Group별 가장 약한 1개 Scenario의 실패 원인을 먼저 보완하고 고정 테스트셋에서 명시적 "
                    "재검증해 비교 가능 Group 수를 높인다."
                ),
            },
            {
                "target": "파라미터 종류 동일",
                "idea": (
                    "같은 Group의 공통 Lever·hydrated binding을 동일 canonical routing 입력으로 유지하고, "
                    "Scenario별 근거는 값 산정 단계에서 분기한다."
                ),
            },
            {
                "target": "같은 종류 + Scenario별 다른 제안값",
                "idea": (
                    "Scenario별 방향·강도·기간·대상 근거를 값 산정 prompt에 명시해 일률적인 기본값 수렴을 "
                    "줄이되, 근거 없는 차별화는 만들지 않는다."
                ),
            },
            {
                "target": "동일 exact slot 값 차이 (보조)",
                "idea": (
                    "업무적으로 같은 좌표를 비교할 수 있는 경우 coordinate 선택을 안정화하되, 관련 없는 "
                    "좌표를 억지로 맞춰 메인 지표를 왜곡하지 않는다."
                ),
            },
        ],
        "groups": group_results,
    }


def build_reusable_testset(
    plan: Mapping[str, Any],
    report: Mapping[str, Any],
) -> dict[str, Any]:
    groups = [
        {
            "cohort_order": group.get("cohort_order"),
            "scenario_group_id": group["scenario_group_id"],
            "event_type_id": group["event_type_id"],
            "event_type_code": group["event_type_code"],
            "event_id": group["event_id"],
            "event_title": group.get("event_title"),
            "selection_diagnostics": group.get("selection_diagnostics") or {},
            "scenarios": group.get("selected_scenarios") or [],
        }
        for group in plan.get("groups") or []
    ]
    baseline_groups = [
        {
            "scenario_group_id": group["scenario_group_id"],
            "successful_count": group["successful_count"],
            "actual_parameter_sets_identical": group["actual_parameter_sets_identical"],
            "any_parameter_value_variation": group["any_parameter_value_variation"],
            "all_three_scenario_value_signatures_distinct": group.get(
                "all_three_scenario_value_signatures_distinct",
                False,
            ),
            "exact_common_slot_count": group["exact_common_slot_count"],
            "exact_common_slots_with_different_values": group["exact_common_slots_with_different_values"],
            "scenarios": [
                {
                    "scenario_id": scenario["scenario_id"],
                    "status": scenario["status"],
                    "actual_parameter_names": scenario.get("actual_parameter_names") or [],
                    "value_cell_count": scenario.get("value_cell_count", 0),
                    "failed_stage": scenario.get("failed_stage"),
                }
                for scenario in group.get("scenarios") or []
            ],
        }
        for group in report.get("groups") or []
    ]
    selection_policy = str(plan.get("selection_policy") or "")
    group_count = len(groups)
    if selection_policy == EXPANDED_EVENT_SELECTION_POLICY:
        dataset_id = "model-parameter-v4.1.2-expanded-event-cohort-20-groups-20261007"
        purpose = "Reusable expanded Event cohort for Scenario Lever and Proposal Flow regression evaluation"
        cohort_identity = {
            "selection_policy": selection_policy,
            "baseline_event_ids": [int(item) for item in plan.get("baseline_event_ids") or []],
            "expanded_event_ids": [int(item) for item in plan.get("expanded_event_ids") or []],
            "event_sets_disjoint": not (
                set(plan.get("baseline_event_ids") or []) & set(plan.get("expanded_event_ids") or [])
            ),
        }
    else:
        dataset_id = (
            f"model-parameter-v4.1.2-existing-event-pool-regenerated-{group_count}-groups-20261007"
        )
        purpose = (
            "Reusable representative-trio cohort regenerated add-only from the fixed existing Event pool"
        )
        source_event_ids = [int(item) for item in plan.get("source_event_ids") or []]
        cohort_event_ids = [int(item) for item in plan.get("cohort_event_ids") or []]
        cohort_identity = {
            "selection_policy": selection_policy,
            "source_event_ids": source_event_ids,
            "cohort_event_ids": cohort_event_ids,
            "event_pool_reused_exactly": source_event_ids == cohort_event_ids,
            "original_group_ids": [int(item) for item in plan.get("baseline_group_ids") or []],
            "regenerated_group_ids": [int(item) for item in plan.get("new_group_ids") or []],
            "preserved_incomplete_attempt_group_ids": [
                int(item) for item in plan.get("preserved_incomplete_attempt_group_ids") or []
            ],
        }
    return {
        "schema_version": 1,
        "dataset_id": dataset_id,
        "created_at": plan.get("generated_at"),
        "purpose": purpose,
        "contract": {
            "api_version": EXPECTED_API_VERSION,
            "generation_strategy": EXPECTED_GENERATION_STRATEGY,
            "scenario_lever_release": EXPECTED_CATALOG_VERSION,
            "scenario_lever_catalog_checksum": EXPECTED_CATALOG_CHECKSUM,
            "proposal_flow_release": FIXED_TESTSET_SOURCE_FLOW_RELEASE,
            "selection_policy": plan.get("selection_policy"),
            "group_count": len(groups),
            "representative_scenarios_per_group": 3,
            "scenario_count": sum(len(group["scenarios"]) for group in groups),
        },
        "cohort_identity": cohort_identity,
        "selection_method": plan.get("method") or {},
        "groups": groups,
        "scenario_group_creation": report.get("scenario_group_creation") or {},
        "observed_baseline": {
            "baseline_is_observational": True,
            "available": bool(baseline_groups),
            "note": (
                "Outcome fields are comparison baselines, not immutable assertions; "
                "the cohort and release contract above are the fixed test-set boundary."
                if baseline_groups
                else "The cohort was frozen before Proposal execution; outcomes remain outside the immutable fixture."
            ),
            "generated_at": report.get("generated_at"),
            "kpis": report.get("kpis") or {},
            "groups": baseline_groups,
        },
    }


def validate_immutable_testset(
    plan: Mapping[str, Any],
    testset: Mapping[str, Any],
    *,
    source: str,
    sha256: str,
) -> dict[str, Any]:
    contract = testset.get("contract") if isinstance(testset.get("contract"), Mapping) else {}
    testset_groups = testset.get("groups") if isinstance(testset.get("groups"), list) else []
    plan_groups = plan.get("groups") if isinstance(plan.get("groups"), list) else []

    def identity_from_testset(group: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "cohort_order": group.get("cohort_order"),
            "scenario_group_id": int(group["scenario_group_id"]),
            "event_type_id": int(group["event_type_id"]),
            "event_id": int(group["event_id"]),
            "scenario_ids": [int(item["scenario_id"]) for item in group.get("scenarios") or []],
        }

    def identity_from_plan(group: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "cohort_order": group.get("cohort_order"),
            "scenario_group_id": int(group["scenario_group_id"]),
            "event_type_id": int(group["event_type_id"]),
            "event_id": int(group["event_id"]),
            "scenario_ids": [
                int(item["scenario_id"]) for item in group.get("selected_scenarios") or []
            ],
        }

    testset_identity = [identity_from_testset(group) for group in testset_groups if isinstance(group, Mapping)]
    plan_identity = [identity_from_plan(group) for group in plan_groups if isinstance(group, Mapping)]
    selection_policy = str(plan.get("selection_policy") or contract.get("selection_policy") or "")
    expected_group_count = len(plan_identity)
    expected_scenario_count = expected_group_count * 3
    expected_dataset_id = (
        "model-parameter-v4.1.2-expanded-event-cohort-20-groups-20261007"
        if selection_policy == EXPANDED_EVENT_SELECTION_POLICY
        else f"model-parameter-v4.1.2-existing-event-pool-regenerated-{expected_group_count}-groups-20261007"
    )
    checks = {
        "dataset_id_fixed": testset.get("dataset_id") == expected_dataset_id,
        "api_version_v4": contract.get("api_version") == EXPECTED_API_VERSION,
        "generation_strategy_fixed": contract.get("generation_strategy") == EXPECTED_GENERATION_STRATEGY,
        "scenario_lever_release_fixed": contract.get("scenario_lever_release") == EXPECTED_CATALOG_VERSION,
        "catalog_checksum_fixed": contract.get("scenario_lever_catalog_checksum") == EXPECTED_CATALOG_CHECKSUM,
        "proposal_flow_release_fixed": contract.get("proposal_flow_release")
        == FIXED_TESTSET_SOURCE_FLOW_RELEASE,
        "selection_policy_fixed": contract.get("selection_policy") == selection_policy,
        "group_count_matches_plan": contract.get("group_count")
        == len(testset_identity)
        == expected_group_count
        > 0,
        "exactly_3_scenarios_per_group": contract.get("representative_scenarios_per_group") == 3
        and all(len(group["scenario_ids"]) == 3 for group in testset_identity),
        "scenario_count_matches_plan": contract.get("scenario_count") == expected_scenario_count
        and len({scenario_id for group in testset_identity for scenario_id in group["scenario_ids"]})
        == expected_scenario_count,
        "plan_identity_matches_testset": plan_identity == testset_identity,
    }
    cohort_identity = testset.get("cohort_identity")
    cohort_identity = cohort_identity if isinstance(cohort_identity, Mapping) else {}
    if selection_policy == EXPANDED_EVENT_SELECTION_POLICY:
        checks.update(
            {
                "expanded_event_contract_fixed": expected_group_count == 20
                and cohort_identity.get("event_sets_disjoint") is True,
                "baseline_event_ids_match_plan": cohort_identity.get("baseline_event_ids")
                == [int(item) for item in plan.get("baseline_event_ids") or []],
                "expanded_event_ids_match_plan": cohort_identity.get("expanded_event_ids")
                == [int(item) for item in plan.get("expanded_event_ids") or []],
            },
        )
    elif selection_policy == REGENERATED_EVENT_POOL_SELECTION_POLICY:
        checks.update(
            {
                "regenerated_event_pool_contract_fixed": expected_group_count == 40
                and cohort_identity.get("event_pool_reused_exactly") is True,
                "source_event_ids_match_plan": cohort_identity.get("source_event_ids")
                == [int(item) for item in plan.get("source_event_ids") or []],
                "cohort_event_ids_match_plan": cohort_identity.get("cohort_event_ids")
                == [int(item) for item in plan.get("cohort_event_ids") or []],
                "original_group_ids_match_plan": cohort_identity.get("original_group_ids")
                == [int(item) for item in plan.get("baseline_group_ids") or []],
                "regenerated_group_ids_match_plan": cohort_identity.get("regenerated_group_ids")
                == [int(item) for item in plan.get("new_group_ids") or []],
                "incomplete_attempt_group_ids_match_plan": cohort_identity.get(
                    "preserved_incomplete_attempt_group_ids",
                )
                == [int(item) for item in plan.get("preserved_incomplete_attempt_group_ids") or []],
            },
        )
    else:
        checks["supported_selection_policy"] = False
    return {
        "source": source,
        "sha256": sha256,
        "checks": checks,
        "pass": all(checks.values()),
        "group_count": len(testset_identity),
        "scenario_count": sum(len(group["scenario_ids"]) for group in testset_identity),
    }


def reconcile_final_history(
    report: Mapping[str, Any],
    history: Mapping[str, Any],
    *,
    source: str | None = None,
) -> dict[str, Any]:
    updated = dict(report)
    selection = history.get("selection") if isinstance(history.get("selection"), Mapping) else {}
    counts = selection.get("counts") if isinstance(selection.get("counts"), Mapping) else {}
    expected_success_ids: set[int] = set()
    expected_uncovered_ids: set[int] = set()
    expected_skip_ids: set[int] = set()
    expected_group_by_scenario: dict[int, int] = {}
    for group in updated.get("groups") or []:
        if not isinstance(group, Mapping):
            continue
        group_id = int(group["scenario_group_id"])
        for scenario in group.get("scenarios") or []:
            if not isinstance(scenario, Mapping):
                continue
            scenario_id = int(scenario["scenario_id"])
            expected_group_by_scenario[scenario_id] = group_id
            if scenario.get("proposal_eligible", True) is not True:
                expected_skip_ids.add(scenario_id)
            elif scenario.get("status") == "PASS":
                expected_success_ids.add(scenario_id)
            else:
                expected_uncovered_ids.add(scenario_id)

    actual_covered_ids: set[int] = set()
    actual_uncovered_ids: set[int] = set()
    actual_skip_ids: set[int] = set()
    history_identity_errors: list[str] = []
    proposal_rows = [
        row
        for item in history.get("preflight") or []
        if isinstance(item, Mapping)
        for row in (item.get("uncovered_guard") or {}).get("history") or []
        if isinstance(row, Mapping)
    ]
    for item in history.get("preflight") or []:
        if not isinstance(item, Mapping) or item.get("scenario_id") is None:
            continue
        scenario_id = int(item["scenario_id"])
        guard = item.get("uncovered_guard") if isinstance(item.get("uncovered_guard"), Mapping) else {}
        if item.get("status") == "SKIP":
            actual_skip_ids.add(scenario_id)
        elif guard.get("decision") == "SKIP":
            actual_covered_ids.add(scenario_id)
        elif guard.get("eligible") is True:
            actual_uncovered_ids.add(scenario_id)
        actual_group_id = item.get("scenario_group_id")
        expected_group_id = expected_group_by_scenario.get(scenario_id)
        if expected_group_id is None:
            history_identity_errors.append(f"out-of-scope scenario_id={scenario_id}")
        elif actual_group_id != expected_group_id:
            history_identity_errors.append(
                f"scenario_id={scenario_id}: group={actual_group_id!r}, expected={expected_group_id!r}",
            )
        for row in guard.get("history") or []:
            if not isinstance(row, Mapping):
                continue
            if row.get("scenario_id") != scenario_id or row.get("scenario_group_id") != expected_group_id:
                history_identity_errors.append(
                    f"proposal_id={row.get('model_param_proposal_id')}: Scenario/Group identity mismatch",
                )
    proposal_statuses = Counter(str(row.get("status") or "") for row in proposal_rows)
    callback_statuses = Counter(str(row.get("callback_status") or "") for row in proposal_rows)
    kpis = updated["kpis"]
    checks = {
        "history_status_pass": history.get("status") == "PASS",
        "covered_count_matches_successes": counts.get("covered_skip") == kpis["successful_proposal_count"],
        "uncovered_count_matches_failures": counts.get("eligible_uncovered")
        == kpis["semantic_empty_failure_count"] + kpis["other_failure_count"],
        "coverage_limit_count_matches": counts.get("lifecycle_or_capability_skip")
        == kpis["preflight_coverage_limit_scenario_count"],
        "no_hard_stop": counts.get("hard_stop") == 0,
        "all_persisted_rows_proposed": proposal_statuses == {"PROPOSED": kpis["successful_proposal_count"]},
        "all_callbacks_skipped": callback_statuses == {"SKIPPED": kpis["successful_proposal_count"]},
        "covered_scenario_ids_match_successes": actual_covered_ids == expected_success_ids,
        "uncovered_scenario_ids_match_non_successes": actual_uncovered_ids == expected_uncovered_ids,
        "lifecycle_skip_scenario_ids_match": actual_skip_ids == expected_skip_ids,
        "history_scenario_group_identity": not history_identity_errors,
    }
    updated["db_reconciliation"] = {
        "source": source,
        "counts": dict(counts),
        "proposal_status_counts": dict(sorted(proposal_statuses.items())),
        "callback_status_counts": dict(sorted(callback_statuses.items())),
        "expected_success_scenario_ids": sorted(expected_success_ids),
        "actual_covered_scenario_ids": sorted(actual_covered_ids),
        "expected_uncovered_scenario_ids": sorted(expected_uncovered_ids),
        "actual_uncovered_scenario_ids": sorted(actual_uncovered_ids),
        "expected_skip_scenario_ids": sorted(expected_skip_ids),
        "actual_skip_scenario_ids": sorted(actual_skip_ids),
        "identity_errors": history_identity_errors,
        "checks": checks,
        "pass": all(checks.values()),
    }
    operational_checks = dict(updated["operational_checks"])
    operational_checks["final_db_history_reconciled"] = all(checks.values())
    updated["operational_checks"] = operational_checks
    updated["operational_pass"] = all(operational_checks.values())
    if not updated["operational_pass"]:
        updated["verdict"] = "FAIL"
    return updated


def attach_final_cohort_trio_analysis(
    report: Mapping[str, Any],
    testset: Mapping[str, Any],
    history: Mapping[str, Any],
    *,
    testset_source: str | None = None,
    testset_sha256: str | None = None,
    history_source: str | None = None,
    history_sha256: str | None = None,
) -> dict[str, Any]:
    updated = dict(report)
    analysis = build_final_cohort_trio_analysis(
        testset,
        history,
        testset_source=testset_source,
        testset_sha256=testset_sha256,
        history_source=history_source,
        history_sha256=history_sha256,
    )
    updated["final_cohort_trio_analysis"] = analysis
    operational_checks = dict(updated.get("operational_checks") or {})
    operational_checks["final_cohort_trio_analysis_complete"] = analysis["pass"]
    updated["operational_checks"] = operational_checks
    updated["operational_pass"] = all(operational_checks.values())
    if not updated["operational_pass"]:
        updated["verdict"] = "FAIL"
    elif analysis["quality_review_reasons"] and updated.get("verdict") == "PASS":
        updated["verdict"] = "REVIEW"
    return updated


def render_final_cohort_trio_section(analysis: Mapping[str, Any]) -> str:
    kpis = analysis.get("kpis")
    kpis = kpis if isinstance(kpis, Mapping) else {}
    groups = [item for item in analysis.get("groups") or [] if isinstance(item, Mapping)]
    incomplete_by_scenario = analysis.get("slot_rationale_incomplete_by_scenario")
    incomplete_by_scenario = (
        incomplete_by_scenario if isinstance(incomplete_by_scenario, Mapping) else {}
    )
    lines = [
        "## 최종 DB 기준 Trio Parameter·값 변별",
        "",
        (
            f"- 고정 {kpis.get('group_count', 0)} Group x 대표 3개 Scenario 전체를 분모로 최종 "
            "저장된 Proposal payload를 read-only 재조회한 결과입니다. 종류·값 비교는 세 Proposal이 "
            "모두 있는 Group만 수행합니다."
        ),
        "",
        "| KPI | 결과 |",
        "| --- | ---: |",
        (
            f"| Proposal 있음 | {kpis.get('proposal_success_count', 0)} / "
            f"{kpis.get('scenario_count', 0)} ({kpis.get('proposal_success_rate_percent', 0)}%) |"
        ),
        (
            f"| 그룹 내 3개 모두 Proposal 있음 | {kpis.get('triple_success_group_count', 0)} / "
            f"{kpis.get('group_count', 0)} ({kpis.get('triple_success_group_rate_percent', 0)}%) |"
        ),
        (
            "| 파라미터 종류 동일 (full-trio 분모) | "
            f"{kpis.get('identical_parameter_type_group_count', 0)} / "
            f"{kpis.get('triple_success_group_count', 0)} "
            f"({kpis.get('parameter_type_consistency_rate_percent', 0)}%) |"
        ),
        (
            "| 같은 종류 + 세 Scenario 전체 proposed-value signature 모두 다름 | "
            f"{kpis.get('same_types_with_all_three_scenario_values_distinct_group_count', 0)} / "
            f"{kpis.get('identical_parameter_type_group_count', 0)} "
            f"({kpis.get('same_types_with_all_three_scenario_values_distinct_rate_percent', 0)}%) |"
        ),
        (
            "| exact common slot 값 차이 | "
            f"{kpis.get('exact_common_slots_with_different_values', 0)} / "
            f"{kpis.get('exact_common_slot_count', 0)} "
            f"({kpis.get('exact_common_slots_with_different_values_rate_percent', 0)}%) |"
        ),
        (
            "| exact common slot 세 값 모두 다름 | "
            f"{kpis.get('exact_common_slots_with_all_three_values_distinct', 0)} / "
            f"{kpis.get('exact_common_slot_count', 0)} "
            f"({kpis.get('exact_common_slots_with_all_three_values_distinct_rate_percent', 0)}%) |"
        ),
        f"| Value cell | {kpis.get('value_cell_count', 0)} |",
        (
            "| Slot 근거 non-empty | "
            f"{kpis.get('slot_rationale_nonempty_count', 0)} / "
            f"{kpis.get('value_cell_count', 0)} "
            f"({kpis.get('slot_rationale_nonempty_rate_percent', 0)}%) |"
        ),
        (
            "| Slot 근거 필수 섹션 완전 | "
            f"{kpis.get('slot_rationale_explicit_count', 0)} / "
            f"{kpis.get('value_cell_count', 0)} "
            f"({kpis.get('slot_rationale_explicit_rate_percent', 0)}%) |"
        ),
        "",
        "### Group별 최종 결과",
        "",
        "| # | Group | Scenario IDs | 성공 | 동일 종류 | 값 차이 | exact slot / 차이 slot | Parameter |",
        "| ---: | ---: | --- | ---: | --- | --- | ---: | --- |",
    ]
    for index, group in enumerate(groups, start=1):
        triple_success = group.get("triple_success") is True
        comparable = group.get("trio_payload_comparable") is True
        identical = group.get("actual_parameter_sets_identical") is True
        lines.append(
            "| {order} | {group_id} | {scenario_ids} | {success}/3 | {same} | {different} | "
            "{slots} | {parameters} |".format(
                order=group.get("cohort_order") or index,
                group_id=group.get("scenario_group_id"),
                scenario_ids=", ".join(
                    str(item) for item in group.get("selected_scenario_ids") or []
                ),
                success=group.get("successful_count", 0),
                same=("Y" if identical else "N") if comparable else "N/A",
                different=(
                    "Y" if group.get("all_three_scenario_value_signatures_distinct") else "N"
                ) if comparable and identical else "N/A",
                slots=(
                    f"{group.get('exact_common_slot_count', 0)}/"
                    f"{group.get('exact_common_slots_with_different_values', 0)}"
                    if comparable
                    else "N/A"
                ),
                parameters=(
                    ", ".join(str(item) for item in group.get("common_parameter_names") or [])
                    or "-"
                ) if triple_success else "N/A",
            ),
        )
    lines.extend(
        [
            "",
            "### 판정 기준과 증적 완전성",
            "",
            (
                "- `값 차이`는 같은 Parameter 종류를 제안한 full-trio에서 각 Scenario의 전체 "
                "`proposedValue` signature 세 개가 서로 모두 다른지 판정합니다."
            ),
            (
                "- `exact slot`은 Parameter명과 모든 좌표가 세 Proposal에 공통인 cell만 비교하는 "
                "보조 지표입니다. 좌표 구성이 다르면 이 분모에 들어가지 않습니다."
            ),
            (
                "- Slot 근거 필수 섹션은 대상·기간, 근거 유형, 인과 경로, 기준값, 적용 정책, 계산, "
                "제안값, 근거, 주요 가정, 판단 설명, 불확실성입니다."
            ),
            (
                "- 필수 섹션 미완전 Scenario: "
                + (", ".join(str(item) for item in sorted(map(int, incomplete_by_scenario))) or "없음")
            ),
            "",
            f"- 증적 정합성: `{'PASS' if analysis.get('pass') else 'FAIL'}`",
            *[
                f"- [{'x' if passed else ' '}] `{name}`"
                for name, passed in (analysis.get("checks") or {}).items()
            ],
        ],
    )
    review_reasons = analysis.get("quality_review_reasons") or []
    if review_reasons:
        lines.extend(["", "### 품질 검토 필요", "", *[f"- {item}" for item in review_reasons]])
    return "\n".join(lines)


def render_final_cohort_trio_report(analysis: Mapping[str, Any]) -> str:
    testset = analysis.get("testset")
    testset = testset if isinstance(testset, Mapping) else {}
    final_history = analysis.get("final_history")
    final_history = final_history if isinstance(final_history, Mapping) else {}
    verdict = analysis.get("verdict") or (
        "FAIL"
        if analysis.get("pass") is not True
        else "REVIEW" if analysis.get("quality_review_reasons") else "PASS"
    )
    return "\n".join(
        [
            "# v4.1.x Proposal Flow 최종 고정 Cohort Trio 품질 Report",
            "",
            f"- 생성 시각(UTC): {analysis.get('generated_at')}",
            f"- 판정: `{verdict}`",
            f"- 고정 테스트셋: `{testset.get('source')}`",
            f"- 테스트셋 SHA-256: `{testset.get('sha256')}`",
            f"- 최종 DB read-back: `{final_history.get('source')}`",
            f"- read-back SHA-256: `{final_history.get('sha256')}`",
            "",
            render_final_cohort_trio_section(analysis),
        ],
    )


def require_mi_base_fallback_mode(
    report: Mapping[str, Any],
    execution: Mapping[str, Any],
    *,
    expected_mode: str,
) -> dict[str, Any]:
    updated = dict(report)
    raw_sources = execution.get("execution_sources")
    source_rows = raw_sources if isinstance(raw_sources, list) else []
    if not source_rows:
        source_rows = [
            {
                "source": "merged execution",
                "phase": "final",
                "mi_base_fallback_policy": execution.get("manifest", {}).get(
                    "mi_base_fallback_policy",
                ),
            },
        ]
    observed: list[dict[str, Any]] = []
    for source in source_rows:
        if not isinstance(source, Mapping):
            continue
        policy = source.get("mi_base_fallback_policy")
        policy = policy if isinstance(policy, Mapping) else {}
        actual_mode = policy.get("active_case_unavailable_mode")
        observed.append(
            {
                "source": source.get("source"),
                "phase": source.get("phase"),
                "actual_mode": actual_mode,
                "matches": actual_mode == expected_mode,
            },
        )
    passed = bool(observed) and all(item["matches"] for item in observed)
    trace_summary = report.get("mi_base_trace_summary")
    trace_summary = trace_summary if isinstance(trace_summary, Mapping) else {}
    attempted_count = int(trace_summary.get("attempted_scenario_count") or 0)
    directly_observed_trace_count = int(
        trace_summary.get("directly_observed_trace_count", trace_summary.get("observed_trace_count")) or 0,
    )
    effective_trace_count = int(
        trace_summary.get("effective_trace_count", trace_summary.get("observed_trace_count")) or 0,
    )
    backfilled_trace_count = int(trace_summary.get("authorized_backfilled_trace_count") or 0)
    backfill_audit = trace_summary.get("backfill_audit")
    backfill_audit = backfill_audit if isinstance(backfill_audit, Mapping) else {}
    backfill_audit_pass = backfill_audit.get("pass") is True
    expected_trace_source = expected_mode if expected_mode in {"configured_fallback", "verified_cache"} else None
    trace_sources = trace_summary.get("sources")
    trace_sources = trace_sources if isinstance(trace_sources, Mapping) else {}
    direct_trace_complete = attempted_count == directly_observed_trace_count
    trace_complete = attempted_count == effective_trace_count
    trace_source_matches = expected_trace_source is None or (
        set(trace_sources) == {expected_trace_source}
        and int(trace_sources.get(expected_trace_source) or 0) == attempted_count
    )
    trace_identity_consistent = trace_summary.get("identity_consistent") is True
    if attempted_count:
        passed = (
            passed
            and trace_complete
            and trace_source_matches
            and trace_identity_consistent
            and (backfilled_trace_count == 0 or backfill_audit_pass)
        )
    updated["mi_base_fallback_expectation"] = {
        "expected_mode": expected_mode,
        "sources": observed,
        "expected_trace_source": expected_trace_source,
        "direct_trace_complete": direct_trace_complete,
        "trace_complete": trace_complete,
        "effective_trace_complete": trace_complete,
        "directly_observed_trace_count": directly_observed_trace_count,
        "authorized_backfilled_trace_count": backfilled_trace_count,
        "effective_trace_count": effective_trace_count,
        "backfill_audit_pass": backfill_audit_pass if backfilled_trace_count else None,
        "trace_source_matches": trace_source_matches,
        "trace_identity_consistent": trace_identity_consistent,
        "pass": passed,
    }
    operational_checks = dict(updated["operational_checks"])
    operational_checks["mi_base_fallback_mode_matches_requested"] = passed
    updated["operational_checks"] = operational_checks
    updated["operational_pass"] = all(operational_checks.values())
    if not updated["operational_pass"]:
        updated["verdict"] = "FAIL"
    return updated


def attach_diagnostic_executions(
    report: Mapping[str, Any],
    sources: Sequence[tuple[str, Mapping[str, Any]]],
) -> dict[str, Any]:
    updated = dict(report)
    fallback_expectation = report.get("mi_base_fallback_expectation")
    expected_mode = (
        fallback_expectation.get("expected_mode")
        if isinstance(fallback_expectation, Mapping)
        else None
    )
    diagnostics: list[dict[str, Any]] = []
    for label, execution in sources:
        attempts = [item for item in execution.get("attempts") or [] if isinstance(item, Mapping)]
        status_counts = Counter(str(item.get("status") or "UNKNOWN") for item in attempts)
        persisted_count = sum(
            item.get("proposal_persisted") is True or bool(item.get("new_proposal_ids"))
            for item in attempts
        )
        manifest = execution.get("manifest") if isinstance(execution.get("manifest"), Mapping) else {}
        policy = (
            manifest.get("mi_base_fallback_policy")
            if isinstance(manifest.get("mi_base_fallback_policy"), Mapping)
            else {}
        )
        errors = sorted({str(item.get("error") or "") for item in attempts if item.get("error")})
        diagnostics.append(
            {
                "source": label,
                "status": execution.get("status"),
                "attempt_count": len(attempts),
                "status_counts": dict(sorted(status_counts.items())),
                "mi_base_fallback_mode": policy.get("active_case_unavailable_mode"),
                "persisted_attempt_count": persisted_count,
                "errors": errors,
                "excluded_reason": (
                    f"요구한 {expected_mode or 'fallback mode'}과 실제 실행 정책이 달라 "
                    "MI Base 준비 단계에서 종료됨"
                ),
            },
        )
    updated["diagnostic_executions"] = diagnostics
    operational_checks = dict(updated["operational_checks"])
    operational_checks["excluded_diagnostic_runs_did_not_persist"] = all(
        item["persisted_attempt_count"] == 0 for item in diagnostics
    )
    updated["operational_checks"] = operational_checks
    updated["operational_pass"] = all(operational_checks.values())
    if not updated["operational_pass"]:
        updated["verdict"] = "FAIL"
    return updated


def render_markdown(report: Mapping[str, Any]) -> str:
    kpis = report["kpis"]
    checks = report["operational_checks"]
    post_fix_comparison = report.get("post_fix_comparison")
    fallback_expectation = report.get("mi_base_fallback_expectation")
    diagnostic_executions = report.get("diagnostic_executions")
    mi_base_trace = report.get("mi_base_trace_summary")
    mi_base_trace = mi_base_trace if isinstance(mi_base_trace, Mapping) else {}
    mi_base_backfill_audit = mi_base_trace.get("backfill_audit")
    mi_base_backfill_audit = (
        mi_base_backfill_audit if isinstance(mi_base_backfill_audit, Mapping) else {}
    )
    mi_base_trace_remediation = report.get("mi_base_trace_remediation")
    mi_base_trace_remediation = (
        mi_base_trace_remediation if isinstance(mi_base_trace_remediation, Mapping) else {}
    )
    creation = report.get("scenario_group_creation")
    creation = creation if isinstance(creation, Mapping) else {}

    def compact_ids(values: Sequence[object]) -> str:
        rendered = [str(item) for item in values]
        if len(rendered) <= 12:
            return ", ".join(rendered)
        return f"{', '.join(rendered[:6])}, …, {', '.join(rendered[-3:])} (총 {len(rendered)}개)"

    baseline_group_ids = compact_ids(creation.get("baseline_group_ids", []))
    new_group_ids = compact_ids(creation.get("new_group_ids", []))
    incomplete_group_ids = compact_ids(creation.get("preserved_incomplete_attempt_group_ids", []))
    baseline_event_ids = compact_ids(creation.get("baseline_event_ids", []))
    cohort_event_ids = compact_ids(
        creation.get("cohort_event_ids", creation.get("expanded_event_ids", [])),
    )
    regenerated_pool = creation.get("selection_policy") == REGENERATED_EVENT_POOL_SELECTION_POLICY
    read_only_release = report.get("read_only_release_contract")
    read_only_release = read_only_release if isinstance(read_only_release, Mapping) else {}
    release_pin_passed = (
        (read_only_release.get("scenario_lever_release") or report.get("scenario_lever_release"))
        == EXPECTED_CATALOG_VERSION
        and (read_only_release.get("proposal_flow_release") or report.get("proposal_flow_release"))
        == EXPECTED_PROPOSAL_FLOW_RELEASE
    )
    lines = [
        "# v4.1 Scenario Lever / v4.1.3 Proposal Flow 대표 3개 품질 평가",
        "",
        f"- 생성 시각(UTC): {report['generated_at']}",
        f"- Proposal 품질 실행 상태: `{report.get('execution_status')}`",
        f"- 최종 평가: `{report.get('verdict', 'PASS' if report['operational_pass'] else 'FAIL')}`",
        f"- 운영 정합성 판정: `{'PASS' if report['operational_pass'] else 'FAIL'}`",
        (
            "- 상태 해석: `ABSTAINED`는 근거 부족 등으로 의도적으로 제안하지 않은 품질 결과이며, "
            "그 자체는 하드 오류가 아닙니다. 다만 독립적인 운영·증적 gate가 실패하면 최종 판정은 `FAIL`입니다."
        ),
        "",
        "## Scenario Group 순증",
        "",
        "| 항목 | 결과 |",
        "| --- | --- |",
        f"| 기존 Group | {creation.get('baseline_group_count', 0)}개 ({baseline_group_ids}) |",
        f"| 신규 완료 Group | {creation.get('added_group_count', 0)}개 ({new_group_ids}) |",
        (
            f"| 보존된 미완료 attempt Group | {creation.get('preserved_incomplete_attempt_group_count', 0)}개 "
            f"({incomplete_group_ids or '-'}) |"
        ),
        (
            f"| 완료 Group 순증 / 기존 삭제 | {creation.get('net_added_group_count', 0)} / "
            f"{creation.get('existing_deleted_group_count')} |"
        ),
        f"| Event cohort 정책 | `{creation.get('selection_policy')}` |",
        (
            f"| 신규 Event / Event Type | {creation.get('net_added_event_count', 0)} / "
            f"{creation.get('expanded_event_type_count', 0)} |"
        ),
        f"| {'원본' if regenerated_pool else 'Baseline'} Event IDs | {baseline_event_ids} |",
        f"| {'재사용' if regenerated_pool else 'Expanded'} Event IDs | {cohort_event_ids} |",
        f"| 신규 Scenario | {creation.get('new_scenario_count', 0)}개 |",
        "",
        "## 방법론",
        "",
        "| 단계 | 방법 |",
        "| ---: | --- |",
        *[f"| {item['step']} | **{item['name']}** — {item['method']} |" for item in report.get("methodology") or []],
        "",
        "## 실행 기준",
        "",
        "| 항목 | 값 |",
        "| --- | --- |",
        f"| Scenario Lever | `{report['scenario_lever_release']}` |",
        f"| Proposal Flow | `{report.get('proposal_flow_release')}` |",
        (
            "| MI Base fallback | `{}` |".format(
                (report.get("mi_base_fallback_policy") or {}).get("active_case_unavailable_mode", "not-recorded"),
            )
        ),
        (
            "| 요구 MI Base fallback / 증적 일치 | `{}` / {} |".format(
                (fallback_expectation or {}).get("expected_mode", "not-required"),
                (
                    "PASS"
                    if isinstance(fallback_expectation, Mapping) and fallback_expectation.get("pass")
                    else "N/A" if not isinstance(fallback_expectation, Mapping) else "FAIL"
                ),
            )
        ),
        (
            "| MI Base 실제 trace source | `{}` |".format(
                ", ".join(
                    f"{source} {count}"
                    for source, count in (mi_base_trace.get("sources") or {}).items()
                )
                or "not-recorded",
            )
        ),
        (
            f"| MI Base trace 직접 관측 / 소급 보정 / 전체 attempt | "
            f"{mi_base_trace.get('directly_observed_trace_count', mi_base_trace.get('observed_trace_count', 0))} / "
            f"{mi_base_trace.get('authorized_backfilled_trace_count', 0)} / "
            f"{mi_base_trace.get('attempted_scenario_count', 0)} |"
        ),
        (
            "| MI Base 유효 trace 완전성 | {} |".format(
                "PASS"
                if isinstance(fallback_expectation, Mapping)
                and fallback_expectation.get("effective_trace_complete")
                else "FAIL",
            )
        ),
        (
            "| MI Base 소급 보정 audit | {} |".format(
                "PASS"
                if mi_base_backfill_audit.get("required") and mi_base_backfill_audit.get("pass")
                else "FAIL" if mi_base_backfill_audit.get("required") else "N/A",
            )
        ),
        f"| 유효 MI Base identity 일치 | {'PASS' if mi_base_trace.get('identity_consistent') else 'FAIL'} |",
        f"| 실행 증적 수 | {len(report.get('execution_sources') or []) or 1} |",
        f"| 명시적 post-fix 교체 시도 | {len(report.get('post_fix_replacements') or [])} |",
        "",
        "## Read-only KPI (핵심 7개)",
        "",
        (
            "- 의미: Scenario·Proposal history와 release/runtime 후보를 조회해 **실행 가능성만 판정**한 "
            "결과입니다. LLM 제안 로직, Proposal 저장, confirmation, callback은 실행하지 않습니다."
        ),
        (
            "- 로컬에서는 Object Storage 연결을 검증하지 않습니다. 따라서 Read-only PASS는 active MI Base가 "
            "사용 가능하다는 뜻이 아니며, 실제 실행은 아래 기록된 `configured_fallback` 정책과 별도 해석합니다."
        ),
        "",
        "| KPI | 결과 |",
        "| --- | ---: |",
        (
            f"| 대상 Group / 전체·대표 Scenario | {kpis['requested_group_count']} / "
            f"{kpis['generated_scenario_count']} / {kpis['selected_scenario_count']} |"
        ),
        f"| Release 고정 | {'PASS' if release_pin_passed else 'FAIL'} |",
        (
            f"| Runtime-capable / coverage limit | {kpis['read_only_runtime_capable_scenario_count']} / "
            f"{kpis['read_only_coverage_limit_scenario_count']} |"
        ),
        (
            f"| 현재 write eligible / covered | "
            f"{kpis['read_only_current_write_eligible_scenario_count']} / "
            f"{kpis['read_only_covered_scenario_count']} |"
        ),
        (
            f"| 3개 이상 write eligible / coverage-limit Group | "
            f"{kpis['groups_with_three_write_eligible_scenarios']} / "
            f"{kpis['coverage_limit_group_count']} |"
        ),
        (
            f"| 대표 3개 후보 종류 동일 | "
            f"{kpis['preflight_identical_parameter_type_group_count']} / "
            f"{kpis['requested_group_count']} "
            f"({kpis['preflight_parameter_type_consistency_rate_percent']}%) |"
        ),
        (
            f"| Preflight FAIL / hard stop | {kpis['read_only_preflight_fail_scenario_count']} / "
            f"{kpis['read_only_hard_stop_scenario_count']} |"
        ),
        "",
        "## Proposal 결과 KPI",
        "",
        (
            "- 메인 KPI는 `같은 종류 + Scenario별 다른 제안값`입니다. Scenario별 전체 제안 결과가 "
            "의도대로 달라지는지를 봅니다."
        ),
        (
            "- `동일 exact slot 값 차이`는 Parameter와 모든 좌표가 같은 cell만 비교해 좌표 구성 차이를 "
            "통제하는 보조 KPI입니다. 비교 가능한 분모가 더 작으므로 메인 KPI를 대체하지 않습니다."
        ),
        "",
        "| KPI | 결과 |",
        "| --- | ---: |",
        (
            f"| Proposal 성공 | {kpis['successful_proposal_count']} / "
            f"{kpis['selected_scenario_count']} ({kpis['proposal_coverage_percent']}%) |"
        ),
        (
            f"| Preflight→Proposal 전환율 | {kpis['successful_proposal_count']} / "
            f"{kpis['proposal_eligible_selected_scenario_count']} "
            f"({kpis['preflight_to_proposal_conversion_percent']}%) |"
        ),
        (
            f"| Semantic abstention | {kpis['semantic_abstention_count']} / "
            f"{kpis['attempted_scenario_count']} ({kpis['semantic_empty_rate_percent']}%) |"
        ),
        (
            f"| Resolved no-change / actionable abstention | "
            f"{kpis['resolved_no_change_count']} / "
            f"{kpis['actionable_semantic_abstention_count']} |"
        ),
        (
            f"| Semantic trace 완전 / 누락 | {kpis['semantic_trace_complete_count']} / "
            f"{kpis['semantic_trace_missing_count']} |"
        ),
        (
            f"| 그룹 내 3개 모두 성공 | {kpis['triple_success_group_count']} / "
            f"{kpis['requested_group_count']} "
            f"({kpis['triple_success_group_rate_percent']}%) |"
        ),
        (
            f"| 파라미터 종류 동일 (triple-success 분모) | "
            f"{kpis['identical_parameter_type_group_count']} / "
            f"{kpis['triple_success_group_count']} "
            f"({kpis['parameter_type_consistency_rate_percent']}%) |"
        ),
        (
            f"| 같은 종류 + Scenario별 다른 제안값 (메인; type-consistent 분모) | "
            f"{kpis['same_types_with_all_three_scenario_values_distinct_group_count']} / "
            f"{kpis['identical_parameter_type_group_count']} "
            f"({kpis['same_types_with_all_three_scenario_values_distinct_rate_percent']}%) |"
        ),
        (
            f"| 동일 exact slot 비교 가능 / 값 차이 Group (보조) | {kpis['groups_with_exact_common_slots']} / "
            f"{kpis['groups_with_different_values_on_exact_common_slots']} |"
        ),
        f"| Value cell | {kpis['value_cell_count']} |",
        f"| Identity / integrity 오류 | {kpis['identity_error_count']} / {kpis['integrity_error_count']} |",
        f"| 실패 시 Proposal 저장 | {kpis['persisted_failed_attempt_count']} |",
        f"| LLM retry / tokens | {kpis['llm_retry_count']} / {kpis['total_tokens']} |",
        (
            f"| 성공 지연 p50 / p95 (초) | {kpis['success_latency_seconds_p50']} / "
            f"{kpis['success_latency_seconds_p95']} |"
        ),
        (
            f"| 전체 시도 지연 p50 / p95 (초) | {kpis['all_attempt_latency_seconds_p50']} / "
            f"{kpis['all_attempt_latency_seconds_p95']} |"
        ),
        "",
    ]
    qualitative = report.get("qualitative_assessment")
    if isinstance(qualitative, list) and qualitative:
        lines.extend(
            [
                "## KPI 정성 평가",
                "",
                "| 영역 | 평가 | 근거 |",
                "| --- | --- | --- |",
                *[
                    f"| {item['area']} | {item['assessment']} | {item['basis']} |"
                    for item in qualitative
                    if isinstance(item, Mapping)
                ],
                "",
                "- 비율 정성 기준: `양호 ≥90%`, `보통 70~89.9%`, `개선 필요 <70%`; 비교 분모가 0이면 `판정 불가`.",
                "",
            ],
        )
    if isinstance(post_fix_comparison, Mapping):
        baseline = post_fix_comparison.get("baseline") or {}
        final = post_fix_comparison.get("final") or {}
        delta = post_fix_comparison.get("delta") or {}
        comparison_rows = (
            ("Proposal 성공", "successful_proposal_count", "건"),
            ("성공률", "success_rate_percent", "%p"),
            ("Semantic abstention", "semantic_abstention_count", "건"),
            ("기타 실패", "other_failure_count", "건"),
            ("구조화 semantic abstention", "structured_semantic_abstention_count", "건"),
            ("Semantic trace 완전", "semantic_trace_complete_count", "건"),
            ("Semantic trace 누락", "semantic_trace_missing_count", "건"),
        )
        lines.extend(
            [
                "## 개선 전후 비교 (동일 테스트셋)",
                "",
                (
                    "- 시도 Scenario 집합 동일성: "
                    f"`{'PASS' if post_fix_comparison.get('same_attempt_scope') else 'FAIL'}`"
                ),
                "",
                "| 지표 | 기존 | 개선 후 | 증감 |",
                "| --- | ---: | ---: | ---: |",
                *[
                    f"| {label} | {baseline.get(key)} | {final.get(key)} | "
                    f"{delta.get(key):+g}{unit} |"
                    for label, key, unit in comparison_rows
                ],
                "",
            ],
        )
    if isinstance(diagnostic_executions, list) and diagnostic_executions:
        lines.extend(
            [
                "## 제외된 진단 실행",
                "",
                "| 증적 | 정책 | 상태 / 시도 | 결과 | 저장 | 제외 사유 |",
                "| --- | --- | --- | --- | ---: | --- |",
                *[
                    "| `{source}` | `{mode}` | {status} / {attempts} | {results} | {persisted} | {reason} |".format(
                        source=Path(str(item.get("source") or "unknown")).name,
                        mode=item.get("mi_base_fallback_mode"),
                        status=item.get("status"),
                        attempts=item.get("attempt_count"),
                        results=", ".join(
                            f"{status} {count}"
                            for status, count in (item.get("status_counts") or {}).items()
                        ),
                        persisted=item.get("persisted_attempt_count"),
                        reason=item.get("excluded_reason"),
                    )
                    for item in diagnostic_executions
                ],
                "",
            ],
        )
    lines.extend(["## 정합성 검사", ""])
    lines.extend(f"- [{'x' if passed else ' '}] `{name}`" for name, passed in checks.items())
    if report.get("review_reasons"):
        lines.extend(
            [
                "",
                "## 검토·실패 사유",
                "",
                *[f"- {reason}" for reason in report["review_reasons"]],
            ],
        )
    if mi_base_trace_remediation.get("required"):
        historical_backfill = mi_base_trace_remediation.get("historical_evidence_backfilled") is True
        lines.extend(
            [
                "",
                "## MI Base trace 증적 구분",
                "",
                "| 항목 | 내용 |",
                "| --- | --- |",
                (
                    "| 영향 | Proposal KPI와 DB 대조는 변하지 않으며, 직접 관측과 추론 증적을 분리해 "
                    "해석해야 함 |"
                    if historical_backfill
                    else (
                        "| 영향 | Proposal KPI와 DB 대조는 유지되지만, 요구 fallback의 attempt별 관측 "
                        "완전성 gate는 FAIL |"
                    )
                ),
                (
                    "| 현재 증적 처리 | 승인된 소급 backfill 있음 / Proposal 재실행 없음 / 원본 증적 보존 |"
                    if historical_backfill
                    else (
                        "| 현재 증적 처리 | 소급 backfill 없음 / Proposal 재실행 없음 / 기존 FAIL 판정 유지 |"
                    )
                ),
                (
                    "| 직접 관측 / 추론 | {} / {}건 |".format(
                        mi_base_trace.get("directly_observed_trace_count", 0),
                        mi_base_trace.get("authorized_backfilled_trace_count", 0),
                    )
                    if historical_backfill
                    else "| 직접 관측 / 추론 | 해당 없음 |"
                ),
                (
                    "| 보정 audit | {} |".format(
                        "PASS" if mi_base_backfill_audit.get("pass") else "FAIL",
                    )
                    if historical_backfill
                    else "| 보정 audit | N/A |"
                ),
                f"| 해석 | {mi_base_trace_remediation.get('interpretation')} |",
            ],
        )
    immutable = report.get("immutable_testset")
    if isinstance(immutable, Mapping):
        lines.extend(
            [
                "",
                "## 고정 테스트셋",
                "",
                "| 항목 | 값 |",
                "| --- | --- |",
                f"| 파일 | `{immutable.get('source')}` |",
                f"| SHA-256 | `{immutable.get('sha256')}` |",
                f"| Group / Scenario | {immutable.get('group_count')} / {immutable.get('scenario_count')} |",
                f"| plan 대조 | {'PASS' if immutable.get('pass') else 'FAIL'} |",
            ],
        )
    reconciliation = report.get("db_reconciliation")
    if isinstance(reconciliation, Mapping):
        counts = reconciliation.get("counts") or {}
        proposal_statuses = reconciliation.get("proposal_status_counts") or {}
        callback_statuses = reconciliation.get("callback_status_counts") or {}
        lines.extend(
            [
                "",
                "## 최종 DB read-back",
                "",
                "| 항목 | 건수 |",
                "| --- | ---: |",
                f"| PROPOSED | {proposal_statuses.get('PROPOSED', 0)} |",
                f"| Callback SKIPPED | {callback_statuses.get('SKIPPED', 0)} |",
                f"| Eligible uncovered | {counts.get('eligible_uncovered', 0)} |",
                f"| Capability/preflight SKIP | {counts.get('lifecycle_or_capability_skip', 0)} |",
                f"| Hard stop | {counts.get('hard_stop', 0)} |",
                f"| 대조 판정 | {'PASS' if reconciliation.get('pass') else 'FAIL'} |",
            ],
        )
    final_cohort_analysis = report.get("final_cohort_trio_analysis")
    if isinstance(final_cohort_analysis, Mapping):
        lines.extend(["", *render_final_cohort_trio_section(final_cohort_analysis).splitlines()])
    if report.get("failure_reason_counts"):
        lines.extend(
            [
                "",
                "## 실패 원인",
                "",
                "| 원인 | 건수 |",
                "| --- | ---: |",
                *[f"| {item['reason']} | {item['count']} |" for item in report["failure_reason_counts"]],
            ],
        )
    if report.get("semantic_abstention_by_stage"):
        lines.extend(
            [
                "",
                "## Semantic abstention 단계별 분포",
                "",
                "| 단계 | 건수 |",
                "| --- | ---: |",
                *[
                    f"| {item['stage']} | {item['count']} |"
                    for item in report["semantic_abstention_by_stage"]
                ],
                "",
                "| reason_code | 건수 |",
                "| --- | ---: |",
                *[
                    f"| {item['reason_code']} | {item['count']} |"
                    for item in report["semantic_abstention_by_reason_code"]
                ],
            ],
        )
    if report.get("existing_kpi_improvement_ideas"):
        lines.extend(
            [
                "",
                "## 기존 KPI 개선 방안 (추가 KPI 아님)",
                "",
                "| 개선 대상 | 성공률·품질을 높이는 방향 |",
                "| --- | --- |",
                *[
                    f"| {item['target']} | {item['idea']} |"
                    for item in report["existing_kpi_improvement_ideas"]
                ],
            ],
        )
    lines.extend(
        [
            "",
            "## 그룹별 결과",
            "",
            "| # | Group | Event | Event Type | 성공 | 동일 종류 | 값 차이 | exact slot / 차이 slot | Parameter |",
            "| ---: | ---: | ---: | --- | ---: | --- | --- | ---: | --- |",
        ],
    )
    lines.extend(
        (
            "| {order} | {group} | {event} | {event_type} | {success}/3 | {same} | {different} | "
            "{slot_comparison} | {parameters} |"
        ).format(
            order=group.get("cohort_order") or "-",
            group=group["scenario_group_id"],
            event=group.get("event_id") or "-",
            event_type=group["event_type_code"],
            success=group["successful_count"],
            same=(
                "Y" if group["actual_parameter_sets_identical"] else "N"
            ) if group["triple_success"] else "N/A",
            different=(
                "Y" if group["all_three_scenario_value_signatures_distinct"] else "N"
            ) if group["triple_success"] and group["actual_parameter_sets_identical"] else "N/A",
            slot_comparison=(
                f"{group['exact_common_slot_count']}/{group['exact_common_slots_with_different_values']}"
                if group["triple_success"]
                else "N/A"
            ),
            parameters=(", ".join(group["common_parameter_names"]) or "-") if group["triple_success"] else "N/A",
        )
        for group in report["groups"]
    )
    lines.extend(
        [
            "",
            "## 해석 주의",
            "",
            (
                "- `Proposal 성공률`의 분모는 고정 대표 Scenario 전체이고, `Preflight→Proposal 전환율`의 "
                "분모는 그중 현재 write eligible인 Scenario입니다. 서로 다른 분모를 섞어 비교하면 안 됩니다."
            ),
            (
                "- `covered`는 기존 Proposal이 있어 중복 쓰기를 차단했다는 뜻이지 이번 실행의 성공이 아닙니다. "
                "`coverage limit`도 runtime 후보가 없어 LLM/쓰기를 시도하지 않은 상태이지 실행 실패가 아닙니다."
            ),
            (
                "- `Semantic abstention`은 근거·적용 좌표·유효한 값이 부족해 쓰지 않은 안전한 품질 결과입니다. "
                "전체 coverage는 낮추지만 하드 오류와 구분합니다."
            ),
            (
                "- `ABSTAINED_NO_CHANGE`는 unchanged 또는 완전 상쇄를 정직하게 보존한 resolved no-change로 "
                "따로 집계하며, 근거·slot·값 보강 대상인 actionable abstention과 섞지 않습니다."
            ),
            "- `파라미터 종류 동일`은 그룹 내 3개 Proposal이 모두 성공한 경우에만 판정합니다.",
            (
                "- 메인 `같은 종류 + Scenario별 다른 제안값`도 triple-success이면서 종류가 같은 Group만 "
                "분모입니다. 대표 3개의 전체 값 signature가 서로 모두 달라야 통과하며, 성공하지 않은 Group을 "
                "값 차이 실패로 간주하지 않습니다."
            ),
            (
                "- 보조 `exact slot 값 차이`는 모든 좌표가 같은 cell만 비교하므로 정상적인 좌표 차이까지 "
                "제외합니다. 분모가 더 작아 메인 지표와 수치를 직접 비교하면 안 됩니다."
            ),
            (
                "- 이번 실행은 Proposal-only입니다. confirmation/callback은 호출하지 않았고, 실패·abstain을 "
                "감추는 자동 외부 재시도도 하지 않았습니다."
            ),
            (
                "- `configured_fallback`은 Object Storage/active MI Base 검증이 아니라 로컬 고정 workbook의 "
                "Basecase를 사용했다는 뜻입니다. 운영 MI Base 연동 품질로 확대 해석하면 안 됩니다."
            ),
            (
                "- 특정 fallback을 실행 계약으로 요구한 경우 모든 attempt에 path-free MI Base identity가 있어야 "
                "합니다. 누락분은 자동 추정하지 않습니다. 명시적 사용자 승인과 fail-closed audit 조건을 모두 "
                "충족한 소급 보정만 유효 증적으로 인정하며, 이 경우에도 보정분은 직접 관측이 아닌 추론으로 "
                "표시하고 최종 품질 판정은 최소 `REVIEW`로 유지합니다."
            ),
            (
                "- 불변 경계는 고정 Event ID, 새 Group/Scenario ID, 대표 3개 ID와 release pin입니다. KPI 결과는 "
                "관측 baseline이며 향후 같은 테스트셋 재실행에서 달라질 수 있습니다."
            ),
            (
                "- 명시적 생성 실패가 남긴 Scenario 0건의 미완료 Group은 삭제하지 않고 audit으로 보존하되, "
                "완료 Group/대표 Scenario testset과 모든 Proposal KPI 분모에서는 제외합니다."
            ),
            (
                "- `PASS`는 운영·정합성 gate까지 충족했다는 뜻입니다. `REVIEW`는 gate는 통과했지만 "
                "semantic abstention 등 품질 검토 항목이 남았다는 뜻입니다."
            ),
            "",
            "## 표 컬럼 설명 (고정)",
            "",
            "### 그룹별 결과",
            "",
            "| 컬럼 | 의미 |",
            "| --- | --- |",
            *[f"| {column} | {meaning} |" for column, meaning in GROUP_RESULT_COLUMN_DEFINITIONS],
            "",
            "### Read-only KPI",
            "",
            "| 컬럼 | 의미 |",
            "| --- | --- |",
            *[f"| {column} | {meaning} |" for column, meaning in READ_ONLY_KPI_COLUMN_DEFINITIONS],
            "",
            "### Proposal 결과 KPI",
            "",
            "| 컬럼 | 의미 |",
            "| --- | --- |",
            *[f"| {column} | {meaning} |" for column, meaning in PROPOSAL_KPI_COLUMN_DEFINITIONS],
        ],
    )
    if isinstance(post_fix_comparison, Mapping):
        lines.extend(
            [
                "",
                "### 개선 전후 비교",
                "",
                "| 컬럼 | 의미 |",
                "| --- | --- |",
                *[
                    f"| {column} | {meaning} |"
                    for column, meaning in POST_FIX_COMPARISON_COLUMN_DEFINITIONS
                ],
            ],
        )
    if isinstance(diagnostic_executions, list) and diagnostic_executions:
        lines.extend(
            [
                "",
                "### 제외된 진단 실행",
                "",
                "| 컬럼 | 의미 |",
                "| --- | --- |",
                *[
                    f"| {column} | {meaning} |"
                    for column, meaning in DIAGNOSTIC_EXECUTION_COLUMN_DEFINITIONS
                ],
            ],
        )
    return "\n".join(lines)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    select = subparsers.add_parser("select")
    select.add_argument("--scenario-campaign-summary", type=Path, required=True)
    select.add_argument("--preflight-evidence", type=Path, required=True)
    select.add_argument("--baseline-scenario-summary", type=Path)
    select.add_argument("--output", type=Path, required=True)
    freeze = subparsers.add_parser("freeze")
    freeze.add_argument("--plan", type=Path, required=True)
    freeze.add_argument("--output", type=Path, required=True)
    final_cohort = subparsers.add_parser("final-cohort")
    final_cohort.add_argument("--testset-input", type=Path, required=True)
    final_cohort.add_argument("--final-history-evidence", type=Path, required=True)
    final_cohort.add_argument("--output-json", type=Path, required=True)
    final_cohort.add_argument("--output-markdown", type=Path, required=True)
    evaluate = subparsers.add_parser("evaluate")
    evaluate.add_argument("--plan", type=Path, required=True)
    evaluate.add_argument("--execution-evidence", type=Path, action="append", required=True)
    evaluate.add_argument("--post-fix-execution-evidence", type=Path, action="append", default=[])
    evaluate.add_argument("--post-fix-reason")
    evaluate.add_argument(
        "--diagnostic-execution-evidence",
        type=Path,
        action="append",
        default=[],
    )
    evaluate.add_argument(
        "--expected-mi-base-fallback-mode",
        choices=("fail", "verified_cache", "configured_fallback"),
    )
    evaluate.add_argument("--output-json", type=Path, required=True)
    evaluate.add_argument("--output-markdown", type=Path, required=True)
    evaluate.add_argument("--testset-input", type=Path)
    evaluate.add_argument("--testset-output", type=Path)
    evaluate.add_argument("--final-history-evidence", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "select":
        plan = build_selection_plan(
            scenario_summary_path=args.scenario_campaign_summary.resolve(),
            preflight_path=args.preflight_evidence.resolve(),
            baseline_summary_path=(
                args.baseline_scenario_summary.resolve() if args.baseline_scenario_summary else None
            ),
        )
        _write_json(args.output.resolve(), plan)
        print(json.dumps({"pass": plan["pass"], "counts": plan["counts"]}, ensure_ascii=False))
        return 0 if plan["pass"] else 1
    if args.command == "freeze":
        plan = _read_json(args.plan.resolve())
        if plan.get("pass") is not True:
            message = "Cannot freeze a representative-trio plan that did not pass"
            raise ValueError(message)
        frozen = build_reusable_testset(
            plan,
            {
                "generated_at": _now(),
                "kpis": {},
                "groups": [],
            },
        )
        output_path = args.output.resolve()
        if output_path.exists():
            message = f"Refusing to overwrite immutable testset: {output_path}"
            raise FileExistsError(message)
        _write_json(output_path, frozen)
        digest = hashlib.sha256(output_path.read_bytes()).hexdigest()
        print(json.dumps({"output": str(output_path), "sha256": digest}, ensure_ascii=False))
        return 0
    if args.command == "final-cohort":
        testset_path = args.testset_input.resolve()
        history_path = args.final_history_evidence.resolve()
        testset_bytes = testset_path.read_bytes()
        history_bytes = history_path.read_bytes()
        testset = json.loads(testset_bytes)
        history = json.loads(history_bytes)
        if not isinstance(testset, Mapping):
            message = f"Expected a JSON object: {testset_path}"
            raise TypeError(message)
        if not isinstance(history, Mapping):
            message = f"Expected a JSON object: {history_path}"
            raise TypeError(message)
        analysis = build_final_cohort_trio_analysis(
            testset,
            history,
            testset_source=str(testset_path),
            testset_sha256=hashlib.sha256(testset_bytes).hexdigest(),
            history_source=str(history_path),
            history_sha256=hashlib.sha256(history_bytes).hexdigest(),
        )
        _write_new_outputs(
            output_json=args.output_json,
            output_markdown=args.output_markdown,
            payload=analysis,
            markdown=render_final_cohort_trio_report(analysis),
        )
        print(
            json.dumps(
                {
                    "verdict": analysis["verdict"],
                    "pass": analysis["pass"],
                    "kpis": analysis["kpis"],
                },
                ensure_ascii=False,
            ),
        )
        return 0 if analysis["pass"] else 1
    plan = _read_json(args.plan.resolve())
    execution_sources = [(str(path.resolve()), _read_json(path.resolve())) for path in args.execution_evidence]
    post_fix_sources = [
        (str(path.resolve()), _read_json(path.resolve())) for path in args.post_fix_execution_evidence
    ]
    execution = merge_execution_evidence(
        execution_sources,
        post_fix_sources=post_fix_sources,
        post_fix_reason=args.post_fix_reason,
    )
    report = evaluate_execution(plan, execution)
    if args.expected_mi_base_fallback_mode:
        report = require_mi_base_fallback_mode(
            report,
            execution,
            expected_mode=args.expected_mi_base_fallback_mode,
        )
    if args.diagnostic_execution_evidence:
        diagnostic_sources = [
            (str(path.resolve()), _read_json(path.resolve()))
            for path in args.diagnostic_execution_evidence
        ]
        report = attach_diagnostic_executions(report, diagnostic_sources)
    testset: Mapping[str, Any] | None = None
    testset_path: Path | None = None
    testset_sha256: str | None = None
    if args.testset_input:
        testset_path = args.testset_input.resolve()
        testset_bytes = testset_path.read_bytes()
        testset = json.loads(testset_bytes)
        if not isinstance(testset, Mapping):
            message = f"Expected a JSON object: {testset_path}"
            raise TypeError(message)
        immutable = validate_immutable_testset(
            plan,
            testset,
            source=str(testset_path),
            sha256=hashlib.sha256(testset_bytes).hexdigest(),
        )
        testset_sha256 = immutable["sha256"]
        report["immutable_testset"] = immutable
        report["operational_checks"] = {
            **report["operational_checks"],
            "immutable_testset_matches_plan": immutable["pass"],
        }
        report["operational_pass"] = all(report["operational_checks"].values())
        if not report["operational_pass"]:
            report["verdict"] = "FAIL"
    if args.final_history_evidence:
        if testset is None or testset_path is None or testset_sha256 is None:
            message = (
                "--final-history-evidence requires --testset-input so the mandatory final-cohort "
                "trio Parameter/value section can be generated"
            )
            raise ValueError(message)
        history_path = args.final_history_evidence.resolve()
        history_bytes = history_path.read_bytes()
        history = json.loads(history_bytes)
        if not isinstance(history, Mapping):
            message = f"Expected a JSON object: {history_path}"
            raise TypeError(message)
        report = reconcile_final_history(
            report,
            history,
            source=str(history_path),
        )
        report = attach_final_cohort_trio_analysis(
            report,
            testset,
            history,
            testset_source=str(testset_path),
            testset_sha256=testset_sha256,
            history_source=str(history_path),
            history_sha256=hashlib.sha256(history_bytes).hexdigest(),
        )
    _write_json(args.output_json.resolve(), report)
    _write_text(args.output_markdown.resolve(), render_markdown(report))
    if args.testset_output:
        if args.testset_input and args.testset_output.resolve() == args.testset_input.resolve():
            message = "Immutable --testset-input cannot also be --testset-output"
            raise ValueError(message)
        _write_json(args.testset_output.resolve(), build_reusable_testset(plan, report))
    print(
        json.dumps(
            {
                "verdict": report["verdict"],
                "operational_pass": report["operational_pass"],
                "kpis": report["kpis"],
            },
            ensure_ascii=False,
        ),
    )
    return 0 if report["verdict"] in {"PASS", "REVIEW"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
