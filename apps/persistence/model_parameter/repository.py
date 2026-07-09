from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, or_, select

from apps.common.configs.database.sync_database.base import BaseSyncSQLRepository
from apps.persistence.model_parameter.models import (
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


class ModelParameterRepository(BaseSyncSQLRepository):
    def fetch_parameter_mapping_resources(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        parameter_definitions = self._fetch_model_parameter_definitions()
        mapping_rules = self._fetch_dimension_mapping_rules()
        return mapping_rules, parameter_definitions

    def fetch_model_parameter_definitions(self) -> list[dict[str, Any]]:
        return self._fetch_model_parameter_definitions()

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
            crt_usr_logn_id=request_usr_id if request_usr_id is not None else "system",
            mod_usr_logn_id=request_usr_id if request_usr_id is not None else "system",
            status="PROPOSED",
            proposal_parameters=proposal_parameters,
            proposal_completed_dtm=datetime.now(),
            callback_status="SKIPPED",
        )
        self.session.add(proposal)
        self.session.flush()
        return int(proposal.model_param_proposal_id)

    def create_processing_model_param_proposal(
        self,
        *,
        scenario_id: int,
        scenario_group_id: int,
        mi_event_id: int,
        request_usr_id: int | None,
    ) -> int:
        proposal = MiModelParamProposalModel(
            scenario_id=scenario_id,
            scenario_group_id=scenario_group_id,
            mi_event_id=mi_event_id,
            request_usr_id=request_usr_id,
            crt_usr_logn_id=request_usr_id if request_usr_id is not None else "system",
            mod_usr_logn_id=request_usr_id if request_usr_id is not None else "system",
            status="PROCESSING",
            proposal_parameters=[],
            callback_status="PENDING",
        )
        self.session.add(proposal)
        self.session.flush()
        return int(proposal.model_param_proposal_id)

    def fetch_proposals_by_group(
        self,
        scenario_group_id: int,
        scenario_ids: list[int] | None = None,
    ) -> list[dict[str, Any]]:
        """그룹 내 시나리오별 최신 제안 파라미터(read-only).

        가격전망 해석 입력용. 제안이 확정(CONFIRMED)된 행도 proposal_parameters를
        그대로 보유하므로 PROPOSED/CONFIRMED 를 모두 포함하고, proposal_parameters가
        비어 있지 않은 행만 대상으로 한다. 시나리오별로 가장 큰
        model_param_proposal_id(최신) 1건만 반환한다.
        """
        stmt = (
            select(MiModelParamProposalModel)
            .where(
                MiModelParamProposalModel.scenario_group_id == scenario_group_id,
                MiModelParamProposalModel.del_yn == "N",
                MiModelParamProposalModel.status.in_(["PROPOSED", "CONFIRMED"]),
                MiModelParamProposalModel.proposal_parameters.isnot(None),
            )
            .order_by(
                MiModelParamProposalModel.scenario_id,
                MiModelParamProposalModel.model_param_proposal_id,
            )
        )
        if scenario_ids:
            stmt = stmt.where(
                MiModelParamProposalModel.scenario_id.in_(scenario_ids)
            )
        rows = self.session.execute(stmt).scalars().all()
        latest: dict[int, MiModelParamProposalModel] = {}
        for proposal in rows:
            # id 오름차순 정렬이므로 마지막(최신)이 남는다.
            latest[int(proposal.scenario_id)] = proposal
        return [
            {
                "scenario_id": int(proposal.scenario_id),
                "scenario_group_id": int(proposal.scenario_group_id),
                "mi_event_id": int(proposal.mi_event_id),
                "status": proposal.status,
                "proposal_parameters": _json_safe(proposal.proposal_parameters),
            }
            for proposal in latest.values()
        ]

    def fetch_model_param_proposal(
        self,
        model_param_proposal_id: int,
    ) -> dict[str, Any] | None:
        stmt = select(MiModelParamProposalModel).where(
            MiModelParamProposalModel.model_param_proposal_id == model_param_proposal_id,
            MiModelParamProposalModel.del_yn == "N",
        )
        proposal = self.session.execute(stmt).scalars().one_or_none()
        if proposal is None:
            return None
        return {
            "model_param_proposal_id": int(proposal.model_param_proposal_id),
            "scenario_id": int(proposal.scenario_id),
            "scenario_group_id": int(proposal.scenario_group_id),
            "mi_event_id": int(proposal.mi_event_id),
            "status": proposal.status,
            "proposal_parameters": _json_safe(proposal.proposal_parameters),
            "confirmation_parameters": _json_safe(proposal.confirmation_parameters),
        }

    def confirm_model_param_proposal(
        self,
        *,
        model_param_proposal_id: int,
        user_id: int | None,
        confirmation_parameters: list[dict[str, Any]],
    ) -> None:
        stmt = select(MiModelParamProposalModel).where(
            MiModelParamProposalModel.model_param_proposal_id == model_param_proposal_id,
            MiModelParamProposalModel.del_yn == "N",
        )
        proposal = self.session.execute(stmt).scalars().one_or_none()
        if proposal is None:
            return
        proposal.confirmation_parameters = confirmation_parameters
        proposal.status = "CONFIRMED"
        proposal.confirmed_dtm = datetime.now()
        if user_id is not None:
            proposal.mod_usr_logn_id = user_id

    def complete_model_param_proposal(
        self,
        *,
        model_param_proposal_id: int,
        proposal_parameters: list[dict[str, Any]],
    ) -> None:
        stmt = select(MiModelParamProposalModel).where(
            MiModelParamProposalModel.model_param_proposal_id == model_param_proposal_id,
            MiModelParamProposalModel.del_yn == "N",
        )
        proposal = self.session.execute(stmt).scalars().one_or_none()
        if proposal is None:
            return
        proposal.proposal_parameters = proposal_parameters
        proposal.status = "PROPOSED"
        proposal.proposal_completed_dtm = datetime.now()
        proposal.error_code = None
        proposal.error_message = None

    def fail_model_param_proposal(
        self,
        *,
        model_param_proposal_id: int,
        error_code: str,
        error_message: str,
    ) -> None:
        stmt = select(MiModelParamProposalModel).where(
            MiModelParamProposalModel.model_param_proposal_id == model_param_proposal_id,
            MiModelParamProposalModel.del_yn == "N",
        )
        proposal = self.session.execute(stmt).scalars().one_or_none()
        if proposal is None:
            return
        proposal.proposal_parameters = []
        proposal.status = "FAILED"
        proposal.proposal_completed_dtm = datetime.now()
        proposal.error_code = error_code
        proposal.error_message = error_message

    def update_model_param_callback_status(
        self,
        *,
        model_param_proposal_id: int,
        callback_status: str,
    ) -> None:
        stmt = select(MiModelParamProposalModel).where(
            MiModelParamProposalModel.model_param_proposal_id == model_param_proposal_id,
            MiModelParamProposalModel.del_yn == "N",
        )
        proposal = self.session.execute(stmt).scalars().one_or_none()
        if proposal is None:
            return
        proposal.callback_status = callback_status
        if callback_status == "SUCCEEDED":
            proposal.callback_sent_dtm = datetime.now()

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
