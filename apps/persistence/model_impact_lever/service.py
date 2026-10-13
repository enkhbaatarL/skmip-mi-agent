# Copyright (c) 2026 SK Innovation E&S.

from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy.orm import Session

from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode
from apps.persistence.model_impact_lever.repository import ModelImpactLeverRepository
from apps.persistence.model_impact_lever.schema import (
    KnownUnsupportedReasonCode,
    ModelImpactLeverPayload,
)


def resolve_binding_support(
    *,
    requested_status: str,
    master_use_yn: str,
    requested_reason_code: str | None,
) -> tuple[str, KnownUnsupportedReasonCode | None]:
    """Resolve a catalog capability against the canonical master switch."""
    if requested_status == "executable" and master_use_yn == "Y":
        return "executable", None
    if requested_status == "executable":
        return "known_unsupported", "INACTIVE_MODEL_PARAMETER"
    if requested_reason_code == "INACTIVE_MODEL_PARAMETER":
        return "known_unsupported", "INACTIVE_MODEL_PARAMETER"
    return "known_unsupported", "CATALOG_MARKED_UNSUPPORTED"


def _hydrate_catalog(
    repository: ModelImpactLeverRepository,
    *,
    catalog_version: str,
) -> tuple[list[ModelImpactLeverPayload], str, str]:
    requested_version = catalog_version.strip()
    if not requested_version:
        raise MIBaseError(
            ErrorCode.INVALID_REQUEST,
            detail="Model impact lever catalog version is required",
        )
    raw_levers = repository.fetch_active_impact_levers(
        catalog_version=requested_version,
    )
    parameter_names = [
        str(binding.get("parameter_name") or "")
        for lever in raw_levers
        for binding in lever.get("parameter_bindings") or []
        if isinstance(binding, dict)
    ]
    definitions = repository.fetch_parameter_definitions_by_names(parameter_names)
    definition_by_name = {str(definition["canonical_parameter_name"]): definition for definition in definitions}

    hydrated: list[ModelImpactLeverPayload] = []
    for raw_lever in raw_levers:
        bindings: list[dict[str, Any]] = []
        for raw_binding in raw_lever.get("parameter_bindings") or []:
            if not isinstance(raw_binding, dict):
                continue
            parameter_name = str(raw_binding.get("parameter_name") or "").strip()
            definition = definition_by_name.get(parameter_name)
            if definition is None:
                raise MIBaseError(
                    ErrorCode.INVALID_REQUEST,
                    detail=(
                        "Impact lever references an unknown model parameter: "
                        f"leverCode={raw_lever.get('lever_code')}, parameterName={parameter_name}"
                    ),
                )
            requested_status = str(
                raw_binding.get("support_status") or "known_unsupported",
            )
            support_status, unsupported_reason_code = resolve_binding_support(
                requested_status=requested_status,
                master_use_yn=str(definition.get("use_yn") or "N"),
                requested_reason_code=raw_binding.get("unsupported_reason_code"),
            )
            bindings.append(
                {
                    "parameter_name": parameter_name,
                    "role": raw_binding.get("role") or "primary",
                    "selection_mode": raw_binding.get("selection_mode") or "deterministic",
                    "applicability": raw_binding.get("applicability") or "",
                    "support_status": support_status,
                    "unsupported_reason_code": unsupported_reason_code,
                },
            )
        hydrated.append(
            ModelImpactLeverPayload.model_validate(
                {**raw_lever, "parameter_bindings": bindings},
            ),
        )

    versions = sorted({lever.catalog_version for lever in hydrated})
    if not versions:
        raise MIBaseError(
            ErrorCode.INVALID_REQUEST,
            detail=(f"Active model impact lever catalog is empty: catalogVersion={requested_version}"),
        )
    if versions != [requested_version]:
        raise MIBaseError(
            ErrorCode.INVALID_REQUEST,
            detail=(
                "Active model impact lever catalog does not match the requested version: "
                f"requested={requested_version}, actual={versions}"
            ),
        )
    version = requested_version
    checksum_payload: list[dict[str, Any]] = []
    for lever in hydrated:
        lever_payload = lever.model_dump(mode="json", exclude={"impact_lever_id"})
        for binding in lever_payload.get("parameter_bindings") or []:
            if binding.get("selection_mode") == "deterministic":
                binding.pop("selection_mode", None)
        checksum_payload.append(lever_payload)
    checksum = hashlib.sha256(
        json.dumps(
            checksum_payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8"),
    ).hexdigest()
    return hydrated, version, checksum


class ModelImpactLeverService:
    """Shared catalog hydration for Scenario and Model Parameter agents."""

    def __init__(self, *, session: Session | None = None) -> None:
        self._session = session

    def load_active_catalog(
        self,
        *,
        catalog_version: str,
    ) -> tuple[list[ModelImpactLeverPayload], str, str]:
        if self._session is not None:
            return _hydrate_catalog(
                ModelImpactLeverRepository(session=self._session),
                catalog_version=catalog_version,
            )

        from apps.common.configs.database.sync_database.connection import (
            get_sync_session,
        )

        session = get_sync_session()
        try:
            return _hydrate_catalog(
                ModelImpactLeverRepository(session=session),
                catalog_version=catalog_version,
            )
        finally:
            session.close()

    def load_parameter_semantic_axes(self, levers: list[ModelImpactLeverPayload]) -> dict[str, str]:
        """Return each bound model parameter's semantic_axes (required slots and value ranges).

        Kept outside the hydrated catalog so the catalog checksum pinned by stored Scenario Groups does not change.
        """
        parameter_names = [binding.parameter_name for lever in levers for binding in lever.parameter_bindings]
        if not parameter_names:
            return {}
        if self._session is not None:
            definitions = ModelImpactLeverRepository(session=self._session).fetch_parameter_definitions_by_names(
                parameter_names,
            )
        else:
            from apps.common.configs.database.sync_database.connection import (
                get_sync_session,
            )

            session = get_sync_session()
            try:
                definitions = ModelImpactLeverRepository(session=session).fetch_parameter_definitions_by_names(
                    parameter_names,
                )
            finally:
                session.close()
        return {
            str(definition["canonical_parameter_name"]): str(definition.get("semantic_axes") or "")
            for definition in definitions
        }


__all__ = ["ModelImpactLeverService", "resolve_binding_support"]
