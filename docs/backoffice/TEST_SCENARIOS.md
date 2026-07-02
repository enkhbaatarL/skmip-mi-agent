# Backoffice 화면 기준 테스트 시나리오

## 1. 목적

이 문서는 Backoffice 화면에서 `Event List`부터 Scenario Group confirmation까지 사용자 시나리오를 검증하기 위한 QA 기준이다.

검증 대상:

- 이벤트 리스트 조회 및 이벤트 선택
- 시나리오 생성 요청, accepted 응답, generation callback 반영
- 생성된 시나리오 분기 기준 확인/수정/추가
- 검토 요청 및 validation callback 반영
- Signpost 생성 요청 및 signpost callback 반영
- Signpost 확률/내용 수정 후 confirmation
- Scenario Group detail 화면 확인
- 오류, 지연, 빈 데이터, 입력 제한 등 edge case

## 2. 공통 사전조건

- Backoffice가 실행 중이어야 한다.
  - URL: `http://127.0.0.1:9010/`
- Agent가 실행 중이어야 한다.
  - URL: `http://127.0.0.1:8000/`
- Agent callback 설정은 Backoffice를 바라봐야 한다.
  - `CALLBACK_BASE_URL=http://127.0.0.1:9010`
  - `CALLBACK_OAUTH2_TOKEN_URL=http://127.0.0.1:9010/api/v1/oauth2/token`
- Backoffice runtime bar의 `Agent Base URL`은 `http://127.0.0.1:8000`이어야 한다.
- 테스트 가능한 `miEventId`, `userId`가 준비되어 있어야 한다.
- QA Inspector에서 request body, accepted response, callback payload, detail response를 확인할 수 있어야 한다.

## 3. 통과 품질 기준

### 3.1 기능 품질

- 사용자는 화면 조작만으로 `이벤트 선택 -> 시나리오 생성 -> 검토 요청 -> 검토 완료 -> Signpost 생성 -> confirmation`까지 수행할 수 있어야 한다.
- long-running API는 즉시 accepted 응답을 보여주고, callback 수신 후 화면이 자동 갱신되어야 한다.
- callback 또는 SSE가 지연될 때도 화면이 깨지지 않고 manual refresh로 복구 가능해야 한다.
- validation, signpost, confirmation 요청 body는 화면에서 수정한 최신 값으로 생성되어야 한다.
- `runId`, `scenarioGroupId`, Agent `status`, Agent `stage`, local lifecycle이 화면에 표시되어야 한다.
- raw JSON inspector에서 요청/응답/callback/error 증적을 확인할 수 있어야 한다.

### 3.2 데이터 품질

- 선택한 이벤트의 `miEventId`가 생성 요청 body에 정확히 반영되어야 한다.
- generation callback 이후 시나리오 row 수, 제목, 분기 기준, baseline `BC` 표시가 화면에 반영되어야 한다.
- 시나리오 추가/삭제/수정 후 validation 요청 body에 변경 내용이 포함되어야 한다.
- Step 2에서 수정한 scenario group명, 설명, narrative, probability, signpost 값이 confirmation 요청 body에 포함되어야 한다.
- confirmation 이후 detail 화면의 요약, 가정 및 실현 가능성, 시나리오 상세 탭이 최신 데이터와 일치해야 한다.

### 3.3 UX 품질

- 요청 중에는 중복 클릭이 방지되어야 한다.
- 로딩 중에도 기존 입력값이 사라지지 않아야 한다.
- warning/error는 원인과 다음 행동을 알 수 있게 표시되어야 한다.
- 긴 텍스트는 화면을 깨지 않고 줄바꿈, 스크롤, ellipsis, raw view 중 하나로 확인 가능해야 한다.
- 모바일/좁은 화면에서도 주요 버튼과 입력값이 겹치지 않아야 한다.

### 3.4 실패 기준

아래 중 하나라도 발생하면 해당 케이스는 실패다.

- request body가 화면 입력값과 다르게 전송된다.
- callback 수신 후 lifecycle이나 화면 데이터가 갱신되지 않는다.
- validation/signpost/confirmation 중 버튼 중복 클릭으로 중복 요청이 발생한다.
- 시나리오 추가/수정 값이 다음 단계에서 유실된다.
- error callback 또는 Agent 오류가 raw inspector에 남지 않는다.
- confirmation 완료 후 detail 화면으로 이동하지 않거나 필수 탭이 렌더링되지 않는다.

## 4. 정상 동작 케이스

### TC-N-001 기본 end-to-end 생성 플로우

목적: 이벤트 1개를 선택해서 시나리오 생성부터 confirmation까지 기본 플로우가 정상 동작하는지 확인한다.

사전조건:

- Backoffice와 Agent가 실행 중이다.
- runtime bar의 `Agent Base URL`, `miEventId`, `userId`가 유효하다.

절차:

1. Backoffice 메인 화면을 연다.
2. `Event List` 탭이 활성화되어 있는지 확인한다.
3. 이벤트 리스트에서 이벤트 1개를 선택한다.
4. 선택한 이벤트의 시나리오 생성 액션 버튼을 클릭한다.
5. Scenario Design Step 1 화면으로 이동하는지 확인한다.
6. 시나리오 생성 요청 accepted 응답을 확인한다.
7. `runId`, `scenarioGroupId`, local lifecycle, Agent `status`, Agent `stage`가 표시되는지 확인한다.
8. generation callback 수신 후 시나리오 생성 결과 테이블을 확인한다.
9. 생성된 시나리오 row, `BC` badge, 분기 기준 컬럼, 셀 값이 표시되는지 확인한다.
10. `변경사항 검토` 버튼을 클릭한다.
11. validation 요청 중 overlay/loading이 표시되고 중복 클릭이 막히는지 확인한다.
12. validation accepted 응답과 validation callback 결과를 QA Inspector에서 확인한다.
13. 검토 결과가 성공 또는 진행 가능 상태이면 `검토 완료` 버튼을 클릭한다.
14. Scenario Design Step 2 화면으로 이동하는지 확인한다.
15. `Signpost 생성 요청` 버튼을 클릭한다.
16. signpost accepted 응답과 signpost callback 결과를 확인한다.
17. 각 시나리오 카드에 주요 Signpost가 표시되는지 확인한다.
18. `시나리오 그룹 생성` 버튼을 클릭한다.
19. confirmation 응답을 확인한다.
20. Scenario Group detail 화면으로 이동하는지 확인한다.
21. `요약`, `가정 및 실현 가능성`, `가격 전망`, `시나리오 상세` 탭을 순서대로 확인한다.

기대결과:

- Event List에서 선택한 이벤트 기준으로 생성 요청이 전송된다.
- Step 1에 generation callback 기반 시나리오 테이블이 표시된다.
- validation 이후 Step 2로 이동할 수 있다.
- signpost callback 이후 signpost 목록이 표시된다.
- confirmation 이후 detail 화면이 표시된다.
- QA Inspector에 create, validation, signpost, confirmation request/response/callback 증적이 남는다.

확인 증적:

- `request_body`: create, validation, signpost, confirmation
- `accepted`: create, validation, signpost, confirmation
- `callback`: generation, validation, signposts
- detail 화면 스크린샷

### TC-N-002 시나리오 추가 후 검토 요청

목적: generation 결과 확인 후 사용자가 시나리오 row를 추가하고 validation 요청을 보낼 수 있는지 확인한다.

절차:

1. TC-N-001의 8번 단계까지 진행해 Step 1 시나리오 생성 결과 테이블을 표시한다.
2. 테이블 우측 상단 또는 하단의 row 추가 버튼을 클릭한다.
3. 새 시나리오 row가 추가되는지 확인한다.
4. 새 row의 시나리오명을 입력한다.
5. 각 분기 기준 dropdown 값을 선택한다.
6. 추가된 row에 edited 상태 표시가 나타나는지 확인한다.
7. `변경사항 검토` 버튼을 클릭한다.
8. QA Inspector에서 validation request body를 확인한다.

기대결과:

- 추가 row가 validation request body의 `table.rows`에 포함된다.
- `displayOrder`가 기존 row와 충돌하지 않는다.
- 빈 필수값이 있으면 사용자가 인지 가능한 warning/error가 표시된다.
- 요청 중 추가 row 값이 화면에서 사라지지 않는다.

확인 증적:

- validation request body의 추가 row
- validation accepted response
- validation callback 또는 error callback

### TC-N-003 시나리오 값 수정 후 검토 요청

목적: generation 결과 확인 후 기존 시나리오 값을 수정하고 validation 요청에 반영되는지 확인한다.

절차:

1. TC-N-001의 8번 단계까지 진행한다.
2. 기존 시나리오 row 하나를 선택한다.
3. 시나리오명을 수정한다.
4. `기간`, `공급 차질`, `회복 패턴`, `대체 LNG 공급 가능성` 등 분기 기준 값을 하나 이상 수정한다.
5. 수정된 row에 edited 상태 표시가 나타나는지 확인한다.
6. `변경사항 검토` 버튼을 클릭한다.
7. validation request body에 수정 값이 반영되었는지 확인한다.
8. validation callback 결과를 확인한다.

기대결과:

- 수정된 title과 cells 값이 validation request body에 반영된다.
- validation 결과가 warning이면 warning callout에 사유와 수정 방향이 표시된다.
- validation 결과가 success이면 `검토 완료`가 가능하다.
- validation callback이 와도 사용자가 수정한 미확정 입력값이 예상치 않게 덮어써지지 않는다.

확인 증적:

- 수정 전/후 화면 스크린샷
- validation request body
- validation result 표시 영역

### TC-N-004 시나리오 추가 및 수정 복합 후 검토 요청

목적: 기존 시나리오 수정과 신규 시나리오 추가를 함께 수행한 뒤 validation 요청이 정상 생성되는지 확인한다.

절차:

1. Step 1 생성 결과를 표시한다.
2. 기존 row 1개의 시나리오명과 분기 기준 값을 수정한다.
3. 새 row 1개를 추가한다.
4. 새 row의 시나리오명과 전체 분기 기준 값을 입력한다.
5. 필요하면 기존 row 1개를 삭제한다.
6. row 순서와 `displayOrder`가 화면에서 자연스럽게 재정렬되는지 확인한다.
7. `변경사항 검토`를 클릭한다.
8. validation request body의 headers와 rows를 확인한다.

기대결과:

- 삭제된 row는 validation request body에 포함되지 않는다.
- 추가 row는 누락 없이 포함된다.
- 수정 row의 변경 값이 포함된다.
- baseline row가 삭제되거나 변경된 경우 화면에서 사용자가 인지할 수 있어야 한다.

확인 증적:

- validation request body
- Step 1 table 화면
- validation callback 결과

### TC-N-005 Signpost 생성 후 확률 수정 및 confirmation

목적: signpost 생성 후 scenario probability 또는 signpost 관련 값을 수정하고 confirmation 요청에 반영되는지 확인한다.

절차:

1. TC-N-001의 17번 단계까지 진행해 Step 2에 signpost가 표시되도록 한다.
2. 시나리오 카드 1개를 선택한다.
3. `시나리오 가능성` percent 값을 수정한다.
4. Signpost 편집 동작을 실행한다.
5. Signpost의 확률/영향 관련 값 또는 표시 가능한 signpost 값을 수정한다.
6. 수정 값이 카드 또는 상세 표시 영역에 반영되는지 확인한다.
7. `시나리오 그룹 생성`을 클릭한다.
8. confirmation request body를 QA Inspector에서 확인한다.
9. confirmation 응답 후 detail 화면으로 이동한다.
10. detail의 `가정 및 실현 가능성` 및 `시나리오 상세` 탭에서 수정한 probability/signpost 값이 반영되었는지 확인한다.

기대결과:

- 수정한 scenario probability가 confirmation request body의 해당 scenario row에 포함된다.
- 수정한 signpost 값이 confirmation request body에 포함된다.
- confirmation 중 버튼 중복 클릭이 막힌다.
- confirmation 완료 후 detail 화면에서 수정 결과를 확인할 수 있다.

확인 증적:

- 수정 전/후 Step 2 카드 화면
- confirmation request body
- detail 탭 화면

### TC-N-006 수동 새로고침으로 detail 동기화

목적: SSE 또는 callback 화면 반영이 지연될 때 manual refresh로 detail을 복구할 수 있는지 확인한다.

절차:

1. create accepted 이후 `scenarioGroupId`가 표시되는 상태까지 진행한다.
2. callback 화면 반영 전 또는 반영 후 `Refresh` 버튼을 클릭한다.
3. detail API 응답이 QA Inspector에 기록되는지 확인한다.
4. 화면의 시나리오 테이블 또는 Step 2 모델이 detail 기반으로 갱신되는지 확인한다.

기대결과:

- `Refresh` 요청 중 중복 클릭이 막힌다.
- detail response가 raw JSON으로 남는다.
- 갱신 가능한 데이터는 화면에 반영된다.
- refresh 실패 시 기존 화면 데이터는 유지되고 error가 표시된다.

## 5. Edge Case

### TC-E-001 Event List 빈 결과

절차:

1. status filter, 추천 항목만 보기, 검색어를 조합해 결과가 없도록 만든다.
2. Event List 영역을 확인한다.

기대결과:

- 빈 상태 메시지가 표시된다.
- 테이블 헤더나 화면 레이아웃이 깨지지 않는다.
- runtime bar와 QA Inspector는 계속 사용 가능하다.

### TC-E-002 Agent Base URL 누락 또는 잘못된 URL

절차:

1. runtime bar의 `Agent Base URL`을 비운다.
2. create 버튼 상태를 확인한다.
3. 잘못된 URL을 입력하고 create를 시도한다.

기대결과:

- URL이 비어 있으면 create 버튼이 비활성화된다.
- 잘못된 URL이면 error callout이 표시된다.
- raw inspector에 오류 상세가 기록된다.
- 화면이 초기화되거나 입력값이 유실되지 않는다.

### TC-E-003 miEventId/userId 누락 또는 숫자가 아닌 값

절차:

1. `miEventId`를 비우거나 숫자가 아닌 값으로 입력한다.
2. `userId`를 비우거나 숫자가 아닌 값으로 입력한다.
3. create 버튼과 요청 결과를 확인한다.

기대결과:

- 잘못된 입력은 요청 전에 차단되거나 API 오류가 명확히 표시된다.
- 잘못된 값이 `NaN` 형태로 request body에 들어가지 않아야 한다.
- 오류 후 입력 필드는 사용자가 수정 가능한 상태로 유지된다.

### TC-E-004 generation callback 실패

절차:

1. generation callback payload가 `result=failure`인 상황을 만든다.
2. 화면과 QA Inspector를 확인한다.

기대결과:

- local lifecycle이 failed 또는 실패 상태로 표시된다.
- failure callback payload가 raw inspector에 남는다.
- 실패 사유가 화면에 표시된다.
- manual refresh 또는 재시도 경로가 남아 있다.

### TC-E-005 validation warning 또는 failure

절차:

1. 상호 모순되는 분기 기준 조합을 입력한다.
2. `변경사항 검토`를 클릭한다.
3. validation 결과를 확인한다.

기대결과:

- warning callout이 표시된다.
- callout에 대상 조합, 사유, 수정 권장 방향이 표시된다.
- 정책상 진행 불가한 failure면 `검토 완료`가 disabled 된다.
- 정책상 진행 가능한 warning이면 사용자가 인지한 뒤 계속 진행할 수 있다.

### TC-E-006 scenario row 0개 또는 1개만 남김

절차:

1. Step 1에서 row를 삭제해 0개 또는 1개만 남긴다.
2. `변경사항 검토`를 클릭한다.

기대결과:

- 최소 row 수 정책에 맞는 validation 오류 또는 warning이 표시된다.
- 테이블이 빈 상태여도 화면이 깨지지 않는다.
- row 추가 버튼으로 복구 가능하다.

### TC-E-007 baseline scenario 삭제 또는 baseline 중복

절차:

1. `BC` badge가 있는 row를 삭제한다.
2. 또는 baseline 성격의 row를 중복 생성한다.
3. validation 요청을 보낸다.

기대결과:

- baseline이 없거나 중복될 때 validation warning/error가 표시된다.
- request body와 raw inspector에서 baseline 상태를 추적할 수 있다.
- 화면은 사용자가 수정할 수 있는 상태로 유지된다.

### TC-E-008 긴 텍스트 입력

절차:

1. scenario group명을 100자 가까이 입력한다.
2. scenario group 설명을 500자 가까이 입력한다.
3. scenario narrative를 500자 가까이 입력한다.
4. signpost label/evidence에 긴 텍스트가 포함된 payload를 확인한다.

기대결과:

- character counter가 정확히 표시된다.
- 제한을 초과한 입력은 차단된다.
- 긴 텍스트 때문에 버튼, 카드, 탭, 테이블이 겹치지 않는다.
- 카드에서는 truncate되더라도 detail/raw view에서 전체 값을 확인할 수 있다.

### TC-E-009 probability 비정상 값

절차:

1. Step 2에서 probability에 음수, 100 초과, 문자, 소수점 과다 값을 입력한다.
2. confirmation을 시도한다.

기대결과:

- 잘못된 값은 입력 단계에서 제한되거나 confirmation 전 validation/error로 표시된다.
- request body에 의도하지 않은 `0`, `NaN`, 빈 문자열이 조용히 들어가지 않아야 한다.
- 오류 후 사용자는 값을 수정하고 재시도할 수 있다.

### TC-E-010 Signpost 없는 상태에서 confirmation

절차:

1. Step 2로 이동한 뒤 signpost 생성 없이 confirmation을 시도한다.
2. 또는 signpost callback이 실패한 상태에서 confirmation을 시도한다.

기대결과:

- 정책상 signpost 필수이면 confirmation 버튼이 disabled 되거나 오류가 표시된다.
- signpost optional이면 confirmation body에 빈 signpost 배열이 명확히 포함된다.
- 사용자는 signpost 생성 재시도를 할 수 있어야 한다.

### TC-E-011 SSE 연결 끊김

절차:

1. run 생성 후 SSE 연결이 끊긴 상황을 만든다.
2. callback은 Backoffice backend에 정상 수신되도록 한다.
3. 화면에서 refresh를 수행한다.

기대결과:

- SSE 오류가 timeline/error로 기록된다.
- run state는 backend 메모리에 유지된다.
- manual refresh로 최신 detail 또는 callback 기반 상태를 회복할 수 있다.

### TC-E-012 callback이 run 생성보다 먼저 도착

절차:

1. 특정 `scenarioGroupId`에 대한 callback을 Backoffice에 먼저 보낸다.
2. 이후 같은 `scenarioGroupId`로 run이 accepted 되도록 만든다.

기대결과:

- callback은 orphan callback으로 저장된다.
- run이 해당 `scenarioGroupId`에 bind되면 orphan callback이 attach된다.
- lifecycle이 callback 결과 상태로 유지되고 waiting 상태로 되돌아가지 않는다.

### TC-E-013 confirmation 실패

절차:

1. confirmation 요청 중 Agent 오류 또는 4xx/5xx 응답을 만든다.
2. 화면 상태를 확인한다.

기대결과:

- confirmation 실패 callout이 표시된다.
- detail 화면으로 잘못 이동하지 않는다.
- confirmation request body와 Agent error body가 raw inspector에 남는다.
- 사용자는 수정 후 재시도할 수 있다.

### TC-E-014 브라우저 새로고침 후 run 복구

절차:

1. run 생성 후 `runId`, `scenarioGroupId`가 표시된 상태에서 브라우저를 새로고침한다.
2. local storage 또는 runtime bar 값이 복구되는지 확인한다.
3. manual refresh를 수행한다.

기대결과:

- runtime bar의 run context가 가능한 범위에서 유지된다.
- refresh로 detail 상태를 다시 불러올 수 있다.
- 복구할 수 없는 경우 사용자에게 필요한 값 입력 안내가 표시된다.

## 6. 회귀 체크리스트

- [ ] Backoffice root URL이 정상 렌더링된다.
- [ ] OAuth token mock이 `access_token`, `expires_in` snake_case로 응답한다.
- [ ] Agent startup 시 Backoffice token mock에서 token을 정상 prefetch한다.
- [ ] Event List에서 이벤트 선택 시 `miEventId`가 runtime bar에 반영된다.
- [ ] create accepted 후 `runId`, `scenarioGroupId`가 표시된다.
- [ ] generation callback 후 Step 1 테이블이 표시된다.
- [ ] 시나리오 추가 row가 validation request body에 포함된다.
- [ ] 시나리오 수정 값이 validation request body에 포함된다.
- [ ] validation warning/success 상태가 화면에 표시된다.
- [ ] `검토 완료` 후 Step 2로 이동한다.
- [ ] signpost 생성 후 카드에 signpost가 표시된다.
- [ ] signpost/probability 수정 값이 confirmation request body에 포함된다.
- [ ] confirmation 완료 후 detail 화면으로 이동한다.
- [ ] detail 탭 4개가 모두 렌더링된다.
- [ ] raw inspector에 request, accepted, callback, detail, error가 남는다.
- [ ] 오류 발생 시 기존 화면 입력값이 유실되지 않는다.

