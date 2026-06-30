from __future__ import annotations

import asyncio
from decimal import Decimal
from typing import TYPE_CHECKING, Any, TypedDict

from pydantic import BaseModel, ConfigDict

from apps.agents.scenario_group_agent.baseline_contrast import (
    apply_single_baseline_by_probability,
)
from apps.agents.scenario_group_agent.persistence.scenario.repository import (
    ScenarioRepository,
)
from apps.agents.scenario_group_agent.persistence.scenario_group.repository import (
    ScenarioGroupRepository,
)
from apps.agents.scenario_group_agent.persistence.signpost.repository import (
    SignpostRepository,
)
from apps.agents.scenario_group_agent.schemas.domain.event import EventPayload
from apps.agents.scenario_group_agent.schemas.domain.scenario import ScenarioPayload
from apps.agents.scenario_group_agent.schemas.enums import ScenarioStatus
from apps.agents.scenario_group_agent.schemas.graph.generation import (
    ScenarioTemplate,
    TemplateDimension,
)


if TYPE_CHECKING:
    from apps.agents.scenario_group_agent.schemas.domain.template import (
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


class NewScenarioGeneratedDetails(BaseModel):
    model_config = ConfigDict(frozen=True)

    narrative: str
    probability_weight: Decimal
    probability_delta: Decimal
    impact_jkm: str | None
    impact_ttf: str | None
    impact_hh: str | None

_LIKELIHOOD_WEIGHTS: dict[str, int] = {
    "very_low": 5,
    "low": 10,
    "medium": 20,
    "high": 35,
    "very_high": 50,
}


def _normalize_scores_to_100(likelihoods: list[str]) -> list[Decimal]:
    """likelihood_prior 목록을 합계가 정확히 100인 probability_score 목록으로 변환.

    각 tier의 상대 가중치를 기반으로 비례 배분하고,
    나머지는 largest-remainder 방식으로 처리해 정수 합계 100을 보장한다.
    """
    weights = [
        Decimal(_LIKELIHOOD_WEIGHTS.get(t, _LIKELIHOOD_WEIGHTS["medium"]))
        for t in likelihoods
    ]
    return _normalize_decimal_scores_to_100(weights)


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
    def load_dimension_template(
        self, event_type_l2_id: int
    ) -> list["CommonScenarioTemplateDimension"]:
        from apps.agents.scenario_group_agent.schemas.domain.template import (
            ScenarioTemplateDimension as CommonScenarioTemplateDimension,
        )

        pipeline_template = self.load_pipeline_template(event_type_l2_id)
        return [
            CommonScenarioTemplateDimension(
                dimension_id=dimension.dim_key,
                label_ko=dimension.label,
                description=dimension.label,
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

    def load_pipeline_template(self, event_type_l2_id: int) -> ScenarioTemplate:
        template_json = self._load_template_json_from_db(event_type_l2_id)
        return self._map_template_json_to_pipeline_template(
            template_json,
            event_type_l2_id,
        )

    def load_scenario_template(
        self, event_type_l2_id: int
    ) -> "CommonScenarioTemplate":
        from apps.agents.scenario_group_agent.schemas.domain.template import (
            ScenarioTemplate as CommonScenarioTemplate,
            ScenarioTemplateDimension,
            ScenarioTemplateEnum,
        )

        pipeline_template = self.load_pipeline_template(event_type_l2_id)
        dimensions = [
            ScenarioTemplateDimension(
                dimension_id=dimension.dim_key,
                label_ko=dimension.label,
                description=dimension.label,
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

    def _load_template_json_from_db(
        self, event_type_l2_id: int
    ) -> list[dict[str, Any]]:
        from apps.common.configs.database.sync_database.connection import (
            get_sync_session,
        )

        session = get_sync_session()
        try:
            template_json = ScenarioRepository(
                session=session
            )._load_template_json_from_db(event_type_l2_id)
        finally:
            session.close()

        if template_json is None:
            raise KeyError(
                f"scenario dimension template 없음: event_type_l2_id={event_type_l2_id}"
            )

        if not isinstance(template_json, list):
            raise ValueError(
                "tmm_mi_scenario_dimension_template_m.template_json must be JSON ARRAY "
                f"(event_type_l2_id={event_type_l2_id})"
            )
        return template_json

    def _map_template_json_to_pipeline_template(
        self,
        template_json: list[dict[str, Any]],
        event_type_l2_id: int,
    ) -> ScenarioTemplate:
        if not template_json:
            raise ValueError(
                f"template_json is empty: event_type_l2_id={event_type_l2_id}"
            )

        dimensions = [
            self._map_template_dimension(item, event_type_l2_id, index)
            for index, item in enumerate(template_json, start=1)
        ]
        return ScenarioTemplate(
            label_ko=f"event_type_l2_id={event_type_l2_id}",
            template_dimensions_total=len(dimensions),
            dimensions=dimensions,
            compatibility_rules=[],
        )

    def _map_template_dimension(
        self,
        raw_dimension: dict[str, Any],
        event_type_l2_id: int,
        index: int,
    ) -> TemplateDimension:
        if not isinstance(raw_dimension, dict):
            raise ValueError(
                "template_json item must be object: "
                f"event_type_l2_id={event_type_l2_id}, index={index}"
            )

        dim_key = str(raw_dimension.get("dim_key", "")).strip()
        if not dim_key:
            raise ValueError(
                "dim_key is required: "
                f"event_type_l2_id={event_type_l2_id}, index={index}"
            )

        raw_value_enums = raw_dimension.get("value_enums") or []
        if not isinstance(raw_value_enums, list):
            raise ValueError(
                "value_enums must be array: "
                f"event_type_l2_id={event_type_l2_id}, dim_key={dim_key}"
            )

        return TemplateDimension(
            label=str(raw_dimension.get("label", "")).strip() or dim_key,
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
                ScenarioPayload.model_validate(repository.model_to_dict(model))
                for model in repository.fetch_models_by_group_id(scenario_group_id)
            ]
        finally:
            session.close()

    def save_generated_scenarios(
        self,
        scenario_group_id: int,
        scenario_result: dict[str, Any],
        user_id: int,
    ) -> list[int]:
        from apps.common.configs.database.sync_database.connection import (
            get_sync_session,
        )

        stage4 = scenario_result.get("stage4_scenario_synthesis", {}) or {}
        stage5 = scenario_result.get("stage5_validation", {}) or {}
        scenarios = stage4.get("scenarios", []) or []
        likelihood_prior = stage5.get("likelihood_prior", {}) or {}

        likelihoods = [
            likelihood_prior.get(scenario.get("scenario_id", ""), "medium")
            for scenario in scenarios
        ]
        normalized_scores = _normalize_scores_to_100(likelihoods)

        session = get_sync_session()
        try:
            repository = ScenarioRepository(session=session)
            saved_ids: list[int] = []
            for index, (scenario, probability_score) in enumerate(
                zip(scenarios, normalized_scores), start=1
            ):
                price_direction = scenario.get("price_direction", {}) or {}
                payload = {
                    "scenario_group_id": scenario_group_id,
                    "title": (scenario.get("title") or "")[:255],
                    "narrative": scenario.get("description") or "",
                    "status": ScenarioStatus.CREATING.value,
                    "dimension_values": self._normalize_dimension_values_object(
                        scenario.get("dimension_values") or {}
                    ),
                    "probability_score": probability_score,
                    "probability_delta": Decimal("0.0"),
                    "impact_jkm": price_direction.get("jkm"),
                    "impact_ttf": price_direction.get("ttf"),
                    "impact_hh": price_direction.get("hh"),
                    "display_order": index,
                    "baseline_yn": "N",
                    "crt_usr_logn_id": user_id,
                    "mod_usr_logn_id": user_id,
                }
                saved_ids.append(repository.insert_scenario(payload))
            self.apply_baseline_by_probability(
                repository.fetch_models_by_group_id(scenario_group_id),
                user_id=user_id,
            )
            session.commit()
            return saved_ids
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

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
        event_type_l2_id: int,
        table_payload: ScenarioSyncTablePayload,
        user_id: int,
        event_data: EventPayload | dict[str, Any] | None = None,
    ) -> ScenarioSyncResult:
        return asyncio.run(
            self.sync_from_table_async(
                scenario_group_id=scenario_group_id,
                event_type_l2_id=event_type_l2_id,
                table_payload=table_payload,
                user_id=user_id,
                event_data=event_data,
            )
        )

    async def sync_from_table_async(
        self,
        scenario_group_id: int,
        event_type_l2_id: int,
        table_payload: ScenarioSyncTablePayload,
        user_id: int,
        event_data: EventPayload | dict[str, Any] | None = None,
    ) -> ScenarioSyncResult:
        from apps.common.configs.database.sync_database.connection import (
            get_sync_session,
        )

        session = get_sync_session()
        try:
            scenario_repository = ScenarioRepository(session=session)
            signpost_repository = SignpostRepository(session=session)
            group_repository = ScenarioGroupRepository(session=session)

            scenarios = scenario_repository.fetch_models_by_group_id(
                scenario_group_id
            )
            scenarios_by_id = {
                int(scenario.scenario_id): scenario for scenario in scenarios
            }
            requested_existing_ids: set[int] = set()
            inserted_ids: list[int] = []
            updated_ids: list[int] = []
            unchanged_existing_ids: list[int] = []
            rows = table_payload.get("rows", []) or []
            template_by_key = self._load_dimension_template_by_key(event_type_l2_id)
            new_rows = [row for row in rows if row.get("scenario_id") is None]
            new_row_details = await self._generate_new_row_details_async(
                event_data,
                [
                    self.cells_to_dimension_values_with_template(
                        template_by_key,
                        row.get("cells") or {},
                    )
                    for row in new_rows
                ],
            )
            details_by_row_id = {
                id(row): detail for row, detail in zip(new_rows, new_row_details)
            }

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
                    raise ValueError(
                        f"Scenario does not belong to group: {scenario_id}"
                    )
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

            deleted_ids = [
                scenario_id
                for scenario_id in scenarios_by_id
                if scenario_id not in requested_existing_ids
            ]
            scenario_repository.soft_delete_by_ids(deleted_ids, user_id=user_id)

            regenerate_ids = [*inserted_ids, *updated_ids]
            signpost_repository.soft_delete_by_scenario_ids(
                [*updated_ids, *deleted_ids],
                user_id=user_id,
            )

            active_scenarios = scenario_repository.fetch_models_by_group_id(
                scenario_group_id
            )
            self._normalize_active_probability_scores(
                active_scenarios,
                user_id=user_id,
            )
            self._apply_baseline_by_probability(active_scenarios, user_id=user_id)

            group = group_repository.fetch_by_id(scenario_group_id)
            if group is not None:
                header_keys = [
                    str(header["key"])
                    for header in table_payload.get("headers", []) or []
                    if header.get("key")
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
                "active_scenario_ids": [
                    int(scenario.scenario_id) for scenario in active_scenarios
                ],
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

    def _normalize_dimension_values_object(
        self, dimension_values: dict[str, Any]
    ) -> dict[str, Any]:
        return {
            str(dim_key): value
            for dim_key, value in dimension_values.items()
            if str(dim_key).strip()
        }

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
            str(item.get("dim_key")): item
            for item in template_json
            if isinstance(item, dict) and item.get("dim_key")
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

    def _generate_new_row_details(
        self,
        event_data: EventPayload | dict[str, Any] | None,
        dimension_values_list: list[ScenarioDimensionValues],
    ) -> list[NewScenarioGeneratedDetails]:
        return asyncio.run(
            self._generate_new_row_details_async(
                event_data=event_data,
                dimension_values_list=dimension_values_list,
            )
        )

    async def _generate_new_row_details_async(
        self,
        event_data: EventPayload | dict[str, Any] | None,
        dimension_values_list: list[ScenarioDimensionValues],
    ) -> list[NewScenarioGeneratedDetails]:
        if not dimension_values_list:
            return []
        if event_data is None:
            raise ValueError("event_data is required to create new scenario rows")

        from apps.agents.scenario_group_agent.subgraphs.scenario_generation.generation_stages import (
            stage1_build_context_pack,
            stage4_synthesize_fixed_scenarios,
            stage5_validate,
        )

        pack = stage1_build_context_pack(event_data)
        stage4 = await stage4_synthesize_fixed_scenarios(
            pack,
            [
                {str(key): str(value) for key, value in dimension_values.items()}
                for dimension_values in dimension_values_list
            ],
        )
        stage5 = await stage5_validate(pack, stage4)
        likelihoods = [
            stage5.likelihood_prior.get(scenario.scenario_id, "medium")
            for scenario in stage4.scenarios
        ]
        details: list[NewScenarioGeneratedDetails] = []
        for scenario, likelihood in zip(stage4.scenarios, likelihoods):
            details.append(
                NewScenarioGeneratedDetails(
                    narrative=scenario.description,
                    probability_weight=Decimal(
                        _LIKELIHOOD_WEIGHTS.get(
                            likelihood,
                            _LIKELIHOOD_WEIGHTS["medium"],
                        )
                    ),
                    probability_delta=Decimal("0.0"),
                    impact_jkm=scenario.price_direction.jkm,
                    impact_ttf=scenario.price_direction.ttf,
                    impact_hh=scenario.price_direction.hh,
                )
            )
        return details

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
            "impact_jkm": generated_details.impact_jkm,
            "impact_ttf": generated_details.impact_ttf,
            "impact_hh": generated_details.impact_hh,
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
