# Event 검색 문서 구성

## 현재 범위

MySQL의 Event를 임베딩 전 검색 문서로 변환하고 로컬 JSONL로 검토한다.
임베딩 모델·Vector DB에 종속되지 않으며 DB 변경, LLM 호출, 임베딩 생성, 벡터 저장은 수행하지 않는다.
추천 기준은 [Event 추천 기준](08_EVENT_RECOMMENDATION_CRITERIA.md)을 따른다.
생성한 JSONL의 로컬 임베딩·Qdrant 적재·검색 방법은 [로컬 벡터 검색 테스트](10_LOCAL_EVENT_VECTOR_SEARCH.md)에 있다.

| 소스 | 책임 |
| --- | --- |
| `apps/persistence/event/schema.py`의 `EventSearchSource` | DB 조회 전용 DTO, 원본 JSON shape 유지 |
| `apps/persistence/event/repository.py`의 `list_search_sources` | 삭제되지 않은 PUBLISHED Event와 활성 Record 연결 SELECT |
| `apps/persistence/event/service.py`의 `load_search_sources` | session 범위, 최대 200개 조회, DTO 검증 |
| `schemas/event_search_document.py` | 검색 문서·메타데이터 계약 |
| `utils/event_search_document.py` | 텍스트 구성, 분할, ID·해시 생성 |
| `scripts/export_event_search_documents.py` | 샘플 선정, JSONL·보고서 생성, 원문 보존 확인 |

이것은 내부 개발용 export다. 게시·삭제 필터는 적용하지만 요청 사용자별 접근 권한은 평가하지 않는다.
운영 추천 API는 현재 DB 상태와 요청 사용자 권한을 별도로 확인해야 하며, export 데이터를 그대로
공개 조회 API로 노출하지 않는다. DB migration은 필요하지 않다.

## 필드 매핑과 보존

| DB 컬럼 | 문서 용도 |
| --- | --- |
| `one_line_summary` | 제목; 기존 `EventPayload.one_line_summary`의 요약 의미와 혼동하지 않는다 |
| `search_text` | 요약 |
| `key_bullets_json` | 핵심 내용 |
| `tags_json` | 태그 텍스트 및 메타데이터 |
| `detail_analysis` | 상세 분석 |
| `numeric_facts_md` | 수치·단위·기간을 포함한 정량 근거 |
| `institution_view_synthesis` | 저장되어 있는 기관 전망 |
| ID·유형·발생일·생성일·수정일·게시/삭제 상태·Record ID | 메타데이터 |

JSON 배열, `{"bullets": [...]}` / `{"tags": [...]}` wrapper, JSON 문자열을 지원한다.
예상과 다른 shape나 깨진 JSON 문자열은 원문/JSON 표현을 텍스트에 보존하고 경고를 남긴다.
정규화는 개행을 LF로 통일하고 각 필드 바깥의 공백을 정리하는 정도다. Markdown·표·URL·숫자·단위·
주체·가정·전망 표현 및 내부 공백은 유지한다. 중복처럼 보이는 문장도 출처나 전제가 다를 수 있어
자동 삭제하거나 LLM으로 요약하지 않는다.

누락된 값은 채우지 않는다. 날짜는 DB 값을 그대로 직렬화하며 timezone 없는 DATETIME에 UTC를
추정해 붙이지 않는다. `occurred_at`은 발생일이고 영향 대상 기간을 뜻하지 않는다.
`contains_assumption_or_test_marker`는 '가정/가상/테스트/hypothetical/test event' 문자열 탐지 결과다.
Event 전체의 사실 여부를 분류하지 않으며, 해당 표현을 제거하거나 자동 제외하지 않는다.

## 문서 분할과 갱신 계약

- 문서 형식 버전은 `event-search-v1`이다.
- 짧은 Event는 하나의 문서다. 정규화 문서가 기본 2,400자를 초과하면 문단 → 줄 → 문장 → 공백
  경계를 우선해 분할한다. 경계가 없으면 글자 수 상한으로 나눈다.
- 2,400자는 토큰 수가 아니며 임베딩 모델의 입력 한도를 보장하지 않는다. 모델 선정 시 다시 조정한다.
- 각 문서의 `content`는 정규화 문서의 정확한 부분 문자열이다. 겹침 없이 이어 붙이면 전체가 복원된다.
- 첫 문서의 `text`는 `content`와 같다. 후속 문서에는 제목을 앞에 붙여 검색 맥락을 보완한다.
  제목 접두어는 `max_content_chars` 밖의 추가 길이다. Vector DB에는 `text`를 임베딩한다.
- `content_start/end`는 Python 문자 인덱스이며 end는 exclusive다. 원본 DB 문자열의 byte offset이 아니다.
- 모든 문서에 `event_id`, `chunk_index/count`, 원본 날짜·Record ID가 있다. 추천 후보는 Event 단위로
  중복 제거하고, 최종 LLM 판단 전 전체 Event를 다시 조회해 문서 경계의 문맥 손실을 보완한다.
- `document_id = event:{ID}:event-search-v1:{max_content_chars}:{chunk_index:04d}`.
  같은 정책/내용의 재실행은 동일 ID를 생성한다.
- `source_hash`는 날짜·상태·원본 JSON을 포함한 조회 DTO의 SHA-256, `text_hash`는 실제 임베딩 텍스트의
  SHA-256이다. 메타데이터만 변경되면 source hash는 달라져도 text hash는 같을 수 있다.
- 향후 동기화 시 Event별 전체 문서를 교체하고, 분할 수 감소·정책 변경 시 남은 옛 문서를 제거해야 한다.
  삭제·미게시 전환도 기존 벡터 제거 대상이다. 이 문서 준비 단계에서는 동기화를 수행하지 않는다.
- 모든 내용이 비어 있으면 문서를 만들지 않고 `empty_content` 경고를 남긴다.

## 실행

저장소 루트의 PowerShell에서 실행한다. Windows에서는 기존 YAML 설정을 UTF-8로 읽도록 `-X utf8`을 쓴다.
DB 모드는 기본 `envs/.env`를 `override=True`로 로드한 뒤 기존 `get_settings()` 설정을 사용한다.
다른 환경은 `--env-file`로 명시한다. 접속 정보는 산출물에 기록하지 않는다.

```powershell
.venv\Scripts\python.exe -X utf8 scripts/export_event_search_documents.py --sample-size 30
```

기본 후보 풀은 최근 수정순 최대 200개다. 그 안에서 본문이 가장 짧은/긴 Event와 전망 표현이 있는
Event를 우선 포함하고, 나머지는 조회 순서대로 채운다. 통계는 전체 DB가 아닌 조회 풀·선택 샘플 범위다.
특정 Event만 지정하려면 `--event-ids 5 9 47`을 사용한다. 요청한 ID가 조회되지 않으면 실패한다.

```powershell
.venv\Scripts\python.exe -X utf8 scripts/export_event_search_documents.py --event-ids 5 9 47
```

결과는 `local/output/event_search_documents/{KST 실행시각}/` 아래에 생성한다. `--output-dir`로 지정할 수
있으며 기존 폴더를 덮어쓰지 않는다. `local/` 산출물은 Git에 포함하지 않는다.

| 파일 | 내용 |
| --- | --- |
| `source_events.jsonl` | 조회 원본 DTO; 선택한 컬럼의 원본 JSON과 날짜 보존 |
| `documents.jsonl` | `document_id`, 임베딩할 `text`, 복원용 `content`, `metadata` |
| `report.json` | Event/문서 수, 누락 필드, 경고, Event별 복원 검증 |
| `preview.md` | 전체 샘플 요약과 대표 3개 Event 내용 |

DB 재조회 없이 변환을 재현할 수도 있다.

```powershell
.venv\Scripts\python.exe -X utf8 scripts/export_event_search_documents.py --input-jsonl local/output/event_search_documents/20261030_sample/source_events.jsonl
```

## 검증

문서 `content`를 순서대로 합친 결과가 정규화 전체 문서와 같은지, 원본 텍스트 필드와 offset이
보존되는지 확인한다. 이는 변환 과정의 누락 검사이며, Event의 사실 여부 검증이나 추천 품질 평가는 아니다.
JSON wrapper·잘못된 JSON 보존, 수치·기관 전망·URL 보존, 긴 문서 복원, 게시/삭제 필터, 안정적인
ID/해시, JSONL 재실행을 `tests/automated/test_event_search_documents.py`에서 검증한다.
