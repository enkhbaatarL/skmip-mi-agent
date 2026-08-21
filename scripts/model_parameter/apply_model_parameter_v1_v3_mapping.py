from __future__ import annotations

# Copyright (c) 2026 SK Innovation E&S.
import argparse
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
import hashlib
import json
import logging
from pathlib import Path
import sys
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.model_parameter import apply_model_parameter_v4 as v4  # noqa: E402


LOGGER = logging.getLogger("model_parameter_v1_v3_mapping")
MAPPING_CANONICAL_VERSION = "model-parameter-canonical-v1"
MAPPING_CANONICAL_PATH = ROOT_DIR / "scripts/model_parameter/model-parameter-canonical-v1.json"
V4_MODEL_PARAMETER_CANONICAL_PATH = ROOT_DIR / "scripts/model_parameter/model-parameter-canonical-v4.json"
V4_IMPACT_LEVER_CANONICAL_PATH = ROOT_DIR / "scripts/model_parameter/model-impact-lever-canonical-v4.json"
SNAPSHOT_PATH = ROOT_DIR / "scripts/model_parameter/snapshots/external_dev_before_model_parameter_v4_20260813.json"

EXPECTED_MAPPING_COUNT = 129
EXPECTED_METHOD_COUNTS = {
    "direct": 35,
    "routing": 6,
    "indirect": 55,
    "na": 33,
}
EXPECTED_CANDIDATE_NAMES = {
    "GDP",
    "PMI",
    "PowerMix",
    "Temperature",
    "Population",
    "HurricaneIntensity",
    "LiqProdAdjustment",
    "LiqUtilAdjustment",
    "PipelineAdjustment",
    "SupplyDisruption",
}
BASE_MAPPING_IDS = frozenset(range(1, 129))
CANDIDATE_UPDATE_IDS = frozenset({2, 5, 9, 16, 18, 23, 66, 68, 70, 96, 97, 106, 107})
COMMENT_ONLY_UPDATE_IDS = frozenset({67, 95, 105})
UPDATED_MAPPING_IDS = CANDIDATE_UPDATE_IDS | COMMENT_ONLY_UPDATE_IDS
POPULATION_NATURAL_KEY = (21, "economic_intensity", 11)

MAPPING_TARGET_COLUMNS = (
    "use_yn",
    "event_type_l2_id",
    "dimension_key",
    "dimension_label",
    "mapping_method",
    "model_param_id",
    "comment",
    "mod_usr_logn_id",
    "del_yn",
)
CANDIDATE_DML_COLUMNS = ("mapping_method", "model_param_id", "comment", "mod_usr_logn_id")
COMMENT_ONLY_DML_COLUMNS = ("comment",)
MAPPING_STABLE_COLUMNS = tuple(column for column in v4.MAPPING_COLUMNS if column != "mod_dtm")
MAPPING_CREATION_COLUMNS = (
    "model_param_dimension_map_id",
    "crt_usr_logn_id",
    "crt_dtm",
)
POPULATION_READ_BACK_COLUMNS = tuple(
    column for column in v4.MAPPING_COLUMNS if column not in {"model_param_dimension_map_id", "crt_dtm", "mod_dtm"}
)
TEMPLATE_COLUMNS = (
    "scenario_dimension_template_id",
    "event_type_l2_id",
    "template_json",
    "del_yn",
)

CANDIDATE_MAPPING_UPDATE = text(
    """
    UPDATE tmm_mi_model_param_dimension_map
       SET mapping_method = :mapping_method,
           model_param_id = :model_param_id,
           `comment` = :comment,
           mod_usr_logn_id = :mod_usr_logn_id,
           mod_dtm = CURRENT_TIMESTAMP(6)
     WHERE model_param_dimension_map_id = :model_param_dimension_map_id
    """,
)
COMMENT_ONLY_MAPPING_UPDATE = text(
    """
    UPDATE tmm_mi_model_param_dimension_map
       SET `comment` = :comment,
           mod_dtm = CURRENT_TIMESTAMP(6)
     WHERE model_param_dimension_map_id = :model_param_dimension_map_id
    """,
)
POPULATION_UPSERT = text(
    """
    INSERT INTO tmm_mi_model_param_dimension_map (
        use_yn,
        event_type_l2_id,
        dimension_key,
        dimension_label,
        mapping_method,
        model_param_id,
        `comment`,
        crt_usr_logn_id,
        mod_usr_logn_id,
        del_yn
    ) VALUES (
        :use_yn,
        :event_type_l2_id,
        :dimension_key,
        :dimension_label,
        :mapping_method,
        :model_param_id,
        :comment,
        :crt_usr_logn_id,
        :mod_usr_logn_id,
        :del_yn
    )
    ON DUPLICATE KEY UPDATE
        use_yn = VALUES(use_yn),
        dimension_label = VALUES(dimension_label),
        mapping_method = VALUES(mapping_method),
        `comment` = VALUES(`comment`),
        mod_usr_logn_id = VALUES(mod_usr_logn_id),
        mod_dtm = CURRENT_TIMESTAMP(6),
        del_yn = VALUES(del_yn)
    """,
)


@dataclass(frozen=True)
class RolloutArtifacts:
    target_document: dict[str, Any]
    canonical_master: list[dict[str, Any]]
    target_mappings: list[dict[str, Any]]
    canonical_levers: list[dict[str, Any]]
    snapshot_mappings: list[dict[str, Any]]
    snapshot_templates: list[dict[str, Any]]


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate and atomically apply only the approved shared v1/v3 legacy mapping rollout. "
            "The default is a transactional dry-run that always rolls back."
        ),
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--apply",
        action="store_true",
        help="Commit the verified mapping-only update. Without this flag, roll back.",
    )
    mode.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate the mapping target and protected v4 artifacts without opening a DB connection.",
    )
    parser.add_argument("--mapping-canonical", type=Path, default=MAPPING_CANONICAL_PATH)
    parser.add_argument(
        "--v4-model-parameter-canonical",
        type=Path,
        default=V4_MODEL_PARAMETER_CANONICAL_PATH,
    )
    parser.add_argument(
        "--v4-impact-lever-canonical",
        type=Path,
        default=V4_IMPACT_LEVER_CANONICAL_PATH,
    )
    parser.add_argument("--snapshot", type=Path, default=SNAPSHOT_PATH)
    return parser.parse_args(argv)


def _load_json(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        message = f"JSON root must be an object: {path}"
        raise TypeError(message)
    return document


def _rows(document: Mapping[str, Any], key: str) -> list[dict[str, Any]]:
    value = document.get(key)
    if not isinstance(value, list) or not all(isinstance(row, dict) for row in value):
        message = f"{key} must be an array of objects"
        raise RuntimeError(message)
    return [dict(row) for row in value]


def _normalize(value: Any, *, column: str | None = None) -> Any:  # noqa: ANN401
    if column == "parameter_bindings":
        decoded = json.loads(value) if isinstance(value, str) else value
        if not isinstance(decoded, list) or not all(isinstance(item, dict) for item in decoded):
            message = "parameter_bindings must be a JSON array of objects"
            raise RuntimeError(message)
        return json.dumps(
            decoded,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    if isinstance(value, date | datetime):
        return value.isoformat()
    return value


def _projection(row: Mapping[str, Any], columns: Iterable[str]) -> tuple[Any, ...]:
    return tuple(_normalize(row.get(column), column=column) for column in columns)


def _by_id(
    rows: Iterable[Mapping[str, Any]],
    id_column: str,
) -> dict[int, dict[str, Any]]:
    indexed: dict[int, dict[str, Any]] = {}
    for source in rows:
        raw_id = source.get(id_column)
        if raw_id is None:
            continue
        row_id = int(raw_id)
        if row_id in indexed:
            message = f"duplicate {id_column}: {row_id}"
            raise RuntimeError(message)
        indexed[row_id] = dict(source)
    return indexed


def _population_row(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any] | None:
    matches = [
        dict(row)
        for row in rows
        if (
            int(row.get("event_type_l2_id") or 0),
            str(row.get("dimension_key") or ""),
            int(row.get("model_param_id") or 0),
        )
        == POPULATION_NATURAL_KEY
    ]
    if len(matches) > 1:
        message = f"duplicate Population natural key: count={len(matches)}"
        raise RuntimeError(message)
    return matches[0] if matches else None


def _effective_target_row(
    snapshot_row: Mapping[str, Any],
    target_row: Mapping[str, Any],
) -> dict[str, Any]:
    effective = dict(snapshot_row)
    for column in MAPPING_TARGET_COLUMNS:
        effective[column] = target_row.get(column)
    return effective


def _mapping_changed_fields(
    snapshot_row: Mapping[str, Any],
    target_row: Mapping[str, Any],
) -> frozenset[str]:
    return frozenset(column for column in MAPPING_TARGET_COLUMNS if snapshot_row.get(column) != target_row.get(column))


def _parse_template_json(value: object, *, event_type_l2_id: int) -> list[dict[str, Any]]:
    decoded = json.loads(value) if isinstance(value, str) else value
    if not isinstance(decoded, list) or not all(isinstance(item, dict) for item in decoded):
        message = f"invalid active scenario dimension template: event_type_l2_id={event_type_l2_id}"
        raise RuntimeError(message)
    return [dict(item) for item in decoded]


def _candidate_names(
    mappings: list[dict[str, Any]],
    master_rows: list[dict[str, Any]],
) -> set[str]:
    master_by_id = _by_id(master_rows, "model_param_id")
    candidates: set[str] = set()
    for row in mappings:
        if row.get("use_yn") != "Y" or row.get("del_yn") != "N":
            continue
        if row.get("mapping_method") not in {"direct", "routing"}:
            continue
        raw_model_param_id = row.get("model_param_id")
        if raw_model_param_id is None:
            message = f"direct/routing mapping has no parameter: mapping_id={row.get('model_param_dimension_map_id')}"
            raise RuntimeError(message)
        parameter = master_by_id.get(int(raw_model_param_id))
        if parameter is None:
            message = f"orphan mapping parameter: model_param_id={raw_model_param_id}"
            raise RuntimeError(message)
        if parameter.get("use_yn") != "Y" or parameter.get("del_yn") != "N":
            message = f"candidate mapping references inactive v4 parameter: model_param_id={raw_model_param_id}"
            raise RuntimeError(message)
        candidates.add(str(parameter["parameter_name"]))
    return candidates


def _assert_mapping_invariants(  # noqa: C901
    mapping_rows: list[dict[str, Any]],
    master_rows: list[dict[str, Any]],
    template_rows: list[dict[str, Any]],
) -> None:
    if len(mapping_rows) != EXPECTED_MAPPING_COUNT:
        message = f"mapping count must be 129, got {len(mapping_rows)}"
        raise RuntimeError(message)
    if any(row.get("use_yn") != "Y" or row.get("del_yn") != "N" for row in mapping_rows):
        message = "all 129 target mappings must be active and non-deleted"
        raise RuntimeError(message)

    method_counts = Counter(str(row.get("mapping_method")) for row in mapping_rows)
    if dict(method_counts) != EXPECTED_METHOD_COUNTS:
        message = f"mapping method counts mismatch: {dict(method_counts)}"
        raise RuntimeError(message)

    mapping_ids = [
        int(row["model_param_dimension_map_id"])
        for row in mapping_rows
        if row.get("model_param_dimension_map_id") is not None
    ]
    if len(mapping_ids) != len(set(mapping_ids)):
        message = "duplicate mapping primary key"
        raise RuntimeError(message)

    master_by_id = _by_id(master_rows, "model_param_id")
    natural_keys: list[tuple[int, str, int]] = []
    for row in mapping_rows:
        raw_model_param_id = row.get("model_param_id")
        if raw_model_param_id is None:
            continue
        model_param_id = int(raw_model_param_id)
        parameter = master_by_id.get(model_param_id)
        if parameter is None:
            message = f"orphan model parameter FK: mapping_id={row.get('model_param_dimension_map_id')}"
            raise RuntimeError(message)
        if parameter.get("use_yn") != "Y" or parameter.get("del_yn") != "N":
            message = (
                "active mapping references an inactive/deleted v4 parameter: "
                f"mapping_id={row.get('model_param_dimension_map_id')}, model_param_id={model_param_id}"
            )
            raise RuntimeError(message)
        natural_keys.append(
            (
                int(row["event_type_l2_id"]),
                str(row["dimension_key"]),
                model_param_id,
            ),
        )
    if len(natural_keys) != len(set(natural_keys)):
        message = "duplicate non-null mapping natural key"
        raise RuntimeError(message)

    candidates = _candidate_names(mapping_rows, master_rows)
    if candidates != EXPECTED_CANDIDATE_NAMES:
        message = f"v1/v3 candidate names mismatch: {sorted(candidates)}"
        raise RuntimeError(message)

    template_keys: set[tuple[int, str]] = set()
    for row in template_rows:
        if row.get("del_yn") != "N":
            continue
        event_type_l2_id = int(row["event_type_l2_id"])
        dimensions = _parse_template_json(
            row.get("template_json"),
            event_type_l2_id=event_type_l2_id,
        )
        for dimension in dimensions:
            dimension_key = str(dimension.get("dim_key") or "").strip()
            if dimension_key:
                template_keys.add((event_type_l2_id, dimension_key))
    mapping_keys = {(int(row["event_type_l2_id"]), str(row["dimension_key"])) for row in mapping_rows}
    missing_template_keys = sorted(mapping_keys - template_keys)
    if missing_template_keys:
        message = f"mapping keys missing from active scenario templates: {missing_template_keys}"
        raise RuntimeError(message)


def _validate_mapping_target(  # noqa: C901
    target_document: Mapping[str, Any],
    canonical_master: list[dict[str, Any]],
    snapshot_mappings: list[dict[str, Any]],
    snapshot_templates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if target_document.get("canonical_version") != MAPPING_CANONICAL_VERSION:
        message = f"unexpected mapping canonical version: {target_document.get('canonical_version')!r}"
        raise RuntimeError(message)
    if target_document.get("audit_user") != MAPPING_CANONICAL_VERSION:
        message = f"unexpected mapping audit_user: {target_document.get('audit_user')!r}"
        raise RuntimeError(message)
    if set(target_document.get("active_parameter_names") or []) != EXPECTED_CANDIDATE_NAMES:
        message = "mapping canonical declared candidate set must contain exactly the approved 10 names"
        raise RuntimeError(message)

    target_mappings = _rows(target_document, "dimension_mappings")
    if target_document.get("mapping_count") != EXPECTED_MAPPING_COUNT:
        message = f"mapping canonical declared count must be {EXPECTED_MAPPING_COUNT}"
        raise RuntimeError(message)
    if len(snapshot_mappings) != len(BASE_MAPPING_IDS):
        message = f"v4 source snapshot mapping count must be 128, got {len(snapshot_mappings)}"
        raise RuntimeError(message)

    target_by_id = _by_id(target_mappings, "model_param_dimension_map_id")
    snapshot_by_id = _by_id(snapshot_mappings, "model_param_dimension_map_id")
    if set(target_by_id) != BASE_MAPPING_IDS or set(snapshot_by_id) != BASE_MAPPING_IDS:
        message = "target and snapshot must each identify mapping IDs 1..128 exactly once"
        raise RuntimeError(message)

    population = _population_row(target_mappings)
    if population is None or population.get("model_param_dimension_map_id") is not None:
        message = "target must contain one auto-ID Population routing row"
        raise RuntimeError(message)
    if len(target_mappings) != len(target_by_id) + 1:
        message = "target may add only the Population natural-key row"
        raise RuntimeError(message)

    actual_changed_ids: set[int] = set()
    for mapping_id in sorted(BASE_MAPPING_IDS):
        changed_fields = _mapping_changed_fields(snapshot_by_id[mapping_id], target_by_id[mapping_id])
        if changed_fields:
            actual_changed_ids.add(mapping_id)
        if mapping_id in CANDIDATE_UPDATE_IDS:
            expected_fields = {"mapping_method", "model_param_id", "comment", "mod_usr_logn_id"}
            if changed_fields != expected_fields:
                message = (
                    f"candidate mapping diff is not approved: mapping_id={mapping_id}, fields={sorted(changed_fields)}"
                )
                raise RuntimeError(message)
        elif mapping_id in COMMENT_ONLY_UPDATE_IDS:
            if changed_fields != {"comment"}:
                message = (
                    "comment-only mapping diff is not approved: "
                    f"mapping_id={mapping_id}, fields={sorted(changed_fields)}"
                )
                raise RuntimeError(message)
        elif changed_fields:
            message = f"unapproved mapping target diff: mapping_id={mapping_id}, fields={sorted(changed_fields)}"
            raise RuntimeError(message)
    if actual_changed_ids != UPDATED_MAPPING_IDS:
        message = f"mapping target must change exactly the approved 16 IDs: actual={sorted(actual_changed_ids)}"
        raise RuntimeError(message)

    _assert_mapping_invariants(target_mappings, canonical_master, snapshot_templates)
    return target_mappings


def validate_artifacts(
    *,
    mapping_canonical_path: Path,
    v4_model_parameter_canonical_path: Path,
    v4_impact_lever_canonical_path: Path,
    snapshot_path: Path,
) -> RolloutArtifacts:
    """Validate the mapping target and the unchanged v4 authorities without DB access."""
    (
        canonical_master,
        _,
        canonical_levers,
        _,
        snapshot_mappings,
        _,
        snapshot_templates,
    ) = v4.validate_artifacts(
        model_parameter_canonical_path=v4_model_parameter_canonical_path,
        impact_lever_canonical_path=v4_impact_lever_canonical_path,
        snapshot_path=snapshot_path,
    )
    v4_model_parameter_document = _load_json(v4_model_parameter_canonical_path)
    expected_target_sha256 = v4_model_parameter_document.get("source_canonical_sha256")
    actual_target_sha256 = hashlib.sha256(mapping_canonical_path.read_bytes()).hexdigest()
    if actual_target_sha256 != expected_target_sha256:
        message = "mapping target does not match the v1 canonical pinned by canonical v4"
        raise RuntimeError(message)
    target_document = _load_json(mapping_canonical_path)
    target_mappings = _validate_mapping_target(
        target_document,
        canonical_master,
        snapshot_mappings,
        snapshot_templates,
    )
    return RolloutArtifacts(
        target_document=target_document,
        canonical_master=canonical_master,
        target_mappings=target_mappings,
        canonical_levers=canonical_levers,
        snapshot_mappings=snapshot_mappings,
        snapshot_templates=snapshot_templates,
    )


def _assert_v4_canonical_state(
    live_master: list[dict[str, Any]],
    live_levers: list[dict[str, Any]],
    canonical_master: list[dict[str, Any]],
    canonical_levers: list[dict[str, Any]],
) -> None:
    live_master_by_id = _by_id(live_master, "model_param_id")
    canonical_master_by_id = _by_id(canonical_master, "model_param_id")
    if set(live_master_by_id) != set(canonical_master_by_id):
        message = "live master IDs do not match canonical v4"
        raise RuntimeError(message)
    for model_param_id in sorted(canonical_master_by_id):
        if _projection(live_master_by_id[model_param_id], v4.MASTER_STABLE_COLUMNS) != _projection(
            canonical_master_by_id[model_param_id],
            v4.MASTER_STABLE_COLUMNS,
        ):
            message = f"live master row does not match canonical v4: model_param_id={model_param_id}"
            raise RuntimeError(message)

    live_lever_by_id = _by_id(live_levers, "impact_lever_id")
    canonical_lever_by_id = _by_id(canonical_levers, "impact_lever_id")
    if set(live_lever_by_id) != set(canonical_lever_by_id):
        message = "live Impact Lever IDs do not match canonical v4"
        raise RuntimeError(message)
    for impact_lever_id in sorted(canonical_lever_by_id):
        if _projection(live_lever_by_id[impact_lever_id], v4.IMPACT_LEVER_STABLE_COLUMNS) != _projection(
            canonical_lever_by_id[impact_lever_id],
            v4.IMPACT_LEVER_STABLE_COLUMNS,
        ):
            message = f"live Impact Lever row does not match canonical v4: impact_lever_id={impact_lever_id}"
            raise RuntimeError(message)


def _assert_mapping_preconditions(  # noqa: C901
    live_mappings: list[dict[str, Any]],
    target_mappings: list[dict[str, Any]],
    snapshot_mappings: list[dict[str, Any]],
) -> None:
    if len(live_mappings) not in {128, 129}:
        message = f"live mapping count must be source 128 or final 129, got {len(live_mappings)}"
        raise RuntimeError(message)
    live_by_id = _by_id(live_mappings, "model_param_dimension_map_id")
    target_by_id = _by_id(target_mappings, "model_param_dimension_map_id")
    snapshot_by_id = _by_id(snapshot_mappings, "model_param_dimension_map_id")
    if not BASE_MAPPING_IDS.issubset(live_by_id):
        message = f"live mapping is missing source IDs: {sorted(BASE_MAPPING_IDS - set(live_by_id))}"
        raise RuntimeError(message)

    for mapping_id in sorted(BASE_MAPPING_IDS):
        live = live_by_id[mapping_id]
        source = snapshot_by_id[mapping_id]
        target = _effective_target_row(source, target_by_id[mapping_id])
        if _projection(live, MAPPING_CREATION_COLUMNS) != _projection(source, MAPPING_CREATION_COLUMNS):
            message = f"mapping creation audit differs from v4 snapshot: mapping_id={mapping_id}"
            raise RuntimeError(message)
        if mapping_id in UPDATED_MAPPING_IDS:
            live_state = _projection(live, MAPPING_STABLE_COLUMNS)
            allowed_states = {
                _projection(source, MAPPING_STABLE_COLUMNS),
                _projection(target, MAPPING_STABLE_COLUMNS),
            }
            if live_state not in allowed_states:
                message = f"mapping row is neither approved source nor final: mapping_id={mapping_id}"
                raise RuntimeError(message)
        elif _projection(live, v4.MAPPING_COLUMNS) != _projection(source, v4.MAPPING_COLUMNS):
            message = f"unapproved live mapping drift: mapping_id={mapping_id}"
            raise RuntimeError(message)

    population = _population_row(live_mappings)
    extra_ids = set(live_by_id) - BASE_MAPPING_IDS
    if len(live_mappings) == 128:
        if population is not None or extra_ids:
            message = "128-row source state contains an unexpected extra/Population row"
            raise RuntimeError(message)
        return
    if population is None or len(extra_ids) != 1:
        message = "129-row final state must add only the Population natural-key row"
        raise RuntimeError(message)
    canonical_population = _population_row(target_mappings)
    if canonical_population is None or _projection(population, POPULATION_READ_BACK_COLUMNS) != _projection(
        canonical_population,
        POPULATION_READ_BACK_COLUMNS,
    ):
        message = "existing Population mapping is not in approved final state"
        raise RuntimeError(message)


def _assert_preconditions(
    live_master: list[dict[str, Any]],
    live_mappings: list[dict[str, Any]],
    live_levers: list[dict[str, Any]],
    artifacts: RolloutArtifacts,
) -> None:
    _assert_v4_canonical_state(
        live_master,
        live_levers,
        artifacts.canonical_master,
        artifacts.canonical_levers,
    )
    _assert_mapping_preconditions(
        live_mappings,
        artifacts.target_mappings,
        artifacts.snapshot_mappings,
    )


def _assert_exact_rows_unchanged(
    before_rows: list[dict[str, Any]],
    after_rows: list[dict[str, Any]],
    *,
    id_column: str,
    columns: tuple[str, ...],
    label: str,
) -> None:
    before_by_id = _by_id(before_rows, id_column)
    after_by_id = _by_id(after_rows, id_column)
    if set(before_by_id) != set(after_by_id):
        message = f"{label} identities changed"
        raise RuntimeError(message)
    for row_id in sorted(before_by_id):
        if _projection(before_by_id[row_id], columns) != _projection(after_by_id[row_id], columns):
            message = f"{label} row changed: {id_column}={row_id}"
            raise RuntimeError(message)


def _assert_v4_rows_unchanged(
    before_master: list[dict[str, Any]],
    after_master: list[dict[str, Any]],
    before_levers: list[dict[str, Any]],
    after_levers: list[dict[str, Any]],
) -> None:
    _assert_exact_rows_unchanged(
        before_master,
        after_master,
        id_column="model_param_id",
        columns=v4.MASTER_COLUMNS,
        label="protected v4 master",
    )
    _assert_exact_rows_unchanged(
        before_levers,
        after_levers,
        id_column="impact_lever_id",
        columns=v4.IMPACT_LEVER_COLUMNS,
        label="protected v4 Impact Lever",
    )


def _assert_final_mapping_read_back(
    actual_mappings: list[dict[str, Any]],
    target_mappings: list[dict[str, Any]],
    snapshot_mappings: list[dict[str, Any]],
) -> None:
    if len(actual_mappings) != EXPECTED_MAPPING_COUNT:
        message = f"final mapping count must be 129, got {len(actual_mappings)}"
        raise RuntimeError(message)
    actual_by_id = _by_id(actual_mappings, "model_param_dimension_map_id")
    target_by_id = _by_id(target_mappings, "model_param_dimension_map_id")
    snapshot_by_id = _by_id(snapshot_mappings, "model_param_dimension_map_id")
    for mapping_id in sorted(BASE_MAPPING_IDS):
        expected = _effective_target_row(snapshot_by_id[mapping_id], target_by_id[mapping_id])
        comparison_columns = MAPPING_STABLE_COLUMNS if mapping_id in UPDATED_MAPPING_IDS else v4.MAPPING_COLUMNS
        if _projection(actual_by_id[mapping_id], comparison_columns) != _projection(
            expected,
            comparison_columns,
        ):
            message = f"mapping final read-back mismatch: mapping_id={mapping_id}"
            raise RuntimeError(message)
    actual_population = _population_row(actual_mappings)
    target_population = _population_row(target_mappings)
    if actual_population is None or target_population is None:
        message = "Population mapping missing from final read-back"
        raise RuntimeError(message)
    if _projection(actual_population, POPULATION_READ_BACK_COLUMNS) != _projection(
        target_population,
        POPULATION_READ_BACK_COLUMNS,
    ):
        message = "Population final read-back mismatch"
        raise RuntimeError(message)


def _fetch_master(session: Session, *, lock: bool) -> list[dict[str, Any]]:
    suffix = " FOR SHARE" if lock else ""
    query = (
        f"SELECT {', '.join(v4.MASTER_COLUMNS)} FROM tmm_mi_model_param_m "  # noqa: S608
        f"ORDER BY model_param_id{suffix}"
    )
    return [dict(row) for row in session.execute(text(query)).mappings().all()]


def _fetch_mappings(session: Session, *, lock: bool) -> list[dict[str, Any]]:
    suffix = " FOR UPDATE" if lock else ""
    columns = ", ".join(f"`{column}`" if column == "comment" else column for column in v4.MAPPING_COLUMNS)
    query = (
        f"SELECT {columns} FROM tmm_mi_model_param_dimension_map "  # noqa: S608
        f"ORDER BY model_param_dimension_map_id{suffix}"
    )
    return [dict(row) for row in session.execute(text(query)).mappings().all()]


def _fetch_levers(session: Session, *, lock: bool) -> list[dict[str, Any]]:
    suffix = " FOR SHARE" if lock else ""
    query = (
        f"SELECT {', '.join(v4.IMPACT_LEVER_COLUMNS)} FROM tmm_mi_model_impact_lever_m "  # noqa: S608
        f"ORDER BY impact_lever_id{suffix}"
    )
    return [dict(row) for row in session.execute(text(query)).mappings().all()]


def _fetch_templates(session: Session, *, lock: bool) -> list[dict[str, Any]]:
    suffix = " FOR SHARE" if lock else ""
    query = (
        "SELECT scenario_dimension_template_id, event_type_l2_id, template_json, del_yn "  # noqa: S608
        "FROM tmm_mi_scenario_dimension_template_m "
        f"ORDER BY scenario_dimension_template_id{suffix}"
    )
    return [dict(row) for row in session.execute(text(query)).mappings().all()]


def _apply_mappings(
    session: Session,
    live_mappings: list[dict[str, Any]],
    target_mappings: list[dict[str, Any]],
    snapshot_mappings: list[dict[str, Any]],
) -> tuple[int, bool]:
    live_by_id = _by_id(live_mappings, "model_param_dimension_map_id")
    target_by_id = _by_id(target_mappings, "model_param_dimension_map_id")
    snapshot_by_id = _by_id(snapshot_mappings, "model_param_dimension_map_id")
    updated_count = 0
    for mapping_id in sorted(UPDATED_MAPPING_IDS):
        target = _effective_target_row(snapshot_by_id[mapping_id], target_by_id[mapping_id])
        if _projection(live_by_id[mapping_id], MAPPING_STABLE_COLUMNS) == _projection(
            target,
            MAPPING_STABLE_COLUMNS,
        ):
            continue
        if mapping_id in CANDIDATE_UPDATE_IDS:
            statement = CANDIDATE_MAPPING_UPDATE
            dml_columns = CANDIDATE_DML_COLUMNS
        else:
            statement = COMMENT_ONLY_MAPPING_UPDATE
            dml_columns = COMMENT_ONLY_DML_COLUMNS
        parameters = {column: target.get(column) for column in dml_columns}
        parameters["model_param_dimension_map_id"] = mapping_id
        result = session.execute(statement, parameters)
        if result.rowcount != 1:
            message = f"mapping update affected {result.rowcount} rows: mapping_id={mapping_id}"
            raise RuntimeError(message)
        updated_count += 1

    population = _population_row(target_mappings)
    if population is None:
        message = "target Population mapping is missing"
        raise RuntimeError(message)
    population_inserted = _population_row(live_mappings) is None
    if population_inserted:
        result = session.execute(POPULATION_UPSERT, population)
        if result.rowcount not in {1, 2}:
            message = f"Population upsert affected unexpected row count: {result.rowcount}"
            raise RuntimeError(message)
    return updated_count, population_inserted


def _state_digest(
    master_rows: list[dict[str, Any]],
    mapping_rows: list[dict[str, Any]],
    lever_rows: list[dict[str, Any]],
) -> str:
    payload = {
        "master": [
            {column: _normalize(row.get(column), column=column) for column in v4.MASTER_COLUMNS} for row in master_rows
        ],
        "mappings": [
            {column: _normalize(row.get(column), column=column) for column in v4.MAPPING_COLUMNS}
            for row in mapping_rows
        ],
        "impact_levers": [
            {column: _normalize(row.get(column), column=column) for column in v4.IMPACT_LEVER_COLUMNS}
            for row in lever_rows
        ],
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _fetch_fresh_state() -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    from apps.common.configs.database.sync_database.connection import get_sync_session

    session = get_sync_session()
    try:
        return (
            _fetch_master(session, lock=False),
            _fetch_mappings(session, lock=False),
            _fetch_levers(session, lock=False),
            _fetch_templates(session, lock=False),
        )
    finally:
        session.close()


def _assert_digest_equal(actual: str, expected: str, *, message: str) -> None:
    if actual != expected:
        raise RuntimeError(message)


def run(
    *,
    apply: bool,
    mapping_canonical_path: Path,
    v4_model_parameter_canonical_path: Path,
    v4_impact_lever_canonical_path: Path,
    snapshot_path: Path,
) -> None:
    from apps.common.configs.database.sync_database.connection import get_sync_session

    artifacts = validate_artifacts(
        mapping_canonical_path=mapping_canonical_path,
        v4_model_parameter_canonical_path=v4_model_parameter_canonical_path,
        v4_impact_lever_canonical_path=v4_impact_lever_canonical_path,
        snapshot_path=snapshot_path,
    )
    session = get_sync_session()
    before_digest: str | None = None
    transaction_committed = False
    before_master: list[dict[str, Any]] = []
    before_levers: list[dict[str, Any]] = []
    try:
        before_master = _fetch_master(session, lock=True)
        before_mappings = _fetch_mappings(session, lock=True)
        before_levers = _fetch_levers(session, lock=True)
        before_templates = _fetch_templates(session, lock=True)
        before_digest = _state_digest(before_master, before_mappings, before_levers)
        _assert_preconditions(before_master, before_mappings, before_levers, artifacts)

        updated_count, population_inserted = _apply_mappings(
            session,
            before_mappings,
            artifacts.target_mappings,
            artifacts.snapshot_mappings,
        )
        actual_master = _fetch_master(session, lock=True)
        actual_mappings = _fetch_mappings(session, lock=True)
        actual_levers = _fetch_levers(session, lock=True)
        actual_templates = _fetch_templates(session, lock=True)
        _assert_v4_canonical_state(
            actual_master,
            actual_levers,
            artifacts.canonical_master,
            artifacts.canonical_levers,
        )
        _assert_v4_rows_unchanged(before_master, actual_master, before_levers, actual_levers)
        _assert_exact_rows_unchanged(
            before_templates,
            actual_templates,
            id_column="scenario_dimension_template_id",
            columns=TEMPLATE_COLUMNS,
            label="scenario dimension template",
        )
        _assert_final_mapping_read_back(
            actual_mappings,
            artifacts.target_mappings,
            artifacts.snapshot_mappings,
        )
        _assert_mapping_invariants(actual_mappings, actual_master, actual_templates)
        transactional_digest = _state_digest(actual_master, actual_mappings, actual_levers)

        if apply:
            session.commit()
            transaction_committed = True
            persisted_master, persisted_mappings, persisted_levers, persisted_templates = _fetch_fresh_state()
            _assert_v4_canonical_state(
                persisted_master,
                persisted_levers,
                artifacts.canonical_master,
                artifacts.canonical_levers,
            )
            _assert_v4_rows_unchanged(before_master, persisted_master, before_levers, persisted_levers)
            _assert_exact_rows_unchanged(
                before_templates,
                persisted_templates,
                id_column="scenario_dimension_template_id",
                columns=TEMPLATE_COLUMNS,
                label="scenario dimension template",
            )
            _assert_final_mapping_read_back(
                persisted_mappings,
                artifacts.target_mappings,
                artifacts.snapshot_mappings,
            )
            _assert_mapping_invariants(persisted_mappings, persisted_master, persisted_templates)
            persisted_digest = _state_digest(persisted_master, persisted_mappings, persisted_levers)
            _assert_digest_equal(
                persisted_digest,
                transactional_digest,
                message="persisted mapping rollout differs from the verified transaction state",
            )
            LOGGER.info(
                "v1/v3 mapping-only rollout committed: mappings=%s updated=%s population_inserted=%s "
                "v4_master_unchanged=true v4_impact_lever_unchanged=true before_digest=%s after_digest=%s",
                len(persisted_mappings),
                updated_count,
                population_inserted,
                before_digest,
                persisted_digest,
            )
        else:
            session.rollback()
            persisted_master, persisted_mappings, persisted_levers, _ = _fetch_fresh_state()
            rollback_digest = _state_digest(persisted_master, persisted_mappings, persisted_levers)
            _assert_digest_equal(
                rollback_digest,
                before_digest,
                message="mapping-only dry-run rollback did not restore the exact pre-transaction state",
            )
            _assert_v4_rows_unchanged(before_master, persisted_master, before_levers, persisted_levers)
            LOGGER.info(
                "v1/v3 mapping-only dry-run passed and rolled back: mappings=%s updated=%s "
                "population_inserted=%s v4_master_unchanged=true v4_impact_lever_unchanged=true "
                "before_digest=%s transactional_digest=%s rollback_digest=%s",
                len(actual_mappings),
                updated_count,
                population_inserted,
                before_digest,
                transactional_digest,
                rollback_digest,
            )
    except Exception:
        session.rollback()
        if before_digest is not None and not transaction_committed:
            persisted_master, persisted_mappings, persisted_levers, _ = _fetch_fresh_state()
            rollback_digest = _state_digest(persisted_master, persisted_mappings, persisted_levers)
            _assert_digest_equal(
                rollback_digest,
                before_digest,
                message="failed mapping-only operation did not roll back exactly",
            )
            _assert_v4_rows_unchanged(before_master, persisted_master, before_levers, persisted_levers)
        raise
    finally:
        session.close()


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = _parse_args(argv)
    try:
        if args.validate_only:
            artifacts = validate_artifacts(
                mapping_canonical_path=args.mapping_canonical.resolve(),
                v4_model_parameter_canonical_path=args.v4_model_parameter_canonical.resolve(),
                v4_impact_lever_canonical_path=args.v4_impact_lever_canonical.resolve(),
                snapshot_path=args.snapshot.resolve(),
            )
            LOGGER.info(
                "v1/v3 mapping-only artifacts validated without DB access: mappings=%s candidates=%s "
                "protected_v4_master=%s protected_v4_impact_levers=%s",
                len(artifacts.target_mappings),
                len(EXPECTED_CANDIDATE_NAMES),
                len(artifacts.canonical_master),
                len(artifacts.canonical_levers),
            )
            return 0
        run(
            apply=bool(args.apply),
            mapping_canonical_path=args.mapping_canonical.resolve(),
            v4_model_parameter_canonical_path=args.v4_model_parameter_canonical.resolve(),
            v4_impact_lever_canonical_path=args.v4_impact_lever_canonical.resolve(),
            snapshot_path=args.snapshot.resolve(),
        )
    except Exception:
        LOGGER.exception("v1/v3 mapping-only canonical operation failed")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
