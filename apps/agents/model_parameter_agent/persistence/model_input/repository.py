from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import joinedload

from apps.agents.event_flow_agent.models.mi_event_models_orm import (
    MiEventTypeL2Model,
)
from apps.agents.scenario_group_agent.persistence.event.repository import (
    EventRepository,
)
from apps.agents.scenario_group_agent.persistence.scenario.models import (
    MiScenarioDimensionTemplateModel,
    MiScenarioModel,
)
from apps.agents.scenario_group_agent.persistence.scenario_group.models import (
    MiScenarioGroupModel,
)
from apps.common.configs.database.sync_database.base import BaseSyncSQLRepository
from apps.agents.model_parameter_agent.persistence.model_input.models import (
    MiModelParamDimensionMapModel,
    MiModelParamModel,
    MiModelParamProposalModel,
)


def _json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if hasattr(value, "value"):
        return value.value
    return value


class ModelInputRepository(BaseSyncSQLRepository):
    def fetch_context_by_scenario_id(self, scenario_id: int) -> dict[str, Any] | None:
        scenario = self._fetch_scenario(scenario_id)
        if scenario is None:
            return None

        group = self._fetch_group(int(scenario.scenario_group_id))
        if group is None:
            return None

        event = EventRepository(session=self.session).fetch_event_by_id(
            int(group.mi_event_id),
        )
        event_type = self._fetch_event_type(int(group.event_type_l2_id))
        template_json = self._fetch_dimension_template(int(group.event_type_l2_id))

        return {
            "scenario": self._scenario_to_dict(scenario),
            "scenario_group": self._group_to_dict(group),
            "event": event or {},
            "event_type": event_type or {},
            "dimension_template": template_json or [],
        }

    def fetch_parameter_mapping_resources(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        parameter_definitions = self._fetch_model_parameter_definitions()
        mapping_rules = self._fetch_dimension_mapping_rules()
        return mapping_rules, parameter_definitions

    def create_model_param_proposal(
        self,
        *,
        scenario_id: int,
        scenario_group_id: int,
        mi_event_id: int,
        request_usr_id: int | None,
        proposal_parameters: list[dict[str, Any]],
    ) -> int:
        proposal = MiModelParamProposalModel(
            scenario_id=scenario_id,
            scenario_group_id=scenario_group_id,
            mi_event_id=mi_event_id,
            request_usr_id=request_usr_id,
            status="PROPOSED",
            proposal_parameters=proposal_parameters,
            proposal_completed_dtm=datetime.now(),
            callback_status="SKIPPED",
        )
        self.session.add(proposal)
        self.session.flush()
        return int(proposal.model_param_proposal_id)

    def _fetch_scenario(self, scenario_id: int) -> MiScenarioModel | None:
        stmt = select(MiScenarioModel).where(
            MiScenarioModel.scenario_id == scenario_id,
            MiScenarioModel.del_yn == "N",
        )
        return self.session.execute(stmt).scalars().one_or_none()

    def _fetch_group(self, scenario_group_id: int) -> MiScenarioGroupModel | None:
        stmt = select(MiScenarioGroupModel).where(
            MiScenarioGroupModel.scenario_group_id == scenario_group_id,
            MiScenarioGroupModel.del_yn == "N",
        )
        return self.session.execute(stmt).scalars().one_or_none()

    def _fetch_event_type(self, event_type_l2_id: int) -> dict[str, Any] | None:
        stmt = (
            select(MiEventTypeL2Model)
            .options(joinedload(MiEventTypeL2Model.level_1))
            .where(
                MiEventTypeL2Model.event_type_l2_id == event_type_l2_id,
                MiEventTypeL2Model.del_yn == "N",
            )
        )
        l2 = self.session.execute(stmt).scalars().one_or_none()
        if l2 is None:
            return None
        l1 = l2.level_1
        return {
            "event_type_l1_id": int(l2.event_type_l1_id),
            "event_type_l2_id": int(l2.event_type_l2_id),
            "level_1_code": l1.level_1_code if l1 else "",
            "level_1_label": l1.level_1_label if l1 else "",
            "level_2_code": l2.level_2_code,
            "level_2_label": l2.level_2_label,
        }

    def _fetch_dimension_template(self, event_type_l2_id: int) -> list[dict[str, Any]]:
        stmt = select(MiScenarioDimensionTemplateModel.template_json).where(
            MiScenarioDimensionTemplateModel.event_type_l2_id == event_type_l2_id,
            MiScenarioDimensionTemplateModel.del_yn == "N",
        )
        raw = self.session.execute(stmt).scalars().first()
        return raw if isinstance(raw, list) else []

    def _fetch_model_parameter_definitions(self) -> list[dict[str, Any]]:
        stmt = (
            select(MiModelParamModel)
            .where(
                MiModelParamModel.del_yn == "N",
                MiModelParamModel.use_yn == "Y",
            )
            .order_by(MiModelParamModel.model_param_id)
        )
        rows = self.session.execute(stmt).scalars().all()
        return [self._parameter_definition_to_dict(row) for row in rows]

    def _fetch_dimension_mapping_rules(self) -> list[dict[str, Any]]:
        stmt = (
            select(MiModelParamDimensionMapModel, MiModelParamModel)
            .outerjoin(
                MiModelParamModel,
                and_(
                    MiModelParamDimensionMapModel.model_param_id
                    == MiModelParamModel.model_param_id,
                    MiModelParamModel.del_yn == "N",
                    MiModelParamModel.use_yn == "Y",
                ),
            )
            .where(
                MiModelParamDimensionMapModel.del_yn == "N",
                MiModelParamDimensionMapModel.use_yn == "Y",
                or_(
                    MiModelParamDimensionMapModel.model_param_id.is_(None),
                    MiModelParamModel.model_param_id.is_not(None),
                ),
            )
            .order_by(MiModelParamDimensionMapModel.model_param_dimension_map_id)
        )
        return [
            self._dimension_mapping_rule_to_dict(mapping, parameter)
            for mapping, parameter in self.session.execute(stmt).all()
        ]

    def _scenario_to_dict(self, scenario: MiScenarioModel) -> dict[str, Any]:
        return {
            "scenario_id": int(scenario.scenario_id),
            "scenario_group_id": int(scenario.scenario_group_id),
            "title": scenario.title,
            "narrative": scenario.narrative or "",
            "status": _json_safe(scenario.status),
            "dimension_values": _json_safe(scenario.dimension_values or {}),
            "probability_score": _json_safe(scenario.probability_score),
            "probability_delta": _json_safe(scenario.probability_delta),
            "impact": {
                "jkm": scenario.impact_jkm,
                "ttf": scenario.impact_ttf,
                "hh": scenario.impact_hh,
            },
            "baseline_yn": scenario.baseline_yn,
        }

    def _group_to_dict(self, group: MiScenarioGroupModel) -> dict[str, Any]:
        return {
            "scenario_group_id": int(group.scenario_group_id),
            "mi_event_id": int(group.mi_event_id),
            "event_type_l2_id": int(group.event_type_l2_id),
            "request_usr_id": (
                int(group.request_usr_id) if group.request_usr_id is not None else None
            ),
            "title": group.title,
            "summary": group.summary,
            "description": group.description,
            "dimension_selected": group.dimension_selected or [],
            "scenario_count": int(group.scenario_count or 0),
            "status": _json_safe(group.status),
            "stage": _json_safe(group.stage),
        }

    def _parameter_definition_to_dict(self, parameter: MiModelParamModel) -> dict[str, Any]:
        return {
            "canonical_parameter_name": parameter.parameter_name,
            "parameter_hint": parameter.parameter_hint,
            "model_file": parameter.model_file,
            "model_sheet": parameter.model_sheet,
            "model_table": parameter.model_table,
            "parameter_name": parameter.parameter_name,
            "semantic_axes": parameter.semantic_axes,
            "basecase_read_mode": parameter.basecase_read_mode,
            "basecase_header_row": parameter.basecase_header_row,
            "basecase_data_start_row": parameter.basecase_data_start_row,
            "basecase_column_roles": parameter.basecase_column_roles,
            "basecase_row_filter": parameter.basecase_row_filter,
            "basecase_year_row": parameter.basecase_year_row,
            "basecase_month_row": parameter.basecase_month_row,
            "basecase_period_row": parameter.basecase_period_row,
            "basecase_value_start_col": parameter.basecase_value_start_col,
            "basecase_value_end_col": parameter.basecase_value_end_col,
            "basecase_stop_rule": parameter.basecase_stop_rule,
        }

    def _dimension_mapping_rule_to_dict(
        self,
        mapping: MiModelParamDimensionMapModel,
        parameter: MiModelParamModel | None,
    ) -> dict[str, Any]:
        return {
            "event_type_l2_id": int(mapping.event_type_l2_id),
            "dimension_key": mapping.dimension_key,
            "dimension_label": mapping.dimension_label,
            "canonical_parameter_name": (
                parameter.parameter_name if parameter is not None else ""
            ),
            "mapping_method": mapping.mapping_method,
            "comment": mapping.mapping_comment,
        }
