from enum import Enum, unique


@unique
class ErrorCode(Enum):
    # 100 ~ 199: Runtime 관련 오류
    RUNTIME_REGISTRY_NOT_READY = (-100, "Runtime Registry 준비 안됨", 503)
    SEMAPHORE_MANAGEMENT_ERROR = (-101, "세마포어 관리 오류", 500)
    USER_QUERY_ERROR = (-200, "사용자 질의는 1글자 이상 입력되어야합니다.", 422)
    ENTITY_NOT_FOUND = (-201, "요청한 리소스를 찾을 수 없습니다", 404)
    INVALID_REQUEST = (-202, "요청이 유효하지 않습니다.", 400)

    # 1000 ~ 1999: Scenario Group Agent 관련 오류
    CLASSIFY_SCENARIO_TYPE_FAILED = (-1000, "사용자 질의 내용 기반으로 시나리오 타입 분류에 실패했습니다.", 500)
    SCENARIO_GROUP_ALREADY_CREATED = (-1001, "시나리오 그룹이 이미 생성되었습니다.", 400)
    SCENARIO_VALIDATION_INPUT_ERROR = (-1002, "시나리오 검증 입력 오류", 422)
    SCENARIO_GROUP_OWNERSHIP_CONFLICT = (
        -1003,
        "시나리오 그룹 생성 권한이 없습니다. 다른 사용자에 의해 시나리오가 생성중입니다.",
        403,
    )
    SCENARIO_GROUP_ADMIN_FORBIDDEN = (-1004, "시나리오 그룹 관리자 권한이 없습니다.", 403)
    SCENARIO_GROUP_OPERATION_CONFLICT = (
        -1005,
        "실행 중인 Scenario Group 작업과 충돌합니다.",
        409,
    )
    SCENARIO_VALIDATION_STALE = (
        -1006,
        "Validation 이후 Scenario 또는 Dimension 정의가 변경되었습니다. 화면을 새로고침한 뒤 Validation을 다시 실행해주세요.",
        409,
    )

    # 추후 분류 예정
    FLOW_MAPPING_FAILED = (-2000, "Flow매핑에 실패했습니다.", 500)
    QUERY_STRUCTURING_FAILED = (-3000, "질의 구조화 중 오류가 발생했습니다.", 500)
    DATA_RETRIEVAL_FAILED = (-4000, "데이터 조회 중 문제가 발생했습니다.", 500)
    LLM_RESPONSE_TIMEOUT = (-5000, "LLM 응답이 지연되었습니다.", 504)
    LLM_RESPONSE_ERROR = (-5001, "LLM 응답 중 오류가 발생했습니다.", 500)
    LLM_INVALID_RESPONSE_ERROR = (-5001, "LLM 응답이 포맷에 맞지 않습니다", 500)
    LLM_INVOCATION_ERROR = (-5002, "LLM 호출 후 비정상 오류가 발생했습니다.", 500)
    RDB_DATA_FETCH_FAILED = (-6000, "RDB 데이터 조회시 오류가 발생했습니다.", 500)
    RDB_ACCESS_DENIED = (-6001, "해당 RDB 데이터 접근 권한이 없습니다.", 403)
    HTTP_CONNECTION_ERROR = (-7000, "HTTP연결 실패했습니다.", 502)
    UNKNOWN_ERROR = (-9999, "알 수 없는 오류가 발생했습니다.", 500)
