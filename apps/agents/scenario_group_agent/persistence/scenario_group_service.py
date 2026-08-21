from __future__ import annotations

from decimal import Decimal
import hashlib
import secrets
from typing import Any, TypedDict

from sqlalchemy.exc import IntegrityError

from apps.agents.scenario_group_agent.persistence.scenario_service import (
    ScenarioService,
    is_v4_model_lever_group,
)
from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode
from apps.persistence.enums import (
    ScenarioGroupStage,
    ScenarioGroupStatus,
    ScenarioStatus,
)
from apps.persistence.event.repository import EventRepository
from apps.persistence.event.schema import EventPayload
from apps.persistence.scenario.repository import (
    ScenarioRepository,
)
from apps.persistence.scenario.schema import ScenarioPayload
from apps.persistence.scenario_group.event_set import event_set_hash
from apps.persistence.scenario_group.models import MiScenarioGroupModel
from apps.persistence.scenario_group.repository import (
    ScenarioGroupRepository,
)
from apps.persistence.scenario_group.schema import (
    ScenarioGroupPayload,
)
from apps.persistence.scenario_group_operation.models import MiScenarioGroupOperationModel
from apps.persistence.scenario_group_operation.schema import ScenarioGroupOperationPayload
from apps.persistence.signpost.repository import (
    SignpostRepository,
)


class ScenarioGroupDetailData(TypedDict):
    group: dict[str, Any]
    scenarios: list[dict[str, Any]]
    signposts: list[dict[str, Any]]


class ScenarioGroupCommonDetailData(ScenarioGroupDetailData):
    events: list[EventPayload]
    latest_operation: ScenarioGroupOperationPayload | None


class ScenarioGroupPresentationData(ScenarioGroupDetailData):
    events: list[EventPayload]
    operation: ScenarioGroupOperationPayload | None
    legacy_template_dimensions: list[dict[str, Any]]
    legacy_snapshot_dimension_values: list[dict[str, Any]]


def _normalize_probability_scores_to_100(
    rows: list[dict[str, Any]],
) -> dict[int, Decimal]:
    """rows에서 probability_score를 추출해 합계 100으로 정규화한 {row_index: score} 반환.

    하나라도 null이거나 rows가 비어있으면 빈 dict 반환 (정규화 생략).
    """
    raw: list[Decimal] = []
    for row in rows:
        metrics = row.get("metrics") or {}
        score = metrics.get("probability_score")
        if score is None:
            return {}
        try:
            raw.append(Decimal(str(score)))
        except Exception:
            return {}

    if not raw:
        return {}

    total = sum(raw)
    if total <= 0:
        equal = Decimal(100) / Decimal(len(raw))
        return {i: equal for i in range(len(raw))}

    exact = [float(s) / float(total) * 100 for s in raw]
    floors = [int(v) for v in exact]
    remainders = [v - int(v) for v in exact]
    deficit = 100 - sum(floors)
    for i in sorted(range(len(remainders)), key=lambda k: -remainders[k])[:deficit]:
        floors[i] += 1

    return {i: Decimal(str(floors[i])) for i in range(len(floors))}


class ScenarioGroupService:
    @staticmethod
    def _raise_for_event_set_conflict(
        *,
        groups: list[MiScenarioGroupModel],
        event_ids_by_group_id: dict[int, list[int]],
        latest_operations: dict[int, MiScenarioGroupOperationModel],
        active_operations: dict[int, MiScenarioGroupOperationModel],
        requested_event_ids: list[int],
        user_id: int,
    ) -> None:
        requested_set = sorted(requested_event_ids)
        exact_groups = [
            group
            for group in groups
            if sorted(event_ids_by_group_id.get(int(group.scenario_group_id), [])) == requested_set
        ]

        for group in exact_groups:
            group_id = int(group.scenario_group_id)
            active_operation = active_operations.get(group_id)
            if active_operation is not None:
                ScenarioGroupService._raise_existing_group_conflict(
                    group=group,
                    operation=active_operation,
                    user_id=user_id,
                    active=True,
                )

        for group in exact_groups:
            group_id = int(group.scenario_group_id)
            latest_operation = latest_operations.get(group_id)
            if latest_operation is not None and latest_operation.status in {"failed", "interrupted"}:
                continue
            stage = group.stage.value if hasattr(group.stage, "value") else group.stage
            if stage != ScenarioGroupStage.COMPLETED.value:
                ScenarioGroupService._raise_existing_group_conflict(
                    group=group,
                    operation=latest_operation,
                    user_id=user_id,
                    active=False,
                )

    @staticmethod
    def _raise_existing_group_conflict(
        *,
        group: MiScenarioGroupModel,
        operation: MiScenarioGroupOperationModel | None,
        user_id: int,
        active: bool,
    ) -> None:
        group_id = int(group.scenario_group_id)
        operation_id = str(operation.operation_id) if operation is not None else None
        context: dict[str, Any] = {"scenarioGroupId": group_id}
        if operation_id is not None:
            context["operationId"] = operation_id
        same_owner = group.request_usr_id is not None and int(group.request_usr_id) == user_id
        if not same_owner:
            raise MIBaseError(
                ErrorCode.SCENARIO_GROUP_OWNERSHIP_CONFLICT,
                detail=f"Scenario group {group_id} is owned by another user",
                context=context,
            )
        if active:
            raise MIBaseError(
                ErrorCode.SCENARIO_GROUP_OPERATION_CONFLICT,
                detail=f"Scenario group {group_id} operation {operation_id} is still active",
                context=context,
            )
        raise MIBaseError(
            ErrorCode.SCENARIO_GROUP_ALREADY_CREATED,
            detail=f"Scenario group {group_id} is awaiting confirmation",
            context=context,
        )

    def list_groups(
        self,
        *,
        include_deleted: bool = False,
        mi_event_id: int | None = None,
        keyword: str | None = None,
        status: str | None = None,
        stage: str | None = None,
        sort: str = "latest",
    ) -> dict[str, Any]:
        from apps.common.configs.database.sync_database.connection import (
            get_sync_session,
        )

        session = get_sync_session()
        try:
            from apps.agents.scenario_group_agent.persistence.scenario_group_operation_service import (
                ScenarioGroupOperationService,
            )
            from apps.persistence.scenario_group_operation.repository import (
                ScenarioGroupOperationRepository,
            )

            group_repository = ScenarioGroupRepository(session=session)
            scenario_repository = ScenarioRepository(session=session)
            signpost_repository = SignpostRepository(session=session)

            groups = group_repository.list_for_backoffice(
                include_deleted=include_deleted,
                mi_event_id=mi_event_id,
                keyword=keyword,
                status=status,
                stage=stage,
                sort=sort,
            )
            latest_operations = ScenarioGroupOperationRepository(session=session).fetch_latest_by_group_ids(
                [int(group.scenario_group_id) for group in groups]
            )
            relations_by_group_id = group_repository.fetch_active_group_events_by_group_ids(
                [int(group.scenario_group_id) for group in groups]
            )
            rows: list[dict[str, Any]] = []
            for group in groups:
                group_relations = relations_by_group_id.get(int(group.scenario_group_id), [])
                event_relation = group_relations[0] if len(group_relations) == 1 else None
                scenarios = scenario_repository.fetch_models_by_group_id(
                    int(group.scenario_group_id),
                    include_deleted=include_deleted,
                )
                signposts = signpost_repository.fetch_models_by_scenario_ids(
                    [int(scenario.scenario_id) for scenario in scenarios],
                    include_deleted=include_deleted,
                )
                status_value = group.status.value if hasattr(group.status, "value") else group.status
                stage_value = group.stage.value if hasattr(group.stage, "value") else group.stage
                row: dict[str, Any] = {
                    "scenarioGroupId": int(group.scenario_group_id),
                    "scenario_group_id": int(group.scenario_group_id),
                    "title": group.title,
                    "baseEventTitle": None,
                    "miEventId": int(event_relation.mi_event_id) if event_relation is not None else None,
                    "mi_event_id": int(event_relation.mi_event_id) if event_relation is not None else None,
                    "status": status_value,
                    "stage": stage_value,
                    "scenarioCount": len([scenario for scenario in scenarios if scenario.del_yn != "Y"]),
                    "scenario_count": len([scenario for scenario in scenarios if scenario.del_yn != "Y"]),
                    "signpostCount": len([signpost for signpost in signposts if signpost.del_yn != "Y"]),
                    "signpost_count": len([signpost for signpost in signposts if signpost.del_yn != "Y"]),
                    "createdAt": group.crt_dtm.isoformat() if group.crt_dtm else None,
                    "created_at": group.crt_dtm.isoformat() if group.crt_dtm else None,
                    "updatedAt": group.mod_dtm.isoformat() if group.mod_dtm else None,
                    "updated_at": group.mod_dtm.isoformat() if group.mod_dtm else None,
                    "deleted": group.del_yn == "Y",
                    "delYn": group.del_yn,
                    "del_yn": group.del_yn,
                }
                latest = latest_operations.get(int(group.scenario_group_id))
                latest_payload = (
                    ScenarioGroupOperationService.operation_payload_from_model(latest).model_dump(
                        mode="json",
                        by_alias=True,
                    )
                    if latest is not None
                    else None
                )
                row["latestOperation"] = latest_payload
                row["activeOperation"] = (
                    latest_payload if latest is not None and latest.status in {"queued", "running"} else None
                )
                rows.append(row)
            return {
                "rows": rows,
                "meta": {
                    "source": "agent_db",
                    "total": len(rows),
                    "returned": len(rows),
                    "includeDeleted": include_deleted,
                    "include_deleted": include_deleted,
                },
            }
        finally:
            session.close()

    def load_by_id(self, scenario_group_id: int) -> ScenarioGroupPayload | None:
        from apps.common.configs.database.sync_database.connection import (
            get_sync_session,
        )

        session = get_sync_session()
        try:
            repository = ScenarioGroupRepository(session=session)
            group = repository.fetch_by_id(scenario_group_id)
            if group is None:
                return None
            return ScenarioGroupPayload.from_model(
                group,
                repository.fetch_single_active_group_event(scenario_group_id),
            )
        finally:
            session.close()

    def load_detail(self, scenario_group_id: int, *, include_deleted: bool = False) -> ScenarioGroupDetailData:
        from apps.common.configs.database.sync_database.connection import (
            get_sync_session,
        )

        session = get_sync_session()
        try:
            group_repository = ScenarioGroupRepository(session=session)
            scenario_repository = ScenarioRepository(session=session)
            signpost_repository = SignpostRepository(session=session)

            group = group_repository.fetch_by_id_for_query(
                scenario_group_id,
                include_deleted=include_deleted,
            )
            if group is None:
                raise MIBaseError(
                    ErrorCode.ENTITY_NOT_FOUND,
                    detail=f"Scenario group not found: {scenario_group_id}",
                )

            scenarios = scenario_repository.fetch_models_by_group_id(
                scenario_group_id,
                include_deleted=include_deleted,
            )
            scenario_ids = [int(scenario.scenario_id) for scenario in scenarios]
            signposts = signpost_repository.fetch_models_by_scenario_ids(
                scenario_ids,
                include_deleted=include_deleted,
            )

            return {
                "group": group_repository.model_to_dict(group, include_del_yn=True),
                "scenarios": [
                    scenario_repository.model_to_dict(
                        scenario,
                        include_del_yn=True,
                    )
                    for scenario in scenarios
                ],
                "signposts": [
                    signpost_repository.model_to_dict(signpost, include_del_yn=True) for signpost in signposts
                ],
            }
        finally:
            session.close()

    def load_common_detail(
        self,
        scenario_group_id: int,
        *,
        include_deleted: bool = False,
    ) -> ScenarioGroupCommonDetailData:
        from apps.agents.scenario_group_agent.persistence.event_service import EventService
        from apps.agents.scenario_group_agent.persistence.scenario_group_operation_service import (
            ScenarioGroupOperationService,
        )

        detail = self.load_detail(scenario_group_id, include_deleted=include_deleted)
        event_ids = self.load_event_ids(scenario_group_id)
        return {
            **detail,
            "events": EventService().load_events(event_ids) if event_ids else [],
            "latest_operation": ScenarioGroupOperationService().get_latest(scenario_group_id),
        }

    def load_presentation_detail(
        self,
        scenario_group_id: int,
        *,
        operation_id: str | None = None,
    ) -> ScenarioGroupPresentationData:
        from apps.agents.scenario_group_agent.persistence.event_service import EventService
        from apps.agents.scenario_group_agent.persistence.scenario_group_operation_service import (
            ScenarioGroupOperationService,
        )

        detail = self.load_detail(scenario_group_id)
        group = detail["group"]
        event_ids = self.load_event_ids(scenario_group_id)
        operation_service = ScenarioGroupOperationService()
        operation = (
            operation_service.get_operation(scenario_group_id, operation_id)
            if operation_id is not None
            else operation_service.get_latest(scenario_group_id)
        )
        return {
            **detail,
            "events": EventService().load_events(event_ids) if event_ids else [],
            "operation": operation,
            "legacy_template_dimensions": self._load_trusted_legacy_template_dimensions(group),
            "legacy_snapshot_dimension_values": self._load_legacy_snapshot_dimension_values(
                scenario_group_id,
                group,
            ),
        }

    @staticmethod
    def _load_trusted_legacy_template_dimensions(group: dict[str, Any]) -> list[dict[str, Any]]:
        if str(group.get("api_version") or "v1") != "v1":
            return []
        event_type_l2_id = group.get("event_type_l2_id")
        stored_checksum = str(group.get("template_checksum") or "").strip()
        if event_type_l2_id is None or not stored_checksum:
            return []
        try:
            template = ScenarioService().load_template_record(int(event_type_l2_id))
        except (KeyError, ValueError):
            return []
        if str(template.get("template_checksum") or "") != stored_checksum:
            return []
        return [item for item in template.get("template_json") or [] if isinstance(item, dict)]

    @staticmethod
    def _load_legacy_snapshot_dimension_values(
        scenario_group_id: int,
        group: dict[str, Any],
    ) -> list[dict[str, Any]]:
        if str(group.get("api_version") or "v1") != "v1":
            return []
        from apps.common.configs.database.sync_database.connection import get_sync_session

        session = get_sync_session()
        try:
            rows = ScenarioGroupRepository(session=session).fetch_latest_confirmation_dimension_values(
                scenario_group_id,
            )
            return [item for row in rows for item in row]
        finally:
            session.close()

    def approve_dimension_mappings(
        self,
        scenario_group_id: int,
        *,
        user_id: int,
        decisions: list[dict[str, Any]],
    ) -> tuple[bool, list[dict[str, Any]]]:
        group = self.load_by_id(scenario_group_id)
        if group is None:
            raise MIBaseError(
                ErrorCode.ENTITY_NOT_FOUND,
                detail=f"Scenario group not found: {scenario_group_id}",
            )
        if group.request_usr_id is not None and group.request_usr_id != user_id:
            raise MIBaseError(
                ErrorCode.SCENARIO_GROUP_OWNERSHIP_CONFLICT,
                detail=f"이미 사용자 {group.request_usr_id}가 점유하고 있습니다.",
            )
        results = ScenarioService().decide_mapping_proposals(scenario_group_id, decisions, user_id)
        refreshed = self.load_by_id(scenario_group_id)
        if refreshed is None:
            raise MIBaseError(
                ErrorCode.ENTITY_NOT_FOUND,
                detail=f"Scenario group not found: {scenario_group_id}",
            )
        return refreshed.parameter_mapping_ready, results

    def load_event_ids(self, scenario_group_id: int) -> list[int]:
        from apps.common.configs.database.sync_database.connection import (
            get_sync_session,
        )

        session = get_sync_session()
        try:
            return [
                int(relation.mi_event_id)
                for relation in ScenarioGroupRepository(
                    session=session,
                ).fetch_group_events(scenario_group_id)
            ]
        finally:
            session.close()

    def prepare_multi_event_group(
        self,
        *,
        events: list[dict[str, Any]],
        templates: list[dict[str, Any]],
        api_version: str,
        generation_strategy: str,
        user_id: int,
    ) -> ScenarioGroupPayload:
        from apps.common.configs.database.sync_database.connection import (
            get_sync_session,
        )

        event_ids = [int(event["mi_event_id"]) for event in events]
        if len(events) != len(templates):
            raise MIBaseError(
                ErrorCode.INVALID_REQUEST,
                detail="Every event must have a scenario template",
            )
        requested_template_checksums = {
            event_id: str(template["template_checksum"])
            for event_id, template in zip(event_ids, templates, strict=True)
        }
        checksum_material = "|".join(
            f"{event_id}:{requested_template_checksums[event_id]}" for event_id in sorted(requested_template_checksums)
        )
        aggregate_checksum = hashlib.sha256(
            checksum_material.encode("utf-8"),
        ).hexdigest()

        session = get_sync_session()
        try:
            repository = ScenarioGroupRepository(session=session)
            scenario_group_id = repository.insert_group(
                {
                    "request_usr_id": user_id,
                    "title": f"Scenario group ({len(events)} selected events)",
                    "summary": "선택 MI Event 기반 시나리오",
                    "description": None,
                    "dimension_selected": [],
                    "scenario_count": 0,
                    "status": ScenarioGroupStatus.CREATING.value,
                    "stage": ScenarioGroupStage.READY.value,
                    "api_version": api_version,
                    "generation_strategy": generation_strategy,
                    "comparison_run_id": None,
                    "template_checksum": aggregate_checksum,
                    "parameter_mapping_ready": False,
                    "dimension_definitions": [],
                    "generation_diagnostics": {},
                    "crt_usr_logn_id": user_id,
                    "mod_usr_logn_id": user_id,
                },
            )
            for display_order, (event, template) in enumerate(
                zip(events, templates, strict=True),
                start=1,
            ):
                repository.insert_group_event(
                    {
                        "scenario_group_id": scenario_group_id,
                        "mi_event_id": int(event["mi_event_id"]),
                        "event_type_l2_id": int(event["event_type_l2_id"]),
                        "scenario_dimension_template_id": int(
                            template["scenario_dimension_template_id"],
                        ),
                        "template_checksum": str(
                            template["template_checksum"],
                        ),
                        "display_order": display_order,
                        "crt_usr_logn_id": user_id,
                        "mod_usr_logn_id": user_id,
                    },
                )
            session.commit()
            created = repository.fetch_by_id(scenario_group_id)
            if created is None:
                raise MIBaseError(
                    ErrorCode.UNKNOWN_ERROR,
                    detail="Scenario group not found after creation",
                )
            return ScenarioGroupPayload.from_model(
                created,
                repository.fetch_single_active_group_event(scenario_group_id),
            )
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def prepare_v4_multi_event_group(
        self,
        *,
        events: list[dict[str, Any]],
        impact_catalog_version: str,
        impact_catalog_checksum: str,
        user_id: int,
        operation_id: str | None = None,
    ) -> ScenarioGroupPayload:
        from apps.common.configs.database.sync_database.connection import (
            get_sync_session,
        )

        event_ids = [int(event["mi_event_id"]) for event in events]
        requested_event_set_hash = event_set_hash(event_ids)
        session = get_sync_session()
        try:
            repository = ScenarioGroupRepository(session=session)
            if operation_id is not None:
                locked_event_ids = EventRepository(session=session).lock_events(event_ids)
                if locked_event_ids != sorted(event_ids):
                    missing_event_ids = sorted(set(event_ids) - set(locked_event_ids))
                    raise MIBaseError(
                        ErrorCode.ENTITY_NOT_FOUND,
                        detail=f"Events not found while preparing creation: {missing_event_ids}",
                    )
                candidates = repository.fetch_event_set_candidates(
                    engine_version="v4",
                    event_set_hash=requested_event_set_hash,
                    for_update=True,
                )
                candidate_group_ids = [int(group.scenario_group_id) for group in candidates]
                from apps.persistence.scenario_group_operation.repository import (
                    ScenarioGroupOperationRepository,
                )

                operation_repository = ScenarioGroupOperationRepository(session=session)
                self._raise_for_event_set_conflict(
                    groups=candidates,
                    event_ids_by_group_id=repository.fetch_event_ids_by_group_ids(candidate_group_ids),
                    latest_operations=operation_repository.fetch_latest_by_group_ids(
                        candidate_group_ids,
                        for_update=True,
                    ),
                    active_operations=operation_repository.fetch_active_by_group_ids(
                        candidate_group_ids,
                        for_update=True,
                    ),
                    requested_event_ids=event_ids,
                    user_id=user_id,
                )
            scenario_group_id = repository.insert_group(
                {
                    "request_usr_id": user_id,
                    "title": f"Global LNG scenario group ({len(events)} selected events)",
                    "summary": "선택 MI Event 기반 모델 영향 레버 시나리오",
                    "description": None,
                    "dimension_selected": [],
                    "scenario_count": 0,
                    "status": ScenarioGroupStatus.CREATING.value,
                    "stage": ScenarioGroupStage.READY.value,
                    "api_version": "v4",
                    "generation_strategy": "multi_event_model_lever_dimensions",
                    "event_set_hash": requested_event_set_hash,
                    "comparison_run_id": None,
                    "impact_catalog_version": impact_catalog_version,
                    "impact_catalog_checksum": impact_catalog_checksum,
                    "template_checksum": None,
                    "parameter_mapping_ready": True,
                    "dimension_definitions": [],
                    "generation_diagnostics": {},
                    "crt_usr_logn_id": user_id,
                    "mod_usr_logn_id": user_id,
                },
            )
            for display_order, event in enumerate(events, start=1):
                repository.insert_group_event(
                    {
                        "scenario_group_id": scenario_group_id,
                        "mi_event_id": int(event["mi_event_id"]),
                        "event_type_l2_id": int(event["event_type_l2_id"]),
                        "scenario_dimension_template_id": None,
                        "template_checksum": None,
                        "display_order": display_order,
                        "crt_usr_logn_id": user_id,
                        "mod_usr_logn_id": user_id,
                    },
                )
            if operation_id is not None:
                from apps.agents.scenario_group_agent.persistence.scenario_group_operation_service import (
                    ScenarioGroupOperationService,
                )

                ScenarioGroupOperationService().create_accepted_in_session(
                    session,
                    scenario_group_id=scenario_group_id,
                    operation_id=operation_id,
                    operation_type="create",
                    engine_version="v4",
                    user_id=user_id,
                )
            session.commit()
            created = repository.fetch_by_id(scenario_group_id)
            if created is None:
                raise MIBaseError(
                    ErrorCode.UNKNOWN_ERROR,
                    detail="Scenario group not found after v4 creation",
                )
            return ScenarioGroupPayload.from_model(
                created,
                repository.fetch_single_active_group_event(scenario_group_id),
            )
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def persist_multi_event_generation(
        self,
        *,
        scenario_group_id: int,
        title: str,
        description: str,
        dimension_definitions: list[dict[str, Any]],
        generation_diagnostics: dict[str, Any],
        scenarios: list[dict[str, Any]],
        user_id: int,
    ) -> tuple[ScenarioGroupPayload, list[ScenarioPayload]]:
        """Persist scenarios and group metadata in one transaction."""
        from apps.common.configs.database.sync_database.connection import (
            get_sync_session,
        )

        session = get_sync_session()
        try:
            group_repository = ScenarioGroupRepository(session=session)
            scenario_repository = ScenarioRepository(session=session)
            group = group_repository.fetch_by_id(scenario_group_id)
            if group is None:
                raise MIBaseError(
                    ErrorCode.ENTITY_NOT_FOUND,
                    detail=f"Scenario group not found: {scenario_group_id}",
                )
            if scenario_repository.fetch_models_by_group_id(
                scenario_group_id,
            ):
                raise MIBaseError(
                    ErrorCode.SCENARIO_GROUP_ALREADY_CREATED,
                    detail=f"Scenario group ID: {scenario_group_id}",
                )

            for display_order, scenario in enumerate(scenarios, start=1):
                scenario_repository.insert_scenario(
                    {
                        "scenario_group_id": scenario_group_id,
                        "title": str(scenario["title"])[:255],
                        "narrative": scenario.get("narrative") or "",
                        "status": ScenarioStatus.CREATING.value,
                        "dimension_values": dict(
                            scenario.get("dimension_values") or {},
                        ),
                        "probability_score": Decimal(
                            str(scenario["probability_score"]),
                        ),
                        "probability_delta": Decimal("0.0"),
                        "impact_jkm": None,
                        "impact_ttf": None,
                        "impact_hh": None,
                        "display_order": display_order,
                        "baseline_yn": scenario["baseline_yn"],
                        "global_pressure_band": scenario["pressure_band"],
                        "scenario_role": scenario.get("scenario_role"),
                        "global_pressure_rationale": scenario["pressure_rationale"],
                        "related_markets": list(
                            scenario.get("related_markets") or [],
                        ),
                        "crt_usr_logn_id": user_id,
                        "mod_usr_logn_id": user_id,
                    },
                )
            group_repository.update_group(
                group,
                {
                    "title": title[:255],
                    "description": description,
                    "dimension_selected": [definition["dimension_id"] for definition in dimension_definitions],
                    "dimension_definitions": dimension_definitions,
                    "generation_diagnostics": generation_diagnostics,
                    "scenario_count": len(scenarios),
                    "status": ScenarioGroupStatus.CREATING.value,
                    "stage": ScenarioGroupStage.SCENARIO_CREATED.value,
                    "mod_usr_logn_id": user_id,
                },
            )
            persisted_scenarios = scenario_repository.fetch_models_by_group_id(
                scenario_group_id,
            )
            session.commit()
            return (
                ScenarioGroupPayload.from_model(
                    group,
                    group_repository.fetch_single_active_group_event(scenario_group_id),
                ),
                [ScenarioPayload.from_model(scenario) for scenario in persisted_scenarios],
            )
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def set_parameter_mapping_ready(
        self,
        scenario_group_id: int,
        *,
        ready: bool,
        user_id: int,
    ) -> None:
        from apps.common.configs.database.sync_database.connection import (
            get_sync_session,
        )

        session = get_sync_session()
        try:
            repository = ScenarioGroupRepository(session=session)
            group = repository.fetch_by_id(scenario_group_id)
            if group is None:
                raise MIBaseError(
                    ErrorCode.ENTITY_NOT_FOUND,
                    detail=f"Scenario group not found: {scenario_group_id}",
                )
            repository.update_group(
                group,
                {
                    "parameter_mapping_ready": ready,
                    "mod_usr_logn_id": user_id,
                },
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def update_state(
        self,
        scenario_group_id: int,
        *,
        status: ScenarioGroupStatus | str | None = None,
        stage: ScenarioGroupStage | str | None = None,
        dimension_selected: list[str] | None = None,
        title: str | None = None,
        description: str | None = None,
        user_id: int | None = None,
    ) -> dict[str, Any] | None:
        from apps.common.configs.database.sync_database.connection import (
            get_sync_session,
        )

        session = get_sync_session()
        try:
            repository = ScenarioGroupRepository(session=session)
            group = repository.fetch_by_id(scenario_group_id)
            if group is None:
                raise MIBaseError(
                    ErrorCode.ENTITY_NOT_FOUND,
                    detail=f"Scenario group not found: {scenario_group_id}. It might be deleted.",
                )
            payload: dict[str, Any] = {}
            if status is not None:
                payload["status"] = status.value if isinstance(status, ScenarioGroupStatus) else status
            if stage is not None:
                payload["stage"] = stage.value if isinstance(stage, ScenarioGroupStage) else stage
            if dimension_selected is not None:
                payload["dimension_selected"] = dimension_selected
            if title is not None:
                payload["title"] = title
            if description is not None:
                payload["description"] = description
            if user_id is not None:
                payload["mod_usr_logn_id"] = user_id
            repository.update_group(group, payload)
            session.commit()
            return repository.model_to_dict(group)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def soft_delete_group(self, scenario_group_id: int, *, user_id: int, authorization: str | None) -> dict[str, int]:
        self._assert_delete_authorization(authorization)

        from apps.common.configs.database.sync_database.connection import (
            get_sync_session,
        )

        session = get_sync_session()
        try:
            group_repository = ScenarioGroupRepository(session=session)
            scenario_repository = ScenarioRepository(session=session)
            signpost_repository = SignpostRepository(session=session)

            group = group_repository.fetch_by_id_for_query(
                scenario_group_id,
                include_deleted=False,
            )
            if group is None:
                raise MIBaseError(
                    ErrorCode.ENTITY_NOT_FOUND,
                    detail=f"Scenario group not found: {scenario_group_id}",
                )

            scenarios = scenario_repository.fetch_models_by_group_id(
                scenario_group_id,
            )
            scenario_ids = [int(scenario.scenario_id) for scenario in scenarios]
            signpost_deleted = signpost_repository.soft_delete_by_scenario_ids(
                scenario_ids,
                user_id=user_id,
            )
            scenario_deleted = scenario_repository.soft_delete_by_group_id(
                scenario_group_id,
                user_id=user_id,
            )
            scenario_group_deleted = group_repository.soft_delete_group(
                group,
                user_id=user_id,
            )
            session.commit()
            return {
                "scenario_group_deleted": scenario_group_deleted,
                "scenario_deleted": scenario_deleted,
                "signpost_deleted": signpost_deleted,
            }
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def soft_delete_group_for_owner(self, scenario_group_id: int, *, user_id: int) -> dict[str, int]:
        """Business soft delete used by the common Multi-Event API."""
        from apps.common.configs.database.sync_database.connection import get_sync_session
        from apps.persistence.scenario_group_operation.repository import ScenarioGroupOperationRepository

        session = get_sync_session()
        try:
            group_repository = ScenarioGroupRepository(session=session)
            scenario_repository = ScenarioRepository(session=session)
            signpost_repository = SignpostRepository(session=session)
            group = group_repository.fetch_by_id_for_query(scenario_group_id, include_deleted=False)
            if group is None:
                raise MIBaseError(
                    ErrorCode.ENTITY_NOT_FOUND,
                    detail=f"Scenario group not found: {scenario_group_id}",
                )
            if group.request_usr_id is not None and int(group.request_usr_id) != user_id:
                raise MIBaseError(
                    ErrorCode.SCENARIO_GROUP_OWNERSHIP_CONFLICT,
                    detail=f"Scenario group owner is user {group.request_usr_id}",
                )
            active = ScenarioGroupOperationRepository(session=session).fetch_active(scenario_group_id)
            if active is not None:
                raise MIBaseError(
                    ErrorCode.SCENARIO_GROUP_OPERATION_CONFLICT,
                    detail=f"Operation is still {active.status}: {active.operation_id}",
                )
            scenarios = scenario_repository.fetch_models_by_group_id(scenario_group_id)
            scenario_ids = [int(scenario.scenario_id) for scenario in scenarios]
            signpost_deleted = signpost_repository.soft_delete_by_scenario_ids(scenario_ids, user_id=user_id)
            scenario_deleted = scenario_repository.soft_delete_by_group_id(scenario_group_id, user_id=user_id)
            scenario_group_deleted = group_repository.soft_delete_group(group, user_id=user_id)
            session.commit()
            return {
                "scenario_group_deleted": scenario_group_deleted,
                "scenario_deleted": scenario_deleted,
                "signpost_deleted": signpost_deleted,
            }
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def soft_delete_signposts_by_group_id(
        self, scenario_group_id: int, *, user_id: int, authorization: str | None
    ) -> dict[str, int]:
        self._assert_delete_authorization(authorization)

        from apps.common.configs.database.sync_database.connection import (
            get_sync_session,
        )

        session = get_sync_session()
        try:
            group_repository = ScenarioGroupRepository(session=session)
            scenario_repository = ScenarioRepository(session=session)
            signpost_repository = SignpostRepository(session=session)

            group = group_repository.fetch_by_id_for_query(
                scenario_group_id,
                include_deleted=False,
            )
            if group is None:
                raise MIBaseError(
                    ErrorCode.ENTITY_NOT_FOUND,
                    detail=f"Scenario group not found: {scenario_group_id}",
                )

            scenarios = scenario_repository.fetch_models_by_group_id(scenario_group_id)
            scenario_ids = [int(scenario.scenario_id) for scenario in scenarios]
            signpost_deleted = signpost_repository.soft_delete_by_scenario_ids(
                scenario_ids,
                user_id=user_id,
            )
            session.commit()
            return {"signpost_deleted": signpost_deleted}
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def hard_delete_group(
        self,
        scenario_group_id: int,
        *,
        user_id: int,
        confirm: bool,
        authorization: str | None,
    ) -> dict[str, int]:
        if not confirm:
            raise MIBaseError(
                ErrorCode.INVALID_REQUEST,
                detail="confirm=true is required",
            )
        self._assert_delete_authorization(authorization)

        from apps.common.configs.database.sync_database.connection import (
            get_sync_session,
        )

        session = get_sync_session()
        try:
            repository = ScenarioGroupRepository(session=session)
            if (
                repository.fetch_by_id_for_query(
                    scenario_group_id,
                    include_deleted=True,
                )
                is None
            ):
                raise MIBaseError(
                    ErrorCode.ENTITY_NOT_FOUND,
                    detail=f"Scenario group not found: {scenario_group_id}",
                )
            counts = repository.hard_delete_group(scenario_group_id)
            session.commit()
            return counts
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _assert_delete_authorization(self, authorization: str | None) -> None:
        from apps.common.configs.config import get_settings

        bearer_token = self._extract_bearer_token(authorization)
        allowed_tokens = get_settings().scenario_group_admin_bearer_tokens
        if not bearer_token or not any(
            secrets.compare_digest(bearer_token, allowed_token) for allowed_token in allowed_tokens if allowed_token
        ):
            raise MIBaseError(
                ErrorCode.SCENARIO_GROUP_ADMIN_FORBIDDEN,
                detail="Invalid Authorization bearer token",
            )

    def _extract_bearer_token(self, authorization: str | None) -> str | None:
        if not authorization:
            return None
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token.strip():
            return None
        return token.strip()

    def _assert_group_owner(self, group: dict[str, Any], *, user_id: int) -> None:
        request_usr_id = group.get("request_usr_id")
        if request_usr_id is not None and int(request_usr_id) != int(user_id):
            raise MIBaseError(
                ErrorCode.SCENARIO_GROUP_OWNERSHIP_CONFLICT,
                detail=f"이미 사용자 {request_usr_id}가 점유하고 있습니다.",
            )

    def apply_confirmation(
        self,
        scenario_group_id: int,
        scenario_group_payload: dict[str, Any],
        table_payload: dict[str, Any],
        user_id: int | None = None,
    ) -> dict[str, Any]:
        from apps.common.configs.database.sync_database.connection import (
            get_sync_session,
        )

        session = get_sync_session()
        try:
            group_repository = ScenarioGroupRepository(session=session)
            scenario_repository = ScenarioRepository(session=session)
            signpost_repository = SignpostRepository(session=session)

            group = group_repository.fetch_by_id(scenario_group_id)
            if group is None:
                return {"status": "failure", "message": "Scenario group not found"}
            if getattr(group, "generation_strategy", None) in {
                "multi_event_source_dimensions",
                "multi_event_composite_dimensions",
                "multi_event_model_lever_dimensions",
            } and not getattr(group, "parameter_mapping_ready", False):
                return {
                    "status": "failure",
                    "message": ("Dimension value mapping approvals are not complete"),
                }

            scenarios = scenario_repository.fetch_models_by_group_id(scenario_group_id)
            scenarios_by_id = {int(scenario.scenario_id): scenario for scenario in scenarios}
            signposts = signpost_repository.fetch_models_by_scenario_ids(list(scenarios_by_id))
            signposts_by_id = {int(signpost.signpost_id): signpost for signpost in signposts}
            event_relation = group_repository.fetch_single_active_group_event(scenario_group_id)

            rows = table_payload.get("rows", [])
            scenario_service = ScenarioService()
            requires_v4_value_ids = is_v4_model_lever_group(group)
            group_dimension_template = (
                scenario_service.build_group_dimension_template_by_key(
                    group.dimension_definitions,
                    require_catalog_value_ids=True,
                )
                if requires_v4_value_ids
                else {}
            )
            normalized_scores = (
                {}
                if getattr(group, "generation_strategy", None)
                in {
                    "multi_event_source_dimensions",
                    "multi_event_composite_dimensions",
                    "multi_event_model_lever_dimensions",
                }
                else _normalize_probability_scores_to_100(rows)
            )

            for row_index, row in enumerate(rows):
                scenario_id = int(row["scenario_id"])
                scenario = scenarios_by_id.get(scenario_id)
                if scenario is None:
                    return {
                        "status": "failure",
                        "message": f"Scenario does not belong to group: {scenario_id}",
                    }
                if requires_v4_value_ids:
                    try:
                        dimension_values = scenario_service.cells_to_dimension_values_with_template(
                            group_dimension_template,
                            row["cells"],
                            require_complete_catalog_values=True,
                        )
                    except ValueError as exc:
                        session.rollback()
                        return {
                            "status": "failure",
                            "message": str(exc),
                            "error_code": ErrorCode.INVALID_REQUEST.name,
                        }
                elif getattr(group, "dimension_definitions", None):
                    dimension_values = {
                        str(key): value for key, value in row["cells"].items()
                    }
                else:
                    if event_relation is None:
                        return {
                            "status": "failure",
                            "message": "Scenario group requires exactly one active Event relation",
                        }
                    dimension_values = scenario_service.cells_to_dimension_values(
                        int(event_relation.event_type_l2_id),
                        row["cells"],
                    )
                scenario_update: dict[str, Any] = {
                    "dimension_values": dimension_values,
                }
                if user_id is not None:
                    scenario_update["mod_usr_logn_id"] = user_id
                for field in ("title", "narrative", "display_order", "baseline_yn"):
                    if field in row:
                        scenario_update[field] = row[field]
                if "metrics" in row and row["metrics"] is not None:
                    metrics = row["metrics"]
                    if "probability_score" in metrics:
                        scenario_update["probability_score"] = normalized_scores.get(
                            row_index, metrics["probability_score"]
                        )
                    if "probability_delta" in metrics:
                        scenario_update["probability_delta"] = metrics["probability_delta"]
                scenario_repository.update_from_payload(
                    scenario,
                    scenario_update,
                )
                for signpost_payload in row.get("signposts", []):
                    if user_id is not None:
                        signpost_payload["mod_usr_logn_id"] = user_id
                    signpost_id = int(signpost_payload["signpost_id"])
                    signpost = signposts_by_id.get(signpost_id)
                    if signpost is None or int(signpost.scenario_id) != scenario_id:
                        return {
                            "status": "failure",
                            "message": f"Signpost does not belong to scenario: {signpost_id}",
                        }
                    signpost_repository.update_from_payload(signpost, signpost_payload)

            ScenarioService().apply_baseline_by_probability(
                scenarios,
                user_id=user_id if user_id is not None else 0,
            )
            scenario_repository.update_status(scenario_group_id, ScenarioStatus.CREATED.value)

            group_update: dict[str, Any] = {
                "scenario_count": len(scenarios),
                "status": ScenarioGroupStatus.CREATED.value,
                "stage": ScenarioGroupStage.COMPLETED.value,
            }
            if user_id is not None:
                group_update["mod_usr_logn_id"] = user_id
            for field in ("title", "summary", "description", "dimension_selected"):
                if field in scenario_group_payload:
                    group_update[field] = scenario_group_payload[field]
            group_repository.update_group(group, group_update)
            if not scenarios:
                return {"status": "failure", "message": "No scenarios to confirm"}
            if not signposts:
                return {"status": "failure", "message": "No signposts to confirm"}

            signposts_by_scenario_id: dict[int, list] = {}
            for signpost in signposts:
                signposts_by_scenario_id.setdefault(int(signpost.scenario_id), []).append(signpost)
            snapshot_id = group_repository.create_confirmation_snapshot(
                scenario_group_id=scenario_group_id,
                scenarios=scenarios,
                signposts_by_scenario_id=signposts_by_scenario_id,
            )
            group_repository.update_group(
                group,
                {
                    "status": ScenarioGroupStatus.CREATED.value,
                    "stage": ScenarioGroupStage.COMPLETED.value,
                },
            )
            session.commit()
            return {
                "status": "success",
                "snapshot_id": snapshot_id,
                "scenario_count": len(scenarios),
                "signpost_count": len(signposts),
                "group": group_repository.model_to_dict(group),
            }
        except IntegrityError as exc:
            session.rollback()
            return {
                "status": "failure",
                "message": f"DB constraint violation: {exc}",
            }
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def create_confirmation_snapshot(self, scenario_group_id: int) -> dict[str, Any]:
        from apps.common.configs.database.sync_database.connection import (
            get_sync_session,
        )

        session = get_sync_session()
        try:
            group_repository = ScenarioGroupRepository(session=session)
            scenario_repository = ScenarioRepository(session=session)
            signpost_repository = SignpostRepository(session=session)

            group = group_repository.fetch_by_id(scenario_group_id)
            if group is None:
                return {"status": "failure", "message": "Scenario group not found"}

            scenarios = scenario_repository.fetch_models_by_group_id(scenario_group_id)
            if not scenarios:
                return {"status": "failure", "message": "No scenarios to confirm"}

            signposts = signpost_repository.fetch_models_by_scenario_ids([int(s.scenario_id) for s in scenarios])
            if not signposts:
                return {"status": "failure", "message": "No signposts to confirm"}

            signposts_by_scenario_id: dict[int, list] = {}
            for signpost in signposts:
                signposts_by_scenario_id.setdefault(int(signpost.scenario_id), []).append(signpost)

            snapshot_id = group_repository.create_confirmation_snapshot(
                scenario_group_id=scenario_group_id,
                scenarios=scenarios,
                signposts_by_scenario_id=signposts_by_scenario_id,
            )
            group_repository.update_scenario_count(scenario_group_id, len(scenarios))
            scenario_repository.update_status(scenario_group_id, ScenarioStatus.CREATED.value)
            group_repository.update_group(
                group,
                {
                    "status": ScenarioGroupStatus.CREATED.value,
                    "stage": ScenarioGroupStage.COMPLETED.value,
                },
            )
            session.commit()
            return {
                "status": "success",
                "snapshot_id": snapshot_id,
                "scenario_count": len(scenarios),
                "signpost_count": len(signposts),
            }
        except IntegrityError as exc:
            session.rollback()
            return {
                "status": "failure",
                "message": f"DB constraint violation: {exc}",
            }
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
