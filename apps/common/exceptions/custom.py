from __future__ import annotations

from apps.common.values.error_codes import ErrorCode


class MIBaseError(Exception):
    """
    Example:
        raise MIBaseError(ErrorCode.ENTITY_NOT_FOUND, detail="id=123")
        raise MIBaseError(ErrorCode.RDB_DATA_FETCH_FAILED, detail=str(exc)) from exc
    """

    def __init__(self, error_code: ErrorCode, detail: str | None = None) -> None:
        code, base_message, http_status = error_code.value
        self.error_message = f"{base_message} - {detail}" if detail else base_message
        self.error_code = error_code
        self.code = code
        self.status_code = http_status
        super().__init__(f"[{error_code.name}] {self.error_message}")
