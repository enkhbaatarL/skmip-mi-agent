[Code 구조 규칙 - 에이전트가 반드시 지킬 것]
1) default: claude-opus-4-1-20250805 모델 적용
2) LLM Chain 구조로 설계 (공통 state 공유)
   외부 리소스 로딩 → Pydantic 스키마 → Prompt 조립 → LLM Chain 호출(+재시도) → 방어적 후처리 → DB 친화 Document 조립 → JSON 저장 → 터미널 요약
3) 컴포넌트만 형식적으로 있고 상세 내용 미구현 상태면 "\### 생략: <추가 설명>" 형식으로 채워넣기.

[Code 스타일 규칙 — 에이전트가 반드시 지킬 것]
1) 파일 구조 — 최상단 모듈 docstring(개요/관계/Usage/Output), `# ══...` 섹션 구분,
   진입점은 `main()` 하나로 수렴 + `if __name__`.
2) 문법 기본 — stdlib→3rd party import / private `_snake`, 상수 `UPPER`,
   환경변수 공통 접두어(`REF_*`) / 타입 힌트 필수(PEP 604 `X | None`).
3) Docstring & 주석 — 한 줄 요약→빈 줄→상세, **실패/경계 조건 명시**.
   "왜"를 설명, 섹션 헤더 아래 `# [패턴]` 블록으로 의도 요약.
4) Pydantic 규약 — `Field(description=...)` 필수, `# --- 그룹 ---` 주석으로 그룹핑,
   비즈니스 검증은 `@model_validator(mode="after")`, `conlist` 에
   `# type: ignore[valid-type]`, mutable 기본값은 `default_factory=list`.
5) Prompt 설계 — SYSTEM / USER / HARD_CONSTRAINTS 3분할.
   HARD_CONSTRAINTS 는 재시도 시 누적 주입(점진 강화).
6) LLM 호출 — 재시도(지수 백오프+지터) + fallback 경로 필수.
   `except Exception as exc:  # noqa: BLE001` 후 판정 함수로 분기 + reason 로그.
   출력은 "입력 범위 밖 값" 제거 등 방어적 후처리.
7) 함수 설계 — 단일 책임(retry 판정처럼 종류별로 쪼개고 상위는 조합만).
   불변 데이터(taxonomy 등)는 모듈 로드 시 1회 계산해 상수화.
8) I/O 관례 — 경로 기준 `Path(__file__).parent` + `encoding="utf-8"` 필수.
   JSON 은 `ensure_ascii=False, indent=2`. datetime 은 UTC 통일 + ISO-8601 `Z`,
   느슨한 파서로 다양한 입력 포맷 수용.
9) 튜닝 파라미터 — 모델/max_tokens/경로 등은 `os.getenv("REF_*", default)` 로 노출.
10) 로그/출력 — ▸ 정보 / ↳ 재시도·경고 / => 완료 / ✅ 성공 / ═ 헤더.
    터미널 표는 f-string 고정폭, 마지막에 커버리지/누락 집계 1줄.