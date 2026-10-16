# Copyright (c) 2026 SK Innovation E&S.

from __future__ import annotations

from functools import lru_cache
import hashlib
import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode


PACKAGE_RESOURCE_DIR = Path(__file__).resolve().parents[1] / "resources"
DEFAULT_PROPOSAL_CAPABILITY_CONTRACT_PATH = (
    PACKAGE_RESOURCE_DIR / "contracts/model-parameter-proposal-capabilities-v5.json"
)
EXPECTED_EXTEND17_PARAMETER_IDS = frozenset(
    {4, 6, 7, 8, 11, 12, 13, 14, 15, 16, 17, 18, 20, 22, 23, 25, 26},
)
EXPECTED_COMPATIBILITY_PARAMETER_IDS = frozenset(
    {*EXPECTED_EXTEND17_PARAMETER_IDS, 24},
)
EXPECTED_EXTEND17_RELEASE_ID = "extend17-v9"
EXPECTED_CATALOG_CHECKSUMS = {
    "v4.0": "b9d8c051872b39903cc3b4d2f19cd00570156eecd82295f0d2b02fd042c4000b",
    "v4.1": "467749ea59c3af7e875669be23da00c0fd8ef7c226256f9518a5945e36e4d7c4",
}
CatalogVersion = Literal["v4.0", "v4.1"]


class ProposalModelTarget(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    model_file: str
    model_sheet: str
    model_table: str


class ProposalCapabilityEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    model_param_id: int = Field(gt=0)
    parameter_name: str = Field(min_length=1)
    catalog_versions: tuple[CatalogVersion, ...] = Field(min_length=1)
    model_target: ProposalModelTarget
    reference_mode: Literal["v4_workbook_then_lut"]
    exact_axes: tuple[str, ...] = Field(min_length=1)
    evidence_policy: Literal["explicit_or_unique_inferred"]
    constraints: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_exact_axes(self) -> ProposalCapabilityEntry:
        if len(self.exact_axes) != len(set(self.exact_axes)):
            msg = f"duplicate exact axis: modelParamId={self.model_param_id}"
            raise ValueError(msg)
        if len(self.catalog_versions) != len(set(self.catalog_versions)):
            msg = f"duplicate catalog version: modelParamId={self.model_param_id}"
            raise ValueError(msg)
        return self


class ProposalCapabilityContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["model-parameter-proposal-capabilities-v5"]
    release_id: Literal["extend17-v9"]
    current_catalog_version: Literal["v4.1"]
    catalog_checksums: dict[CatalogVersion, str]
    parameters: tuple[ProposalCapabilityEntry, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_release(self) -> ProposalCapabilityContract:
        ids = [item.model_param_id for item in self.parameters]
        names = [item.parameter_name for item in self.parameters]
        if len(ids) != len(set(ids)):
            msg = "duplicate modelParamId in proposal capability contract"
            raise ValueError(msg)
        if len(names) != len(set(names)):
            msg = "duplicate parameterName in proposal capability contract"
            raise ValueError(msg)
        if frozenset(ids) != EXPECTED_COMPATIBILITY_PARAMETER_IDS:
            msg = (
                "extend17 compatibility capability IDs differ: "
                f"expected={sorted(EXPECTED_COMPATIBILITY_PARAMETER_IDS)}, actual={sorted(ids)}"
            )
            raise ValueError(msg)
        if self.catalog_checksums != EXPECTED_CATALOG_CHECKSUMS:
            msg = "extend17 proposal capability catalog checksums differ from the reviewed v4/v4.1 contracts"
            raise ValueError(msg)
        ids_by_version = {
            version: frozenset(
                item.model_param_id
                for item in self.parameters
                if version in item.catalog_versions
            )
            for version in EXPECTED_CATALOG_CHECKSUMS
        }
        legacy_ids = frozenset(
            {4, 6, 7, 8, 11, 12, 13, 14, 15, 16, 17, 18, 20, 22, 23, 24},
        )
        if ids_by_version["v4.0"] != legacy_ids:
            msg = "legacy v4.0 capability scope must remain pinned to the CanalToll contract"
            raise ValueError(msg)
        if ids_by_version["v4.1"] != EXPECTED_EXTEND17_PARAMETER_IDS:
            msg = "v4.1 capability scope must use the split Suez/Panama parameters"
            raise ValueError(msg)
        return self

    @property
    def by_id(self) -> dict[int, ProposalCapabilityEntry]:
        return {item.model_param_id: item for item in self.parameters}

    @property
    def by_name(self) -> dict[str, ProposalCapabilityEntry]:
        return {item.parameter_name: item for item in self.parameters}

    def parameters_for(
        self,
        catalog_version: CatalogVersion,
    ) -> tuple[ProposalCapabilityEntry, ...]:
        return tuple(
            item
            for item in self.parameters
            if catalog_version in item.catalog_versions
        )


def proposal_capability_contract_sha256(path: Path | str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@lru_cache(maxsize=4)
def load_proposal_capability_contract(
    path: Path | str = DEFAULT_PROPOSAL_CAPABILITY_CONTRACT_PATH,
) -> ProposalCapabilityContract:
    contract_path = Path(path).expanduser().resolve(strict=True)
    try:
        document = json.loads(contract_path.read_text(encoding="utf-8"))
        return ProposalCapabilityContract.model_validate(document)
    except (OSError, ValueError) as exc:
        raise MIBaseError(
            ErrorCode.INVALID_REQUEST,
            detail=f"Invalid model parameter proposal capability contract: path={contract_path}, error={exc}",
        ) from exc


def validate_v4_candidate_capability(
    candidate: dict[str, Any],
    *,
    contract: ProposalCapabilityContract | None = None,
) -> ProposalCapabilityEntry | None:
    active_contract = contract
    if active_contract is None:
        from apps.agents.model_parameter_agent.utils.resource_runtime import (
            get_registered_model_parameter_resource_paths,
        )

        runtime_paths = get_registered_model_parameter_resource_paths()
        active_contract = (
            runtime_paths.proposal_capability_contract
            if runtime_paths is not None and runtime_paths.proposal_capability_contract is not None
            else load_proposal_capability_contract()
        )
    parameter_name = str(
        candidate.get("canonical_parameter_name") or candidate.get("parameter_name") or "",
    ).strip()
    capability = active_contract.by_name.get(parameter_name)
    if capability is None:
        return None
    catalog_version = str(candidate.get("impact_catalog_version") or "").strip()
    if not catalog_version:
        raise MIBaseError(
            ErrorCode.INVALID_REQUEST,
            detail=f"v4 proposal candidate is missing impactCatalogVersion: parameter={parameter_name}",
        )
    if catalog_version not in capability.catalog_versions:
        return None
    expected_checksum = active_contract.catalog_checksums.get(catalog_version)
    candidate_checksum = str(candidate.get("impact_catalog_checksum") or "").strip()
    if candidate_checksum and candidate_checksum != expected_checksum:
        raise MIBaseError(
            ErrorCode.INVALID_REQUEST,
            detail=(
                "v4 proposal candidate catalog checksum differs from the capability contract: "
                f"parameter={parameter_name}, catalogVersion={catalog_version}"
            ),
        )
    try:
        model_param_id = int(candidate.get("model_param_id"))
    except (TypeError, ValueError) as exc:
        raise MIBaseError(
            ErrorCode.INVALID_REQUEST,
            detail=f"v4 proposal candidate is missing modelParamId: parameter={parameter_name}",
        ) from exc
    target = capability.model_target
    actual_target = (
        str(candidate.get("model_file") or ""),
        str(candidate.get("model_sheet") or ""),
        str(candidate.get("model_table") or ""),
    )
    expected_target = (target.model_file, target.model_sheet, target.model_table)
    if model_param_id != capability.model_param_id or actual_target != expected_target:
        raise MIBaseError(
            ErrorCode.INVALID_REQUEST,
            detail=(
                "v4 proposal candidate does not match the extend17 capability contract: "
                f"parameter={parameter_name}, expectedId={capability.model_param_id}, actualId={model_param_id}, "
                f"expectedTarget={expected_target}, actualTarget={actual_target}"
            ),
        )
    return capability
