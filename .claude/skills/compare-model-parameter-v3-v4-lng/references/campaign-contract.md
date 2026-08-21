# 다중 pair campaign 계약

## 목차

1. 용어와 기본 예산
2. Campaign manifest
3. Pair 선택과 coverage
4. DB mutation allowlist
5. 단계·재개·동시성
6. Export·환경·XLSM
7. 실패·retry·cleanup
8. 기존 도구 연결과 capability gap
9. Artifact 구조

## 1. 용어와 기본 예산

- `Event set`: display order가 보존된 2~5개의 중복 없는 active Event ID 목록
- `pair`: 같은 ordered Event set을 가진 v3 group 하나와 v4 group 하나
- `case`: 하나의 scenario를 하나의 pinned confirmed input과 run ID로 실행한 engine run
- `attempt`: preflight/export/engine/evidence를 한 번 시도한 이력. 성공 retry도 이전 실패 attempt를 제거하지 않음
- `campaign`: 실행 전에 고정한 pair universe와 예산을 공유하는 비교 단위

기본 목표는 distinct pair 3개 이상, total engine case 20개 이상이다. 하나의 group에 scenario를 임의 추가해 case 수를 채우지 않는다.

## 2. Campaign manifest

Manifest를 mutable 작업 메모가 아니라 versioned source of truth로 사용한다. stage가 바뀔 때 새 revision을 기록하고 이전 revision hash를 연결한다.

```yaml
schemaVersion: model-parameter-v3-v4-lng-campaign-v1
campaignId: <globally-unique-id>
createdAt: <ISO-8601 with timezone>
source:
  gitSha: <sha>
  dirty: true|false
  dirtyDiffSha256: <sha|null>
  appConfig: <name>
  appConfigSha256: <sha>
  targetDb: <credential-free identity>
  canonicalVersion: <version>
  legacyMappingSignature: <count/method-count/hash>
  impactLeverCatalog: <version/checksum>
  basecaseLutRelease: <hashes>
  engineTemplateRelease: <hashes>
  toolHashes: {<relative-path>: <sha>}
authority:
  createGroups: true|false
  createProposals: true|false
  confirmProposals: true|false
  useExternalLlm: true|false
budget:
  targetPairs: <n>
  targetCases: <n>
  jobsWithinGroup: <n>
  diskRequiredBytes: <n>
policy:
  orderedTags: [strong_bullish, bullish, balanced, bearish, strong_bearish]
  absoluteEpsilon: 0.000001
  minimumTagsPerVersion: 3
  requiredRegions: [East Asia Spot, TTF, HH]
  requiredStrata: [annual, monthly]
  maxAttemptsPerCase: 1
  retryableSignatures: []
pairs:
  - pairId: <stable-local-id>
    orderedEventIds: [<id>, <id>]
    eventSequenceSha256: <sha>
    replicateOf: <pair-id|null>
    v3Group: {id: <id>, strategy: multi_event_composite_dimensions}
    v4Group:
      id: <id>
      strategy: multi_event_model_lever_dimensions
      storedCatalogVersion: <version>
      storedCatalogChecksum: <sha>
      candidateSignature: <sha>
    cases:
      - version: v3|v4
        scenarioId: <id>
        pressureTag: <tag>
        proposalId: <id>
        confirmedPayloadSha256: <sha>
        reservedRunId: <id>
        artifactRoot: <path>
    coverageContribution: [<axis=value>]
    coverageGaps: [<reason>]
    coverageStatus: FULL|PARTIAL|NONE
    qualityStatus: PASS|REVIEW|FAIL|N/A
    pairStage: <state>
    versions:
      v3: {stage: <state>, artifactHashes: {}, attempts: []}
      v4: {stage: <state>, artifactHashes: {}, attempts: []}
previousManifestSha256: <sha|null>
manifestSha256: <sha>
```

최소 identity에는 pair/group/scenario/proposal/run ID, ordered Event IDs, tag/role/baseline, payload와 artifact hash가 포함되어야 한다. credential, token, 전체 prompt 원문은 넣지 않는다.

Canonical JSON은 UTF-8, key 정렬, compact separator, non-finite number 금지로 직렬화한다. `manifestSha256` 필드 자체를 제외해 hash하고 `previousManifestSha256`로 revision chain을 만든다. 새 revision 파일을 완성·fsync한 뒤 current manifest를 atomic replace한다. Pair-level 하나의 stage로 version별 부분 완료를 덮지 않는다.

## 3. Pair 선택과 coverage

### Identity gate

- relation의 active display order를 사용한다. 정렬된 set equality로 대체하지 않는다.
- soft-deleted relation과 중복 Event를 제외한다.
- 공통 pressure tag가 2개 미만이면 alignment coverage는 `NONE`, 2개이면 `PARTIAL`이다.
- 기본 `FULL` coverage는 version별 tag 3개 이상과 manifest의 required region/stratum row가 모두 있어야 한다.
- role·baseline은 대응 보조 근거이고 primary match key가 아니다.
- scenario/parameter count가 다르더라도 one-sided coverage로 보존한다.
- 같은 `eventSequenceSha256`는 distinct coverage pair로 한 번만 센다. 추가 조합이나 재실행은 replicate로 분리한다.

### Coverage 우선순위

다음 축에서 아직 없는 조합을 가장 많이 추가하는 pair부터 선택한다.

| 축 | 예시 |
|---|---|
| Domain | demand, supply, trade/shipping |
| Candidate relation | v3/v4 shared, v3-only, v4-only, primary/alternative |
| Reference source | Basecase exact, LUT-backed, mixed |
| Lever state | increase, decrease, disrupt, recover, conflicting, unchanged-only |
| Price behavior | responsive, tied, one-sided, prior reversal |
| Scenario shape | 3/4/5 pressure tags, 2/3/4/5 Events |

전체 universe와 제외 사유를 manifest에 먼저 고정한다. 성공 가능성이 높아 보이는 pair만 사후 선택하지 않는다.

## 4. DB mutation allowlist

### 기존 pair 재사용

허용 delta:

- campaign proposal/confirmation rows
- modifier/confirmation timestamp 등 해당 row의 정상 workflow 변경
- 로컬 report/evidence/output

불허 delta:

- master, mapping, Impact Lever, schema, Basecase/LUT
- 기존 group/scenario/relation
- pre-existing proposal row
- 기존 v4 runtime 후보 결과

### counterpart 생성

추가 허용 delta:

- manifest에 기록된 새 counterpart group 1개
- 그 group의 scenario와 ordered group-event relation

Retained 생성은 `compare_v3_v4_proposals.py --create-missing-counterpart`가 호출하는 versioned sync create로 고정한다. Soft-delete comparison orchestration과 SSE create를 섞지 않는다. Proposal 전에 `del_yn=N`, target version/strategy, ordered relation, scenario 완결성, v4 stored catalog version/checksum을 read-back한다.

POST 전에 `CREATE_PENDING` manifest revision에 source group, target version, ordered Events, user, attempt, DB baseline을 기록한다. Timeout/crash면 `CREATE_UNKNOWN`으로 두고 그 baseline 이후 생성된 exact version/Event sequence 결과가 유일할 때만 채택한다. 0건 또는 여러 건이면 자동 재시도하지 않고 중단한다.

기존 row update나 unrelated group·operation 생성은 불허한다. create timeout 후 같은 POST를 blind retry하지 않는다.

v4 isolation evidence는 mode별 allowlist를 이해해야 한다. 각 v4 group의 stored catalog version/checksum과 `selected value → Lever state → candidate parameter` signature를 proposal 전에 pin하고 실제 후보가 그 allowlist 부분집합인지 확인한다. 기존 pair용 fingerprint comparator를 새 group 생성 mode에 그대로 사용해 expected insert를 오류로 만들지 않는다.

## 5. 단계·재개·동시성

Pair stage를 다음 순서로 유지한다.

```text
DISCOVERED
→ AUTHORIZED
→ CREATE_PENDING|REUSED
→ CREATED_OR_REUSED
→ PROPOSED
→ CONFIRMED
→ PINNED
→ EXPORTED
→ PREFLIGHT_PASS
→ ENGINE_COMPLETE
→ EVIDENCE_VALIDATED
→ REPORTED
```

Terminal 보조 상태는 `FAILED`, `REVIEW`, `COVERAGE_LIMIT`이다. 이전 stage artifact hash와 DB snapshot이 모두 일치할 때만 resume한다. `PROPOSED` 이전으로 무조건 되감아 DB row를 중복 생성하지 않는다.

`CREATE_UNKNOWN`은 reconciliation 전 blocked 상태다. Version별 stage와 artifact hash를 독립 저장하고, pair stage는 두 version 중 더 이른 완료 단계로 계산한다.

실행은 group 단위 global lock을 지킨다. Pair와 group은 순차 실행하고 현재 group 내부 case에만 제한된 `jobs`를 사용한다. Campaign 전체 run ID를 먼저 예약하며 형식에 campaign/pair/version/scenario/attempt identity를 포함한다.

## 6. Export·환경·XLSM

### Proposal pinning

Planning 단계에서 scenario별 최신 유효 `CONFIRMED AND del_yn='N'` 한 건을 해석할 수는 있다. 그 즉시 proposal ID, payload, hash를 manifest에 pin한다. Export 직전에 exact ID의 scenario/group/version/status/del_yn/payload hash를 한 snapshot에서 재확인한다. Export는 이 exact ID만 사용하며 장시간 campaign 도중 `latest`를 다시 조회하거나 fallback하면 안 된다.

Export 전후 DB proposal snapshot/hash가 같아야 한다. Export는 temp directory에서 완결성과 hash를 검사한 뒤 최종 신규 path로 publish한다. 기존 target path를 덮어쓰지 않는다. Case별 target XLSM hash, patch cell, formula/data-only read-back, confirmed numeric을 manifest에 고정하고 engine 직전에 다시 대조한다.

### Cell resolution

- 값이 있는 Basecase reference는 exact existing cell을 사용한다.
- `basecaseValue=null`인 LUT-backed parameter는 parameter별 adapter 계약을 적용한다.
- `LiqProdAdjustment`는 exact LUT value/full coordinates → same-row Basecase metadata anchor → exact Year/Month/Period header 순서로 existing cell을 찾는다.
- LiqProd 규칙을 다른 adapter에 일반화하지 않는다.
- partial key, nearest period, 신규 cell 생성은 금지한다.

### XLSM preflight

Case마다 정확히 다음 3개만 허용한다.

- `Demand Model_Input.xlsm`
- `Supply Model_Input.xlsm`
- `Trade Model_Input.xlsm`

filename-role, nonzero size, ZIP/CRC, OOXML parts, macro content type, required sheets, source hash를 확인한다. 변경 formula/cell과 필요한 calcChain 제거 외 OOXML/VBA part는 불변이어야 한다.

### Interpreter preflight

- `tests/lng_model/.venv/bin/python` 경로를 symlink-resolve하지 않는다.
- `sys.executable`, `sys.prefix`, `sys.base_prefix`, Python version/architecture를 기록한다.
- `sys.prefix`가 exact `tests/lng_model/.venv`이고 `sys.base_prefix != sys.prefix`임을 요구한다.
- 모든 child stage가 같은 interpreter를 사용함을 실행 차단 gate로 확인한다.
- `PYTHONPATH`를 제거하고 `PYTHONNOUSERSITE=1`을 사용한다.
- writable `UV_CACHE_DIR`를 사용한다.
- dependency 기준은 `pyproject.toml`과 lock file이다. binary일 수 있는 `requirements.txt`를 텍스트 설치 입력으로 가정하지 않는다.

## 7. 실패·retry·cleanup

| 분류 | 예 | 진행 규칙 |
|---|---|---|
| `PREFLIGHT` | identity, collision, lock, manifest mismatch | 원인 수정 전 실행 금지 |
| `ENVIRONMENT` | venv 이탈, import, launch | 환경 조치 후 full preflight 재실행 |
| `INPUT` | export, XLSM, OOXML, role | 영향 case만 재-export·검증 |
| `MODEL` | Demand/Supply/Trade/Output native nonzero | stage log·native rc 진단 후 제한 retry |
| `TIMEOUT_ORCHESTRATION` | timeout, process state 불명 | 상태 read-back 전 blind retry 금지 |
| `EVIDENCE` | hash, parity, lineage, report binding | 공식 report publish 금지 |

Attempt마다 command, interpreter, start/end, native/wrapper rc, category, stage, stderr 요약, exact cleanup, retry parent를 기록한다. 기본 `maxAttemptsPerCase=1`이며, manifest에 실행 전 고정한 retryable native signature와 stage에만 최대 총 2 attempts를 허용한다.

- 동일 run ID를 retry에 재사용하지 않는다.
- 성공 retry가 최초 실패 증적을 덮지 않는다.
- source XLSM, confirmed export, 성공 output을 삭제하지 않는다.
- cleanup 전에 실패 log/manifest를 `failed_attempts/<attempt-id>/`에 immutable 복제하고 hash를 고정한다.
- cleanup은 root containment와 symlink 부재를 확인한 manifest experiment root 안의 정확한 incomplete `outputs/<run-id>`와 `log/<run-id>`만 허용한다. 복제된 실패 증적은 삭제하지 않는다.
- Timeout은 전체 process tree 종료, group lock 해제, partial output inventory 확인 후에만 새 run ID로 재시도한다.
- 환경·input이 공통 원인이면 다음 group 실행을 중단한다.

Disk gate에는 성공 case뿐 아니라 temp export, 보존된 failed attempt, 허용 retry의 peak 공간을 포함한다.

## 8. 기존 도구 연결과 capability gap

| 역할 | 기존 자원 | 현재 경계 |
|---|---|---|
| pair discovery/proposal/confirmation | `tests/manual/model_parameter_agent/compare_v3_v4_proposals.py` | 한 pair 중심; 명시 group ID로 반복 사용 |
| missing counterpart | 같은 runner의 `--create-missing-counterpart` | 한쪽 counterpart 하나만, explicit authorization 필요 |
| v4 fingerprint | `tests/manual/model_parameter_agent/capture_v4_mapping_invariance.py` | 기존 pair 재사용 delta에 적합; 생성 allowlist는 별도 처리 필요 |
| confirmed export | `tests/manual/model_parameter_agent/export_confirmed_scenario_model_inputs.py` | 현재 scenario별 latest confirmed 선택; exact manifest pin 지원을 먼저 확인/보강 |
| group engine | `tests/lng_model/skills/evaluate-lng-price-tags/scripts/run_group.py` | group 하나와 group 내부 jobs만 지원 |
| deterministic evidence | `tests/lng_model/skills/evaluate-lng-price-tags/scripts/collect_evidence.py` | group별 `evaluation.json` |
| pair report | `tests/manual/model_parameter_agent/report_v3_v4_engine_comparison.py` | 한 pair MD/PNG 중심; multi-pair aggregate 지원을 먼저 확인/보강 |

없는 campaign 기능을 shell loop와 수기 복사로 감추지 않는다. Exact proposal pinning, manifest resume, aggregate renderer가 없다면 live write 전에 `tests/manual/` tooling과 `tests/automated/` contract를 먼저 추가한다.

## 9. Artifact 구조

```text
tests/reports/model_parameter_agent/campaigns/<campaign-id>/
├── manifest.json
├── manifests/manifest_<revision>.json
├── discovery/pair_universe.json
├── invariance/before.json
├── invariance/after.json
├── pairs/<pair-id>/
│   ├── proposal_confirmation.md
│   ├── v3/group_<id>/...
│   ├── v3/evaluation/{run_map.json,evaluation.json}
│   ├── v4/group_<id>/...
│   ├── v4/evaluation/{run_map.json,evaluation.json}
│   ├── failed_attempts/
│   └── pair_result.json
├── campaign_index.json
├── campaign_report.md
└── campaign_summary.png
```

JSON evidence는 내부 source of truth이고 공식 사용자 산출물은 요청에 따라 Markdown/PNG로 제한한다.
