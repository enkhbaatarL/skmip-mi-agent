# Copyright (c) 2026 SK Innovation E&S.

"""Create an audited derivative of proposal evidence with missing MI Base traces.

This utility never changes the source evidence and never runs Proposal logic.  It
is intentionally narrow: only structured semantic abstentions that happen after
MI Base preparation may inherit the single identity directly observed elsewhere
in the same sequential campaign.  The inherited rows stay explicitly labelled
as inferred evidence rather than direct runtime observations.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from copy import deepcopy
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any


BACKFILL_KIND = "authorized_inferred_backfill"
EXPECTED_FALLBACK_MODE = "configured_fallback"
SEMANTIC_STAGES = frozenset({"step1_5", "step2", "step3"})


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        message = f"Expected a JSON object: {path}"
        raise TypeError(message)
    return payload


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )


def _trace(attempt: Mapping[str, Any]) -> dict[str, Any] | None:
    for container_name in ("evaluation", "failure_trace"):
        container = attempt.get(container_name)
        if not isinstance(container, Mapping):
            continue
        trace = container.get("trace_mi_base_resource")
        if isinstance(trace, Mapping) and trace:
            return dict(trace)
    return None


def _identity(trace: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "source": trace.get("source"),
        "case_id": trace.get("case_id"),
        "workbook_sha256": trace.get("workbook_sha256"),
    }


def _identity_signature(trace: Mapping[str, Any]) -> str:
    return json.dumps(_identity(trace), ensure_ascii=False, sort_keys=True, default=str)


def _semantic_abstention_backfillable(attempt: Mapping[str, Any]) -> bool:
    semantic = attempt.get("semantic_empty")
    failure_trace = attempt.get("failure_trace")
    stage = semantic.get("stage") if isinstance(semantic, Mapping) else None
    return bool(
        attempt.get("status") == "ABSTAINED"
        and attempt.get("execution_attempt_count") == 1
        and stage in SEMANTIC_STAGES
        and attempt.get("failed_stage") == f"semantic abstention: {stage}"
        and isinstance(semantic, Mapping)
        and semantic.get("structured") is True
        and semantic.get("observability_complete") is True
        and isinstance(failure_trace, Mapping)
        and failure_trace.get("partial_state_captured") is True
        and failure_trace.get("mapping_trace_captured") is True
        and failure_trace.get("observability_complete") is True
        and attempt.get("proposal_persisted") is False
        and not attempt.get("new_proposal_ids")
    )


def _check(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def build_backfilled_evidence(
    evidence: Mapping[str, Any],
    *,
    source_path: str,
    source_sha256: str,
    authorization_note: str,
    expected_attempt_count: int,
    expected_direct_count: int,
    expected_backfill_count: int,
    performed_at: str | None = None,
) -> dict[str, Any]:
    """Return an audited copy after fail-closed backfill validation."""

    attempts = evidence.get("attempts")
    _check(isinstance(attempts, list), "evidence.attempts must be a list")
    attempt_rows = [item for item in attempts if isinstance(item, Mapping)]
    _check(len(attempt_rows) == len(attempts), "every attempt must be a JSON object")
    scenario_ids = [int(item["scenario_id"]) for item in attempt_rows]
    _check(len(scenario_ids) == len(set(scenario_ids)), "Scenario attempt IDs must be unique")
    _check(len(attempt_rows) == expected_attempt_count, "unexpected attempt count")
    _check(evidence.get("runner") == "model_parameter_proposal_only", "unexpected runner")
    _check(evidence.get("mode") == "execute", "source evidence is not an execute campaign")
    _check(evidence.get("status") == "REVIEW", "source campaign must be REVIEW")

    manifest = evidence.get("manifest")
    manifest = manifest if isinstance(manifest, Mapping) else {}
    fallback_policy = manifest.get("mi_base_fallback_policy")
    fallback_policy = fallback_policy if isinstance(fallback_policy, Mapping) else {}
    _check(
        manifest.get("required_mi_base_fallback_mode") == EXPECTED_FALLBACK_MODE,
        "required MI Base fallback mode is not configured_fallback",
    )
    _check(
        fallback_policy.get("active_case_unavailable_mode") == EXPECTED_FALLBACK_MODE,
        "active MI Base fallback policy is not configured_fallback",
    )

    safety = evidence.get("safety")
    safety = safety if isinstance(safety, Mapping) else {}
    _check(safety.get("sequential") is True, "campaign must be sequential")
    _check(safety.get("max_attempts_per_scenario") == 1, "campaign must permit one attempt per Scenario")
    _check(safety.get("automatic_retry") is False, "automatic retry must be disabled")
    _check(safety.get("confirmation_invoked") is False, "confirmation must not have been invoked")
    _check(safety.get("callback_invoked") is False, "callback must not have been invoked")

    directly_observed = [item for item in attempt_rows if _trace(item) is not None]
    missing = [item for item in attempt_rows if _trace(item) is None]
    _check(len(directly_observed) == expected_direct_count, "unexpected directly observed trace count")
    _check(len(missing) == expected_backfill_count, "unexpected missing trace count")
    _check(bool(directly_observed), "at least one direct MI Base trace is required")
    _check(bool(missing), "there are no missing MI Base traces to backfill")
    _check(
        all(_semantic_abstention_backfillable(item) for item in missing),
        "missing traces include a non-backfillable attempt",
    )

    observed_traces = [_trace(item) for item in directly_observed]
    identity_signatures = {
        _identity_signature(trace)
        for trace in observed_traces
        if isinstance(trace, Mapping)
    }
    _check(len(identity_signatures) == 1, "direct MI Base identities are not identical")
    observed_identity = _identity(next(trace for trace in observed_traces if trace is not None))
    _check(
        observed_identity.get("source") == EXPECTED_FALLBACK_MODE,
        "direct MI Base trace source is not configured_fallback",
    )
    _check(isinstance(observed_identity.get("case_id"), int), "direct MI Base trace lacks case_id")
    workbook_sha256 = observed_identity.get("workbook_sha256")
    _check(
        isinstance(workbook_sha256, Mapping)
        and set(workbook_sha256) == {"demand", "supply", "trade"}
        and all(isinstance(value, str) and len(value) == 64 for value in workbook_sha256.values()),
        "direct MI Base trace lacks the three workbook SHA-256 values",
    )

    backfilled = deepcopy(dict(evidence))
    backfilled_attempts = backfilled["attempts"]
    backfilled_ids = {int(item["scenario_id"]) for item in missing}
    provenance = {
        "kind": BACKFILL_KIND,
        "directly_observed": False,
        "authorization_note": authorization_note,
        "source_evidence_sha256": source_sha256,
        "basis": (
            "same sequential execute campaign; MI Base preparation precedes the structured "
            "Step1.5/2/3 semantic abstention; all direct traces share one configured_fallback identity"
        ),
    }
    for attempt in backfilled_attempts:
        if int(attempt["scenario_id"]) not in backfilled_ids:
            continue
        trace = {**deepcopy(observed_identity), "evidence_provenance": deepcopy(provenance)}
        attempt["failure_trace"]["trace_mi_base_resource"] = trace

    performed_at_value = performed_at or _now()
    preconditions = {
        "single_source_execute_campaign": True,
        "sequential_one_attempt_no_automatic_retry": True,
        "required_and_active_fallback_mode_configured_fallback": True,
        "direct_identity_unique_and_complete": True,
        "targets_are_structured_post_resource_semantic_abstentions": True,
        "targets_have_no_persisted_proposal": True,
        "confirmation_and_callback_not_invoked": True,
        "attempt_scope_unchanged": True,
    }
    backfilled["mi_base_trace_backfill_audit"] = {
        "schema_version": 1,
        "status": "PASS",
        "performed_at": performed_at_value,
        "authorization": {
            "explicit": True,
            "note": authorization_note,
        },
        "method": BACKFILL_KIND,
        "source_evidence": {
            "path": source_path,
            "sha256": source_sha256,
        },
        "fallback_mode": EXPECTED_FALLBACK_MODE,
        "inferred_identity": deepcopy(observed_identity),
        "counts": {
            "attempts": len(attempt_rows),
            "directly_observed": len(directly_observed),
            "backfilled": len(missing),
            "effective": len(attempt_rows),
        },
        "scenario_ids": {
            "directly_observed": sorted(int(item["scenario_id"]) for item in directly_observed),
            "backfilled": sorted(backfilled_ids),
        },
        "preconditions": preconditions,
        "original_evidence_overwritten": False,
        "proposal_logic_reexecuted": False,
        "application_data_mutated": False,
        "limitation": (
            "Backfilled identities are audit-supported inference, not direct per-attempt runtime observation."
        ),
    }
    return backfilled


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-source-sha256", required=True)
    parser.add_argument("--expected-attempt-count", type=int, required=True)
    parser.add_argument("--expected-direct-count", type=int, required=True)
    parser.add_argument("--expected-backfill-count", type=int, required=True)
    parser.add_argument("--authorization-note", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    source_path = args.source.resolve()
    output_path = args.output.resolve()
    if source_path == output_path:
        message = "Source evidence must not be overwritten"
        raise ValueError(message)
    if output_path.exists():
        message = f"Refusing to overwrite derived evidence: {output_path}"
        raise FileExistsError(message)
    source_bytes = source_path.read_bytes()
    source_sha256 = hashlib.sha256(source_bytes).hexdigest()
    if source_sha256 != args.expected_source_sha256:
        message = (
            "Source evidence SHA-256 mismatch: "
            f"actual={source_sha256}, expected={args.expected_source_sha256}"
        )
        raise ValueError(message)
    backfilled = build_backfilled_evidence(
        _read_json(source_path),
        source_path=str(source_path),
        source_sha256=source_sha256,
        authorization_note=str(args.authorization_note).strip(),
        expected_attempt_count=args.expected_attempt_count,
        expected_direct_count=args.expected_direct_count,
        expected_backfill_count=args.expected_backfill_count,
    )
    _write_json(output_path, backfilled)
    print(
        json.dumps(
            {
                "output": str(output_path),
                "source_sha256": source_sha256,
                "audit": backfilled["mi_base_trace_backfill_audit"],
            },
            ensure_ascii=False,
        ),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
