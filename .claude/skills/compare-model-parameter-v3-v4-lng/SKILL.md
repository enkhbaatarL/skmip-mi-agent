---
name: compare-model-parameter-v3-v4-lng
description: Orchestrate evidence-bound MI Model Parameter v3/v4 LNG comparison campaigns across multiple Event-set pairs and tens of engine cases. Discover or create retained v3/v4 groups with identical ordered Event IDs, run proposal/confirmation, export exact confirmed inputs, execute Demand→Supply→Trade→Output safely, quantify bullish/bearish price-tag alignment, preserve failures and v4 isolation, and produce campaign Markdown/PNG reports. Use for multi-pair or many-case v3/v4 Model Parameter comparisons, LNG price-direction alignment campaigns, campaign resume/aggregation, or expansion of the prior single-pair flow. Do not use for a scenario-only proposal test or scenario-generation-only comparison.
---

# Model Parameter v3/v4 LNG 다중 비교 캠페인

## 역할

여러 개의 독립적인 v3/v4 Scenario Group pair를 하나의 campaign으로 조율한다. 각 pair는 같은 순서의 원천 Event를 공유하되 v3와 v4의 후보 산출 경계를 그대로 유지한다. 기술 실행 성공과 가격 tag 정합성을 분리해 판정하고, 성공한 case만 골라 집계하지 않는다.

기본 확장 목표는 서로 다른 Event-set pair 3개 이상, 완료 예정 engine case 20개 이상이다. 사용자가 다른 예산을 지정하면 그 값을 우선한다. 실제 DB coverage가 부족하면 목표를 몰래 낮추지 말고 `COVERAGE LIMIT`으로 보고한다.

## 필수 참조

작업 전에 다음을 완전히 읽는다.

1. [campaign-contract.md](references/campaign-contract.md): pair 선택, manifest, DB 변경 허용 범위, 재개, 실패 보존 계약
2. [report-contract.md](references/report-contract.md): 가격 비교 단위, 판정, macro/micro 집계, MD/PNG 형식
3. `.claude/skills/verify-model-parameter-release/references/v3-v4-lng-comparison.md`
4. `tests/lng_model/skills/evaluate-lng-price-tags/SKILL.md`와 그 `references/evidence-schema.md`

필요한 단계에만 다음 기존 skill을 추가로 읽고 그대로 재사용한다.

- 기존 pair discovery 또는 retained counterpart 생성: `.claude/skills/scenario-sync-pipeline/SKILL.md`
- v3 sourceRef·mapping·proposal 품질: `.claude/skills/model-parameter-multi-event-quality/SKILL.md`
- proposal·confirmation rollback/read-back: `.claude/skills/model-parameter-agent-test/SKILL.md`
- release 또는 canonical acceptance까지 포함: `.claude/skills/verify-model-parameter-release/SKILL.md`

## 변경 권한과 격리

- 항상 SELECT-only discovery부터 수행한다.
- 사용자가 campaign 실행을 요청한 경우에만 proposal·confirmation 행 생성을 승인된 범위로 본다.
- 적합한 pair가 없을 때의 group/scenario/relation 생성은 사용자가 명시적으로 허용한 경우에만 수행한다.
- canonical master, legacy dimension mapping, Impact Lever catalog, DB schema, Basecase/LUT, production v3/v4 Agent 로직은 이 비교를 위해 수정하지 않는다.
- v3는 현재 DB의 legacy direct/routing mapping을 사용하고, v4는 catalog-pinned Lever 경로만 사용한다. 대칭 coverage를 만들려고 한쪽 binding을 다른 쪽에 복사하지 않는다.
- 비교 도구 외 영역이나 다른 Agent에 영향이 필요한 경우 실행 전에 사용자에게 변경 범위를 확인한다.

## 0. Campaign 범위 고정

실행 전에 다음을 확정하고 campaign manifest 초안을 만든다.

- target DB/environment, git SHA와 dirty 상태, config/resource release
- 목표 pair 수, 목표 case 수, 허용 시간·token·disk·동시성
- group 생성, proposal/confirmation, 외부 LLM 사용에 대한 권한
- canonical tag order와 epsilon
- 공식 산출물 형식과 보존 기간

사용자가 계획·스킬·문서만 요청하면 여기서 실행을 멈추고 DB/API/LLM/엔진을 호출하지 않는다.

## 1. Pair universe discovery

현재 DB에서 v3 `multi_event_composite_dimensions`와 v4 `multi_event_model_lever_dimensions` group을 읽는다. 다음 조건을 모두 만족할 때만 pair로 인정한다.

- 양쪽 active relation의 `ordered_event_ids`가 순서까지 정확히 같음
- Event ID가 중복되지 않고 2~5개임
- v3/v4 group과 scenario identity가 서로 다름

scenario 수, parameter 수, 문장, Dimension 조합의 동일성은 요구하지 않는다. 공통 tag는 비교하고 one-sided tag·parameter는 coverage로 보존한다. 공통 tag가 2개 미만이면 alignment coverage를 `NONE`, 2개뿐이면 `PARTIAL`로 기록하고 campaign 품질 PASS 분모에는 넣지 않는다.

같은 ordered Event set에서 여러 group 조합을 발견해도 coverage pair는 결정론적인 v3 1개·v4 1개만 선택한다. 같은 Event set의 추가 실행은 `replicate`로 분리하고 distinct pair 목표에 중복 계산하지 않는다.

전체 pair universe를 먼저 고정한 뒤 domain, mapping relation, Basecase/LUT source, Lever state, responsive/tie 이력의 신규 coverage가 큰 pair부터 선택한다. 반복 auto-discovery로 같은 pair를 다시 뽑지 말고 이후 모든 명령에 명시적인 group ID를 사용한다.

## 2. 부족한 counterpart 생성

기존 pair만으로 예산을 채우지 못하면 다음 순서를 따른다.

1. 생성 권한과 target DB를 재확인한다.
2. POST 전에 manifest를 `CREATE_PENDING` revision으로 고정한다.
3. `compare_v3_v4_proposals.py --create-missing-counterpart`의 versioned sync create 경로로 반대 version group 하나만 생성한다. Scenario version 비교기의 soft-delete orchestration이나 SSE create 경로를 섞지 않는다.
4. non-idempotent create timeout을 자동 재시도하지 않는다. `CREATE_UNKNOWN`으로 전환하고 API/DB exact read-back으로 유일한 결과를 찾는다.
5. 생성된 group/scenario/relation ID를 manifest allowlist에 기록한다.
6. `del_yn=N`, version/strategy, ordered relation, scenario 완결성, v4 stored catalog checksum을 proposal 전에 다시 검증한다.

Scenario version 비교기의 기본 soft-delete orchestration은 이 campaign의 retained group 생성에 사용하지 않는다. proposal 실행 전에 group을 삭제하는 경로를 선택하지 않는다.

## 3. Capability gate

live write 전에 현재 도구가 다음을 지원하는지 확인한다.

- campaign 전체 pair/case/run ID를 고정하는 versioned manifest
- scenario마다 exact proposal ID와 confirmed payload hash를 pin하는 export
- pair별 evidence를 유지하는 resumable stage 상태
- pair-level 결과를 macro 중심으로 집계하는 campaign report generator
- 기존 pair와 retained counterpart 생성 delta를 각각 이해하는 v4 fingerprint verifier

현재 pair runner나 exporter가 single-pair 또는 moving `latest CONFIRMED`만 지원하면 그대로 반복 실행하지 않는다. 먼저 `tests/manual/` 범위의 orchestration/export/report 도구와 automated contract test를 보강한다. production Agent 동작이나 v4 결과를 바꾸는 방식으로 해결하지 않는다.

## 4. Baseline fingerprint와 허용 delta

첫 write 전에 master, legacy mapping, Impact Lever catalog/checksum, 기존 v4 group/scenario/relation, pre-existing runtime 후보, Basecase/LUT/engine/template hash를 캡처한다.

- 기존 pair 재사용: 신규 proposal·confirmation 행과 로컬 artifact만 허용한다.
- counterpart 생성: manifest에 명시한 신규 group/scenario/relation과 proposal·confirmation 행만 추가 허용한다.
- 기존 row update, canonical/mapping/catalog 변화, pre-existing v4 runtime 후보 변화는 허용하지 않는다.

Campaign 종료 후 같은 fingerprint를 다시 캡처하고 allowlist diff를 검증한다.

## 5. Proposal과 confirmation

pair별로 v3 group 전체 scenario를 완료한 뒤 v4 group을 처리한다. 기본 retry는 0이며, retry를 허용해도 모든 attempt와 token·시간을 남긴다.

- v3 eligible 후보는 current DB direct/routing mapping과 sourceRef lineage에서 도출한다.
- v4 후보는 catalog-pinned Lever state에서 도출한다.
- proposal마다 scenario/group/version, parameter, exact slot, value, rationale, token, elapsed, retry, payload hash를 기록한다.
- group마다 empty confirmation rollback을 1회 이상 검증한다.
- 모든 성공 proposal을 exact full payload로 confirm하고 DB read-back한다.
- group마다 reconfirmation을 1회 이상 검증한다.
- 안전한 기존 비정상 status row가 있을 때만 invalid-status rollback을 1회 검증한다.

완료된 proposal ID와 confirmation payload hash를 manifest에 고정한다. Export 직전에 exact ID의 scenario/group/version, `CONFIRMED`, `del_yn=N`, payload hash를 하나의 snapshot에서 다시 확인한다. 불일치하면 실패하며 `latest` fallback을 사용하지 않는다.

## 6. Confirmed input export와 preflight

DB SELECT-only로 exact pinned proposal을 Demand/Supply/Trade workbook에 반영한다. Basecase exact cell과 LUT-backed cell을 구분하고 partial key·nearest period·신규 cell fallback을 금지한다.

각 case의 XLSM 3개, OOXML/VBA/CRC, role sheet, 변경 cell, formula/data-only dual read-back, proposed numeric, source/target hash를 검증해 manifest에 고정한다. Engine 시작 직전에 같은 target hash와 patch 목록을 다시 확인한다.

`.venv/bin/python`은 resolve하지 않고 전달한다. `sys.prefix == tests/lng_model/.venv`, `sys.base_prefix != sys.prefix`, 모든 child stage interpreter 동일성, lock 기준 package import/version을 실행 차단 gate로 확인한다. `PYTHONPATH` 제거, `PYTHONNOUSERSITE=1`, writable `UV_CACHE_DIR`를 유지한다.

대표 case 실사용량을 측정한 뒤 `case당 크기 × 예정 case 수 × 1.2` 이상의 여유 disk를 요구한다. campaign 전체의 전역 고유 run ID를 실행 전에 예약한다.

## 7. LNG engine 실행

한 번에 하나의 group만 실행한다. 순서는 `pair 1 v3 → evidence → pair 1 v4 → evidence → pair 2 ...`로 유지한다. `--jobs`는 현재 group 내부 case에만 적용한다.

각 case에서 Demand → Supply → Trade → Output의 native rc, log, manifest, output hash를 보존한다. 실패는 `PREFLIGHT`, `ENVIRONMENT`, `INPUT`, `MODEL`, `TIMEOUT_ORCHESTRATION`, `EVIDENCE`로 분류한다.

기본 `maxAttemptsPerCase=1`로 retry를 끈다. 사전에 manifest에 고정한 retryable stage/native signature에만 총 2 attempts 이내를 허용한다. Timeout은 process tree 종료, lock 해제, output 상태 확인 뒤에만 재시도한다.

Retry는 원인을 확인하고 scoped remediation을 기록한 뒤 새 run ID로만 수행한다. 실패 log/manifest를 immutable failed-attempt artifact로 먼저 복제·hash한 뒤, root containment와 symlink 부재를 확인한 정확한 incomplete output/log path만 정리한다. 실패 attempt의 증적을 덮어쓰지 않는다.

## 8. Evidence와 가격 정합성 평가

group마다 독립 `evaluation.json`을 생성하고 immutable input, input diff, upstream diff, annual/monthly price, warning, failed attempt를 검증한다. pressure tag는 proposal 생성의 힌트로 주입하지 않고 결과 평가용 holdout으로 유지한다.

pair마다 다음 다섯 축을 독립 판정한다.

1. export integrity
2. engine execution
3. pressure-tag alignment
4. mechanistic consistency
5. model expressiveness

Engine PASS를 tag alignment PASS로 바꾸지 않는다. 동일 입력·전 구간 tie는 기술 실행이 성공해도 `indeterminate/REVIEW`로 남긴다. 자세한 계산과 aggregate 규칙은 report contract를 따른다.

## 9. Campaign report와 완료 판정

공식 Markdown 하나와 세로형 summary PNG 하나를 동일한 deterministic evidence에서 생성한다. pair 상세 evidence와 JSON은 내부 artifact로 유지한다. 사용자가 MD/PNG만 요청하면 HTML/SVG를 공식 산출물로 만들지 않는다.

재생성 byte 동일성, hash binding, source lineage, PNG 잘림·가독성을 검증한다. 최종 응답에는 다음만 요약한다.

- 계획/완료/실패/COVERAGE LIMIT pair와 case 수
- v3/v4 macro 판정과 micro 보조 지표
- tag 순서, tie·reversal, responsive region, 주요 expressiveness gap
- failed-attempt 분류·native rc·조치·cleanup
- v4 isolation과 허용 DB delta
- 시간·token·disk 및 남은 확장 한계
- 공식 MD/PNG 절대경로

## 중단 조건

다음 중 하나면 다음 live stage로 진행하지 않는다.

- target DB 또는 write 권한이 불명확함
- exact ordered Event pair identity가 깨짐
- exact proposal pinning이나 artifact hash binding을 증명할 수 없음
- venv/XLSM preflight 또는 disk gate 실패
- 예상 밖 DB/canonical/v4 fingerprint 변화
- non-idempotent create/proposal 결과가 timeout으로 불명확함
- 다른 Agent 또는 production v4 결과 변경이 필요함
