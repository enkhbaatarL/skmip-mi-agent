from __future__ import annotations  # noqa: CPY001

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import re


# 정규화한 제목의 문자 2-gram Jaccard 유사도가 이 값 이상이면 제목이 비슷한 쌍으로 본다.
SIMILAR_TITLE_THRESHOLD = 0.6

_TITLE_NOISE_PATTERN = re.compile(r"[\s\W_]+", re.UNICODE)


@dataclass(frozen=True, slots=True)
class ScenarioSimilarityInput:
    title: str
    pressure_band: str
    dimension_values: Mapping[str, str]


def _title_bigrams(title: str) -> set[str]:
    normalized = _TITLE_NOISE_PATTERN.sub("", title).lower()
    if len(normalized) < 2:
        return {normalized} if normalized else set()
    return {normalized[index : index + 2] for index in range(len(normalized) - 1)}


def title_similarity(left: str, right: str) -> float:
    left_bigrams = _title_bigrams(left)
    right_bigrams = _title_bigrams(right)
    if not left_bigrams or not right_bigrams:
        return 0.0
    return len(left_bigrams & right_bigrams) / len(left_bigrams | right_bigrams)


def find_similar_scenario_pairs(
    scenarios: Sequence[ScenarioSimilarityInput],
    *,
    title_threshold: float = SIMILAR_TITLE_THRESHOLD,
) -> list[dict[str, object]]:
    """같은 band이면서 Dimension 값이 1개만 다르거나 제목이 거의 같은 Scenario 쌍을 찾는다.

    결과는 비슷한 Scenario가 얼마나 생성되는지 보기 위한 통계이며 생성 결과를 바꾸지 않는다.
    """
    pairs: list[dict[str, object]] = []
    for left_index, left in enumerate(scenarios):
        for right in scenarios[left_index + 1 :]:
            dimension_ids = sorted(set(left.dimension_values) | set(right.dimension_values))
            differing = [
                dimension_id
                for dimension_id in dimension_ids
                if left.dimension_values.get(dimension_id) != right.dimension_values.get(dimension_id)
            ]
            similarity = round(title_similarity(left.title, right.title), 2)
            kinds: list[str] = []
            if left.pressure_band == right.pressure_band and len(differing) == 1:
                kinds.append("same_band_one_dimension")
            if similarity >= title_threshold:
                kinds.append("similar_title")
            if not kinds:
                continue
            pairs.append(
                {
                    "scenario_titles": [left.title, right.title],
                    "kinds": kinds,
                    "pressure_bands": [left.pressure_band, right.pressure_band],
                    "differing_dimension_ids": differing,
                    "title_similarity": similarity,
                }
            )
    return pairs


__all__ = [
    "SIMILAR_TITLE_THRESHOLD",
    "ScenarioSimilarityInput",
    "find_similar_scenario_pairs",
    "title_similarity",
]
