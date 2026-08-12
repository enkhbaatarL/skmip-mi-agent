from __future__ import annotations

from collections.abc import Collection, Mapping
from decimal import Decimal
from typing import Any

from pydantic import BaseModel

from apps.agents.model_parameter_agent.utils.lut.keys import (
    apply_numeric_precision,
)
from apps.agents.model_parameter_agent.utils.lut.precision import (
    NumericPrecisionMode,
)
from apps.common.configs.config import get_settings
from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode
from apps.persistence.event.repository import EventRepository
from apps.persistence.model_parameter.repository import ModelParameterRepository
from apps.persistence.scenario.repository import ScenarioRepository
from apps.persistence.scenario_group.repository import ScenarioGroupRepository


CONFIRMABLE_PROPOSAL_STATUSES = ("PROPOSED", "CONFIRMED")
PROCESSING_PROPOSAL_STATUSES = ("PROCESSING",)
CALLBACK_READY_PROPOSAL_STATUSES = ("PROPOSED", "CONFIRMED", "FAILED")
CALLBACK_TARGET_STATUSES = {"SUCCEEDED", "FAILED", "SKIPPED"}
PERSISTED_PARAMETER_VALUE_FIELDS = frozenset({"basecaseValue", "proposedValue"})
ParameterValuePrecision = Mapping[str, tuple[int, NumericPrecisionMode]]
V1_GENERATION_STRATEGY = "single_event_template_dimensions"
V3_GENERATION_STRATEGY = "multi_event_composite_dimensions"


def _json_payload(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json", by_alias=True)
    if isinstance(value, dict):
        return {str(key): _json_payload(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_payload(item) for item in value]
    return value


def _normalize_persisted_parameter_values(
    value: Any,
    *,
    field_precision: ParameterValuePrecision,
    path: str = "parameters",
) -> Any:
    """Bound stored basecase/proposed values regardless of the caller path."""
    if isinstance(value, dict):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            field_path = f"{path}.{key}"
            if key in PERSISTED_PARAMETER_VALUE_FIELDS and item is not None:
                max_decimal_places, precision_mode = field_precision[key]
                normalized[key] = apply_numeric_precision(
                    item,
                    label=field_path,
                    max_decimal_places=max_decimal_places,
                    mode=precision_mode,
                )
            else:
                normalized[key] = _normalize_persisted_parameter_values(
                    item,
                    field_precision=field_precision,
                    path=field_path,
                )
        return normalized
    if isinstance(value, list):
        return [
            _normalize_persisted_parameter_values(
                item,
                field_precision=field_precision,
                path=f"{path}[{index}]",
            )
            for index, item in enumerate(value)
        ]
    return value


def _parameter_json_payload(value: Any) -> Any:
    settings = get_settings()
    return _normalize_persisted_parameter_values(
        _json_payload(value),
        field_precision={
            "basecaseValue": (
                settings.model_parameter_basecase_value_max_decimal_places,
                settings.model_parameter_basecase_value_precision_mode,
            ),
            "proposedValue": (
                settings.model_parameter_proposed_value_max_decimal_places,
                settings.model_parameter_proposed_value_precision_mode,
            ),
        },
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


def _proposal_for_update(
    repository: ModelParameterRepository,
    model_param_proposal_id: int,
) -> dict[str, Any]:
    proposal = repository.fetch_model_param_proposal_for_update(
        model_param_proposal_id,
    )
    if proposal is None:
        raise MIBaseError(
            ErrorCode.ENTITY_NOT_FOUND,
            detail=(f"Model parameter proposal not found: model_param_proposal_id={model_param_proposal_id}"),
        )
    return proposal


def _ensure_proposal_status(
    proposal: dict[str, Any],
    *,
    model_param_proposal_id: int,
    allowed_statuses: Collection[str],
    action: str,
) -> None:
    status = str(proposal.get("status") or "")
    if status in allowed_statuses:
        return
    expected = " or ".join(allowed_statuses)
    raise MIBaseError(
        ErrorCode.INVALID_REQUEST,
        detail=(
            f"Model parameter proposal must be {expected} before {action}: "
            f"model_param_proposal_id={model_param_proposal_id}, status={status}"
        ),
    )


def _ensure_transition_updated(
    updated: bool,
    *,
    model_param_proposal_id: int,
) -> None:
    if updated:
        return
    raise MIBaseError(
        ErrorCode.ENTITY_NOT_FOUND,
        detail=(
            "Model parameter proposal disappeared during state transition: "
            f"model_param_proposal_id={model_param_proposal_id}"
        ),
    )


def _model_field(value: Any, field_name: str, default: Any = None) -> Any:  # noqa: ANN401
    if isinstance(value, Mapping):
        return value.get(field_name, default)
    return getattr(value, field_name, default)


def _json_field(value: Mapping[str, Any], *field_names: str) -> Any:  # noqa: ANN401
    for field_name in field_names:
        if field_name in value:
            return value[field_name]
    return None


def _required_context_int(value: Any, *, field_name: str) -> int:  # noqa: ANN401
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise MIBaseError(
            ErrorCode.INVALID_REQUEST,
            detail=f"{field_name} is required for model parameter context",
        ) from exc


def _load_v1_context(
    *,
    scenario: Any,  # noqa: ANN401
    group: Any,  # noqa: ANN401
    scenario_repository: ScenarioRepository,
    group_repository: ScenarioGroupRepository,
    event_repository: EventRepository,
) -> dict[str, Any]:
    scenario_group_id = _required_context_int(
        _model_field(group, "scenario_group_id"),
        field_name="scenario_group.scenario_group_id",
    )
    relation = group_repository.fetch_single_active_group_event(
        scenario_group_id,
    )
    if relation is None:
        raise MIBaseError(
            ErrorCode.INVALID_REQUEST,
            detail=(
                "v1 scenario group must contain exactly one active event relation: "
                f"scenario_group_id={scenario_group_id}"
            ),
        )
    mi_event_id = _required_context_int(
        _model_field(relation, "mi_event_id"),
        field_name="scenario_group_event.mi_event_id",
    )
    event_type_l2_id = _required_context_int(
        _model_field(relation, "event_type_l2_id"),
        field_name="scenario_group_event.event_type_l2_id",
    )
    group_context = _group_to_context_dict(group)
    group_context.update(
        {
            "mi_event_id": mi_event_id,
            "event_type_l2_id": event_type_l2_id,
        },
    )
    return {
        "scenario": _scenario_to_context_dict(scenario),
        "scenario_group": group_context,
        "event": event_repository.fetch_event_by_id(mi_event_id) or {},
        "events": [],
        "event_type": event_repository.fetch_event_type_by_l2_id(event_type_l2_id) or {},
        "dimension_template": scenario_repository.fetch_dimension_template(
            event_type_l2_id,
        ),
        "dimension_lineage": [],
        "validation_warnings": [],
    }


def _group_event_to_context(
    relation: Any,  # noqa: ANN401
    event: dict[str, Any],
    event_type: dict[str, Any],
) -> dict[str, Any]:
    mi_event_id = _required_context_int(
        _model_field(relation, "mi_event_id"),
        field_name="scenario_group_event.mi_event_id",
    )
    event_type_l2_id = _required_context_int(
        _model_field(relation, "event_type_l2_id"),
        field_name="scenario_group_event.event_type_l2_id",
    )
    payload = {
        **event,
        "mi_event_id": mi_event_id,
        "event_type_l2_id": event_type_l2_id,
        "scenario_dimension_template_id": _optional_int(
            _model_field(relation, "scenario_dimension_template_id"),
        ),
        "template_checksum": _model_field(relation, "template_checksum"),
        "display_order": _required_context_int(
            _model_field(relation, "display_order"),
            field_name="scenario_group_event.display_order",
        ),
        "event_type": event_type,
    }
    return _json_safe(payload)


def _dimension_mapping_to_context(mapping: Any) -> dict[str, Any]:  # noqa: ANN401
    return {
        "dimension_value_id": _model_field(mapping, "dimension_value_id"),
        "dimension_id": _model_field(mapping, "dimension_id"),
        "display_value": _model_field(mapping, "display_value"),
        "source_projections": _json_safe(
            _model_field(mapping, "source_projections", []) or [],
        ),
        "mapping_proposal": _json_safe(
            _model_field(mapping, "mapping_proposal", {}) or {},
        ),
        "mapping_version": _optional_int(
            _model_field(mapping, "mapping_version"),
        ),
        "status": str(_model_field(mapping, "status", "") or ""),
    }


def _normalized_source_event_ids(
    definition: Mapping[str, Any],
    *,
    dimension_key: str,
) -> list[int]:
    raw_ids = _json_field(definition, "source_event_ids", "sourceEventIds")
    if not isinstance(raw_ids, list) or not raw_ids:
        raise MIBaseError(
            ErrorCode.INVALID_REQUEST,
            detail=(f"v3 dimension sourceEventIds must be a non-empty array: dimension={dimension_key}"),
        )
    event_ids = [
        _required_context_int(
            raw_id,
            field_name=f"dimensionDefinitions[{dimension_key}].sourceEventIds",
        )
        for raw_id in raw_ids
    ]
    if len(set(event_ids)) != len(event_ids):
        raise MIBaseError(
            ErrorCode.INVALID_REQUEST,
            detail=f"v3 dimension contains duplicate sourceEventIds: {dimension_key}",
        )
    return event_ids


def _normalized_source_refs(
    definition: Mapping[str, Any],
    *,
    dimension_key: str,
) -> list[dict[str, Any]]:
    raw_refs = _json_field(definition, "source_refs", "sourceRefs")
    if not isinstance(raw_refs, list) or not raw_refs:
        raise MIBaseError(
            ErrorCode.INVALID_REQUEST,
            detail=(f"v3 dimension sourceRefs must be a non-empty array: dimension={dimension_key}"),
        )
    refs: list[dict[str, Any]] = []
    seen: set[tuple[int, str]] = set()
    for raw_ref in raw_refs:
        if not isinstance(raw_ref, Mapping):
            raise MIBaseError(
                ErrorCode.INVALID_REQUEST,
                detail=f"v3 dimension sourceRef must be an object: dimension={dimension_key}",
            )
        template_id = _required_context_int(
            _json_field(
                raw_ref,
                "scenario_dimension_template_id",
                "scenarioDimensionTemplateId",
            ),
            field_name=(f"dimensionDefinitions[{dimension_key}].sourceRefs.scenarioDimensionTemplateId"),
        )
        mapping_dimension_key = str(
            _json_field(raw_ref, "dim_key", "dimKey") or "",
        ).strip()
        if not mapping_dimension_key:
            raise MIBaseError(
                ErrorCode.INVALID_REQUEST,
                detail=(
                    f"v3 dimension sourceRef.dimKey is required: dimension={dimension_key}, template={template_id}"
                ),
            )
        ref_key = (template_id, mapping_dimension_key)
        if ref_key in seen:
            raise MIBaseError(
                ErrorCode.INVALID_REQUEST,
                detail=f"v3 dimension contains duplicate sourceRefs: {dimension_key}",
            )
        seen.add(ref_key)
        refs.append(
            {
                "scenario_dimension_template_id": template_id,
                "dim_key": mapping_dimension_key,
            },
        )
    return refs


def _matching_value_definition(
    definition: Mapping[str, Any],
    selected_value: Any,  # noqa: ANN401
) -> dict[str, Any] | None:
    selected_text = str(selected_value).strip()
    raw_values = _json_field(definition, "values")
    if not isinstance(raw_values, list):
        return None
    for raw_value in raw_values:
        if not isinstance(raw_value, Mapping):
            continue
        value_id = str(_json_field(raw_value, "value_id", "valueId") or "").strip()
        label = str(_json_field(raw_value, "label") or "").strip()
        if selected_text not in {value_id, label}:
            continue
        return {
            "value_id": value_id or None,
            "label": label or selected_text,
            "description": _json_field(raw_value, "description"),
            "derivation_rationale": _json_field(
                raw_value,
                "derivation_rationale",
                "derivationRationale",
            ),
            "pressure_contribution": _json_field(
                raw_value,
                "pressure_contribution",
                "pressureContribution",
            ),
        }
    return None


def _normalize_v3_dimension_lineage(  # noqa: C901
    *,
    scenario: dict[str, Any],
    group: dict[str, Any],
    events: list[dict[str, Any]],
    dimension_mappings: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    definitions = group.get("dimension_definitions") or []
    if not isinstance(definitions, list) or not definitions:
        raise MIBaseError(
            ErrorCode.INVALID_REQUEST,
            detail="v3 scenario group dimensionDefinitions are required",
        )
    dimension_values = scenario.get("dimension_values")
    if not isinstance(dimension_values, dict):
        raise MIBaseError(
            ErrorCode.INVALID_REQUEST,
            detail="v3 scenario.dimension_values must be a JSON object",
        )

    relations_by_template: dict[int, list[dict[str, Any]]] = {}
    group_event_ids: set[int] = set()
    for event in events:
        event_id = _required_context_int(
            event.get("mi_event_id"),
            field_name="scenario_group_event.mi_event_id",
        )
        group_event_ids.add(event_id)
        template_id = _optional_int(event.get("scenario_dimension_template_id"))
        if template_id is not None:
            relations_by_template.setdefault(template_id, []).append(event)

    mappings_by_value: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for mapping in dimension_mappings:
        key = (
            str(mapping.get("dimension_id") or ""),
            str(mapping.get("display_value") or ""),
        )
        mappings_by_value.setdefault(key, []).append(mapping)

    definition_by_key: dict[str, Mapping[str, Any]] = {}
    for raw_definition in definitions:
        if not isinstance(raw_definition, Mapping):
            raise MIBaseError(
                ErrorCode.INVALID_REQUEST,
                detail="v3 dimensionDefinitions item must be an object",
            )
        dimension_key = str(
            _json_field(raw_definition, "dimension_id", "dimensionId") or "",
        ).strip()
        if not dimension_key:
            raise MIBaseError(
                ErrorCode.INVALID_REQUEST,
                detail="v3 dimensionDefinitions.dimensionId is required",
            )
        if dimension_key in definition_by_key:
            raise MIBaseError(
                ErrorCode.INVALID_REQUEST,
                detail=f"v3 dimensionDefinitions contains duplicate dimensionId: {dimension_key}",
            )
        definition_by_key[dimension_key] = raw_definition

    warnings: list[str] = []
    if not bool(group.get("parameter_mapping_ready")):
        warnings.append(
            "v3 scenario group parameter_mapping_ready=false; approved source projections are optional evidence",
        )

    lineage: list[dict[str, Any]] = []
    lineage_event_ids: set[int] = set()
    for dimension_key, selected_value in dimension_values.items():
        definition = definition_by_key.get(str(dimension_key))
        if definition is None:
            warnings.append(
                f"v3 dimensionDefinitions에 없는 scenario dimension을 제외했습니다: dimension={dimension_key}",
            )
            continue
        source_event_ids = _normalized_source_event_ids(
            definition,
            dimension_key=str(dimension_key),
        )
        unknown_event_ids = sorted(set(source_event_ids) - group_event_ids)
        if unknown_event_ids:
            raise MIBaseError(
                ErrorCode.INVALID_REQUEST,
                detail=(
                    "v3 dimension sourceEventIds are not members of the scenario group: "
                    f"dimension={dimension_key}, event_ids={unknown_event_ids}"
                ),
            )
        source_refs = _normalized_source_refs(
            definition,
            dimension_key=str(dimension_key),
        )
        mapped_sources: list[dict[str, Any]] = []
        covered_event_ids: set[int] = set()
        for source_ref in source_refs:
            template_id = int(source_ref["scenario_dimension_template_id"])
            matching_relations = [
                relation
                for relation in relations_by_template.get(template_id, [])
                if int(relation["mi_event_id"]) in source_event_ids
            ]
            if not matching_relations:
                raise MIBaseError(
                    ErrorCode.INVALID_REQUEST,
                    detail=(
                        "v3 sourceRef does not match a scenario group event relation: "
                        f"dimension={dimension_key}, template={template_id}, "
                        f"dim_key={source_ref['dim_key']}"
                    ),
                )
            event_ids_by_type: dict[int, list[int]] = {}
            for relation in matching_relations:
                event_id = int(relation["mi_event_id"])
                covered_event_ids.add(event_id)
                event_type_l2_id = _required_context_int(
                    relation.get("event_type_l2_id"),
                    field_name="scenario_group_event.event_type_l2_id",
                )
                event_ids_by_type.setdefault(event_type_l2_id, []).append(event_id)
            for event_type_l2_id, matched_event_ids in event_ids_by_type.items():
                mapped_sources.append(
                    {
                        "mapping_dimension_key": source_ref["dim_key"],
                        "event_type_l2_id": event_type_l2_id,
                        "scenario_dimension_template_id": template_id,
                        "source_event_ids": list(dict.fromkeys(matched_event_ids)),
                        "source_ref": dict(source_ref),
                    },
                )
        uncovered_event_ids = sorted(set(source_event_ids) - covered_event_ids)
        if uncovered_event_ids:
            raise MIBaseError(
                ErrorCode.INVALID_REQUEST,
                detail=(
                    "v3 sourceEventIds are not covered by sourceRefs: "
                    f"dimension={dimension_key}, event_ids={uncovered_event_ids}"
                ),
            )
        lineage_event_ids.update(source_event_ids)

        value_definition = _matching_value_definition(definition, selected_value)
        matching_mappings = mappings_by_value.get(
            (str(dimension_key), str(selected_value)),
            [],
        )
        approved_mappings = [
            mapping for mapping in matching_mappings if str(mapping.get("status") or "").lower() == "approved"
        ]
        approved_source_projections = [
            projection
            for mapping in approved_mappings
            for projection in mapping.get("source_projections") or []
            if isinstance(projection, dict)
        ]
        if matching_mappings and not approved_mappings:
            statuses = sorted(
                {str(mapping.get("status") or "unknown") for mapping in matching_mappings},
            )
            warnings.append(
                "v3 dimension value source projection is not approved and was ignored: "
                f"dimension={dimension_key}, value={selected_value}, statuses={statuses}",
            )
        elif value_definition is None and not approved_source_projections:
            warnings.append(
                "v3 free dimension value has no approved source projection; raw composite value is used: "
                f"dimension={dimension_key}, value={selected_value}",
            )

        lineage.append(
            {
                "scenario_dimension_key": str(dimension_key),
                "scenario_dimension_label": _json_field(definition, "label") or str(dimension_key),
                "scenario_dimension_description": _json_field(
                    definition,
                    "description",
                ),
                "scenario_dimension_rationale": _json_field(
                    definition,
                    "rationale",
                ),
                "scenario_dimension_value": selected_value,
                "scenario_dimension_value_id": (value_definition.get("value_id") if value_definition else None),
                "scenario_dimension_value_label": (
                    value_definition.get("label") if value_definition else str(selected_value)
                ),
                "value_description": (value_definition.get("description") if value_definition else None),
                "derivation_rationale": (value_definition.get("derivation_rationale") if value_definition else None),
                "pressure_contribution": (value_definition.get("pressure_contribution") if value_definition else None),
                "source_event_ids": source_event_ids,
                "source_refs": source_refs,
                "mapped_sources": mapped_sources,
                "approved_source_projections": approved_source_projections,
                "approved_projection_mappings": approved_mappings,
                "parameter_mapping_ready": bool(
                    group.get("parameter_mapping_ready"),
                ),
                "is_free_value": value_definition is None,
            },
        )
    orphan_group_event_ids = sorted(group_event_ids - lineage_event_ids)
    if orphan_group_event_ids:
        raise MIBaseError(
            ErrorCode.INVALID_REQUEST,
            detail=(
                "v3 scenario group events are not referenced by selected dimension lineage: "
                f"event_ids={orphan_group_event_ids}"
            ),
        )
    return lineage, warnings


def _load_v3_context(
    *,
    scenario: Any,  # noqa: ANN401
    group: Any,  # noqa: ANN401
    scenario_repository: ScenarioRepository,
    group_repository: ScenarioGroupRepository,
    event_repository: EventRepository,
) -> dict[str, Any]:
    api_version = str(_model_field(group, "api_version", "") or "")
    if api_version != "v3":
        raise MIBaseError(
            ErrorCode.INVALID_REQUEST,
            detail=(f"multi_event_composite_dimensions requires api_version=v3: api_version={api_version}"),
        )
    scenario_group_id = _required_context_int(
        _model_field(group, "scenario_group_id"),
        field_name="scenario_group.scenario_group_id",
    )
    relations = group_repository.fetch_group_events(scenario_group_id)
    if not 2 <= len(relations) <= 5:
        raise MIBaseError(
            ErrorCode.INVALID_REQUEST,
            detail=(
                "v3 scenario group must contain 2 to 5 event relations: "
                f"scenario_group_id={scenario_group_id}, count={len(relations)}"
            ),
        )

    events: list[dict[str, Any]] = []
    for relation in relations:
        event_id = _required_context_int(
            _model_field(relation, "mi_event_id"),
            field_name="scenario_group_event.mi_event_id",
        )
        event_type_l2_id = _required_context_int(
            _model_field(relation, "event_type_l2_id"),
            field_name="scenario_group_event.event_type_l2_id",
        )
        event = event_repository.fetch_event_by_id(event_id)
        if event is None:
            raise MIBaseError(
                ErrorCode.INVALID_REQUEST,
                detail=(
                    "v3 scenario group relation references a missing event: "
                    f"scenario_group_id={scenario_group_id}, mi_event_id={event_id}"
                ),
            )
        actual_event_type_l2_id = _optional_int(
            event.get("event_type_l2_id"),
        )
        if actual_event_type_l2_id != event_type_l2_id:
            raise MIBaseError(
                ErrorCode.INVALID_REQUEST,
                detail=(
                    "v3 scenario group relation event type does not match the event: "
                    f"mi_event_id={event_id}, relation_event_type_l2_id="
                    f"{event_type_l2_id}, event_event_type_l2_id="
                    f"{actual_event_type_l2_id}"
                ),
            )
        event_type = event_repository.fetch_event_type_by_l2_id(event_type_l2_id)
        if event_type is None:
            raise MIBaseError(
                ErrorCode.INVALID_REQUEST,
                detail=(
                    f"v3 scenario group relation references a missing event type: event_type_l2_id={event_type_l2_id}"
                ),
            )
        events.append(_group_event_to_context(relation, event, event_type))

    scenario_context = _scenario_to_context_dict(scenario)
    group_context = _group_to_context_dict(group)
    dimension_mappings = [
        _dimension_mapping_to_context(mapping)
        for mapping in scenario_repository.fetch_mappings_by_group_id(
            scenario_group_id,
        )
    ]
    dimension_lineage, warnings = _normalize_v3_dimension_lineage(
        scenario=scenario_context,
        group=group_context,
        events=events,
        dimension_mappings=dimension_mappings,
    )
    return {
        "scenario": scenario_context,
        "scenario_group": group_context,
        "event": {},
        "events": events,
        "event_type": {},
        "dimension_template": group_context.get("dimension_definitions") or [],
        "dimension_value_mappings": dimension_mappings,
        "dimension_lineage": dimension_lineage,
        "validation_warnings": warnings,
    }


class ModelParameterService:
    def load_context(self, scenario_id: int) -> dict[str, Any]:
        from apps.common.configs.database.sync_database.connection import get_sync_session

        session = get_sync_session()
        try:
            scenario_repository = ScenarioRepository(session=session)
            group_repository = ScenarioGroupRepository(session=session)
            event_repository = EventRepository(session=session)
            model_parameter_repository = ModelParameterRepository(session=session)

            scenario = scenario_repository.fetch_model_by_id(scenario_id)
            if scenario is None:
                context = None
            else:
                group = group_repository.fetch_by_id(int(scenario.scenario_group_id))
                if group is None:
                    context = None
                else:
                    mapping_rules, parameter_definitions = (
                        model_parameter_repository.fetch_parameter_mapping_resources()
                    )
                    strategy = str(getattr(group, "generation_strategy", None) or V1_GENERATION_STRATEGY)
                    if strategy == V3_GENERATION_STRATEGY:
                        context = _load_v3_context(
                            scenario=scenario,
                            group=group,
                            scenario_repository=scenario_repository,
                            group_repository=group_repository,
                            event_repository=event_repository,
                        )
                    elif strategy == V1_GENERATION_STRATEGY:
                        context = _load_v1_context(
                            scenario=scenario,
                            group=group,
                            scenario_repository=scenario_repository,
                            group_repository=group_repository,
                            event_repository=event_repository,
                        )
                    else:
                        raise MIBaseError(
                            ErrorCode.INVALID_REQUEST,
                            detail=(
                                f"Unsupported scenario generation strategy for model parameter proposal: {strategy}"
                            ),
                        )
                    context["parameter_mapping_resources"] = {
                        "mapping_rules": mapping_rules,
                        "parameter_definitions": parameter_definitions,
                    }
        finally:
            session.close()

        if context is None:
            raise MIBaseError(
                ErrorCode.ENTITY_NOT_FOUND,
                detail=f"Scenario context not found: scenario_id={scenario_id}",
            )
        return context

    def load_parameter_mapping_resources(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        from apps.common.configs.database.sync_database.connection import get_sync_session

        session = get_sync_session()
        try:
            return ModelParameterRepository(session=session).fetch_parameter_mapping_resources()
        finally:
            session.close()

    def load_model_parameter_definitions(self) -> list[dict[str, Any]]:
        from apps.common.configs.database.sync_database.connection import get_sync_session

        session = get_sync_session()
        try:
            return ModelParameterRepository(session=session).fetch_model_parameter_definitions()
        finally:
            session.close()

    def save_proposal_result(
        self,
        *,
        scenario_context: dict[str, Any],
        user_id: int | None = None,
        proposal_parameters: list[Any],
    ) -> int:
        from apps.common.configs.database.sync_database.connection import get_sync_session

        scenario = scenario_context.get("scenario") or {}
        scenario_group = scenario_context.get("scenario_group") or {}
        event = scenario_context.get("event") or {}
        scenario_id = _required_int(
            scenario.get("scenario_id"),
            field_name="scenario.scenario_id",
        )
        scenario_group_id = _required_int(
            scenario.get("scenario_group_id") or scenario_group.get("scenario_group_id"),
            field_name="scenario_group.scenario_group_id",
        )
        mi_event_id = _proposal_event_id(
            scenario_group=scenario_group,
            event=event,
        )
        request_usr_id = _optional_int(user_id)
        payload = _parameter_json_payload(proposal_parameters)

        session = get_sync_session()
        try:
            proposal_id = ModelParameterRepository(session=session).create_model_param_proposal(
                scenario_id=scenario_id,
                scenario_group_id=scenario_group_id,
                mi_event_id=mi_event_id,
                request_usr_id=request_usr_id,
                proposal_parameters=payload,
            )
            session.commit()
            return proposal_id
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def create_processing_proposal(
        self,
        *,
        scenario_context: dict[str, Any],
        user_id: int | None = None,
    ) -> int:
        from apps.common.configs.database.sync_database.connection import get_sync_session

        scenario = scenario_context.get("scenario") or {}
        scenario_group = scenario_context.get("scenario_group") or {}
        event = scenario_context.get("event") or {}
        scenario_id = _required_int(
            scenario.get("scenario_id"),
            field_name="scenario.scenario_id",
        )
        scenario_group_id = _required_int(
            scenario.get("scenario_group_id") or scenario_group.get("scenario_group_id"),
            field_name="scenario_group.scenario_group_id",
        )
        mi_event_id = _proposal_event_id(
            scenario_group=scenario_group,
            event=event,
        )
        request_usr_id = _optional_int(user_id)

        session = get_sync_session()
        try:
            proposal_id = ModelParameterRepository(
                session=session,
            ).create_processing_model_param_proposal(
                scenario_id=scenario_id,
                scenario_group_id=scenario_group_id,
                mi_event_id=mi_event_id,
                request_usr_id=request_usr_id,
            )
            session.commit()
            return proposal_id
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def complete_proposal_result(
        self,
        *,
        model_param_proposal_id: int,
        proposal_parameters: list[Any],
    ) -> None:
        from apps.common.configs.database.sync_database.connection import get_sync_session

        payload = _parameter_json_payload(proposal_parameters)
        session = get_sync_session()
        try:
            repository = ModelParameterRepository(session=session)
            proposal = _proposal_for_update(repository, model_param_proposal_id)
            _ensure_proposal_status(
                proposal,
                model_param_proposal_id=model_param_proposal_id,
                allowed_statuses=PROCESSING_PROPOSAL_STATUSES,
                action="completion",
            )
            updated = repository.complete_model_param_proposal(
                model_param_proposal_id=model_param_proposal_id,
                proposal_parameters=payload,
            )
            _ensure_transition_updated(
                updated,
                model_param_proposal_id=model_param_proposal_id,
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def fail_proposal_result(
        self,
        *,
        model_param_proposal_id: int,
        error_code: str,
        error_message: str,
    ) -> None:
        from apps.common.configs.database.sync_database.connection import get_sync_session

        session = get_sync_session()
        try:
            repository = ModelParameterRepository(session=session)
            proposal = _proposal_for_update(repository, model_param_proposal_id)
            _ensure_proposal_status(
                proposal,
                model_param_proposal_id=model_param_proposal_id,
                allowed_statuses=PROCESSING_PROPOSAL_STATUSES,
                action="failure",
            )
            updated = repository.fail_model_param_proposal(
                model_param_proposal_id=model_param_proposal_id,
                error_code=error_code,
                error_message=error_message,
            )
            _ensure_transition_updated(
                updated,
                model_param_proposal_id=model_param_proposal_id,
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def update_callback_status(
        self,
        *,
        model_param_proposal_id: int,
        callback_status: str,
    ) -> None:
        from apps.common.configs.database.sync_database.connection import get_sync_session

        if callback_status not in CALLBACK_TARGET_STATUSES:
            raise MIBaseError(
                ErrorCode.INVALID_REQUEST,
                detail=f"Unsupported model parameter callback status: {callback_status}",
            )
        session = get_sync_session()
        try:
            repository = ModelParameterRepository(session=session)
            proposal = _proposal_for_update(repository, model_param_proposal_id)
            _ensure_proposal_status(
                proposal,
                model_param_proposal_id=model_param_proposal_id,
                allowed_statuses=CALLBACK_READY_PROPOSAL_STATUSES,
                action="callback status update",
            )
            current_callback_status = str(proposal.get("callback_status") or "")
            if current_callback_status != "PENDING":
                raise MIBaseError(
                    ErrorCode.INVALID_REQUEST,
                    detail=(
                        "Model parameter callback status must be PENDING before update: "
                        f"model_param_proposal_id={model_param_proposal_id}, "
                        f"callback_status={current_callback_status}"
                    ),
                )
            updated = repository.update_model_param_callback_status(
                model_param_proposal_id=model_param_proposal_id,
                callback_status=callback_status,
            )
            _ensure_transition_updated(
                updated,
                model_param_proposal_id=model_param_proposal_id,
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def confirm_proposal_result(
        self,
        *,
        model_param_proposal_id: int,
        user_id: int | None = None,
        confirmation_parameters: list[Any],
    ) -> dict[str, Any]:
        from apps.common.configs.database.sync_database.connection import get_sync_session

        payload = _parameter_json_payload(confirmation_parameters)
        session = get_sync_session()
        try:
            repository = ModelParameterRepository(session=session)
            proposal = _proposal_for_update(repository, model_param_proposal_id)
            _ensure_proposal_status(
                proposal,
                model_param_proposal_id=model_param_proposal_id,
                allowed_statuses=CONFIRMABLE_PROPOSAL_STATUSES,
                action="confirmation",
            )
            updated = repository.confirm_model_param_proposal(
                model_param_proposal_id=model_param_proposal_id,
                user_id=_optional_int(user_id),
                confirmation_parameters=payload,
            )
            _ensure_transition_updated(
                updated,
                model_param_proposal_id=model_param_proposal_id,
            )
            session.commit()
            return {
                "model_param_proposal_id": model_param_proposal_id,
                "status": "CONFIRMED",
            }
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


def _scenario_to_context_dict(scenario: Any) -> dict[str, Any]:
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


def _group_to_context_dict(group: Any) -> dict[str, Any]:
    return {
        "scenario_group_id": int(group.scenario_group_id),
        "mi_event_id": _optional_int(getattr(group, "mi_event_id", None)),
        "event_type_l2_id": _optional_int(
            getattr(group, "event_type_l2_id", None),
        ),
        "request_usr_id": (int(group.request_usr_id) if group.request_usr_id is not None else None),
        "title": group.title,
        "summary": group.summary,
        "description": group.description,
        "dimension_selected": group.dimension_selected or [],
        "scenario_count": int(group.scenario_count or 0),
        "status": _json_safe(group.status),
        "stage": _json_safe(group.stage),
        "api_version": getattr(group, "api_version", None) or "v1",
        "generation_strategy": (getattr(group, "generation_strategy", None) or V1_GENERATION_STRATEGY),
        "parameter_mapping_ready": bool(
            getattr(group, "parameter_mapping_ready", False),
        ),
        "dimension_definitions": _json_safe(
            getattr(group, "dimension_definitions", None) or [],
        ),
    }


def _proposal_event_id(
    *,
    scenario_group: Mapping[str, Any],
    event: Mapping[str, Any],
) -> int | None:
    strategy = str(
        scenario_group.get("generation_strategy") or V1_GENERATION_STRATEGY,
    )
    if strategy == V3_GENERATION_STRATEGY:
        return None
    return _required_int(
        event.get("mi_event_id") or scenario_group.get("mi_event_id"),
        field_name="event.mi_event_id",
    )


def _required_int(value: Any, *, field_name: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise MIBaseError(
            ErrorCode.INVALID_REQUEST,
            detail=f"{field_name} is required for model parameter proposal persistence",
        ) from exc


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
