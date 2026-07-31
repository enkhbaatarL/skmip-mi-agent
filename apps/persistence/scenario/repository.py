from __future__ import annotations

from typing import Any

from sqlalchemy import select

from apps.common.configs.database.sync_database.base import BaseSyncSQLRepository
from apps.persistence.scenario.models import (
    MiDimensionValueMappingModel,
    MiScenarioDimensionTemplateModel,
    MiScenarioModel,
)


class ScenarioRepository(BaseSyncSQLRepository):
    def _load_template_json_from_db(self, event_type_l2_id: int) -> Any | None:
        stmt = select(MiScenarioDimensionTemplateModel.template_json).where(
            MiScenarioDimensionTemplateModel.event_type_l2_id == event_type_l2_id,
            MiScenarioDimensionTemplateModel.del_yn == "N",
        )
        return self.session.execute(stmt).scalars().first()

    def fetch_template_model(
        self,
        event_type_l2_id: int,
    ) -> MiScenarioDimensionTemplateModel | None:
        stmt = (
            select(MiScenarioDimensionTemplateModel)
            .where(
                MiScenarioDimensionTemplateModel.event_type_l2_id == event_type_l2_id,
                MiScenarioDimensionTemplateModel.del_yn == "N",
            )
            .order_by(MiScenarioDimensionTemplateModel.scenario_dimension_template_id.desc())
            .limit(1)
        )
        return self.session.execute(stmt).scalars().first()

    def update_template_domain_knowledge(
        self,
        template: MiScenarioDimensionTemplateModel,
        *,
        event_type_definition: str,
        lng_price_impact_examples: str,
        template_json: list[dict[str, Any]],
        user_id: int,
    ) -> None:
        template.event_type_definition = event_type_definition
        template.lng_price_impact_examples = lng_price_impact_examples
        template.template_json = template_json
        template.mod_usr_logn_id = user_id
        self.session.flush()

    def fetch_model_by_id(self, scenario_id: int) -> MiScenarioModel | None:
        stmt = select(MiScenarioModel).where(
            MiScenarioModel.scenario_id == scenario_id,
            MiScenarioModel.del_yn == "N",
        )
        return self.session.execute(stmt).scalars().one_or_none()

    def fetch_dimension_template(self, event_type_l2_id: int) -> list[dict[str, Any]]:
        raw = self._load_template_json_from_db(event_type_l2_id)
        return raw if isinstance(raw, list) else []

    def fetch_models_by_group_id(
        self, scenario_group_id: int, *, include_deleted: bool = False
    ) -> list[MiScenarioModel]:
        stmt = (
            select(MiScenarioModel)
            .where(
                MiScenarioModel.scenario_group_id == scenario_group_id,
            )
            .order_by(MiScenarioModel.display_order, MiScenarioModel.scenario_id)
        )
        if not include_deleted:
            stmt = stmt.where(MiScenarioModel.del_yn == "N")
        return list(self.session.execute(stmt).scalars().all())

    def insert_scenario(self, payload: dict[str, Any]) -> int:
        scenario = MiScenarioModel(**payload)
        self.session.add(scenario)
        self.session.flush()
        return int(scenario.scenario_id)

    def update_status(self, scenario_group_id: int, status: str) -> int:
        scenarios = self.fetch_models_by_group_id(scenario_group_id)
        for scenario in scenarios:
            scenario.status = status
        self.session.flush()
        return len(scenarios)

    def update_status_by_ids(self, scenario_ids: list[int], status: str) -> int:
        if not scenario_ids:
            return 0
        scenarios = self.fetch_models_by_ids(scenario_ids)
        for scenario in scenarios:
            scenario.status = status
        self.session.flush()
        return len(scenarios)

    def fetch_models_by_ids(self, scenario_ids: list[int]) -> list[MiScenarioModel]:
        if not scenario_ids:
            return []
        stmt = (
            select(MiScenarioModel)
            .where(
                MiScenarioModel.scenario_id.in_(scenario_ids),
                MiScenarioModel.del_yn == "N",
            )
            .order_by(MiScenarioModel.display_order, MiScenarioModel.scenario_id)
        )
        return list(self.session.execute(stmt).scalars().all())

    def soft_delete_by_ids(self, scenario_ids: list[int], user_id: int) -> int:
        scenarios = self.fetch_models_by_ids(scenario_ids)
        for scenario in scenarios:
            scenario.del_yn = "Y"
            scenario.mod_usr_logn_id = user_id
        self.session.flush()
        return len(scenarios)

    def soft_delete_by_group_id(self, scenario_group_id: int, user_id: int) -> int:
        scenarios = self.fetch_models_by_group_id(scenario_group_id)
        for scenario in scenarios:
            scenario.del_yn = "Y"
            scenario.mod_usr_logn_id = user_id
        self.session.flush()
        return len(scenarios)

    def update_from_payload(self, scenario: MiScenarioModel, payload: dict[str, Any]) -> None:
        for field in (
            "title",
            "narrative",
            "dimension_values",
            "probability_score",
            "probability_delta",
            "display_order",
            "baseline_yn",
            "global_pressure_band",
            "scenario_role",
            "global_pressure_rationale",
            "related_markets",
            "status",
            "mod_usr_logn_id",
        ):
            if field in payload:
                setattr(scenario, field, payload[field])
        self.session.flush()

    def model_to_dict(self, scenario: MiScenarioModel, *, include_del_yn: bool = False) -> dict[str, Any]:
        raw_dimension_values = scenario.dimension_values
        if isinstance(raw_dimension_values, dict):
            dim_dict = {str(dim_key): value for dim_key, value in raw_dimension_values.items() if str(dim_key).strip()}
        elif isinstance(raw_dimension_values, list):
            dim_dict = {
                str(item.get("dim_key")): item.get("value")
                for item in raw_dimension_values
                if isinstance(item, dict) and item.get("dim_key")
            }
        else:
            dim_dict = {}
        payload = {
            "scenario_id": int(scenario.scenario_id),
            "scenario_group_id": int(scenario.scenario_group_id),
            "title": scenario.title,
            "description": scenario.narrative or "",
            "narrative": scenario.narrative,
            "status": scenario.status,
            "dimension_values": dim_dict,
            "probability_score": scenario.probability_score,
            "probability_delta": scenario.probability_delta,
            "display_order": scenario.display_order,
            "baseline_yn": scenario.baseline_yn,
            "global_pressure_band": scenario.global_pressure_band,
            "scenario_role": scenario.scenario_role,
            "global_pressure_rationale": scenario.global_pressure_rationale,
            "related_markets": scenario.related_markets or [],
        }
        if include_del_yn:
            payload["del_yn"] = scenario.del_yn
        return payload

    def fetch_mapping_by_value_id(
        self,
        scenario_group_id: int,
        dimension_value_id: str,
        *,
        include_deleted: bool = False,
    ) -> MiDimensionValueMappingModel | None:
        stmt = select(MiDimensionValueMappingModel).where(
            MiDimensionValueMappingModel.scenario_group_id == scenario_group_id,
            MiDimensionValueMappingModel.dimension_value_id == dimension_value_id,
        )
        if not include_deleted:
            stmt = stmt.where(MiDimensionValueMappingModel.del_yn == "N")
        stmt = stmt.order_by(
            MiDimensionValueMappingModel.mapping_version.desc(),
        ).limit(1)
        return self.session.execute(stmt).scalars().first()

    def fetch_mappings_by_group_id(
        self,
        scenario_group_id: int,
    ) -> list[MiDimensionValueMappingModel]:
        stmt = (
            select(MiDimensionValueMappingModel)
            .where(
                MiDimensionValueMappingModel.scenario_group_id == scenario_group_id,
                MiDimensionValueMappingModel.del_yn == "N",
            )
            .order_by(
                MiDimensionValueMappingModel.dimension_id,
                MiDimensionValueMappingModel.dimension_value_id,
            )
        )
        return list(self.session.execute(stmt).scalars().all())

    def deactivate_mappings_except(
        self,
        scenario_group_id: int,
        active_dimension_value_ids: set[str],
        user_id: int,
    ) -> None:
        for mapping in self.fetch_mappings_by_group_id(scenario_group_id):
            if mapping.dimension_value_id in active_dimension_value_ids:
                continue
            mapping.del_yn = "Y"
            mapping.mod_usr_logn_id = user_id
        self.session.flush()

    def upsert_mapping_proposal(
        self,
        *,
        scenario_group_id: int,
        dimension_value_id: str,
        dimension_id: str,
        display_value: str,
        source_projections: list[dict[str, Any]],
        mapping_proposal: dict[str, Any],
        user_id: int,
    ) -> MiDimensionValueMappingModel:
        existing = self.fetch_mapping_by_value_id(
            scenario_group_id,
            dimension_value_id,
            include_deleted=True,
        )
        if existing is None:
            existing = MiDimensionValueMappingModel(
                scenario_group_id=scenario_group_id,
                dimension_value_id=dimension_value_id,
                dimension_id=dimension_id,
                display_value=display_value,
                source_projections=source_projections,
                mapping_proposal=mapping_proposal,
                mapping_version=1,
                status="pending",
                crt_usr_logn_id=user_id,
                mod_usr_logn_id=user_id,
            )
            self.session.add(existing)
        else:
            was_deleted = existing.del_yn == "Y"
            changed = (
                existing.display_value != display_value
                or existing.source_projections != source_projections
                or existing.mapping_proposal != mapping_proposal
            )
            if was_deleted or changed:
                existing.mapping_version += 1
                existing.mod_usr_logn_id = user_id
            if was_deleted:
                existing.del_yn = "N"
            if changed:
                existing.display_value = display_value
                existing.source_projections = source_projections
                existing.mapping_proposal = mapping_proposal
                existing.status = "pending"
        self.session.flush()
        return existing
