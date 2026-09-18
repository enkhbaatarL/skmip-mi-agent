from __future__ import annotations

# Copyright (c) 2026 SK Innovation E&S.
import argparse
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime
from decimal import Decimal
import hashlib
import json
import logging
from pathlib import Path
import sys
from typing import Any

from sqlalchemy import text


ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from apps.agents.model_parameter_agent.persistence.model_parameter_service import (  # noqa: E402
    ModelParameterService,
)
from apps.agents.model_parameter_agent.utils.parameter_mapping import (  # noqa: E402
    get_parameter_knowledge_base_from_resources,
    match_parameter_candidates,
)
from apps.persistence.model_impact_lever.service import ModelImpactLeverService  # noqa: E402


LOGGER = logging.getLogger("model_parameter_v4_mapping_invariance")
BASECASE_DIR = ROOT_DIR / "apps/agents/model_parameter_agent/resources/basecase"


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Capture SELECT-only v4 runtime and persistence fingerprints before or after a shared v1/v3 mapping change."
        ),
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--compare",
        type=Path,
        help="Optional earlier evidence JSON. All v4 invariants must match exactly.",
    )
    return parser.parse_args(argv)


def _normalize(value: Any) -> Any:  # noqa: ANN401
    if isinstance(value, datetime):
        return value.isoformat(timespec="microseconds")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, bytes):
        return value.hex()
    if isinstance(value, Mapping):
        return {str(key): _normalize(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    if isinstance(value, list | tuple):
        return [_normalize(item) for item in value]
    if hasattr(value, "value"):
        return _normalize(value.value)
    return value


def _digest(value: Any) -> str:  # noqa: ANN401
    payload = json.dumps(
        _normalize(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _fetch_rows(session: Any, query: str) -> list[dict[str, Any]]:  # noqa: ANN401
    return [_normalize(dict(row)) for row in session.execute(text(query)).mappings().all()]


def _database_evidence() -> tuple[dict[str, Any], list[int]]:
    from apps.common.configs.database.sync_database.connection import get_sync_session

    session = get_sync_session()
    try:
        session.execute(text("SET TRANSACTION READ ONLY"))
        master_rows = _fetch_rows(
            session,
            "SELECT * FROM tmm_mi_model_param_m ORDER BY model_param_id",
        )
        lever_rows = _fetch_rows(
            session,
            "SELECT * FROM tmm_mi_model_impact_lever_m ORDER BY impact_lever_id",
        )
        group_rows = _fetch_rows(
            session,
            """
            SELECT *
              FROM tmm_mi_scenario_group_m
             WHERE generation_strategy = 'multi_event_model_lever_dimensions'
             ORDER BY scenario_group_id
            """,
        )
        group_ids = [int(row["scenario_group_id"]) for row in group_rows]
        scenario_rows = _fetch_rows(
            session,
            """
            SELECT s.*
              FROM tmm_mi_scenario_m AS s
              JOIN tmm_mi_scenario_group_m AS g
                ON g.scenario_group_id = s.scenario_group_id
             WHERE g.generation_strategy = 'multi_event_model_lever_dimensions'
             ORDER BY s.scenario_id
            """,
        )
        relation_rows = _fetch_rows(
            session,
            """
            SELECT r.*
              FROM tmm_mi_scenario_group_event_m AS r
              JOIN tmm_mi_scenario_group_m AS g
                ON g.scenario_group_id = r.scenario_group_id
             WHERE g.generation_strategy = 'multi_event_model_lever_dimensions'
             ORDER BY r.scenario_group_event_id
            """,
        )
        proposal_rows = _fetch_rows(
            session,
            """
            SELECT p.*
              FROM tmm_mi_model_param_proposal_m AS p
              JOIN tmm_mi_scenario_group_m AS g
                ON g.scenario_group_id = p.scenario_group_id
             WHERE g.generation_strategy = 'multi_event_model_lever_dimensions'
             ORDER BY p.model_param_proposal_id
            """,
        )
        mapping_summary = {
            str(row["mapping_method"]): int(row["row_count"])
            for row in _fetch_rows(
                session,
                """
                SELECT mapping_method, COUNT(*) AS row_count
                  FROM tmm_mi_model_param_dimension_map
                 GROUP BY mapping_method
                 ORDER BY mapping_method
                """,
            )
        }
        impact_levers, catalog_version, catalog_checksum = ModelImpactLeverService(
            session=session,
        ).load_active_catalog(catalog_version="v4")
        catalog_projection = [lever.model_dump(mode="json") for lever in impact_levers]
        scenario_ids = [int(row["scenario_id"]) for row in scenario_rows]
        return (
            {
                "master": {"count": len(master_rows), "sha256": _digest(master_rows)},
                "impact_levers": {
                    "count": len(lever_rows),
                    "sha256": _digest(lever_rows),
                    "active_catalog_version": catalog_version,
                    "active_catalog_checksum": catalog_checksum,
                    "hydrated_catalog_sha256": _digest(catalog_projection),
                },
                "scenario_groups": {
                    "count": len(group_rows),
                    "ids": group_ids,
                    "sha256": _digest(group_rows),
                },
                "scenarios": {
                    "count": len(scenario_rows),
                    "ids": scenario_ids,
                    "sha256": _digest(scenario_rows),
                },
                "group_event_relations": {
                    "count": len(relation_rows),
                    "sha256": _digest(relation_rows),
                },
                "stored_proposals": {
                    "count": len(proposal_rows),
                    "ids": [int(row["model_param_proposal_id"]) for row in proposal_rows],
                    "sha256": _digest(proposal_rows),
                },
                "shared_mapping_observation": {
                    "count": sum(mapping_summary.values()),
                    "method_counts": mapping_summary,
                },
            },
            scenario_ids,
        )
    finally:
        try:
            session.rollback()
        finally:
            session.close()


def _runtime_evidence(scenario_ids: list[int]) -> dict[str, Any]:
    service = ModelParameterService()
    parameter_rows = service.load_model_parameter_definitions()
    knowledge_base = get_parameter_knowledge_base_from_resources(
        mapping_rows=[],
        parameter_rows=parameter_rows,
        basecase_dir_path=str(BASECASE_DIR),
        allow_empty_mapping_rows=True,
    )
    outcomes: list[dict[str, Any]] = []
    for scenario_id in scenario_ids:
        try:
            context = service.load_context(scenario_id)
            mapping_rules = (context.get("parameter_mapping_resources") or {}).get("mapping_rules") or []
            _assert_v4_mapping_rules_empty(mapping_rules, scenario_id=scenario_id)
            candidates, non_inputs, warnings = match_parameter_candidates(knowledge_base, context)
            outcomes.append(
                {
                    "scenario_id": scenario_id,
                    "status": "loaded",
                    "catalog_version": context.get("impact_catalog_version"),
                    "catalog_checksum": context.get("impact_catalog_checksum"),
                    "executable_binding_occurrences": context.get("executable_binding_occurrences"),
                    "reason_codes": sorted(context.get("candidate_exclusion_reason_codes") or []),
                    "candidates": _normalize(candidates),
                    "non_inputs": _normalize(non_inputs),
                    "warnings": _normalize(warnings),
                    "mapping_rule_count": 0,
                },
            )
        except Exception as exc:
            outcomes.append(
                {
                    "scenario_id": scenario_id,
                    "status": "error",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                },
            )
    return {
        "scenario_count": len(scenario_ids),
        "loaded_count": sum(item["status"] == "loaded" for item in outcomes),
        "error_count": sum(item["status"] == "error" for item in outcomes),
        "outcome_sha256": _digest(outcomes),
        "outcomes": outcomes,
    }


def _assert_v4_mapping_rules_empty(mapping_rules: list[Any], *, scenario_id: int) -> None:
    if mapping_rules:
        message = f"v4 scenario unexpectedly loaded legacy mapping rules: scenario_id={scenario_id}"
        raise RuntimeError(message)


def capture() -> dict[str, Any]:
    database, scenario_ids = _database_evidence()
    runtime = _runtime_evidence(scenario_ids)
    return {
        "evidence_version": "model-parameter-v4-mapping-invariance-v1",
        "captured_at_utc": datetime.now(UTC).isoformat(),
        "v4_invariants": {key: value for key, value in database.items() if key != "shared_mapping_observation"}
        | {"runtime": runtime},
        "shared_mapping_observation": database["shared_mapping_observation"],
    }


def _assert_matches_baseline(actual: Mapping[str, Any], baseline: Mapping[str, Any]) -> None:
    actual_invariants = actual.get("v4_invariants")
    baseline_invariants = baseline.get("v4_invariants")
    if actual_invariants != baseline_invariants:
        message = (
            "v4 invariants changed across the shared v1/v3 mapping operation: "
            f"before_sha256={_digest(baseline_invariants)}, after_sha256={_digest(actual_invariants)}"
        )
        raise RuntimeError(message)


def _load_baseline(path: Path) -> dict[str, Any]:
    baseline = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(baseline, dict):
        message = "baseline evidence root must be a JSON object"
        raise TypeError(message)
    return baseline


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = _parse_args(argv)
    try:
        evidence = capture()
        if args.compare is not None:
            baseline = _load_baseline(args.compare)
            _assert_matches_baseline(evidence, baseline)
        output_path = args.output.resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except Exception:
        LOGGER.exception("v4 mapping-invariance capture failed")
        return 1
    LOGGER.info(
        "v4 mapping-invariance evidence captured: output=%s invariant_sha256=%s mapping=%s",
        args.output,
        _digest(evidence["v4_invariants"]),
        evidence["shared_mapping_observation"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
