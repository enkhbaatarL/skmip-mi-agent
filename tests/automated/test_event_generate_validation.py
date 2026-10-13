# ruff: noqa: PT009

from __future__ import annotations

from datetime import date
import os
from typing import Any
import unittest
from unittest.mock import patch


os.environ.setdefault("METADATA_DB_PORT", "3306")

from apps.agents.event_generate_agent.flows.generate_from_query.nodes import (
    fact_timeline as fact_timeline_node,
    generate as generate_node,
    persist,
    validate_claims as validate_claims_node,
)
from apps.agents.event_generate_agent.flows.generate_from_query.nodes.summarize import _to_brief
from apps.agents.event_generate_agent.flows.generate_from_query.routing import (
    NODE_DRAFT_EVENTS,
    NODE_PERSIST_EVENTS,
    route_after_validation,
)
from apps.agents.event_generate_agent.flows.generate_from_query.schema import (
    AssetStatus,
    EvidencedFact,
    EvidenceItem,
    EvidenceOrigin,
    ExistingEventHit,
    FactKind,
    FactTimeline,
    QueryPlan,
    SearchTopic,
    TemporalStatus,
    TopicBrief,
    WebDocument,
)
from apps.agents.event_generate_agent.flows.generate_from_query.state import GenerateFromQueryState
from apps.agents.event_generate_agent.flows.generate_from_query.tools.claim_rules import (
    apply_claim_rules,
)
from apps.agents.event_generate_agent.flows.generate_from_query.tools.evidence import (
    event_hits_to_evidences,
    web_documents_to_evidences,
)
from apps.agents.event_generate_agent.flows.generate_from_query.tools.temporal import (
    build_timeline,
    evaluate_fact,
    parse_period,
)
from apps.agents.event_generate_agent.prompts import (
    claim_verification as verify_prompt,
    topic_brief as brief_prompt,
)
from apps.agents.event_generate_agent.schemas.api.event import GeneratedEventOut
from apps.agents.event_generate_agent.schemas.domain import (
    ClaimType,
    EventClaim,
    EventDraft,
    EventTypeAssignment,
    EventValidation,
    FeasibilityStatus,
    InferencePlausibility,
    IssueSeverity,
    ScenarioSeverity,
    SupportStatus,
)
from apps.connectors.llm.llm_client import LLMStructuredResult


TARGET = date(2027, 1, 1)


def _fact(fact_id: str, **kwargs: Any) -> EvidencedFact:  # noqa: ANN401
    return EvidencedFact(fact_id=fact_id, statement=kwargs.pop("statement", fact_id), evidence_keys=["T1-W1"], **kwargs)


def _claim(claim_id: str, claim_type: ClaimType, **kwargs: Any) -> EventClaim:  # noqa: ANN401
    return EventClaim(claim_id=claim_id, text=kwargs.pop("text", claim_id), claim_type=claim_type, **kwargs)


def _draft(claims: list[EventClaim], severity: ScenarioSeverity | None = ScenarioSeverity.BASE) -> EventDraft:
    return EventDraft(event_title_ko="테스트 이벤트", claims=claims, scenario_severity=severity)


def _codes(validation: EventValidation, severity: IssueSeverity) -> list[str]:
    return [issue.code for issue in validation.issues if issue.severity is severity]


class TemporalTests(unittest.TestCase):
    def test_parse_period_precision(self) -> None:
        self.assertEqual(parse_period("2028"), (date(2028, 1, 1), date(2028, 12, 31)))
        self.assertEqual(parse_period("2027-02"), (date(2027, 2, 1), date(2027, 2, 28)))
        self.assertEqual(parse_period("2026년 3월 5일"), (date(2026, 3, 5), date(2026, 3, 5)))
        self.assertIsNone(parse_period("미정"))

    def test_project_starting_after_target_is_not_yet(self) -> None:
        nfs = _fact("T1-F1", fact_kind=FactKind.PLAN, entity="NFS", asset_status=AssetStatus.PLANNED, valid_from="2028")
        self.assertIs(evaluate_fact(nfs, TARGET).status, TemporalStatus.NOT_YET)

    def test_project_with_first_lng_before_target_is_active(self) -> None:
        golden_pass = _fact(
            "T1-F2",
            fact_kind=FactKind.ACTUAL,
            entity="Golden Pass Train 1",
            asset_status=AssetStatus.OPERATING,
            valid_from="2026-03",
        )
        self.assertIs(evaluate_fact(golden_pass, TARGET).status, TemporalStatus.ACTIVE)

    def test_outage_with_recovery_after_target_is_still_active(self) -> None:
        ras_laffan = _fact(
            "T1-F3",
            fact_kind=FactKind.FORECAST,
            entity="Ras Laffan",
            asset_status=AssetStatus.OUTAGE,
            valid_from="2026-04",
            valid_to="2029",
        )
        self.assertIs(evaluate_fact(ras_laffan, TARGET).status, TemporalStatus.ACTIVE)

    def test_past_outage_without_end_is_stale_not_active(self) -> None:
        outage = _fact(
            "T1-F8",
            fact_kind=FactKind.STATUS,
            entity="Ras Laffan Train 4",
            asset_status=AssetStatus.OUTAGE,
            as_of="2026-09",
            valid_from="2026-04",
        )
        status_only = _fact(
            "T1-F9",
            fact_kind=FactKind.STATUS,
            entity="Ras Laffan",
            asset_status=AssetStatus.OUTAGE,
            as_of="2026-09",
        )
        situation = _fact("T1-F10", fact_kind=FactKind.STATUS, entity="호르무즈", as_of="2026-08-20")
        for fact in (outage, status_only, situation):
            self.assertIs(evaluate_fact(fact, TARGET).status, TemporalStatus.STALE, fact.fact_id)
        # 기준일이 관측 시점 안이면 그 상태는 확인된 것이다.
        self.assertIs(evaluate_fact(outage, date(2026, 9, 15)).status, TemporalStatus.ACTIVE)

    def test_past_one_off_event_is_past_event_not_active(self) -> None:
        # 2021-01 JKM 사상 최고치 같은 일회성 실적은 시작 시점만 있다고 기준일에 "유효"하지 않다.
        record = _fact("T3-F1", fact_kind=FactKind.ACTUAL, entity="Platts JKM", valid_from="2021-01-07")
        self.assertIs(evaluate_fact(record, TARGET).status, TemporalStatus.PAST_EVENT)
        # 발생일이 기준일과 겹치면 판정하지 않는다.
        self.assertIs(evaluate_fact(record, date(2021, 1, 7)).status, TemporalStatus.UNCERTAIN)
        # 이미 가동에 들어간 설비(ACTUAL + OPERATING)는 일회성 사건이 아니라 지속 상태다.
        operating = _fact("T1-F2", fact_kind=FactKind.ACTUAL, asset_status=AssetStatus.OPERATING, valid_from="2026-03")
        self.assertIs(evaluate_fact(operating, TARGET).status, TemporalStatus.ACTIVE)

    def test_operating_asset_without_end_stays_active(self) -> None:
        operating = _fact("T1-F11", fact_kind=FactKind.STATUS, asset_status=AssetStatus.OPERATING, as_of="2026-06")
        self.assertIs(evaluate_fact(operating, TARGET).status, TemporalStatus.ACTIVE)

    def test_start_in_same_period_is_uncertain_and_ended_contract_is_ended(self) -> None:
        same_year = _fact("T1-F4", asset_status=AssetStatus.PLANNED, valid_from="2027")
        ended = _fact("T1-F5", valid_from="2020", valid_to="2026-06")
        self.assertIs(evaluate_fact(same_year, TARGET).status, TemporalStatus.UNCERTAIN)
        self.assertIs(evaluate_fact(ended, TARGET).status, TemporalStatus.ENDED)

    def test_timeline_skips_facts_without_timing_or_asset_status(self) -> None:
        plain = _fact("T1-F6")
        planned = _fact("T1-F7", asset_status=AssetStatus.PLANNED)
        timeline = build_timeline([plain, planned], TARGET)
        self.assertEqual([entry.fact_id for entry in timeline], ["T1-F7"])
        self.assertIs(timeline[0].status, TemporalStatus.UNCERTAIN)


def _apply(claims: list[EventClaim], verdicts: list[EventClaim], **kwargs: Any) -> EventValidation:  # noqa: ANN401
    return apply_claim_rules(
        _draft(claims, kwargs.pop("severity", ScenarioSeverity.BASE)),
        verdicts={verdict.claim_id: verdict for verdict in verdicts},
        untracked=kwargs.pop("untracked", []),
        quantitative_issues=kwargs.pop("quantitative_issues", []),
        unmarked_assumptions=kwargs.pop("unmarked_assumptions", []),
        reasoning_issues=kwargs.pop("reasoning_issues", []),
    )


class ClaimRuleTests(unittest.TestCase):
    def test_unsupported_user_assumptions_are_normal_scenario_conditions(self) -> None:
        cold = _claim("C1", ClaimType.USER_ASSUMPTION, text="2027년 1월 북서유럽 한파 발생")
        delay = _claim("C2", ClaimType.USER_ASSUMPTION, text="NFE 가동 6개월 지연")
        hormuz = _claim("C3", ClaimType.USER_ASSUMPTION, text="호르무즈 통항 정상화")
        validation = _apply(
            [cold, delay, hormuz],
            [
                cold.model_copy(update={"support": SupportStatus.UNSUPPORTED}),
                delay.model_copy(update={"support": SupportStatus.PARTIAL}),
                # 근거상 현재 차질 중이라도 정상화는 상태 변화 가정이다(hard_conflict=False).
                hormuz.model_copy(update={"support": SupportStatus.CONTRADICTED}),
            ],
        )
        self.assertEqual(validation.issues, [])
        self.assertFalse(validation.blocked)
        self.assertIs(validation.feasibility_status, FeasibilityStatus.CONSISTENT)

    def test_user_assumption_blocks_only_on_hard_conflict(self) -> None:
        claim = _claim("C1", ClaimType.USER_ASSUMPTION, text="Ras Laffan 손상 설비 2개월 내 완전 정상화")
        validation = _apply(
            [claim],
            [claim.model_copy(update={"support": SupportStatus.CONTRADICTED, "hard_conflict": True})],
            severity=ScenarioSeverity.TAIL_RISK,
        )
        self.assertEqual(_codes(validation, IssueSeverity.ERROR), ["USER_ASSUMPTION_CONFLICT"])
        self.assertFalse(validation.issues[0].fixable)
        self.assertTrue(validation.blocked)
        # 발생 강도(TAIL_RISK)와 성립성(근거 충돌)은 별개 축으로 남는다.
        self.assertIs(validation.scenario_severity, ScenarioSeverity.TAIL_RISK)
        self.assertIs(validation.feasibility_status, FeasibilityStatus.CONFLICTS_WITH_EVIDENCE)

    def test_user_assumption_off_schedule_only_warns(self) -> None:
        claim = _claim("C1", ClaimType.USER_ASSUMPTION, text="NFS 조기 가동(가정)")
        validation = _apply(
            [claim],
            [claim.model_copy(update={"support": SupportStatus.UNSUPPORTED, "temporal_ok": False})],
        )
        self.assertEqual(_codes(validation, IssueSeverity.WARNING), ["ASSUMPTION_TIMING"])
        self.assertFalse(validation.blocked)
        self.assertIs(validation.feasibility_status, FeasibilityStatus.CONSISTENT)

    def test_model_inference_is_judged_by_plausibility_not_direct_evidence(self) -> None:
        mechanism = _claim("C1", ClaimType.MODEL_INFERENCE, text="유럽 수요 급증으로 TTF 상승, 대서양 카고 유럽 유입")
        overreach = _claim("C2", ClaimType.MODEL_INFERENCE, text="JKM $24~30 확정")
        validation = _apply(
            [mechanism, overreach],
            [
                mechanism.model_copy(
                    update={"support": SupportStatus.UNSUPPORTED, "plausibility": InferencePlausibility.PLAUSIBLE},
                ),
                overreach.model_copy(
                    update={"support": SupportStatus.UNSUPPORTED, "plausibility": InferencePlausibility.WEAK},
                ),
            ],
        )
        self.assertEqual(_codes(validation, IssueSeverity.WARNING), ["WEAK_INFERENCE"])
        self.assertEqual(validation.issues[0].claim_id, "C2")
        self.assertFalse(validation.blocked)

    def test_model_inference_contradicting_evidence_is_fixable_error(self) -> None:
        claim = _claim("C1", ClaimType.MODEL_INFERENCE, text="Ras Laffan 2027년 1월 정상 가동 회복")
        validation = _apply(
            [claim],
            [
                claim.model_copy(
                    update={"plausibility": InferencePlausibility.CONTRADICTED, "reason": "복구 3~5년 소요"},
                ),
            ],
        )
        self.assertEqual(_codes(validation, IssueSeverity.ERROR), ["CONTRADICTS_EVIDENCE"])
        self.assertTrue(validation.issues[0].fixable)
        self.assertTrue(validation.blocked)
        self.assertIs(validation.feasibility_status, FeasibilityStatus.CONFLICTS_WITH_EVIDENCE)

    def test_fact_label_without_support_and_temporal_mismatch_are_errors(self) -> None:
        mislabeled = _claim("C1", ClaimType.EVIDENCED_FACT)
        buffer = _claim("C2", ClaimType.MODEL_INFERENCE, text="NFS 물량이 2027년 초 공급 완충재로 작동")
        validation = _apply(
            [mislabeled, buffer],
            [
                mislabeled.model_copy(update={"support": SupportStatus.UNSUPPORTED}),
                buffer.model_copy(update={"plausibility": InferencePlausibility.PLAUSIBLE, "temporal_ok": False}),
            ],
            quantitative_issues=["저장 인출 2.5~4 bcm 과 재고 3~5%p 하락이 저장 용량 기준으로 맞지 않음"],
            unmarked_assumptions=["한파 -6℃ 를 가정 표시 없이 서술"],
        )
        self.assertEqual(
            _codes(validation, IssueSeverity.ERROR),
            ["MISLABELED_FACT", "TEMPORAL_MISMATCH", "QUANT_INCONSISTENT"],
        )
        self.assertEqual(_codes(validation, IssueSeverity.WARNING), ["UNMARKED_ASSUMPTION"])

    def test_reasoning_gap_is_fixable_error_while_weak_inference_stays_warning(self) -> None:
        price = _claim("C1", ClaimType.MODEL_INFERENCE, text="공급 회복에도 수요 증가로 JKM 상승")
        validation = _apply(
            [price],
            [price.model_copy(update={"plausibility": InferencePlausibility.WEAK})],
            reasoning_issues=["공급 회복(하방)과 수요 증가(상방)를 합성하지 않고 상승으로 단정함"],
        )
        self.assertEqual(_codes(validation, IssueSeverity.ERROR), ["REASONING_GAP"])
        self.assertEqual(_codes(validation, IssueSeverity.WARNING), ["WEAK_INFERENCE"])
        self.assertTrue(all(issue.fixable for issue in validation.issues))
        self.assertTrue(validation.blocked)

    def test_severity_floor_counts_independent_shock_clusters_once(self) -> None:
        shocks = [
            _claim("C1", ClaimType.USER_ASSUMPTION, shock_cluster="북서유럽 기상"),
            _claim("C2", ClaimType.MODEL_INFERENCE, shock_cluster="북서유럽  기상"),  # 같은 묶음(공백 차이)
            _claim("C3", ClaimType.MODEL_INFERENCE, shock_cluster="호르무즈 통항 차질"),
            _claim("C4", ClaimType.MODEL_INFERENCE, shock_cluster="카타르 NFE 지연"),
            _claim("C5", ClaimType.EVIDENCED_FACT, shock_cluster="이미 확인된 충격"),
        ]
        verdicts = {
            claim.claim_id: claim.model_copy(
                update={
                    "support": SupportStatus.SUPPORTED
                    if claim.claim_type is ClaimType.EVIDENCED_FACT
                    else SupportStatus.UNSUPPORTED,
                },
            )
            for claim in shocks
        }
        validation = apply_claim_rules(
            _draft(shocks, ScenarioSeverity.BASE),
            verdicts=verdicts,
            untracked=[],
            quantitative_issues=[],
            unmarked_assumptions=[],
        )
        self.assertEqual(validation.shock_clusters, ["북서유럽 기상", "호르무즈 통항 차질", "카타르 NFE 지연"])
        self.assertIs(validation.scenario_severity, ScenarioSeverity.SEVERE_STRESS)
        self.assertIn("SEVERITY_RAISED", _codes(validation, IssueSeverity.WARNING))

    def test_untracked_contradiction_and_failed_verification_block(self) -> None:
        untracked = _claim("U1", ClaimType.EVIDENCED_FACT, support=SupportStatus.CONTRADICTED)
        validation = apply_claim_rules(
            _draft([]),
            verdicts={},
            untracked=[untracked],
            quantitative_issues=[],
            unmarked_assumptions=[],
        )
        self.assertEqual(_codes(validation, IssueSeverity.ERROR), ["CONTRADICTS_EVIDENCE"])

        failed = apply_claim_rules(
            _draft([]),
            verdicts=None,
            untracked=[],
            quantitative_issues=[],
            unmarked_assumptions=[],
        )
        self.assertEqual(_codes(failed, IssueSeverity.ERROR), ["VALIDATION_FAILED"])
        self.assertIs(failed.feasibility_status, FeasibilityStatus.UNVERIFIED)


class SummarizeFactTests(unittest.TestCase):
    def test_facts_drop_facts_without_relevant_evidence(self) -> None:
        topic = SearchTopic(topic_key="T1", label="카타르 공급")
        evidences = [
            EvidenceItem(evidence_key="T1-W1", origin=EvidenceOrigin.WEB, topic_key="T1"),
            EvidenceItem(evidence_key="T1-W2", origin=EvidenceOrigin.WEB, topic_key="T1"),
        ]
        output = brief_prompt.TopicBriefLLMOutput(
            relevant_evidence_keys=["T1-W1"],
            found=True,
            summary="요약",
            facts=[
                brief_prompt.FactLLMItem(
                    statement="NFS 2028년 가동 개시 예정",
                    evidence_keys=["[T1-W1]"],
                    fact_kind=FactKind.PLAN,
                    entity="NFS",
                    asset_status=AssetStatus.PLANNED,
                    valid_from="2028",
                ),
                # 관련 근거로 고르지 않은 근거에서 나온 사실은 버린다.
                brief_prompt.FactLLMItem(statement="무관한 사실", evidence_keys=["T1-W2"], fact_kind=FactKind.ACTUAL),
            ],
        )
        brief = _to_brief(output, topic, evidences)
        self.assertEqual([fact.fact_id for fact in brief.facts], ["T1-F1"])
        self.assertEqual(brief.facts[0].valid_from, "2028")
        self.assertEqual(brief.facts[0].evidence_keys, ["T1-W1"])


def _state_with_draft(**kwargs: Any) -> GenerateFromQueryState:  # noqa: ANN401
    claim = _claim("C1", ClaimType.MODEL_INFERENCE, text="Ras Laffan 2027년 1월 정상 가동 회복")
    return GenerateFromQueryState(
        user_query="카타르 공급 차질 시나리오",
        draft=_draft([claim]),
        fact_timeline=FactTimeline(target_date="2027-01-01"),
        topic_briefs=[TopicBrief(topic_key="T1", found=True)],
        **kwargs,
    )


def _verification(plausibility: InferencePlausibility) -> verify_prompt.ClaimVerificationLLMOutput:
    return verify_prompt.ClaimVerificationLLMOutput(
        claims=[
            verify_prompt.ClaimVerdictLLMItem(
                claim_id="C1",
                support=SupportStatus.UNSUPPORTED,
                plausibility=plausibility,
                temporal_ok=True,
                reason="r",
            ),
        ],
    )


class ValidateClaimsNodeTests(unittest.IsolatedAsyncioTestCase):
    async def _run(self, state: GenerateFromQueryState, plausibility: InferencePlausibility) -> dict[str, Any]:
        async def fake_invoke(**_: Any) -> LLMStructuredResult[verify_prompt.ClaimVerificationLLMOutput]:  # noqa: ANN401
            return LLMStructuredResult(result=_verification(plausibility))

        with patch("apps.connectors.llm.llm_client.invoke_llm_structured_output", new=fake_invoke):
            return await validate_claims_node.validate_claims(state)

    async def test_fixable_error_schedules_one_revision(self) -> None:
        update = await self._run(_state_with_draft(), InferencePlausibility.CONTRADICTED)
        self.assertTrue(update["pending_revision"])
        self.assertEqual(update["revision_count"], 1)
        self.assertTrue(update["validation"].blocked)

        revised = _state_with_draft(revision_count=1)
        update = await self._run(revised, InferencePlausibility.CONTRADICTED)
        self.assertFalse(update["pending_revision"])
        self.assertEqual(route_after_validation(revised.model_copy(update=update)), NODE_PERSIST_EVENTS)

    async def test_clean_draft_goes_forward(self) -> None:
        state = _state_with_draft()
        # 직접 근거가 없어도 타당한 모델 추론이면 통과한다.
        update = await self._run(state, InferencePlausibility.PLAUSIBLE)
        self.assertFalse(update["pending_revision"])
        self.assertFalse(update["validation"].blocked)
        self.assertEqual(route_after_validation(state.model_copy(update=update)), NODE_PERSIST_EVENTS)
        self.assertEqual(
            route_after_validation(state.model_copy(update={"pending_revision": True})),
            NODE_DRAFT_EVENTS,
        )


class PersistGateTests(unittest.TestCase):
    def _target(self, validation: EventValidation | None) -> tuple[Any, str | None]:  # noqa: ANN401
        state = GenerateFromQueryState(
            draft=EventDraft(event_title_ko="초안"),
            validation=validation,
            type_assignment=EventTypeAssignment(event_type_l2_id=3),
        )
        return persist._persist_target(state)  # noqa: SLF001

    def test_only_validated_unblocked_draft_is_persisted(self) -> None:
        target, warning = self._target(EventValidation())
        self.assertIsNotNone(target)
        self.assertIsNone(warning)

    def test_blocked_or_unvalidated_draft_is_not_persisted(self) -> None:
        blocked = apply_claim_rules(
            EventDraft(event_title_ko="충돌"),
            verdicts=None,
            untracked=[],
            quantitative_issues=[],
            unmarked_assumptions=[],
        )
        target, warning = self._target(blocked)
        self.assertIsNone(target)
        self.assertIsNone(warning)  # 차단 사유는 finalize 가 검증 이슈로 알린다.

        target, warning = self._target(None)
        self.assertIsNone(target)
        self.assertIsNotNone(warning)


class FactTimelineNodeTests(unittest.IsolatedAsyncioTestCase):
    def _state(self, scenario_date: str) -> GenerateFromQueryState:
        fact = EvidencedFact(
            fact_id="T1-F1",
            topic_key="T1",
            statement="NFS 2028년 가동 개시 예정",
            evidence_keys=["T1-W1"],
            fact_kind=FactKind.PLAN,
            entity="NFS",
            asset_status=AssetStatus.PLANNED,
            valid_from="2028",
        )
        return GenerateFromQueryState(
            query_plan=QueryPlan(scenario_date=scenario_date),
            topic_briefs=[TopicBrief(topic_key="T1", found=True, facts=[fact])],
        )

    async def test_uses_scenario_date_from_plan(self) -> None:
        update = await fact_timeline_node.build_fact_timeline(self._state("2027-01-15"))
        timeline = update["fact_timeline"]
        self.assertEqual(timeline.target_date, "2027-01-15")
        self.assertEqual([entry.status for entry in timeline.entries], [TemporalStatus.NOT_YET])

    async def test_falls_back_to_today_without_scenario_date(self) -> None:
        with patch.object(fact_timeline_node, "today_str", return_value="2029-03-01"):
            update = await fact_timeline_node.build_fact_timeline(self._state(""))
        self.assertEqual(update["fact_timeline"].target_date, "2029-03-01")
        self.assertEqual([entry.status for entry in update["fact_timeline"].entries], [TemporalStatus.ACTIVE])


class EvidenceKeyTests(unittest.TestCase):
    def test_keys_continue_per_topic_and_origin_on_fallback(self) -> None:
        first = web_documents_to_evidences(
            [WebDocument(url="a", topic_key="T1"), WebDocument(url="b", topic_key="T1"), WebDocument(topic_key="T2")],
            [],
        )
        self.assertEqual([e.evidence_key for e in first], ["T1-W1", "T1-W2", "T2-W1"])

        # 폴백 패스: 기존 근거 키는 그대로 두고 이어지는 번호로 덧붙인다. 출처가 다르면 번호도 따로 센다.
        events = event_hits_to_evidences([ExistingEventHit(mi_event_id=7, topic_key="T2")], first)
        self.assertEqual([e.evidence_key for e in events], ["T2-E1"])
        self.assertEqual(events[0].ref_id, 7)
        more_web = web_documents_to_evidences([WebDocument(url="c", topic_key="T2")], [*first, *events])
        self.assertEqual([e.evidence_key for e in more_web], ["T2-W2"])


class EvidenceReducerTests(unittest.IsolatedAsyncioTestCase):
    async def test_parallel_search_nodes_append_to_evidences(self) -> None:
        from langgraph.graph import END, START, StateGraph

        async def web(_: GenerateFromQueryState) -> dict[str, Any]:  # noqa: RUF029
            return {"evidences": web_documents_to_evidences([WebDocument(url="a", topic_key="T1")], [])}

        async def events(_: GenerateFromQueryState) -> dict[str, Any]:  # noqa: RUF029
            return {"evidences": event_hits_to_evidences([ExistingEventHit(mi_event_id=1, topic_key="T1")], [])}

        builder = StateGraph(GenerateFromQueryState)
        builder.add_node("web", web)
        builder.add_node("events", events)
        builder.add_edge(START, "web")
        builder.add_edge(START, "events")
        builder.add_edge(["web", "events"], END)
        final = await builder.compile().ainvoke(GenerateFromQueryState())
        self.assertEqual(sorted(e.evidence_key for e in final["evidences"]), ["T1-E1", "T1-W1"])


class FinalizeResponseTests(unittest.IsolatedAsyncioTestCase):
    def _state(self) -> GenerateFromQueryState:
        claim = _claim("C1", ClaimType.MODEL_INFERENCE)
        return GenerateFromQueryState(
            draft=_draft([claim]),
            validation=apply_claim_rules(
                _draft([claim]),
                verdicts={"C1": claim},
                untracked=[],
                quantitative_issues=[],
                unmarked_assumptions=["제목의 가정 표시 누락"],
            ),
            topic_briefs=[TopicBrief(topic_key="T1", label="토픽", found=True, facts=[_fact("T1-F1")])],
            fact_timeline=FactTimeline(target_date="2027-01-15"),
            warnings=["검색 경고"],
        )

    async def test_default_response_has_event_fields_and_route(self) -> None:
        result = (await generate_node.finalize(self._state()))["result"]
        self.assertEqual(set(result.model_dump()), {"meta", "events"})
        self.assertEqual(result.meta.warnings, ["검색 경고"])  # 검증 이슈 내용은 로그에만 남는다.
        self.assertEqual(
            set(result.events[0].model_dump()),
            {
                *GeneratedEventOut.model_fields,
                "operation",
                "source_mi_event_ids",
                "generation_rationale",
                "evidences",
                "mi_event_id",
            },
        )
        self.assertEqual(set(result.meta.model_dump()), {"route", "route_reason", "persisted_count", "warnings"})

    async def test_validation_issues_are_logged_not_returned(self) -> None:
        with patch.object(generate_node.logger, "info") as info:
            result = (await generate_node.finalize(self._state()))["result"]
        logged = " ".join(str(call.args[0]) for call in info.call_args_list)
        self.assertIn("VALIDATION_ISSUE", logged)
        self.assertIn("UNMARKED_ASSUMPTION", logged)
        self.assertNotIn("UNMARKED_ASSUMPTION", result.model_dump_json())


if __name__ == "__main__":
    unittest.main()
