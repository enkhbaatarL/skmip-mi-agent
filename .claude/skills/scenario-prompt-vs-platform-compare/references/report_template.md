# Comparison report template

Write the report in Korean. The reader is the skill user (developer/PM investigating quality). Every claim must point
to evidence: platform trace call (`[create #n]`), DB field, or workshop file and section. Separate "trace로 확인" from
"추정". Use run ids (`run_01` …) when N > 1.

Reference examples:
- N=1 (or one run of N): `references/example_report_group307.md`
- N>1 combined: `references/example_report_combined_3runs.md`

Files to produce:
- N=1: `report_run_01.md`
- N>1: `report_run_01.md` … `report_run_NN.md` (per-run, structure A) and `report_combined_Nruns.md` (structure B)

---

## A. Per-run report

```markdown
# run_XX 비교 보고서: 플랫폼(그룹 {id}) 대 워크숍 단계별 프롬프트 (Lever {catalog})

- 작성일
- 비교 대상: 플랫폼 (`POST /scenario-groups`, group id, model, MLflow trace id) / 워크숍 (guide 파일명, catalog, runner model,
  실행한 Step 범위 — 4a·6 실행 여부)
- 공통 조건: 이벤트 목록과 순서(mi_event_id), 분석 기준일, catalog
- 증적 위치: run 폴더, (있으면) 실패 run 기록

## 1. 결론
- 3~7개 bullet. 가장 큰 차이가 어느 단계에서 생겼는지, 원인 1순위, 이 run에서 새로 보인 문제, 점수 요약.

## 2. 조건 차이
| 항목 | 플랫폼 | 워크숍 | 비고 |
(모델·reasoning, 이벤트 입력 범위, 분석 기준일, 실행 시간·재시도, 실행 환경(장애·동시 부하), 채점자)

## 3. 단계별 비교
### 3.1 입력 (Step 0)
### 3.2 Fact·Impact Path (Step 1)   — Fact 수, 누락된 Fact와 영향, Primary Fact, Lever, role, balance, 질문 형태
### 3.3 Interaction (Step 2)        — relation·조합, materiality, 재시도로 바뀐 내용(trace)
### 3.4 Dimension·조합 결정 (Step 3) — 결정표 유무, 중복 Dimension, Interaction 질문 사용 여부, Choice 경계·why·pressure
### 3.5 Scenario (Step 4)           — band/확률/baseline, ceiling·floor·혼합, Interaction 적용 규칙, breakdown, 표현 문제
### 3.6 검수·보완 (Step 4a, 5, 6)
각 절은 `| | 플랫폼 | 워크숍 |` 표 + 필요한 경우 `> trace 확인:` 인용 블록.
relation 유형이 다르면 의미 차이(예: causal_link 대 amplification의 이중 계산 위험)를 한 줄로 설명한다.

## 4. 같은 기준(가이드 Step 5)으로 채점
### 4.1 Hard Gate (HG-01~12) — 플랫폼 / 워크숍 PASS·WARN·FAIL과 근거
### 4.2 의미 품질 rubric (J-01~06, J-11) — 1~5점, 근거, 평균

## 5. 원인 매핑
| 원인 | 이 run의 증상 | 판정(trace로 확인 / 추정 / 양쪽 공통) | 코드 위치 |
SKILL.md "원인 후보 체크리스트" 기준. 새로 발견한 원인은 "신규"로 표시.
```

---

## B. Combined report (N>1)

```markdown
# 종합 보고서: 플랫폼 대 워크숍 단계별 프롬프트, N회 반복 비교 (Lever {catalog})

- 작성일, 실행(group id 목록, 워크숍 run 수), 공통 조건, run별 분석 기준일, 모델, 개별 보고서·aggregate.md 경로

## 1. 결론
- 점수 평균(범위)과 run별 우위가 유지됐는지
- "반복해도 유지되는 차이"(안정성 포함)와 "run마다 하나씩 터지는 문제"를 구분
- 양쪽 공통 한계는 차이의 원인이 아님을 명시

## 2. 조건 차이와 한계
| 항목 | 내용 | 영향 |  (모델, 입력, 기준일, 장애·재실행, 채점자 편향, 표본 크기)

## 3. 단계별 비교 (N회 종합)   ← 생략 금지
3.1~3.6을 A와 같은 단위로 쓰되, 각 셀에 `run_01 값 · run_02 값 · run_03 값` 또는 "3회 모두 …"로 적는다.
run별 상세 근거는 개별 보고서를 가리킨다.

## 4. 반복 안정성 비교
### 4.1 구조 지표 (aggregate.md 해석)
| 지표 | 플랫폼 run_01 / 02 / 03 | 워크숍 run_01 / 02 / 03 |
(Fact·Path·Dimension 수, 축 구성, 조합 결정 표, Interaction, baseline, 극단 band, 제외 후보)
### 4.2 플랫폼 run별 결함 발생 표
| 결함 | run_01 | run_02 | run_03 | 빈도 |  (● 표시, 빈도 n/N)
### 4.3 워크숍 쪽 변동

## 5. 같은 기준 채점
### 5.1 Hard Gate에서 통과하지 못한 항목 (run별)
### 5.2 rubric — run별 점수, 평균, 워크숍과의 차이
| rubric | 플랫폼 run별 | 평균 | 워크숍 run별 | 평균 | 차이 |

## 6. 원인 매핑 (N회 근거 기준)
| 순위 | 원인 | 근거(빈도) | 판정 | 위치 |
매 run 모양이 달라도 근본 원인이 같으면 하나로 묶는다. 양쪽 공통·모델 변수는 별도 행.

## 7. 개선 우선순위
| 순위 | 개선 | 기대 효과(rubric) | 난이도 |

## 8. 남은 확인 사항
(모델 변수 분리, 개선 후 회귀, 다른 이벤트 조합, 테스트 데이터 정리)
```

---

## C. 마지막 채팅 요약 (보고서 파일과 별도로 사용자에게 제시)

```markdown
| 순위 | 원인 | 근거 | 조치 방안 |
|---|---|---|---|
| 1 | … | 3회 모두 … | … |

**양쪽 공통이라 이번 차이의 원인이 아닌 것**: …
**아직 분리하지 못한 변수**: 모델 차이 …
**권장 순서**: 문구 수정으로 끝나는 조치부터 적용 → 같은 이벤트로 N회 재실행해 이 보고서 표와 비교
```
