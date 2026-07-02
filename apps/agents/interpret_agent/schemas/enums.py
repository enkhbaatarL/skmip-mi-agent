from __future__ import annotations

from enum import Enum


class PriceInterpretationStatus(str, Enum):
    """가격전망 해석 라이프사이클 상태.

    - PROCESSING: 생성 요청 접수 후 background 해석 생성 중
    - CREATED: 해석 생성 완료(callback으로 B.E에 전달됨)
    - FAILED: 해석 생성 실패
    """

    PROCESSING = "PROCESSING"
    CREATED = "CREATED"
    FAILED = "FAILED"

    @classmethod
    def from_string(cls, value: str) -> "PriceInterpretationStatus":
        return cls(str(value).upper())
