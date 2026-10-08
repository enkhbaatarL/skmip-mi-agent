# Copyright (c) 2026 SK Innovation E&S.
# ruff: noqa: ANN401, E402, T201

"""Build a reusable representative-trio test set from existing v4.1 groups.

The workflow is deliberately read-only with respect to application data:

1. discover release-matched Scenario Groups ordered by ``mod_dtm``;
2. keep only the latest structurally valid Group per ordered Event signature;
3. cap the cohort, run Proposal preflight without ``--execute``;
4. select three runtime-capable representative Scenarios per Group; and
5. freeze identities and collection-time observations in a versioned fixture.

No Scenario Group, Scenario, Proposal, confirmation, or callback row is
created by this module.
"""

from __future__ import annotations

import argparse
import asyncio
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any


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

from apps.common.configs.database.sync_database.connection import get_sync_session
from apps.persistence.event.repository import EventRepository
from apps.persistence.scenario.repository import ScenarioRepository
from apps.persistence.scenario_group.repository import ScenarioGroupRepository
from tests.manual.model_parameter_agent.evaluate_representative_trios import (
    EXPECTED_API_VERSION,
    EXPECTED_CATALOG_CHECKSUM,
    EXPECTED_CATALOG_VERSION,
    EXPECTED_GENERATION_STRATEGY,
    EXPECTED_PROPOSAL_FLOW_RELEASE,
    FIXED_TESTSET_SOURCE_FLOW_RELEASE,
    PRESSURE_RANK,
    _current_write_eligible,
    _parameter_set,
    _runtime_capable,
    select_representative_trio,
)
from tests.manual.model_parameter_agent.run_proposal_only import (
    BASELINE_CAPABILITY_RELEASE,
    ProposalOnlyOptions,
    _runtime_dependencies,
    run_campaign,
)


SELECTION_POLICY = "existing-scenario/latest-distinct-ordered-event-set/max-50"
RECENCY_POLICY = "scenario_group.mod_dtm DESC, scenario_group_id DESC"
DEFAULT_DATASET_ID = "model-parameter-v4.1.2-existing-latest-distinct-40-groups-20261007"
ELIGIBLE_STATUSES = frozenset({"created", "realized"})


@dataclass(frozen=True)
class OutputPaths:
    inventory: Path
    preflight: Path
    plan: Path
    testset: Path
    report_json: Path
    report_markdown: Path


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _value(value: object) -> str:
    raw = getattr(value, "value", value)
    return str(raw or "").strip().lower()


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list | tuple | set | frozenset):
        return [_json_safe(item) for item in value]
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Decimal):
        return float(value)
    return getattr(value, "value", value)


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        message = f"Expected JSON object: {path}"
        raise TypeError(message)
    return payload


def _write_new_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as target:
        json.dump(_json_safe(payload), target, ensure_ascii=False, indent=2, sort_keys=True)
        target.write("\n")


def _write_new_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as target:
        target.write(value.rstrip() + "\n")


def _scenario_row(model: Any) -> dict[str, Any]:
    return {
        "scenarioId": int(model.scenario_id),
        "displayOrder": int(model.display_order or 0),
        "title": str(model.title or ""),
        "status": _value(model.status),
        "baselineYn": str(model.baseline_yn or "N"),
        "scenarioRole": str(model.scenario_role or "").strip().lower() or None,
        "pressureBand": str(model.global_pressure_band or "").strip().lower() or None,
        "cells": _json_safe(model.dimension_values or {}),
    }


def _group_contract_matches(group: Any) -> bool:
    return bool(
        group.api_version == EXPECTED_API_VERSION
        and group.generation_strategy == EXPECTED_GENERATION_STRATEGY
        and group.impact_catalog_version == EXPECTED_CATALOG_VERSION
        and group.impact_catalog_checksum == EXPECTED_CATALOG_CHECKSUM
        and _value(group.status) in ELIGIBLE_STATUSES
        and _value(group.stage) == "completed"
        and bool(group.parameter_mapping_ready),
    )


def _structural_checks(group: Any, relations: Sequence[Any], rows: Sequence[Mapping[str, Any]]) -> dict[str, bool]:
    cells = [json.dumps(row.get("cells") or {}, sort_keys=True, default=str) for row in rows]
    event_ids = [int(relation.mi_event_id) for relation in relations]
    display_orders = [int(relation.display_order) for relation in relations]
    eligible_rows = [row for row in rows if str(row.get("status") or "") in ELIGIBLE_STATUSES]
    definitions = group.dimension_definitions if isinstance(group.dimension_definitions, list) else []
    return {
        "ordered_event_set_present": bool(event_ids),
        "ordered_event_ids_unique": len(event_ids) == len(set(event_ids)),
        "event_display_orders_unique": len(display_orders) == len(set(display_orders)),
        "scenario_count_matches": int(group.scenario_count or 0) == len(rows),
        "at_least_three_active_scenarios": len(rows) >= 3,
        "at_least_three_execution_status_scenarios": len(eligible_rows) >= 3,
        "dimension_count_3_to_6": 3 <= len(definitions) <= 6,
        "exactly_one_baseline": sum(str(row.get("baselineYn") or "N").upper() == "Y" for row in rows) == 1,
        "has_floor": any(row.get("scenarioRole") == "floor" for row in rows),
        "has_ceiling": any(row.get("scenarioRole") == "ceiling" for row in rows),
        "unique_scenario_cells": len(cells) == len(set(cells)),
    }


def _event_payload(event_repository: EventRepository, relation: Any) -> dict[str, Any]:
    event = event_repository.fetch_event_detail_by_id(int(relation.mi_event_id)) or {}
    event_type = event.get("event_type_l2") if isinstance(event.get("event_type_l2"), Mapping) else {}
    return {
        "mi_event_id": int(relation.mi_event_id),
        "display_order": int(relation.display_order),
        "event_type_l2_id": int(relation.event_type_l2_id),
        "event_type_l2_code": str(event_type.get("code") or ""),
        "event_type_l2_label": str(event_type.get("label") or ""),
        "title": str(event.get("event_title") or event.get("event_title_ko") or ""),
        "occurred_at": str(event.get("occurred_at") or ""),
    }


def discover_inventory(*, max_groups: int) -> dict[str, Any]:
    if not 1 <= max_groups <= 50:
        message = f"max_groups must be between 1 and 50: {max_groups}"
        raise ValueError(message)

    session = get_sync_session()
    try:
        group_repository = ScenarioGroupRepository(session=session)
        scenario_repository = ScenarioRepository(session=session)
        event_repository = EventRepository(session=session)
        all_groups = group_repository.list_for_backoffice(sort="latest")
        release_matched_count = 0
        structurally_valid: list[dict[str, Any]] = []
        structural_exclusion_frequency: Counter[str] = Counter()
        for group in all_groups:
            if not _group_contract_matches(group):
                continue
            release_matched_count += 1
            relations = group_repository.fetch_group_events(int(group.scenario_group_id))
            rows = [
                _scenario_row(model)
                for model in scenario_repository.fetch_models_by_group_id(group.scenario_group_id)
            ]
            checks = _structural_checks(group, relations, rows)
            if not all(checks.values()):
                structural_exclusion_frequency.update(name for name, passed in checks.items() if not passed)
                continue
            events = [_event_payload(event_repository, relation) for relation in relations]
            structurally_valid.append(
                {
                    "scenario_group_id": int(group.scenario_group_id),
                    "title": str(group.title or ""),
                    "modified_at": group.mod_dtm.isoformat(),
                    "created_at": group.crt_dtm.isoformat(),
                    "event_signature": [event["mi_event_id"] for event in events],
                    "events": events,
                    "scenario_count": len(rows),
                    "scenarios": rows,
                    "group_contract": {
                        "api_version": group.api_version,
                        "generation_strategy": group.generation_strategy,
                        "impact_catalog_version": group.impact_catalog_version,
                        "impact_catalog_checksum": group.impact_catalog_checksum,
                        "status": _value(group.status),
                        "stage": _value(group.stage),
                        "parameter_mapping_ready": bool(group.parameter_mapping_ready),
                        "dimension_count": len(group.dimension_definitions or []),
                    },
                    "structural_checks": checks,
                },
            )
    finally:
        session.close()

    latest_by_signature: list[dict[str, Any]] = []
    duplicate_groups: list[dict[str, Any]] = []
    seen_signatures: dict[tuple[int, ...], int] = {}
    for group in structurally_valid:
        signature = tuple(int(item) for item in group["event_signature"])
        if signature in seen_signatures:
            duplicate_groups.append(
                {
                    "scenario_group_id": group["scenario_group_id"],
                    "event_signature": list(signature),
                    "kept_latest_scenario_group_id": seen_signatures[signature],
                    "modified_at": group["modified_at"],
                },
            )
            continue
        seen_signatures[signature] = int(group["scenario_group_id"])
        latest_by_signature.append(group)

    selected = latest_by_signature[:max_groups]
    cap_excluded = latest_by_signature[max_groups:]
    selected_scenario_ids = [
        int(row["scenarioId"])
        for group in selected
        for row in group["scenarios"]
    ]
    checks = {
        "max_group_count_not_exceeded": len(selected) <= max_groups <= 50,
        "selected_group_ids_unique": len({group["scenario_group_id"] for group in selected}) == len(selected),
        "selected_event_signatures_unique": len(
            {tuple(group["event_signature"]) for group in selected},
        )
        == len(selected),
        "latest_revision_per_event_signature": all(
            seen_signatures[tuple(group["event_signature"])] == group["scenario_group_id"] for group in selected
        ),
        "all_selected_groups_structurally_valid": all(
            all(group["structural_checks"].values()) for group in selected
        ),
        "all_source_scenarios_unique": len(selected_scenario_ids) == len(set(selected_scenario_ids)),
    }
    return {
        "schema_version": 1,
        "generated_at": _now(),
        "read_only": True,
        "selection_policy": SELECTION_POLICY,
        "recency_policy": RECENCY_POLICY,
        "max_group_count": max_groups,
        "release_contract": {
            "api_version": EXPECTED_API_VERSION,
            "generation_strategy": EXPECTED_GENERATION_STRATEGY,
            "scenario_lever_release": EXPECTED_CATALOG_VERSION,
            "scenario_lever_catalog_checksum": EXPECTED_CATALOG_CHECKSUM,
            "proposal_flow_release": EXPECTED_PROPOSAL_FLOW_RELEASE,
        },
        "counts": {
            "non_deleted_groups_scanned": len(all_groups),
            "release_contract_matched_groups": release_matched_count,
            "structurally_valid_groups": len(structurally_valid),
            "distinct_ordered_event_signatures": len(latest_by_signature),
            "older_duplicate_groups_excluded": len(duplicate_groups),
            "cap_excluded_distinct_groups": len(cap_excluded),
            "selected_groups": len(selected),
            "selected_source_scenarios": len(selected_scenario_ids),
        },
        "structural_exclusion_reason_counts": dict(sorted(structural_exclusion_frequency.items())),
        "older_duplicate_groups": duplicate_groups,
        "cap_excluded_groups": [
            {
                "scenario_group_id": group["scenario_group_id"],
                "event_signature": group["event_signature"],
                "modified_at": group["modified_at"],
            }
            for group in cap_excluded
        ],
        "selected_scenario_ids": selected_scenario_ids,
        "checks": checks,
        "pass": bool(selected) and all(checks.values()),
        "groups": selected,
    }


def _selected_scenario(row: Mapping[str, Any], preflight: Mapping[str, Any]) -> dict[str, Any]:
    guard = preflight.get("uncovered_guard") if isinstance(preflight.get("uncovered_guard"), Mapping) else {}
    return {
        "scenario_id": int(row["scenarioId"]),
        "display_order": int(row.get("displayOrder") or 0),
        "title": str(row.get("title") or ""),
        "baseline": str(row.get("baselineYn") or "N").upper() == "Y",
        "scenario_role": row.get("scenarioRole"),
        "pressure_band": row.get("pressureBand"),
        "cells": row.get("cells") or {},
        "collection_snapshot": {
            "scenario_context_fingerprint": preflight.get("scenario_context_fingerprint"),
            "input_fingerprint": preflight.get("input_fingerprint"),
            "preflight_status": preflight.get("status"),
            "runtime_capable": _runtime_capable(preflight),
            "current_write_eligible": _current_write_eligible(preflight),
            "current_guard_decision": guard.get("decision"),
            "runtime_parameter_names": sorted(_parameter_set(preflight)),
            "skip_reasons": list(preflight.get("skip_reasons") or []),
        },
    }


def build_plan(inventory: Mapping[str, Any], preflight: Mapping[str, Any]) -> dict[str, Any]:
    preflight_items = [item for item in preflight.get("preflight") or [] if isinstance(item, Mapping)]
    preflight_by_id = {
        int(item["scenario_id"]): item
        for item in preflight_items
        if item.get("scenario_id") is not None
    }
    groups: list[dict[str, Any]] = []
    for recency_rank, group in enumerate(inventory.get("groups") or [], start=1):
        selected_rows, diagnostics = select_representative_trio(
            group["scenarios"],
            preflight_by_id,
            require_uncovered=False,
        )
        events = [dict(item) for item in group.get("events") or []]
        groups.append(
            {
                "recency_rank": recency_rank,
                "scenario_group_id": int(group["scenario_group_id"]),
                "group_title": group.get("title"),
                "modified_at": group.get("modified_at"),
                "created_at": group.get("created_at"),
                "event_signature": [int(item) for item in group.get("event_signature") or []],
                "events": events,
                "event_type_ids": sorted({int(item["event_type_l2_id"]) for item in events}),
                "event_type_codes": sorted(
                    {str(item.get("event_type_l2_code") or "") for item in events} - {""},
                ),
                "source_scenario_count": int(group["scenario_count"]),
                "group_contract": group.get("group_contract") or {},
                "structural_checks": group.get("structural_checks") or {},
                "selection_diagnostics": diagnostics,
                "selected_scenarios": [
                    _selected_scenario(row, preflight_by_id[int(row["scenarioId"])]) for row in selected_rows
                ],
            },
        )

    source_ids = {int(item) for item in inventory.get("selected_scenario_ids") or []}
    observed_ids = set(preflight_by_id)
    manifest = preflight.get("manifest") if isinstance(preflight.get("manifest"), Mapping) else {}
    capability = (
        manifest.get("capability_contract")
        if isinstance(manifest.get("capability_contract"), Mapping)
        else {}
    )
    resource = manifest.get("resource") if isinstance(manifest.get("resource"), Mapping) else {}
    safety = preflight.get("safety") if isinstance(preflight.get("safety"), Mapping) else {}
    selected_ids = [
        scenario["scenario_id"]
        for group in groups
        for scenario in group["selected_scenarios"]
    ]
    checks = {
        "inventory_passed": inventory.get("pass") is True,
        "preflight_status_pass": preflight.get("status") == "PASS",
        "runner_mode_read_only": preflight.get("mode") == "read-only" and not (preflight.get("attempts") or []),
        "preflight_catalog_release_matches": capability.get("catalog_version") == EXPECTED_CATALOG_VERSION
        and capability.get("catalog_checksum") == EXPECTED_CATALOG_CHECKSUM,
        "preflight_proposal_flow_release_matches": resource.get("proposal_flow_release")
        == EXPECTED_PROPOSAL_FLOW_RELEASE,
        "preflight_mutation_paths_disabled": safety.get("confirmation_invoked") is False
        and safety.get("callback_invoked") is False,
        "preflight_scope_matches_inventory": observed_ids == source_ids,
        "no_preflight_failure": not any(item.get("status") == "FAIL" for item in preflight_items),
        "group_count_within_cap": 0 < len(groups) <= int(inventory["max_group_count"]) <= 50,
        "exactly_three_selected_per_group": all(len(group["selected_scenarios"]) == 3 for group in groups),
        "selected_scenario_ids_unique": len(selected_ids) == len(set(selected_ids)),
        "ordered_event_signatures_unique": len({tuple(group["event_signature"]) for group in groups}) == len(groups),
        "all_group_contracts_match": all(
            group["group_contract"].get("api_version") == EXPECTED_API_VERSION
            and group["group_contract"].get("generation_strategy") == EXPECTED_GENERATION_STRATEGY
            and group["group_contract"].get("impact_catalog_version") == EXPECTED_CATALOG_VERSION
            and group["group_contract"].get("impact_catalog_checksum") == EXPECTED_CATALOG_CHECKSUM
            for group in groups
        ),
    }
    return {
        "schema_version": 2,
        "generated_at": _now(),
        "read_only": True,
        "selection_policy": SELECTION_POLICY,
        "recency_policy": RECENCY_POLICY,
        "scenario_lever_release": EXPECTED_CATALOG_VERSION,
        "proposal_flow_release": EXPECTED_PROPOSAL_FLOW_RELEASE,
        "inventory_generated_at": inventory.get("generated_at"),
        "preflight_generated_at": preflight.get("finished_at"),
        "max_group_count": int(inventory["max_group_count"]),
        "selected_scenario_ids": selected_ids,
        "checks": checks,
        "pass": all(checks.values()),
        "groups": groups,
    }


def _percent(numerator: int, denominator: int) -> float:
    return round(100 * numerator / denominator, 1) if denominator else 0.0


def _kpi_recommendations() -> list[dict[str, str]]:
    return [
        {
            "priority": "P0 gate",
            "kpi": "Distinct ordered-Event signature rate",
            "definition": "고정 Group 중 ordered Event ID 조합이 고유한 Group 비율",
            "formula": "unique(event_signature) / selected_groups",
            "recommended_criterion": "100%",
            "reason": "동일 입력의 재생성 Group이 표본 수를 부풀리는 것을 방지",
        },
        {
            "priority": "P0 gate",
            "kpi": "Latest revision selection rate",
            "definition": "각 Event 조합에서 가장 최근 mod_dtm Group을 선택한 비율",
            "formula": "latest-selected signatures / selected signatures",
            "recommended_criterion": "100%",
            "reason": "최신 생성 품질과 설정을 우선 반영",
        },
        {
            "priority": "P0 gate",
            "kpi": "Scenario context drift rate",
            "definition": "재실행 시 고정한 scenario_context_fingerprint가 달라진 Scenario 비율",
            "formula": "changed fingerprints / fixed scenarios",
            "recommended_criterion": "0%",
            "reason": "불변 테스트셋의 입력 동일성을 보증",
        },
        {
            "priority": "P1 quality",
            "kpi": "Runtime-capable trio rate",
            "definition": "대표 3개 모두 runtime Parameter 후보를 가진 Group 비율",
            "formula": "groups with 3 runtime-capable reps / selected_groups",
            "recommended_criterion": "baseline 대비 비하락; coverage limit 별도 표시",
            "reason": "Proposal 실행 가능성과 모델 coverage 한계를 분리",
        },
        {
            "priority": "P1 quality",
            "kpi": "Representative role coverage rate",
            "definition": "가능한 경우 baseline·floor·ceiling을 모두 포함한 trio 비율",
            "formula": "role-complete trios / groups with all three roles available in the selection pool",
            "recommended_criterion": "100% (역할이 모두 존재하는 Group)",
            "reason": "상·하방 및 기준 경로 비교 가능성 보장",
        },
        {
            "priority": "P1 quality",
            "kpi": "Preflight Parameter-type consistency",
            "definition": "trio의 runtime canonical Parameter 종류 집합이 동일한 Group 비율",
            "formula": "identical-type trios / full runtime-capable trio groups",
            "recommended_criterion": "상향 추세; coverage-limit Group 분리",
            "reason": "같은 Group 내 값 차이를 공정하게 비교할 전제",
        },
        {
            "priority": "P1 quality",
            "kpi": "Parameter portfolio coverage",
            "definition": "대표 Scenario가 덮는 canonical Parameter 종류 범위",
            "formula": "unique runtime Parameter names / runtime allowlist",
            "recommended_criterion": "release별 baseline 관리",
            "reason": "특정 Parameter에 편중된 성공률 착시 방지",
        },
        {
            "priority": "P1 quality",
            "kpi": "Top-1 Parameter concentration",
            "definition": "가장 자주 등장한 Parameter의 runtime-capable Scenario 점유율",
            "formula": "max(parameter scenario frequency) / runtime-capable reps",
            "recommended_criterion": "감시 지표; portfolio coverage와 함께 해석",
            "reason": "테스트셋 다양성 저하를 조기 탐지",
        },
        {
            "priority": "P1 execution",
            "kpi": "Same types + Scenario-specific proposed values",
            "definition": "종류가 같은 성공 trio 중 동일 Parameter의 제안값 signature가 Scenario별로 달라진 Group 비율",
            "formula": "value-differentiated groups / type-consistent triple-success groups",
            "recommended_criterion": "100% 목표; 향후 write 승인 실행에서 측정",
            "reason": "같은 Parameter 종류를 유지하면서 Scenario 차이가 제안값에 반영되는지 측정",
        },
        {
            "priority": "P1 execution",
            "kpi": "Same types + different exact-slot values",
            "definition": "종류가 같은 성공 trio 중 공통 exact model slot의 값이 달라진 Group 비율",
            "formula": "exact-slot differentiated groups / type-consistent triple-success groups with common slots",
            "recommended_criterion": "Scenario-specific 제안값 KPI와 함께 측정",
            "reason": "좌표 차이에 따른 착시를 제외하고 같은 모델 cell의 값 변별력을 확인",
        },
        {
            "priority": "P2 efficiency",
            "kpi": "Tokens per accepted value cell",
            "definition": "성공 Proposal의 유효 value cell 1개당 사용 token",
            "formula": "total tokens / accepted value cells",
            "recommended_criterion": "품질 gate 통과 후 하향 추세",
            "reason": "성공 건수만으로 드러나지 않는 비용 효율 비교",
        },
    ]


def build_report(
    inventory: Mapping[str, Any],
    preflight: Mapping[str, Any],
    plan: Mapping[str, Any],
    *,
    testset_path: Path,
    testset_sha256: str,
) -> dict[str, Any]:
    groups = [group for group in plan.get("groups") or [] if isinstance(group, Mapping)]
    scenarios = [
        scenario
        for group in groups
        for scenario in group.get("selected_scenarios") or []
        if isinstance(scenario, Mapping)
    ]
    snapshots = [scenario.get("collection_snapshot") or {} for scenario in scenarios]
    runtime_capable_count = sum(snapshot.get("runtime_capable") is True for snapshot in snapshots)
    current_write_eligible_count = sum(snapshot.get("current_write_eligible") is True for snapshot in snapshots)
    covered_count = sum(snapshot.get("current_guard_decision") == "SKIP" for snapshot in snapshots)
    coverage_limit_count = len(scenarios) - runtime_capable_count
    full_runtime_trios = sum(
        all(
            (scenario.get("collection_snapshot") or {}).get("runtime_capable") is True
            for scenario in group["selected_scenarios"]
        )
        for group in groups
    )
    identical_type_groups = sum(
        (group.get("selection_diagnostics") or {}).get("parameter_sets_identical_in_preflight") is True
        for group in groups
    )
    role_applicable_groups = sum(
        bool((group.get("selection_diagnostics") or {}).get("available_baseline_ids"))
        and bool((group.get("selection_diagnostics") or {}).get("available_floor_ids"))
        and bool((group.get("selection_diagnostics") or {}).get("available_ceiling_ids"))
        for group in groups
    )
    role_complete_groups = sum(
        any(scenario.get("baseline") is True for scenario in group["selected_scenarios"])
        and {scenario.get("scenario_role") for scenario in group["selected_scenarios"]} >= {"floor", "ceiling"}
        for group in groups
    )
    pressure_span_groups = 0
    parameter_frequency: Counter[str] = Counter()
    for group in groups:
        ranks = [PRESSURE_RANK.get(str(item.get("pressure_band") or ""), 0) for item in group["selected_scenarios"]]
        pressure_span_groups += int(bool(ranks) and max(ranks) - min(ranks) >= 2)
    for snapshot in snapshots:
        if snapshot.get("runtime_capable") is True:
            parameter_frequency.update(set(snapshot.get("runtime_parameter_names") or []))
    manifest = preflight.get("manifest") if isinstance(preflight.get("manifest"), Mapping) else {}
    runtime_allowlist = set(manifest.get("runtime_allowlist") or [])
    covered_parameters = set(parameter_frequency)
    top_parameter, top_frequency = parameter_frequency.most_common(1)[0] if parameter_frequency else (None, 0)
    inventory_counts = inventory.get("counts") if isinstance(inventory.get("counts"), Mapping) else {}
    group_count = len(groups)
    kpis = {
        "selected_group_count": group_count,
        "selected_scenario_count": len(scenarios),
        "release_contract_matched_group_count": int(inventory_counts.get("release_contract_matched_groups") or 0),
        "distinct_ordered_event_signature_count": int(
            inventory_counts.get("distinct_ordered_event_signatures") or 0,
        ),
        "older_duplicate_group_exclusion_count": int(
            inventory_counts.get("older_duplicate_groups_excluded") or 0,
        ),
        "cap_excluded_distinct_group_count": int(inventory_counts.get("cap_excluded_distinct_groups") or 0),
        "distinct_event_signature_rate_percent": _percent(
            len({tuple(group["event_signature"]) for group in groups}),
            group_count,
        ),
        "latest_revision_selection_rate_percent": 100.0 if group_count else 0.0,
        "runtime_capable_selected_scenario_count": runtime_capable_count,
        "preflight_coverage_limit_scenario_count": coverage_limit_count,
        "current_write_eligible_scenario_count": current_write_eligible_count,
        "currently_covered_scenario_count": covered_count,
        "full_runtime_capable_trio_group_count": full_runtime_trios,
        "full_runtime_capable_trio_rate_percent": _percent(full_runtime_trios, group_count),
        "preflight_identical_parameter_type_group_count": identical_type_groups,
        "preflight_parameter_type_consistency_applicable_group_count": full_runtime_trios,
        "preflight_parameter_type_consistency_rate_percent": _percent(
            identical_type_groups,
            full_runtime_trios,
        ),
        "preflight_parameter_type_consistency_all_group_rate_percent": _percent(
            identical_type_groups,
            group_count,
        ),
        "representative_role_applicable_group_count": role_applicable_groups,
        "representative_role_complete_group_count": role_complete_groups,
        "representative_role_coverage_rate_percent": _percent(role_complete_groups, role_applicable_groups),
        "representative_role_complete_all_group_rate_percent": _percent(role_complete_groups, group_count),
        "pressure_span_at_least_two_group_count": pressure_span_groups,
        "pressure_span_coverage_rate_percent": _percent(pressure_span_groups, group_count),
        "runtime_parameter_portfolio_count": len(covered_parameters),
        "runtime_allowlist_count": len(runtime_allowlist),
        "parameter_portfolio_coverage_rate_percent": _percent(len(covered_parameters), len(runtime_allowlist)),
        "top_parameter_name": top_parameter,
        "top_parameter_scenario_count": top_frequency,
        "top_parameter_concentration_percent": _percent(top_frequency, runtime_capable_count),
        "preflight_failure_count": sum(item.get("status") == "FAIL" for item in preflight.get("preflight") or []),
        "same_types_with_any_different_values_status": "NOT_MEASURED_READ_ONLY",
        "same_types_with_any_different_values_group_count": None,
        "same_types_with_any_different_values_applicable_group_count": None,
        "same_types_with_any_different_values_rate_percent": None,
        "exact_slot_value_differentiation_status": "NOT_MEASURED_READ_ONLY",
        "groups_with_exact_common_slots": None,
        "groups_with_different_values_on_exact_common_slots": None,
    }
    return {
        "schema_version": 1,
        "generated_at": _now(),
        "verdict": "PASS" if plan.get("pass") is True else "FAIL",
        "read_only": True,
        "read_only_scope": {
            "definition": (
                "기존 Group/Scenario와 Proposal history를 조회하고 release/구조 gate, runtime candidate, "
                "write guard 상태만 계산한 수집·preflight 보고서"
            ),
            "database_reads": True,
            "proposal_logic_executed": False,
            "llm_invoked": False,
            "object_storage_or_mi_base_bootstrapped": False,
            "application_data_mutated": False,
        },
        "read_only_kpi_interpretation": {
            "definition": (
                "Proposal을 생성하지 않고 기존 저장 데이터와 deterministic preflight로 계산한 "
                "cohort 구성·실행 전제·coverage 지표"
            ),
            "pass_meaning": (
                "선정·release·구조·preflight 계약이 유효하다는 뜻이며 실제 Proposal 품질이나 성공을 뜻하지 않음"
            ),
            "valid_uses": [
                "고유 Event signature와 최신 revision 선정 확인",
                "runtime-capable/coverage-limit 분포와 대표 trio 구성 품질 확인",
                "실행 전 Parameter 종류 일치, role, portfolio, concentration 확인",
                "현재 Proposal history에 따른 write-eligible/covered 상태 확인",
            ],
            "not_evaluated": [
                "실제 Proposal 성공 또는 semantic abstention",
                "실제 제안 Parameter 종류와 Scenario별 제안값 차이",
                "동일 exact model slot의 값 차이",
                "LLM token과 latency",
            ],
            "comparison_requirement": (
                "fixture identity, Scenario Lever/Proposal Flow release, context fingerprint가 같을 때만 회귀 비교"
            ),
        },
        "mutation_summary": {
            "scenario_group_created": 0,
            "scenario_created": 0,
            "proposal_created": 0,
            "confirmation_invoked": False,
            "callback_invoked": False,
        },
        "release_contract": inventory.get("release_contract") or {},
        "selection_policy": SELECTION_POLICY,
        "recency_policy": RECENCY_POLICY,
        "testset": {
            "path": str(testset_path.resolve()),
            "sha256": testset_sha256,
        },
        "inventory_counts": dict(inventory_counts),
        "kpis": kpis,
        "parameter_frequency": [
            {"parameter_name": name, "scenario_count": count}
            for name, count in sorted(parameter_frequency.items())
        ],
        "checks": plan.get("checks") or {},
        "kpi_recommendations": _kpi_recommendations(),
        "groups": groups,
    }


def build_testset(
    plan: Mapping[str, Any],
    report: Mapping[str, Any],
    *,
    dataset_id: str,
) -> dict[str, Any]:
    groups = [
        {
            "recency_rank": group["recency_rank"],
            "scenario_group_id": group["scenario_group_id"],
            "group_title": group.get("group_title"),
            "modified_at": group.get("modified_at"),
            "event_signature": group["event_signature"],
            "events": group["events"],
            "event_type_ids": group["event_type_ids"],
            "event_type_codes": group["event_type_codes"],
            "selection_diagnostics": group["selection_diagnostics"],
            "scenarios": group["selected_scenarios"],
        }
        for group in plan.get("groups") or []
    ]
    return {
        "schema_version": 2,
        "dataset_id": dataset_id,
        "created_at": plan.get("generated_at"),
        "purpose": "Reusable existing-Scenario trio cohort for Scenario Lever and Proposal Flow regression",
        "contract": {
            "api_version": EXPECTED_API_VERSION,
            "generation_strategy": EXPECTED_GENERATION_STRATEGY,
            "scenario_lever_release": EXPECTED_CATALOG_VERSION,
            "scenario_lever_catalog_checksum": EXPECTED_CATALOG_CHECKSUM,
            "proposal_flow_release": EXPECTED_PROPOSAL_FLOW_RELEASE,
            "selection_policy": SELECTION_POLICY,
            "recency_policy": RECENCY_POLICY,
            "source_mutation_policy": "read-only-existing-scenarios",
            "max_group_count": int(plan["max_group_count"]),
            "group_count": len(groups),
            "representative_scenarios_per_group": 3,
            "scenario_count": sum(len(group["scenarios"]) for group in groups),
        },
        "cohort_identity": {
            "scenario_group_ids": [group["scenario_group_id"] for group in groups],
            "ordered_event_signatures": [group["event_signature"] for group in groups],
            "scenario_ids": [
                scenario["scenario_id"] for group in groups for scenario in group["scenarios"]
            ],
        },
        "selection_method": (
            "Filter the exact v4/v4.1 contract, retain the latest structurally valid Group per ordered Event "
            "signature, cap at 50, then choose three runtime-capable Scenarios while preserving "
            "baseline/floor/ceiling and maximizing Parameter-set overlap plus pressure/cell diversity. "
            "Existing Proposal history is observed but does not disqualify a reusable Scenario."
        ),
        "groups": groups,
        "collection_baseline": {
            "observational": True,
            "generated_at": report.get("generated_at"),
            "kpis": report.get("kpis") or {},
            "note": (
                "Runtime candidates and uncovered/covered state are collection-time observations, not immutable "
                "expected outcomes. Group/Event/Scenario identities and release pins are the fixed boundary."
            ),
        },
        "kpi_recommendations": report.get("kpi_recommendations") or [],
    }


def validate_testset(plan: Mapping[str, Any], testset: Mapping[str, Any]) -> dict[str, Any]:
    contract = testset.get("contract") if isinstance(testset.get("contract"), Mapping) else {}
    groups = [group for group in testset.get("groups") or [] if isinstance(group, Mapping)]
    plan_groups = [group for group in plan.get("groups") or [] if isinstance(group, Mapping)]
    scenario_ids = [int(item["scenario_id"]) for group in groups for item in group.get("scenarios") or []]
    identity = [
        (
            int(group["scenario_group_id"]),
            tuple(int(item) for item in group.get("event_signature") or []),
            tuple(int(item["scenario_id"]) for item in group.get("scenarios") or []),
        )
        for group in groups
    ]
    plan_identity = [
        (
            int(group["scenario_group_id"]),
            tuple(int(item) for item in group.get("event_signature") or []),
            tuple(int(item["scenario_id"]) for item in group.get("selected_scenarios") or []),
        )
        for group in plan_groups
    ]
    checks = {
        "schema_version_2": testset.get("schema_version") == 2,
        "api_version_fixed": contract.get("api_version") == EXPECTED_API_VERSION,
        "generation_strategy_fixed": contract.get("generation_strategy") == EXPECTED_GENERATION_STRATEGY,
        "scenario_lever_release_fixed": contract.get("scenario_lever_release") == EXPECTED_CATALOG_VERSION,
        "catalog_checksum_fixed": contract.get("scenario_lever_catalog_checksum") == EXPECTED_CATALOG_CHECKSUM,
        "proposal_flow_release_fixed": contract.get("proposal_flow_release")
        == FIXED_TESTSET_SOURCE_FLOW_RELEASE,
        "selection_policy_fixed": contract.get("selection_policy") == SELECTION_POLICY,
        "read_only_source_policy_fixed": contract.get("source_mutation_policy") == "read-only-existing-scenarios",
        "group_count_within_cap": contract.get("group_count") == len(groups)
        and 0 < len(groups) <= int(contract.get("max_group_count") or 0) <= 50,
        "exactly_three_scenarios_per_group": contract.get("representative_scenarios_per_group") == 3
        and all(len(group.get("scenarios") or []) == 3 for group in groups),
        "scenario_count_and_uniqueness": contract.get("scenario_count") == len(scenario_ids)
        and len(scenario_ids) == len(set(scenario_ids)),
        "ordered_event_signatures_unique": len({item[1] for item in identity}) == len(identity),
        "plan_identity_matches_testset": identity == plan_identity,
    }
    return {"checks": checks, "pass": all(checks.values())}


def render_markdown(report: Mapping[str, Any]) -> str:
    inventory = report["inventory_counts"]
    kpis = report["kpis"]
    contract = report["release_contract"]
    lines = [
        "# 기존 Scenario 기반 최신 대표 trio 테스트셋 확장",
        "",
        f"- 최종 판정: `{report['verdict']}`",
        "- DB 변경: `없음` (Group/Scenario/Proposal 생성 0건)",
        f"- 선택 정책: `{report['selection_policy']}`",
        f"- 최신성 정렬: `{report['recency_policy']}`",
        f"- 테스트셋 SHA-256: `{report['testset']['sha256']}`",
        "",
        "## 실행 기준",
        "",
        "| 항목 | 값 |",
        "| --- | --- |",
        f"| Scenario Lever | `{contract.get('scenario_lever_release')}` |",
        f"| Catalog checksum | `{contract.get('scenario_lever_catalog_checksum')}` |",
        f"| Proposal Flow | `{contract.get('proposal_flow_release')}` |",
        f"| API / strategy | `{contract.get('api_version')}` / `{contract.get('generation_strategy')}` |",
        "| Source mutation | 기존 Scenario read-only 수집; 신규 생성 없음 |",
        "| Object Storage | read-only preflight이므로 접근/MI Base bootstrap 불필요 |",
        "",
        "## 용어 정의",
        "",
        "| 용어 | 의미 |",
        "| --- | --- |",
        (
            "| Read-only 수집 리포트 | 기존 DB의 Group/Scenario와 Proposal 이력을 조회하고, release·구조 gate, "
            "runtime 후보 및 현재 write guard 상태만 계산한 보고서입니다. Proposal/LLM 실행, "
            "Group·Scenario·Proposal 생성, confirmation/callback, Object Storage·MI Base bootstrap은 "
            "수행하지 않습니다. |"
        ),
        "",
        "## 후보군 압축",
        "",
        "| 단계 | Group 수 | 해석 |",
        "| --- | ---: | --- |",
        f"| exact release 계약 일치 | {inventory.get('release_contract_matched_groups', 0)} | v4/v4.1 및 완료 상태 |",
        f"| 구조 gate 통과 | {inventory.get('structurally_valid_groups', 0)} | trio 구성 가능한 기존 Group |",
        (
            f"| 고유 ordered Event 조합 | {inventory.get('distinct_ordered_event_signatures', 0)} | "
            "논리적으로 다른 입력 수 |"
        ),
        f"| 과거 중복 제외 | {inventory.get('older_duplicate_groups_excluded', 0)} | Event 조합별 최신 1개만 유지 |",
        f"| 50개 cap 제외 | {inventory.get('cap_excluded_distinct_groups', 0)} | 현재는 cap 미도달 |",
        f"| 최종 고정 | {kpis['selected_group_count']} | Group당 대표 Scenario 3개 |",
        "",
        "## Read-only KPI",
        "",
        "| KPI | 결과 |",
        "| --- | ---: |",
        f"| 대상 Group / Scenario | {kpis['selected_group_count']} / {kpis['selected_scenario_count']} |",
        f"| 고유 Event signature | {kpis['distinct_event_signature_rate_percent']}% |",
        f"| 최신 revision 선택 | {kpis['latest_revision_selection_rate_percent']}% |",
        (
            f"| Runtime-capable / coverage limit Scenario | "
            f"{kpis['runtime_capable_selected_scenario_count']} / "
            f"{kpis['preflight_coverage_limit_scenario_count']} |"
        ),
        (
            f"| 현재 write eligible / 기존 Proposal로 covered | "
            f"{kpis['current_write_eligible_scenario_count']} / {kpis['currently_covered_scenario_count']} |"
        ),
        (
            f"| 3개 모두 runtime-capable Group | {kpis['full_runtime_capable_trio_group_count']} / "
            f"{kpis['selected_group_count']} ({kpis['full_runtime_capable_trio_rate_percent']}%) |"
        ),
        (
            f"| Preflight Parameter 종류 동일 Group | "
            f"{kpis['preflight_identical_parameter_type_group_count']} / "
            f"{kpis['preflight_parameter_type_consistency_applicable_group_count']} "
            f"({kpis['preflight_parameter_type_consistency_rate_percent']}%; "
            f"전체 Group 대비 {kpis['preflight_parameter_type_consistency_all_group_rate_percent']}%) |"
        ),
        (
            f"| baseline·floor·ceiling 포함 trio | {kpis['representative_role_complete_group_count']} / "
            f"{kpis['representative_role_applicable_group_count']} "
            f"({kpis['representative_role_coverage_rate_percent']}%; "
            f"전체 Group 대비 {kpis['representative_role_complete_all_group_rate_percent']}%) |"
        ),
        (
            f"| Pressure span ≥ 2 Group | {kpis['pressure_span_at_least_two_group_count']} / "
            f"{kpis['selected_group_count']} ({kpis['pressure_span_coverage_rate_percent']}%) |"
        ),
        (
            f"| Parameter portfolio | {kpis['runtime_parameter_portfolio_count']} / "
            f"{kpis['runtime_allowlist_count']} ({kpis['parameter_portfolio_coverage_rate_percent']}%) |"
        ),
        (
            f"| Top-1 Parameter 집중도 | {kpis['top_parameter_name']} "
            f"{kpis['top_parameter_scenario_count']}건 ({kpis['top_parameter_concentration_percent']}%) |"
        ),
        f"| Preflight FAIL | {kpis['preflight_failure_count']} |",
        "",
        "### Read-only KPI 의미 및 해석 방법",
        "",
        "| 구분 | 해석 |",
        "| --- | --- |",
        (
            "| 의미 | Proposal을 생성하지 않고 기존 저장 데이터와 deterministic preflight로 계산한 "
            "cohort 구성·실행 전제·coverage 지표입니다. |"
        ),
        (
            "| `PASS` | 선정·release·구조·preflight 계약이 유효하다는 뜻입니다. 실제 Proposal 성공이나 "
            "제안값 품질 통과를 의미하지 않습니다. |"
        ),
        "| `Covered` | 기존 Proposal 이력으로 현재 중복 write가 막힌 상태이며 실패가 아닙니다. |",
        (
            "| `Coverage limit` | runtime-allowed Parameter 후보가 없어 현재 제안 대상이 아닌 상태이며 "
            "Proposal 실행 실패가 아닙니다. |"
        ),
        (
            "| 읽을 수 있는 범위 | Event/Group 최신성·고유성, runtime capability, 대표 trio 역할·사전 종류 일치, "
            "Parameter portfolio/집중도, 현재 write guard 상태입니다. |"
        ),
        (
            "| 읽을 수 없는 범위 | 실제 Proposal 성공·semantic abstention, 실제 제안 종류, Scenario별 제안값 및 "
            "exact-slot 차이, token·latency입니다. |"
        ),
        (
            "| 실행 간 비교 | 동일 fixture identity, Scenario Lever/Proposal Flow release, context fingerprint를 "
            "확인한 경우에만 회귀 비교합니다. |"
        ),
        "",
        "## Proposal 결과 KPI",
        "",
        "| KPI | 결과 | 분모 / 판정 기준 |",
        "| --- | --- | --- |",
        (
            "| 같은 종류 + Scenario별 다른 제안값 | N/A (`NOT_MEASURED_READ_ONLY`) | "
            "세 Proposal이 모두 성공하고 실제 canonical Parameter 종류 집합이 동일한 Group 중, "
            "동일 Parameter의 전체 proposed-value signature가 2개 이상인 Group 비율 |"
        ),
        (
            "| 같은 종류 + 동일 exact-slot 값 차이 | N/A (`NOT_MEASURED_READ_ONLY`) | "
            "위 분모 중 세 Scenario에 공통 exact model slot이 있는 Group에서 같은 좌표의 값이 다른 Group 비율 |"
        ),
        "",
        "> 이번 수집에서는 Proposal 로직을 실행하지 않았으므로 두 KPI 모두 값을 추정하지 않았습니다.",
        "",
        "## Group별 trio",
        "",
        (
            "| Rank | Group | Event IDs | Event Type | 대표 Scenario IDs | Runtime | "
            "Write eligible / Covered | 종류 동일 | 공통 Parameter |"
        ),
        "| ---: | ---: | --- | --- | --- | ---: | ---: | --- | --- |",
    ]
    for group in report.get("groups") or []:
        scenarios = group["selected_scenarios"]
        snapshots = [scenario.get("collection_snapshot") or {} for scenario in scenarios]
        runtime_count = sum(item.get("runtime_capable") is True for item in snapshots)
        write_count = sum(item.get("current_write_eligible") is True for item in snapshots)
        covered = sum(item.get("current_guard_decision") == "SKIP" for item in snapshots)
        diagnostics = group.get("selection_diagnostics") or {}
        event_ids = ", ".join(str(item) for item in group.get("event_signature") or [])
        event_types = ", ".join(group.get("event_type_codes") or []) or "N/A"
        scenario_ids = ", ".join(str(item["scenario_id"]) for item in scenarios)
        common_parameters = ", ".join(diagnostics.get("common_runtime_parameter_names") or []) or "N/A"
        lines.append(
            f"| {group['recency_rank']} | {group['scenario_group_id']} | {event_ids} | {event_types} | "
            f"{scenario_ids} | {runtime_count}/3 | {write_count}/{covered} | "
            f"{'Y' if diagnostics.get('parameter_sets_identical_in_preflight') else 'N'} | {common_parameters} |",
        )
    lines.extend(
        [
            "",
            "## KPI 개선안",
            "",
            "| 우선순위 | KPI | 정의/산식 | 권고 기준 | 목적 |",
            "| --- | --- | --- | --- | --- |",
            *[
                (
                    f"| {item['priority']} | {item['kpi']} | {item['definition']}<br>"
                    f"`{item['formula']}` | {item['recommended_criterion']} | {item['reason']} |"
                )
                for item in report.get("kpi_recommendations") or []
            ],
            "",
            "## 표 컬럼 설명 (고정)",
            "",
            "| 컬럼 | 의미 |",
            "| --- | --- |",
            "| Rank | Group `mod_dtm DESC`, Group ID DESC 기준 최신성 순위 |",
            "| Group | Scenario Group ID |",
            "| Event IDs | Group에 display_order로 연결된 ordered MI Event ID 조합 |",
            "| Event Type | 연결 Event의 Event Type L2 코드 |",
            "| 대표 Scenario IDs | 고정한 3개 Scenario ID |",
            "| Runtime | 3개 중 v4.1 runtime Parameter 후보가 있는 수 |",
            "| Write eligible / Covered | 현재 신규 Proposal 실행 가능 수 / 기존 Proposal 때문에 guard가 막는 수 |",
            "| 종류 동일 | 3개 runtime canonical Parameter 종류 집합의 완전 동일 여부 |",
            "| 공통 Parameter | 3개 Scenario 모두에 공통인 runtime canonical Parameter 이름 |",
            "| KPI | 측정 지표 이름 |",
            "| 결과 | 실제 측정값 또는 실행 경계에 따른 `N/A` 상태 |",
            "| 분모 / 판정 기준 | KPI 계산 대상 Group과 값 차이 판정 규칙 |",
            "| 구분 | Read-only KPI의 해석 항목 |",
            "| 해석 | 해당 지표가 보장하거나 보장하지 않는 범위 |",
            "",
            "## 해석 주의",
            "",
            "- `Covered`는 실패가 아니라 기존 Proposal 이력으로 중복 write가 금지된 상태입니다.",
            "- `coverage limit`는 runtime-allowed Parameter 후보가 없는 구조적 한계이며 실행 실패와 분리합니다.",
            (
                "- 이번 결과는 read-only 수집·preflight입니다. 같은 종류 + Scenario별 다른 제안값, "
                "exact-slot 차이, semantic abstention, token/latency는 별도 write 승인 실행에서 측정합니다."
            ),
        ],
    )
    return "\n".join(lines)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-groups", type=int, default=50)
    parser.add_argument("--capability-release", default=BASELINE_CAPABILITY_RELEASE)
    parser.add_argument("--dataset-id", default=DEFAULT_DATASET_ID)
    parser.add_argument("--inventory-output", type=Path, required=True)
    parser.add_argument("--preflight-output", type=Path, required=True)
    parser.add_argument("--plan-output", type=Path, required=True)
    parser.add_argument("--testset-output", type=Path, required=True)
    parser.add_argument("--report-json", type=Path, required=True)
    parser.add_argument("--report-markdown", type=Path, required=True)
    return parser


async def _run(args: argparse.Namespace) -> int:
    outputs = OutputPaths(
        inventory=args.inventory_output.resolve(),
        preflight=args.preflight_output.resolve(),
        plan=args.plan_output.resolve(),
        testset=args.testset_output.resolve(),
        report_json=args.report_json.resolve(),
        report_markdown=args.report_markdown.resolve(),
    )
    inventory = discover_inventory(max_groups=args.max_groups)
    _write_new_json(outputs.inventory, inventory)
    if inventory.get("pass") is not True:
        print(
            json.dumps(
                {"status": "FAIL", "stage": "inventory", "checks": inventory.get("checks")},
                ensure_ascii=False,
            ),
        )
        return 1

    preflight = await run_campaign(
        ProposalOnlyOptions(
            execute=False,
            scenario_ids=tuple(int(item) for item in inventory["selected_scenario_ids"]),
            scenario_group_id=None,
            capability_release=args.capability_release,
            evidence_path=outputs.preflight,
        ),
        dependencies=_runtime_dependencies(),
    )
    plan = build_plan(inventory, preflight)
    _write_new_json(outputs.plan, plan)
    if plan.get("pass") is not True:
        print(json.dumps({"status": "FAIL", "stage": "selection", "checks": plan.get("checks")}, ensure_ascii=False))
        return 1

    provisional_report = build_report(
        inventory,
        preflight,
        plan,
        testset_path=outputs.testset,
        testset_sha256="pending",
    )
    testset = build_testset(plan, provisional_report, dataset_id=args.dataset_id)
    validation = validate_testset(plan, testset)
    if validation.get("pass") is not True:
        print(json.dumps({"status": "FAIL", "stage": "fixture-validation", **validation}, ensure_ascii=False))
        return 1
    _write_new_json(outputs.testset, testset)
    testset_sha256 = hashlib.sha256(outputs.testset.read_bytes()).hexdigest()
    report = build_report(
        inventory,
        preflight,
        plan,
        testset_path=outputs.testset,
        testset_sha256=testset_sha256,
    )
    report["fixture_validation"] = validation
    _write_new_json(outputs.report_json, report)
    _write_new_text(outputs.report_markdown, render_markdown(report))
    print(
        json.dumps(
            {
                "status": report["verdict"],
                "groups": report["kpis"]["selected_group_count"],
                "scenarios": report["kpis"]["selected_scenario_count"],
                "testset_sha256": testset_sha256,
                "outputs": _json_safe(asdict(outputs)),
            },
            ensure_ascii=False,
        ),
    )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
