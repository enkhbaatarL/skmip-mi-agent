from __future__ import annotations

from enum import StrEnum


class StateDirection(StrEnum):
    """Shared v4 Lever-state direction and its Presentation label."""

    label_ko: str

    INCREASE = ("increase", "증가")
    DECREASE = ("decrease", "감소")
    DISRUPT = ("disrupt", "차질")
    RECOVER = ("recover", "회복")
    UNCHANGED = ("unchanged", "현 수준 유지")

    def __new__(cls, value: str, label_ko: str) -> StateDirection:
        member = str.__new__(cls, value)
        member._value_ = value
        member.label_ko = label_ko
        return member

    @classmethod
    def prompt_values(cls) -> str:
        """Return the allowed wire values for structured-output prompt guidance."""
        return ", ".join(member.value for member in cls)


__all__ = ["StateDirection"]
