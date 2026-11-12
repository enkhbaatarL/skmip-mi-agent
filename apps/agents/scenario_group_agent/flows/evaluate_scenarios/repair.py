from __future__ import annotations

# ruff: noqa: CPY001
from copy import deepcopy
import hashlib
import json
import re
from types import SimpleNamespace
from typing import Any

from apps.agents.scenario_group_agent.flows.validate_scenarios.v4_validation import (
    analyze_v4_validation_request,
    rebase_v4_pressure_bands,
    validate_v4_pressure_aggregate,
)
from apps.agents.scenario_group_agent.prompts.scenario_quality_repair import QualityRepairPlan, QualityRepairStrategies
from apps.agents.scenario_group_agent.utils.pressure_band import uses_unique_strong_bands
from apps.persistence.scenario_group_operation.schema import ValidationCheckPayload
from apps.persistence.scenario_quality_evaluation.schema import ScenarioQualityJudgment


_ALLOWED_PATH = re.compile(
    r"/(?:group/(?:title|summary|description|dimension_definitions/[0-9]+/"
    r"(?:label|description|rationale|dimension_type|values/[0-9]+/(?:label|assumption_rationale)))"
    r"|scenarios/[0-9]+/(?:title|narrative|global_pressure_rationale|dimension_values/[^/~]+))",
)


def snapshot_hash(snapshot: dict[str, Any]) -> str:
    data = {key: value for key, value in snapshot.items() if key != "sourceOperationId"}
    return hashlib.sha256(
        json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"),
    ).hexdigest()


def build_repaired_snapshot(  # noqa: C901
    snapshot: dict[str, Any],
    judgment: ScenarioQualityJudgment,
    plan: QualityRepairPlan,
    diagnostics: dict[str, Any],
) -> tuple[dict[str, Any], list[ValidationCheckPayload]]:
    """Apply allowlisted patches in memory, then run the existing v4 structural checks."""
    from apps.agents.scenario_group_agent.persistence.scenario_service import ScenarioService

    candidate = deepcopy(snapshot)
    items = {item.judge_id: item for item in judgment.items}
    seen: set[str] = set()
    changed = False
    for change in plan.changes:
        item = items.get(change.judge_id)
        if item is None or item.verdict == "PASS" or change.violation_index >= len(item.violations):
            msg = "Repair must reference an existing WARN/FAIL violation"
            raise ValueError(msg)
        issue = item.violations[change.violation_index]
        if not _ALLOWED_PATH.fullmatch(change.path) or change.path in seen:
            msg = "Repair path is forbidden or duplicated"
            raise ValueError(msg)
        seen.add(change.path)
        tokens = change.path[1:].split("/")
        if tokens[0] == "scenarios":
            target = candidate["scenarios"][int(tokens[1])]
            if target["scenario_id"] not in issue.scenario_ids:
                msg = "Repair targets an unrelated scenario"
                raise ValueError(msg)
        elif not issue.evidence_path.startswith("/group/"):
            msg = "Group repair requires group-level evidence"
            raise ValueError(msg)
        target = candidate
        for token in tokens[:-1]:
            target = target[int(token)] if isinstance(target, list) else target[token]
        key = tokens[-1]
        if key not in target:
            msg = "Repair cannot add fields"
            raise ValueError(msg)
        if key == "title" and len(change.value) > 255:
            msg = "Repair title exceeds storage limit"
            raise ValueError(msg)
        changed |= target[key] != change.value
        target[key] = change.value
    if not changed:
        msg = "Repair produced no changes"
        raise ValueError(msg)

    group = candidate["group"]
    definitions = group["dimension_definitions"]
    selected = group["dimension_selected"]
    # Reuse the normal closed-enum, duplicate/title, diversity and contrast checks.
    analysis = analyze_v4_validation_request(
        request_table={
            "headers": [{"key": key} for key in selected],
            "rows": [
                {
                    "scenarioId": row["scenario_id"],
                    "displayOrder": row["display_order"],
                    "title": row["title"],
                    "cells": row["dimension_values"],
                }
                for row in candidate["scenarios"]
            ],
        },
        persisted_scenarios=snapshot["scenarios"],
        dimension_definitions=definitions,
        generation_diagnostics=diagnostics,
        stored_header_order=selected,
    )
    probabilities = {row["scenario_id"]: float(row["probability_score"] or 0) for row in candidate["scenarios"]}
    baseline_key, bands = rebase_v4_pressure_bands(
        rows=analysis.canonical_rows,
        dimension_definitions=definitions,
        probability_scores={row.client_row_key: probabilities[row.scenario_id] for row in analysis.canonical_rows},
        unique_strong=uses_unique_strong_bands(diagnostics),
    )
    checks = [
        *analysis.checks,
        *validate_v4_pressure_aggregate(
            rows=analysis.canonical_rows,
            dimension_definitions=definitions,
            pressure_bands=bands,
            baseline_row_key=baseline_key,
        ),
    ]
    if any(check.blocking and check.status == "FAIL" for check in checks):
        msg = "Repair validation blocked: " + "; ".join(
            check.detail for check in checks if check.blocking and check.status == "FAIL"
        )
        raise ValueError(msg)
    models = [SimpleNamespace(**row) for row in candidate["scenarios"]]
    ScenarioService()._apply_v4_baseline_and_roles(  # noqa: SLF001
        models,
        definitions,
        user_id=0,
        generation_diagnostics=diagnostics,
    )
    for row, model in zip(candidate["scenarios"], models, strict=True):
        if "description" in row:
            row["description"] = row["narrative"]
        for field in ("global_pressure_band", "baseline_yn", "scenario_role"):
            row[field] = getattr(model, field)
    return candidate, checks


def validate_repair_strategies(
    snapshot: dict[str, Any], judgment: ScenarioQualityJudgment, strategies: QualityRepairStrategies,
) -> None:
    """Check plans against the same scope as actual patches before comparing them."""
    items = {item.judge_id: item for item in judgment.items}
    for strategy in strategies.candidates:
        seen = set()
        for target in strategy.targets:
            item = items.get(target.judge_id)
            if item is None or item.verdict == "PASS" or target.violation_index >= len(item.violations):
                msg = "Plan must reference an existing WARN/FAIL violation"
                raise ValueError(msg)
            if not _ALLOWED_PATH.fullmatch(target.path) or target.path in seen:
                msg = "Plan path is forbidden or duplicated"
                raise ValueError(msg)
            seen.add(target.path)
            issue = item.violations[target.violation_index]
            tokens = target.path[1:].split("/")
            if tokens[0] == "scenarios":
                if snapshot["scenarios"][int(tokens[1])]["scenario_id"] not in issue.scenario_ids:
                    msg = "Plan targets an unrelated scenario"
                    raise ValueError(msg)
            elif not issue.evidence_path.startswith("/group/"):
                msg = "Group plan requires group-level evidence"
                raise ValueError(msg)
            value = snapshot
            for token in tokens:
                value = value[int(token)] if isinstance(value, list) else value[token]
