"""interpret_price flow 노드.

파이프라인:
  load_input → extract_diffs → interpret_scenarios(LLM) → synthesize_group(LLM) → finalize

여러 입력 feature(기온·전원믹스 등)를 시장(지수)별로 종합해, 시나리오 간 동일 구조로
비교 가능한 해석을 생성한다.
"""

from __future__ import annotations

import asyncio

from apps.agents.interpret_agent.flows.interpret_price.api_schema import (
    GroupSynthesisOut,
    PriceInterpretationMetaOut,
    PriceInterpretationResult,
    ScenarioComparisonOut,
)
from apps.agents.interpret_agent.flows.interpret_price.schema import (
    FeatureSeries,
    InterpretInput,
    PriceSeries,
    ScenarioDiffBundle,
)
from apps.agents.interpret_agent.flows.interpret_price.state import InterpretPriceState
from apps.agents.interpret_agent.persistence.proposal_parameter_service import (
    ProposalParameterService,
)
from apps.agents.interpret_agent.prompts import group_synthesizer as gs_prompt
from apps.agents.interpret_agent.prompts import scenario_interpreter as si_prompt
from apps.agents.interpret_agent.utils.region_index import INDEX_ORDER
from apps.agents.interpret_agent.utils.series_metrics import (
    analyze_feature_diff,
    analyze_price_diff,
)
from apps.common.exceptions.custom import MIBaseError
from apps.common.logging.logger_config import logger
from apps.common.values.enums import ModelPreference
from apps.common.values.error_codes import ErrorCode


def load_input(state: InterpretPriceState) -> dict:
    interpret_input = ProposalParameterService().load_interpret_input(
        scenario_group_id=state.scenario_group_id,
        scenario_ids=state.scenario_ids or None,
    )
    return {"interpret_input": interpret_input}


def _feature_lookup(features: list[FeatureSeries]) -> dict[tuple[str, str, str | None], FeatureSeries]:
    # (feature, region, qualifier) 로 매칭해 multi-feature/부가구분을 구분한다.
    return {(f.feature, f.region, f.qualifier): f for f in features}


def _price_lookup(prices: list[PriceSeries]) -> dict[str, PriceSeries]:
    return {p.index: p for p in prices}


def _collect_data_quality(bundle: ScenarioDiffBundle) -> list[str]:
    signals: list[str] = []
    for fm in bundle.feature_diffs:
        if fm.anomalies:
            signals.append(f"입력 {fm.label}({fm.index or fm.region}) 극단 편차")
    for pm in bundle.price_diffs:
        for a in pm.anomalies:
            if a.kind == "negative_price":
                signals.append(f"예측 가격 음수({pm.index})")
            elif a.kind == "spike":
                signals.append(f"예측 가격 급변({pm.index})")
    return list(dict.fromkeys(signals))


def extract_diffs(state: InterpretPriceState) -> dict:
    inp: InterpretInput | None = state.interpret_input
    if inp is None:
        raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="interpret_input 미로딩")

    base_features = _feature_lookup(inp.scenario_features[inp.base_scenario_id].features)
    base_prices = _price_lookup(inp.scenario_prices[inp.base_scenario_id].prices)

    bundles: dict[str, ScenarioDiffBundle] = {}
    for sid in inp.scenario_ids:
        bundle = ScenarioDiffBundle(scenario_id=sid)

        scen_features = inp.scenario_features.get(sid)
        if scen_features is not None:
            for fs in scen_features.features:
                base_fs = base_features.get((fs.feature, fs.region, fs.qualifier))
                if base_fs is not None:
                    bundle.feature_diffs.append(analyze_feature_diff(fs, base_fs))

        scen_prices = inp.scenario_prices.get(sid)
        if scen_prices is not None:
            ordered = sorted(
                scen_prices.prices,
                key=lambda p: INDEX_ORDER.index(p.index)
                if p.index in INDEX_ORDER
                else len(INDEX_ORDER),
            )
            for ps in ordered:
                base_ps = base_prices.get(ps.index)
                if base_ps is not None:
                    bundle.price_diffs.append(analyze_price_diff(ps, base_ps))

        bundle.flags = _collect_data_quality(bundle)
        bundles[sid] = bundle

    return {"diff_bundles": bundles}


async def _interpret_one(
    sid: str, bundle: ScenarioDiffBundle
) -> ScenarioComparisonOut:
    from apps.connectors.llm.llm_client import invoke_llm_structured_output

    user = si_prompt.build_user_prompt(
        scenario_id=sid,
        feature_metrics=bundle.feature_diffs,
        price_metrics=bundle.price_diffs,
        data_quality=bundle.flags,
    )
    result = await invoke_llm_structured_output(
        output_schema=si_prompt.ScenarioComparisonLLMOutput,
        messages=[
            {"role": "system", "content": si_prompt.SYSTEM_PROMPT},
            {"role": "user", "content": user},
        ],
        preference=ModelPreference.QUALITY,
        temperature=0.0,
    )
    llm = result.result
    return ScenarioComparisonOut(
        scenario_id=sid,
        identity=llm.identity,
        driver_phase=llm.driver_phase,
        price_character=llm.price_character,
        summary=llm.summary,
    )


async def interpret_scenarios(state: InterpretPriceState) -> dict:
    inp = state.interpret_input
    if inp is None:
        raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="interpret_input 미로딩")

    tasks = [
        _interpret_one(sid, state.diff_bundles[sid])
        for sid in inp.scenario_ids
        if sid in state.diff_bundles
    ]
    interpretations = await asyncio.gather(*tasks)
    return {"interpretations": list(interpretations)}


def _scenarios_brief(
    interpretations: list[ScenarioComparisonOut],
    diff_bundles: dict[str, ScenarioDiffBundle],
) -> list[dict]:
    return [
        {
            "scenario_id": it.scenario_id,
            "identity": it.identity,
            "price_character": it.price_character,
            "data_quality_signals": (
                diff_bundles[it.scenario_id].flags
                if it.scenario_id in diff_bundles
                else []
            ),
        }
        for it in interpretations
    ]


async def synthesize_group(state: InterpretPriceState) -> dict:
    from apps.connectors.llm.llm_client import invoke_llm_structured_output

    brief = _scenarios_brief(state.interpretations, state.diff_bundles)
    user = gs_prompt.build_user_prompt(scenarios_brief=brief)

    result = await invoke_llm_structured_output(
        output_schema=gs_prompt.GroupSynthesisLLMOutput,
        messages=[
            {"role": "system", "content": gs_prompt.SYSTEM_PROMPT},
            {"role": "user", "content": user},
        ],
        preference=ModelPreference.QUALITY,
        temperature=0.0,
    )
    return {"synthesis": GroupSynthesisOut(overall_message=result.result.overall_message)}


def finalize(state: InterpretPriceState) -> dict:
    inp = state.interpret_input
    if inp is None:
        raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="interpret_input 미로딩")

    meta = PriceInterpretationMetaOut(
        scenario_group_id=inp.scenario_group_id,
        base_scenario_id=inp.base_scenario_id,
        features=inp.features,
        indices=list(INDEX_ORDER),
        period_start=inp.period_start,
        period_end=inp.period_end,
    )
    result = PriceInterpretationResult(
        meta=meta,
        scenarios=state.interpretations,
        synthesis=state.synthesis or GroupSynthesisOut(),
    )
    logger.info(
        f"[interpret_price] built result | scenarios={len(state.interpretations)} "
        f"| features={inp.features}"
    )
    return {"result": result}
