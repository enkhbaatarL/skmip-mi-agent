from __future__ import annotations

from collections import defaultdict

from apps.persistence.enums import SignpostStrength
from apps.persistence.signpost.models import MiSignpostModel
from apps.persistence.signpost.repository import (
    SignpostRepository,
)
from apps.persistence.signpost.schema import GeneratedSignpostPayload, SignpostPayload


def build_signpost_model(
    payload: GeneratedSignpostPayload,
    *,
    display_order: int,
    user_id: int | None = None,
) -> MiSignpostModel:
    rationale = payload.rationale_ko or ""
    if payload.keyword_hints:
        rationale = f"{rationale}\n\nkeyword_hints: {', '.join(map(str, payload.keyword_hints))}".strip()
    strength = (
        SignpostStrength.from_string(payload.strength)
        if isinstance(payload.strength, str)
        else payload.strength
    )
    strength_value = strength.to_string() if strength is not None else None
    impact_score = strength.to_impact_score() if strength is not None else None

    model = MiSignpostModel(
        scenario_id=int(payload.scenario_id),
        label=(payload.label or "")[:500],
        probability_direction_code=payload.direction.to_string(),
        strength=strength_value,
        probability_impact_score=impact_score,
        signpost_reason=rationale,
        display_order=display_order,
        keyword_hints=payload.keyword_hints,
        use_yn="Y",
    )
    if user_id is not None:
        model.crt_usr_logn_id = user_id
        model.mod_usr_logn_id = user_id
    return model


class SignpostService:
    def load_by_scenario_ids(self, scenario_ids: list[int]) -> list[SignpostPayload]:
        from apps.common.configs.database.sync_database.connection import (
            get_sync_session,
        )

        session = get_sync_session()
        try:
            repository = SignpostRepository(session=session)
            return [SignpostPayload.from_model(model) for model in repository.fetch_models_by_scenario_ids(scenario_ids)]
        finally:
            session.close()

    def has_signposts(self, scenario_id: int) -> bool:
        from apps.common.configs.database.sync_database.connection import (
            get_sync_session,
        )

        session = get_sync_session()
        try:
            return SignpostRepository(session=session).exists_for_scenario(scenario_id)
        finally:
            session.close()

    def save_generated_signposts(
        self,
        signposts: list[GeneratedSignpostPayload],
        user_id: int | None = None,
    ) -> list[int]:
        from apps.common.configs.database.sync_database.connection import (
            get_sync_session,
        )

        session = get_sync_session()
        try:
            repository = SignpostRepository(session=session)
            saved_ids: list[int] = []
            display_order_by_scenario: dict[int, int] = defaultdict(int)
            for signpost in signposts:
                scenario_id = int(signpost.scenario_id)
                display_order_by_scenario[scenario_id] += 1
                saved_ids.append(
                    repository.insert_signpost(
                        build_signpost_model(
                            payload=signpost,
                            display_order=display_order_by_scenario[scenario_id],
                            user_id=user_id,
                        )
                    )
                )
            session.commit()
            return saved_ids
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
