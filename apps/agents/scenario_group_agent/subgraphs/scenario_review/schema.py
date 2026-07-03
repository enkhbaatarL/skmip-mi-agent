from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class CheckResult:
    check_id: str
    stage: str
    name: str
    status: Literal["PASS", "WARN", "FAIL", "INFO"]
    detail: str
    offenders: list[str] = field(default_factory=list)
    # 현업 사용자에게 그대로 노출할 완성형 안내 문장(시나리오명·값·권장 변경 포함).
    # 비어 있으면 CHECK_DISPLAY 기반 일반 문구로 대체된다.
    advice: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "stage": self.stage,
            "name": self.name,
            "status": self.status,
            "detail": self.detail,
            "offenders": self.offenders,
            "advice": self.advice,
        }


@dataclass
class ReviewContext:
    group: dict[str, Any]
    scenarios: list[dict[str, Any]]
    template_dims: list[dict[str, Any]]
    selected_dims: list[str]
    dim_index: dict[str, dict[str, Any]]
    enum_index: dict[str, list[str]]
    # 요청 본문이 DB(create scenario 결과)와 정확히 일치하는지 여부.
    # True 면 사용자가 수정한 것이 없으므로 review 를 건너뛰고 통과 처리한다.
    unchanged: bool = False


@dataclass
class ReviewReport:
    verdict: Literal["PASS", "REVIEW", "BLOCK"]
    is_valid: bool
    reason: str
    summary: dict[str, int]
    checks: list[CheckResult]
