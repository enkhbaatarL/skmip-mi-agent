# 가격 tag 정합성 및 campaign 보고 계약

## 목차

1. 비교 단위와 가격 정책
2. Pair-level 지표와 판정
3. 다섯 품질 축
4. Campaign aggregate
5. 왜곡 방지
6. Markdown 계약
7. PNG 계약
8. 최종 상태

## 1. 비교 단위와 가격 정책

기대 가격 순서는 다음과 같다.

```text
strong_bullish > bullish > balanced > bearish > strong_bearish
```

없는 tag를 제거하고 존재하는 tag를 canonical 순서로 배치한 뒤 같은 `version × pair × region × period` 안의 인접 tag를 비교한다. 원자 비교는 다음 tuple이다.

```text
(version, pair_id, annual|monthly, year, month|null, region, higher_tag, lower_tag)
```

가격은 `user_adjusted_price`를 사용한다. t1 annual과 t2 monthly를 직접 사용하며 서로 파생하지 않는다. 기본 epsilon은 실행 전 고정한 absolute `1e-6`이다. 상대 epsilon이나 business materiality threshold를 추가하려면 실행 전에 별도 policy로 승인·기록하고 기존 판정을 소급 변경하지 않는다.

```text
delta = price(higher_tag) - price(lower_tag)
met       := delta > epsilon
tie       := abs(delta) <= epsilon
reversed  := delta < -epsilon
```

Annual과 monthly는 서로 다른 strata로 보고한다. 두 strata를 독립 표본처럼 합쳐 신뢰도를 과장하지 않는다.

## 2. Pair-level 지표와 판정

각 version/pair/stratum에 다음을 계산한다.

- `met`, `reversed`, `tie`, `total`
- `strict_satisfaction = met / total`
- `tie_rate = tie / total`
- `reversal_rate = reversed / total`
- `decisive_accuracy = met / (met + reversed)`; 분모가 0이면 `N/A`
- `responsive_slice_rate`: 하나 이상의 non-tie edge가 있는 region-period slice 비율
- `tag_coverage`: 실제 비교 가능한 tag/edge와 제외 사유
- `pressure_span`: 최상위와 최하위 존재 tag의 가격 차이; pair 내부 진단값으로만 사용

결정적 verdict는 group evidence schema를 따른다.

| Verdict | 조건 |
|---|---|
| `aligned` | 모든 비교가 met이고 tie/reversed가 없음 |
| `partially_aligned` | met이 하나 이상이며 tie 또는 reversed도 존재 |
| `misaligned` | reversed가 하나 이상이고 met이 없음 |
| `indeterminate` | responsive region이 없거나 모든 비교가 tie |

Deterministic verdict와 quality gate를 구분한다. Verdict는 위 표를 그대로 사용하되 quality gate는 `aligned=PASS`, reversal이 없는 `partially_aligned`와 `indeterminate=REVIEW`, `reversed > 0` 또는 `misaligned=FAIL`로 표시한다. 따라서 met과 reversal이 함께 있어 verdict가 `partially_aligned`여도 quality는 반드시 `FAIL`이며 reversal count와 worst edge를 노출한다.

집계 순서는 다음으로 고정한다.

1. atomic edge
2. region-period slice
3. version별 annual/monthly stratum
4. version
5. pair
6. campaign

Version quality는 어느 stratum·slice에서든 reversal이 하나라도 있으면 `FAIL`, 모든 comparable edge가 aligned이고 coverage가 `FULL`이면 `PASS`, 나머지는 `REVIEW`다. Pair와 campaign은 version 및 다섯 품질 축을 `FAIL > REVIEW > PASS` 우선순위로 roll-up한다.

## 3. 다섯 품질 축

| 축 | PASS | REVIEW | FAIL |
|---|---|---|---|
| Export integrity | exact pinned payload와 XLSM/hash 계약 일치 | 비핵심 warning이나 수동 확인 필요 | wrong proposal/cell, hash·OOXML·DB immutability 위반 |
| Engine execution | 모든 계획 case와 4개 stage 성공, 필수 output/parity PASS | 성공했지만 retry·중요 warning 존재 | 미복구 case, output/parity/hash 실패 |
| Tag alignment | `aligned`이며 coverage `FULL` | reversal 없는 `partially_aligned` 또는 `indeterminate`; coverage 부족 | `reversed > 0` 또는 `misaligned` |
| Mechanistic consistency | input→upstream→price 방향이 설명됨 | 반응 없음·일부 chain 미관측 | 확정 input/upstream과 가격 방향이 모순됨 |
| Model expressiveness | scenario tag별 causal input signature가 충분히 구분됨 | signature 중복, one-sided parameter, 일부 driver 미표현 | mapping/lineage 결함으로 잘못된 input이 실행됨 |

모든 tag가 같은 confirmed input signature라서 tie인 경우는 기술 실패로 만들지 않는다. `model_expressiveness=REVIEW`, `tag_alignment=indeterminate`로 기록한다. 반면 서로 다른 pinned payload인데 exporter가 같은 cell/value를 만든 경우는 export integrity `FAIL`이다.

Pair `quality_status` 우선순위는 `FAIL > REVIEW > PASS`다. `coverage_status=FULL|PARTIAL|NONE`은 결함 판정과 별도 축으로 유지하며, `PARTIAL`인 pair는 headline `PASS`로 발표하지 않는다.

## 4. Campaign aggregate

### Primary macro

Pair를 동일 가중치로 집계한다.

- pair `quality_status` PASS/REVIEW/FAIL 건수·비율과 `coverage_status` FULL/PARTIAL/NONE 건수·비율
- version별 pair strict/tie/reversal rate의 평균, 중앙값, 최소/최대
- pair별 v3→v4 strict delta, tie-rate delta, reversal-rate delta
- `improved`, `unchanged`, `degraded`, `not_comparable` pair 수
- 다섯 품질 축의 pair verdict matrix

### Secondary micro

Annual atomic comparison과 monthly atomic comparison의 met/reversed/tie 합과 rate를 서로 분리한 보조 지표로 제공한다. Annual·monthly raw count를 하나의 micro rate로 합치지 않는다. 두 strata를 함께 요약해야 하면 stratum별 rate의 동일 가중 macro만 별도로 표시한다. Month·case가 많은 pair가 결과를 지배하므로 어떤 micro도 campaign headline으로 사용하지 않는다.

다음 breakdown을 제공한다.

- annual vs monthly
- region
- tag edge
- Event/domain
- parameter와 shared/v3-only/v4-only 관계
- Basecase/LUT source

Cross-version 가격 차이는 같은 pair의 공통 tag에서만 계산한다. Exact slot까지 같은 subset을 별도 표시하고, unmatched coverage를 0이나 tie로 채우지 않는다.

## 5. 왜곡 방지

- 실행 전 pair universe와 제외 기준을 고정한다.
- 성공한 pair만 사후 선택하지 않는다.
- ordered Event ID가 같은 pair만 합산한다.
- 같은 group/pair/case를 중복 집계하지 않는다.
- 3-tag와 5-tag raw count를 직접 비교하지 않고 rate와 coverage를 함께 쓴다.
- unrelated Event-set의 절대 가격을 서로 순서 비교하지 않는다.
- annual/monthly/region을 독립적인 campaign 성공 건수처럼 부풀리지 않는다.
- missing을 0 또는 tie로 대체하지 않는다.
- engine/LUT/template/canonical cohort hash가 다른 실행은 한 aggregate에 섞지 않는다.
- epsilon은 결과를 본 뒤 바꾸지 않는다. 민감도 분석은 별도 보조표로만 둔다.
- retry 성공이 이전 실패 attempt를 제거하지 않는다.
- v3/v4의 scenario 수·parameter 집합이 다름을 버전 실패로 간주하지 않는다.
- pressure tag를 proposal prompt에 평가 정답처럼 주입하지 않는다.

## 6. Markdown 계약

`campaign_report.md`를 사용자용 source of truth로 만든다. 최소 구조는 다음과 같다.

1. 문서 통제: status, campaign/schema/policy version, 시간·timezone, git SHA/dirty, credential-free DB identity
2. Executive conclusion: 기술 실행과 tag 품질을 분리한 한 문단
3. Scope와 coverage funnel: discovered → eligible → selected → proposed → confirmed → exported → executed → evaluated
4. Pair registry: ordered Events, v3/v4 group, scenario/tag/case 수, creation/reuse 여부, `quality_status`, `coverage_status`
5. Aggregate: macro headline, micro 보조, v3→v4 delta, coverage gaps
6. Pair verdict matrix: 다섯 품질 축과 pair overall
7. 가격 분석: annual/monthly, region, tag edge, responsive/tie/reversal, worst pair
8. Mechanism/expressiveness: parameter signature, exact input, upstream propagation, one-sided coverage
9. Proposal/confirmation: IDs, payload hash, rollback/read-back/reconfirm, token/time/retry
10. Failed-attempt register: stage/category/native rc/cause/remediation/cleanup/retry lineage
11. Environment/XLSM/disk: interpreter, imports, workbook count, warning, size estimate
12. DB·v4 isolation: baseline/after fingerprint와 allowlist delta
13. Limitations/COVERAGE LIMIT과 다음 확장 우선순위
14. Exact rerun/resume command와 artifact index

Pair 상세 raw payload를 본문에 반복하지 않는다. Manifest/evaluation 경로와 hash를 연결하고 핵심 parameter/value/slot만 표로 보여준다.

## 7. PNG 계약

`campaign_summary.png`는 dashboard가 아니라 세로형 executive report figure로 만든다.

- 상단: campaign quality overall과 coverage status를 분리하고, pair/case coverage, engine success, macro verdict를 표시
- 중단: v3/v4 macro strict/tie/reversal과 pair×quality-axis matrix
- 하단: pair별 alignment 분포, responsive region, worst pair와 failed-attempt footer
- missing은 `N/A`, failure는 실패 색상, tie와 reversal은 서로 다른 고정 색상으로 표시
- 모든 case 상세를 작은 글씨로 밀어 넣지 않고 MD로 넘김
- footer에 policy version, epsilon, 분모, evidence hash를 표시
- 외부 font/CDN 없이 결정적으로 렌더링하고 잘림·겹침·단위·색상 범례를 육안 검수

Pair가 많으면 상위 summary와 worst/review pair만 PNG에 표시하고 전체 matrix는 MD에 둔다. Pair별 PNG는 내부 진단 artifact로 선택적으로 보존한다.

## 8. 최종 상태

Campaign의 기술 실행과 가격 품질 상태를 각각 표시한다.

- Technical: 모든 계획·비제외 case와 evidence가 성공하면 `PASS`; 미복구 실패가 있으면 `FAIL`; 실행 권한 부족은 `COVERAGE LIMIT`
- Alignment quality: 어느 comparable edge에서든 reversal이 있거나 pair quality가 `FAIL`이면 `FAIL`; reversal 없이 partial/indeterminate가 있으면 `REVIEW`; 모든 comparable pair가 aligned이고 coverage가 `FULL`일 때만 `PASS`
- Coverage: `FULL|PARTIAL|NONE`을 quality와 별도로 표시한다.
- Publication overall: 어느 축이든 `FAIL`이면 `FAIL`; quality가 PASS여도 coverage가 `PARTIAL`이면 `REVIEW · COVERAGE LIMIT`; coverage가 `NONE`이면 primary 상태를 `COVERAGE LIMIT`으로 표시한다. 모든 필수 축이 PASS이고 coverage가 `FULL`일 때만 `PASS`다.

완료 engine run 성공률과 campaign attempt 성공률을 별도로 표시한다. `9/9 engine PASS` 같은 기술 결과만으로 가격 tag 정합성을 PASS로 결론내리지 않는다.
