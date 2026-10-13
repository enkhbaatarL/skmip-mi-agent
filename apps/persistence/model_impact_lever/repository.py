from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import select

from apps.common.configs.database.sync_database.base import BaseSyncSQLRepository
from apps.persistence.model_impact_lever.models import MiModelImpactLeverModel
from apps.persistence.model_parameter.models import MiModelParamModel


def _json_safe(value: Any) -> Any:  # noqa: ANN401
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if hasattr(value, "value"):
        return value.value
    return value


class ModelImpactLeverRepository(BaseSyncSQLRepository):
    def fetch_display_labels(self, *, catalog_version: str) -> dict[str, str]:
        stmt = (
            select(
                MiModelImpactLeverModel.lever_code,
                MiModelImpactLeverModel.label,
            )
            .where(
                MiModelImpactLeverModel.catalog_version == catalog_version,
                MiModelImpactLeverModel.del_yn == "N",
            )
            .order_by(MiModelImpactLeverModel.lever_code)
        )
        return {
            str(lever_code): str(label)
            for lever_code, label in self.session.execute(stmt).all()
            if lever_code and label
        }

    def fetch_active_impact_levers(self, *, catalog_version: str) -> list[dict[str, Any]]:
        stmt = (
            select(MiModelImpactLeverModel)
            .where(
                MiModelImpactLeverModel.catalog_version == catalog_version,
                MiModelImpactLeverModel.del_yn == "N",
                MiModelImpactLeverModel.use_yn == "Y",
            )
            .order_by(
                MiModelImpactLeverModel.domain,
                MiModelImpactLeverModel.lever_code,
            )
        )
        return [
            {
                "impact_lever_id": int(lever.impact_lever_id),
                "lever_code": lever.lever_code,
                "domain": lever.domain,
                "label": lever.label,
                "description": lever.description,
                "applicability_hint": lever.applicability_hint,
                "parent_lever_code": lever.parent_lever_code,
                "parameter_bindings": _json_safe(lever.parameter_bindings or []),
                "catalog_version": lever.catalog_version,
            }
            for lever in self.session.execute(stmt).scalars().all()
        ]

    def fetch_parameter_definitions_by_names(self, parameter_names: list[str]) -> list[dict[str, Any]]:
        normalized = sorted({str(name).strip() for name in parameter_names if str(name).strip()})
        if not normalized:
            return []
        stmt = (
            select(MiModelParamModel)
            .where(
                MiModelParamModel.del_yn == "N",
                MiModelParamModel.parameter_name.in_(normalized),
            )
            .order_by(MiModelParamModel.model_param_id)
        )
        return [
            {
                "canonical_parameter_name": parameter.parameter_name,
                "use_yn": parameter.use_yn,
                "semantic_axes": parameter.semantic_axes,
            }
            for parameter in self.session.execute(stmt).scalars().all()
        ]
