# Copyright (c) 2026 SK Innovation E&S.

from __future__ import annotations

from collections.abc import Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from itertools import pairwise
import math
import re
from typing import Any
import unicodedata

from apps.agents.model_parameter_agent.utils.lut import (
    BasecaseIndex,
    LutCatalog,
    resolve_effective_reference,
)
from apps.agents.model_parameter_agent.utils.lut.keys import (
    canonical_key_from_axes,
)
from apps.agents.model_parameter_agent.utils.workbook_contract import (
    APPROVED_POWER_MIX_VECTOR_MEMBERS,
)
from apps.common.exceptions.custom import MIBaseError


V4_GENERATION_STRATEGY = "multi_event_model_lever_dimensions"
ABSTAINED_INSUFFICIENT_EVIDENCE = "ABSTAINED_INSUFFICIENT_EVIDENCE"
POWER_MIX_PARAMETER = "PowerMix"
LIQ_UTIL_PARAMETER = "LiqUtilAdjustment"
POWER_MIX_SUM_TOLERANCE = 1e-6
POWER_MIX_ENERGY_SOURCES = APPROVED_POWER_MIX_VECTOR_MEMBERS
_SUPPORTED_LIQ_UTIL_DIRECTIONS = frozenset(
    {
        "increase",
        "decrease",
        "disrupt",
        "disruption",
        "recover",
        "recovery",
    },
)
_SPECIFIC_TIME_PATTERN = re.compile(
    r"(?:(?<!\d)20\d{2}(?!\d)|\bq[1-4]\b|\bh[12]\b|\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|"
    r"may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\b|"
    r"\d+\s*(?:일|주|개월|달|년|days?|weeks?|months?|years?)|\d{1,2}\s*월|"
    r"[1-4]\s*분기|상반기|하반기|올해|내년|다음\s*달|이번\s*달|단기|short[- ]?term|"
    r"\d{4}\s*[-./년]\s*\d{1,2})",
    re.IGNORECASE,
)
_SHORT_TERM_PATTERN = re.compile(r"단기|short[- ]?term", re.IGNORECASE)
_ENTITY_GENERIC_TOKENS = frozenset({"lng", "plant", "terminal"})
_ALIAS_REMOVABLE_TOKENS = _ENTITY_GENERIC_TOKENS | {"export"}
_FACILITY_TYPE_ALIAS_TOKENS = ("lng", "plant", "terminal", "export")
_KOREAN_POSTPOSITION_SUFFIXES = ("와", "과", "은", "는", "이", "가", "을", "를", "의")


@dataclass(frozen=True, slots=True)
class LiqUtilEvidenceDecision:
    allowed: bool
    missing_components: tuple[str, ...]
    user_notes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class LLMEntityResolutionValidation:
    entity_matches: bool
    coordinate_note: str | None = None
    period_evidence: str | None = None
    period_note: str | None = None


@dataclass(frozen=True, slots=True)
class ApprovedCoordinateAliasIndex:
    """Aliases derived from actual model coordinates and accepted only when unique."""

    plant_aliases_by_target: Mapping[str, tuple[str, ...]]
    train_aliases_by_target: Mapping[tuple[str, str], tuple[str, ...]]
    strict_alias_pairs_by_target: Mapping[
        tuple[str, str],
        tuple[tuple[str, str], ...],
    ]


@dataclass(frozen=True, slots=True)
class PowerMixAtomicValidation:
    valid_slot_keys: frozenset[str]
    warnings: tuple[str, ...]


def is_v4_contract_context(scenario_context: Mapping[str, Any] | None) -> bool:
    group = (scenario_context or {}).get("scenario_group") or {}
    return (
        str(group.get("api_version") or "") == "v4"
        and str(group.get("generation_strategy") or "") == V4_GENERATION_STRATEGY
    )


def parameter_name(candidate: Mapping[str, Any]) -> str:
    return str(
        candidate.get("canonical_parameter_name") or candidate.get("parameter_name") or "",
    ).strip()


def slot_coordinates(slot: Mapping[str, Any]) -> dict[str, Any]:
    coordinates: dict[str, Any] = {}
    for raw_axis in slot.get("slot_axes") or []:
        if not isinstance(raw_axis, Mapping):
            continue
        axis_name = str(raw_axis.get("axis_name") or "").strip()
        if not axis_name:
            continue
        value = raw_axis.get("axis_value")
        if axis_name in {"Year", "Month"}:
            with suppress(TypeError, ValueError):
                value = int(float(str(value).strip()))
        coordinates[axis_name] = value
    return coordinates


def _canonical_text(value: object) -> str:
    normalized = unicodedata.normalize("NFKC", str(value or "")).casefold()
    return " ".join(re.sub(r"[^0-9a-z가-힣]+", " ", normalized).split())


def _canonical_entity_text(value: object) -> str:
    normalized = unicodedata.normalize("NFKC", str(value or "")).casefold()
    normalized = re.sub(
        r"(?<=[a-z0-9])(?:와|과|은|는|이|가|을|를|의)(?=\s|$)",
        " ",
        normalized,
    )
    normalized = re.sub(r"(?<!\d)(\d+)\s*단계", r" stage \1 ", normalized)
    normalized = re.sub(r"(?:train|트레인)\s*(\d+)", r" t\1 ", normalized)
    normalized = re.sub(r"(?<![a-z0-9])t\s+(\d+)", r" t\1 ", normalized)
    return " ".join(re.sub(r"[^0-9a-z가-힣~\-–—∼]+", " ", normalized).split())


def _canonical_evidence_text(value: object) -> str:
    normalized = unicodedata.normalize("NFKC", str(value or "")).casefold()
    return " ".join(re.sub(r"[^0-9a-z가-힣~\-–—∼]+", " ", normalized).split())


def _contains_exact_phrase(text: str, phrase: object) -> bool:
    normalized_text = _canonical_entity_text(text)
    normalized_phrase = _canonical_entity_text(phrase)
    if not normalized_phrase:
        return False
    return f" {normalized_phrase} " in f" {normalized_text} "


def _entity_acronym(value: object) -> str:
    words = [
        token
        for token in _canonical_entity_text(value).split()
        if token not in _ENTITY_GENERIC_TOKENS and token not in {"phase", "stage"} and not token.isdigit()
    ]
    return "".join(word[0] for word in words if word and word[0].isalpha())


def _coordinate_axes(value: object) -> Mapping[str, Any]:
    axes = getattr(value, "axes", None)
    if isinstance(axes, Mapping):
        return axes
    if isinstance(value, Mapping):
        nested_axes = value.get("axes")
        if isinstance(nested_axes, Mapping):
            return nested_axes
        return slot_coordinates(value)
    return {}


def _alias_without_generic_tokens(value: object) -> str:
    return " ".join(
        token
        for token in _canonical_entity_text(value).split()
        if token not in _ALIAS_REMOVABLE_TOKENS
    )


def _plant_alias_candidates(plant: str) -> set[str]:
    aliases = {_canonical_entity_text(plant)}
    generic_free = _alias_without_generic_tokens(plant)
    if len(generic_free) >= 4:
        aliases.add(generic_free)
        aliases.update(
            f"{generic_free} {facility_type}"
            for facility_type in _FACILITY_TYPE_ALIAS_TOKENS
        )
    acronym = _entity_acronym(plant)
    if len(acronym) >= 3:
        aliases.add(acronym)
    return {alias for alias in aliases if alias}


def _train_alias_candidates(
    *,
    plant: str,
    train: str,
    implicit_train_number: int | None = None,
) -> tuple[set[str], set[str]]:
    canonical_plant = _canonical_entity_text(plant)
    canonical_train = _canonical_entity_text(train)
    aliases = set() if canonical_train == canonical_plant else {canonical_train}
    generic_free = _alias_without_generic_tokens(train)
    if generic_free and canonical_train != canonical_plant:
        aliases.add(generic_free)
    train_number = _train_number(train) or implicit_train_number
    synthesized_train_aliases: set[str] = set()
    if train_number is not None:
        for plant_alias in _plant_alias_candidates(plant):
            if plant_alias:
                train_alias = f"{plant_alias} t{train_number}"
                aliases.add(train_alias)
                if implicit_train_number is not None:
                    synthesized_train_aliases.add(train_alias)
    return (
        {alias for alias in aliases if alias},
        {alias for alias in synthesized_train_aliases if alias},
    )


def _unique_aliases_by_target(
    aliases_by_target: Mapping[Any, set[str]],
) -> dict[Any, tuple[str, ...]]:
    targets_by_alias: dict[str, set[Any]] = {}
    for target, aliases in aliases_by_target.items():
        for alias in aliases:
            targets_by_alias.setdefault(alias, set()).add(target)
    return {
        target: tuple(
            sorted(
                alias
                for alias in aliases
                if len(targets_by_alias.get(alias, ())) == 1
            ),
        )
        for target, aliases in aliases_by_target.items()
    }


def _phrase_token_spans(text: str, phrase: str) -> tuple[tuple[int, int], ...]:
    text_tokens = _canonical_entity_text(text).split()
    phrase_tokens = _canonical_entity_text(phrase).split()
    if not phrase_tokens or len(phrase_tokens) > len(text_tokens):
        return ()
    width = len(phrase_tokens)
    return tuple(
        (index, index + width)
        for index in range(len(text_tokens) - width + 1)
        if text_tokens[index : index + width] == phrase_tokens
    )


def _contains_distinct_phrase_pair(
    text: str,
    first_phrase: str,
    second_phrase: str,
) -> bool:
    first_spans = _phrase_token_spans(text, first_phrase)
    second_spans = _phrase_token_spans(text, second_phrase)
    return bool(second_spans) and any(
        all(
            first_end <= second_start or second_end <= first_start
            for second_start, second_end in second_spans
        )
        for first_start, first_end in first_spans
    )


def _evidence_phrase_token_spans(
    text: str,
    phrase: str,
) -> tuple[tuple[int, int], ...]:
    text_tokens = _canonical_evidence_text(text).split()
    phrase_tokens = _canonical_evidence_text(phrase).split()
    if not phrase_tokens or len(phrase_tokens) > len(text_tokens):
        return ()
    width = len(phrase_tokens)

    def matches(candidate_tokens: list[str]) -> bool:
        for index, (candidate_token, phrase_token) in enumerate(
            zip(candidate_tokens, phrase_tokens, strict=True),
        ):
            if candidate_token == phrase_token:
                continue
            if index == width - 1 and any(
                candidate_token == f"{phrase_token}{suffix}"
                for suffix in _KOREAN_POSTPOSITION_SUFFIXES
            ):
                continue
            return False
        return True

    return tuple(
        (index, index + width)
        for index in range(len(text_tokens) - width + 1)
        if matches(text_tokens[index : index + width])
    )


def _validated_llm_entity_resolution(
    slot: Mapping[str, Any],
    evidence_text: str,
    *,
    resolution_conflicted: bool = False,
) -> LLMEntityResolutionValidation:
    raw_resolution = slot.get("_llm_entity_coordinate_resolution")
    if not isinstance(raw_resolution, Mapping) or resolution_conflicted:
        return LLMEntityResolutionValidation(entity_matches=False)
    plant_evidence = str(raw_resolution.get("plant_evidence_text") or "").strip()
    train_evidence = str(raw_resolution.get("train_evidence_text") or "").strip()
    note = str(raw_resolution.get("coordinate_match_note_ko") or "").strip()
    if not plant_evidence or not train_evidence or not note:
        return LLMEntityResolutionValidation(entity_matches=False)
    if _canonical_evidence_text(plant_evidence) == _canonical_evidence_text(
        train_evidence,
    ):
        return LLMEntityResolutionValidation(entity_matches=False)
    plant_spans = _evidence_phrase_token_spans(evidence_text, plant_evidence)
    train_spans = _evidence_phrase_token_spans(evidence_text, train_evidence)
    has_distinct_evidence = bool(train_spans) and any(
        all(
            plant_end <= train_start or train_end <= plant_start
            for train_start, train_end in train_spans
        )
        for plant_start, plant_end in plant_spans
    )
    if not has_distinct_evidence:
        return LLMEntityResolutionValidation(entity_matches=False)

    period_evidence = str(raw_resolution.get("period_evidence_text") or "").strip()
    period_note = str(raw_resolution.get("period_match_note_ko") or "").strip()
    period_spans = (
        _evidence_phrase_token_spans(evidence_text, period_evidence)
        if period_evidence and period_note
        else ()
    )
    return LLMEntityResolutionValidation(
        entity_matches=True,
        coordinate_note=note,
        period_evidence=period_evidence if period_spans else None,
        period_note=period_note if period_spans else None,
    )


def build_approved_coordinate_alias_index(
    coordinates: Sequence[object],
) -> ApprovedCoordinateAliasIndex:
    """Build a collision-safe alias dictionary from the loaded model coordinates.

    This is a deterministic fallback after structured LLM entity inference.
    It derives only generic facility-word, stage/train-notation, and unique-acronym
    variants from the supplied exact coordinates; no target-specific dictionary is
    consulted.
    """

    coordinate_pairs: set[tuple[str, str]] = set()
    for coordinate in coordinates:
        axes = _coordinate_axes(coordinate)
        plant = str(axes.get("LNG Plant") or axes.get("Plant") or "").strip()
        train = str(axes.get("LNG Plant Train") or axes.get("Train") or "").strip()
        if plant and train:
            coordinate_pairs.add((plant, train))

    trains_by_plant: dict[str, set[str]] = {}
    for plant, train in coordinate_pairs:
        trains_by_plant.setdefault(plant, set()).add(train)

    plant_aliases: dict[str, set[str]] = {}
    train_aliases: dict[tuple[str, str], set[str]] = {}
    synthesized_train_aliases: dict[tuple[str, str], set[str]] = {}
    for plant, train in sorted(coordinate_pairs):
        plant_aliases.setdefault(plant, set()).update(_plant_alias_candidates(plant))
        implicit_train_number = (
            1
            if len(trains_by_plant[plant]) == 1
            and _canonical_entity_text(plant) == _canonical_entity_text(train)
            and _train_number(train) is None
            else None
        )
        aliases, synthesized = _train_alias_candidates(
            plant=plant,
            train=train,
            implicit_train_number=implicit_train_number,
        )
        train_aliases[(plant, train)] = aliases
        synthesized_train_aliases[(plant, train)] = synthesized

    unique_plant_aliases = _unique_aliases_by_target(plant_aliases)
    unique_train_aliases = _unique_aliases_by_target(train_aliases)
    strict_alias_pairs = {
        target: tuple(
            (plant_alias, train_alias)
            for plant_alias in unique_plant_aliases.get(target[0], ())
            for train_alias in unique_train_aliases.get(target, ())
            if train_alias in synthesized_train_aliases.get(target, set())
        )
        for target in sorted(coordinate_pairs)
        if synthesized_train_aliases.get(target)
    }

    return ApprovedCoordinateAliasIndex(
        plant_aliases_by_target=unique_plant_aliases,
        train_aliases_by_target=unique_train_aliases,
        strict_alias_pairs_by_target=strict_alias_pairs,
    )


def _plant_evidence_match(
    text: str,
    plant: object,
    alias_index: ApprovedCoordinateAliasIndex,
) -> tuple[bool, bool]:
    if _contains_exact_phrase(text, plant):
        literal_plant = _canonical_evidence_text(plant)
        literal_match = f" {literal_plant} " in f" {_canonical_evidence_text(text)} "
        return True, not literal_match
    if any(
        _contains_exact_phrase(text, alias)
        for alias in alias_index.plant_aliases_by_target.get(str(plant), ())
    ):
        return True, True
    return False, False


def _train_number(value: object) -> int | None:
    match = re.search(r"\bt0*(\d+)\b", _canonical_entity_text(value))
    return int(match.group(1)) if match else None


def _train_number_is_explicit(text: str, train_number: int) -> bool:
    text = _canonical_entity_text(text)
    if re.search(rf"\b(?:t|train)\s*0*{train_number}\b", text):
        return True
    if re.search(rf"(?<!\d)0*{train_number}\s*호기", text):
        return True
    for raw_start, raw_end in re.findall(
        r"(?<!\d)(\d+)\s*(?:~|-|–|—|∼|부터)\s*(\d+)\s*호기",
        text,
    ):
        start, end = int(raw_start), int(raw_end)
        if start <= train_number <= end:
            return True
    return False


def _train_evidence_match(
    text: str,
    *,
    plant: object,
    train: object,
    alias_index: ApprovedCoordinateAliasIndex,
) -> tuple[bool, bool]:
    plant_matches, _ = _plant_evidence_match(text, plant, alias_index)
    if not plant_matches:
        return False, False
    if _contains_exact_phrase(text, train):
        literal_train = _canonical_evidence_text(train)
        literal_match = f" {literal_train} " in f" {_canonical_evidence_text(text)} "
        return True, not literal_match
    if any(
        _contains_exact_phrase(text, alias)
        for alias in alias_index.train_aliases_by_target.get(
            (str(plant), str(train)),
            (),
        )
    ):
        return True, True
    train_number = _train_number(train)
    if train_number is None:
        return False, False
    if _train_number_is_explicit(text, train_number):
        return True, True
    return False, False


def _json_text(value: object) -> str:
    parts: list[str] = []

    def visit(item: object) -> None:
        if isinstance(item, Mapping):
            for key, nested in item.items():
                if str(key) in {"embedding", "vector"}:
                    continue
                visit(nested)
            return
        if isinstance(item, Sequence) and not isinstance(item, str | bytes | bytearray):
            for nested in item:
                visit(nested)
            return
        if item is not None:
            text = _canonical_evidence_text(item)
            if text:
                parts.append(text)

    visit(value)
    return " ".join(parts)


def _event_id(event: Mapping[str, Any]) -> int | None:
    raw_event_id = event.get("mi_event_id") or event.get("event_id") or event.get("eventId")
    try:
        return int(raw_event_id) if raw_event_id is not None else None
    except (TypeError, ValueError):
        return None


def _provenance_items(candidate: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [item for item in candidate.get("lever_provenance") or [] if isinstance(item, Mapping)]


def _matching_source_dimensions(
    candidate: Mapping[str, Any],
    provenance: Mapping[str, Any],
) -> list[Mapping[str, Any]]:
    dimension_key = str(provenance.get("scenario_dimension_key") or "").strip()
    dimensions = [item for item in candidate.get("source_dimensions") or [] if isinstance(item, Mapping)]
    if not dimension_key:
        return []
    return [
        item
        for item in dimensions
        if str(
            item.get("scenario_dimension_key") or item.get("dimension_key") or item.get("source_dimension_id") or "",
        ).strip()
        == dimension_key
    ]


def _source_event_ids(provenance: Mapping[str, Any]) -> set[int]:
    event_ids: set[int] = set()
    for raw_event_id in provenance.get("source_event_ids") or []:
        try:
            event_ids.add(int(raw_event_id))
        except (TypeError, ValueError):
            continue
    return event_ids


def evaluate_liq_util_evidence(
    candidate: Mapping[str, Any],
    slot: Mapping[str, Any],
    scenario_context: Mapping[str, Any],
    *,
    exact_candidate_count: int | None = None,
    coordinate_alias_index: ApprovedCoordinateAliasIndex | None = None,
    llm_resolution_conflicted: bool = False,
) -> LiqUtilEvidenceDecision:
    """Require one coherent v4 Lever lineage item to ground an exact facility slot.

    ``exact_candidate_count`` is retained for caller compatibility only.  A
    single candidate no longer bypasses explicit Plant, Train, and period
    evidence because that shortcut could expand a parent facility mention into
    unsupported slots.
    """

    coordinates = slot_coordinates(slot)
    plant = coordinates.get("LNG Plant") or coordinates.get("Plant")
    train = coordinates.get("LNG Plant Train") or coordinates.get("Train")
    alias_index = coordinate_alias_index or build_approved_coordinate_alias_index(
        [slot],
    )
    events = [item for item in scenario_context.get("events") or [] if isinstance(item, Mapping)]
    events_by_id = {event_id: event for event in events if (event_id := _event_id(event)) is not None}

    observed_missing: set[str] = set()
    for provenance in _provenance_items(candidate):
        missing: set[str] = set()
        if not str(provenance.get("scenario_dimension_key") or "").strip():
            missing.add("scenario_dimension_lineage")
        if str(provenance.get("lever_code") or "").strip() != "liquefaction_utilization":
            missing.add("direct_operational_lever")
        direction = str(provenance.get("direction") or "").strip().casefold()
        if direction not in _SUPPORTED_LIQ_UTIL_DIRECTIONS:
            missing.add("direction")

        source_event_ids = _source_event_ids(provenance)
        linked_events = [events_by_id[event_id] for event_id in sorted(source_event_ids) if event_id in events_by_id]
        if not source_event_ids or not linked_events:
            missing.add("source_event")

        evidence_text = _json_text(
            {
                "scope": provenance.get("scope"),
                "source_dimensions": _matching_source_dimensions(candidate, provenance),
                "events": linked_events,
                "scenario": scenario_context.get("scenario"),
                "scenario_group": scenario_context.get("scenario_group"),
            },
        )
        resolution = _validated_llm_entity_resolution(
            slot,
            evidence_text,
            resolution_conflicted=llm_resolution_conflicted,
        )
        time_window = str(provenance.get("time_window") or "").strip()
        lineage_time_matches = time_evidence_matches_slot(
            time_window,
            year=coordinates.get("Year"),
            month=coordinates.get("Month"),
        )
        llm_period_matches = bool(resolution.period_evidence) and time_evidence_matches_slot(
            resolution.period_evidence,
            year=coordinates.get("Year"),
            month=coordinates.get("Month"),
        )
        requires_slot_period_evidence = (exact_candidate_count or 0) > 1
        time_matches = lineage_time_matches or llm_period_matches
        if not time_matches:
            missing.add("specific_time_window")
            if requires_slot_period_evidence:
                missing.add("slot_specific_period_evidence")

        user_notes: list[str] = []
        if not plant or not train:
            missing.add("exact_facility_slot")
        else:
            plant_matches, plant_uses_alias = _plant_evidence_match(
                evidence_text,
                plant,
                alias_index,
            )
            train_matches, train_uses_alias = _train_evidence_match(
                evidence_text,
                plant=plant,
                train=train,
                alias_index=alias_index,
            )
            strict_pairs = alias_index.strict_alias_pairs_by_target.get(
                (str(plant), str(train)),
                (),
            )
            strict_alias_pair_matches = (
                not (plant_uses_alias or train_uses_alias)
                or not strict_pairs
                or any(
                    _contains_distinct_phrase_pair(
                        evidence_text,
                        plant_alias,
                        train_alias,
                    )
                    for plant_alias, train_alias in strict_pairs
                )
            )
            deterministic_matches = (
                plant_matches and train_matches and strict_alias_pair_matches
            )
            if not (resolution.entity_matches or deterministic_matches):
                missing.add("specific_facility_evidence")
            elif resolution.entity_matches:
                user_notes.append(
                    "근거 원문의 Plant·Train 문구를 LLM이 실제 Basecase 좌표 "
                    f"'{plant} / {train}'와 같은 실체로 해석했습니다. "
                    f"원문 존재·서로 다른 근거 span·exact target을 서버가 검증했습니다: "
                    f"{resolution.coordinate_note}",
                )
            elif plant_uses_alias or train_uses_alias:
                user_notes.append(
                    "근거의 공통어·단계·호기 표기를 실제 Basecase 좌표에서 "
                    f"유일하게 승인된 영문 설비 '{plant}'의 Train 좌표로 정규화해 연결했습니다.",
                )
        if llm_period_matches:
            user_notes.append(
                "근거 원문의 기간 문구를 exact Year/Month 좌표와 대조해 검증했습니다: "
                f"{resolution.period_note}",
            )
        if time_matches and _SHORT_TERM_PATTERN.search(time_window):
            user_notes.append(
                "'단기' 기간은 분석 기준일이 속한 월의 단일 모델 slot으로 보수적으로 해석했습니다.",
            )

        if not missing:
            return LiqUtilEvidenceDecision(
                allowed=True,
                missing_components=(),
                user_notes=tuple(user_notes),
            )
        observed_missing.update(missing)

    return LiqUtilEvidenceDecision(
        allowed=False,
        missing_components=tuple(sorted(observed_missing or {"lever_provenance"})),
        user_notes=(),
    )


def has_specific_time_evidence(value: object) -> bool:
    return _SPECIFIC_TIME_PATTERN.search(str(value or "").strip()) is not None


def _has_invalid_absolute_time_syntax(normalized: str) -> bool:  # noqa: C901
    for raw_month in re.findall(r"(?<!\d)(\d+)\s*월", normalized):
        if not 1 <= int(raw_month) <= 12:
            return True
    for match in re.finditer(
        r"(?<!\d)20\d{2}\s*[./]\s*(\d+)(?!\d)",
        normalized,
    ):
        if not 1 <= int(match.group(1)) <= 12:
            return True
    for match in re.finditer(
        r"(?<!\d)20\d{2}\s*-\s*(\d+)(?!\d)",
        normalized,
    ):
        suffix = match.group(1)
        if len(suffix) == 4 and suffix.startswith("20"):
            continue
        if not 1 <= int(suffix) <= 12:
            return True
    for match in re.finditer(
        r"(?<!\d)20\d{2}\s*년\s*(\d+)\s*월",
        normalized,
    ):
        if not 1 <= int(match.group(1)) <= 12:
            return True
    for period_type, raw_number in re.findall(r"\b([qh])(\d+)\b", normalized):
        limit = 4 if period_type == "q" else 2
        if not 1 <= int(raw_number) <= limit:
            return True
    for raw_quarter in re.findall(r"(?<!\d)(\d+)\s*분기", normalized):
        if not 1 <= int(raw_quarter) <= 4:
            return True
    for start, end in re.findall(
        r"(?<!\d)(20\d{2})\s*[-~\u2013\u2014]\s*(20\d{2})(?!\d)",
        normalized,
    ):
        if int(start) > int(end):
            return True
    if re.search(r"[-+\u2212]\s*\d+(?:\.\d+)?\s*(?:개월|months?)", normalized):
        return True
    return re.search(r"\d+\.\d+\s*(?:개월|months?)", normalized) is not None


def _relative_period_months(normalized: str) -> frozenset[int]:
    months: set[int] = set()
    for raw_quarter in re.findall(r"\bq([1-4])\b", normalized):
        first_month = (int(raw_quarter) - 1) * 3 + 1
        months.update(range(first_month, first_month + 3))
    for raw_half in re.findall(r"\bh([12])\b", normalized):
        first_month = 1 if raw_half == "1" else 7
        months.update(range(first_month, first_month + 6))
    for raw_quarter in re.findall(r"(?<!\d)([1-4])\s*분기", normalized):
        first_month = (int(raw_quarter) - 1) * 3 + 1
        months.update(range(first_month, first_month + 3))
    if "상반기" in normalized:
        months.update(range(1, 7))
    if "하반기" in normalized:
        months.update(range(7, 13))
    return frozenset(months)


def time_evidence_matches_slot(  # noqa: C901
    value: object,
    *,
    year: object,
    month: object,
    anchor_year: int | None = None,
    anchor_month: int | None = None,
) -> bool:
    """Reject an explicit absolute period that does not cover the exact slot.

    Relative periods such as ``내년`` or ``6개월`` remain usable when the
    lineage does not carry a resolvable calendar anchor.  Whenever a calendar
    year, month, quarter, or half-year is explicit, it must include the slot.
    """

    text = str(value or "").strip()
    if not has_specific_time_evidence(text):
        return False
    try:
        slot_year = int(year)
        slot_month = int(month)
    except (TypeError, ValueError):
        return False

    normalized = unicodedata.normalize("NFKC", text).casefold()
    if _has_invalid_absolute_time_syntax(normalized):
        return False
    english_months = {
        1: r"\bjan(?:uary)?\b",
        2: r"\bfeb(?:ruary)?\b",
        3: r"\bmar(?:ch)?\b",
        4: r"\bapr(?:il)?\b",
        5: r"\bmay\b",
        6: r"\bjun(?:e)?\b",
        7: r"\bjul(?:y)?\b",
        8: r"\baug(?:ust)?\b",
        9: r"\bsep(?:tember)?\b",
        10: r"\boct(?:ober)?\b",
        11: r"\bnov(?:ember)?\b",
        12: r"\bdec(?:ember)?\b",
    }
    calendar_tokens: list[tuple[int, int, int, int]] = []

    def add_calendar_token(
        match: re.Match[str],
        token_year: int,
        first_month: int,
        last_month: int,
    ) -> None:
        calendar_tokens.append(
            (
                match.start(),
                match.end(),
                token_year * 12 + first_month - 1,
                token_year * 12 + last_month - 1,
            ),
        )

    numeric_month_patterns = (
        r"(?<!\d)(20\d{2})\s*[-./]\s*(1[0-2]|0?[1-9])(?!\d)",
        r"(?<!\d)(20\d{2})\s*년\s*(1[0-2]|0?[1-9])\s*월(?!\d)",
    )
    for pattern in numeric_month_patterns:
        for match in re.finditer(pattern, normalized):
            add_calendar_token(match, int(match.group(1)), int(match.group(2)), int(match.group(2)))

    for match in re.finditer(
        r"(?:(?<!\d)(20\d{2})\s*년?\s*[- ]?\s*([qh][1-4])\b|"
        r"\b([qh][1-4])\s*[- ]?\s*(20\d{2})\s*년?(?!\d))",
        normalized,
    ):
        token_year = int(match.group(1) or match.group(4))
        period = str(match.group(2) or match.group(3))
        period_number = int(period[1])
        if period.startswith("q"):
            first_month = (period_number - 1) * 3 + 1
            last_month = first_month + 2
        elif period_number <= 2:
            first_month = 1 if period_number == 1 else 7
            last_month = 6 if period_number == 1 else 12
        else:
            continue
        add_calendar_token(match, token_year, first_month, last_month)

    for match in re.finditer(
        r"(?<!\d)(20\d{2})\s*년?\s*(상반기|하반기)",
        normalized,
    ):
        first_month = 1 if match.group(2) == "상반기" else 7
        add_calendar_token(match, int(match.group(1)), first_month, first_month + 5)

    for match in re.finditer(
        r"(?<!\d)(20\d{2})\s*년?\s*([1-4])\s*분기",
        normalized,
    ):
        first_month = (int(match.group(2)) - 1) * 3 + 1
        add_calendar_token(match, int(match.group(1)), first_month, first_month + 2)

    month_pattern = (
        r"jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
        r"jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?"
    )
    for match in re.finditer(
        rf"(?:(?<!\d)(20\d{{2}})\s+({month_pattern})\b|\b({month_pattern})\s+(20\d{{2}})(?!\d))",
        normalized,
    ):
        token_year = int(match.group(1) or match.group(4))
        month_text = str(match.group(2) or match.group(3))
        token_month = next(
            month_number for month_number, pattern in english_months.items() if re.fullmatch(pattern, month_text)
        )
        add_calendar_token(match, token_year, token_month, token_month)

    if calendar_tokens:
        tokens = sorted(set(calendar_tokens))
        covered_intervals: list[tuple[int, int]] = []
        consumed: set[int] = set()
        for index, (left, right) in enumerate(pairwise(tokens)):
            separator = normalized[left[1] : right[0]]
            if re.fullmatch(r"\s*(?:[-~\u2013\u2014]|to|부터)\s*", separator) is None:
                continue
            consumed.update((index, index + 1))
            if left[2] <= right[3]:
                covered_intervals.append((left[2], right[3]))
        covered_intervals.extend((token[2], token[3]) for index, token in enumerate(tokens) if index not in consumed)
        slot_ordinal = slot_year * 12 + slot_month - 1
        return any(start <= slot_ordinal <= end for start, end in covered_intervals)

    explicit_years = {int(item) for item in re.findall(r"(?<!\d)(20\d{2})(?!\d)", normalized)}
    for start, end in re.findall(
        r"(?<!\d)(20\d{2})\s*[-~\u2013\u2014]\s*(20\d{2})(?!\d)",
        normalized,
    ):
        start_year = int(start)
        end_year = int(end)
        if start_year <= end_year:
            explicit_years.update(range(start_year, end_year + 1))
    if explicit_years:
        return slot_year in explicit_years

    allowed_months = {
        int(item)
        for item in re.findall(
            r"(?<!\d)(1[0-2]|0?[1-9])\s*월",
            normalized,
        )
    }
    allowed_months.update(
        candidate_month for candidate_month, pattern in english_months.items() if re.search(pattern, normalized)
    )
    relative_period_months = _relative_period_months(normalized)

    today = datetime.now(UTC).astimezone().date()
    resolved_anchor_year = anchor_year if anchor_year is not None else today.year
    resolved_anchor_month = anchor_month if anchor_month is not None else today.month
    if not 1 <= resolved_anchor_month <= 12:
        return False
    if "이번 달" in normalized or "이번달" in normalized:
        return (slot_year, slot_month) == (resolved_anchor_year, resolved_anchor_month)
    if "다음 달" in normalized or "다음달" in normalized:
        next_month_index = resolved_anchor_year * 12 + resolved_anchor_month
        next_year, next_month_zero_based = divmod(next_month_index, 12)
        return (slot_year, slot_month) == (
            next_year,
            next_month_zero_based + 1,
        )
    if "내년" in normalized:
        return (
            slot_year == resolved_anchor_year + 1
            and (not allowed_months or slot_month in allowed_months)
            and (not relative_period_months or slot_month in relative_period_months)
        )
    if "올해" in normalized:
        return (
            slot_year == resolved_anchor_year
            and (not allowed_months or slot_month in allowed_months)
            and (not relative_period_months or slot_month in relative_period_months)
        )

    if _SHORT_TERM_PATTERN.search(normalized):
        return (slot_year, slot_month) == (resolved_anchor_year, resolved_anchor_month)

    duration_match = re.search(
        r"(?<!\d)(\d+)\s*(?:개월|months?)(?![a-z])",
        normalized,
    )
    if duration_match:
        duration_months = int(duration_match.group(1))
        month_offset = (slot_year - resolved_anchor_year) * 12 + (slot_month - resolved_anchor_month)
        return duration_months > 0 and 0 <= month_offset < duration_months

    if re.search(r"\bq[1-4]\b|\bh[12]\b|[1-4]\s*분기|상반기|하반기", normalized):
        return False
    if allowed_months:
        return any(
            (slot_year, slot_month)
            == (
                resolved_anchor_year if candidate_month >= resolved_anchor_month else resolved_anchor_year + 1,
                candidate_month,
            )
            for candidate_month in allowed_months
        )
    return False


def _power_mix_group(axes: Mapping[str, Any]) -> tuple[str, int] | None:
    country = str(axes.get("Country") or "").strip()
    raw_year = axes.get("Year")
    try:
        year = int(raw_year)
    except (TypeError, ValueError):
        return None
    return (country, year) if country else None


def _validated_power_mix_seed_group(
    slot: Mapping[str, Any],
    candidate_key: str,
    basecase_index: BasecaseIndex,
) -> tuple[str, int] | None:
    """Validate the unmodified Step2 seed before replacing it with an atomic vector."""

    expected_axes = basecase_index.candidate_key_axes.get(candidate_key)
    if expected_axes != ("Country", "Year", "Energy Source"):
        return None
    raw_axes = slot.get("slot_axes")
    if not isinstance(raw_axes, Sequence) or isinstance(raw_axes, str | bytes | bytearray):
        return None

    coordinates: dict[str, Any] = {}
    axis_names: list[str] = []
    for raw_axis in raw_axes:
        if not isinstance(raw_axis, Mapping):
            return None
        axis_name = str(raw_axis.get("axis_name") or "").strip()
        if not axis_name or axis_name in coordinates:
            return None
        axis_names.append(axis_name)
        coordinates[axis_name] = raw_axis.get("axis_value")
    if len(axis_names) != len(expected_axes) or set(axis_names) != set(expected_axes):
        return None

    try:
        country, year, source = canonical_key_from_axes(coordinates, expected_axes)
    except MIBaseError:
        return None
    if (
        not isinstance(country, str)
        or not country.strip()
        or not isinstance(year, int)
        or source not in POWER_MIX_ENERGY_SOURCES
    ):
        return None
    return country, year


def expand_power_mix_atomic_slots(
    slots: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    basecase_index: BasecaseIndex,
    lut_catalog: LutCatalog | None,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Expand each selected PowerMix Country/Year member to its complete source vector."""

    candidate_by_key = {str(candidate.get("candidate_key") or ""): candidate for candidate in candidates}
    expanded: list[dict[str, Any]] = []
    warnings: list[str] = []
    emitted_groups: set[tuple[str, str, int]] = set()

    for raw_slot in slots:
        candidate_key = str(raw_slot.get("candidate_key") or "")
        candidate = candidate_by_key.get(candidate_key) or {}
        if parameter_name(candidate) != POWER_MIX_PARAMETER:
            expanded.append(dict(raw_slot))
            continue

        group = _validated_power_mix_seed_group(
            raw_slot,
            candidate_key,
            basecase_index,
        )
        if group is None:
            warnings.append(
                "PowerMix Step2 seed의 axis schema/value가 canonical exact key를 충족하지 않아 "
                f"제외했습니다: candidate={candidate_key}",
            )
            continue
        country, year = group
        emitted_key = (candidate_key, country, year)
        if emitted_key in emitted_groups:
            continue
        emitted_groups.add(emitted_key)

        expected_sources = set(POWER_MIX_ENERGY_SOURCES)

        group_slots: list[dict[str, Any]] = []
        group_values: list[float] = []
        for source in POWER_MIX_ENERGY_SOURCES:
            axes = {"Country": country, "Year": year, "Energy Source": source}
            reference = resolve_effective_reference(
                candidate_key,
                axes,
                basecase_index,
                lut_catalog,
            )
            if reference is None:
                break
            value = float(reference.llm_reference_value)
            if not math.isfinite(value) or not 0 <= value <= 1:
                break
            group_values.append(value)
            group_slot = dict(raw_slot)
            group_slot["slot_axes"] = [
                {"axis_name": axis_name, "axis_value": axes[axis_name]}
                for axis_name in ("Country", "Year", "Energy Source")
            ]
            group_slot["_atomic_group_key"] = f"{candidate_key}|PowerMix|{country}|{year}"
            group_slot["_atomic_group_size"] = len(expected_sources)
            group_slots.append(group_slot)

        if len(group_slots) != len(expected_sources) or not math.isclose(
            math.fsum(group_values),
            1.0,
            rel_tol=0.0,
            abs_tol=1e-6,
        ):
            warnings.append(
                "PowerMix effective reference vector가 exact-key/범위 제약을 충족하지 않아 atomic group 전체를 "
                f"제외했습니다: candidate={candidate_key}, Country={country}, Year={year}",
            )
            continue
        expanded.extend(group_slots)

    return expanded, warnings


def validate_power_mix_atomic_values(
    expected_contexts: Mapping[str, Mapping[str, Any]],
    proposed_values: Mapping[str, float],
    *,
    invalid_slot_keys: set[str] | None = None,
) -> PowerMixAtomicValidation:
    """Validate complete Step3 vectors and return only keys from valid Country/Year groups."""

    invalid_keys = invalid_slot_keys or set()
    groups: dict[tuple[str, int], list[tuple[str, str]]] = {}
    malformed_slots: set[str] = set()
    for slot_key, context in expected_contexts.items():
        reference = context.get("reference") or {}
        axes = reference.get("axes") or {}
        group = _power_mix_group(axes)
        source = str(axes.get("Energy Source") or "").strip()
        if group is None or not source:
            malformed_slots.add(slot_key)
            continue
        groups.setdefault(group, []).append((slot_key, source))

    valid_slot_keys: set[str] = set()
    warnings: list[str] = []
    expected_sources = set(POWER_MIX_ENERGY_SOURCES)
    for (country, year), members in sorted(groups.items()):
        member_keys = {slot_key for slot_key, _ in members}
        member_sources = {source for _, source in members}
        values = [proposed_values[slot_key] for slot_key in member_keys if slot_key in proposed_values]
        valid = (
            len(members) == len(member_keys) == len(expected_sources)
            and member_sources == expected_sources
            and not (member_keys & invalid_keys)
            and member_keys <= set(proposed_values)
            and all(math.isfinite(value) and 0 <= value <= 1 for value in values)
            and math.isclose(
                math.fsum(values),
                1.0,
                rel_tol=0.0,
                abs_tol=POWER_MIX_SUM_TOLERANCE,
            )
        )
        if valid:
            valid_slot_keys.update(member_keys)
            continue
        warnings.append(
            "PowerMix Step3 응답이 full-vector 범위/합계 제약을 충족하지 않아 atomic group 전체를 "
            f"제외했습니다: Country={country}, Year={year}",
        )

    if malformed_slots:
        warnings.append(
            f"PowerMix Step3 atomic group 좌표가 불완전해 관련 slot을 제외했습니다: slotKeys={sorted(malformed_slots)}",
        )
    return PowerMixAtomicValidation(
        valid_slot_keys=frozenset(valid_slot_keys),
        warnings=tuple(warnings),
    )
