# Copyright (c) 2026 SK Innovation E&S.
# ruff: noqa: S101

from __future__ import annotations

from pathlib import Path
from types import MappingProxyType

import pytest

from apps.agents.model_parameter_agent.utils.lut.catalog import LutCatalog
from apps.agents.model_parameter_agent.utils.lut.domain import (
    build_basecase_index,
    build_slot_catalog,
    resolve_effective_reference,
)
from apps.agents.model_parameter_agent.utils.lut.keys import canonical_key_from_axes
from apps.agents.model_parameter_agent.utils.lut.models import (
    LutRecord,
    ReferenceLoadPolicy,
    freeze_mapping,
)
from apps.agents.model_parameter_agent.utils.lut.registry import (
    ParameterSpecRegistry,
    load_parameter_spec_registry,
)


PARAMETER_NAME = "TestParameter"
KEY_AXES = ("Country", "Year")


def _registry(tmp_path: Path) -> ParameterSpecRegistry:
    config = b"""\
TestParameter:
  adapter: tabular
  layout: row
  files:
    values:
      path: values.csv
      axis_columns:
        Country: Country
        Year: Year
      value_column: Value
  key_axes: [Country, Year]
"""
    return load_parameter_spec_registry(
        tmp_path / "registry.yaml",
        lut_root=tmp_path,
        yaml_bytes=config,
    )


def _candidate(candidate_key: str) -> dict[str, str]:
    return {
        "candidate_key": candidate_key,
        "canonical_parameter_name": PARAMETER_NAME,
    }


def _basecase_record(
    candidate_key: str,
    country: str,
    value: float,
) -> dict[str, object]:
    return {
        "candidate_key": candidate_key,
        "reference_id": f"base:{candidate_key}:{country}",
        "axes": {"Country": country, "Year": 2026},
        "value": value,
    }


def _lut_catalog(
    registry: ParameterSpecRegistry,
    policy: ReferenceLoadPolicy,
) -> LutCatalog:
    records = tuple(
        LutRecord(
            parameter_name=PARAMETER_NAME,
            canonical_key=canonical_key_from_axes(axes, KEY_AXES),
            axes=freeze_mapping(axes),
            value=value,
            metadata=freeze_mapping(),
            reference_id=f"lut:{country}",
        )
        for country, value in (("A", 1.0), ("B", 2.0))
        for axes in ({"Country": country, "Year": 2026},)
    )
    return LutCatalog(
        version="test-lut-v1",
        policy=policy,
        registry=registry,
        records=records,
        diagnostics=(),
        _by_parameter=MappingProxyType(
            {
                PARAMETER_NAME: MappingProxyType(
                    {record.canonical_key: record for record in records},
                ),
            },
        ),
    )


def test_blocked_basecase_key_is_immutable_and_candidate_scoped(tmp_path: Path) -> None:
    registry = _registry(tmp_path)
    source_keys = {("A", 2026)}
    candidates = [_candidate("candidate-a"), _candidate("candidate-b")]
    index = build_basecase_index(
        [
            _basecase_record("candidate-a", "A", 10.0),
            _basecase_record("candidate-a", "B", 11.0),
            _basecase_record("candidate-b", "A", 20.0),
        ],
        candidates,
        registry=registry,
        blocked_exact_keys_by_candidate={"candidate-a": source_keys},
    )

    source_keys.add(("B", 2026))

    assert index.blocked_exact_keys_by_candidate["candidate-a"] == frozenset({("A", 2026)})
    assert index.blocked_exact_keys_by_candidate["candidate-b"] == frozenset()
    with pytest.raises(TypeError):
        index.blocked_exact_keys_by_candidate["candidate-a"] = frozenset()  # type: ignore[index]

    assert resolve_effective_reference("candidate-a", {"Country": "A", "Year": 2026}, index) is None
    candidate_b_reference = resolve_effective_reference(
        "candidate-b",
        {"Country": "A", "Year": 2026},
        index,
    )
    assert candidate_b_reference is not None
    assert candidate_b_reference.llm_reference_value == 20

    slot_catalog = build_slot_catalog(index)
    assert not slot_catalog.contains("candidate-a", {"Country": "A", "Year": 2026})
    assert slot_catalog.contains("candidate-a", {"Country": "B", "Year": 2026})
    assert slot_catalog.contains("candidate-b", {"Country": "A", "Year": 2026})


def test_blocked_lut_only_key_is_not_reintroduced_into_slot_union(tmp_path: Path) -> None:
    registry = _registry(tmp_path)
    policy = ReferenceLoadPolicy(start_year=2026, end_year=2026)
    lut_catalog = _lut_catalog(registry, policy)
    index = build_basecase_index(
        [],
        [_candidate("candidate")],
        policy=policy,
        registry=registry,
        blocked_exact_keys_by_candidate={"candidate": {("A", 2026)}},
    )

    slot_catalog = build_slot_catalog(index, lut_catalog)

    assert not slot_catalog.contains("candidate", {"Country": "A", "Year": 2026})
    assert slot_catalog.contains("candidate", {"Country": "B", "Year": 2026})
    assert (
        resolve_effective_reference(
            "candidate",
            {"Country": "A", "Year": 2026},
            index,
            lut_catalog,
        )
        is None
    )
    fallback = resolve_effective_reference(
        "candidate",
        {"Country": "B", "Year": 2026},
        index,
        lut_catalog,
    )
    assert fallback is not None
    assert fallback.effective_source == "lut"
    assert fallback.llm_reference_value == 2


def test_omitted_blocked_keys_preserve_basecase_priority_and_lut_fallback(tmp_path: Path) -> None:
    registry = _registry(tmp_path)
    policy = ReferenceLoadPolicy(start_year=2026, end_year=2026)
    lut_catalog = _lut_catalog(registry, policy)
    index = build_basecase_index(
        [_basecase_record("candidate", "A", 10.0)],
        [_candidate("candidate")],
        policy=policy,
        registry=registry,
    )

    slot_catalog = build_slot_catalog(index, lut_catalog)
    basecase = resolve_effective_reference(
        "candidate",
        {"Country": "A", "Year": 2026},
        index,
        lut_catalog,
    )
    fallback = resolve_effective_reference(
        "candidate",
        {"Country": "B", "Year": 2026},
        index,
        lut_catalog,
    )

    assert index.blocked_exact_keys_by_candidate["candidate"] == frozenset()
    assert slot_catalog.contains("candidate", {"Country": "A", "Year": 2026})
    assert slot_catalog.contains("candidate", {"Country": "B", "Year": 2026})
    assert basecase is not None
    assert basecase.effective_source == "basecase"
    assert basecase.llm_reference_value == 10
    assert fallback is not None
    assert fallback.effective_source == "lut"
    assert fallback.llm_reference_value == 2
