# Scenario Group Agent DB Spec

## 기준

이 문서는 Scenario Group Agent가 읽고 쓰는 table의 관계와 업무상 중요한 컬럼을 설명한다. 실제 column type,
index, constraint mapping은 `apps/persistence/<domain>/models.py`가 런타임 정본이다. DB migration의 정본은
별도 `skmip-mi-agent-mgmt` 저장소의 Alembic이며, 현재 Scenario 관련 기준 revision은 0026이다.

Agent flow나 node에서 SQL을 직접 실행하지 않는다.

```text
flow / node
  → apps/agents/scenario_group_agent/persistence/*_service.py
  → apps/persistence/<domain>/repository.py
  → ORM model
```

## 관계 개요

```mermaid
erDiagram
    %% Cardinality: || = exactly one, o{ / }o = zero or more
    %% Relationship labels such as selected_as, has, and contains describe domain meaning only.
    MI_EVENT ||--o{ SCENARIO_GROUP_EVENT : selected_as
    SCENARIO_GROUP ||--o{ SCENARIO_GROUP_EVENT : has
    SCENARIO_GROUP ||--o{ SCENARIO : contains
    SCENARIO ||--o{ SIGNPOST : has
    SCENARIO_GROUP ||--o{ OPERATION : runs
    OPERATION ||--o{ OPERATION_EVENT : emits
    MODEL_IMPACT_LEVER }o--o{ SCENARIO_GROUP : grounds_v4
```

### 관계 기호와 이름

| 표기 | 의미 |
| --- | --- |
| `||` | 정확히 1개이며 필수 |
| `o|`, `|o` | 0개 또는 1개 |
| `|{`, `}|` | 1개 이상 |
| `o{`, `}o` | 0개 이상 |
| `||--o{` | 왼쪽 1개에 오른쪽 0개 이상이 연결되는 1:N 관계 |
| `}o--o{` | 양쪽 모두 0개 이상 연결될 수 있는 선택적 N:M 관계 |

관계 이름은 Mermaid나 DB가 해석하는 제약 키워드가 아니라 업무 의미를 설명하는 label이다. `selected_as`는
Event가 Scenario Group 생성 대상으로 선택된 관계, `has`는 상위 개체가 하위 개체를 가지는 관계,
`contains`는 Group이 Scenario를 구성요소로 포함하는 관계를 뜻한다. 필수 여부와 개수는 관계 이름이 아니라
위 기호로 읽으며, 실제 FK, null 허용 여부, 삭제 동작은 ORM과 migration 정의를 따른다.

`MI_EVENT`와 `SCENARIO_GROUP`은 `SCENARIO_GROUP_EVENT` 연결 table을 통해 N:M 관계를 구성한다. 즉 하나의
Event가 여러 Group에 선택될 수 있고, 하나의 Group도 여러 Event를 선택할 수 있다.

## 1. 입력 정본

### Event

| Table | 역할 |
| --- | --- |
| `tmm_mi_mievent_m` | Event 제목, 요약, 핵심 사실, 발생 시각, 추천 상태 |
| `tmm_mi_event_type_l1_m` | Event Type L1 master |
| `tmm_mi_event_type_l2_m` | Event Type L2 master |
| `tmm_mi_mievent_record_map` | Event와 원본 MI record 관계 |

v4 create는 Event Type Template을 생성 기준으로 사용하지 않지만 Event 상세 조회와 legacy v1~v3 복원에는
Event Type 관계가 필요하다.

검색 문서 샘플 export는 `EventRepository.list_search_sources`로 `del_yn='N'`, `publish_status='PUBLISHED'`
Event와 활성 Record 연결을 읽는다. 신규 컬럼이나 테이블을 만들지 않는다. 사용자별 권한을 평가하는
운영 검색 API는 아니며, 문서 변환 계약은 [Event 검색 문서 구성](09_EVENT_SEARCH_DOCUMENTS.md)을 따른다.

### Event 검증 결과와 검색 근거 보관

관리 저장소 revision `0053_mievent_verification`은 `tmm_mi_mievent_verification_m`을 생성한다.
검증 API는 이 테이블에 내부 판정·원본 검색 인용·Event 전체 row 해시를 저장한 뒤 verificationId를 반환한다.
업데이트 API는 verificationId로 근거를 조회하며 재검색하지 않는다. 테이블은 관리 저장소에서 사전 적용해야 한다.

| 컬럼 | 타입 / 용도 |
| --- | --- |
| `mi_event_verification_id` | CHAR(36) PK, 서버 생성 UUID |
| `mi_event_id` | INT UNSIGNED NOT NULL, Event FK |
| `event_fingerprint` | CHAR(64) NOT NULL, 검증 당시 Event 상태 SHA-256 |
| `verification_result_json` | JSON NOT NULL, 내부 등급·항목별 판정·후기 |
| `search_evidence_json` | JSON NOT NULL, 근거별 id/url/title/content 배열, 근거 없으면 [] |
| `checked_at`, `expires_at` | DATETIME(6) NOT NULL, UTC 검증 기준 시각과 만료 시각 |
| `applied_mi_event_snapshot_id` | INT UNSIGNED NULL, 적용 시 생성한 변경 전 Snapshot FK |
| `crt_usr_logn_id`, `mod_usr_logn_id` | VARCHAR(100) NOT NULL, 검증 요청 actor로 생성, 적용 시 mod actor만 갱신 |
| `crt_dtm`, `mod_dtm` | DATETIME(6) NOT NULL, CURRENT_TIMESTAMP(6); mod_dtm은 ON UPDATE 자동 갱신 |
| `del_yn`, `del_dtm` | CHAR(1) NOT NULL DEFAULT N / DATETIME(6) NULL, 논리 삭제 여부와 시각 |

총 14개 컬럼이다. `(mi_event_id, checked_at)` 조회 인덱스와 적용 Snapshot FK용 인덱스를 둔다.
`expires_at = checked_at + event_verification_reuse_ttl_sec`이며 기본 1800초(30분)다. 시각은 UTC로 저장한다.
검증 배치의 모든 결과는 한 transaction으로 저장하며 실패 시 ID를 반환하지 않는다.
업데이트 시작 시 Event ID·del_yn·적용 여부·만료·Event hash를 확인한다. 저장 transaction에서는 검증 행을
FOR UPDATE로 먼저 잠근 다음 Event를 잠그고 만료·hash를 재확인한다. 동일 verificationId 재적용은
409/EVENT_VERIFICATION_ALREADY_APPLIED와 기존 Snapshot ID를 반환한다. 만료는 409/EVENT_VERIFICATION_EXPIRED다.
적용 Snapshot ID와 수정 actor는 Snapshot INSERT·Event UPDATE와 함께 커밋되며, 어느 저장이든 실패하면 모두 롤백한다.
미변경/생략에는 적용 표시를 하지 않는다. 만료 행은 자동 삭제하지 않으며, 런타임 DDL도 실행하지 않는다.

### 검증 기반 Event UPDATE와 변경 전 Snapshot

`POST /events/{miEventId}/verification-updates`는 저장된 검증 근거로 수정안을 생성하고 재검증이 공개 기준 pass이면
(6개 항목 비교 완료, 최소 한 항목 일치, contradicted/outdated 없음; 주의·일부 미확인은 허용)
`tmm_mi_mievent_snapshot_m`에 **UPDATE 직전 값**을 INSERT한 후 `tmm_mi_mievent_m`을 UPDATE한다.
저장 유스케이스는 `apps/persistence/event/service.py`, SQL은 `update_repository.py`가 소유한다.
이 API에 한해 Agent가 Snapshot을 직접 생성한다. 기존 ingestion Snapshot 생성 경로는 계속 사용한다.

| Snapshot 컬럼 | 생성 규칙 |
| --- | --- |
| `mi_event_snapshot_id` | DB AUTO_INCREMENT |
| `mi_event_id` | 잠근 현재 Event ID |
| `snapshot_version_no` | 해당 Event의 최대 기존 버전 + 1, 없거나 기존 버전이 모두 null이면 1 |
| `previous_mi_event_snapshot_id` | 해당 Event의 직전 Snapshot ID, 없으면 null. 삭제된 이력도 버전 계산에서 제외하지 않음 |
| `crt_usr_logn_id`, `mod_usr_logn_id` | 요청 actor |
| `crt_dtm`, `mod_dtm`, `del_yn` | INSERT에서 생략하고 DB 기본값 사용 |
| `update_trigger_cd` | `LLM_VALIDATION_UPDATE` |
| `update_reason` | 검증 기준 시각·수정 이유·전후 값 해시·출처 URL·근거 발췌·수정안 검증 등급·남은 주의 사유 JSON 문자열 |
| `changed_fields_json` | 최초 Snapshot은 [], 이후 실제 변경 본문 컬럼명 배열 |
| `event_del_yn` | 변경 전 Event의 `del_yn` |
| `event_crt_*`, `event_mod_*` | 변경 전 Event의 `crt_*`, `mod_*` |
| 본문·분류·상태·발생일·Record 시각 등 나머지 동명 컬럼 | 변경 전 Event에서 그대로 복사 |

Agent 조회 ORM은 DB 전체 컬럼의 부분집합이므로 두 테이블을 reflection하여 복사한다. v0046에서 추가된
`event_revision`, `summary_json`, 게시·검색 관련 확장 컬럼도 Snapshot에 동명 컬럼이 있으면 원본 그대로 보존한다.
현재 관리 저장소의 v0047 이후 스키마를 기준으로 `one_line_summary`는 표시 제목, `search_text`는 검색 요약이다.
제거된 `event_title`은 수정 대상에 포함하지 않는다. Event와 Snapshot 양쪽의 `search_text` 컬럼이 필수다.
수정 가능한 컬럼은 명시적 allowlist로 제한한다. 필수 감사 컬럼이나 수정 컬럼의 Snapshot 보존 컬럼이 없으면
schema 오류로 중단하며 런타임 DDL이나 임의 데이터 보완은 수행하지 않는다. migration 정본은 관리 저장소다.

동일 transaction에서 Event를 `SELECT ... FOR UPDATE`로 잠근 뒤 조회 때의 전체 row hash를 비교한다.
일치할 때만 버전·직전 ID를 배정하고 Snapshot INSERT, Event UPDATE를 수행한다. 모든 Snapshot 작성자는
동일 Event row lock 순서를 따라야 하며 unique 충돌을 포함한 저장 실패는 전체 롤백한다.
Event의 `mod_usr_logn_id`와 `mod_dtm`을 명시적으로 갱신하고 `new_yn=N`, 존재하는 `event_revision`은 +1 한다.
본문 변경 내역에는 이러한 감사·리비전 컬럼을 포함하지 않는다. 무변경 요청에는 Snapshot을 만들지 않는다.

변경 전 Snapshot은 신규 Scenario 생성의 현재 입력으로 선택하지 않는다. `fetch_latest_snapshot_id`는 현재
Event 수정 시각과 일치하는 ingestion Snapshot만 선택하며 없으면 기존 live fallback을 사용한다.
이미 Snapshot ID가 고정된 Scenario의 참조는 유지한다. Snapshot ID가 없는 기존 Scenario의 live fallback은
기존 동작을 따르므로 과거 입력 고정을 보장하지 않는다.

### Dimension Template과 Impact Lever

| Table | 역할 |
| --- | --- |
| `tmm_mi_scenario_dimension_template_m` | legacy v1~v3 Event Type별 Dimension Template |
| `tmm_mi_model_impact_lever_m` | v4 LNG 영향 Lever catalog와 model parameter binding |

v4는 `lever_code`, domain, 설명, 적용 기준, `parameter_bindings`, catalog version을 사용한다. 0030 이후 identity는
`(catalog_version, lever_code)`이며 domain index와 parent self-FK도 catalog version을 함께 사용한다. v4 create는
설정의 `scenario_group_v4_impact_catalog_version`(현재 신규 Group은 `v4.1`), `use_yn='Y'`, `del_yn='N'`을
명시적으로 조회하고 그 checksum을 Group에 pin한다. v4.1의 `route_disruption`, `trade_restriction`과
`price_only` Lever는 conditional binding이 있어 Model Parameter 근거 판정 후보가 될 수 있다. unknown Parameter
binding이나 version 혼합은 계약 오류로 fail-close한다.
Additional Dimension 생성과 Presentation label enrichment도 Group의 `impact_catalog_version`과
`impact_catalog_checksum`을 한 쌍으로 검증한다. 같은 version 문자열이라도 checksum이 다르면 현재 catalog 의미를
과거 Group에 소급하지 않는다.

## 2. Scenario Group

### `tmm_mi_scenario_group_m`

Scenario Group의 master다.

| 컬럼 | 역할 |
| --- | --- |
| `scenario_group_id` | Group 식별자 |
| `request_usr_id` | 소유 사용자 |
| `title`, `summary`, `description` | 사용자 표시 메타데이터 |
| `dimension_selected` | table header 순서의 Dimension ID 배열 |
| `scenario_count` | 활성 Scenario 수 |
| `status`, `stage` | 업무 상태와 단계 |
| `api_version`, `generation_strategy` | 생성 엔진 계약 |
| `event_set_hash` | 순서와 무관한 Event 조합 식별 정보; 동일 조합의 새 그룹 생성을 차단하지 않음 |
| `impact_catalog_version`, `impact_catalog_checksum` | v4 Lever catalog snapshot 식별자 |
| `template_checksum` | legacy Template 호환 정보 |
| `dimension_definitions` | Dimension·Value 정의 JSON |
| `generation_diagnostics` | v4 분석·lineage·경고·Additional Dimension lifecycle JSON |
| `parameter_mapping_ready` | mapping proposal 승인 준비 상태 |
| `del_yn` | soft delete |

master에는 대표 `mi_event_id`, `event_type_l2_id`를 두지 않는다. 단일 Event 호환 필드는 활성 Event 관계가
정확히 하나일 때 API projection에서만 계산한다.

### `tmm_mi_scenario_group_event_m`

Scenario Group과 Event의 N:M 관계이자 Event lineage 정본이다.

| 컬럼 | 역할 |
| --- | --- |
| `scenario_group_event_id` | 관계 식별자 |
| `scenario_group_id`, `mi_event_id` | Group·Event FK |
| `event_type_l2_id` | 생성 시점 Event Type lineage |
| `scenario_dimension_template_id`, `template_checksum` | legacy Template lineage |
| `display_order` | 요청 Event 표시 순서 |

같은 Group 안의 Event는 중복될 수 없다(`scenario_group_id`, `mi_event_id` 유일성). 같은 Event 또는 Event
조합을 여러 Group에 연결할 수 있으며, 기존 Group의 소유자나 operation 상태에 관계없이 새 Group을 생성한다.

## 3. Scenario와 Signpost

### `tmm_mi_scenario_m`

| 컬럼 | 역할 |
| --- | --- |
| `scenario_id`, `scenario_group_id` | Scenario와 소속 Group |
| `title`, `narrative`, `display_order` | 사용자 표시 내용과 순서 |
| `status` | `creating | created | realized | discarded` |
| `dimension_values` | `{dimensionId: valueId}` 의미의 JSON |
| `probability_score`, `probability_delta` | 현재 확률과 증감 |
| `baseline_yn` | 기준 Scenario 여부 `Y|N` |
| `global_pressure_band` | DB 호환명으로 저장하는 JKM pressure band |
| `scenario_role` | floor, ceiling, mixed 등 생성 역할 |
| `global_pressure_rationale` | JKM pressure 근거 |
| `related_markets` | 선택적인 TTF·HH 보조 근거 JSON |
| `del_yn` | soft delete |

public API의 `pressureBand`, `pressureRationale`은 persistence adapter가 DB 호환 컬럼명에서 변환한다.
`impact_jkm`, `impact_ttf`, `impact_hh`는 legacy 컬럼이며 신규 생성은 가격 방향을 쓰지 않고 `NULL`을 유지한다.

### `tmm_mi_signpost_m`

Scenario별 관측 신호다. 주요 컬럼은 `label`, `probability_direction_code`, `strength`,
`probability_impact_score`, `signpost_reason`, `keyword_hints`, `display_order`, `use_yn`, `del_yn`이다.

Signpost 재생성이 필요한 Scenario의 기존 row는 soft delete하고 새 결과를 저장한다. hard delete는 로컬 관리
경로에서만 허용한다.

## 4. Operation과 SSE event

### `tmm_mi_scenario_group_operation_m`

create, validation, signpost, confirmation, quality_evaluation 작업의 master다.

| 컬럼 | 역할 |
| --- | --- |
| `operation_id` | 26자리 ULID |
| `scenario_group_id`, `operation_type`, `engine_version` | 작업 대상과 종류 |
| `status`, `current_phase` | 실행 상태와 phase |
| `retry_summary` | 단계별 재시도 요약 |
| `presentation_snapshot` | 검증 완료된 중간 Presentation projection |
| `result_payload` | Validation 결과·Change Set 같은 내부 terminal payload |
| `snapshot_revision`, `latest_sequence` | 화면 revision과 SSE cursor |
| `last_error`, `mlflow_trace_id` | 오류·추적 정보 |
| `started_at`, `completed_at`, `heartbeat_at` | 실행 수명 정보 |

operation status는 `queued | running | succeeded | failed | interrupted`다. `result_payload`는 내부 정본이며
Scenario Group 상세나 Presentation에 자동 병합하지 않는다.

### `tmm_mi_scenario_group_operation_event_h`

operation별 append-only SSE history다. `(operation_id, sequence)`는 유일하며 sequence는 1부터 증가한다.
`event_type`, `phase`, 사용자용 `title`·`message_markdown`, 구조화 `payload`, `snapshot_revision`, trace ID를
저장한다.

Scenario Group, create operation, 첫 `accepted` event는 같은 transaction으로 생성한다. 검증된 중간 projection과
`section_ready`도 같은 transaction에서 revision을 맞춘다.

## 5. Dimension value mapping

`tmm_mi_scenario_quality_eval_m`은 평가 operation과 operation_id PK/FK로 연결되는 1:1 상세다.
requestId UUID는 전역 unique이며 입력 snapshot/hash, prompt version, 점수·위반 JSON, 모델 사용량을 저장한다.
실행 상태·heartbeat·오류는 operation이 소유한다. 상세: [품질 평가](07_SCENARIO_QUALITY_EVALUATION.md).
Signpost 전 WARN/FAIL 자동 수정은 최초 평가 완료와 재평가 접수를 같은 transaction으로 묶는다.
수정 전후 평가 상세는 별도 행으로 유지하고, 기존 operation의 retry_summary.qualityRepair에 부모/후속 ID와
1회 제한 및 수정 내역을 기록한다. 수정 적용·새 Validation acceptance·재평가 입력 갱신도 함께 commit한다.
전용 Scenario snapshot 테이블이나 새 컬럼은 추가하지 않는다.

`tmm_mi_dimension_value_mapping_m`은 legacy v2/v3 자유값을 model parameter source에 연결하는 proposal과
승인 상태를 저장한다. 주요 값은 `dimension_value_id`, `dimension_id`, `display_value`,
`source_projections`, `mapping_proposal`, `mapping_version`, `status`다.

v4 closed enum Dimension과 `leverStates`는 이 자유값 mapping을 생성 경로의 정본으로 사용하지 않는다.

## 상태 전이

| 작업 | Group status | Group stage | Scenario status |
| --- | --- | --- | --- |
| create 완료 | `creating` | `scenario_created` | `creating` |
| Validation 통과 | `creating` | `scenario_validated` | `creating` |
| Validation 차단 | `creating` | `scenario_created` | `creating` |
| Signpost 완료 | `creating` | `signpost_created` | `created` |
| v4 direct Confirmation | `created` | `completed` | `created` |
| Signpost 후 Confirmation | `created` | `completed` | `created` |

## Transaction 경계

- Event 사전 웹 검증(`POST /events/verifications`): 기존 게시·미삭제 Event 조회 DTO를 읽고 세션을 닫은 뒤
  웹 검색·비교를 수행한다. 결과 저장·Event 수정·새 테이블·migration은 없으며 조회 시점의 `mod_dtm`을
  `sourceUpdatedAt`으로 반환한다. 실행 중 수정된 Event를 자동 재조회하거나 잠그지는 않는다.

- canonical create 접수: Group + Event 관계 + operation + `accepted`
- Presentation 중간 갱신: operation projection + revision + `section_ready`
- create 완료: Group/Scenario 일괄 저장 후 operation terminal event
- Validation 완료: Change Set 1회 적용 + application fingerprint 기록
- Signpost prepare: Validation/application fingerprint 재검사 + operation 생성
- v4 direct Confirmation: Validation/application fingerprint 재검사 + Signpost 0건 허용 + Group·Scenario 상태 변경
- Signpost 후 Confirmation: stale 검사 + Scenario·Signpost 변경 적용 + Group·Scenario 상태 변경
- soft delete: active operation 부재와 소유권 확인 후 Group 상태 변경

긴 LLM 호출 동안 DB row lock을 유지하지 않는다. prepare와 최종 apply에서 fingerprint 또는 row lock으로
동시 변경을 다시 확인한다.

## DB 변경 체크리스트

- migration은 관리 저장소에 먼저 정의하고 이 저장소 ORM·DTO를 함께 맞춘다.
- JSON shape 변경은 write, legacy read, Presentation, callback, manual runner를 함께 검토한다.
- Event lineage를 master 대표 컬럼으로 되돌리지 않는다.
- 신규 query는 공유 repository, 여러 repository 조합은 Agent service에 둔다.
- status/stage/check constraint와 API enum을 함께 검증한다.
- soft delete와 `includeDeleted` 의미를 명시한다.
