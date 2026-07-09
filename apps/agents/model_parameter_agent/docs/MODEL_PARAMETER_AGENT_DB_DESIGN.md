# 수급모델 파라미터 Agent DB 설계

- 작성일: 2026-07-01
- 기준 API: `MODEL_PARAMETER_AGENT_API_SPEC.md`
- 협의 방식:
  - Codex: `skmip-mi-agent`의 agent/API 맥락 기준 설계
  - mgmt Codex: `/Users/messiah/skg-mi/skmip-mi-agent-mgmt`의 ORM/Alembic/SQL 관리 관점 검토
  - Claude: 독립 DB/API 설계 리뷰

## 1. 결론

현 시점에서는 proposal/confirmation payload에 대해 정규화된 child table을 만들지 않고, runtime proposal table 1개를 둔다.

권장 runtime table:

```text
tmm_mi_model_param_proposal_m
```

이유:

- API가 `proposalParameters`, `confirmationParameters`를 전체 set 단위로 주고받는다.
- `values[]`의 slot axis 이름과 개수가 파라미터마다 다르다.
- 현재 요구는 proposal ID, scenario ID, status, callback 상태 기준 조회가 중심이다.
- value 내부 slot/value별 검색, 집계, 부분 수정 요구가 아직 없다.
- 정규화하면 parameter/value table을 만들더라도 slot axis는 결국 JSON 또는 EAV 형태가 되어 복잡도만 커진다.

따라서 `proposal_parameters`, `confirmation_parameters` JSON에는 API payload와 같은 camelCase 구조를 그대로 저장한다. 외부 payload에서 제외하기로 한 `unit`, `slot`, `slotKey`는 이 테이블의 기본 저장 구조에도 포함하지 않는다.

엑셀 매핑 기준정보는 runtime proposal payload와 성격이 다르므로 별도 기준 테이블 2개로 분리한다.

```text
tmm_mi_model_param_m
tmm_mi_model_param_dimension_map
```

`tmm_mi_model_param_m`은 `Parameter Excel Mapping` sheet를 대체하는 수급모델 파라미터 마스터이고, `tmm_mi_model_param_dimension_map`은 `Dimension Parameter Mapping` sheet를 대체하는 event type/dimension to model parameter 매핑이다. 현재 엑셀에서는 `canonical_parameter_name`과 `parameter_name`이 모두 동일하므로 DB에는 `parameter_name`만 둔다.

## 2. 테이블 역할

`tmm_mi_model_param_proposal_m`은 아래 흐름의 상태와 payload를 보관한다.

1. 제안 요청 수신 시 row 생성
2. 즉시 response로 `modelParamProposalId`, `status=PROCESSING` 반환
3. background 작업 완료 후 `proposal_parameters` 저장
4. callback 전송 상태 기록
5. confirmation API 수신 후 `confirmation_parameters` 저장

Proposal 생성 상태와 callback 전송 상태는 분리한다.

예:

- proposal 생성 성공, callback HTTP 실패: `status=PROPOSED`, `callback_status=FAILED`
- proposal 생성 실패, 실패 callback 전송 성공: `status=FAILED`, `callback_status=SUCCEEDED`

## 3. 컬럼 설계

| Column | Type | Null | Default | 설명 |
|---|---|---:|---|---|
| `model_param_proposal_id` | `INT UNSIGNED` | N | AI | PK. API의 `modelParamProposalId` |
| `scenario_id` | `INT UNSIGNED` | N |  | 요청 scenario ID |
| `scenario_group_id` | `INT UNSIGNED` | N |  | callback payload용 scenario group ID snapshot |
| `mi_event_id` | `INT UNSIGNED` | N |  | callback payload의 `eventId` |
| `request_usr_id` | `INT UNSIGNED` | Y | `NULL` | 요청 사용자 ID. 인증 연동 전까지 nullable |
| `status` | `VARCHAR(50) COLLATE utf8mb4_bin` | N | `'PROCESSING'` | proposal 상태 |
| `proposal_parameters` | `JSON` | Y | `NULL` | Backend 재조회 및 confirmation 입력 기준이 되는 `proposalParameters` 전체 array |
| `confirmation_parameters` | `JSON` | Y | `NULL` | confirmation API로 받은 `confirmationParameters` 전체 array |
| `proposal_completed_dtm` | `DATETIME(6)` | Y | `NULL` | `PROPOSED` 또는 `FAILED` 전이 시각 |
| `confirmed_dtm` | `DATETIME(6)` | Y | `NULL` | `CONFIRMED` 전이 시각 |
| `error_code` | `VARCHAR(100) COLLATE utf8mb4_bin` | Y | `NULL` | 실패 코드. 내부 표준화 후 사용 |
| `error_message` | `TEXT COLLATE utf8mb4_bin` | Y | `NULL` | 실패 메시지 또는 요약 |
| `callback_status` | `VARCHAR(50) COLLATE utf8mb4_bin` | N | `'PENDING'` | callback 전송 상태 |
| `callback_sent_dtm` | `DATETIME(6)` | Y | `NULL` | 마지막 callback 성공 시각 |
| `crt_usr_logn_id` | `VARCHAR(100) COLLATE utf8mb4_bin` | N | `'system'` | 생성자 |
| `crt_dtm` | `DATETIME(6)` | N | `CURRENT_TIMESTAMP(6)` | 생성일시 |
| `mod_usr_logn_id` | `VARCHAR(100) COLLATE utf8mb4_bin` | N | `'system'` | 수정자 |
| `mod_dtm` | `DATETIME(6)` | N | `CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6)` | 수정일시 |
| `del_yn` | `CHAR(1) COLLATE utf8mb4_bin` | N | `'N'` | 삭제여부 |

`event_type_l2_id`는 기본 컬럼에 넣지 않는다. 이벤트 유형별 조회가 필요하면 `scenario_group_id` 또는 `mi_event_id`를 통해 join한다. 운영 조회 성능 요구가 확인되면 optional 컬럼으로 추가한다.

Audit 사용자 ID 저장 규칙:

- proposal 요청의 `userId`는 `request_usr_id`, `crt_usr_logn_id`, 초기 `mod_usr_logn_id`에 저장한다.
- confirmation 요청의 `userId`는 `mod_usr_logn_id`에 저장한다.
- proposal `userId`가 없으면 `request_usr_id`는 `NULL`, audit user 컬럼은 기본값 `system`을 사용한다.

## 4. 상태값

### 4.1 Proposal status

| Status | 의미 |
|---|---|
| `PROCESSING` | 요청 접수 후 background 생성 중 |
| `PROPOSED` | 유효한 proposal parameter가 1개 이상 생성됨 |
| `CONFIRMED` | 사용자가 confirmation API로 확정 완료. 재호출 시 최종 확정값을 overwrite |
| `FAILED` | proposal 생성/저장 실패 또는 유효한 proposal parameter 없음 |

전이:

```text
PROCESSING -> PROPOSED
PROCESSING -> FAILED
PROPOSED -> CONFIRMED
CONFIRMED -> CONFIRMED  # confirmation_parameters overwrite
```

`FAILED`는 terminal 상태로 둔다. `CONFIRMED`는 재확정 요청을 허용하며, 같은 row의
`confirmation_parameters`, `confirmed_dtm`, `mod_usr_logn_id`를 새 요청 기준으로 갱신한다.

### 4.2 Callback status

| Status | 의미 |
|---|---|
| `PENDING` | 아직 callback 전송 전 |
| `SUCCEEDED` | callback endpoint가 성공 응답 반환 |
| `FAILED` | 마지막 callback 전송 실패. 재시도 가능 |
| `SKIPPED` | 설정 또는 운영 판단으로 callback 미전송 |

callback URL 자체는 row에 저장하지 않고 운영 설정으로 관리한다. scenario group agent처럼 `callbackBaseUrl + callbackPath` 조합을 따른다.

## 5. 제약 조건과 인덱스

### 5.1 Foreign key

| Constraint | Column | Reference | On delete |
|---|---|---|---|
| `fk_tmm_mi_model_param_proposal_m_01` | `scenario_id` | `tmm_mi_scenario_m.scenario_id` | `RESTRICT` |
| `fk_tmm_mi_model_param_proposal_m_02` | `scenario_group_id` | `tmm_mi_scenario_group_m.scenario_group_id` | `RESTRICT` |
| `fk_tmm_mi_model_param_proposal_m_03` | `mi_event_id` | `tmm_mi_mievent_m.mi_event_id` | `RESTRICT` |

proposal은 사용자 확정 이력을 포함할 수 있으므로 `ON DELETE CASCADE`는 적용하지 않는다. scenario, scenario group, event를 hard delete하려면 proposal row를 먼저 soft delete 또는 별도 이관한 뒤 처리한다.

### 5.2 Check constraint

| Constraint | 조건 |
|---|---|
| `ck_tmm_mi_model_param_proposal_m_01` | `status IN ('PROCESSING','PROPOSED','CONFIRMED','FAILED')` |
| `ck_tmm_mi_model_param_proposal_m_02` | `callback_status IN ('PENDING','SUCCEEDED','FAILED','SKIPPED')` |
| `ck_tmm_mi_model_param_proposal_m_03` | `proposal_parameters IS NULL OR JSON_TYPE(proposal_parameters) = 'ARRAY'` |
| `ck_tmm_mi_model_param_proposal_m_04` | `confirmation_parameters IS NULL OR JSON_TYPE(confirmation_parameters) = 'ARRAY'` |

JSON 내부 구조 검증은 DB가 아니라 Pydantic/application layer에서 수행한다.

검증 대상:

- `proposalParameters[]`, `confirmationParameters[]` item shape
- `modelTarget.valueFieldNames` array
- `modelTarget.slotAxesFieldNames` array
- `values[]`의 slot axis key가 `basecaseValue`, `proposedValue`, `rationale`와 충돌하지 않는지
- 동일 parameter/slot 중복 또는 충돌 여부

### 5.3 Index

| Index | Columns | 목적 |
|---|---|---|
| `idx_tmm_mi_model_param_proposal_m_01` | `scenario_id`, `model_param_proposal_id` | scenario별 proposal 조회 |
| `idx_tmm_mi_model_param_proposal_m_02` | `status`, `model_param_proposal_id` | 처리 상태별 조회 |
| `idx_tmm_mi_model_param_proposal_m_03` | `callback_status`, `model_param_proposal_id` | callback 미전송/실패 대상 조회 |
| `idx_tmm_mi_model_param_proposal_m_04` | `scenario_group_id` | scenario group 기준 조회 |
| `idx_tmm_mi_model_param_proposal_m_05` | `mi_event_id` | event 기준 조회 |

unique constraint는 현재 두지 않는다. 같은 scenario에 대한 재요청이 새 proposal인지, 기존 PROCESSING row 재사용인지 아직 확정되지 않았다. 중복 방지는 우선 application layer에서 처리한다.

## 6. 저장 payload

`proposal_parameters`와 `confirmation_parameters`는 API payload와 같은 구조를 저장한다.

```json
[
  {
    "parameterName": "Temperature",
    "modelTarget": {
      "modelFile": "Demand",
      "modelSheet": "WeatherAdjustment",
      "valueFieldNames": ["Temperature"],
      "slotAxesFieldNames": ["Country", "Year", "Month"]
    },
    "rationale": "한파 강도가 기온 하락으로 직접 표현되므로 Temperature 조정 대상입니다.",
    "values": [
      {
        "Country": "Germany",
        "Year": 2027,
        "Month": 1,
        "basecaseValue": 1.2,
        "proposedValue": -3.8,
        "rationale": "Germany 2027년 1월 한파 영향을 반영해 제안값을 산정했습니다."
      }
    ]
  }
]
```

저장하지 않는 외부 제외 field:

- `unit`
- `slot`
- `slotKey`

내부 디버깅용으로 원본 rich state를 보존해야 한다면 `internal_metadata_json` 같은 별도 nullable JSON 컬럼을 추가할 수 있다. 다만 현재 최소 설계에서는 제외한다.

## 7. DDL 초안

아래 SQL은 설계 검토용 초안이다. 실제 반영은 `skmip-mi-agent-mgmt`의 ORM/Alembic/SQL snapshot 절차로 생성해야 한다.

```sql
CREATE TABLE `tmm_mi_model_param_proposal_m` (
    `model_param_proposal_id` INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '수급모델 파라미터 제안 ID',
    `scenario_id` INT UNSIGNED NOT NULL COMMENT '시나리오 ID',
    `scenario_group_id` INT UNSIGNED NOT NULL COMMENT '시나리오 그룹 ID',
    `mi_event_id` INT UNSIGNED NOT NULL COMMENT 'MI 이벤트 ID',
    `request_usr_id` INT UNSIGNED NULL COMMENT '요청자 사용자 ID',
    `status` VARCHAR(50) COLLATE utf8mb4_bin NOT NULL DEFAULT 'PROCESSING' COMMENT '상태 (PROCESSING/PROPOSED/CONFIRMED/FAILED)',
    `proposal_parameters` JSON NULL COMMENT '제안 파라미터 배열 JSON',
    `confirmation_parameters` JSON NULL COMMENT '확정 파라미터 배열 JSON',
    `proposal_completed_dtm` DATETIME(6) NULL COMMENT '제안 완료일시',
    `confirmed_dtm` DATETIME(6) NULL COMMENT '확정일시',
    `error_code` VARCHAR(100) COLLATE utf8mb4_bin NULL COMMENT '오류 코드',
    `error_message` TEXT COLLATE utf8mb4_bin NULL COMMENT '오류 메시지',
    `callback_status` VARCHAR(50) COLLATE utf8mb4_bin NOT NULL DEFAULT 'PENDING' COMMENT 'Callback 상태',
    `callback_sent_dtm` DATETIME(6) NULL COMMENT 'Callback 성공일시',

    `crt_usr_logn_id` VARCHAR(100) COLLATE utf8mb4_bin NOT NULL DEFAULT 'system' COMMENT '생성자',
    `crt_dtm` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) COMMENT '생성일시',
    `mod_usr_logn_id` VARCHAR(100) COLLATE utf8mb4_bin NOT NULL DEFAULT 'system' COMMENT '수정자',
    `mod_dtm` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6) COMMENT '수정일시',
    `del_yn` CHAR(1) COLLATE utf8mb4_bin NOT NULL DEFAULT 'N' COMMENT '삭제여부',

    PRIMARY KEY (`model_param_proposal_id`),
    KEY `idx_tmm_mi_model_param_proposal_m_01` (`scenario_id`, `model_param_proposal_id`),
    KEY `idx_tmm_mi_model_param_proposal_m_02` (`status`, `model_param_proposal_id`),
    KEY `idx_tmm_mi_model_param_proposal_m_03` (`callback_status`, `model_param_proposal_id`),
    KEY `idx_tmm_mi_model_param_proposal_m_04` (`scenario_group_id`),
    KEY `idx_tmm_mi_model_param_proposal_m_05` (`mi_event_id`),

    CONSTRAINT `ck_tmm_mi_model_param_proposal_m_01`
        CHECK (`status` IN ('PROCESSING','PROPOSED','CONFIRMED','FAILED')),
    CONSTRAINT `ck_tmm_mi_model_param_proposal_m_02`
        CHECK (`callback_status` IN ('PENDING','SUCCEEDED','FAILED','SKIPPED')),
    CONSTRAINT `ck_tmm_mi_model_param_proposal_m_03`
        CHECK (`proposal_parameters` IS NULL OR JSON_TYPE(`proposal_parameters`) = 'ARRAY'),
    CONSTRAINT `ck_tmm_mi_model_param_proposal_m_04`
        CHECK (`confirmation_parameters` IS NULL OR JSON_TYPE(`confirmation_parameters`) = 'ARRAY'),
    CONSTRAINT `fk_tmm_mi_model_param_proposal_m_01`
        FOREIGN KEY (`scenario_id`)
        REFERENCES `tmm_mi_scenario_m` (`scenario_id`),
    CONSTRAINT `fk_tmm_mi_model_param_proposal_m_02`
        FOREIGN KEY (`scenario_group_id`)
        REFERENCES `tmm_mi_scenario_group_m` (`scenario_group_id`),
    CONSTRAINT `fk_tmm_mi_model_param_proposal_m_03`
        FOREIGN KEY (`mi_event_id`)
        REFERENCES `tmm_mi_mievent_m` (`mi_event_id`)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_bin
  COMMENT='수급모델 파라미터 제안';
```

## 8. 엑셀 매핑 기준 테이블

두 기준 테이블은 현재 코드가 직접 읽는 아래 두 sheet를 DB화한다.

| Excel sheet | DB table | Row 수 | 역할 |
|---|---|---:|---|
| `Parameter Excel Mapping` | `tmm_mi_model_param_m` | 19 | 수급모델 parameter target, basecase read config |
| `Dimension Parameter Mapping` | `tmm_mi_model_param_dimension_map` | 128 | event type/dimension을 model parameter 후보로 연결 |

설계 원칙:

- `tmm_mi_model_param_m.parameter_name`은 현재 엑셀의 `canonical_parameter_name`과 동일하게 사용한다.
- `tmm_mi_model_param_dimension_map`은 `parameter_name` 문자열을 FK로 갖지 않고 `model_param_id`를 nullable FK로 갖는다.
- `Dimension Parameter Mapping`에는 모델 input 대상이 아닌 `indirect`, `na` row가 있으므로 `model_param_id`는 `NULL`을 허용한다.
- agent 후보 생성 시에는 map/master 모두 `use_yn='Y'`, `del_yn='N'`인 row만 사용한다. map이 `use_yn='Y'`이어도 연결된 `tmm_mi_model_param_m.use_yn='N'`이면 제외한다.
- 후보 parameter는 `mapping_method IN ('direct','routing')`, `model_param_id IS NOT NULL`인 row에서 생성한다.
- proposal payload에서 제외한 `unit`은 기준정보 성격의 `tmm_mi_model_param_m`에는 유지한다.

현재 엑셀 검증 결과:

- `Parameter Excel Mapping.parameter_name`: 19개 모두 unique
- `Parameter Excel Mapping.canonical_parameter_name == parameter_name`: 전체 true
- `Dimension Parameter Mapping.canonical_parameter_name` blank: 61개
- `Dimension Parameter Mapping.mapping_method IN ('direct','routing')`이면서 `canonical_parameter_name` blank: 1개
- `Dimension Parameter Mapping.event_type_l2_id + dimension_key`: 중복 46개 존재
- `Dimension Parameter Mapping.event_type_l2_id + dimension_key + canonical_parameter_name`: 중복 없음

`direct`인데 `model_param_id`가 없는 1개 row는 `event_type_l2_id=11`, `dimension_key=supply_disruption_intensity`이다. 이 row는 routing으로 선택된 시설 유형 parameter의 값 크기를 설명하는 dimension이며, 독립 model parameter 후보가 아니므로 `model_param_id=NULL`로 보존한다.

### 8.1 `tmm_mi_model_param_m`

| Column | Type | Null | Default | 설명 |
|---|---|---:|---|---|
| `model_param_id` | `INT UNSIGNED` | N | AI | PK |
| `use_yn` | `CHAR(1) COLLATE utf8mb4_bin` | N | `'Y'` | Excel `enabled` |
| `parameter_name` | `VARCHAR(150) COLLATE utf8mb4_bin` | N |  | 수급모델 parameter명. 현재 canonical name 역할 |
| `parameter_hint` | `TEXT COLLATE utf8mb4_bin` | N |  | parameter 산정/제약/참고 설명 |
| `model_file` | `VARCHAR(100) COLLATE utf8mb4_bin` | N |  | basecase workbook group |
| `model_sheet` | `VARCHAR(150) COLLATE utf8mb4_bin` | N |  | target sheet |
| `model_table` | `VARCHAR(50) COLLATE utf8mb4_bin` | N |  | model sheet 내 table 구분 |
| `unit` | `VARCHAR(100) COLLATE utf8mb4_bin` | Y | `NULL` | 기준정보용 단위 |
| `semantic_axes` | `TEXT COLLATE utf8mb4_bin` | Y | `NULL` | parameter 의미/축 설명 |
| `basecase_read_mode` | `VARCHAR(50) COLLATE utf8mb4_bin` | N |  | `fixed_columns`, `matrix_time_columns` |
| `basecase_header_row` | `SMALLINT UNSIGNED` | N |  | header row |
| `basecase_data_start_row` | `SMALLINT UNSIGNED` | N |  | data start row |
| `basecase_column_roles` | `VARCHAR(1000) COLLATE utf8mb4_bin` | N |  | column role mapping string |
| `basecase_row_filter` | `VARCHAR(200) COLLATE utf8mb4_bin` | Y | `NULL` | row filter string |
| `basecase_year_row` | `SMALLINT UNSIGNED` | Y | `NULL` | matrix year row |
| `basecase_month_row` | `SMALLINT UNSIGNED` | Y | `NULL` | matrix month row |
| `basecase_period_row` | `SMALLINT UNSIGNED` | Y | `NULL` | matrix period row |
| `basecase_value_start_col` | `VARCHAR(10) COLLATE utf8mb4_bin` | Y | `NULL` | matrix value start col |
| `basecase_value_end_col` | `VARCHAR(10) COLLATE utf8mb4_bin` | Y | `NULL` | matrix value end col |
| `basecase_stop_rule` | `VARCHAR(100) COLLATE utf8mb4_bin` | N |  | scan stop rule |
| `crt_usr_logn_id` | `VARCHAR(100) COLLATE utf8mb4_bin` | N | `'system'` | 생성자 |
| `crt_dtm` | `DATETIME(6)` | N | `CURRENT_TIMESTAMP(6)` | 생성일시 |
| `mod_usr_logn_id` | `VARCHAR(100) COLLATE utf8mb4_bin` | N | `'system'` | 수정자 |
| `mod_dtm` | `DATETIME(6)` | N | `CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6)` | 수정일시 |
| `del_yn` | `CHAR(1) COLLATE utf8mb4_bin` | N | `'N'` | 삭제여부 |

제약/인덱스:

| Type | Name | Columns/Condition |
|---|---|---|
| PK | `pk_tmm_mi_model_param_m` | `model_param_id` |
| UK | `uk_tmm_mi_model_param_m_01` | `parameter_name` |
| IDX | `idx_tmm_mi_model_param_m_01` | `model_file`, `model_sheet` |
| CHECK | `ck_tmm_mi_model_param_m_01` | `use_yn IN ('Y','N')` |
| CHECK | `ck_tmm_mi_model_param_m_02` | `del_yn IN ('Y','N')` |
| CHECK | `ck_tmm_mi_model_param_m_03` | `basecase_read_mode IN ('fixed_columns','matrix_time_columns')` |

### 8.2 `tmm_mi_model_param_dimension_map`

| Column | Type | Null | Default | 설명 |
|---|---|---:|---|---|
| `model_param_dimension_map_id` | `INT UNSIGNED` | N | AI | PK |
| `use_yn` | `CHAR(1) COLLATE utf8mb4_bin` | N | `'Y'` | Excel `enabled` |
| `event_type_l2_id` | `INT UNSIGNED` | N |  | event type L2 FK |
| `dimension_key` | `VARCHAR(150) COLLATE utf8mb4_bin` | N |  | scenario dimension key |
| `dimension_label` | `VARCHAR(200) COLLATE utf8mb4_bin` | N |  | scenario dimension label |
| `mapping_method` | `VARCHAR(50) COLLATE utf8mb4_bin` | N |  | `direct`, `routing`, `indirect`, `na` |
| `model_param_id` | `INT UNSIGNED` | Y | `NULL` | model parameter FK. non-input row는 `NULL` |
| `comment` | `TEXT COLLATE utf8mb4_bin` | Y | `NULL` | 매핑 설명 |
| `crt_usr_logn_id` | `VARCHAR(100) COLLATE utf8mb4_bin` | N | `'system'` | 생성자 |
| `crt_dtm` | `DATETIME(6)` | N | `CURRENT_TIMESTAMP(6)` | 생성일시 |
| `mod_usr_logn_id` | `VARCHAR(100) COLLATE utf8mb4_bin` | N | `'system'` | 수정자 |
| `mod_dtm` | `DATETIME(6)` | N | `CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6)` | 수정일시 |
| `del_yn` | `CHAR(1) COLLATE utf8mb4_bin` | N | `'N'` | 삭제여부 |

제약/인덱스:

| Type | Name | Columns/Condition |
|---|---|---|
| PK | `pk_tmm_mi_model_param_dimension_map` | `model_param_dimension_map_id` |
| UK | `uk_tmm_mi_model_param_dimension_map_01` | `event_type_l2_id`, `dimension_key`, `model_param_id` |
| IDX | `idx_tmm_mi_model_param_dimension_map_01` | `event_type_l2_id`, `dimension_key` |
| IDX | `idx_tmm_mi_model_param_dimension_map_02` | `model_param_id` |
| FK | `fk_tmm_mi_model_param_dimension_map_01` | `event_type_l2_id` -> `tmm_mi_event_type_l2_m.event_type_l2_id` |
| FK | `fk_tmm_mi_model_param_dimension_map_02` | `model_param_id` -> `tmm_mi_model_param_m.model_param_id` |
| CHECK | `ck_tmm_mi_model_param_dimension_map_01` | `use_yn IN ('Y','N')` |
| CHECK | `ck_tmm_mi_model_param_dimension_map_02` | `del_yn IN ('Y','N')` |
| CHECK | `ck_tmm_mi_model_param_dimension_map_03` | `mapping_method IN ('direct','indirect','routing','na')` |

`uk_tmm_mi_model_param_dimension_map_01`은 동일 event/dimension이 여러 parameter로 확장되는 것은 허용하고, 동일 parameter로 중복 적재되는 것만 막는다. MySQL unique index는 `NULL`을 중복으로 보지 않으므로, `model_param_id IS NULL`인 indirect/na row의 중복 방지는 seed의 명시 PK 또는 application layer에서 관리한다.

### 8.3 DDL 초안

```sql
CREATE TABLE `tmm_mi_model_param_m` (
    `model_param_id` INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '수급모델 파라미터 ID',
    `use_yn` CHAR(1) COLLATE utf8mb4_bin NOT NULL DEFAULT 'Y' COMMENT '사용 여부',
    `parameter_name` VARCHAR(150) COLLATE utf8mb4_bin NOT NULL COMMENT '수급모델 파라미터명',
    `parameter_hint` TEXT COLLATE utf8mb4_bin NOT NULL COMMENT '수급모델 파라미터 설명',
    `model_file` VARCHAR(100) COLLATE utf8mb4_bin NOT NULL COMMENT '모델 파일 구분',
    `model_sheet` VARCHAR(150) COLLATE utf8mb4_bin NOT NULL COMMENT '모델 시트명',
    `model_table` VARCHAR(50) COLLATE utf8mb4_bin NOT NULL COMMENT '모델 시트 내 테이블명',
    `unit` VARCHAR(100) COLLATE utf8mb4_bin NULL COMMENT '단위',
    `semantic_axes` TEXT COLLATE utf8mb4_bin NULL COMMENT '의미 축 설명',
    `basecase_read_mode` VARCHAR(50) COLLATE utf8mb4_bin NOT NULL COMMENT 'Basecase 읽기 방식',
    `basecase_header_row` SMALLINT UNSIGNED NOT NULL COMMENT 'Basecase header row',
    `basecase_data_start_row` SMALLINT UNSIGNED NOT NULL COMMENT 'Basecase data start row',
    `basecase_column_roles` VARCHAR(1000) COLLATE utf8mb4_bin NOT NULL COMMENT 'Basecase column role mapping',
    `basecase_row_filter` VARCHAR(200) COLLATE utf8mb4_bin NULL COMMENT 'Basecase row filter',
    `basecase_year_row` SMALLINT UNSIGNED NULL COMMENT 'Basecase year row',
    `basecase_month_row` SMALLINT UNSIGNED NULL COMMENT 'Basecase month row',
    `basecase_period_row` SMALLINT UNSIGNED NULL COMMENT 'Basecase period row',
    `basecase_value_start_col` VARCHAR(10) COLLATE utf8mb4_bin NULL COMMENT 'Basecase value start column',
    `basecase_value_end_col` VARCHAR(10) COLLATE utf8mb4_bin NULL COMMENT 'Basecase value end column',
    `basecase_stop_rule` VARCHAR(100) COLLATE utf8mb4_bin NOT NULL COMMENT 'Basecase scan stop rule',

    `crt_usr_logn_id` VARCHAR(100) COLLATE utf8mb4_bin NOT NULL DEFAULT 'system' COMMENT '생성자',
    `crt_dtm` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) COMMENT '생성일시',
    `mod_usr_logn_id` VARCHAR(100) COLLATE utf8mb4_bin NOT NULL DEFAULT 'system' COMMENT '수정자',
    `mod_dtm` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6) COMMENT '수정일시',
    `del_yn` CHAR(1) COLLATE utf8mb4_bin NOT NULL DEFAULT 'N' COMMENT '삭제여부',

    PRIMARY KEY (`model_param_id`),
    UNIQUE KEY `uk_tmm_mi_model_param_m_01` (`parameter_name`),
    KEY `idx_tmm_mi_model_param_m_01` (`model_file`, `model_sheet`),
    CONSTRAINT `ck_tmm_mi_model_param_m_01` CHECK (`use_yn` IN ('Y','N')),
    CONSTRAINT `ck_tmm_mi_model_param_m_02` CHECK (`del_yn` IN ('Y','N')),
    CONSTRAINT `ck_tmm_mi_model_param_m_03` CHECK (`basecase_read_mode` IN ('fixed_columns','matrix_time_columns'))
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_bin
  COMMENT='수급모델 파라미터 마스터';

CREATE TABLE `tmm_mi_model_param_dimension_map` (
    `model_param_dimension_map_id` INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '수급모델 파라미터 dimension 매핑 ID',
    `use_yn` CHAR(1) COLLATE utf8mb4_bin NOT NULL DEFAULT 'Y' COMMENT '사용 여부',
    `event_type_l2_id` INT UNSIGNED NOT NULL COMMENT '이벤트 유형 L2 ID',
    `dimension_key` VARCHAR(150) COLLATE utf8mb4_bin NOT NULL COMMENT '시나리오 dimension key',
    `dimension_label` VARCHAR(200) COLLATE utf8mb4_bin NOT NULL COMMENT '시나리오 dimension label',
    `mapping_method` VARCHAR(50) COLLATE utf8mb4_bin NOT NULL COMMENT '매핑 방식',
    `model_param_id` INT UNSIGNED NULL COMMENT '수급모델 파라미터 ID',
    `comment` TEXT COLLATE utf8mb4_bin NULL COMMENT '매핑 설명',

    `crt_usr_logn_id` VARCHAR(100) COLLATE utf8mb4_bin NOT NULL DEFAULT 'system' COMMENT '생성자',
    `crt_dtm` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) COMMENT '생성일시',
    `mod_usr_logn_id` VARCHAR(100) COLLATE utf8mb4_bin NOT NULL DEFAULT 'system' COMMENT '수정자',
    `mod_dtm` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6) COMMENT '수정일시',
    `del_yn` CHAR(1) COLLATE utf8mb4_bin NOT NULL DEFAULT 'N' COMMENT '삭제여부',

    PRIMARY KEY (`model_param_dimension_map_id`),
    UNIQUE KEY `uk_tmm_mi_model_param_dimension_map_01` (`event_type_l2_id`, `dimension_key`, `model_param_id`),
    KEY `idx_tmm_mi_model_param_dimension_map_01` (`event_type_l2_id`, `dimension_key`),
    KEY `idx_tmm_mi_model_param_dimension_map_02` (`model_param_id`),
    CONSTRAINT `ck_tmm_mi_model_param_dimension_map_01` CHECK (`use_yn` IN ('Y','N')),
    CONSTRAINT `ck_tmm_mi_model_param_dimension_map_02` CHECK (`del_yn` IN ('Y','N')),
    CONSTRAINT `ck_tmm_mi_model_param_dimension_map_03` CHECK (`mapping_method` IN ('direct','indirect','routing','na')),
    CONSTRAINT `fk_tmm_mi_model_param_dimension_map_01`
        FOREIGN KEY (`event_type_l2_id`)
        REFERENCES `tmm_mi_event_type_l2_m` (`event_type_l2_id`)
        ON DELETE RESTRICT,
    CONSTRAINT `fk_tmm_mi_model_param_dimension_map_02`
        FOREIGN KEY (`model_param_id`)
        REFERENCES `tmm_mi_model_param_m` (`model_param_id`)
        ON DELETE RESTRICT
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_bin
  COMMENT='수급모델 파라미터 dimension 매핑';
```

## 9. 엑셀 기준 seed 데이터

엑셀 기준 seed insert query는 운영 DB/mgmt repo 반영 흐름에서 관리한다.
agent repo에는 재실행용 seed SQL을 별도로 보관하지 않는다.

seed 기준:

- source workbook: `apps/agents/model_parameter_agent/resources/mapping/260625_시나리오가정_MI수급모델_input_매핑_vfShare_agent.xlsx`
- source sheets: `Parameter Excel Mapping`, `Dimension Parameter Mapping`
- `tmm_mi_model_param_m`: `parameter_name` unique 기준 upsert
- `tmm_mi_model_param_dimension_map`: `model_param_dimension_map_id`를 Excel row 순서 기준으로 명시해 재실행 가능하게 구성
- `model_param_id`: `parameter_name`으로 `tmm_mi_model_param_m`을 조회해 FK resolve
- `canonical_parameter_name` blank row: `model_param_id=NULL`

seed 적용 후 기대 검증값:

| Query | Expected |
|---|---:|
| `tmm_mi_model_param_m` active row count | 19 |
| `tmm_mi_model_param_dimension_map` active row count | 128 |
| `mapping_method IN ('direct','routing') AND model_param_id IS NULL` | 1 |

## 10. mgmt repo 반영 범위

실제 schema 반영은 `/Users/messiah/skg-mi/skmip-mi-agent-mgmt`에서 진행한다.

수정 필요 파일:

- `models/tables.py`: `MiModelParamProposalM`, `MiModelParamM`, `MiModelParamDimensionMap` ORM class 추가
- `models/base.py`: `MANAGED_TABLES`에 `tmm_mi_model_param_proposal_m`, `tmm_mi_model_param_m`, `tmm_mi_model_param_dimension_map` 추가
- `models/__init__.py`: 신규 class import/export
- `migrations/versions/0016_*.py`: Alembic migration 추가
- `sql/versions/0016/0016_01_schema_ddl.sql`: fresh build DDL
- `sql/versions/0016/0016_02_seed_data.sql`: 모델 파라미터 seed data를 mgmt SQL convention에 맞춰 반영
- `sql/versions/0016/0016_03_select_queries.sql`: 검증 조회
- `sql/versions/0016/0016_04_incremental_apply.sql`: 기존 DB 증분 적용 SQL
- `sql/versions/0016/0016_05_data_cleansing.sql`: 필요 시 data cleansing

검증 명령:

```bash
make db-up
poetry run alembic upgrade head
poetry run alembic check
ALEMBIC="poetry run alembic" ./scripts/gen_sql_snapshot.sh 0016
```

추가로 임시 DB에서 아래 두 경로를 각각 확인한다.

- `0016_01_schema_ddl.sql` fresh apply
- `0016_04_incremental_apply.sql` incremental apply

`make db-reset`은 MySQL volume을 삭제하므로 명시적 합의 없이는 사용하지 않는다.

## 11. agent repo 반영 범위

DB schema가 확정되면 `skmip-mi-agent`에서는 다음을 반영한다.

- model parameter proposal persistence model/repository/service 추가
- `POST /model-parameters/scenarios/{scenario_id}/proposals`
  - scenario context 조회
  - proposal row 생성
  - immediate response 반환
  - background task enqueue
- background proposal 생성 완료 시
  - `proposal_parameters` 저장
  - `status=PROPOSED` 또는 `FAILED` 전이
  - callback 전송 및 `callback_status` 갱신
- `POST /model-parameters/proposals/{modelParamProposalId}/confirmation`
  - proposal row 조회
  - `status=PROPOSED` 또는 `CONFIRMED`인지 검증
  - `confirmation_parameters` 저장
  - `status=CONFIRMED` 전이 또는 유지
- mapping 기준정보 DB 전환
  - `Parameter Excel Mapping` loader를 `tmm_mi_model_param_m` 조회로 대체
  - `Dimension Parameter Mapping` loader를 `tmm_mi_model_param_dimension_map` 조회로 대체
  - 초기 전환 기간에는 Excel loader와 DB loader 결과 row count 및 candidate set을 비교 검증

## 12. 확정 필요 사항

| 항목 | 권장안 | 확정 필요 내용 |
|---|---|---|
| 동일 scenario 재요청 | unique 없음, application layer에서 중복 PROCESSING 방지 | 새 proposal 생성인지 기존 row 재사용인지 |
| confirmation 재호출 | 허용 | 같은 row의 최종 `confirmation_parameters` overwrite |
| callback retry | `callback_status=FAILED` row를 worker가 재시도 | 재시도 횟수, backoff, 실패 사유는 로그/worker 정책으로 관리 |
| 내부 debug payload | 기본 제외 | rich state, prompt trace 보존 필요 여부 |
| event type 조회 | 기본 join 조회 | `event_type_l2_id` denormalized 컬럼 추가 여부 |
| payload 크기 제한 | application layer 제한 | parameter/value 최대 개수 |
| mapping seed 갱신 | 엑셀 기준 seed SQL 재생성 | 운영에서 수동 수정 허용 여부와 Excel/DB 중 source of truth |

## 13. 협의 결과 요약

mgmt Codex와 Claude 모두 proposal payload는 단일 runtime table의 JSON 컬럼에 저장하고, 엑셀 매핑 기준정보는 별도 기준 테이블로 분리하는 방향에 동의했다.

반영한 의견:

- Claude는 callback 재전송을 위해 callback 운영 컬럼을 분리하는 점을 강조했다.
- Claude는 `event_type_l2_id` FK, nullable `model_param_id` FK, `ON DELETE RESTRICT` 기준을 명시하는 것을 권고했다.
- Claude는 proposal payload에서 제외한 `unit`도 mapping master 기준정보에는 유지해야 한다고 지적했다.
- mgmt Codex는 `tmm_mi_model_param_m` + dimension map 구조와 `model_param_id` surrogate FK를 권고했다.
- mgmt Codex는 `MANAGED_TABLES`, ORM, Alembic, `sql/versions/<NNNN>` snapshot 동시 반영 누락을 가장 큰 구현 리스크로 보았다.

최종 설계에는 두 의견을 모두 반영했다.
