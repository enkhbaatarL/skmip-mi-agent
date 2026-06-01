from __future__ import annotations

from copy import deepcopy
from typing import Any


def _get_scenarios(state: dict[str, Any]) -> list[dict[str, Any]]:
    s4 = state.get("stage4_scenario_synthesis")
    if not isinstance(s4, dict):
        raise ValueError("Missing stage4_scenario_synthesis object.")
    scenarios = s4.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        raise ValueError("stage4_scenario_synthesis.scenarios must be a non-empty list.")
    return scenarios


def _iter_stage3_third_enum_pairs(state: dict[str, Any]) -> list[tuple[str, str]]:
    s3 = state.get("stage3_value_selection")
    if not isinstance(s3, dict):
        return []
    per_dim = s3.get("per_dimension")
    if not isinstance(per_dim, list):
        return []

    out: list[tuple[str, str]] = []
    for item in per_dim:
        if not isinstance(item, dict):
            continue
        dim_id = str(item.get("dimension_id", "")).strip()
        if not dim_id:
            continue
        enum_full = item.get("template_enum_full")
        selected = item.get("selected_enum")
        candidates = enum_full if isinstance(enum_full, list) and enum_full else selected
        if not isinstance(candidates, list) or len(candidates) < 3:
            continue
        third_enum = str(candidates[2]).strip()
        if not third_enum:
            continue
        out.append((dim_id, third_enum))
    return out


def _build_added_scenario(base_state: dict[str, Any], scenario_idx: int) -> dict[str, Any]:
    dim_pairs = _iter_stage3_third_enum_pairs(base_state)
    if not dim_pairs:
        raise ValueError(
            "Cannot add scenario: each dimension must provide at least 3 enum candidates."
        )
    return {
        "scenario_id": "__HITL_ADDED__",
        "title": f"[HITL 추가] 시나리오 {scenario_idx:02d}",
        "dimension_values": {dim_id: enum_id for dim_id, enum_id in dim_pairs},
        "description": (
            "HITL 단계에서 추가된 시나리오입니다. "
            "각 dimension의 가능한 enum 중 세 번째 값을 조합해 구성했습니다."
        ),
        "derivation_rationale": (
            "HITL 사용자 요청에 따라 stage3_value_selection의 각 dimension에서 "
            "세 번째 enum을 결합해 신규 시나리오를 생성했습니다."
        ),
        "price_direction": {"brent": "neutral", "jkm": "neutral", "ttf": "neutral"},
        "compatibility_passed": True,
    }


def _normalize_scenarios_for_hitl(
    current_state: dict[str, Any],
    human_payload: dict[str, Any],
    *,
    delete_scenario_ids: set[str] | None = None,
    add_scenario: bool = False,
) -> dict[str, Any]:
    payload = deepcopy(human_payload)
    scenarios = _get_scenarios(payload)
    current_ids = {str(s.get("scenario_id", "")).strip() for s in _get_scenarios(current_state)}
    delete_ids = delete_scenario_ids or set()
    unknown_ids = sorted(sid for sid in delete_ids if sid not in current_ids)
    if unknown_ids:
        raise ValueError(f"Unknown scenario_id in delete list: {unknown_ids}")

    kept: list[dict[str, Any]] = []
    for scenario in scenarios:
        sid = str(scenario.get("scenario_id", "")).strip()
        if sid in delete_ids:
            continue
        kept.append(scenario)

    if add_scenario:
        kept.append(_build_added_scenario(current_state, len(kept) + 1))

    if not kept:
        raise ValueError(
            "No scenarios remain after HITL delete/add operations. Keep at least one scenario."
        )

    prior_in: dict[str, Any] = {}
    s5 = payload.get("stage5_validation")
    if isinstance(s5, dict):
        prior = s5.get("likelihood_prior")
        if isinstance(prior, dict):
            prior_in = prior

    prior_out: dict[str, Any] = {}
    for idx, scenario in enumerate(kept, start=1):
        old_id = str(scenario.get("scenario_id", "")).strip()
        new_id = f"S_{idx:02d}"
        scenario["scenario_id"] = new_id
        prior_out[new_id] = prior_in.get(old_id, "medium")

    payload["stage4_scenario_synthesis"]["scenarios"] = kept

    if isinstance(s5, dict):
        s5["likelihood_prior"] = prior_out

    return payload


def validate_human_edit_payload(state: dict[str, Any]) -> None:
    scenarios = _get_scenarios(state)
    seen_ids: set[str] = set()

    for scenario in scenarios:
        sid = str(scenario.get("scenario_id", "")).strip()
        if not sid:
            raise ValueError("Every scenario must have a non-empty scenario_id.")
        if sid in seen_ids:
            raise ValueError(f"Duplicate scenario_id detected: {sid}")
        seen_ids.add(sid)

        dim_values = scenario.get("dimension_values")
        if not isinstance(dim_values, dict) or not dim_values:
            raise ValueError(f"Scenario {sid}: dimension_values must be a non-empty object.")
        for dim_id, enum_id in dim_values.items():
            if not str(dim_id).strip() or not str(enum_id).strip():
                raise ValueError(
                    f"Scenario {sid}: dimension_values keys and values must be non-empty strings."
                )

        # signposts can be omitted in HITL payload and are generated after human edits.
        signposts = scenario.get("signposts")
        if signposts is not None:
            if not isinstance(signposts, list):
                raise ValueError(f"Scenario {sid}: signposts must be a list.")
            for sp in signposts:
                if not isinstance(sp, dict):
                    raise ValueError(f"Scenario {sid}: signpost item must be object.")
                label = str(sp.get("label_ko", "")).strip()
                if not label:
                    raise ValueError(f"Scenario {sid}: signpost label_ko is required.")
                strength = str(sp.get("strength", "")).strip().upper()
                if strength and strength not in {"STRONG", "MEDIUM", "WEAK"}:
                    raise ValueError(
                        f"Scenario {sid}: strength must be one of STRONG/MEDIUM/WEAK."
                    )


def apply_human_edit(
    current_state: dict[str, Any],
    human_payload: dict[str, Any],
    *,
    delete_scenario_ids: set[str] | None = None,
    add_scenario: bool = False,
) -> dict[str, Any]:
    # Human-edited full JSON is the source of truth after validation.
    normalized_payload = _normalize_scenarios_for_hitl(
        current_state,
        human_payload,
        delete_scenario_ids=delete_scenario_ids,
        add_scenario=add_scenario,
    )
    validate_human_edit_payload(normalized_payload)
    return normalized_payload
