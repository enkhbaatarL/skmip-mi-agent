# Copyright (c) 2026 SK Innovation E&S.
# ruff: noqa: ANN401, C901, E402

"""Discover uncovered v4 scenarios and optionally run proposals once.

The default mode is DB read-only. ``--execute`` is intentionally narrower than
the API/background workflows: it calls ``_evaluate_scenario`` directly, never
calls confirmation or callback code, and never retries a write-producing
attempt. The uncovered-only guard cannot be bypassed.
"""

from __future__ import annotations

import argparse
import asyncio
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
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

from apps.agents.model_parameter_agent.persistence.model_parameter_service import (
    ModelParameterService,
)
from apps.agents.model_parameter_agent.utils.proposal_capabilities import (
    load_proposal_capability_contract,
)
from apps.agents.model_parameter_agent.utils.resource_manifest import (
    PACKAGE_RESOURCE_DIR,
    load_model_parameter_resource_manifest,
)
from apps.agents.model_parameter_agent.utils.resource_runtime import (
    get_registered_model_parameter_resource_paths,
)
from apps.agents.model_parameter_agent.utils.workbook_contract import (
    DEFAULT_WORKBOOK_CONTRACT_PATH,
    load_workbook_contract,
    validate_workbook_hashes,
)
from apps.common.configs.config import CONFIG_FILE_PATH, get_settings
from apps.common.configs.database.sync_database.connection import get_sync_session
from apps.common.logging.logger_config import logger
from apps.persistence.model_parameter.repository import ModelParameterRepository
from apps.persistence.scenario.repository import ScenarioRepository
from apps.persistence.scenario_group.repository import ScenarioGroupRepository
from tests.manual.model_parameter_agent.evaluate_multi_event_quality import (
    _schema_preflight,
    build_v4_scenario_evidence,
)
from tests.manual.model_parameter_agent.evaluate_proposals import (
    _ensure_model_parameter_test_resource_runtime,
    _evaluate_scenario,
    _failure_trace_from_exception,
)
from tests.manual.model_parameter_agent.runner_common import (
    fetch_proposal_db_row,
    json_safe,
    proposal_id,
)


V4_API_VERSION = "v4"
V4_STRATEGY = "multi_event_model_lever_dimensions"
EVIDENCE_SCHEMA_VERSION = 3
UNCOVERED_POLICY_VERSION = "uncovered-only-v1"
BASELINE_CAPABILITY_RELEASE = "extend7-v4"
EXPECTED_0032_CATALOG_CHECKSUM = "b9d8c051872b39903cc3b4d2f19cd00570156eecd82295f0d2b02fd042c4000b"
EXPECTED_NEW_BC_V4_CONTRACT_SHA256 = "8f976303c9404b03945dafb9b7b871b6ac6eb6335d5e5b084ad9d7939f842a2d"
EXPECTED_EXTEND7_V4_CONTRACT_SHA256 = "6eca2fe50b10ed39a801d4071b0ac646c41d554e8d92c3bc932a4ddc8cf5f0a7"
EXPECTED_RESOURCE_SEMANTIC_SCHEMA_HASH = "cf174dd6e9cae7ee464563d996e503ce1adccad44878fc644b86d19c63f43952"
EXPECTED_PACKAGED_RESOURCE_FINGERPRINT = "b1686b6308e8ba094277417bb79bfd85bfe05bb8013c20ed20545b9b2f9c1a44"
EXPECTED_WORKBOOK_PARAMETER_NAMES = frozenset(
    {
        "GDP",
        "PMI",
        "PowerMix",
        "Temperature",
        "LiqUtilAdjustment",
        "PipelineAdjustment",
        "SupplyDisruption",
    },
)
EXPECTED_EXTEND7_ALLOWLIST = frozenset(
    {
        *EXPECTED_WORKBOOK_PARAMETER_NAMES,
        "PipelineAdjustment",
        "SupplyDisruption",
    },
)
RUNTIME_PROPOSAL_CAPABILITY_NAMES = frozenset(load_proposal_capability_contract().by_name)
CAPABILITY_RELEASES: dict[str, dict[str, Any]] = {
    BASELINE_CAPABILITY_RELEASE: {
        "catalog_version": V4_API_VERSION,
        "catalog_checksum": EXPECTED_0032_CATALOG_CHECKSUM,
        "runtime_allowlist": EXPECTED_EXTEND7_ALLOWLIST,
        "proposal_capability_release_id": "extend7-v4",
        "proposal_capability_sha256": EXPECTED_EXTEND7_V4_CONTRACT_SHA256,
        "workbook_parameter_names": EXPECTED_WORKBOOK_PARAMETER_NAMES,
        "resource_release_id": "new-bc-v4",
        "workbook_contract_sha256": EXPECTED_NEW_BC_V4_CONTRACT_SHA256,
        "resource_semantic_schema_hash": EXPECTED_RESOURCE_SEMANTIC_SCHEMA_HASH,
        "effective_resource_fingerprint": EXPECTED_PACKAGED_RESOURCE_FINGERPRINT,
        "uncovered_policy_version": UNCOVERED_POLICY_VERSION,
    },
}
DEFAULT_EVIDENCE_DIR = ROOT_DIR / "tests" / "reports" / "model_parameter_agent"
ELIGIBLE_SCENARIO_STATUSES = frozenset({"created", "realized"})
ELIGIBLE_GROUP_STATUSES = frozenset({"created", "realized"})
ELIGIBLE_GROUP_STAGE = "completed"
BLOCKING_PROPOSAL_STATUSES = frozenset({"PROCESSING", "PROPOSED", "CONFIRMED"})
KNOWN_PROPOSAL_STATUSES = frozenset({*BLOCKING_PROPOSAL_STATUSES, "ABSTAINED", "FAILED"})

_SECRET_PATTERNS = (
    re.compile(
        r"(?i)(password|passwd|pwd|token|api[_-]?key|authorization|secret)"
        r"(\s*[=:]\s*)([^\s,;]+)",
    ),
    re.compile(r"(?i)([a-z][a-z0-9+.-]*://[^:/@\s]+):([^@\s]+)@"),
    re.compile(r"(?i)(bearer\s+)([a-z0-9._~+/-]+=*)"),
)
_OMITTED_KEYS = {
    "access_key",
    "access_key_id",
    "access_token",
    "api_key",
    "authorization",
    "client_secret",
    "context",
    "cookie",
    "messages",
    "password",
    "prompt",
    "refresh_token",
    "scenario_context",
    "secret",
    "secret_access_key",
    "token",
}
_PROPOSAL_ROW_FIELDS = (
    "model_param_proposal_id",
    "scenario_id",
    "scenario_group_id",
    "mi_event_id",
    "request_usr_id",
    "status",
    "callback_status",
    "proposal_completed_dtm",
    "callback_sent_dtm",
    "confirmed_dtm",
    "error_code",
    "error_message",
    "proposal_parameters",
    "confirmation_parameters",
    "mod_usr_logn_id",
    "crt_dtm",
    "mod_dtm",
    "fetch_status",
)


@dataclass(frozen=True)
class ProposalOnlyOptions:
    execute: bool
    scenario_ids: tuple[int, ...]
    scenario_group_id: int | None
    capability_release: str
    evidence_path: Path


@dataclass(frozen=True)
class RunnerDependencies:
    load_context: Callable[[int], Mapping[str, Any]]
    snapshot_proposal_rows: Callable[[int, Sequence[int]], tuple[dict[str, Any], ...]]
    evaluate_scenario: Callable[[int], Awaitable[dict[str, Any]]]
    fetch_proposal: Callable[[int | None], dict[str, Any]]
    failure_trace: Callable[[BaseException], Mapping[str, Any]]
    discover_scenario_ids: Callable[[int], tuple[int, ...]] = lambda _scenario_group_id: ()
    build_quality_evidence: Callable[[int, Mapping[str, Any]], Any] | None = None
    prepare_resources: Callable[[], Awaitable[Any]] | None = None
    schema_preflight: Callable[[], Any] | None = None
    evaluate_scenario_with_context: Callable[[int, Mapping[str, Any]], Awaitable[dict[str, Any]]] | None = None
    require_registered_resources: bool = False


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Discover uncovered v4 scenarios and optionally run each proposal exactly once "
            "without confirmation/callback."
        ),
    )
    scope = parser.add_mutually_exclusive_group(required=True)
    scope.add_argument(
        "--scenario-group-id",
        type=int,
        help="Discover scenarios inside one explicit Scenario Group.",
    )
    scope.add_argument(
        "--scenario-id",
        action="append",
        dest="scenario_ids",
        type=int,
        default=[],
        help="Explicit Scenario ID; repeat for additional scenarios.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Write one proposal for each eligible uncovered scenario; omitted means read-only discovery.",
    )
    parser.add_argument(
        "--capability-release",
        required=True,
        choices=tuple(sorted(CAPABILITY_RELEASES)),
        help="Approved capability release contract; unknown labels are rejected.",
    )
    parser.add_argument("--evidence-path", type=Path)
    return parser


def _default_evidence_path(started_at: datetime) -> Path:
    timestamp = started_at.strftime("%Y%m%d_%H%M%S_%f")
    return DEFAULT_EVIDENCE_DIR / f"model_parameter_proposal_only_{timestamp}.json"


def _options_from_args(args: argparse.Namespace, started_at: datetime) -> ProposalOnlyOptions:
    raw_path = args.evidence_path or _default_evidence_path(started_at)
    return ProposalOnlyOptions(
        execute=bool(args.execute),
        scenario_ids=tuple(args.scenario_ids),
        scenario_group_id=args.scenario_group_id,
        capability_release=str(args.capability_release or "").strip(),
        evidence_path=raw_path.expanduser().resolve(),
    )


def _validate_options(options: ProposalOnlyOptions) -> None:
    has_scenario_ids = bool(options.scenario_ids)
    has_group_id = options.scenario_group_id is not None
    if has_scenario_ids == has_group_id:
        message = "exactly one explicit scope is required: --scenario-group-id or --scenario-id"
        raise ValueError(message)
    if options.capability_release not in CAPABILITY_RELEASES:
        message = f"unsupported --capability-release: {options.capability_release!r}"
        raise ValueError(message)
    invalid_ids = [scenario_id for scenario_id in options.scenario_ids if scenario_id <= 0]
    if invalid_ids:
        message = f"--scenario-id must be positive: {invalid_ids}"
        raise ValueError(message)
    if options.scenario_group_id is not None and options.scenario_group_id <= 0:
        message = f"--scenario-group-id must be positive: {options.scenario_group_id}"
        raise ValueError(message)
    duplicate_ids = sorted(
        {scenario_id for scenario_id in options.scenario_ids if options.scenario_ids.count(scenario_id) > 1},
    )
    if duplicate_ids:
        message = f"duplicate --scenario-id values are not allowed: {duplicate_ids}"
        raise ValueError(message)


def _redact_text(value: object) -> str:
    text = str(value)
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub(r"\1\2<redacted>", text) if pattern.groups == 3 else pattern.sub(r"\1<redacted>", text)
    return text


def _sanitize_json(value: Any) -> Any:
    safe = json_safe(value)
    if isinstance(safe, Mapping):
        sanitized: dict[str, Any] = {}
        for raw_key, item in safe.items():
            key = str(raw_key)
            normalized_key = key.casefold().replace("-", "_")
            if (
                normalized_key in _OMITTED_KEYS
                or normalized_key.endswith(("_context", "_messages", "_secret"))
                or "prompt" in normalized_key
            ):
                continue
            sanitized[key] = _sanitize_json(item)
        return sanitized
    if isinstance(safe, list | tuple):
        return [_sanitize_json(item) for item in safe]
    if isinstance(safe, str):
        return _redact_text(safe)
    return safe


def _reserve_evidence_path(path: Path, initial_evidence: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as evidence_file:
        json.dump(
            _sanitize_json(initial_evidence),
            evidence_file,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        evidence_file.write("\n")


def _write_evidence(path: Path, evidence: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(
            _sanitize_json(evidence),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _discover_scenario_ids(scenario_group_id: int) -> tuple[int, ...]:
    session = get_sync_session()
    try:
        group = ScenarioGroupRepository(session=session).fetch_by_id(scenario_group_id)
        if group is None:
            return ()
        return tuple(
            int(scenario.scenario_id)
            for scenario in ScenarioRepository(session=session).fetch_models_by_group_id(
                scenario_group_id,
            )
        )
    finally:
        session.close()


def _snapshot_proposal_rows(
    scenario_group_id: int,
    scenario_ids: Sequence[int],
) -> tuple[dict[str, Any], ...]:
    session = get_sync_session()
    try:
        return tuple(
            ModelParameterRepository(session=session).fetch_proposal_guard_rows(
                scenario_group_id=scenario_group_id,
                scenario_ids=list(scenario_ids),
            ),
        )
    finally:
        session.close()


def _stable_file_sha256(path: Path) -> str:
    before = path.stat()
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    after = path.stat()
    before_signature = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    after_signature = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    if before_signature != after_signature:
        message = f"resource file changed while hashing: {path.name}"
        raise RuntimeError(message)
    return digest.hexdigest()


def _effective_resource_fingerprint(
    *,
    resource_root: Path,
    basecase_dir: Path | None = None,
    lut_root: Path | None = None,
    resource_manifest: Any,
    lut_enabled: bool,
) -> str:
    resolved_root = resource_root.resolve(strict=True)
    resolved_basecase_dir = (basecase_dir or resolved_root / "basecase").resolve(strict=True)
    resolved_lut_root = (lut_root or resolved_root / "lut").resolve(strict=True)
    digest = hashlib.sha256()
    selected_by_target = {
        item.target_relative_path: item for item in resource_manifest.selected_files(lut_enabled=lut_enabled)
    }
    for target_relative_path in sorted(selected_by_target):
        relative_path = Path(target_relative_path)
        if relative_path.parts and relative_path.parts[0] == "basecase":
            allowed_root = resolved_basecase_dir
            relative_path = Path(*relative_path.parts[1:])
        elif relative_path.parts and relative_path.parts[0] == "lut":
            allowed_root = resolved_lut_root
            relative_path = Path(*relative_path.parts[1:])
        else:
            allowed_root = resolved_root
        path = (allowed_root / relative_path).resolve(strict=True)
        if not path.is_relative_to(allowed_root):
            message = f"resource path escapes the selected runtime root: {target_relative_path}"
            raise RuntimeError(message)
        digest.update(target_relative_path.encode("utf-8"))
        digest.update(_stable_file_sha256(path).encode("ascii"))
    return digest.hexdigest()


def _resource_manifest() -> dict[str, Any]:
    registered = get_registered_model_parameter_resource_paths()
    settings = get_settings()
    declared_resources = load_model_parameter_resource_manifest(
        settings.model_parameter_resources,
        source_path=CONFIG_FILE_PATH,
    )
    contract_path = (
        registered.workbook_contract_path
        if registered is not None and registered.workbook_contract_path is not None
        else DEFAULT_WORKBOOK_CONTRACT_PATH
    )
    contract = (
        registered.workbook_contract
        if registered is not None and registered.workbook_contract is not None
        else load_workbook_contract(contract_path)
    )
    validate_workbook_hashes(contract)
    resource_root = registered.root if registered is not None else PACKAGE_RESOURCE_DIR
    effective_resource_fingerprint = _effective_resource_fingerprint(
        resource_root=resource_root,
        basecase_dir=registered.basecase_dir if registered is not None else None,
        lut_root=registered.lut_root if registered is not None else None,
        resource_manifest=declared_resources,
        lut_enabled=settings.model_parameter_lut_enabled,
    )
    manifest = {
        "release_id": contract.release_id,
        "contract_sha256": hashlib.sha256(contract_path.read_bytes()).hexdigest(),
        "contract_parameter_names": sorted(contract.parameters),
        "proposal_capability_release_id": declared_resources.proposal_capability_contract.release_id,
        "proposal_capability_sha256": declared_resources.proposal_capability_contract_sha256,
        "proposal_capability_parameter_names": sorted(
            declared_resources.proposal_capability_contract.by_name,
        ),
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "runtime_registered": registered is not None,
        "runtime_source": registered.source if registered is not None else "not_registered",
        "declared_semantic_schema_hash": declared_resources.semantic_schema_hash,
        "semantic_schema_hash": registered.semantic_schema_hash if registered is not None else None,
        "resource_config_fingerprint": (registered.resource_config_fingerprint if registered is not None else None),
        "resource_fingerprint": registered.resource_fingerprint if registered is not None else None,
        "fallback_reason": registered.fallback_reason if registered is not None else None,
        "effective_resource_fingerprint": effective_resource_fingerprint,
    }
    manifest["identity_fingerprint"] = _semantic_sha256(manifest)
    return manifest


def _capability_contract(capability_release: str) -> Mapping[str, Any]:
    contract = CAPABILITY_RELEASES.get(capability_release)
    if contract is None:
        message = f"unsupported capability release: {capability_release!r}"
        raise ValueError(message)
    return contract


def _release_contract_errors(
    *,
    capability_release: str,
    resource_manifest: Mapping[str, Any],
    require_registered_resources: bool,
) -> list[str]:
    release = _capability_contract(capability_release)
    errors: list[str] = []
    expected_allowlist = frozenset(str(item) for item in release["runtime_allowlist"])
    if expected_allowlist != RUNTIME_PROPOSAL_CAPABILITY_NAMES:
        errors.append(
            "runtime capability drifted from the approved capability release: "
            f"expected={sorted(expected_allowlist)}, actual={sorted(RUNTIME_PROPOSAL_CAPABILITY_NAMES)}",
        )
    if resource_manifest.get("release_id") != release["resource_release_id"]:
        errors.append(
            "resource release does not match the approved capability release: "
            f"expected={release['resource_release_id']!r}, actual={resource_manifest.get('release_id')!r}",
        )
    expected_workbook_names = set(release["workbook_parameter_names"])
    if set(resource_manifest.get("contract_parameter_names") or ()) != expected_workbook_names:
        errors.append(
            "Workbook contract parameters do not match the approved capability release: "
            f"expected={sorted(expected_workbook_names)}, "
            f"actual={sorted(resource_manifest.get('contract_parameter_names') or ())}",
        )
    if resource_manifest.get("proposal_capability_release_id") != release["proposal_capability_release_id"]:
        errors.append("proposal capability release ID does not match the approved capability release")
    if resource_manifest.get("proposal_capability_sha256") != release["proposal_capability_sha256"]:
        errors.append("proposal capability content drifted from the approved capability release")
    if set(resource_manifest.get("proposal_capability_parameter_names") or ()) != expected_allowlist:
        errors.append("proposal capability parameters do not match the approved capability release")
    expected_contract_sha256 = str(release["workbook_contract_sha256"])
    if resource_manifest.get("contract_sha256") != expected_contract_sha256:
        errors.append(
            "Workbook contract content drifted from the approved capability release: "
            f"expected={expected_contract_sha256}, actual={resource_manifest.get('contract_sha256')}",
        )
    expected_semantic_schema_hash = str(release["resource_semantic_schema_hash"])
    if resource_manifest.get("declared_semantic_schema_hash") != expected_semantic_schema_hash:
        errors.append(
            "resource semantic schema drifted from the approved capability release: "
            f"expected={expected_semantic_schema_hash}, "
            f"actual={resource_manifest.get('declared_semantic_schema_hash')}",
        )
    expected_resource_fingerprint = str(release["effective_resource_fingerprint"])
    if resource_manifest.get("effective_resource_fingerprint") != expected_resource_fingerprint:
        errors.append(
            "effective resource content drifted from the approved capability release: "
            f"expected={expected_resource_fingerprint}, "
            f"actual={resource_manifest.get('effective_resource_fingerprint')}",
        )
    if require_registered_resources:
        if resource_manifest.get("runtime_registered") is not True:
            errors.append("execute mode requires a registered Model Parameter resource runtime")
        if resource_manifest.get("runtime_source") not in {"object_storage", "packaged"}:
            errors.append(
                f"execute mode resource source is invalid: {resource_manifest.get('runtime_source')!r}",
            )
        if not resource_manifest.get("semantic_schema_hash"):
            errors.append("execute mode resource semantic schema hash is missing")
        elif resource_manifest.get("semantic_schema_hash") != expected_semantic_schema_hash:
            errors.append(
                "registered resource semantic schema does not match the approved capability release: "
                f"expected={expected_semantic_schema_hash}, "
                f"actual={resource_manifest.get('semantic_schema_hash')}",
            )
        object_storage_fingerprint_missing = resource_manifest.get(
            "runtime_source",
        ) == "object_storage" and not resource_manifest.get("resource_fingerprint")
        if object_storage_fingerprint_missing:
            errors.append("object-storage resource fingerprint is missing")
        registered_fingerprint = resource_manifest.get("resource_fingerprint")
        if registered_fingerprint and registered_fingerprint != expected_resource_fingerprint:
            errors.append(
                "registered resource fingerprint does not match the approved capability release: "
                f"expected={expected_resource_fingerprint}, actual={registered_fingerprint}",
            )
    return errors


async def _evaluate_scenario_with_frozen_context(
    scenario_id: int,
    scenario_context: Mapping[str, Any],
) -> dict[str, Any]:
    return await _evaluate_scenario(
        scenario_id,
        expected_scenario_context=scenario_context,
        require_pre_persistence_quality_pass=True,
        allowed_parameter_names=EXPECTED_EXTEND7_ALLOWLIST,
    )


def _runtime_dependencies() -> RunnerDependencies:
    service = ModelParameterService()
    return RunnerDependencies(
        load_context=service.load_context,
        snapshot_proposal_rows=_snapshot_proposal_rows,
        evaluate_scenario=_evaluate_scenario,
        fetch_proposal=fetch_proposal_db_row,
        failure_trace=_failure_trace_from_exception,
        discover_scenario_ids=_discover_scenario_ids,
        build_quality_evidence=build_v4_scenario_evidence,
        prepare_resources=_ensure_model_parameter_test_resource_runtime,
        schema_preflight=_schema_preflight,
        evaluate_scenario_with_context=_evaluate_scenario_with_frozen_context,
        require_registered_resources=True,
    )


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _semantic_sha256(payload: Mapping[str, Any]) -> str:
    serialized = json.dumps(
        json_safe(payload),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _candidate_parameter_names(candidates: Sequence[Any]) -> list[str]:
    return sorted(
        {
            str(
                item.get("canonical_parameter_name") or item.get("parameter_name") or item.get("parameterName") or "",
            ).strip()
            for item in candidates
            if isinstance(item, Mapping)
        }
        - {""},
    )


def _preflight_scenario(
    scenario_id: int,
    load_context: Callable[[int], Mapping[str, Any]],
    *,
    capability_release: str,
    resource_manifest: Mapping[str, Any],
    build_quality_evidence: Callable[[int, Mapping[str, Any]], Any] | None = None,
    include_context: bool = False,
) -> dict[str, Any]:
    try:
        context = load_context(scenario_id)
        release = _capability_contract(capability_release)
        group = context.get("scenario_group") or {}
        scenario = context.get("scenario") or {}
        api_version = str(group.get("api_version") or "")
        strategy = str(group.get("generation_strategy") or "")
        loaded_scenario_id = _int_or_none(scenario.get("scenario_id"))
        scenario_group_id = _int_or_none(scenario.get("scenario_group_id"))
        loaded_group_id = _int_or_none(group.get("scenario_group_id"))
        errors: list[str] = []
        skip_reasons: list[str] = []
        if loaded_scenario_id != scenario_id:
            errors.append(
                f"scenario identity mismatch: requested={scenario_id}, loaded={loaded_scenario_id}",
            )
        if scenario_group_id is None or loaded_group_id is None or scenario_group_id != loaded_group_id:
            errors.append(
                "scenario/group identity mismatch: "
                f"scenario_group_id={scenario_group_id}, loaded_group_id={loaded_group_id}",
            )
        if api_version != V4_API_VERSION:
            errors.append(f"api_version must be exactly {V4_API_VERSION!r}: actual={api_version!r}")
        if strategy != V4_STRATEGY:
            errors.append(f"generation_strategy must be exactly {V4_STRATEGY!r}: actual={strategy!r}")
        group_status = str(group.get("status") or "").lower()
        group_stage = str(group.get("stage") or "").lower()
        scenario_status = str(scenario.get("status") or "").lower()
        if group_status not in ELIGIBLE_GROUP_STATUSES:
            skip_reasons.append(f"group status is not execution eligible: {group_status or 'missing'}")
        if group_stage != ELIGIBLE_GROUP_STAGE:
            skip_reasons.append(f"group stage is not completed: {group_stage or 'missing'}")
        if scenario_status not in ELIGIBLE_SCENARIO_STATUSES:
            skip_reasons.append(f"scenario status is not execution eligible: {scenario_status or 'missing'}")

        stored_catalog_version = str(group.get("impact_catalog_version") or "")
        stored_catalog_checksum = str(group.get("impact_catalog_checksum") or "")
        expected_catalog_version = str(release["catalog_version"])
        expected_catalog_checksum = str(release["catalog_checksum"])
        if stored_catalog_version != expected_catalog_version:
            errors.append(
                "stored catalog version does not match the approved capability release: "
                f"expected={expected_catalog_version!r}, actual={stored_catalog_version!r}",
            )
        if stored_catalog_checksum != expected_catalog_checksum:
            errors.append(
                "stored catalog checksum does not match the approved capability release: "
                f"expected={expected_catalog_checksum!r}, actual={stored_catalog_checksum!r}",
            )
        quality_payload: dict[str, Any] = {}
        if build_quality_evidence is not None and not errors and not skip_reasons:
            quality = build_quality_evidence(scenario_id, context)
            quality_errors = [str(item) for item in getattr(quality, "errors", ())]
            errors.extend(quality_errors)
            runtime_candidates = tuple(getattr(quality, "runtime_candidates", ()))
            blocked_candidates = tuple(getattr(quality, "blocked_candidates", ()))
            raw_candidates = tuple(getattr(quality, "raw_candidates", ()))
            runtime_parameter_names = _candidate_parameter_names(runtime_candidates)
            approved_parameter_names = set(release["runtime_allowlist"])
            capability_parameter_names = set(resource_manifest.get("proposal_capability_parameter_names") or ())
            quality_payload = {
                "active_catalog_version": getattr(quality, "active_catalog_version", ""),
                "active_catalog_checksum": getattr(quality, "active_catalog_checksum", ""),
                "raw_candidate_count": len(raw_candidates),
                "runtime_candidate_count": len(runtime_candidates),
                "blocked_candidate_count": len(blocked_candidates),
                "raw_candidate_digest": _semantic_sha256({"candidates": list(raw_candidates)}),
                "runtime_candidate_digest": _semantic_sha256({"candidates": list(runtime_candidates)}),
                "blocked_candidate_digest": _semantic_sha256({"candidates": list(blocked_candidates)}),
                "runtime_parameter_names": runtime_parameter_names,
                "runtime_candidate_keys": sorted(
                    str(item.get("candidate_key") or "") for item in runtime_candidates if isinstance(item, Mapping)
                ),
                "blocked_reason_codes": sorted(
                    {
                        str(item.get("reason_code") or item.get("reasonCode") or "")
                        for item in blocked_candidates
                        if isinstance(item, Mapping)
                    }
                    - {""},
                ),
                "dimension_lineage": list(getattr(quality, "dimension_lineage", ())),
            }
            if quality_payload["active_catalog_version"] != expected_catalog_version:
                errors.append(
                    "active catalog version does not match the approved capability release: "
                    f"expected={expected_catalog_version!r}, "
                    f"actual={quality_payload['active_catalog_version']!r}",
                )
            if quality_payload["active_catalog_checksum"] != expected_catalog_checksum:
                errors.append(
                    "active catalog checksum does not match the approved capability release: "
                    f"expected={expected_catalog_checksum!r}, "
                    f"actual={quality_payload['active_catalog_checksum']!r}",
                )
            unexpected_runtime_names = sorted(set(runtime_parameter_names) - approved_parameter_names)
            if unexpected_runtime_names:
                errors.append(
                    f"runtime candidates escaped the approved capability release: {unexpected_runtime_names}",
                )
            missing_contract_names = sorted(set(runtime_parameter_names) - capability_parameter_names)
            if missing_contract_names:
                errors.append(
                    f"runtime candidates are not covered by the proposal capability contract: {missing_contract_names}",
                )
            if not runtime_candidates and not quality_errors:
                skip_reasons.append("no runtime-allowed parameter candidate")

        scenario_context_fingerprint = _semantic_sha256({"proposal_inputs": dict(context)})
        fingerprint_payload = {
            "scenario_id": scenario_id,
            "scenario_group_id": loaded_group_id,
            "catalog_version": stored_catalog_version,
            "catalog_checksum": stored_catalog_checksum,
            "dimension_values": scenario.get("dimension_values") or {},
            "scenario_context_fingerprint": scenario_context_fingerprint,
            "quality": quality_payload,
            "capability_release": capability_release,
            "runtime_allowlist": sorted(RUNTIME_PROPOSAL_CAPABILITY_NAMES),
            "resource": dict(resource_manifest),
            "policy_version": UNCOVERED_POLICY_VERSION,
        }
        status = "FAIL" if errors else "SKIP" if skip_reasons else "PASS"
        result = {
            "scenario_id": scenario_id,
            "scenario_group_id": loaded_group_id,
            "api_version": api_version,
            "generation_strategy": strategy,
            "group_status": group_status,
            "group_stage": group_stage,
            "scenario_status": scenario_status,
            "stored_catalog_version": stored_catalog_version,
            "stored_catalog_checksum": stored_catalog_checksum,
            "scenario_context_fingerprint": scenario_context_fingerprint,
            **quality_payload,
            "input_fingerprint": _semantic_sha256(fingerprint_payload),
            "status": status,
            "errors": errors,
            "skip_reasons": skip_reasons,
        }
        if include_context:
            result["_loaded_context"] = dict(context)
        return result  # noqa: TRY300 - preflight failures are normalized by the boundary below
    except Exception as exc:
        return {
            "scenario_id": scenario_id,
            "status": "FAIL",
            "errors": [f"context preflight failed: {_redact_text(repr(exc))}"],
            "skip_reasons": [],
        }


def _proposal_row_evidence(row: Mapping[str, Any]) -> dict[str, Any]:
    return {field: row.get(field) for field in _PROPOSAL_ROW_FIELDS if field in row}


def _proposal_ids(rows: Sequence[Mapping[str, Any]]) -> tuple[int, ...]:
    return tuple(
        proposal_id for row in rows if (proposal_id := _int_or_none(row.get("model_param_proposal_id"))) is not None
    )


def _classify_uncovered_guard(
    *,
    scenario_id: int,
    scenario_group_id: int,
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    history = [_proposal_row_evidence(row) for row in rows]
    identity_errors = [
        (
            "proposal guard row identity mismatch: "
            f"proposal_id={row.get('model_param_proposal_id')}, "
            f"scenario_id={row.get('scenario_id')}, scenario_group_id={row.get('scenario_group_id')}"
        )
        for row in history
        if _int_or_none(row.get("scenario_id")) != scenario_id
        or _int_or_none(row.get("scenario_group_id")) != scenario_group_id
    ]
    statuses = [str(row.get("status") or "").upper() for row in history]
    unknown_statuses = sorted({status for status in statuses if status not in KNOWN_PROPOSAL_STATUSES})
    proposal_ids = list(_proposal_ids(history))

    if identity_errors:
        return {
            "decision": "HARD_STOP",
            "reason_code": "PROPOSAL_GUARD_IDENTITY_MISMATCH",
            "eligible": False,
            "hard_stop": True,
            "proposal_ids": proposal_ids,
            "statuses": statuses,
            "history": history,
            "errors": identity_errors,
        }
    if unknown_statuses:
        return {
            "decision": "HARD_STOP",
            "reason_code": "UNKNOWN_PROPOSAL_STATUS",
            "eligible": False,
            "hard_stop": True,
            "proposal_ids": proposal_ids,
            "statuses": statuses,
            "history": history,
            "errors": [f"unknown active proposal statuses: {unknown_statuses}"],
        }
    if "PROCESSING" in statuses:
        processing_error = (
            "PROCESSING proposal exists; no authoritative stale threshold or heartbeat is available, "
            "so the campaign must stop for manual review"
        )
        return {
            "decision": "HARD_STOP",
            "reason_code": "PROCESSING_REQUIRES_MANUAL_REVIEW",
            "eligible": False,
            "hard_stop": True,
            "proposal_ids": proposal_ids,
            "statuses": statuses,
            "history": history,
            "errors": [processing_error],
        }
    if "CONFIRMED" in statuses:
        decision = "SKIP"
        reason_code = "CONFIRMED_EXISTS"
        eligible = False
    elif "PROPOSED" in statuses:
        decision = "SKIP"
        reason_code = "PROPOSED_EXISTS"
        eligible = False
    elif statuses and set(statuses) == {"FAILED"}:
        decision = "ELIGIBLE"
        reason_code = "FAILED_ONLY"
        eligible = True
    elif statuses and set(statuses) == {"ABSTAINED"}:
        decision = "ELIGIBLE"
        reason_code = "ABSTAINED_ONLY"
        eligible = True
    elif statuses:
        decision = "ELIGIBLE"
        reason_code = "ABSTAINED_OR_FAILED_ONLY"
        eligible = True
    else:
        decision = "ELIGIBLE"
        reason_code = "NO_PROPOSAL_HISTORY"
        eligible = True
    return {
        "decision": decision,
        "reason_code": reason_code,
        "eligible": eligible,
        "hard_stop": False,
        "proposal_ids": proposal_ids,
        "statuses": statuses,
        "history": history,
        "errors": [],
    }


def _snapshot_campaign_guards(
    preflight: Sequence[Mapping[str, Any]],
    dependencies: RunnerDependencies,
) -> tuple[dict[int, dict[str, Any]], list[str]]:
    errors: list[str] = []
    guards: dict[int, dict[str, Any]] = {}
    preflight_by_group: dict[int, list[Mapping[str, Any]]] = {}
    for item in preflight:
        scenario_group_id = _int_or_none(item.get("scenario_group_id"))
        if scenario_group_id is None:
            errors.append(f"scenario_id={item.get('scenario_id')}: scenario_group_id is missing")
            continue
        preflight_by_group.setdefault(scenario_group_id, []).append(item)

    for scenario_group_id, group_items in preflight_by_group.items():
        group_scenario_ids = [int(item["scenario_id"]) for item in group_items]
        try:
            rows = dependencies.snapshot_proposal_rows(
                scenario_group_id,
                group_scenario_ids,
            )
        except Exception as exc:
            errors.append(
                f"scenario_group_id={scenario_group_id}: proposal guard snapshot failed: {_redact_text(repr(exc))}",
            )
            continue
        invalid_rows = [
            row
            for row in rows
            if _int_or_none(row.get("scenario_id")) not in group_scenario_ids
            or _int_or_none(row.get("scenario_group_id")) != scenario_group_id
        ]
        if invalid_rows:
            errors.append(
                f"scenario_group_id={scenario_group_id}: proposal guard returned "
                f"{len(invalid_rows)} out-of-scope or invalid row(s)",
            )
        rows_by_scenario = {
            scenario_id: [row for row in rows if _int_or_none(row.get("scenario_id")) == scenario_id]
            for scenario_id in group_scenario_ids
        }
        for item in group_items:
            scenario_id = int(item["scenario_id"])
            guards[scenario_id] = _classify_uncovered_guard(
                scenario_id=scenario_id,
                scenario_group_id=scenario_group_id,
                rows=rows_by_scenario[scenario_id],
            )
    return guards, errors


def _public_final_response(record: Mapping[str, Any]) -> dict[str, Any]:
    response = record.get("final_response") or {}
    if not isinstance(response, Mapping):
        return {}
    data = response.get("data") or {}
    safe_data = (
        {
            key: data.get(key)
            for key in (
                "modelParamProposalId",
                "model_param_proposal_id",
                "scenarioId",
                "scenario_id",
                "scenarioGroupId",
                "scenario_group_id",
                "eventId",
                "event_id",
                "proposalParameters",
                "proposal_parameters",
            )
            if key in data
        }
        if isinstance(data, Mapping)
        else {}
    )
    return {
        key: value
        for key, value in {
            "status": response.get("status"),
            "message": response.get("message"),
            "data": safe_data,
        }.items()
        if value is not None
    }


def _llm_call_evidence(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list | tuple):
        return []
    calls: list[dict[str, Any]] = []
    for raw_call in value:
        if not isinstance(raw_call, Mapping):
            continue
        call = {
            field: raw_call.get(field)
            for field in (
                "step",
                "success",
                "model_name",
                "elapsed_seconds",
                "prompt_bytes",
                "prompt_limit_bytes",
                "parameter_bytes",
                "retry_count",
                "internal_retry_count",
                "attempt",
                "attempt_count",
                "retries",
                "error",
            )
            if field in raw_call
        }
        usage = raw_call.get("usage")
        if isinstance(usage, Mapping):
            call["usage"] = {
                field: usage.get(field)
                for field in (
                    "prompt_tokens",
                    "completion_tokens",
                    "total_tokens",
                    "input_tokens",
                    "output_tokens",
                )
                if field in usage
            }
        calls.append(call)
    return calls


def _record_summary(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "mapping_ok": record.get("mapping_ok"),
        "mapping_messages": record.get("mapping_messages") or [],
        "selected_ok": record.get("selected_ok"),
        "selected_messages": record.get("selected_messages") or [],
        "routing_status": record.get("routing_status"),
        "routing_messages": record.get("routing_messages") or [],
        "step_summary": record.get("step_summary") or {},
        "lut_version": record.get("lut_version"),
        "value_signature": record.get("value_signature"),
        "llm_calls": _llm_call_evidence(record.get("llm_calls")),
        "final_response": _public_final_response(record),
    }


def _failure_summary(trace: Mapping[str, Any]) -> dict[str, Any]:
    summary = {
        key: trace.get(key)
        for key in (
            "failed_stage",
            "error",
            "proposal_persisted",
            "model_param_proposal_id",
            "mapping_trace_captured",
            "partial_state_captured",
            "step_summary",
        )
        if key in trace
    }
    summary["llm_calls"] = _llm_call_evidence(trace.get("llm_calls"))
    return summary


def _safe_fetch_proposal(
    proposal_id_value: int,
    fetch_proposal: Callable[[int | None], dict[str, Any]],
) -> tuple[dict[str, Any], str | None]:
    try:
        row = fetch_proposal(proposal_id_value)
        return _proposal_row_evidence(row), None
    except Exception as exc:
        return {}, _redact_text(repr(exc))


def _proposal_parameters_for_comparison(value: Any) -> Any:
    safe = json_safe(value)
    if isinstance(safe, Mapping):
        return {
            str(key): _proposal_parameters_for_comparison(item)
            for key, item in safe.items()
            if str(key) not in {"lutValue", "lut_value"}
        }
    if isinstance(safe, list | tuple):
        return [_proposal_parameters_for_comparison(item) for item in safe]
    return safe


def _contains_parameter_key(value: Any, forbidden_keys: set[str]) -> bool:
    safe = json_safe(value)
    if isinstance(safe, Mapping):
        return any(
            str(key) in forbidden_keys or _contains_parameter_key(item, forbidden_keys) for key, item in safe.items()
        )
    if isinstance(safe, list | tuple):
        return any(_contains_parameter_key(item, forbidden_keys) for item in safe)
    return False


def _proposal_parameter_names(value: Any) -> set[str]:
    if not isinstance(value, list | tuple):
        return set()
    return {
        str(
            item.get("canonicalParameterName")
            or item.get("canonical_parameter_name")
            or item.get("parameterName")
            or item.get("parameter_name")
            or "",
        ).strip()
        for item in value
        if isinstance(item, Mapping)
    } - {""}


def _success_integrity_errors(
    *,
    scenario_id: int,
    scenario_group_id: int | None,
    model_param_proposal_id: int | None,
    new_proposal_ids: Sequence[int],
    proposal_row: Mapping[str, Any],
    readback_error: str | None,
    final_response: Mapping[str, Any],
    allowed_parameter_names: set[str],
) -> list[str]:
    errors: list[str] = []
    response_status = str(final_response.get("status") or "")
    response_data = final_response.get("data") if isinstance(final_response.get("data"), Mapping) else {}
    response_proposal_parameters = response_data.get(
        "proposalParameters",
        response_data.get("proposal_parameters"),
    )
    if response_status != "success":
        errors.append(f"proposal API response status is not success: {response_status!r}")
    response_event_value = response_data.get("eventId", response_data.get("event_id"))
    response_identity = {
        "scenario_id": _int_or_none(response_data.get("scenarioId", response_data.get("scenario_id"))),
        "scenario_group_id": _int_or_none(
            response_data.get("scenarioGroupId", response_data.get("scenario_group_id")),
        ),
        "event_id": _int_or_none(response_event_value),
    }
    if response_identity["scenario_id"] != scenario_id:
        errors.append(
            f"proposal API scenario ID mismatch: actual={response_identity['scenario_id']}, expected={scenario_id}",
        )
    if response_identity["scenario_group_id"] != scenario_group_id:
        errors.append(
            "proposal API Scenario Group ID mismatch: "
            f"actual={response_identity['scenario_group_id']}, expected={scenario_group_id}",
        )
    event_key_present = "eventId" in response_data or "event_id" in response_data
    if not event_key_present or response_event_value is not None:
        errors.append(
            "v4 proposal API eventId must be present and null: "
            f"present={event_key_present}, actual={response_identity['event_id']}",
        )
    if model_param_proposal_id is None:
        errors.append("success response did not contain modelParamProposalId")
    if model_param_proposal_id is not None and tuple(new_proposal_ids) != (model_param_proposal_id,):
        errors.append(
            "proposal ID snapshot delta must contain exactly the returned ID: "
            f"returned={model_param_proposal_id}, delta={list(new_proposal_ids)}",
        )
    if readback_error:
        errors.append(f"proposal DB read-back failed: {readback_error}")
    if model_param_proposal_id is not None and not proposal_row:
        errors.append("proposal DB read-back returned no row")
    expected_fields = {
        "model_param_proposal_id": model_param_proposal_id,
        "scenario_id": scenario_id,
        "scenario_group_id": scenario_group_id,
        "mi_event_id": None,
        "status": "PROPOSED",
        "callback_status": "SKIPPED",
        "confirmation_parameters": None,
        "confirmed_dtm": None,
    }
    for field, expected in expected_fields.items():
        if proposal_row and proposal_row.get(field) != expected:
            errors.append(f"proposal DB field mismatch: {field}={proposal_row.get(field)!r}, expected={expected!r}")
    if proposal_row and proposal_row.get("proposal_completed_dtm") is None:
        errors.append("proposal DB row is missing proposal_completed_dtm")
    persisted_parameters = proposal_row.get("proposal_parameters") if proposal_row else None
    if not isinstance(persisted_parameters, list) or not persisted_parameters:
        errors.append("proposal DB row contains no proposal_parameters")
    if _contains_parameter_key(persisted_parameters, {"lutValue", "lut_value"}):
        errors.append("proposal DB payload must not persist lutValue")
    response_parameter_names = _proposal_parameter_names(response_proposal_parameters)
    persisted_parameter_names = _proposal_parameter_names(persisted_parameters)
    if not response_parameter_names:
        errors.append("proposal API response contains no Parameter names")
    unexpected_response_names = sorted(response_parameter_names - allowed_parameter_names)
    if unexpected_response_names:
        errors.append(f"proposal API response escaped the preflight runtime candidates: {unexpected_response_names}")
    unexpected_persisted_names = sorted(persisted_parameter_names - allowed_parameter_names)
    if unexpected_persisted_names:
        errors.append(f"proposal DB payload escaped the preflight runtime candidates: {unexpected_persisted_names}")
    if _proposal_parameters_for_comparison(persisted_parameters) != _proposal_parameters_for_comparison(
        response_proposal_parameters,
    ):
        errors.append("proposal DB payload does not match the API response after excluding lutValue")
    return errors


async def _execute_once(
    scenario_id: int,
    preflight: Mapping[str, Any],
    dependencies: RunnerDependencies,
    *,
    capability_release: str,
    resource_manifest: Mapping[str, Any],
    campaign_preflight: Sequence[Mapping[str, Any]],
    initially_eligible_ids: Sequence[int],
) -> dict[str, Any]:
    started_at = datetime.now(UTC)
    started = time.perf_counter()
    attempt: dict[str, Any] = {
        "scenario_id": scenario_id,
        "scenario_group_id": preflight.get("scenario_group_id"),
        "execution_attempt_count": 0,
        "started_at": started_at.isoformat(),
        "status": "FAIL",
    }
    scenario_group_id = _int_or_none(preflight.get("scenario_group_id"))
    if scenario_group_id is None:
        attempt.update(
            {
                "failed_stage": "uncovered guard recheck",
                "error": "scenario_group_id is required for the proposal guard",
                "finished_at": datetime.now(UTC).isoformat(),
                "elapsed_seconds": time.perf_counter() - started,
            },
        )
        return attempt

    current_resource_manifest = _resource_manifest()
    resource_errors = _release_contract_errors(
        capability_release=capability_release,
        resource_manifest=current_resource_manifest,
        require_registered_resources=dependencies.require_registered_resources,
    )
    fresh_preflight = _preflight_scenario(
        scenario_id,
        dependencies.load_context,
        capability_release=capability_release,
        resource_manifest=current_resource_manifest,
        build_quality_evidence=dependencies.build_quality_evidence,
        include_context=True,
    )
    frozen_scenario_context = fresh_preflight.pop("_loaded_context", None)
    attempt["preflight_before_write"] = fresh_preflight
    if resource_errors:
        fresh_preflight.setdefault("errors", []).extend(resource_errors)
        fresh_preflight["status"] = "FAIL"
    initial_fingerprint = str(preflight.get("input_fingerprint") or "")
    fresh_fingerprint = str(fresh_preflight.get("input_fingerprint") or "")
    if fresh_preflight.get("status") != "PASS" or not initial_fingerprint or fresh_fingerprint != initial_fingerprint:
        drift_errors = list(fresh_preflight.get("errors") or [])
        if fresh_preflight.get("status") == "SKIP":
            drift_errors.extend(str(item) for item in fresh_preflight.get("skip_reasons") or [])
        if initial_fingerprint and fresh_fingerprint != initial_fingerprint:
            drift_errors.append(
                "proposal input fingerprint changed after campaign preflight: "
                f"initial={initial_fingerprint}, current={fresh_fingerprint}",
            )
        attempt.update(
            {
                "status": "BLOCKED",
                "failed_stage": "context/resource preflight recheck",
                "error": "PREWRITE_INPUT_DRIFT_OR_INELIGIBLE",
                "prewrite_errors": drift_errors,
                "finished_at": datetime.now(UTC).isoformat(),
                "elapsed_seconds": time.perf_counter() - started,
            },
        )
        return attempt
    if dict(current_resource_manifest) != dict(resource_manifest):
        attempt.update(
            {
                "status": "BLOCKED",
                "failed_stage": "resource preflight recheck",
                "error": "RESOURCE_MANIFEST_DRIFT",
                "finished_at": datetime.now(UTC).isoformat(),
                "elapsed_seconds": time.perf_counter() - started,
            },
        )
        return attempt
    if dependencies.require_registered_resources and (
        dependencies.evaluate_scenario_with_context is None or not isinstance(frozen_scenario_context, Mapping)
    ):
        attempt.update(
            {
                "status": "BLOCKED",
                "failed_stage": "frozen context evaluator preflight",
                "error": "FROZEN_CONTEXT_EVALUATOR_REQUIRED",
                "finished_at": datetime.now(UTC).isoformat(),
                "elapsed_seconds": time.perf_counter() - started,
            },
        )
        return attempt

    campaign_guards, campaign_guard_errors = _snapshot_campaign_guards(
        campaign_preflight,
        dependencies,
    )
    attempt["campaign_guard_before_write"] = {
        str(target_scenario_id): guard for target_scenario_id, guard in sorted(campaign_guards.items())
    }
    campaign_hard_stop_ids = sorted(
        target_scenario_id for target_scenario_id, guard in campaign_guards.items() if guard.get("hard_stop") is True
    )
    newly_covered_ids = sorted(
        target_scenario_id
        for target_scenario_id in initially_eligible_ids
        if campaign_guards.get(target_scenario_id, {}).get("eligible") is not True
    )
    if campaign_guard_errors or campaign_hard_stop_ids or newly_covered_ids:
        attempt.update(
            {
                "status": "BLOCKED",
                "failed_stage": "campaign-wide uncovered guard recheck",
                "error": "CAMPAIGN_SCOPE_CHANGED_OR_BLOCKED",
                "campaign_guard_errors": campaign_guard_errors,
                "campaign_hard_stop_scenario_ids": campaign_hard_stop_ids,
                "newly_covered_scenario_ids": newly_covered_ids,
                "finished_at": datetime.now(UTC).isoformat(),
                "elapsed_seconds": time.perf_counter() - started,
            },
        )
        return attempt
    try:
        before_rows = dependencies.snapshot_proposal_rows(
            scenario_group_id,
            (scenario_id,),
        )
    except Exception as exc:
        attempt.update(
            {
                "failed_stage": "uncovered guard recheck",
                "error": _redact_text(repr(exc)),
                "finished_at": datetime.now(UTC).isoformat(),
                "elapsed_seconds": time.perf_counter() - started,
            },
        )
        return attempt

    guard = _classify_uncovered_guard(
        scenario_id=scenario_id,
        scenario_group_id=scenario_group_id,
        rows=before_rows,
    )
    attempt["uncovered_guard_before_write"] = guard
    if not guard["eligible"]:
        attempt.update(
            {
                "status": "BLOCKED",
                "failed_stage": "uncovered guard recheck",
                "error": guard["reason_code"],
                "finished_at": datetime.now(UTC).isoformat(),
                "elapsed_seconds": time.perf_counter() - started,
            },
        )
        return attempt

    before_ids = _proposal_ids(before_rows)
    attempt["proposal_ids_before"] = list(before_ids)
    attempt["execution_attempt_count"] = 1
    evaluation_record: dict[str, Any] = {}
    evaluation_error: Exception | None = None
    trace: Mapping[str, Any] = {}
    final_response: Mapping[str, Any] = {}
    try:
        if dependencies.evaluate_scenario_with_context is not None and isinstance(frozen_scenario_context, Mapping):
            evaluation_record = await dependencies.evaluate_scenario_with_context(
                scenario_id,
                frozen_scenario_context,
            )
        else:
            evaluation_record = await dependencies.evaluate_scenario(scenario_id)
    except Exception as exc:
        evaluation_error = exc
        trace = dependencies.failure_trace(exc)

    if evaluation_error is None:
        attempt["evaluation"] = _record_summary(evaluation_record)
        raw_final_response = evaluation_record.get("final_response") or {}
        final_response = raw_final_response if isinstance(raw_final_response, Mapping) else {}
        model_param_proposal_id = proposal_id(dict(final_response))
    else:
        attempt["failed_stage"] = trace.get("failed_stage") or "proposal evaluation"
        attempt["error"] = _redact_text(repr(evaluation_error))
        attempt["failure_trace"] = _failure_summary(trace)
        model_param_proposal_id = _int_or_none(trace.get("model_param_proposal_id"))
    attempt["model_param_proposal_id"] = model_param_proposal_id

    proposal_row: dict[str, Any] = {}
    readback_error: str | None = None
    if model_param_proposal_id is not None:
        proposal_row, readback_error = _safe_fetch_proposal(
            model_param_proposal_id,
            dependencies.fetch_proposal,
        )
        attempt["proposal_db_row"] = proposal_row
        if readback_error:
            attempt["proposal_db_readback_error"] = readback_error

    after_ids: tuple[int, ...] = ()
    snapshot_after_error: str | None = None
    try:
        after_rows = dependencies.snapshot_proposal_rows(
            scenario_group_id,
            (scenario_id,),
        )
        after_ids = _proposal_ids(after_rows)
        attempt["proposal_ids_after"] = list(after_ids)
        attempt["proposal_statuses_after"] = [str(row.get("status") or "") for row in after_rows]
    except Exception as exc:
        snapshot_after_error = _redact_text(repr(exc))
        attempt["proposal_id_post_snapshot_error"] = snapshot_after_error

    new_ids = tuple(value for value in after_ids if value not in set(before_ids))
    attempt["new_proposal_ids"] = list(new_ids)
    undiscovered_ids = [value for value in new_ids if value != model_param_proposal_id]
    if undiscovered_ids:
        snapshot_rows: dict[str, Any] = {}
        for discovered_id in undiscovered_ids:
            row, error = _safe_fetch_proposal(discovered_id, dependencies.fetch_proposal)
            snapshot_rows[str(discovered_id)] = row if error is None else {"readback_error": error}
        attempt["snapshot_discovered_rows"] = snapshot_rows
        if model_param_proposal_id is None and len(undiscovered_ids) == 1:
            reconciled_id = undiscovered_ids[0]
            attempt["reconciled_model_param_proposal_id"] = reconciled_id
            reconciled_row = snapshot_rows[str(reconciled_id)]
            if "readback_error" not in reconciled_row:
                attempt["proposal_db_row"] = reconciled_row

    integrity_errors: list[str] = []
    if evaluation_error is None:
        integrity_errors.extend(
            _success_integrity_errors(
                scenario_id=scenario_id,
                scenario_group_id=_int_or_none(preflight.get("scenario_group_id")),
                model_param_proposal_id=model_param_proposal_id,
                new_proposal_ids=new_ids,
                proposal_row=proposal_row,
                readback_error=readback_error,
                final_response=final_response,
                allowed_parameter_names=set(
                    fresh_preflight.get("runtime_parameter_names")
                    or _capability_contract(capability_release)["runtime_allowlist"],
                ),
            ),
        )
    else:
        integrity_errors.append("proposal evaluation raised; automatic retry is forbidden")
    if snapshot_after_error:
        integrity_errors.append(f"proposal ID post-snapshot failed: {snapshot_after_error}")
    if integrity_errors:
        attempt["integrity_errors"] = integrity_errors
    else:
        attempt["status"] = "PASS"
    attempt["proposal_persisted"] = bool(
        trace.get("proposal_persisted") or model_param_proposal_id is not None or new_ids,
    )
    attempt["finished_at"] = datetime.now(UTC).isoformat()
    attempt["elapsed_seconds"] = time.perf_counter() - started
    return attempt


async def run_campaign(
    options: ProposalOnlyOptions,
    *,
    dependencies: RunnerDependencies | None = None,
) -> dict[str, Any]:
    _validate_options(options)
    dependencies = dependencies or _runtime_dependencies()
    started_at = datetime.now(UTC)
    resource_manifest = _resource_manifest()
    evidence: dict[str, Any] = {
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "runner": "model_parameter_proposal_only",
        "mode": "execute" if options.execute else "read-only",
        "status": "RESERVED",
        "started_at": started_at.isoformat(),
        "scope": {
            "scenario_group_id": options.scenario_group_id,
            "scenario_ids": list(options.scenario_ids),
        },
        "manifest": {
            "capability_release": options.capability_release,
            "capability_contract": {
                "catalog_version": _capability_contract(options.capability_release)["catalog_version"],
                "catalog_checksum": _capability_contract(options.capability_release)["catalog_checksum"],
                "runtime_allowlist": sorted(
                    _capability_contract(options.capability_release)["runtime_allowlist"],
                ),
                "resource_release_id": _capability_contract(options.capability_release)["resource_release_id"],
                "workbook_contract_sha256": _capability_contract(options.capability_release)[
                    "workbook_contract_sha256"
                ],
                "resource_semantic_schema_hash": _capability_contract(options.capability_release)[
                    "resource_semantic_schema_hash"
                ],
                "effective_resource_fingerprint": _capability_contract(options.capability_release)[
                    "effective_resource_fingerprint"
                ],
                "uncovered_policy_version": _capability_contract(options.capability_release)[
                    "uncovered_policy_version"
                ],
            },
            "runtime_allowlist": sorted(RUNTIME_PROPOSAL_CAPABILITY_NAMES),
            "uncovered_policy_version": UNCOVERED_POLICY_VERSION,
            "resource": resource_manifest,
        },
        "safety": {
            "uncovered_only": True,
            "sequential": True,
            "single_worker_best_effort": True,
            "max_attempts_per_scenario": 1,
            "automatic_retry": False,
            "confirmation_invoked": False,
            "callback_invoked": False,
            "required_api_version": V4_API_VERSION,
            "required_generation_strategy": V4_STRATEGY,
            "processing_policy": "any active PROCESSING row hard-stops the entire campaign",
        },
        "preflight": [],
        "selection": {},
        "attempts": [],
    }
    _reserve_evidence_path(options.evidence_path, evidence)

    resource_errors: list[str] = []
    if options.execute and dependencies.prepare_resources is not None:
        try:
            await dependencies.prepare_resources()
        except Exception as exc:
            resource_errors.append(f"resource runtime preparation failed: {_redact_text(repr(exc))}")
    resource_manifest = _resource_manifest()
    evidence["manifest"]["resource"] = resource_manifest
    resource_errors.extend(
        _release_contract_errors(
            capability_release=options.capability_release,
            resource_manifest=resource_manifest,
            require_registered_resources=(options.execute and dependencies.require_registered_resources),
        ),
    )
    if resource_errors:
        evidence["status"] = "BLOCKED"
        evidence["selection"] = {
            "errors": resource_errors,
            "counts": {
                "discovered": 0,
                "preflight_pass": 0,
                "preflight_skip": 0,
                "preflight_fail": 0,
                "guarded": 0,
                "eligible_uncovered": 0,
                "covered_skip": 0,
                "hard_stop": 0,
                "attempted": 0,
                "succeeded": 0,
                "failed": 0,
            },
        }
        evidence["finished_at"] = datetime.now(UTC).isoformat()
        _write_evidence(options.evidence_path, evidence)
        return evidence

    evidence["status"] = "PREFLIGHT"
    _write_evidence(options.evidence_path, evidence)
    if options.execute:
        if dependencies.schema_preflight is None:
            schema_errors = (
                ["execute mode requires the 0030 DB schema preflight"]
                if dependencies.require_registered_resources
                else []
            )
            schema_checks: list[str] = []
            schema_verdict = "FAIL" if schema_errors else "NOT_CONFIGURED"
        else:
            try:
                schema_result = dependencies.schema_preflight()
                schema_checks = [str(item) for item in getattr(schema_result, "checks", ())]
                schema_errors = [str(item) for item in getattr(schema_result, "errors", ())]
                schema_verdict = str(getattr(schema_result, "verdict", "") or "FAIL")
                if schema_verdict != "PASS" and not schema_errors:
                    schema_errors.append(f"schema preflight verdict is not PASS: {schema_verdict}")
            except Exception as exc:
                schema_checks = []
                schema_errors = [f"schema preflight failed: {_redact_text(repr(exc))}"]
                schema_verdict = "FAIL"
        evidence["schema_preflight"] = {
            "verdict": schema_verdict,
            "checks": schema_checks,
            "errors": schema_errors,
        }
        _write_evidence(options.evidence_path, evidence)
        if schema_errors:
            evidence["status"] = "BLOCKED"
            evidence["selection"] = {
                "errors": schema_errors,
                "counts": {
                    "discovered": 0,
                    "preflight_pass": 0,
                    "preflight_skip": 0,
                    "preflight_fail": 0,
                    "guarded": 0,
                    "eligible_uncovered": 0,
                    "covered_skip": 0,
                    "hard_stop": 0,
                    "attempted": 0,
                    "succeeded": 0,
                    "failed": 0,
                },
            }
            evidence["finished_at"] = datetime.now(UTC).isoformat()
            _write_evidence(options.evidence_path, evidence)
            return evidence

    try:
        scenario_ids = (
            tuple(options.scenario_ids)
            if options.scenario_group_id is None
            else dependencies.discover_scenario_ids(options.scenario_group_id)
        )
    except Exception as exc:
        evidence["status"] = "BLOCKED"
        evidence["selection"] = {
            "errors": [f"scenario discovery failed: {_redact_text(repr(exc))}"],
        }
        evidence["finished_at"] = datetime.now(UTC).isoformat()
        _write_evidence(options.evidence_path, evidence)
        return evidence
    if not scenario_ids:
        evidence["status"] = "BLOCKED"
        evidence["selection"] = {
            "discovered_scenario_ids": [],
            "errors": ["explicit scope contains no non-deleted Scenario"],
        }
        evidence["finished_at"] = datetime.now(UTC).isoformat()
        _write_evidence(options.evidence_path, evidence)
        return evidence

    evidence["selection"] = {"discovered_scenario_ids": list(scenario_ids)}
    preflight = [
        _preflight_scenario(
            scenario_id,
            dependencies.load_context,
            capability_release=options.capability_release,
            resource_manifest=resource_manifest,
            build_quality_evidence=dependencies.build_quality_evidence,
        )
        for scenario_id in scenario_ids
    ]
    if options.scenario_group_id is not None:
        for item in preflight:
            if _int_or_none(item.get("scenario_group_id")) != options.scenario_group_id:
                item.setdefault("errors", []).append(
                    "loaded Scenario Group does not match the explicit campaign scope: "
                    f"requested={options.scenario_group_id}, actual={item.get('scenario_group_id')}",
                )
                item["status"] = "FAIL"
    evidence["preflight"] = preflight
    if any(item.get("status") == "FAIL" for item in preflight):
        preflight_pass_count = sum(item.get("status") == "PASS" for item in preflight)
        preflight_skip_count = sum(item.get("status") == "SKIP" for item in preflight)
        preflight_fail_count = sum(item.get("status") == "FAIL" for item in preflight)
        evidence["status"] = "BLOCKED"
        evidence["selection"].update(
            {
                "eligible_scenario_ids": [],
                "skipped_scenario_ids": [item["scenario_id"] for item in preflight if item.get("status") == "SKIP"],
                "errors": ["at least one Scenario failed context/catalog preflight"],
                "counts": {
                    "discovered": len(scenario_ids),
                    "preflight_pass": preflight_pass_count,
                    "preflight_skip": preflight_skip_count,
                    "preflight_fail": preflight_fail_count,
                    "guarded": 0,
                    "eligible_uncovered": 0,
                    "covered_skip": 0,
                    "hard_stop": 0,
                    "attempted": 0,
                    "succeeded": 0,
                    "failed": 0,
                },
            },
        )
        evidence["finished_at"] = datetime.now(UTC).isoformat()
        _write_evidence(options.evidence_path, evidence)
        return evidence

    eligible_preflight = [item for item in preflight if item.get("status") == "PASS"]
    guards, guard_errors = _snapshot_campaign_guards(preflight, dependencies)
    for item in preflight:
        scenario_id = int(item["scenario_id"])
        if scenario_id in guards:
            item["uncovered_guard"] = guards[scenario_id]

    hard_stop_ids = sorted(scenario_id for scenario_id, guard in guards.items() if guard["hard_stop"])
    eligible_ids = [
        int(item["scenario_id"])
        for item in eligible_preflight
        if guards.get(int(item["scenario_id"]), {}).get("eligible") is True
    ]
    lifecycle_skipped_ids = [int(item["scenario_id"]) for item in preflight if item.get("status") == "SKIP"]
    covered_ids = sorted(scenario_id for scenario_id, guard in guards.items() if guard["decision"] == "SKIP")
    evidence["selection"].update(
        {
            "eligible_scenario_ids": eligible_ids,
            "covered_scenario_ids": covered_ids,
            "lifecycle_or_capability_skipped_scenario_ids": lifecycle_skipped_ids,
            "hard_stop_scenario_ids": hard_stop_ids,
            "errors": guard_errors,
            "counts": {
                "discovered": len(scenario_ids),
                "preflight_pass": len(eligible_preflight),
                "preflight_skip": len(lifecycle_skipped_ids),
                "preflight_fail": 0,
                "guarded": len(guards),
                "eligible_uncovered": len(eligible_ids),
                "covered_skip": len(covered_ids),
                "lifecycle_or_capability_skip": len(lifecycle_skipped_ids),
                "hard_stop": len(hard_stop_ids),
                "attempted": 0,
                "succeeded": 0,
                "failed": 0,
            },
        },
    )
    if guard_errors or hard_stop_ids:
        evidence["status"] = "BLOCKED"
        evidence["finished_at"] = datetime.now(UTC).isoformat()
        _write_evidence(options.evidence_path, evidence)
        return evidence

    if not options.execute:
        evidence["status"] = "PASS"
        evidence["finished_at"] = datetime.now(UTC).isoformat()
        _write_evidence(options.evidence_path, evidence)
        return evidence

    evidence["status"] = "RUNNING"
    _write_evidence(options.evidence_path, evidence)
    preflight_by_id = {int(item["scenario_id"]): item for item in preflight}
    for scenario_index, scenario_id in enumerate(eligible_ids):
        attempt = await _execute_once(
            scenario_id,
            preflight_by_id[scenario_id],
            dependencies,
            capability_release=options.capability_release,
            resource_manifest=resource_manifest,
            campaign_preflight=preflight,
            initially_eligible_ids=eligible_ids[scenario_index:],
        )
        evidence["attempts"].append(attempt)
        _write_evidence(options.evidence_path, evidence)
        if attempt.get("status") != "PASS":
            break

    if any(attempt.get("status") == "BLOCKED" for attempt in evidence["attempts"]):
        evidence["status"] = "BLOCKED"
    elif len(evidence["attempts"]) == len(eligible_ids) and all(
        attempt.get("status") == "PASS" for attempt in evidence["attempts"]
    ):
        evidence["status"] = "PASS"
    else:
        evidence["status"] = "FAIL"
    evidence["selection"]["counts"]["attempted"] = len(evidence["attempts"])
    evidence["selection"]["counts"]["succeeded"] = sum(
        attempt.get("status") == "PASS" for attempt in evidence["attempts"]
    )
    evidence["selection"]["counts"]["failed"] = sum(
        attempt.get("status") not in {"PASS", "BLOCKED"} for attempt in evidence["attempts"]
    )
    evidence["finished_at"] = datetime.now(UTC).isoformat()
    _write_evidence(options.evidence_path, evidence)
    return evidence


def main(argv: Sequence[str] | None = None) -> int:
    started_at = datetime.now(UTC)
    args = build_parser().parse_args(argv)
    options = _options_from_args(args, started_at)
    try:
        evidence = asyncio.run(run_campaign(options))
    except (FileExistsError, ValueError) as exc:
        logger.error("Proposal-only runner safety gate failed | error={}", _redact_text(repr(exc)))
        return 2
    except Exception as exc:
        logger.exception("Proposal-only runner failed unexpectedly | error={}", _redact_text(repr(exc)))
        return 1
    logger.info(
        "Proposal-only runner finished | status={} evidence_path={} scenarios={} attempts={}",
        evidence["status"],
        options.evidence_path,
        len(evidence.get("selection", {}).get("discovered_scenario_ids", [])),
        len(evidence["attempts"]),
    )
    return 0 if evidence["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
