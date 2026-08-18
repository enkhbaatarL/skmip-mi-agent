from __future__ import annotations

import hashlib
import json
from typing import Any

from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode
from apps.persistence.model_impact_lever.repository import ModelImpactLeverRepository
from apps.persistence.model_impact_lever.schema import KnownUnsupportedReasonCode, ModelImpactLeverPayload


def _resolve_binding_support(
    *,
    requested_status: str,
    master_use_yn: str,
    requested_reason_code: str | None,
) -> tuple[str, KnownUnsupportedReasonCode | None]:
    if requested_status == "executable" and master_use_yn == "Y":
        return "executable", None
    if requested_status == "executable":
        return "known_unsupported", "INACTIVE_MODEL_PARAMETER"
    if requested_reason_code == "INACTIVE_MODEL_PARAMETER":
        return "known_unsupported", "INACTIVE_MODEL_PARAMETER"
    return "known_unsupported", "CATALOG_MARKED_UNSUPPORTED"


class ModelImpactLeverService:
    def load_display_labels(self) -> dict[str, str]:
        """Load current screen labels without validating model-parameter bindings."""
        from apps.common.configs.database.sync_database.connection import get_sync_session

        session = get_sync_session()
        try:
            return ModelImpactLeverRepository(session=session).fetch_display_labels()
        finally:
            session.close()

    def load_active_catalog(self) -> tuple[list[ModelImpactLeverPayload], str, str]:
        from apps.common.configs.database.sync_database.connection import get_sync_session

        session = get_sync_session()
        try:
            repository = ModelImpactLeverRepository(session=session)
            raw_levers = repository.fetch_active_impact_levers()
            parameter_names = [
                str(binding.get("parameter_name") or "")
                for lever in raw_levers
                for binding in lever.get("parameter_bindings") or []
                if isinstance(binding, dict)
            ]
            definitions = repository.fetch_parameter_definitions_by_names(parameter_names)
        finally:
            session.close()

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
                requested_status = str(raw_binding.get("support_status") or "known_unsupported")
                support_status, unsupported_reason_code = _resolve_binding_support(
                    requested_status=requested_status,
                    master_use_yn=str(definition.get("use_yn") or "N"),
                    requested_reason_code=raw_binding.get("unsupported_reason_code"),
                )
                bindings.append(
                    {
                        "parameter_name": parameter_name,
                        "role": raw_binding.get("role") or "primary",
                        "applicability": raw_binding.get("applicability") or "",
                        "support_status": support_status,
                        "unsupported_reason_code": unsupported_reason_code,
                    },
                )
            hydrated.append(ModelImpactLeverPayload.model_validate({**raw_lever, "parameter_bindings": bindings}))

        versions = sorted({lever.catalog_version for lever in hydrated})
        version = "+".join(versions)
        checksum_payload = [lever.model_dump(mode="json", exclude={"impact_lever_id"}) for lever in hydrated]
        checksum = hashlib.sha256(
            json.dumps(
                checksum_payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8"),
        ).hexdigest()
        return hydrated, version, checksum
