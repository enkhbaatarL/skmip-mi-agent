from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from decimal import Decimal
import hashlib
import json
from typing import TYPE_CHECKING, Any, TypedDict

from apps.agents.scenario_group_agent.utils.pressure_band import relative_pressure_band
from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode
from apps.persistence.enums import ScenarioStatus
from apps.persistence.scenario.baseline_contrast import (
    apply_single_baseline_by_probability,
)
from apps.persistence.scenario.repository import (
    ScenarioRepository,
)
from apps.persistence.scenario.schema import (
    NewScenarioGeneratedDetails,
    ScenarioPayload,
    ScenarioPipelineTemplate,
    ScenarioPipelineTemplateDimension,
)
from apps.persistence.scenario_group.repository import (
    ScenarioGroupRepository,
)
from apps.persistence.signpost.repository import (
    SignpostRepository,
)


if TYPE_CHECKING:
    from apps.persistence.scenario.schema import (
        ScenarioTemplate as CommonScenarioTemplate,
        ScenarioTemplateDimension as CommonScenarioTemplateDimension,
    )

ScenarioDimensionValues = dict[str, Any]
ScenarioDimensionTemplateByKey = dict[str, dict[str, Any]]


class ScenarioSyncRowPayload(TypedDict, total=False):
    scenario_id: int | None
    display_order: int
    title: str
    cells: ScenarioDimensionValues


class ScenarioSyncHeaderPayload(TypedDict, total=False):
    key: str


class ScenarioSyncTablePayload(TypedDict):
    headers: list[ScenarioSyncHeaderPayload]
    rows: list[ScenarioSyncRowPayload]


class ScenarioSyncResult(TypedDict):
    active_scenario_ids: list[int]
    regenerate_scenario_ids: list[int]
    inserted_scenario_ids: list[int]
    updated_scenario_ids: list[int]
    deleted_scenario_ids: list[int]
    unchanged_existing_scenario_ids: list[int]


class ValidationChangeSetAcceptanceResult(TypedDict):
    operation_id: str | None
    validation_operation_id: str
    signpost_target_scenario_ids: list[int]
    scenario_group: dict[str, Any]


class ExistingScenarioUpdatePayload(TypedDict):
    title: str
    dimension_values: ScenarioDimensionValues
    display_order: int
    mod_usr_logn_id: int


class NewScenarioInsertPayload(ExistingScenarioUpdatePayload):
    scenario_group_id: int
    narrative: str
    status: str
    probability_score: Decimal
    probability_delta: Decimal
    impact_jkm: str | None
    impact_ttf: str | None
    impact_hh: str | None
    baseline_yn: str
    crt_usr_logn_id: int


def _normalize_decimal_scores_to_100(scores: list[Decimal]) -> list[Decimal]:
    """Score 목록을 합계 100인 probability_score 목록으로 변환한다."""
    if not scores:
        return []

    weights = scores
    total = sum(weights)
    if total <= 0:
        even = Decimal(100) / Decimal(len(weights))
        return [even] * len(weights)

    exact = [float(w) / float(total) * 100 for w in weights]
    floors = [int(v) for v in exact]
    remainders = [v - int(v) for v in exact]
    deficit = 100 - sum(floors)
    for i in sorted(range(len(remainders)), key=lambda k: -remainders[k])[:deficit]:
        floors[i] += 1

    return [Decimal(str(s)) for s in floors]


class ScenarioService:
    def load_dimension_template(self, event_type_l2_id: int) -> list["CommonScenarioTemplateDimension"]:
        from apps.persistence.scenario.schema import (
            ScenarioTemplateDimension as CommonScenarioTemplateDimension,
        )

        pipeline_template = self.load_pipeline_template(event_type_l2_id)
        return [
            CommonScenarioTemplateDimension(
                dimension_id=dimension.dim_key,
                label_ko=dimension.label,
                description=dimension.description,
                required=dimension.required,
                enum=[
                    {
                        "id": str(item["id"]),
                        "label": str(item["label"]),
                        "tail": bool(item.get("tail", False)),
                    }
                    for item in dimension.enum_items()
                ],
            )
            for dimension in pipeline_template.dimensions
        ]

    def load_pipeline_template(self, event_type_l2_id: int) -> ScenarioPipelineTemplate:
        return self.load_pipeline_template_with_metadata(event_type_l2_id)

    def load_legacy_pipeline_template(
        self,
        event_type_l2_id: int,
    ) -> ScenarioPipelineTemplate:
        return self._map_template_json_to_pipeline_template(
            self._load_template_json_from_db(event_type_l2_id),
            event_type_l2_id,
        )

    def load_pipeline_template_with_metadata(
        self,
        event_type_l2_id: int,
    ) -> ScenarioPipelineTemplate:
        template_record = self._load_template_record_from_db(event_type_l2_id)
        template = self._map_template_json_to_pipeline_template(
            template_record["template_json"],
            event_type_l2_id,
        )
        return template.model_copy(
            update={key: value for key, value in template_record.items() if key != "template_json"},
        )

    def load_scenario_template(self, event_type_l2_id: int) -> "CommonScenarioTemplate":
        from apps.persistence.scenario.schema import (
            ScenarioTemplate as CommonScenarioTemplate,
            ScenarioTemplateDimension,
            ScenarioTemplateEnum,
        )

        pipeline_template = self.load_pipeline_template(event_type_l2_id)
        dimensions = [
            ScenarioTemplateDimension(
                dimension_id=dimension.dim_key,
                label_ko=dimension.label,
                description=dimension.description,
                required=dimension.required,
                enum=[
                    ScenarioTemplateEnum(
                        id=str(item["id"]),
                        label=str(item["label"]),
                        tail=bool(item.get("tail", False)),
                    )
                    for item in dimension.enum_items()
                ],
            )
            for dimension in pipeline_template.dimensions
        ]
        return CommonScenarioTemplate(
            template_dimensions_total=len(dimensions),
            dimensions=dimensions,
        )

    def _load_template_json_from_db(self, event_type_l2_id: int) -> list[dict[str, Any]]:
        from apps.common.configs.database.sync_database.connection import (
            get_sync_session,
        )

        session = get_sync_session()
        try:
            template_json = ScenarioRepository(
                session=session,
            )._load_template_json_from_db(event_type_l2_id)
        finally:
            session.close()

        if template_json is None:
            raise KeyError(f"scenario dimension template 없음: event_type_l2_id={event_type_l2_id}")

        if not isinstance(template_json, list):
            raise ValueError(
                "tmm_mi_scenario_dimension_template_m.template_json must be JSON ARRAY "
                f"(event_type_l2_id={event_type_l2_id})"
            )
        return template_json

    def _load_template_record_from_db(
        self,
        event_type_l2_id: int,
    ) -> dict[str, Any]:
        from apps.common.configs.database.sync_database.connection import (
            get_sync_session,
        )

        session = get_sync_session()
        try:
            model = ScenarioRepository(session=session).fetch_template_model(
                event_type_l2_id,
            )
        finally:
            session.close()

        if model is None:
            raise KeyError(f"scenario dimension template 없음: event_type_l2_id={event_type_l2_id}")
        if not isinstance(model.template_json, list):
            raise ValueError(
                "tmm_mi_scenario_dimension_template_m.template_json must be JSON ARRAY "
                f"(event_type_l2_id={event_type_l2_id})"
            )
        canonical = json.dumps(
            {
                "event_type_definition": model.event_type_definition or "",
                "lng_price_impact_examples": (model.lng_price_impact_examples or ""),
                "dimensions": model.template_json,
            },
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        return {
            "scenario_dimension_template_id": int(
                model.scenario_dimension_template_id,
            ),
            "event_type_l2_id": event_type_l2_id,
            "template_json": model.template_json,
            "event_type_definition": model.event_type_definition or "",
            "lng_price_impact_examples": model.lng_price_impact_examples or "",
            "template_checksum": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        }

    def load_template_record(self, event_type_l2_id: int) -> dict[str, Any]:
        """Load a Template and its canonical checksum for read-side compatibility checks."""
        return self._load_template_record_from_db(event_type_l2_id)

    def _map_template_json_to_pipeline_template(
        self,
        template_json: list[dict[str, Any]],
        event_type_l2_id: int,
    ) -> ScenarioPipelineTemplate:
        if not template_json:
            raise ValueError(f"template_json is empty: event_type_l2_id={event_type_l2_id}")

        dimensions = [
            self._map_template_dimension(item, event_type_l2_id, index)
            for index, item in enumerate(template_json, start=1)
        ]
        return ScenarioPipelineTemplate(
            label_ko=f"event_type_l2_id={event_type_l2_id}",
            template_dimensions_total=len(dimensions),
            dimensions=dimensions,
            compatibility_rules=[],
        )

    def validate_template_for_write(
        self,
        template_json: list[dict[str, Any]],
        *,
        event_type_l2_id: int,
    ) -> ScenarioPipelineTemplate:
        missing_descriptions = [
            str(item.get("dim_key") or index)
            for index, item in enumerate(template_json, start=1)
            if not isinstance(item, dict) or not str(item.get("description") or "").strip()
        ]
        if missing_descriptions:
            raise ValueError(
                "description is required for new or updated template dimensions: " + ", ".join(missing_descriptions),
            )
        return self._map_template_json_to_pipeline_template(
            template_json,
            event_type_l2_id,
        )

    def update_template_domain_knowledge(
        self,
        *,
        event_type_l2_id: int,
        event_type_definition: str,
        lng_price_impact_examples: str,
        template_json: list[dict[str, Any]],
        user_id: int,
    ) -> None:
        self.validate_template_for_write(
            template_json,
            event_type_l2_id=event_type_l2_id,
        )
        from apps.common.configs.database.sync_database.connection import (
            get_sync_session,
        )

        session = get_sync_session()
        try:
            repository = ScenarioRepository(session=session)
            template = repository.fetch_template_model(event_type_l2_id)
            if template is None:
                raise MIBaseError(
                    ErrorCode.ENTITY_NOT_FOUND,
                    detail=(f"Scenario dimension template not found: event_type_l2_id={event_type_l2_id}"),
                )
            repository.update_template_domain_knowledge(
                template,
                event_type_definition=event_type_definition,
                lng_price_impact_examples=lng_price_impact_examples,
                template_json=template_json,
                user_id=user_id,
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _map_template_dimension(
        self,
        raw_dimension: dict[str, Any],
        event_type_l2_id: int,
        index: int,
    ) -> ScenarioPipelineTemplateDimension:
        if not isinstance(raw_dimension, dict):
            raise ValueError(f"template_json item must be object: event_type_l2_id={event_type_l2_id}, index={index}")

        dim_key = str(raw_dimension.get("dim_key", "")).strip()
        if not dim_key:
            raise ValueError(f"dim_key is required: event_type_l2_id={event_type_l2_id}, index={index}")

        raw_value_enums = raw_dimension.get("value_enums") or []
        if not isinstance(raw_value_enums, list):
            raise ValueError(f"value_enums must be array: event_type_l2_id={event_type_l2_id}, dim_key={dim_key}")

        return ScenarioPipelineTemplateDimension(
            label=str(raw_dimension.get("label", "")).strip() or dim_key,
            description=(
                str(raw_dimension.get("description", "")).strip()
                or str(raw_dimension.get("label", "")).strip()
                or dim_key
            ),
            dim_key=dim_key,
            required=bool(raw_dimension.get("required", False)),
            value_enums=raw_value_enums,
            display_order=self._template_display_order(raw_dimension),
        )

    def _template_display_order(self, item: dict[str, Any]) -> int:
        if not isinstance(item, dict):
            return 999999
        try:
            return int(item.get("display_order", 999999))
        except (TypeError, ValueError):
            return 999999

    def load_by_group_id(self, scenario_group_id: int) -> list[ScenarioPayload]:
        from apps.common.configs.database.sync_database.connection import (
            get_sync_session,
        )

        session = get_sync_session()
        try:
            repository = ScenarioRepository(session=session)
            return [
                ScenarioPayload.from_model(model) for model in repository.fetch_models_by_group_id(scenario_group_id)
            ]
        finally:
            session.close()

    def load_group_dimension_template(
        self,
        dimension_definitions: list[dict[str, Any]],
    ) -> list["CommonScenarioTemplateDimension"]:
        from apps.persistence.scenario.schema import (
            ScenarioTemplateDimension as CommonScenarioTemplateDimension,
            ScenarioTemplateEnum,
        )

        dimensions: list[CommonScenarioTemplateDimension] = []
        for definition in dimension_definitions:
            values = definition.get("values") or []
            dimensions.append(
                CommonScenarioTemplateDimension(
                    dimension_id=str(definition["dimension_id"]),
                    label_ko=str(definition.get("label") or definition["dimension_id"]),
                    description=str(
                        definition.get("description") or definition.get("label") or definition["dimension_id"],
                    ),
                    required=bool(definition.get("required", False)),
                    enum=[
                        ScenarioTemplateEnum(
                            id=str(value.get("value_id") or value.get("label")),
                            label=str(value.get("label") or value.get("value_id")),
                        )
                        for value in values
                        if isinstance(value, dict) and (value.get("value_id") or value.get("label"))
                    ],
                ),
            )
        return dimensions

    def save_mapping_proposals(
        self,
        scenario_group_id: int,
        proposals: list[dict[str, Any]],
        user_id: int,
    ) -> list[dict[str, Any]]:
        from apps.common.configs.database.sync_database.connection import (
            get_sync_session,
        )

        session = get_sync_session()
        try:
            repository = ScenarioRepository(session=session)
            saved: list[dict[str, Any]] = []
            for proposal in proposals:
                model = repository.upsert_mapping_proposal(
                    scenario_group_id=scenario_group_id,
                    dimension_value_id=str(proposal["dimension_value_id"]),
                    dimension_id=str(proposal["dimension_id"]),
                    display_value=str(proposal["display_value"]),
                    source_projections=list(
                        proposal.get("source_projections") or [],
                    ),
                    mapping_proposal=dict(
                        proposal.get("mapping_proposal") or {},
                    ),
                    user_id=user_id,
                )
                saved.append(self._mapping_model_to_dict(model))
            repository.deactivate_mappings_except(
                scenario_group_id,
                {str(proposal["dimension_value_id"]) for proposal in proposals},
                user_id,
            )
            session.commit()
            return saved
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def decide_mapping_proposals(
        self,
        scenario_group_id: int,
        decisions: list[dict[str, Any]],
        user_id: int,
    ) -> list[dict[str, Any]]:
        from apps.common.configs.database.sync_database.connection import (
            get_sync_session,
        )

        session = get_sync_session()
        try:
            repository = ScenarioRepository(session=session)
            decided: list[dict[str, Any]] = []
            for decision in decisions:
                model = repository.fetch_mapping_by_value_id(
                    scenario_group_id,
                    str(decision["dimension_value_id"]),
                )
                if model is None:
                    raise MIBaseError(
                        ErrorCode.ENTITY_NOT_FOUND,
                        detail=(f"Mapping proposal not found: {decision['dimension_value_id']}"),
                    )
                if model.mapping_version != int(decision["mapping_version"]):
                    raise MIBaseError(
                        ErrorCode.INVALID_REQUEST,
                        detail=(
                            "Stale mapping version: "
                            f"{decision['dimension_value_id']} "
                            f"(expected={model.mapping_version}, "
                            f"actual={decision['mapping_version']})"
                        ),
                    )
                model.status = "approved" if decision["decision"] == "approve" else "rejected"
                model.mod_usr_logn_id = user_id
                decided.append(self._mapping_model_to_dict(model))
            session.flush()
            all_mappings = repository.fetch_mappings_by_group_id(
                scenario_group_id,
            )
            ready = all(mapping.status == "approved" for mapping in all_mappings)
            group = ScenarioGroupRepository(session=session).fetch_by_id(
                scenario_group_id,
            )
            if group is None:
                raise MIBaseError(
                    ErrorCode.ENTITY_NOT_FOUND,
                    detail=f"Scenario group not found: {scenario_group_id}",
                )
            ScenarioGroupRepository(session=session).update_group(
                group,
                {
                    "parameter_mapping_ready": ready,
                    "mod_usr_logn_id": user_id,
                },
            )
            session.commit()
            return decided
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @staticmethod
    def _mapping_model_to_dict(model: Any) -> dict[str, Any]:
        return {
            "dimension_value_id": model.dimension_value_id,
            "dimension_id": model.dimension_id,
            "display_value": model.display_value,
            "source_projections": model.source_projections or [],
            "mapping_proposal": model.mapping_proposal or {},
            "mapping_version": int(model.mapping_version),
            "status": model.status,
        }

    def update_status(self, scenario_group_id: int, status: ScenarioStatus | str) -> int:
        from apps.common.configs.database.sync_database.connection import (
            get_sync_session,
        )

        session = get_sync_session()
        try:
            count = ScenarioRepository(session=session).update_status(
                scenario_group_id,
                status.value if isinstance(status, ScenarioStatus) else status,
            )
            session.commit()
            return count
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def update_status_by_ids(
        self,
        scenario_ids: list[int],
        status: ScenarioStatus | str,
    ) -> int:
        from apps.common.configs.database.sync_database.connection import (
            get_sync_session,
        )

        session = get_sync_session()
        try:
            count = ScenarioRepository(session=session).update_status_by_ids(
                scenario_ids,
                status.value if isinstance(status, ScenarioStatus) else status,
            )
            session.commit()
            return count
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def sync_from_table(
        self,
        scenario_group_id: int,
        event_type_l2_id: int | None,
        table_payload: ScenarioSyncTablePayload,
        user_id: int,
        new_row_details: list[NewScenarioGeneratedDetails] | None = None,
        dimension_definitions: list[dict[str, Any]] | None = None,
    ) -> ScenarioSyncResult:
        return asyncio.run(
            self.sync_from_table_async(
                scenario_group_id=scenario_group_id,
                event_type_l2_id=event_type_l2_id,
                table_payload=table_payload,
                user_id=user_id,
                new_row_details=new_row_details,
                dimension_definitions=dimension_definitions,
            )
        )

    def accept_validation_change_set(
        self,
        *,
        scenario_group_id: int,
        user_id: int,
        create_signpost_operation: bool = True,
    ) -> ValidationChangeSetAcceptanceResult:
        from apps.agents.scenario_group_agent.flows.validate_scenarios.v4_validation import (
            dimension_definition_fingerprint,
            scenario_fingerprint,
        )
        from apps.agents.scenario_group_agent.persistence.scenario_group_operation_service import (
            ScenarioGroupOperationService,
            new_operation_id,
        )
        from apps.common.configs.database.sync_database.connection import get_sync_session
        from apps.persistence.scenario_group_operation.repository import ScenarioGroupOperationRepository
        from apps.persistence.scenario_group_operation.schema import (
            ValidationApplicationPayload,
            ValidationOperationResultPayload,
        )

        session = get_sync_session()
        stale_detail: str | None = None
        try:
            scenario_repository = ScenarioRepository(session=session)
            group_repository = ScenarioGroupRepository(session=session)
            signpost_repository = SignpostRepository(session=session)
            operation_repository = ScenarioGroupOperationRepository(session=session)
            group = group_repository.fetch_by_id(scenario_group_id, for_update=True)
            if group is None:
                raise MIBaseError(
                    ErrorCode.ENTITY_NOT_FOUND,
                    detail=f"Scenario group not found: {scenario_group_id}",
                )
            if group.request_usr_id is not None and int(group.request_usr_id) != user_id:
                raise MIBaseError(
                    ErrorCode.SCENARIO_GROUP_OWNERSHIP_CONFLICT,
                    detail=f"이미 사용자 {group.request_usr_id}가 점유하고 있습니다.",
                )
            current_stage = getattr(group.stage, "value", group.stage)
            if current_stage != "scenario_validated":
                raise MIBaseError(
                    ErrorCode.SCENARIO_GROUP_OPERATION_CONFLICT,
                    detail="Scenario Validation을 먼저 통과해야 합니다.",
                )
            active_operation = operation_repository.fetch_active(scenario_group_id)
            if active_operation is not None:
                raise MIBaseError(
                    ErrorCode.SCENARIO_GROUP_OPERATION_CONFLICT,
                    detail=f"실행 중인 operation이 있습니다: {active_operation.operation_id}",
                )
            validation_operation = operation_repository.fetch_latest_by_type(
                scenario_group_id,
                "validation",
                for_update=True,
            )
            if validation_operation is None or validation_operation.status != "succeeded":
                raise MIBaseError(
                    ErrorCode.SCENARIO_GROUP_OPERATION_CONFLICT,
                    detail="가장 최근 Validation이 정상 완료되지 않았습니다.",
                )
            validation_result = ValidationOperationResultPayload.model_validate(
                validation_operation.result_payload,
            )
            if not validation_result.validation_result.can_proceed:
                raise MIBaseError(
                    ErrorCode.SCENARIO_GROUP_OPERATION_CONFLICT,
                    detail="가장 최근 Validation 결과로는 다음 단계로 진행할 수 없습니다.",
                )

            scenarios = scenario_repository.fetch_models_by_group_id(
                scenario_group_id,
                for_update=True,
            )
            scenario_dicts = [scenario_repository.model_to_dict(scenario) for scenario in scenarios]
            current_scenario_fingerprint = scenario_fingerprint(scenario_dicts)
            current_definition_fingerprint = dimension_definition_fingerprint(
                list(group.dimension_definitions or []),
            )
            target_ids: list[int] = []
            application = validation_result.application
            if application is not None:
                if current_definition_fingerprint != validation_result.dimension_definition_fingerprint:
                    stale_detail = "Change Set 적용 후 Dimension definition이 다시 변경되었습니다."
                elif current_scenario_fingerprint != application.applied_scenario_fingerprint:
                    stale_detail = "Change Set 적용 후 Scenario가 다시 변경되었습니다."
            elif (
                current_scenario_fingerprint != validation_result.base_scenario_fingerprint
                or current_definition_fingerprint != validation_result.dimension_definition_fingerprint
            ):
                stale_detail = "Validation 기준 Scenario 또는 Dimension definition fingerprint가 현재 값과 다릅니다."
            elif validation_result.mode == "changed":
                change_set = validation_result.scenario_change_set
                if change_set is None:
                    raise MIBaseError(
                        ErrorCode.UNKNOWN_ERROR,
                        detail="Validation Change Set이 누락되었습니다.",
                    )
                scenarios_by_id = {int(scenario.scenario_id): scenario for scenario in scenarios}
                delete_ids = list(change_set.delete_scenario_ids)
                existing_upsert_ids = {
                    int(upsert.scenario_id) for upsert in change_set.upserts if upsert.scenario_id is not None
                }
                missing_upsert_ids = existing_upsert_ids - set(scenarios_by_id)
                missing_delete_ids = set(delete_ids) - set(scenarios_by_id)
                if missing_upsert_ids:
                    stale_detail = "변경 대상 Scenario가 현재 그룹과 일치하지 않습니다: " + ", ".join(
                        str(item) for item in sorted(missing_upsert_ids)
                    )
                elif missing_delete_ids:
                    stale_detail = "삭제 대상 Scenario가 현재 그룹과 일치하지 않습니다."
                else:
                    new_id_map: dict[str, int] = {}
                    updated_ids: list[int] = []
                    for upsert in change_set.upserts:
                        fields = upsert.generated_fields
                        payload = {
                            "title": upsert.title,
                            "narrative": fields.narrative,
                            "dimension_values": upsert.dimension_values,
                            "probability_score": Decimal(str(fields.probability_score)),
                            "probability_delta": Decimal("0"),
                            "display_order": upsert.display_order,
                            "baseline_yn": "N",
                            "global_pressure_band": fields.pressure_band,
                            "scenario_role": None,
                            "global_pressure_rationale": fields.pressure_rationale,
                            "related_markets": fields.related_markets,
                            "status": ScenarioStatus.CREATING.value,
                            "mod_usr_logn_id": user_id,
                        }
                        if upsert.scenario_id is None:
                            scenario_id = scenario_repository.insert_scenario(
                                {
                                    **payload,
                                    "scenario_group_id": scenario_group_id,
                                    "crt_usr_logn_id": user_id,
                                },
                            )
                            new_id_map[upsert.client_row_key] = scenario_id
                            target_ids.append(scenario_id)
                            continue
                        scenario_id = int(upsert.scenario_id)
                        scenario_repository.update_from_payload(
                            scenarios_by_id[scenario_id],
                            payload,
                        )
                        updated_ids.append(scenario_id)
                        target_ids.append(scenario_id)
                    scenario_repository.soft_delete_by_ids(delete_ids, user_id=user_id)
                    signpost_repository.soft_delete_by_scenario_ids(
                        [*updated_ids, *delete_ids],
                        user_id=user_id,
                    )
                    active_scenarios = scenario_repository.fetch_models_by_group_id(scenario_group_id)
                    self._apply_v4_baseline_and_roles(
                        active_scenarios,
                        list(group.dimension_definitions or []),
                        user_id=user_id,
                    )
                    group_repository.update_group(
                        group,
                        {
                            "scenario_count": len(active_scenarios),
                            "mod_usr_logn_id": user_id,
                        },
                    )
                    applied_dicts = [scenario_repository.model_to_dict(item) for item in active_scenarios]
                    applied_fingerprint = scenario_fingerprint(applied_dicts)
                    validation_result.application = ValidationApplicationPayload(
                        applied_at=datetime.now(UTC),
                        applied_scenario_fingerprint=applied_fingerprint,
                        new_scenario_id_map=new_id_map,
                    )
                    validation_operation.result_payload = validation_result.model_dump(
                        mode="json",
                        by_alias=True,
                    )

            if stale_detail is not None:
                group_repository.update_group(
                    group,
                    {
                        "stage": "scenario_created",
                        "mod_usr_logn_id": user_id,
                    },
                )
                session.commit()
                raise MIBaseError(ErrorCode.SCENARIO_VALIDATION_STALE, detail=stale_detail)

            signpost_operation_id: str | None = None
            if create_signpost_operation:
                signpost_operation_id = new_operation_id()
                ScenarioGroupOperationService().create_accepted_in_session(
                    session,
                    scenario_group_id=scenario_group_id,
                    operation_id=signpost_operation_id,
                    operation_type="signpost",
                    engine_version=str(group.api_version or "v1"),
                    user_id=user_id,
                )
                signpost_operation = operation_repository.fetch_by_id(
                    scenario_group_id,
                    signpost_operation_id,
                    for_update=True,
                )
                if signpost_operation is None:
                    raise MIBaseError(ErrorCode.UNKNOWN_ERROR, detail="Signpost operation creation failed")
                signpost_operation.result_payload = {
                    "schemaVersion": "v1",
                    "validationOperationId": validation_operation.operation_id,
                }
            session.commit()
            return {
                "operation_id": signpost_operation_id,
                "validation_operation_id": validation_operation.operation_id,
                "signpost_target_scenario_ids": target_ids,
                "scenario_group": group_repository.model_to_dict(group),
            }
        except MIBaseError as exc:
            if stale_detail is None:
                session.rollback()
            raise exc
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _apply_v4_baseline_and_roles(
        self,
        scenarios: list[Any],
        dimension_definitions: list[dict[str, Any]],
        *,
        user_id: int,
    ) -> None:
        if not scenarios:
            return
        contribution_by_value: dict[tuple[str, str], int] = {}
        contribution_score = {"bearish": -1, "balanced": 0, "bullish": 1}
        for definition in dimension_definitions:
            dimension_id = str(definition.get("dimension_id") or definition.get("dimensionId") or "")
            for value in definition.get("values") or []:
                if not isinstance(value, dict):
                    continue
                value_id = str(value.get("value_id") or value.get("valueId") or "")
                contribution = str(
                    value.get("pressure_contribution") or value.get("pressureContribution") or "balanced",
                )
                contribution_by_value[(dimension_id, value_id)] = contribution_score.get(contribution, 0)

        scenario_scores: dict[int, tuple[int, set[int]]] = {}
        for scenario in scenarios:
            contributions = {
                contribution_by_value.get((str(key), str(value)), 0)
                for key, value in (scenario.dimension_values or {}).items()
            }
            score = sum(
                contribution_by_value.get((str(key), str(value)), 0)
                for key, value in (scenario.dimension_values or {}).items()
            )
            scenario_scores[int(scenario.scenario_id)] = (score, contributions)
            scenario.baseline_yn = "N"
            scenario.scenario_role = None
            scenario.mod_usr_logn_id = user_id

        baseline = max(
            scenarios,
            key=lambda item: (
                Decimal(str(item.probability_score or 0)),
                -int(item.display_order or 0),
            ),
        )
        baseline.baseline_yn = "Y"
        # pressure band는 Base 대비 pressureContribution 합산 차이다. 편집으로 Base나 조합이 바뀌었을 수
        # 있으므로 모든 Scenario의 band를 다시 계산한다.
        base_score = scenario_scores[int(baseline.scenario_id)][0]
        delta_by_id = {
            scenario_id: score - base_score for scenario_id, (score, _contributions) in scenario_scores.items()
        }
        for scenario in scenarios:
            scenario.global_pressure_band = relative_pressure_band(delta_by_id[int(scenario.scenario_id)])

        # floor/ceiling은 Base를 제외한 Scenario 중 Base 대비 압력이 가장 낮은/높은 것이다.
        non_base = [item for item in scenarios if item is not baseline]
        if len(non_base) >= 2:
            floor = min(
                non_base,
                key=lambda item: (delta_by_id[int(item.scenario_id)], int(item.display_order or 0)),
            )
            ceiling = max(
                (item for item in non_base if item is not floor),
                key=lambda item: (delta_by_id[int(item.scenario_id)], int(item.display_order or 0)),
            )
            floor.scenario_role = "floor"
            ceiling.scenario_role = "ceiling"
        mixed_candidates = [
            item
            for item in scenarios
            if item.scenario_role is None and {-1, 1} <= scenario_scores[int(item.scenario_id)][1]
        ]
        if mixed_candidates:
            min(
                mixed_candidates,
                key=lambda item: (
                    abs(delta_by_id[int(item.scenario_id)]),
                    -Decimal(str(item.probability_score or 0)),
                ),
            ).scenario_role = "mixed"

    async def sync_from_table_async(
        self,
        scenario_group_id: int,
        event_type_l2_id: int | None,
        table_payload: ScenarioSyncTablePayload,
        user_id: int,
        new_row_details: list[NewScenarioGeneratedDetails] | None = None,
        dimension_definitions: list[dict[str, Any]] | None = None,
    ) -> ScenarioSyncResult:
        from apps.common.configs.database.sync_database.connection import (
            get_sync_session,
        )

        session = get_sync_session()
        try:
            scenario_repository = ScenarioRepository(session=session)
            signpost_repository = SignpostRepository(session=session)
            group_repository = ScenarioGroupRepository(session=session)
            group = group_repository.fetch_by_id(scenario_group_id)

            scenarios = scenario_repository.fetch_models_by_group_id(scenario_group_id)
            scenarios_by_id = {int(scenario.scenario_id): scenario for scenario in scenarios}
            requested_existing_ids: set[int] = set()
            inserted_ids: list[int] = []
            updated_ids: list[int] = []
            unchanged_existing_ids: list[int] = []
            rows = table_payload.get("rows", []) or []
            if dimension_definitions:
                template_by_key = {
                    str(definition["dimension_id"]): {
                        "dim_key": definition["dimension_id"],
                        "label": definition.get("label") or definition["dimension_id"],
                        "description": definition.get("description")
                        or definition.get("label")
                        or definition["dimension_id"],
                        "required": definition.get("required", False),
                        "value_enums": [
                            value.get("label") or value.get("value_id")
                            for value in definition.get("values") or []
                            if isinstance(value, dict)
                        ],
                        "values": list(definition.get("values") or []),
                        "display_order": definition.get(
                            "display_order",
                            999999,
                        ),
                    }
                    for definition in dimension_definitions
                }
            elif event_type_l2_id is not None:
                template_by_key = self._load_dimension_template_by_key(
                    event_type_l2_id,
                )
            else:
                raise ValueError("Scenario group dimension definitions are missing")
            if dimension_definitions:
                from apps.agents.scenario_group_agent.utils.dimension_values import (
                    build_dimension_value_catalog,
                    canonicalize_dimension_cells,
                )

                header_keys = [
                    str(header["key"])
                    for header in table_payload.get("headers", []) or []
                    if header.get("key")
                ]
                catalog = build_dimension_value_catalog(dimension_definitions)
                rows = [
                    {
                        **row,
                        "cells": canonicalize_dimension_cells(
                            catalog,
                            header_keys,
                            row.get("cells") or {},
                            allow_label_compatibility=True,
                        ),
                    }
                    for row in rows
                ]
            new_rows = [row for row in rows if row.get("scenario_id") is None]
            if new_rows and len(new_row_details or []) != len(new_rows):
                raise ValueError("Generated scenario details are required for every new scenario row")
            details_by_row_id = {id(row): detail for row, detail in zip(new_rows, new_row_details or [])}

            for row in rows:
                row_scenario_id = row.get("scenario_id")
                if row_scenario_id is None:
                    generated_details = details_by_row_id.get(id(row))
                    if generated_details is None:
                        raise ValueError("Generated scenario details are missing")
                    payload = self._row_to_new_scenario_payload(
                        scenario_group_id=scenario_group_id,
                        template_by_key=template_by_key,
                        row=row,
                        user_id=user_id,
                        generated_details=generated_details,
                    )
                    inserted_ids.append(scenario_repository.insert_scenario(payload))
                    continue

                scenario_id = int(row_scenario_id)
                scenario = scenarios_by_id.get(scenario_id)
                if scenario is None:
                    raise ValueError(f"Scenario does not belong to group: {scenario_id}")
                requested_existing_ids.add(scenario_id)
                payload = self._row_to_existing_scenario_payload(
                    template_by_key=template_by_key,
                    row=row,
                    user_id=user_id,
                )
                if self._scenario_requires_update(scenario, payload):
                    scenario_repository.update_from_payload(scenario, payload)
                    updated_ids.append(scenario_id)
                else:
                    unchanged_existing_ids.append(scenario_id)

            deleted_ids = [scenario_id for scenario_id in scenarios_by_id if scenario_id not in requested_existing_ids]
            scenario_repository.soft_delete_by_ids(deleted_ids, user_id=user_id)

            regenerate_ids = [*inserted_ids, *updated_ids]
            signpost_repository.soft_delete_by_scenario_ids(
                [*updated_ids, *deleted_ids],
                user_id=user_id,
            )

            active_scenarios = scenario_repository.fetch_models_by_group_id(scenario_group_id)
            if group is None or getattr(
                group,
                "generation_strategy",
                None,
            ) not in {
                "multi_event_source_dimensions",
                "multi_event_composite_dimensions",
                "multi_event_model_lever_dimensions",
            }:
                self._normalize_active_probability_scores(
                    active_scenarios,
                    user_id=user_id,
                )
            self._apply_baseline_by_probability(active_scenarios, user_id=user_id)

            if group is not None:
                header_keys = [
                    str(header["key"]) for header in table_payload.get("headers", []) or [] if header.get("key")
                ]
                group_repository.update_group(
                    group,
                    {
                        "dimension_selected": header_keys,
                        "scenario_count": len(active_scenarios),
                        "mod_usr_logn_id": user_id,
                    },
                )

            session.commit()
            return {
                "active_scenario_ids": [int(scenario.scenario_id) for scenario in active_scenarios],
                "regenerate_scenario_ids": regenerate_ids,
                "inserted_scenario_ids": inserted_ids,
                "updated_scenario_ids": updated_ids,
                "deleted_scenario_ids": deleted_ids,
                "unchanged_existing_scenario_ids": unchanged_existing_ids,
            }
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _normalize_dimension_values_object(self, dimension_values: dict[str, Any]) -> dict[str, Any]:
        return {str(dim_key): value for dim_key, value in dimension_values.items() if str(dim_key).strip()}

    def cells_to_dimension_values(
        self,
        event_type_l2_id: int,
        cells: dict[str, Any],
    ) -> dict[str, Any]:
        return self.cells_to_dimension_values_with_template(
            self._load_dimension_template_by_key(event_type_l2_id),
            cells,
        )

    def _load_dimension_template_by_key(
        self,
        event_type_l2_id: int,
    ) -> ScenarioDimensionTemplateByKey:
        template_json = self._load_template_json_from_db(event_type_l2_id)
        template_by_key = {
            str(item.get("dim_key")): item for item in template_json if isinstance(item, dict) and item.get("dim_key")
        }
        return template_by_key

    def cells_to_dimension_values_with_template(
        self,
        template_by_key: ScenarioDimensionTemplateByKey,
        cells: dict[str, Any],
    ) -> ScenarioDimensionValues:
        converted: dict[str, Any] = {}
        for key, value in cells.items():
            if key in template_by_key:
                converted[key] = value
        return self._normalize_dimension_values_object(converted)

    def _row_to_existing_scenario_payload(
        self,
        *,
        template_by_key: ScenarioDimensionTemplateByKey,
        row: ScenarioSyncRowPayload,
        user_id: int,
    ) -> ExistingScenarioUpdatePayload:
        return {
            "title": (row.get("title") or "")[:255],
            "dimension_values": self.cells_to_dimension_values_with_template(
                template_by_key,
                row.get("cells") or {},
            ),
            "display_order": int(row.get("display_order") or 0),
            "mod_usr_logn_id": user_id,
        }

    def _row_to_new_scenario_payload(
        self,
        *,
        scenario_group_id: int,
        template_by_key: ScenarioDimensionTemplateByKey,
        row: ScenarioSyncRowPayload,
        user_id: int,
        generated_details: NewScenarioGeneratedDetails,
    ) -> NewScenarioInsertPayload:
        return {
            "scenario_group_id": scenario_group_id,
            "title": (row.get("title") or "")[:255],
            "narrative": generated_details.narrative,
            "status": ScenarioStatus.CREATING.value,
            "dimension_values": self.cells_to_dimension_values_with_template(
                template_by_key,
                row.get("cells") or {},
            ),
            "display_order": int(row.get("display_order") or 0),
            "baseline_yn": "N",
            "crt_usr_logn_id": user_id,
            "mod_usr_logn_id": user_id,
            "probability_score": generated_details.probability_weight,
            "probability_delta": generated_details.probability_delta,
            "impact_jkm": None,
            "impact_ttf": None,
            "impact_hh": None,
        }

    def _scenario_requires_update(
        self,
        scenario: Any,
        payload: ExistingScenarioUpdatePayload,
    ) -> bool:
        for field in (
            "title",
            "dimension_values",
            "display_order",
        ):
            if self._normalize_compare_value(getattr(scenario, field)) != (
                self._normalize_compare_value(payload.get(field))
            ):
                return True
        return False

    def _normalize_compare_value(self, value: Any) -> Any:
        if isinstance(value, Decimal):
            return value
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            try:
                return Decimal(str(value))
            except Exception:
                return value
        return value

    def _normalize_active_probability_scores(
        self,
        scenarios: list[Any],
        *,
        user_id: int,
    ) -> None:
        raw_scores: list[Decimal] = []
        for scenario in scenarios:
            score = getattr(scenario, "probability_score", None)
            if score is None:
                return
            raw_scores.append(Decimal(str(score)))

        normalized_scores = _normalize_decimal_scores_to_100(raw_scores)
        for scenario, probability_score in zip(scenarios, normalized_scores):
            if self._normalize_compare_value(scenario.probability_score) == (
                self._normalize_compare_value(probability_score)
            ):
                continue
            scenario.probability_score = probability_score
            scenario.mod_usr_logn_id = user_id

    def _apply_baseline_by_probability(
        self,
        scenarios: list[Any],
        *,
        user_id: int,
    ) -> None:
        self.apply_baseline_by_probability(scenarios, user_id=user_id)

    def apply_baseline_by_probability(
        self,
        scenarios: list[Any],
        *,
        user_id: int,
    ) -> None:
        apply_single_baseline_by_probability(scenarios, user_id=user_id)
