from enum import Enum, unique


@unique
class ErrorCode(Enum):
    RUNTIME_REGISTRY_NOT_READY = (
        -100,
        "Runtime Registry 준비 안됨",
    )
    SEMAPHORE_MANAGEMENT_ERROR = (-101, "세마포어 관리 오류")
    USER_QUERY_ERROR = (
        -200,
        "사용자 질의는 1글자 이상 입력되어야합니다.",
    )
    CLASSIFY_SCENARIO_TYPE_FAILED = (
        -1000,
        "사용자 질의 내용 기반으로 시나리오 타입 분류에 실패했습니다.",
    )
    FLOW_MAPPING_FAILED = (-2000, "Flow매핑에 실패했습니다.")
    QUERY_STRUCTURING_FAILED = (-3000, "질의 구조화 중 오류가 발생했습니다.")
    DATA_RETRIEVAL_FAILED = (-4000, "데이터 조회 중 문제가 발생했습니다.")
    LLM_RESPONSE_TIMEOUT = (-5000, "LLM 응답이 지연되었습니다.")
    LLM_INVALID_RESPONSE_ERROR = (-5001, "LLM 응답이 포맷에 맞지 않습니다")
    LLM_INVOCATION_ERROR = (-5002, "LLM 호출 후 비정상 오류가 발생했습니다.")
    RDB_DATA_FETCH_FAILED = (-6000, "RDB 데이터 조회시 오류가 발생했습니다.")
    RDB_ACCESS_DENIED = (-6001, "해당 RDB 데이터 접근 권한이 없습니다.")
    HTTP_CONNECTION_ERROR = (-7000, "HTTP연결 실패했습니다.")
    UNKNOWN_ERROR = (-9999, "알 수 없는 오류가 발생했습니다.")
