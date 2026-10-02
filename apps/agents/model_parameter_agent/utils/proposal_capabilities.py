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
    PACKAGE_RESOURCE_DIR / "contracts/model-parameter-proposal-capabilities-v4.json"
)
EXPECTED_EXTEND14_PARAMETER_IDS = frozenset({4, 6, 7, 8, 9, 11, 12, 13, 14, 15, 16, 17, 18, 20})
EXPECTED_EXTEND14_RELEASE_ID = "extend14-v6"
EXPECTED_EXTEND14_CATALOG_CHECKSUM = "416017351f2b9539370963a3ca413914876da55a1db3f41e3dacd34bd466c763"


class ProposalModelTarget(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    model_file: str
    model_sheet: str
    model_table: str


class ProposalCapabilityEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    model_param_id: int = Field(gt=0)
    parameter_name: str = Field(min_length=1)
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
        return self


class ProposalCapabilityContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["model-parameter-proposal-capabilities-v4"]
    release_id: Literal["extend14-v6"]
    catalog_version: Literal["v4.0"]
    catalog_checksum: str
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
        if frozenset(ids) != EXPECTED_EXTEND14_PARAMETER_IDS:
            msg = (
                "extend14 proposal capability IDs differ: "
                f"expected={sorted(EXPECTED_EXTEND14_PARAMETER_IDS)}, actual={sorted(ids)}"
            )
            raise ValueError(msg)
        if self.catalog_checksum != EXPECTED_EXTEND14_CATALOG_CHECKSUM:
            msg = "extend14 proposal capability catalog checksum differs from the v4.0 catalog contract"
            raise ValueError(msg)
        return self

    @property
    def by_id(self) -> dict[int, ProposalCapabilityEntry]:
        return {item.model_param_id: item for item in self.parameters}

    @property
    def by_name(self) -> dict[str, ProposalCapabilityEntry]:
        return {item.parameter_name: item for item in self.parameters}


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
                "v4 proposal candidate does not match the extend14 capability contract: "
                f"parameter={parameter_name}, expectedId={capability.model_param_id}, actualId={model_param_id}, "
                f"expectedTarget={expected_target}, actualTarget={actual_target}"
            ),
        )
    return capability
