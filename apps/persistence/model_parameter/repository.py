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
        mapping_rules = self._fetch_dimension_mapping_rules()
        candidate_parameter_names = {
            str(rule.get("canonical_parameter_name") or "")
            for rule in mapping_rules
            if rule.get("mapping_method") in {"direct", "routing"} and str(rule.get("canonical_parameter_name") or "")
        }
        parameter_definitions = [
            definition
            for definition in self._fetch_model_parameter_definitions()
            if str(definition.get("canonical_parameter_name") or "") in candidate_parameter_names
        ]
        return mapping_rules, parameter_definitions

    def fetch_model_parameter_definitions(self) -> list[dict[str, Any]]:
        return self._fetch_model_parameter_definitions()

    def create_model_param_proposal(
        self,
        *,
        scenario_id: int,
        scenario_group_id: int,
        mi_event_id: int | None,
        mi_base_case_id: int | None = None,
        request_usr_id: int | None,
        proposal_parameters: list[dict[str, Any]],
    ) -> int:
        proposal = MiModelParamProposalModel(
            scenario_id=scenario_id,
            scenario_group_id=scenario_group_id,
            mi_event_id=mi_event_id,
            mi_base_case_id=mi_base_case_id,
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
        mi_event_id: int | None,
        mi_base_case_id: int | None = None,
        request_usr_id: int | None,
    ) -> int:
        proposal = MiModelParamProposalModel(
            scenario_id=scenario_id,
            scenario_group_id=scenario_group_id,
            mi_event_id=mi_event_id,
            mi_base_case_id=mi_base_case_id,
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

    def create_abstained_model_param_proposal(
        self,
        *,
        scenario_id: int,
        scenario_group_id: int,
        mi_event_id: int | None,
        mi_base_case_id: int | None = None,
        request_usr_id: int | None,
        reason_code: str,
        reason_message: str,
    ) -> int:
        proposal = MiModelParamProposalModel(
            scenario_id=scenario_id,
            scenario_group_id=scenario_group_id,
            mi_event_id=mi_event_id,
            mi_base_case_id=mi_base_case_id,
            request_usr_id=request_usr_id,
            crt_usr_logn_id=request_usr_id if request_usr_id is not None else "system",
            mod_usr_logn_id=request_usr_id if request_usr_id is not None else "system",
            status="ABSTAINED",
            proposal_parameters=[],
            proposal_completed_dtm=datetime.now(),
            error_code=reason_code,
            error_message=reason_message,
            callback_status="SKIPPED",
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

        가격전망 해석 입력용. PROPOSED/CONFIRMED 를 모두 포함하고, proposal_parameters가
        비어 있지 않은 행만 대상으로 한다. 시나리오별로 가장 큰
        model_param_proposal_id(최신) 1건만 반환한다.

        CONFIRMED 행은 사용자가 확정 단계에서 수정한 최종값이 confirmation_parameters에
        저장되므로, 값이 있으면 confirmation_parameters를 우선 사용하고 없을 때만
        proposal_parameters로 fallback한다(가격 결과와 feature diff 기준을 일치시킨다).
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
            stmt = stmt.where(MiModelParamProposalModel.scenario_id.in_(scenario_ids))
        rows = self.session.execute(stmt).scalars().all()
        latest: dict[int, MiModelParamProposalModel] = {}
        for proposal in rows:
            # id 오름차순 정렬이므로 마지막(최신)이 남는다.
            latest[int(proposal.scenario_id)] = proposal
        return [
            {
                "scenario_id": int(proposal.scenario_id),
                "scenario_group_id": int(proposal.scenario_group_id),
                "mi_event_id": (int(proposal.mi_event_id) if proposal.mi_event_id is not None else None),
                "mi_base_case_id": (
                    int(proposal.mi_base_case_id)
                    if getattr(proposal, "mi_base_case_id", None) is not None
                    else None
                ),
                "status": proposal.status,
                "proposal_parameters": _json_safe(
                    proposal.confirmation_parameters
                    if proposal.status == "CONFIRMED" and proposal.confirmation_parameters
                    else proposal.proposal_parameters
                ),
            }
            for proposal in latest.values()
        ]

    def fetch_proposal_guard_rows(
        self,
        *,
        scenario_group_id: int,
        scenario_ids: list[int],
    ) -> list[dict[str, Any]]:
        """Return every non-deleted proposal row needed by execution guards.

        The guard must see all lifecycle states, including failed and in-flight
        attempts, before deciding whether a scenario is safe to execute.  Keep
        this query scoped to one exact group and an explicit, non-empty scenario
        set so callers cannot accidentally inspect or act on a broader cohort.
        """
        if not scenario_ids:
            return []

        stmt = (
            select(MiModelParamProposalModel)
            .where(
                MiModelParamProposalModel.scenario_group_id == scenario_group_id,
                MiModelParamProposalModel.scenario_id.in_(scenario_ids),
                MiModelParamProposalModel.del_yn == "N",
            )
            .order_by(
                MiModelParamProposalModel.scenario_id,
                MiModelParamProposalModel.model_param_proposal_id,
            )
        )
        rows = self.session.execute(stmt).scalars().all()
        return [
            {
                "model_param_proposal_id": int(proposal.model_param_proposal_id),
                "scenario_id": int(proposal.scenario_id),
                "scenario_group_id": int(proposal.scenario_group_id),
                "status": proposal.status,
                "callback_status": proposal.callback_status,
                "callback_sent_dtm": proposal.callback_sent_dtm,
                "crt_dtm": proposal.crt_dtm,
                "mod_dtm": proposal.mod_dtm,
                "proposal_completed_dtm": proposal.proposal_completed_dtm,
                "confirmed_dtm": proposal.confirmed_dtm,
                "error_code": proposal.error_code,
                "error_message": proposal.error_message,
                "proposal_parameters": _json_safe(proposal.proposal_parameters or []),
                "confirmation_parameters": _json_safe(proposal.confirmation_parameters),
            }
            for proposal in rows
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
        return self._proposal_to_dict(proposal)

    def fetch_model_param_proposal_for_update(
        self,
        model_param_proposal_id: int,
    ) -> dict[str, Any] | None:
        stmt = (
            select(MiModelParamProposalModel)
            .where(
                MiModelParamProposalModel.model_param_proposal_id == model_param_proposal_id,
                MiModelParamProposalModel.del_yn == "N",
            )
            .with_for_update()
        )
        proposal = self.session.execute(stmt).scalars().one_or_none()
        return self._proposal_to_dict(proposal)

    @staticmethod
    def _proposal_to_dict(
        proposal: MiModelParamProposalModel | None,
    ) -> dict[str, Any] | None:
        if proposal is None:
            return None
        return {
            "model_param_proposal_id": int(proposal.model_param_proposal_id),
            "scenario_id": int(proposal.scenario_id),
            "scenario_group_id": int(proposal.scenario_group_id),
            "mi_event_id": (int(proposal.mi_event_id) if proposal.mi_event_id is not None else None),
            "mi_base_case_id": (
                int(proposal.mi_base_case_id)
                if getattr(proposal, "mi_base_case_id", None) is not None
                else None
            ),
            "status": proposal.status,
            "callback_status": proposal.callback_status,
            "proposal_parameters": _json_safe(proposal.proposal_parameters),
            "confirmation_parameters": _json_safe(proposal.confirmation_parameters),
            "error_code": getattr(proposal, "error_code", None),
            "error_message": getattr(proposal, "error_message", None),
        }

    def confirm_model_param_proposal(
        self,
        *,
        model_param_proposal_id: int,
        user_id: int | None,
        confirmation_parameters: list[dict[str, Any]],
    ) -> bool:
        stmt = select(MiModelParamProposalModel).where(
            MiModelParamProposalModel.model_param_proposal_id == model_param_proposal_id,
            MiModelParamProposalModel.del_yn == "N",
        )
        proposal = self.session.execute(stmt).scalars().one_or_none()
        if proposal is None:
            return False
        proposal.confirmation_parameters = confirmation_parameters
        proposal.status = "CONFIRMED"
        proposal.confirmed_dtm = datetime.now()
        if user_id is not None:
            proposal.mod_usr_logn_id = user_id
        return True

    def complete_model_param_proposal(
        self,
        *,
        model_param_proposal_id: int,
        proposal_parameters: list[dict[str, Any]],
    ) -> bool:
        stmt = select(MiModelParamProposalModel).where(
            MiModelParamProposalModel.model_param_proposal_id == model_param_proposal_id,
            MiModelParamProposalModel.del_yn == "N",
        )
        proposal = self.session.execute(stmt).scalars().one_or_none()
        if proposal is None:
            return False
        proposal.proposal_parameters = proposal_parameters
        proposal.status = "PROPOSED"
        proposal.proposal_completed_dtm = datetime.now()
        proposal.error_code = None
        proposal.error_message = None
        return True

    def fail_model_param_proposal(
        self,
        *,
        model_param_proposal_id: int,
        error_code: str,
        error_message: str,
    ) -> bool:
        stmt = select(MiModelParamProposalModel).where(
            MiModelParamProposalModel.model_param_proposal_id == model_param_proposal_id,
            MiModelParamProposalModel.del_yn == "N",
        )
        proposal = self.session.execute(stmt).scalars().one_or_none()
        if proposal is None:
            return False
        proposal.proposal_parameters = []
        proposal.status = "FAILED"
        proposal.proposal_completed_dtm = datetime.now()
        proposal.error_code = error_code
        proposal.error_message = error_message
        return True

    def abstain_model_param_proposal(
        self,
        *,
        model_param_proposal_id: int,
        reason_code: str,
        reason_message: str,
    ) -> bool:
        stmt = select(MiModelParamProposalModel).where(
            MiModelParamProposalModel.model_param_proposal_id == model_param_proposal_id,
            MiModelParamProposalModel.del_yn == "N",
        )
        proposal = self.session.execute(stmt).scalars().one_or_none()
        if proposal is None:
            return False
        proposal.proposal_parameters = []
        proposal.status = "ABSTAINED"
        proposal.proposal_completed_dtm = datetime.now()
        proposal.error_code = reason_code
        proposal.error_message = reason_message
        return True

    def update_model_param_callback_status(
        self,
        *,
        model_param_proposal_id: int,
        callback_status: str,
    ) -> bool:
        stmt = select(MiModelParamProposalModel).where(
            MiModelParamProposalModel.model_param_proposal_id == model_param_proposal_id,
            MiModelParamProposalModel.del_yn == "N",
        )
        proposal = self.session.execute(stmt).scalars().one_or_none()
        if proposal is None:
            return False
        proposal.callback_status = callback_status
        if callback_status == "SUCCEEDED":
            proposal.callback_sent_dtm = datetime.now()
        return True

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
                    MiModelParamDimensionMapModel.model_param_id == MiModelParamModel.model_param_id,
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
            "model_param_id": parameter.model_param_id,
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
            "canonical_parameter_name": (parameter.parameter_name if parameter is not None else ""),
            "mapping_method": mapping.mapping_method,
            "comment": mapping.mapping_comment,
        }
