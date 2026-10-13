# Copyright (c) 2026 SK Innovation E&S.
# ruff: noqa: S101
from __future__ import annotations

from collections import Counter
from collections.abc import Callable
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from apps.agents.scenario_group_agent.persistence.model_impact_lever_service import (
    ModelImpactLeverService as ScenarioModelImpactLeverService,
    _resolve_binding_support,
)
from apps.common.exceptions.custom import MIBaseError
from apps.persistence.model_impact_lever.repository import ModelImpactLeverRepository
from apps.persistence.model_impact_lever.service import (
    ModelImpactLeverService as SharedModelImpactLeverService,
    _hydrate_catalog,
    resolve_binding_support,
)


ROOT_DIR = Path(__file__).resolve().parents[2]
MODEL_PARAMETER_CANONICAL_PATH = ROOT_DIR / "scripts/model_parameter/model-parameter-canonical-v4-0030.json"
IMPACT_LEVER_CANONICAL_PATH = ROOT_DIR / "scripts/model_parameter/model-impact-lever-canonical-v4-0030.json"
BindingSupportResolver = Callable[..., tuple[str, str | None]]
EXPECTED_0030_CHECKSUM = "835e6f2d4eb77f5e7aedc9ffe8b90bc73288242d2e9dc764a019f1bea962be51"


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
        fetch_active_impact_levers=lambda *, catalog_version: [
            row for row in ordered_levers if row["catalog_version"] == catalog_version
        ],
        fetch_parameter_definitions_by_names=lambda _names: definitions,
    )


def test_display_labels_require_matching_catalog_pin_and_close_session() -> None:
    session = MagicMock()
    labels = {
        "inventory_condition": "재고 여건",
        "regional_price_spread": "지역 가격 스프레드",
    }
    connection_module = ModuleType("apps.common.configs.database.sync_database.connection")
    connection_module.get_sync_session = MagicMock(return_value=session)
    with (
        patch.dict(
            sys.modules,
            {"apps.common.configs.database.sync_database.connection": connection_module},
        ),
        patch.object(ModelImpactLeverRepository, "fetch_display_labels", return_value=labels) as fetch,
        patch(
            "apps.agents.scenario_group_agent.persistence.model_impact_lever_service."
            "SharedModelImpactLeverService.load_active_catalog",
            return_value=([], "v4", EXPECTED_0030_CHECKSUM),
        ) as load_catalog,
    ):
        result = ScenarioModelImpactLeverService().load_display_labels(
            catalog_version="v4",
            catalog_checksum=EXPECTED_0030_CHECKSUM,
        )

    assert result == labels
    load_catalog.assert_called_once_with(catalog_version="v4")
    fetch.assert_called_once_with(catalog_version="v4")
    session.close.assert_called_once_with()


def test_display_labels_skip_enrichment_when_catalog_checksum_is_stale() -> None:
    session = MagicMock()
    connection_module = ModuleType("apps.common.configs.database.sync_database.connection")
    connection_module.get_sync_session = MagicMock(return_value=session)
    with (
        patch.dict(
            sys.modules,
            {"apps.common.configs.database.sync_database.connection": connection_module},
        ),
        patch.object(ModelImpactLeverRepository, "fetch_display_labels") as fetch,
        patch(
            "apps.agents.scenario_group_agent.persistence.model_impact_lever_service."
            "SharedModelImpactLeverService.load_active_catalog",
            return_value=([], "v4", EXPECTED_0030_CHECKSUM),
        ),
    ):
        result = ScenarioModelImpactLeverService().load_display_labels(
            catalog_version="v4",
            catalog_checksum="a4af2e5bbb90f3a76e9e0aab3a16091015898031a97a271ebcf35ca67f4dc6cd",
        )

    assert result == {}
    fetch.assert_not_called()
    session.close.assert_called_once_with()


@pytest.mark.parametrize(
    "resolver",
    [_resolve_binding_support, resolve_binding_support],
    ids=["scenario-agent", "shared-persistence"],
)
def test_binding_support_distinguishes_active_and_inactive_master_rows(
    resolver: BindingSupportResolver,
) -> None:
    assert resolver(
        requested_status="executable",
        master_use_yn="Y",
        requested_reason_code=None,
    ) == ("executable", None)
    assert resolver(
        requested_status="executable",
        master_use_yn="N",
        requested_reason_code=None,
    ) == ("known_unsupported", "INACTIVE_MODEL_PARAMETER")


@pytest.mark.parametrize(
    "resolver",
    [_resolve_binding_support, resolve_binding_support],
    ids=["scenario-agent", "shared-persistence"],
)
def test_catalog_marked_unsupported_remains_distinguishable(
    resolver: BindingSupportResolver,
) -> None:
    assert resolver(
        requested_status="known_unsupported",
        master_use_yn="Y",
        requested_reason_code=None,
    ) == ("known_unsupported", "CATALOG_MARKED_UNSUPPORTED")


def test_v4_catalog_hydration_matches_0030_counts_and_checksum() -> None:
    expected = _load_json(IMPACT_LEVER_CANONICAL_PATH)

    catalog, version, checksum = _hydrate_catalog(
        _repository_from_v4_canonical(),
        catalog_version="v4",
    )

    bindings = [binding for lever in catalog for binding in lever.parameter_bindings]
    statuses = Counter(binding.support_status for binding in bindings)
    executable_names = {binding.parameter_name for binding in bindings if binding.support_status == "executable"}
    unsupported = {
        binding.parameter_name: binding.unsupported_reason_code
        for binding in bindings
        if binding.support_status == "known_unsupported"
    }

    assert len(catalog) == 18
    assert version == "v4"
    assert expected["hydrated_catalog_checksum"] == EXPECTED_0030_CHECKSUM
    assert checksum == EXPECTED_0030_CHECKSUM
    assert len(bindings) == 16
    assert statuses == {"executable": 14, "known_unsupported": 2}
    assert len(executable_names) == 14
    assert executable_names == set(expected["active_parameter_names"])
    assert unsupported == {
        "CDD": "INACTIVE_MODEL_PARAMETER",
        "HDD": "INACTIVE_MODEL_PARAMETER",
    }


def test_catalog_hydration_rejects_mixed_active_versions() -> None:
    repository = _repository_from_v4_canonical()
    levers = repository.fetch_active_impact_levers(catalog_version="v4")
    levers[0] = {**levers[0], "catalog_version": "v3"}
    repository.fetch_active_impact_levers = lambda *, catalog_version: levers

    with pytest.raises(MIBaseError) as caught:
        _hydrate_catalog(repository, catalog_version="v4")

    assert "does not match the requested version" in caught.value.error_message


def test_catalog_checksum_ignores_parameter_semantic_axes() -> None:
    repository = _repository_from_v4_canonical()
    definitions = repository.fetch_parameter_definitions_by_names([])
    repository.fetch_parameter_definitions_by_names = lambda _names: [
        {**definition, "semantic_axes": "slot=B:Year(YYYY, 2026~2030)"} for definition in definitions
    ]

    _catalog, _version, checksum = _hydrate_catalog(repository, catalog_version="v4")

    # Stored Scenario Groups pin this checksum; slot metadata for prompts must not change it.
    assert checksum == EXPECTED_0030_CHECKSUM


def test_load_parameter_semantic_axes_maps_bound_parameters() -> None:
    catalog, _version, _checksum = _hydrate_catalog(_repository_from_v4_canonical(), catalog_version="v4")
    rows = [
        {"canonical_parameter_name": "ShippingCost", "use_yn": "Y", "semantic_axes": "slot=B:Year(YYYY, 2026~2030)"},
        {"canonical_parameter_name": "CDD", "use_yn": "N", "semantic_axes": None},
    ]
    with patch.object(ModelImpactLeverRepository, "fetch_parameter_definitions_by_names", return_value=rows) as fetch:
        axes = SharedModelImpactLeverService(session=MagicMock()).load_parameter_semantic_axes(catalog)

    requested = set(fetch.call_args.args[0])
    assert {"ShippingCost", "HurricaneIntensity", "CDD"} <= requested
    assert axes == {"ShippingCost": "slot=B:Year(YYYY, 2026~2030)", "CDD": ""}
