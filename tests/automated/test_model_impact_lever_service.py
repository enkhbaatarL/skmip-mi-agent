# Copyright (c) 2026 SK Innovation E&S.
# ruff: noqa: S101
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from apps.common.exceptions.custom import MIBaseError
from apps.persistence.model_impact_lever.service import (
    _hydrate_catalog,
    resolve_binding_support,
)


ROOT_DIR = Path(__file__).resolve().parents[2]
MODEL_PARAMETER_CANONICAL_PATH = ROOT_DIR / "scripts/model_parameter/model-parameter-canonical-v4.json"
IMPACT_LEVER_CANONICAL_PATH = ROOT_DIR / "scripts/model_parameter/model-impact-lever-canonical-v4.json"


def _load_json(path: Path) -> dict[str, object]:
    document = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(document, dict)
    return document


def _repository_from_v4_canonical() -> SimpleNamespace:
    model_parameter = _load_json(MODEL_PARAMETER_CANONICAL_PATH)
    impact_lever = _load_json(IMPACT_LEVER_CANONICAL_PATH)
    master = model_parameter["master"]
    levers = impact_lever["impact_levers"]
    assert isinstance(master, list)
    assert isinstance(levers, list)
    definitions = [
        {
            "canonical_parameter_name": row["parameter_name"],
            "use_yn": row["use_yn"],
        }
        for row in master
    ]
    ordered_levers = sorted(
        levers,
        key=lambda row: (str(row["domain"]), str(row["lever_code"])),
    )
    return SimpleNamespace(
        fetch_active_impact_levers=lambda: ordered_levers,
        fetch_parameter_definitions_by_names=lambda _names: definitions,
    )


def test_binding_support_distinguishes_active_and_inactive_master_rows() -> None:
    assert resolve_binding_support(
        requested_status="executable",
        master_use_yn="Y",
        requested_reason_code=None,
    ) == ("executable", None)
    assert resolve_binding_support(
        requested_status="executable",
        master_use_yn="N",
        requested_reason_code=None,
    ) == ("known_unsupported", "INACTIVE_MODEL_PARAMETER")


def test_catalog_marked_unsupported_remains_distinguishable() -> None:
    assert resolve_binding_support(
        requested_status="known_unsupported",
        master_use_yn="Y",
        requested_reason_code=None,
    ) == ("known_unsupported", "CATALOG_MARKED_UNSUPPORTED")


def test_v4_catalog_hydration_has_20_raw_18_effective_and_16_unique_names() -> None:
    expected = _load_json(IMPACT_LEVER_CANONICAL_PATH)

    catalog, version, checksum = _hydrate_catalog(
        _repository_from_v4_canonical(),
    )

    bindings = [binding for lever in catalog for binding in lever.parameter_bindings]
    statuses = Counter(binding.support_status for binding in bindings)
    executable_names = {binding.parameter_name for binding in bindings if binding.support_status == "executable"}
    unsupported = {
        binding.parameter_name: binding.unsupported_reason_code
        for binding in bindings
        if binding.support_status == "known_unsupported"
    }

    assert len(catalog) == 16
    assert version == "v4"
    assert checksum == expected["hydrated_catalog_checksum"]
    assert len(bindings) == 20
    assert statuses == {"executable": 18, "known_unsupported": 2}
    assert len(executable_names) == 16
    assert executable_names == set(expected["active_parameter_names"])
    assert unsupported == {
        "CDD": "INACTIVE_MODEL_PARAMETER",
        "HDD": "INACTIVE_MODEL_PARAMETER",
    }


def test_catalog_hydration_rejects_mixed_active_versions() -> None:
    repository = _repository_from_v4_canonical()
    levers = repository.fetch_active_impact_levers()
    levers[0] = {**levers[0], "catalog_version": "v3"}
    repository.fetch_active_impact_levers = lambda: levers

    with pytest.raises(MIBaseError) as caught:
        _hydrate_catalog(repository)

    assert "mixed versions" in caught.value.error_message
