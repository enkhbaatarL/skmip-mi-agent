"""Build the reviewed v0050 revision of the v4.1 Impact Lever catalog."""

from __future__ import annotations

# Copyright (c) 2026 SK Innovation E&S.
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SOURCE_PATH = ROOT / "scripts/model_parameter/model-impact-lever-canonical-v4.1-0036.json"
MASTER_PATH = ROOT / "scripts/model_parameter/model-parameter-canonical-v4.1-0050.json"
TARGET_PATH = ROOT / "scripts/model_parameter/model-impact-lever-canonical-v4.1-0050.json"

CATALOG_VERSION = "v4.1"
CANONICAL_VERSION = "model-impact-lever-canonical-v4.1-0050"
AUDIT_USER = "model-impact-lever-v4.1-v0050"
SOURCE_HYDRATED_CHECKSUM = "a8e831d7941d3fb0bd15e45cd8a762a86b9b8c97ec21a4377ed8618a2d70c72e"
EXPECTED_HYDRATED_CHECKSUM = "467749ea59c3af7e875669be23da00c0fd8ef7c226256f9518a5945e36e4d7c4"
REMOVED_INACTIVE_PARAMETERS = frozenset({"User-Adjusted Gas Demand", "HDD", "CDD"})
CANAL_BINDINGS = (
    (
        "Suez Canal Cost",
        "조건부: Suez와 Year별 통항료($/crossing) 경로가 직접 명시된 경우",
    ),
    (
        "Panama Canal Cost",
        "조건부: Panama와 Year별 통항료($/crossing) 경로가 직접 명시된 경우",
    ),
)


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _resolve_binding_support(
    *,
    requested_status: str,
    master_use_yn: str,
    requested_reason_code: str | None,
) -> tuple[str, str | None]:
    if requested_status == "executable" and master_use_yn == "Y":
        return "executable", None
    if requested_status == "executable" or requested_reason_code == "INACTIVE_MODEL_PARAMETER":
        return "known_unsupported", "INACTIVE_MODEL_PARAMETER"
    return "known_unsupported", "CATALOG_MARKED_UNSUPPORTED"


def _split_bindings(bindings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for binding in bindings:
        parameter_name = str(binding.get("parameter_name") or "")
        if parameter_name in REMOVED_INACTIVE_PARAMETERS:
            continue
        if parameter_name != "CanalToll":
            result.append(dict(binding))
            continue
        for split_name, applicability in CANAL_BINDINGS:
            result.append(
                {
                    **binding,
                    "parameter_name": split_name,
                    "selection_mode": "conditional",
                    "applicability": applicability,
                },
            )
    return result


def _hydrated_checksum(
    rows: list[dict[str, Any]],
    *,
    master_use_by_name: dict[str, str],
) -> str:
    hydrated: list[dict[str, Any]] = []
    for row in sorted(rows, key=lambda item: (str(item["domain"]), str(item["lever_code"]))):
        bindings: list[dict[str, Any]] = []
        for raw_binding in row["parameter_bindings"]:
            parameter_name = str(raw_binding["parameter_name"])
            selection_mode = str(raw_binding.get("selection_mode") or "deterministic")
            support_status, unsupported_reason_code = _resolve_binding_support(
                requested_status=str(raw_binding.get("support_status") or "known_unsupported"),
                master_use_yn=master_use_by_name[parameter_name],
                requested_reason_code=raw_binding.get("unsupported_reason_code"),
            )
            binding: dict[str, Any] = {
                "parameter_name": parameter_name,
                "role": raw_binding.get("role") or "primary",
                "selection_mode": selection_mode,
                "applicability": raw_binding.get("applicability") or "",
                "support_status": support_status,
                "unsupported_reason_code": unsupported_reason_code,
            }
            if selection_mode == "deterministic":
                binding.pop("selection_mode")
            bindings.append(binding)
        normalized = {
            "lever_code": row["lever_code"],
            "domain": row["domain"],
            "label": row["label"],
            "description": row["description"],
            "applicability_hint": row.get("applicability_hint"),
            "parent_lever_code": row.get("parent_lever_code"),
            "parameter_bindings": bindings,
            "catalog_version": CATALOG_VERSION,
        }
        for binding in normalized["parameter_bindings"]:
            if binding.get("selection_mode") == "deterministic":
                binding.pop("selection_mode", None)
        hydrated.append(normalized)
    return hashlib.sha256(_canonical_json_bytes(hydrated)).hexdigest()


def build_document() -> dict[str, Any]:
    source_bytes = SOURCE_PATH.read_bytes()
    source = json.loads(source_bytes)
    master = json.loads(MASTER_PATH.read_text(encoding="utf-8"))
    master_use_by_name = {
        str(row["parameter_name"]): str(row["use_yn"]) for row in master["master"] if row.get("del_yn") == "N"
    }
    rows: list[dict[str, Any]] = []
    for raw_row in source["impact_levers"]:
        source_id = int(raw_row["target_impact_lever_id"])
        rows.append(
            {
                "source_impact_lever_id": source_id,
                "target_impact_lever_id": source_id,
                "lever_code": raw_row["lever_code"],
                "domain": raw_row["domain"],
                "label": raw_row["label"],
                "description": raw_row["description"],
                "applicability_hint": raw_row.get("applicability_hint"),
                "parent_lever_code": raw_row.get("parent_lever_code"),
                "parameter_bindings": _split_bindings(raw_row["parameter_bindings"]),
                "catalog_version": CATALOG_VERSION,
                "use_yn": "Y",
                "del_yn": "N",
            },
        )

    checksum = _hydrated_checksum(rows, master_use_by_name=master_use_by_name)
    if EXPECTED_HYDRATED_CHECKSUM and checksum != EXPECTED_HYDRATED_CHECKSUM:
        message = f"v4.1 v0050 hydrated checksum mismatch: expected={EXPECTED_HYDRATED_CHECKSUM}, actual={checksum}"
        raise RuntimeError(message)
    binding_count = sum(len(row["parameter_bindings"]) for row in rows)
    conditional_bindings = [
        binding
        for row in rows
        for binding in row["parameter_bindings"]
        if binding.get("selection_mode") == "conditional"
    ]
    conditional_levers = {
        row["lever_code"]
        for row in rows
        if any(binding.get("selection_mode") == "conditional" for binding in row["parameter_bindings"])
    }
    parameter_names = {str(binding["parameter_name"]) for row in rows for binding in row["parameter_bindings"]}
    executable_parameter_names = {
        str(binding["parameter_name"])
        for row in rows
        for binding in row["parameter_bindings"]
        if _resolve_binding_support(
            requested_status=str(binding.get("support_status") or "known_unsupported"),
            master_use_yn=master_use_by_name[str(binding["parameter_name"])],
            requested_reason_code=binding.get("unsupported_reason_code"),
        )[0]
        == "executable"
    }
    executable_binding_count = sum(
        1
        for row in rows
        for binding in row["parameter_bindings"]
        if _resolve_binding_support(
            requested_status=str(binding.get("support_status") or "known_unsupported"),
            master_use_yn=master_use_by_name[str(binding["parameter_name"])],
            requested_reason_code=binding.get("unsupported_reason_code"),
        )[0]
        == "executable"
    )
    if (
        len(rows) != 21
        or binding_count != 56
        or len(conditional_bindings) != 41
        or len(conditional_levers) != 6
        or len(parameter_names) != 17
        or len(executable_parameter_names) != 17
        or executable_binding_count != 56
    ):
        message = "v4.1 v0050 catalog cardinality differs from the reviewed split contract"
        raise RuntimeError(message)

    return {
        "canonical_version": CANONICAL_VERSION,
        "source_catalog_version": "v4.1",
        "source_catalog_checksum": SOURCE_HYDRATED_CHECKSUM,
        "catalog_version": CATALOG_VERSION,
        "hydrated_catalog_checksum": checksum,
        "audit_user": AUDIT_USER,
        "generated_from_canonical": SOURCE_PATH.relative_to(ROOT).as_posix(),
        "source_canonical_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "master_canonical": MASTER_PATH.relative_to(ROOT).as_posix(),
        "impact_lever_count": len(rows),
        "binding_occurrence_count": binding_count,
        "effective_executable_binding_occurrence_count": executable_binding_count,
        "conditional_binding_occurrence_count": len(conditional_bindings),
        "conditional_binding_lever_count": len(conditional_levers),
        "parameter_reference_count": len(parameter_names),
        "executable_parameter_count": len(executable_parameter_names),
        "lever_full_set": sorted(str(row["lever_code"]) for row in rows),
        "impact_levers": rows,
    }


def main() -> None:
    TARGET_PATH.write_text(
        json.dumps(build_document(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
