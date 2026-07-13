# LUT + Basecase 통합 활용 최종 설계

작성일: 2026-07-09
대상 파라미터: GDP, PMI, PowerMix, Temperature, LiqUtilAdjustment

## 1. 전제와 목표

- **LUT**(`resources/lut/*.csv`)는 모델의 default 전체 기준값이다.
- **basecase**(`resources/basecase/*.xlsm`)는 사용자가 LUT 중 일부 좌표를 override한 값이다.
- 현재 propose flow는 basecase만 근거로 사용하므로, basecase 밖 국가·기간·에너지원·train은
  Step2 slot 후보에서 누락되고 Step3 value 근거도 없다.
- 목표: **slot 후보 전집 = LUT**, **value 근거 = basecase(override) 우선, 없으면 LUT(default)**
  구조로 확장한다. API 계약(`basecaseValue`)은 변경하지 않는다.

## 2. 파라미터별 소스 비교 (검증 완료)

모든 수치는 운영 extractor(`utils/parameter_mapping.py`) + DB 스펙으로 추출한 basecase와
LUT CSV를 직접 대조해 검증했다.

| 파라미터 | basecase slot | LUT slot | LUT value | 동일 좌표 값 차이 |
|---|---|---|---|---|
| GDP | 12개국 × 2024–2031 (93건) | 91개국(모델 대상) × 2019–2031 | △ 절대값(BUSD) → 성장률 파생 | 85/93 |
| PMI | 2개국 × 4개년 (48건) | 84개국 × 2024–2031 × 12월 | ✕ 전부 50 = **의도된 중립 디폴트** | 48/48 |
| PowerMix | 11개국 × Gas (57건) | 84개국 × 10 에너지원 × 2022–2031 | ○ 동일 단위(비율 소수) | 57/57 |
| Temperature | 10개국 × 1–3월 (150건) | 84개국 × 12월 × 2024–2031 | △ HDD/CDD → 기온 역산 | 150/150 |
| LiqUtilAdjustment | 24개국 311 train (21,656건) | 24개국 350 train × 2017–2031(+2050 terminal) | ○ 동일 스케일 | 20,230/21,569 |

핵심 사실:

- basecase slot은 LiqUtil business key 87건을 제외하면 전부 LUT에 포함된다 (LUT ⊇ basecase).
- 동일 좌표에서 basecase 값은 거의 전부 LUT 디폴트와 다르다 → "override" 전제가 데이터로 확인됨.
- PowerMix는 국가·연도별 10개 source 합 = 1.0이 LUT 전 그룹(840개)에서 성립한다.
- Temperature LUT에서 HDD>0 ∧ CDD>0 좌표 0건, HDD=CDD=0 좌표 0건 → 역산식 모호성 없음.
- `Full Country List`(91) 중 `Other ...` 집계 7개국은 PMI만 reference 매핑
  (Other Africa→Iran, Other America N→United States, Other America S→Brazil, Other Asia→Japan,
  Other Australia→Australia, Other Europe→Portugal, Other Middle East→Qatar)으로 해소 가능하고,
  GDP/PowerMix/Temperature는 LUT 디폴트가 없다.

## 3. 매핑 실검증 결과

basecase 각 record의 slot 좌표로 LUT를 실제 조회한 결과
(상세: `tests/reports/model_parameter_agent/lut_basecase_same_slot_value_check_20260709.md`):

| 파라미터 | 매칭률 | 비고 |
|---|---:|---|
| GDP | 100% (93/93) | 성장률 파생값이 미조정 좌표 8건과 소수점까지 일치 → 파생식 = basecase 산식 확인 |
| PMI | 100% (48/48) | 직접 조회로 충분, reference fallback은 `Other ...`에서만 필요 |
| PowerMix | 100% (57/57) | |
| Temperature | 100% (150/150) | HDD/CDD 역산 전 좌표 적용 |
| LiqUtilAdjustment | 99.6% (21,569/21,656) | 미매칭 87건 = LUT에 없는 3개 train(Coral North FLNG, Pan American LNG, Mexico Pacific T3)의 basecase-only override — 조인 로직 문제 아님 |

### 파라미터별 변환·조인 스펙

| 파라미터 | LUT 파일 | 변환 | 조인 키 |
|---|---|---|---|
| GDP | `LUT_BCInput_t2` (+`General_t6` 필터) | `growth(y) = GDP(y)/GDP(y−1) − 1`, 2019년 이후만. **전년 GDP=0이면 성장률 생성 금지** — 전기간 0인 6개국(Falkland Islands, Martinique, Neutral Zone, Nigeria/Sao Tome JDZ, Saint Pierre and Miquelon, Western Sahara)은 제외 (169−6=163) | Country + Year |
| PMI | `PMIInput_t2` (+`t1` reference 매핑) | 연도 metric 열 melt. 값 50 고정 | Country + Year + Month (없으면 reference country로 재조회) |
| PowerMix | `LUT_BCInput_t3` (+`General_t6` 필터) | 없음 (long form) | Country + Year + Energy Source |
| Temperature | `WeatherInput_t1`(HDD) + `t2`(CDD) | melt 후 outer join → `HDD>0: 18−HDD/30 / CDD>0: 18+CDD/30 / else 18` | Country + Year + Month |
| LiqUtilAdjustment | `BCLiquefaction` | `Infra Life Cycle != Closed` + horizon(2024–2031) 필터 | **Country + Plant + Train + Year + Month** (canonical). Period는 조인 키가 아니라 sanity check — 현재 데이터 mismatch 0건이며, 향후 LUT 갱신으로 어긋나면 warning |

### LiqUtil Nameplate Capacity 처리

- basecase `Nameplate Capacity`(MTPA) ↔ LUT `LNG train capacity (Million tonnes LNG per month)` × 12.
  **Bcm/month 컬럼 사용 금지** (부피 단위, 톤과 ≈1.36배 차이).
- MTPM×12 정합성: 311 train 중 297개 정확히 일치. 불일치 14개(Damietta, GLNG, PNG LNG,
  Golden Pass, QatarGas T8–T13)는 basecase가 공칭 명판용량을 별도 관리하는 케이스로,
  어떤 환산으로도 LUT에서 유도 불가.
- LUT의 MTPM은 train당 사실상 상수(350개 중 348개 전 기간 동일, Damietta T1·Oman T3만 2개 값).
  → horizon(2024–2031) 내 값을 취하면 단일 값이며, unique 2개 이상이면 최신값 + warning.
- **채움 규칙**: basecase에 있는 train → basecase capacity 그대로 / LUT-only train → MTPM×12 (근사 표기).
  Life Cycle도 동일 (basecase 우선, LUT-only는 `Infra Life Cycle`). metadata는 조인 키에서 제외
  (metadata까지 exact 매칭 시 common 21,569 → 15,903으로 급감: lifecycle 차이 4,496건, capacity 차이 1,170건 —
  basecase 쪽이 최신).

## 4. 설계

### 4.1 2-계층 lookup과 effective record

```
slot 후보 전집:      LUT (basecase-only 좌표 87건은 union으로 포함)
value 근거 우선순위:  basecase(override) > LUT(default)
```

동일 좌표는 effective record로 병합해 Step2/Step3에 공급한다:

```python
{
    "axes": {...},
    "value_name": "...",
    "effective_value": 0.042,          # 현재 기준값
    "effective_source": "basecase" | "lut",
    "basecase_value": 0.042,           # override 값 (없으면 None)
    "lut_value": 0.039,                # 디폴트 값 (없으면 None)
    "basecase_reference_id": "Demand:...",
    "lut_reference_id": "lut:...",
}
```

병합 우선순위:
1. basecase 있음 → `effective = basecase`, LUT 디폴트 병기 (조정 폭 판단 근거)
2. basecase 없음 + LUT 있음 → `effective = lut`
3. basecase만 있음 (LiqUtil 87건) → basecase-only로 포함
4. 둘 다 없음 → 제외 또는 warning

### 4.2 LutRepository

`utils/lut_repository.py` (신규). CSV를 기동 시 1회 로드하는 read-only 모듈 싱글톤.

- 로드 시점에 파생 계산(GDP 성장률, 기온 역산, melt, LiqUtil 필터)까지 완료해
  lookup dict / indexed DataFrame으로 캐시 — 요청 hot path에 pandas 연산 금지.
- `slots(parameter)` — 유효 slot 축 조합 전집 (dedup)
- `records(parameter, axes_filter)` — basecase record와 동일 스키마 + `source="lut"`,
  `reference_id="lut:{file}:{row}"`
- **LUT 원본/전체 레코드는 LangGraph state에 넣지 않는다** (§5.4-1).

### 4.3 Step2 slot 선택

- slot hierarchy는 **LUT ∪ basecase union**으로 구성. Cartesian product 금지, 실존 path만.
- 각 path에 `overridden_in_basecase` 표시 → 시나리오와 무관한 기존 override 덮어쓰기 방지.
- LiqUtil hierarchy는 **경로(Country>Plant>Train)만** 포함하고 lifecycle/capacity metadata는
  Step3/후처리에서 채운다 (토큰 절약).
- slot country 전집: `Full Country List` 91개 (LiqUtil은 BCLiquefaction 24개국).
  단 GDP/PowerMix/Temperature의 `Other ...` 7개국은 LUT 디폴트가 없으므로 option에서 제외하거나
  warning 대상으로 표시.
- Year/Month 후보는 LUT 시계열 범위로 검증 (GDP 2019–2031, PMI/Temperature 2024–2031,
  LiqUtil은 horizon 2024–2031로 클램프).
- slot 검증(`validation.py`)은 `basecase_slots ∪ lut_slots` 기준으로 확장.
- 프롬프트에 "시나리오와 직접 관련된 slot만 선택" 지침 + 파라미터당 slot 수 상한 명시
  (전집 확대에 따른 출력 폭주 방지).

### 4.4 Step3 value 산정

- **역할 분리 원칙**: lookup·변환(성장률, 기온 역산, 환산)은 전부 서버가 계산해서 넣는다.
  LLM에는 "값을 찾는 작업"이 아니라 **"조정 여부와 폭 판단"만** 맡긴다.
- 선택 slot으로 필터한 effective value group을 제공. LLM 지침:
  - `effective_value`가 현재 기준값
  - `basecase_value`가 있으면 사용자 override이므로 `lut_value`보다 우선
  - 없으면 `lut_value`가 default 기준
- 기존 캡 `model_parameter_max_value_prompt_basecase_records`(기본 100)를 effective record에 동일 적용.
  LUT 쪽에도 동일한 방어선 설정을 신설한다:
  `model_parameter_max_lut_slot_options`, `model_parameter_max_effective_reference_records`.
  캡 적용 시 임의 sampling 금지 — **deterministic sort 후 cap**하고, 초과분은 warning으로 드러낸다
  (같은 입력 → 같은 프롬프트 재현성 보장).
- 파라미터별 특칙:
  - **GDP**: sanity 범위는 전체(−30%~+62%)가 아니라 모델 대상국 × 2024–2031 한정 **−5.5% ~ +13.2%**.
    2018년(전년 없음)과 전년 누락 국가·연도는 디폴트 생성 금지.
  - **PMI**: slot만 LUT에서, value 기준선은 "중립선 50" 상수 (의도된 디폴트로 확정).
    제안 sanity는 PMI 관례 범위(30–70) 상수화. `Other ...`는 t1 reference 매핑으로 lookup하되
    출력 slot Country는 demand country 유지.
  - **PowerMix**: 대상 국가의 전체 source mix(합=1)를 함께 공급. 단일 source 제안 구조에서는
    rationale에 잔여 source 보정 필요성 명시, 복수 source 제안 시 합계 검증 추가.
  - **Temperature**: 국가·월별 역산 기온을 기준값으로. sanity는 전역 범위(−15.4~38.1)가 아니라
    해당 국가·월 기준값 ± 허용 delta.
  - **LiqUtilAdjustment**: business key 조인으로 train 단위 기준값 공급.
    value > 1.0은 양쪽 모두 존재(초과 가동)하므로 0~1 hard validation 금지, 1.0 초과는 warning만.
    Country+Plant 필터 필수 (국가 단위 필터만으로는 record 수천 건).
- sanitizer: `_patch_basecase_value()`에 `lut:` prefix reference id 허용, effective record 기준 패치.

### 4.5 현행 flow 통합 지점

| 현행 | 변경 |
|---|---|
| `load_basecase_samples()` — basecase만 로드 | basecase + LUT 로드 후 effective 병합. state 필드 `lut_records`(compact), `effective_reference_records` 추가, `basecase_records` 호환 유지 |
| `_build_parameter_slot_tasks()` | LUT ∪ basecase union hierarchy + override 표시 |
| `filter_basecase_records_by_slots()` | effective record 기준 필터 |
| `_build_parameter_value_tasks()` | effective value group (`effective_value`/`basecase_value`/`lut_value`) |
| `_patch_basecase_value()` | `lut:` reference id 허용 |

**API 계약 유지**: `basecaseValue`에 effective value를 넣는다. `referenceSource` 등 신규 필드는
프론트 계약 변경이므로 후속 분리. 출처 구분은 내부 rationale/warning에만 기록.

## 5. 성능 검토 (실측)

### 5.1 프롬프트 크기 — 수용 가능

| 항목 | 크기 | 토큰 추정 |
|---|---|---:|
| LiqUtil hierarchy (LUT union 349 trains, 경로만) | 16.4KB | ≈4,100 (현행 311 trains와 유사) |
| PowerMix hierarchy (84국 × 10 source) | 8.6KB | ≈2,100 (실질 최대 증가분) |
| country 91개 리스트 | 1.1KB | ≈280 |

5개 파라미터 합산 Step2 증가 ≈ **+5~7k 토큰**. Step3는 캡 100건 × effective record(레코드당 ≈2배)
= ≈6k 토큰으로 안전.

### 5.2 LLM 시간 — 호출 횟수 불변

구조 유지로 호출 횟수 동일, 입력 증가로 호출당 +1~2초 수준. 리스크는 slot 선택 수 증가 →
출력 길이 증가이며 §4.3의 프롬프트 상한으로 통제.

### 5.3 CSV 로드 — 병목 아님

CSV 8개 총 10.7MB, pandas 전체 로드 **0.10초**, 메모리 **29.3MB**(BCLiquefaction 26MB).
모듈 싱글톤 1회 로드 + 파생 계산 선수행으로 요청당 비용 0. 현재 실제 병목은 openpyxl xlsm 추출이며
LUT 도입은 비용을 더하지 않는다.

### 5.4 Side effect와 완화책

1. **state 비대화 (최우선)**: LUT 41k행을 state에 넣으면 직렬화/checkpoint ~3배.
   → LUT 원본은 프로세스 repository에 유지, state에는 compact option + 필터된 effective record만.
   로드 시 non-Closed + horizon 필터로 41k → ≈30k.
2. **근거 없는 제안**: LUT 디폴트 없는 slot(`Other ...`)은 option 제외 또는 warning.
3. **회귀**: basecase-only 좌표의 `basecaseValue` 출력 동일성 회귀 테스트 필수.
4. **동시성/multi-worker**: read-only 싱글톤이라 lock 불필요. 단 캐시는 worker 수만큼 복제되므로
   (worker당 ≈30MB) worker 수 증가 시 메모리 사용량을 로그로 확인.
5. **LUT 갱신**: CSV 교체 시 재기동 필요 — 배포 절차 명시. 개발 편의용 mtime/checksum 재로드는
   dev 옵션으로만 둔다.
6. **비용**: 입력 토큰 증가분만큼 선형 증가. hierarchy 경로만 유지로 최소화.
7. **로그/DB 저장량**: full LUT record를 LLM trace나 proposal DB에 저장하지 않는다.
   source summary, 선택된 effective record, warning만 저장.
8. **관측성**: LLM call trace에 prompt size, candidate count, selected slot count,
   effective record count, source summary를 남겨 프롬프트 비대·slot 과다 선택을 조기 감지.

## 6. 구현 순서

1. `LutRepository` + 변환·조인 스펙(§3) + 파생 로직 단위 테스트
   (HDD·CDD 동시 양수 0건, PowerMix 합=1, GDP 첫해 제외, LiqUtil MTPM 상수성 검증 포함)
2. effective record 병합 유틸 (normalized coordinate key, basecase 우선, source summary)
3. slot 검증 확장 (`basecase ∪ lut`) — 즉시 효과: 폭염 등 basecase 밖 slot 허용
4. Step2/Step3 packet·프롬프트 빌더 수정 (§4.3, §4.4)
5. sanitizer 보강 (`lut:` reference id)
6. value 검증 규칙 (PowerMix 합 정합성, 국가·월별 기온 sanity, GDP 대상국 성장률 범위)
7. logging/trace 보강 (prompt size, candidate/slot/record count, source summary)
8. 테스트: LUT loader 단위 / 병합 우선순위 / LUT-only slot Step2 포함 여부 / basecase-only 회귀

### 6.1 테스트 기대값 fixture

단위·매핑 테스트는 아래 검증된 수치를 기대값으로 고정한다 (LUT 파일 갱신 시 함께 갱신):

| 항목 | 기대값 |
|---|---|
| GDP raw / 성장률 record / 국가 | 2,365 / 2,118 / 169 (성장률 가능 163, 전기간 0인 6개국 제외) |
| PMI t1 demand / reference 국가 | 91 / 84 |
| PMI t2 long record / 값 | 8,064 / 전부 50.0 |
| PowerMix record / source / 합계 | 8,399 / 10종 / 국가·연도 합 1.0 (840그룹 전부) |
| Temperature 파생 record | 8,064 (HDD 분기 3,848 + CDD 분기 4,216, 동시 양수 0) |
| LiqUtil raw record / train | 41,103 / 350 (non-Closed 349) |
| 매핑률 | GDP·PMI·PowerMix·Temperature 100%, LiqUtil 99.6% (21,569/21,656) |
| LiqUtil unmapped 87건 | Mexico Pacific T3(Phase 2) 36 + Pan American LNG 27 + Coral North FLNG 24 |
| LiqUtil mismatch | Period 0건 / lifecycle 4,496건 / capacity 1,170건 |
| 동일 좌표 값 차이 | GDP 85/93, PMI 48/48, PowerMix 57/57, Temperature 150/150, LiqUtil 20,230/21,569 |

### 6.2 완료 기준 (Definition of Done)

- LUT repository가 요청마다 CSV를 다시 읽지 않는다.
- Step2가 `basecase ∪ lut` slot universe를 사용하고, LUT-only slot이 valid로 인정된다.
- Step3가 `basecase override > LUT default` effective value를 사용한다.
- GDP 성장률·Temperature 역산·LiqUtil MTPA 환산이 서버에서 계산된다.
- `LNG train nameplate capacity (Bcm per month)` 컬럼은 Nameplate Capacity 생성에 사용되지 않는다.
- 프롬프트 크기 방어 설정(§4.4)과 LLM trace 카운트가 존재한다.
- 기존 basecase 좌표의 `basecaseValue` 출력이 이전과 동일하다 (회귀).
- §6.1 fixture의 매핑률·mismatch count가 테스트에서 재현된다.

## 7. 참고 문서

- 상세 비교·검증: `tests/reports/model_parameter_agent/lut_vs_basecase_analysis_20260709.md`
- 동일 slot 값 비교표 (파라미터별 최대 100행): `tests/reports/model_parameter_agent/lut_basecase_same_slot_value_check_20260709.md`
- codex 교차 분석: `apps/agents/model_parameter_agent/docs/lut_basecase_slot_value_comparison_design_20260709.md`
  (business key overlap·값 차이 수치 상호 재검증 완료, effective record 모델·flow 통합 지점 본 문서에 채택)
- codex 최종 구현 명세: `apps/agents/model_parameter_agent/docs/lut_basecase_final_implementation_spec_20260709.md`
  — 본 문서에 채택한 항목: GDP 전기간 0인 6개국 성장률 제외(재검증 완료), LiqUtil canonical lookup key를
  Year/Month 기준으로 하고 Period는 sanity check로 강등(향후 LUT 갱신 대비), LUT용 방어 설정 신설
  (`model_parameter_max_lut_slot_options`, `model_parameter_max_effective_reference_records`),
  deterministic sort/cap 재현성 원칙, "서버가 lookup·계산, LLM은 조정 판단" 역할 분리,
  LLM trace 카운트, 로그/DB에 full LUT 저장 금지, multi-worker 캐시 복제 주의, 테스트 기대값 fixture,
  완료 기준(DoD). 본 문서에만 있는 항목: 프롬프트 토큰·CSV 로드 실측치, LiqUtil MTPM의 train당 상수성
  (350개 중 348개, Damietta·Oman만 시간 가변 → horizon 값 사용 규칙), MTPA≈MTPM×12 불일치 14개 train 목록,
  PMI 50 의도 확정.
