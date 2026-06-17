from __future__ import annotations

from decimal import Decimal
from enum import Enum


class DirectionCode(str, Enum):
    SUP = "SUP"
    # REF = "REF"

    @classmethod
    def from_string(cls, value: str) -> "DirectionCode":
        return cls(value.upper())

    def equals(self, other: "DirectionCode | str") -> bool:
        if isinstance(other, DirectionCode):
            return self is other
        return self.value == str(other).upper()

    def to_string(self) -> str:
        return self.value


class SignpostStrength(str, Enum):
    VERYSTRONG = "VERYSTRONG"
    STRONG = "STRONG"
    MEDIUM = "MEDIUM"
    WEAK = "WEAK"
    VERYWEAK = "VERYWEAK"

    @classmethod
    def from_string(cls, value: str) -> "SignpostStrength":
        return cls(value.upper())

    @classmethod
    def from_string_or_default(
        cls,
        value: "SignpostStrength | str | None",
        default: "SignpostStrength" = MEDIUM,
    ) -> "SignpostStrength":
        if isinstance(value, cls):
            return value
        if value is None:
            return default
        try:
            return cls.from_string(str(value))
        except ValueError:
            return default

    @classmethod
    def stage4_prompt_guide_text(cls) -> str:
        """Build Stage4 prompt guide text from all enum members.

        Example output:
        1. strength 값: VERYSTRONG, STRONG, MEDIUM, WEAK, VERYWEAK
           - VERYSTRONG = 'realized' 신호 (매우 강): 시나리오 실현을 거의 확정하는 결정적 관측.
           - STRONG = 'realized' 신호: 시나리오가 사실상 실현됐음을 직접 증명하는 결정적 관측.
           - MEDIUM = 'early' 신호 (강): 시나리오 방향성의 분명한 초기 신호. 확정은 아님.
           - WEAK = 'early' 신호 (약): 정황적·간접적 초기 신호. 단독으로는 약함.
           - VERYWEAK = 'early' 신호 (매우 약): 약한 정황 신호. 단독 사용 시 신뢰도가 낮음.
        """
        strength_values = ", ".join(member.to_string() for member in cls)
        detail_lines = [
            f"   - {member.to_string()} = {member.description()}"
            for member in cls
        ]
        return "\n".join([f"1. strength 값: {strength_values}", *detail_lines])

    def equals(self, other: "SignpostStrength | str") -> bool:
        if isinstance(other, SignpostStrength):
            return self is other
        return self.value == str(other).upper()

    def to_string(self) -> str:
        return self.value

    def description(self) -> str:
        return _DESCRIPTION_BY_STRENGTH[self.to_string()]

    def to_impact_score(self) -> Decimal:
        return _IMPACT_SCORE_BY_STRENGTH[self.to_string()]


class ScenarioGroupStatus(str, Enum):
    CREATING = "creating"
    CREATED = "created"
    REALIZED = "realized"

    @classmethod
    def from_string(cls, value: str) -> "ScenarioStatus":
        return cls(str(value).lower())


class ScenarioStatus(str, Enum):
    CREATING = "creating"
    CREATED = "created"
    REALIZED = "realized"
    DISCARDED = "discarded"

    @classmethod
    def from_string(cls, value: str) -> "ScenarioStatus":
        return cls(str(value).lower())


_IMPACT_SCORE_BY_STRENGTH: dict[str, Decimal] = {
    SignpostStrength.VERYSTRONG.value: Decimal("1.25"),
    SignpostStrength.STRONG.value: Decimal("1.00"),
    SignpostStrength.MEDIUM.value: Decimal("0.50"),
    SignpostStrength.WEAK.value: Decimal("0.25"),
    SignpostStrength.VERYWEAK.value: Decimal("0.10"),
}

_DESCRIPTION_BY_STRENGTH: dict[str, str] = {
    SignpostStrength.VERYSTRONG.value: "'realized' 신호 (매우 강): 시나리오 실현을 거의 확정하는 결정적 관측.",
    SignpostStrength.STRONG.value: "'realized' 신호: 시나리오가 사실상 실현됐음을 직접 증명하는 결정적 관측.",
    SignpostStrength.MEDIUM.value: "'early' 신호 (강): 시나리오 방향성의 분명한 초기 신호. 확정은 아님.",
    SignpostStrength.WEAK.value: "'early' 신호 (약): 정황적·간접적 초기 신호. 단독으로는 약함.",
    SignpostStrength.VERYWEAK.value: "'early' 신호 (매우 약): 약한 정황 신호. 단독 사용 시 신뢰도가 낮음.",
}
