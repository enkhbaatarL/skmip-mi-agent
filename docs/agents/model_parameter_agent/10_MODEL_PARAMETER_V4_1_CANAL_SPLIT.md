# Model Parameter v4.1 Canal Cost 분리

## 1. 현재 릴리스 기준

| 구분 | 현재값 |
|---|---|
| Scenario Impact Lever catalog | `v4.1` |
| hydrated catalog checksum | `467749ea59c3af7e875669be23da00c0fd8ef7c226256f9518a5945e36e4d7c4` |
| Proposal Flow release | `v4.1.8` |
| proposal capability | `extend17-v9` / `model-parameter-proposal-capabilities-v5.json` |
| workbook contract | `new-bc-v9` / `model-parameter-workbook-contract-v9.json` |
| logical table catalog | `20261016-v4-canal-split` / `model-parameter-logical-table-catalog-v4.json` |
| DB migration | mgmt `0050_split_canal_cost_parameters` |

현재 master는 26행·활성 18행이다. 현행 v4.1 proposal allow-list는 17종이며, 활성 master에 남아 있는
`CanalToll`은 과거 v4.0 catalog를 pin한 Scenario를 실행하기 위한 호환 항목이다. 따라서 master 활성 수
18과 현행 proposal 수 17은 의도적으로 다르다.

v4.1 Impact Lever catalog는 Lever 21개, binding occurrence 56개, conditional binding 41개,
executable 고유 Parameter 17개다. 공유 v1/v3 legacy dimension mapping 129행은 변경하지 않는다.

## 2. 변경된 Parameter와 모델 표

| modelParamId | parameterName | model file | sheet | modelTable | exact axes | 현재 용도 |
|---:|---|---|---|---|---|---|
| 24 | `CanalToll` | Trade | `ShippingCostInput` | `table4` | Canal, Year | v4.0 catalog 호환 전용 |
| 25 | `Suez Canal Cost` | Trade | `ShippingCostInput` | `table4` | Canal=Suez, Year | 현행 v4.1 proposal |
| 26 | `Panama Canal Cost` | Trade | `ShippingCostInput` | `table5` | Canal=Panama, Year | 현행 v4.1 proposal |

`parameterName`은 proposal·confirmation에서 파라미터를 구분하는 고유 키다. Suez와 Panama를 하나의
`CanalToll`로 반환하면 플랫폼이 두 탭을 독립적으로 식별할 수 없으므로, v0050의 v4.1 개정부터 파라미터와
`modelTable`을 모두 분리한다.

- Suez: source rows 39~46, `table4`, 2026~2030 5개 exact record
- Panama: source rows 50~57, `table5`, 2026~2030 5개 exact record
- 두 Parameter 모두 단위는 `$/crossing`, 최종 절대값이며 최소값은 0이다.
- 명시된 운하와 연도가 없으면 다른 운하의 slot을 대신 사용하지 않고 abstain한다.

실제 workbook의 Panama source header에는 닫는 괄호가 빠진 `RE Base Case ($/Crossing` 표기가 존재한다.
v9 contract는 이 원본 header를 그대로 검증하되, Agent 내부 value field는 정규화된 의미로 처리한다.

## 3. 버전 호환 규칙

- 신규 Scenario Group은 설정의 `scenario_group_v4_impact_catalog_version=v4.1`을 사용한다.
- v0050은 기존 v4.1 Group의 version은 유지하고 checksum을 이전 값 `a8e831...`에서 현행
  `467749...`로 같은 transaction에서 이관한다. 과거 v4/v4.0 Group과 그 pin은 변경하지 않는다.
- v4.0 pin에서는 capability v5가 ID 24 `CanalToll`을 허용한다.
- v4.1 pin에서는 ID 24를 제외하고 ID 25·26을 허용한다.
- v4.1 binding은 기존 `CanalToll` occurrence 하나를 Suez/Panama conditional binding 두 개로 확장한다.
- 두 운하 후보는 각각 직접 운하명·연도·통항료 인과 근거와 exact slot을 통과해야 하며, 한 운하의 근거로
  다른 운하까지 자동 선택하지 않는다.

공개 proposal/confirmation JSON shape와 endpoint는 바뀌지 않는다. 결과의 `parameterName`과
`modelTable` 값만 각 운하의 정식 Parameter 정의를 따른다.

PowerMix는 이번 변경 대상이 아니다. `PowerMix` 하나를 유지하고, `table1`은 Year+Country,
`table2`는 Year+Month+Country 단위로 각각 0.01 정밀도·합계 1.00 보정을 적용한다.

## 4. 화면 logical table catalog

`GET /model-parameters/logical-table-catalog`의 현재 catalog는 199개 entry, 고유 logical table 193개,
연결 관계 54개, 연결 Parameter 23개, `WRITE_TARGET` 23개다. Trade 화면에는 다음과 같이 별도 항목을
노출한다.

| parameterName | modelTableKey | displayName | useYn | uiVisible |
|---|---|---|---|---|
| `Suez Canal Cost` | `table4` | `Suez Canal Cost` | `Y` | `true` |
| `Panama Canal Cost` | `table5` | `Panama Canal Cost` | `Y` | `true` |

화면은 `displayName`을 라벨로 쓰고 `modelTableKey`는 저장 키로만 사용한다. master와 catalog 연결은
문자열 추측이 아니라 `modelParamId` 25·26으로 고정한다.

## 5. 정본과 검증

- Agent master canonical: `scripts/model_parameter/model-parameter-canonical-v4.1-0050.json`
- Impact Lever canonical: `scripts/model_parameter/model-impact-lever-canonical-v4.1-0050.json`
- mapping workbook: `resources/mapping/261016_시나리오가정_MI수급모델_input_매핑_model-parameter-canonical-v4.1.xlsx`
- DB migration/SQL 정본: sibling `skmip-mi-agent-mgmt`의 migration 0050과 `sql/versions/0050/`

검증은 canonical 생성 재현, workbook `--check-only`, capability/catalog/workbook contract 교차 검증,
Agent 전체 자동화 테스트, mgmt Alembic upgrade/downgrade/re-upgrade와 disposable MySQL fresh/incremental SQL
적용을 포함한다. 외부개발 DB 적용은 명시 승인 후 read-back까지 수행하고, live proposal/confirmation은
별도 실행 승인이 있는 경우에만 수행한다.
