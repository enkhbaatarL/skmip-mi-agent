from apps.common.values.error_codes import ErrorCode


class MIBaseError(Exception):
    def __init__(self, error_code: ErrorCode, detail: str | None = "") -> None:
        base_message = error_code.value
        if detail:
            self.error_message = f"{base_message} - {detail}"
        else:
            self.error_message = base_message
        self.error_code = error_code
        super().__init__(f"[{error_code.name}] {self.error_message}")


class UserQueryError(MIBaseError):
    def __init__(self, detail: str | None = None) -> None:
        super().__init__(ErrorCode.USER_QUERY_ERROR, detail)


class ClassifyScenarioError(MIBaseError):
    def __init__(self, detail: str | None = None) -> None:
        super().__init__(ErrorCode.CLASSIFY_SCENARIO_TYPE_FAILED, detail)


class FlowMappingError(MIBaseError):
    def __init__(self, detail: str | None = None) -> None:
        super().__init__(ErrorCode.FLOW_MAPPING_FAILED, detail)


class QueryStructuringError(MIBaseError):
    def __init__(self, detail: str | None = None) -> None:
        super().__init__(ErrorCode.QUERY_STRUCTURING_FAILED, detail)


class DataRetrievalError(MIBaseError):
    def __init__(self, detail: str | None = None) -> None:
        super().__init__(ErrorCode.DATA_RETRIEVAL_FAILED, detail)


class LLMTimeoutError(MIBaseError):
    def __init__(self, detail: str | None = None) -> None:
        super().__init__(ErrorCode.LLM_RESPONSE_TIMEOUT, detail)


class RdbDataFetchError(MIBaseError):
    def __init__(self, detail: str | None = None) -> None:
        super().__init__(ErrorCode.RDB_DATA_FETCH_FAILED, detail)


class RdbAccessDeniedError(MIBaseError):
    def __init__(self, detail: str | None = None) -> None:
        super().__init__(ErrorCode.RDB_ACCESS_DENIED, detail)


class LLMInvalidResponseError(MIBaseError):
    def __init__(self, detail: str | None = None) -> None:
        super().__init__(ErrorCode.LLM_INVALID_RESPONSE_ERROR, detail)


class LLMInvocationError(MIBaseError):
    def __init__(self, detail: str | None = None) -> None:
        super().__init__(ErrorCode.LLM_INVOCATION_ERROR, detail)


class RuntimeRegistryNotReadyError(MIBaseError):
    def __init__(self, detail: str | None = None) -> None:
        super().__init__(ErrorCode.RUNTIME_REGISTRY_NOT_READY, detail)


class SemaphoreManagementError(MIBaseError):
    def __init__(self, detail: str | None = None) -> None:
        super().__init__(ErrorCode.SEMAPHORE_MANAGEMENT_ERROR, detail)


class HttpConnectionError(MIBaseError):
    def __init__(self, detail: str | None = None) -> None:
        super().__init__(ErrorCode.HTTP_CONNECTION_ERROR, detail)


class UnknownMIError(MIBaseError):
    def __init__(self, detail: str | None = None) -> None:
        super().__init__(ErrorCode.UNKNOWN_ERROR, detail)
