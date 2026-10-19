from __future__ import annotations

from typing import Final


AGENT_NAME = "event_generate_agent"

# 한 요청에서 생성할 수 있는 이벤트 초안 최대 개수.
MAX_EVENT_DRAFTS = 1

DEFAULT_LANGUAGE = "ko"

# --- generate_from_query flow ---

# 웹 검색 분기에서 근거로 채택할 문서 상한.
MAX_WEB_DOCUMENTS = 7

# 기존 이벤트 검색 분기에서 근거로 채택할 이벤트 상한.
# mi_events_list 는 키워드를 토큰 OR 로 매칭해 무관한 이벤트까지 넓게 물어오므로,
# 최신순 상위 소수만 취해 무관한 근거가 초안 프롬프트로 흘러드는 양을 제한한다.
MAX_EXISTING_EVENTS = 5

# 초안 생성 프롬프트에 넣을 근거(EvidenceItem) 상한(프롬프트 크기 가드).
MAX_EVIDENCE_ITEMS = 17

# Responses API 웹 검색 1건(질의 1개) 안에서 모델이 반복하는 검색 횟수 상한.
# 상한이 없으면 질의 1건이 10~17회 검색하며 150초 이상 걸린다(provider 기본값은 무제한).
# 3회일 때도 질의 1건이 27~37초 걸려 flow 전체의 약 30%를 차지했으므로 2회로 낮춘다(토픽당 질의 2개로 수집량 보완).
# 이 flow 에서만 호출 단위로 덮어쓰며, 다른 Agent 가 공유하는 web_search_* 설정은 바꾸지 않는다.
WEB_SEARCH_MAX_TOOL_CALLS = 2

# Responses API 웹 검색의 reasoning effort(이 flow 전용 호출 단위 override).
WEB_SEARCH_REASONING_EFFORT: Final = "low"

# 웹 검색에서 기간 지정이 없을 때 적용할 기본 조회 기간(일).
# 기존 이벤트 검색은 모집단이 MI DB 로 한정이므로 해당 기간을 사용하지 않음
DEFAULT_SEARCH_LOOKBACK_DAYS = 90

# tmm_mi_event_type_l2_m 카탈로그를 읽지 못했을 때(DB 미연결·빈 테이블) 모든 초안에 채울 event_type_l2_id.
# event_type_l2_id 는 tmm_mi_mievent_m 의 NOT NULL FK라 값이 없으면 저장되지 않는다.
# L2 ID 는 환경(로컬/개발기/운영기)마다 달라 고정값을 두면 FK 오류나 엉뚱한 유형으로 적재될 수 있으므로 None 으로 둔다.
# None 이면 분류하지 못한 초안은 임의 유형으로 저장되지 않고 경고만 남긴다.
FALLBACK_EVENT_TYPE_L2_ID: int | None = None

# 분기 판단·검색 계획·근거 정리·유형 분류처럼 판단 범위가 좁은 SPEED 단계의 reasoning effort.
# SPEED/QUALITY 가 같은 배포 모델을 가리켜도 지연을 줄이도록 단계 단위로 낮춘다.
# 초안 생성·claim 검증(QUALITY 단계)은 전역 설정값(llm_reasoning_effort)을 따른다.
LIGHT_REASONING_EFFORT: Final = "low"

# claim 검증에서 고칠 수 있는 error 가 나왔을 때 초안을 다시 생성하는 최대 횟수.
MAX_DRAFT_REVISIONS = 1

# 초안이 밝힐 claim 수 상한. claim 수에 비례해 초안·검증 출력(지연)이 커지므로 결론을 좌우하는 주장만 남긴다.
# 상한 밖의 본문 주장 중 문제가 있는 것은 검증기가 untracked_claims 로 따로 잡는다.
MAX_DRAFT_CLAIMS = 12

# --- tmm_mi_mievent_m 저장 제약 ---

# search_text 컬럼 길이(VARCHAR(500)).
SEARCH_TEXT_MAX_LENGTH = 500

# one_line_summary 컬럼 길이(VARCHAR(300)).
ONE_LINE_SUMMARY_MAX_LENGTH = 300

# 생성 직후 바로 노출되도록 커스텀 이벤트의 publish_status 를 게시 상태로 저장한다.
EVENT_PUBLISH_STATUS_PUBLISHED: Final = "PUBLISHED"

# 요청에 user_id가 없을 때 쓰는 기본 사용자 ID.
DEFAULT_ACTOR_ID = "user"
# crt_usr_logn_id·mod_usr_logn_id 는 MCP 경유 생성임을 구분하도록 "mcp_{user_id}" 형식으로 저장한다.
EVENT_ACTOR_ID_PREFIX = "mcp_"
