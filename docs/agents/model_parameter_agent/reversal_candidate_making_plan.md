이 내용은 한마디로 말하면, **지금의 “Event → Scenario → Lever → Parameter” 흐름을 거꾸로 훑어서, 앞으로 모니터링할 만한 미래 Event 후보를 먼저 만들어보자는 아이디어**입니다.

참고 자료상 현재 v4는 legacy dimension mapping이 아니라 **선택된 Dimension Value의 Lever state + active Impact Lever catalog binding**으로 raw Parameter capability를 결정합니다. 0032 v4 catalog는 master filtering 전 raw binding 이름 16개, effective active Parameter 14개에 도달하고 v1/v3 mapping은 10개에 도달합니다. 실제 runtime proposal은 v1/v3의 기존 5개와 달리 v4에서 LUT-backed 10개와 exact Basecase-only 4개를 합친 `extend14-v6` 14개를 허용합니다. 이 gate를 통과한 뒤에도 exact slot이 있어야 합니다.

allow-list gate는 Model Parameter Agent의 source matching 뒤, exact slot·값 제안 LLM과 proposal
persistence 전에만 적용됩니다. Scenario Group Agent를 비롯한 다른 Agent의 동작, confirmation,
DB·canonical·catalog checksum과 workbook artifact는 바꾸지 않습니다. capability/workbook contract와 이를
가리키는 config는 `extend14-v6`/`new-bc-v6`로 갱신됩니다.

## 1. “현재 체계를 거꾸로 사용한다”는 의미

현재 정상 방향은 대략 이렇습니다.

```text
발생한 Event
→ Scenario / Dimension / Value
→ Lever state
→ executable Parameter binding의 raw 후보
→ v4 runtime proposal allow-list 14개
→ Basecase/LUT exact slot
→ Parameter proposal
```

본문에서 제안하는 것은 이것을 반대로 탐색하는 것입니다.

```text
v4 runtime proposal에서 허용된 Parameter 14개
→ 그 Parameter로 연결되는 executable Lever
→ 그 Lever가 반복적으로 움직일 만한 조건
→ 그 조건이 나타날 수 있는 미래 시기·지역
→ 미래 Event 후보 주제
```

즉 **“무슨 일이 생길까?”부터 자유롭게 뉴스 주제를 발상하는 것이 아니라, “우리 수급모델에서 실제로 움직일 수 있는 변수가 무엇인가?”에서 출발**하는 겁니다.

이렇게 하면 최종적으로 Event를 발견했는데 정작 수급모델 Parameter로 연결할 수 없는 상황을 줄일 수 있습니다.

참고 자료에서도 v1/v3의 raw mapping 도달 범위는 10개, v4의 raw binding 도달 범위는 16개지만 두 경로 모두 runtime allow-list와 exact slot을 통과한 일부만 proposal로 올라갑니다. 따라서 **“catalog상 연결 가능”, “현재 proposal 허용”, “exact slot까지 실행 가능”은 서로 구별해야 한다**는 전제가 이미 현재 구조에 들어 있습니다.

---

## 2. `weather_demand → Temperature` 예시는 무슨 뜻인가

예를 들어 미래 LNG 시장 리스크를 찾는다고 했을 때 단순히

> “올겨울 한파 가능성”

이라고 후보를 만들면 너무 추상적입니다.

현재 모델에서 실제로 실행 가능한 것이 `Temperature`라면, **Temperature의 exact slot과 값을 결정할 수 있을 정도로 Event 후보를 구체화해야 한다**는 뜻입니다.

참고 자료에서 Temperature는 HDD/CDD를 이용해 기온 값으로 변환하는 LUT-backed Parameter이며, CDD/HDD 자체는 독립 Parameter 후보가 아닙니다.  또한 Temperature adapter는 HDD/CDD로부터 실제 기온 값을 역산하는 구조입니다.

그래서 미래 후보를 이런 식으로 잡자는 것입니다.

**나쁜 예**

> 2026년 겨울 한파 가능성

**좋은 예**

> 2026년 12월 동북아에서 평년 대비 -4~-7°C 수준의 기온 편차가 7~14일 지속되고, 월 중순에 한파가 집중될 가능성

후자가 훨씬 좋은 이유는 나중에 Scenario를 만들 때 바로 다음 정보로 연결할 수 있기 때문입니다.

```text
지역
→ 어느 Temperature slot인가?

대상 월
→ 어느 Year/Month인가?

평년 대비 기온 편차
→ Temperature를 얼마나 조정할 것인가?

지속기간·피크 패턴
→ 월평균 Temperature 조정폭을 어떻게 해석할 것인가?
```

즉 **Event 탐색 단계부터 Model Parameter가 소비할 수 있는 형태로 후보 주제를 설계**하는 겁니다.

---

## 3. 왜 `inventory_condition`은 “주 이벤트”가 아니라 증폭 조건인가

본문의 중요한 부분입니다.

> `inventory_condition`은 진입 재고에 따른 가격 증폭 조건으로만

뜻은 “재고가 낮다” 자체를 항상 독립적인 미래 Event로 만들지 말자는 것입니다.

예를 들어:

```text
한파
+
낮은 진입 재고
```

가 있다면 핵심 수요 충격은 한파이고, 낮은 재고는 그 충격이 가격으로 더 강하게 전달되게 만드는 **amplifier 또는 conditioning factor**로 보는 겁니다.

따라서

> “2026년 12월 동북아 LNG 재고 부족 가능성”

이라는 독립 후보보다는

> **“2026년 12월 동북아 7~14일 한파 가능성 + 겨울 진입 재고가 평년 하단인 경우”**

처럼 만드는 편이 낫다는 주장입니다.

구조적으로 보면:

```text
핵심 Event/Lever
weather_demand
    ↓
Temperature

조건부 증폭 요인
inventory_condition
    ↓
같은 Temperature 충격의 시장 파급력을 강화/완화
```

즉 **모든 Lever를 Parameter 하나씩 만들기 위한 독립 Event로 취급하지 않고, 인과적 역할을 나눠 사용**하자는 이야기입니다.

---

## 4. `power_generation_mix`도 항상 붙이면 안 된다는 의미

본문에서는

> 원전·수력·석탄의 대체 가능성이 실제로 불확실할 때만 별도 Lever로 결합

한다고 했습니다.

이 부분은 Parameter를 억지로 많이 연결하지 말자는 원칙입니다.

예를 들어 폭염이 발생한다고 해서 언제나 PowerMix까지 움직이는 것은 아닙니다.

### 경우 A — Temperature만 필요

> 한국 폭염 가능성
> 발전 수요는 증가하지만 원전·석탄·재생에너지 가동 구조에는 특별한 불확실성이 없음

이 경우:

```text
weather_demand
→ Temperature
```

정도로 끝낼 수 있습니다.

### 경우 B — PowerMix도 필요

> 남유럽 폭염
> 동시에 수력 발전량 저하 가능성 + 원전 냉각수 제약 가능성

이 경우에는 기온 자체뿐 아니라 **가스발전 대체 수요가 얼마나 발생할지가 별도의 불확실성**이 됩니다.

```text
weather_demand
→ Temperature

power_generation_mix
→ PowerMix
```

로 두 Lever를 같이 보는 게 자연스럽습니다.

참고 자료에서 `PowerMix`와 `Temperature` 모두 현재 LUT-backed Parameter로 실제 실행 가능한 범위에 포함되어 있습니다.

즉 “Parameter를 많이 연결할수록 좋다”가 아니라 **해당 미래 사건에서 실제 불확실성으로 작동하는 Lever만 붙인다**가 핵심입니다.

---

## 5. “주기성·선행신호와 파라미터 실행 가능성의 두 관문”은 무엇인가

본문이 제안하는 후보 생성 프로세스의 핵심입니다.

### 1차 관문 — 미래에 반복될 개연성이 있는가

먼저 미래 Event 후보 자체가 근거 없이 만들어지지 않도록 합니다.

예:

```text
계절
허리케인 시즌
정기보수
재고 주입/인출 시즌
계약 만기
신규 LNG Train ramp-up
파이프라인 유지보수
```

처럼 **반복되는 시간 창**을 먼저 잡습니다.

그다음 과거 빈도나 전망 신호 등을 이용해:

```text
Mild
Base
Severe
```

같은 가정을 만들 수 있습니다.

예를 들면:

> 2027년 GoM 허리케인 시즌에 LNG 시설 영향이
> Mild / Base / Severe 중 어느 수준일까?

`HurricaneIntensity`는 `extend14-v6` runtime proposal allow-list에 포함됩니다. 다만 GoM Year/Month,
승인된 영향 시설, 직접 재해 근거와 0~4 정수 계약을 모두 충족해야 하므로, 일반적인 허리케인 전망만으로
실행 가능 후보라고 평가하면 안 됩니다.

### 2차 관문 — 실제 모델 Parameter로 실행 가능한가

그다음 그 미래 가정을 Lever state로 표현해 현재 시스템에 넣어봅니다.

```text
미래 가정
→ Lever state
→ executable binding 존재?
→ active Parameter인가?
→ v4 runtime proposal allow-list 14개에 포함되는가?
→ Basecase/LUT exact slot 존재?
```

여기까지 통과해야 **정식 미래 Event 후보**로 승격합니다.

참고 자료에서도 source matching 직후 allow-list 밖 후보는 값 제안 전에 제외하고, Step3에는 exact 검증된
slot만 전달합니다. 부분 key·nearest·유사 시설 fallback은 사용하지 않습니다. 현재 v4 허용 14개 중 10개는
LUT-backed이고, Basecase-only 4개는 등록 LUT 없이 existing-exact workbook slot과 직접 증적이 있을 때만
proposal에 진입합니다.

따라서 여기서 말하는 “두 관문”은 사실상:

> **① 미래 사건으로서 그럴듯한가? → ② 우리 모델로 실제 계산할 수 있는가?**

입니다.

---

## 6. 예시 두 개를 실제 구조로 풀면

### 예시 A

**“2026년 12월 동북아 7~14일 한파 가능성과 낮은 진입 재고”**

이걸 구조화하면:

```text
미래 후보 Event
2026년 12월 동북아 한파

반복 발생 창
겨울철 기온 극단

핵심 불확실성
강도 / 지속기간 / 피크 시점

Primary Lever
weather_demand

실행 Parameter
Temperature

보조 조건
inventory_condition
→ 겨울 진입 재고 수준에 따른 충격 증폭

최종 질문
"평년 대비 얼마나 낮고,
몇 일간 지속되며,
재고가 어느 수준에서 겨울을 시작하는가?"
```

즉 최종 목적은 한파 뉴스를 예측하는 게 아니라 **Temperature proposal까지 갈 수 있는 형태의 미래 질문을 미리 만들어두는 것**입니다.

### 예시 B

**“2027년 7월 남유럽 폭염과 수력·원전 대체력 약화”**

```text
미래 후보 Event
2027년 7월 남유럽 폭염

Primary Lever
weather_demand
→ Temperature

조건부 추가 Lever
power_generation_mix
→ PowerMix

추가 Lever 조건
폭염 때문에 수력·원전 공급 제약이 실제 불확실한 경우에만 활성화
```

따라서 동일한 “폭염”이라도:

> 폭염만 불확실 → Temperature

와

> 폭염 + 발전 대체력도 불확실 → Temperature + PowerMix

로 나눌 수 있습니다.

---

## 7. 결국 만들고 싶은 것은 “Event 예측기”보다는 “Future Event Candidate Generator”

이 아이디어를 시스템 관점에서 보면 다음 산출물을 만드는 기능에 가깝습니다.

```text
Parameter
↓
Executable Lever
↓
Runtime Proposal Allow-list
↓
Recurring Window
↓
Observable Leading Signals
↓
Mild / Base / Severe Hypotheses
↓
Lever State
↓
Exact-slot Feasibility Check
↓
Future Event Candidate
```

예를 들어 최종적으로 이런 리스트가 나오는 것입니다.

| 미래 후보 주제                | 주요 Lever             | 예상 Parameter                  | 조건부 Lever            | 실행 가능성               |
| ----------------------- | -------------------- | ----------------------------- | -------------------- | -------------------- |
| 2026년 12월 동북아 7~14일 한파  | weather_demand       | Temperature                   | inventory_condition  | 높음                   |
| 2027년 7월 남유럽 폭염         | weather_demand       | Temperature                   | power_generation_mix | 조건부 높음               |
| 2027년 GoM 허리케인 시즌 시설 차질 | us_gom_hurricane_disruption | HurricaneIntensity       | liquefaction 계열      | 영향 시설·강도 근거 시 가능 |
| 특정 국가·부문의 직접 수요 절감 정책 | direct_gas_demand | User-Adjusted Gas Demand | 경기·발전믹스 변화와 중복 여부 | exact 부문·월·BCM 필요 |
| 재기화 터미널 증설·가동 지연 | regasification_capacity | RegasAdjustment | 프로젝트 lifecycle | exact 설비·월 matrix 필요 |
| 국가 간 PNG 계약 갱신 | png_contract_volume | PNG Contract Volume | 실제 flow·capacity 구분 | exact From/To·연도·Mt LNG 필요 |
| 연평균 LNG charter rate 전망 | lng_charter_rate | ShippingCost | 항로별 운임과 구분 | exact 연도·$/d benchmark 필요 |
| 특정 국가 LNG 수입 규제 가능성     | trade restriction 계열 | RemainingUnrestrictedAmount 등 | 계약 조건                | 현재 proposal 차단       |

여기서 마지막 컬럼이 중요합니다. 0032 v4의 **LUT-backed 활성 10개와 Basecase-only 활성 4개**는 raw resource
capability이자 현재 `extend14-v6` proposal 범위입니다. 그렇더라도 “Lever가 Parameter에 연결된다”거나 exact slot이 있다는 사실만으로
현재 실행 가능하다고 판정하면 안 됩니다.

## 핵심 의미

본문의 아이디어는 **“미래에 일어날 만한 사건을 먼저 찾고 나중에 억지로 모델 Parameter에 연결하는 방식”을 뒤집자는 것**입니다.

즉,

> **현재 v4 runtime proposal에서 허용된 Parameter 14개를 출발점으로 삼고 → 그것을 움직이는 Lever를 찾고 → 그 Lever가 반복적으로 변할 만한 미래 조건을 구성하고 → 마지막으로 exact slot과 증적까지 존재하는 후보만 우선 모니터링한다.**

는 구조입니다.

그래서 이 방식의 가장 큰 장점은 **Event 후보 생성과 Model Parameter Agent 사이의 단절을 줄이는 것**입니다. 단순히 흥미로운 미래 사건 목록을 만드는 게 아니라, 처음부터 **“발생하면 실제 수급모델을 돌릴 수 있는 미래 사건 후보”**를 만들어내려는 접근으로 이해하면 가장 정확합니다.
