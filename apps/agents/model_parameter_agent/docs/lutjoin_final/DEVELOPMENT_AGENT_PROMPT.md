# Model Parameter LUT + Basecase 최종 통합 구현 요청

작업 저장소:
`/Users/messiah/skg-mi/skmip-mi-agent`

작업 기준 브랜치:
`design/model-param-lut-final-merge`

## 1. 작업 전 필독 자료

아래 문서를 처음부터 끝까지 읽고 구현 기준으로 삼아라.

1. `/Users/messiah/skg-mi/skmip-mi-agent/AGENTS.md`
2. `/Users/messiah/skg-mi/skmip-mi-agent/.claude/rules/python-conventions.md`
3. `/Users/messiah/skg-mi/skmip-mi-agent/docs/architectures/project_directory_structure.md`
4. 최종 의사결정 문서:
   `/Users/messiah/skg-mi/skmip-mi-agent/apps/agents/model_parameter_agent/docs/lutjoin_final/README.md`

최종 문서의 D-01~D-11과 테스트 게이트를 구현의 최우선 기준으로 사용하라.

비교·참고 브랜치:

- Codex: `feature/model-param-lut-basecase`, commit `7a7a753`
- Claude: `feat/lut-basecase-integration`, commit `8d1f72b`
- 공통 merge base: `main`, commit `7ba92b8`

비교 문서(현재 기준 브랜치에는 없으므로 아래 branch-qualified path에서 읽는다):

- Codex: `feature/model-param-lut-basecase:apps/agents/model_parameter_agent/docs/lutjoin/`
- Claude: `feat/lut-basecase-integration:apps/agents/model_parameter_agent/docs/lutjoin_claude/`

`git ls-tree -r --name-only <branch> -- <path>`로 비교 파일 목록을 확인하고 `git show <branch>:<file>`로 내용을 읽어라. 두 feature branch의 commit은 크기와 관계없이 merge/cherry-pick하지 마라. 현재 브랜치에서 `git show`와 `git diff`로 필요한 함수·테스트만 확인하고, 최종 문서 11장과 14.10의 선별 이식 기준에 맞춰 파일·함수·테스트 아이디어를 수동 재구현하라. 비교를 위해 다른 branch를 checkout하지 마라.

기존 사용자 변경과 미추적 파일을 보존하고 관련 없는 refactor, formatting, 파일 이동을 하지 마라. `review-node` skill은 사용하지 마라. OpenAI `reasoning_effort` 규격을 다시 확인해야 할 때는 `openai-docs` skill과 공식 OpenAI 문서만 사용하라.

## 2. 핵심 구조: pipeline은 하나다

LUT 활성 여부에 따라 별도 legacy flow나 별도 Step2/Step3 pipeline을 만들지 마라. LUT 여부는 초기 reference source만 바꾼다.

    lut_parameters.yaml
      -> flag와 무관하게 processing schema parse/구조 검증
      -> 등록 parameter는 YAML key_axes/metadata_axes 사용
      -> 미등록 parameter는 basecase/candidate canonical axes 전체를 key로 사용

    Basecase load
      +
    LUT source 결정
      - flag=false                         -> basecase-only
      - flag=true + YAML 미등록 parameter -> basecase-only
      - flag=true + YAML 등록·유효         -> basecase + LUT
      - flag=true + YAML 등록 오류         -> 명시적 실패
      |
      v
    동일 SlotCatalog builder
      -> 동일 Step2 prompt/cap/sanitizer
      -> 동일 exact membership validation
      -> 동일 EffectiveReferenceResolver
      -> 동일 Step3 prompt/cap/partial-cell policy
      -> 동일 API/DB projection

flag=false는 과거 node 체계로 우회하는 rollback switch가 아니다. LUT record를 source에서 제외할 뿐이다. proposal horizon, parameter별 cap, compact catalog, exact membership, nearest 금지, partial response, metadata 복원과 API/DB projection은 모든 source mode에서 동일하게 적용하라.

## 3. 확정 기능 요구사항

### Reference source와 exact key

- 대상 LUT parameter는 GDP, PMI, PowerMix, Temperature, LiqUtilAdjustment다.
- 5개 모두 scenario/event와 관련된 LUT-only slot을 허용한다.
- 동일 exact key에 basecase와 LUT가 모두 있으면 LLM 기준값은 actual basecase다.
- basecase-only는 유지하고 LUT-only는 LUT default를 LLM 기준값으로 사용한다.
- 활성 source 어디에도 exact key가 없으면 Step3 전에 제외한다.
- 가까운 연도·월·국가·Plant·Train으로 자동 치환하거나 nearest reference를 조회하지 마라.
- canonical business key:
  - GDP: `Country + Year`
  - PMI: `Country + Year + Month`
  - PowerMix: `Country + Year + Energy Source`
  - Temperature: `Country + Year + Month`
  - LiqUtilAdjustment: `Country + LNG Plant + LNG Plant Train + Year + Month`
- key는 candidate identity별로 격리하고 fuzzy prefix 추론 대신 YAML의 canonical axis와 CSV header 직접 mapping을 사용하라.
- YAML 미등록 parameter는 basecase/candidate schema의 canonical axis 전체를 exact key로 사용하고 `metadata_axes=[]`로 처리하라. 축 이름만으로 metadata를 추론하지 마라.

### Horizon

- `model_parameter_lut_horizon_start_year=2026`
- `model_parameter_lut_horizon_end_year=2030`
- basecase와 LUT의 proposal 후보에 같은 2026~2030 horizon을 적용한다.
- GDP는 2026 성장률 계산을 위해 2025 absolute GDP를 source lookback으로 사용할 수 있지만 2025 slot을 proposal에 노출하지 않는다.
- `start_year <= end_year`를 설정 validation에서 보장한다.
- horizon과 LUT file/catalog hash를 cache identity에 반영한다.

### 최소 LUT YAML과 adapter

신규 설정 파일:
`apps/agents/model_parameter_agent/resources/lut/config/lut_parameters.yaml`

최소 필드만 사용한다.

- `adapter`
- optional `layout: row | year_columns`
- `files`/`path`
- custom adapter의 `required_columns`
- tabular adapter의 `axis_columns`
- `value_column` 또는 `year_value_column`
- `key_axes`
- optional `metadata_axes`

YAML에 임의 Python import, 계산식, validator DSL, horizon/cap을 넣지 말고 DB LUT spec table도 만들지 마라.

YAML은 LUT loader 설정과 등록 parameter의 processing schema를 겸한다. feature flag와 무관하게 YAML 구조와 key/metadata 축을 검증하되, flag=false에서는 실제 CSV를 열거나 LutCatalog를 만들지 않는다.

- 공통 `tabular` adapter:
  - PMI: `year_columns`
  - PowerMix: `row`
- 전용 adapter:
  - GDP growth
  - Temperature degree-days
  - LiqUtil

GDP General 파일, Full Country List, PMI t1 reference-country file/fallback은 사용하지 않는다. PMI는 t2 파일의 84개국만 LUT 후보로 사용하고, 국가 범위는 parameter별 실제 LUT distinct를 따른다.

### Loader 검증과 오류

등록된 LUT에 대해 파일, 필수 header, 값 타입/finite, exact key uniqueness, horizon과 file hash를 검증한다.

- 같은 key의 value와 authoritative metadata까지 완전히 같은 duplicate만 deterministic dedupe하고 진단을 남긴다.
- 같은 key의 value 또는 authoritative metadata가 하나라도 다르면 first/last-wins 없이 적재 실패한다.
- flag=false이면 YAML processing schema는 검증하지만 LUT CSV/catalog는 읽지 않는다.
- flag=true + parameter 미등록은 정상 basecase-only source다.
- flag=true + 등록·유효는 basecase+LUT source다.
- flag=true + catalog/file/header/duplicate 오류는 명시적 domain/config error다.
- 등록 오류를 warning만 남기고 basecase-only로 강등하지 마라.

### Catalog와 state

full LUT 또는 full effective record를 LangGraph state에 넣지 마라.

- process-level immutable `LutCatalog`
- request 단위 `BasecaseIndex`
- Step2용 compact `SlotCatalog`
- Step2가 반환하고 서버 검증을 통과한 selected key
- 선택된 key의 `EffectiveReference`만 Step3 state에 저장

compact catalog에는 canonical axis, 비시간 leaf hierarchy, leaf별 실제 available Year/Month와 활성 basecase/LUT source의 union을 보존한다. raw/effective record를 40,000건 같은 전역 cap으로 먼저 자르지 마라.

### Step2

- 서버는 horizon, schema, exact path, LiqUtil Closed 제외 같은 객관적 유효성만 적용한다.
- scenario/event 관련성은 전체 유효 compact catalog를 받은 LLM이 판단한다.
- 전수 선택이나 최대치 채우기를 지시하지 마라.
- `model_parameter_max_parameter_slots=100`을 각 parameter task의 독립 hard maximum으로 prompt와 validator에 적용한다.
- 한 parameter가 다른 parameter의 예산을 차감하면 안 된다.
- LLM 결과를 canonical key로 바꿔 활성 `BasecaseIndex union LutCatalog`에서 exact membership을 검증한다.

### EffectiveReference와 Step3

내부 모델에서 최소한 다음을 구분한다.

- `actual_basecase_value`
- `lut_default_value`
- `llm_reference_value`
- `effective_source`
- `basecase_reference_id`
- `lut_reference_id`
- `lut_version`
- `diagnostics`

`llm_reference_value`는 actual basecase가 있으면 그 값, 없으면 LUT default다. LLM에는 좌표당 기준 숫자 하나만 전달하고 basecase와 LUT 두 숫자를 동시에 노출하지 마라.

`model_parameter_max_value_prompt_basecase_records=100`을 각 parameter task에 독립 적용한다. cap 때문에 필수 selected reference를 조용히 누락하지 마라.

Step3는 cell 단위로 처리한다.

- LLM이 명시적으로 반환하고 검증을 통과한 cell만 유지한다.
- 누락 cell을 no-change cell로 자동 생성하지 않는다.
- 일부 누락 때문에 같은 candidate의 valid cell 전체를 폐기하지 않는다.
- LLM이 기준값과 같은 값을 명시적으로 반환한 경우 정상 no-change proposal로 저장한다.
- selected/valid/missing/invalid cell 수는 내부 sync/test diagnostics와 metric으로 제공한다.

### LiqUtil metadata와 PowerMix

metadata 복원은 현재 LiqUtil에만 적용한다.

- Period
- Life Cycle Category
- Nameplate Capacity

이 필드는 business key가 아니며 LLM이 만들지 않는다. actual basecase가 있는 exact key는 basecase metadata를, LUT-only exact key는 LUT metadata를 복원한다. Nameplate Capacity는 MTPM x 12로 MTPA를 만들고 Bcm/month column은 사용하지 않는다. Closed lifecycle은 case-insensitive하게 제외한다. 다른 parameter에서 이름만 보고 이 metadata를 전역 제외하지 마라.

PowerMix는 `Country + Year + Energy Source`별 독립 override다. LLM이 반환한 source cell만 저장하고 전체 vector 강제, 합계 1 검증·정규화, 미선택 source 자동 보완과 group 전체 폐기를 하지 마라.

### 운영 API/DB projection

운영 proposal DB와 frontend API의 기존 구조·의미를 변경하지 마라.

- actual basecase가 있으면 `basecaseValue=actual_basecase_value`
- LUT-only이면 LLM 기준값이 LUT여도 운영 `basecaseValue=null`
- LUT용 운영 DB column을 추가하지 않는다.
- 내부 sync/test API는 LUT value/source/provenance를 진단용으로 반환한다. 운영 API에는 추가하지 않는다.

내부 EffectiveReference와 운영 ParameterValueCell projection을 분리하라.

## 4. 공통 LLM connector

`invoke_llm_structured_output`에 optional 호출 인자를 추가한다.

    stream: bool = False
    reasoning_effort: ReasoningEffortOption | None = None

- 기존 caller가 생략하면 non-stream/provider-default로 동작한다.
- connector가 stream 관련 global Settings를 직접 읽지 않는다.
- Model Parameter Agent가 Step1.5, Step2, Step3의 모든 structured-output 호출에 자기 설정값을 전달한다.
- stream/non-stream 모두 완성된 동일 `LLMStructuredResult`를 반환한다.
- stream partial JSON을 반환하지 않고 중단 시 전체 호출을 실패·retry한다.
- provider가 usage를 주지 않으면 nullable 계약을 유지한다.

reasoning_effort 규칙:

- 생략, Python None, 문자열 `default`: request key 자체 생략
- 문자열 `none`: `none`을 그대로 전송
- `minimal/low/medium/high/xhigh`: 그대로 전송
- invalid 설정: 시작/설정 validation에서 거부
- enum 안의 값이 provider/model에서 미지원이면 기존 connector/domain error로 전파하고 default로 fallback하지 않음

코드 기본값:

    model_parameter_lut_enabled: false
    model_parameter_llm_stream_enabled: false
    model_parameter_llm_reasoning_effort: default

checked-in `envs/config.yaml`과 K8s ConfigMap에도 별도 배포 활성화 요청이 없는 한 위 세 값은 각각 false, false, default로 명시하고, horizon 2026/2030과 두 cap 100/100을 일치시켜라. 수동 LUT 통합 테스트에서만 `model_parameter_lut_enabled=true`를 명시적으로 override한다. 환경 활성화 여부를 임의로 바꾸지 마라.

## 5. 구현 및 commit 순서

소스 변경 전에 예상 변경 파일, 영향 범위와 주요 위험을 먼저 보고한 뒤 다음 순서로 구현하라. 각 단계는 독립 review/revert 가능한 작은 commit으로 분리한다.

1. 공통 connector optional stream/reasoning_effort와 독립 테스트
2. app settings, horizon validation, LUT YAML, typed spec loader
3. tabular adapter와 GDP/Temperature/LiqUtil 전용 adapter
4. immutable LutCatalog, request BasecaseIndex, compact SlotCatalog
5. 단일 source-selection 단계와 공통 pipeline 연결
6. Step2 전체 compact catalog, parameter별 cap, strict exact membership
7. selected-key EffectiveReference와 Step3 단일 기준값/partial policy
8. LiqUtil metadata, PowerMix 정책, 운영 projection, sync diagnostics
9. source matrix, 오류, cache, 성능·메모리 테스트
10. 검증 환경이 있으면 최종 28개 scenario를 재실행하고 설정·문서를 동기화한다. 환경이 없으면 blocker와 미검증 위험을 기록한다.

공통 connector 변경과 LUT domain 변경을 분리하고 사용자 변경을 commit에 섞지 마라. push, MR, 배포는 별도 요청이 없으면 수행하지 마라.

## 6. 필수 검증

양쪽 branch의 기존 테스트 사례는 최종 정책에 맞게 선별·재작성한다.

- Codex 참고: `feature/model-param-lut-basecase:tests/automated/test_model_parameter_lut_integration.py`
- Claude 참고: `feat/lut-basecase-integration:tests/automated/test_lut_repository.py`
- 현재 브랜치 contract: `tests/automated/test_model_parameter_agent_contract.py`

최소 자동화 게이트:

1. 5개 loader/transform과 최종 문서 13장의 기대 record 수
2. 2026~2030 horizon, GDP 2025 lookback과 2025 slot 미노출
3. PMI t2-only 84개국, t1/General/Full Country List 미접근
4. basecase override, basecase-only, LUT-only와 exact miss 제외
5. value/metadata가 모두 같은 duplicate dedupe, 동일 key의 value/metadata 충돌 실패
6. leaf에 없는 Year/Month 거부와 nearest 미사용
7. flag/source matrix 네 경우와 source 이후 동일 pipeline; flag=false에서도 YAML 구조 오류는 실패하지만 LUT CSV는 열지 않음
8. LUT 미지원 parameter의 canonical axis 전체 보존과 이름 기반 metadata 제외 미발생
9. parameter별 Step2/Step3 100 cap 독립성
10. explicit no-change 저장과 partial valid/missing/invalid cell 정책
11. PowerMix 독립 override와 비정규화
12. LUT-only 운영 basecaseValue null과 sync diagnostics provenance
13. state에 full LUT/effective record가 없고 raw cap 없이 compact leaf/period 보존
14. stream false/true parsed output, 중단 retry, empty content, nullable usage
15. reasoning_effort 생략/default/none/지원값/invalid와 stream 조합, provider/model 미지원 오류 전파와 무음 fallback 금지
16. cold/warm load, state 직렬화 크기, concurrent cache race

검증 명령에는 관련 pytest, `tests/automated/test_model_parameter_agent_contract.py`, compile check, `git diff --check`와 프로젝트 formatter/linter의 변경 파일 범위 검사를 포함하라.

수동 검증이 가능한 환경이면 `model-parameter-agent-test` skill 절차에 따라 LUT enabled=true, horizon=2026~2030과 최종 stream/reasoning 설정으로 5개 parameter 대상 28개 scenario를 재실행하라. 결과에 resolved config, lut_version, LUT-only/exact reference, missing/invalid cell과 source별 수를 기록하라. 실행할 수 없다면 이유와 남는 위험을 명확히 보고하고 성공을 추정하지 마라.

## 7. 완료 조건과 보고

구현과 실제 코드에 맞춰 이 최종 문서를 갱신하라. package ownership, flow 경계 또는 endpoint mapping을 바꾼 경우 관련 architecture 문서도 갱신한다.

최종 보고에는 다음을 포함하라.

1. 변경 목적과 단일 pipeline/source-selection 동작
2. D-01~D-11 반영 위치와 주요 변경 파일
3. 운영 API/DB 하위호환성
4. 성능·메모리·운영 위험
5. 수행한 테스트 명령과 실제 결과
6. 28개 scenario report 경로와 요약 또는 실행 blocker
7. 미검증 항목과 제약
8. 생성한 commit 목록과 hash
9. 실제 설정의 LUT/stream/reasoning 상태
10. push/MR/배포를 수행하지 않았다는 확인

관련 자동화 테스트, source matrix, exact membership, partial/API projection 회귀, state/raw-cap 검증과 문서·설정 동기화가 끝나기 전에는 완료로 보고하지 마라.
