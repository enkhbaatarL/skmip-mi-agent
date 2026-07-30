# Backoffice Design Specification

## 1. 목적과 기준

이 문서는 `local/images/ui`의 AI Market Insights > AI Forecast 스크린샷을 기준으로 Backoffice 화면의 IA, 레이아웃, 컴포넌트, 상태, 시각 토큰, 반응형/접근성 기준을 정의한다.

Backoffice는 Scenario Group 생성과 검토를 위한 내부 운영 도구다. 화면은 마케팅성 랜딩이 아니라 표, 입력, 검증 결과, 생성 결과를 빠르게 확인하는 업무 콘솔이어야 한다. 기본 톤은 흰 배경, 얇은 구분선, 절제된 블루 포인트, 높은 정보 밀도다.

## 2. IA

### 2.1 전역 쉘

모든 화면은 동일한 전역 쉘을 사용한다.

- 최상단 유틸리티 바: 좌측 `SK gas`, 우측 `Notice`, `Help Center`.
- 메인 헤더: 원형 마크, `AI Market Insights`, 1차 내비게이션, 우측 유저 영역.
- 1차 내비게이션: `Dashboard`, `AI Forecast`, `Market Data`, `Position Play`.
- 현재 위치: `AI Forecast`를 브랜드 블루 텍스트와 2px 하단 라인으로 표시.
- 우측 유틸리티: 알림 아이콘, 세로 구분선, 원형 아바타 이니셜, 사용자 ID `SKGAS001`, chevron.

### 2.2 AI Forecast

`AI Forecast` 하위의 시작 화면은 `Next-Gen MI`다.

- 상위 탭: `Event List`, `Scenario Group List`.
- `Event List`: 원천 이벤트를 탐색하고 Scenario Design으로 진입한다.
- `Scenario Group List`: 생성된 Scenario Group을 탐색하고 상세 화면으로 진입한다.

### 2.3 Scenario Design 플로우

진입 경로: `Event List` 행의 시나리오 액션 > `Scenario Design`.

공통 구조:

- 상단 `Back` 버튼.
- 페이지 제목 `Scenario Design`.
- 2단계 stepper.
- 우측 comment/help 아이콘 버튼.
- 긴 작업 화면에서는 하단 고정 액션 바.

단계:

1. `시나리오 분기항목 및 분기기준 검토`
2. `시나리오 One-view 검토`

### 2.4 Scenario Group Detail

진입 경로: Scenario Group 생성 완료 또는 Scenario Group List 행 선택.

- 상단 뒤로가기 또는 `Scenario Group List` 버튼.
- 엔티티 라벨 `Scenario Group`.
- 제목: Scenario Group명.
- 탭: `요약`, `가정 및 실현 가능성`, `가격 전망`, `시나리오 상세`.
- 우측 액션: comment/help, overflow menu.

## 3. 화면별 레이아웃

### 3.1 공통 페이지 레이아웃

- 페이지는 전체 폭을 사용하되 콘텐츠 좌우 여백을 유지한다.
- 데스크톱 좌우 패딩: 48px.
- 태블릿 좌우 패딩: 24px.
- 모바일 좌우 패딩: 16px.
- 헤더와 본문 사이 간격: 24-32px.
- 페이지 제목과 탭/스텝 사이 간격: 24px.
- 주요 섹션 사이 간격: 40-56px.
- 섹션 제목과 콘텐츠 사이 간격: 12-16px.
- 운영 도구이므로 섹션 전체를 카드로 감싸지 않는다. 카드 형태는 반복 데이터 객체, 입력 블록, 상세 패널에만 사용한다.

### 3.2 Event List

목적: 이벤트를 찾고 시나리오 생성을 시작한다.

구조:

- 제목 `Next-Gen MI`.
- 탭 `Event List`, `Scenario Group List`.
- 섹션 제목 `Event List`.
- 필터 바.
- 이벤트 테이블.
- 우측 floating comment/help 버튼.

필터 바:

- 상태 segmented control: `전체`, `신규`, `갱신`.
- `카테고리` dropdown.
- 기간 shortcut `1개월`과 날짜 범위 `2026-06-02 - 2026-07-02`.
- 정렬 dropdown `최신순`.
- `추천 항목만 보기` toggle.
- 키워드 검색 input, placeholder `이벤트명으로 검색`, 검색 아이콘.

테이블 컬럼:

- 상태 badge: `U`, `N` 같은 단문 상태를 pastel 배경 원형/라운드 배지로 표시.
- 일시.
- 카테고리.
- 이벤트명.
- 시장 지표: `JKM`, `TTF`, `HH`.
- 시나리오 액션.

행 상태:

- 기본 행은 흰 배경과 얇은 하단 divider.
- hover 또는 선택 후보 행은 매우 옅은 gray 배경.
- 이벤트명은 한 줄 유지가 기본이며, 좁은 폭에서는 2줄 clamp 후 tooltip 또는 상세 진입으로 원문 확인.
- 시장 지표는 `S`/`L` 라벨과 작은 막대 아이콘을 조합한다.
- 시나리오 생성 가능 행은 sparkle 아이콘 버튼, 단순 이동 행은 chevron 아이콘 버튼을 사용한다.

### 3.2.1 Scenario Group List

목적: 생성된 Scenario Group을 찾고, 상세로 진입하거나 로컬 테스트 데이터를 soft delete한다.

구조:

- 제목 `Next-Gen MI`.
- 탭 `Event List`, `Scenario Group List`.
- 섹션 제목 `Scenario Group List`.
- 필터 바.
- Scenario Group 테이블.
- 삭제 확인 모달.
- 우측 floating comment/help 버튼.

필터 바:

- 키워드 검색 input, placeholder `시나리오 그룹명, 이벤트명, ID로 검색`, 검색 아이콘.
- `상태` dropdown.
- `단계` dropdown.
- 기간 shortcut과 날짜 범위.
- 정렬 dropdown `최신순`.
- `삭제 항목 포함` toggle. 기본값은 off.
- 우측 `새로고침` icon button.

테이블 컬럼:

- Scenario Group ID.
- Scenario Group명.
- Base Event: 이벤트명 또는 `miEventId`.
- Status.
- Stage.
- 시나리오 수.
- Signpost 수.
- 업데이트 일시.
- 삭제 상태.
- 액션.

행 상태:

- 기본 행은 Event List와 같은 밀도의 흰 배경과 얇은 하단 divider를 사용한다.
- hover 행은 매우 옅은 gray 배경으로 표시한다.
- 상세 진입은 chevron 또는 external-detail icon button을 사용한다.
- 삭제는 trash icon button을 사용하며 danger 색을 과하게 채우지 않고 hover/focus에서만 danger border/text를 강화한다.
- 삭제 요청 중인 행은 row-level spinner와 disabled action을 표시한다.
- soft-deleted 행은 include-deleted on 상태에서만 보이며, 행 전체를 비활성처럼 흐리게 하지 말고 `삭제됨` badge와 muted text로 구분한다.

삭제 확인 모달:

- 모달 제목은 `Scenario Group 삭제`로 표시한다.
- 본문에는 Scenario Group ID, Scenario Group명, Base Event 참조를 확인용으로 노출한다.
- 설명 문구는 soft delete이며 snapshot 계열 데이터는 hard delete하지 않는다는 점을 짧게 알린다.
- 액션은 좌측/보조 `취소`, 우측/danger `삭제`로 구성한다.
- 삭제 중에는 `삭제` 버튼에 loading 상태를 표시하고 모달 닫기와 중복 submit을 막는다.
- 실패 시 모달을 닫지 않고 error callout과 QA inspector 링크/힌트를 표시한다.
- 성공 시 기본 목록에서는 행을 제거하고, `삭제 항목 포함`이 켜져 있으면 `삭제됨` 상태로 남긴다.

빈 상태:

- 전체 데이터가 없으면 `생성된 Scenario Group이 없습니다.`와 Event List 이동 액션을 표시한다.
- 필터 결과가 없으면 `조건에 맞는 Scenario Group이 없습니다.`와 필터 초기화 액션을 표시한다.

### 3.3 Scenario Design Step 1: 분기항목 및 기준 검토

목적: 선택한 Base Event를 기준으로 생성된 시나리오 분기 목록과 기준값을 검토/수정한다.

상단:

- `Back` 버튼은 헤더 아래 좌측에 배치한다.
- stepper의 1단계는 active 상태, `진행중` badge를 붙인다.
- 2단계는 pending 상태다.

Base Event:

- 섹션 제목 `Base Event`.
- 전체 폭 selectable card.
- 1행: 이벤트명.
- 2행: 일시와 카테고리.
- 우측 chevron down으로 펼침/접힘 가능성을 표시한다.

분기 항목 테이블:

- 섹션 제목 `분기 항목 및 분기 기준 검토`.
- 테이블 헤더 좌측 `시나리오 목록`, 보조 badge `3개 이상 구성 권장`.
- 우측 상단 add icon button.
- 하단 전체 폭 add row control.

컬럼:

- 삭제 icon.
- `시나리오 목록`: text input, 첫 행은 `BC` badge 포함 가능.
- `기간`: dropdown.
- `Utilization 변화량`: dropdown.
- `발생 패턴`: dropdown.
- `회복 패턴`: dropdown.
- `대체 LNG 공급 가능성`: dropdown.

하단 고정 액션:

- 좌측: `전체 초기화`.
- 우측: `취소`, `변경사항 검토`, `검토 완료`.
- `변경사항 검토`는 dark emphasis 버튼.
- `검토 완료`는 primary blue 버튼이며 검토 조건을 통과하기 전까지 disabled 또는 약한 blue disabled 상태다.

### 3.4 Scenario Design Step 1 상태

초기 로딩:

- 페이지 쉘, stepper, Base Event 카드, 테이블 형태는 유지한다.
- Base Event와 테이블 row는 skeleton으로 표시한다.
- 중앙에 spinner와 `시나리오 설계를 불러오는 중입니다.`를 표시한다.
- mutation 버튼은 disabled 처리한다. 취소가 안전하면 `취소`만 활성화할 수 있다.

변경사항 검토 중:

- 현재 입력값은 지우지 않는다.
- 테이블 영역 전체를 흰색 반투명 overlay로 덮는다.
- 중앙에 spinner와 `변경사항을 검토하고 있습니다.`를 표시한다.
- 입력, dropdown, 삭제, 추가, 액션 버튼은 disabled 처리한다.

검토 경고:

- 테이블 아래에 `변경사항 검토 결과를 확인해 주세요` 안내 문구를 둔다.
- 그 아래 full-width warning callout을 표시한다.
- callout은 warning icon, 라벨 `값 조합 적합성`, 설명 문장, 우측 `확인 후 수정 권장` 텍스트 액션으로 구성한다.
- 경고가 있어도 진행 가능한 정책이면 `검토 완료`를 활성화한다. 차단성 오류면 `검토 완료`는 disabled로 유지한다.

### 3.5 Scenario Design Step 2: One-view 검토

목적: Scenario Group명/설명, 시나리오 내러티브, 가능성, Signpost를 최종 검토하고 Scenario Group을 생성한다.

상단:

- stepper 1단계는 complete check 상태.
- stepper 2단계는 active 상태, `진행중` badge를 붙인다.

초기 로딩:

- 본문은 비우고 중앙 spinner와 `데이터를 로드 중입니다`를 표시한다.
- comment/help와 전역 내비게이션은 유지한다.

그룹 메타 입력:

- `시나리오 그룹명`: 한 줄 또는 낮은 높이 textarea. 우측 상단 reset/regenerate icon. 하단 우측 counter `27 / 100`.
- `시나리오 그룹 설명`: 큰 textarea. 생성된 내용은 light gray filled surface로 표시하되 수정 가능해야 한다. 하단 우측 counter `291 / 500`.

시나리오 검토 보드:

- 섹션 제목 `시나리오 검토`.
- 데스크톱에서는 가로 스크롤 카드 보드.
- 카드 폭은 440-520px 범위를 유지한다.
- 화면 우측에 다음 카드가 일부 보이도록 해 가로 스크롤 가능성을 드러낸다.
- 카드 수가 많아도 카드 폭을 과하게 줄이지 않는다.

시나리오 카드:

- 상단: 번호 badge, 선택적으로 `BC` badge, 시나리오명.
- 구분선.
- `시나리오 내러티브`: textarea, reset/regenerate icon, 내부 세로 스크롤, counter.
- `시나리오 특화 분기`: light gray assumption tile grid.
- `시나리오 가능성`: percent input과 `%` suffix. 합계 검증 대상이다.
- `주요 Signpost`: light gray list rows, edit pencil icon.

Signpost list item:

- 라벨은 한 줄 ellipsis.
- 2행에 방향/영향도 요약 예: `가능성 강화 · 매우 높음`.
- 우측 edit icon button은 36-40px hit area를 확보한다.

하단 고정 액션:

- 좌측: `전체 초기화`.
- 우측: `취소`, `시나리오 그룹 생성`.
- 생성 중에는 `시나리오 그룹 생성` 버튼에 loading 상태를 표시하고 중복 클릭을 막는다.

### 3.6 Scenario Group Detail: 요약

목적: 생성 완료된 Scenario Group의 기준 이벤트, 설명, 시나리오 가정을 읽기 전용으로 확인한다.

상단:

- `Scenario Group List`로 돌아가는 버튼.
- entity label `Scenario Group`.
- 제목: Scenario Group명.
- 탭: `요약` active.
- 우측 comment/help, overflow.

본문:

- 섹션 `요약`: 아이콘 + 제목.
- `Base Event` table block.
  - 컬럼: `이벤트`, `이벤트 유형`, `업데이트 일시`.
  - light gray surface 안에 header와 body row를 둔다.
- `시나리오 그룹 설명`: light gray content block.
- 섹션 `가정 및 실현 가능성`: 아이콘 + 제목.
- table:
  - `시나리오`
  - `기간`
  - `Utilization 변화량`
  - `발생 패턴`
  - `회복 패턴`
  - `대체 LNG 공급 가능성`
  - `실현가능성`
  - `상태`
- `상태`는 compact select로 표시하며 기본값 예시는 `대기`.

### 3.7 Scenario Group Detail: 시나리오 상세

목적: 개별 시나리오의 내러티브, 발생 확률, 주요 가정, Signpost 정의를 자세히 확인한다.

레이아웃:

- 탭 `시나리오 상세` active.
- 본문은 좌측 시나리오 목록 + 우측 상세 콘텐츠의 2컬럼.
- 좌측 sidebar 폭: 320-360px.
- 우측 콘텐츠는 남은 폭을 사용한다.

좌측 시나리오 목록:

- light gray surface.
- 상단 count 예: `6개 시나리오`.
- 각 item은 번호 badge, 선택적 `BC` badge, 시나리오명.
- active item은 흰/옅은 gray 배경, border, 더 강한 텍스트로 표시한다.

우측 상세:

- entity label `Scenario`.
- 번호 badge와 시나리오명.
- divider.
- `시나리오 내러티브`: light gray text block.
- 우측 `시나리오 발생 확률`: 별도 summary block.
- `시나리오 주요 가정`: 2-3열 tile grid.
- `Signpost 정의`: table.

Signpost 정의 컬럼:

- `Signpost Label`
- `방향`
- `영향도`
- `핵심 근거`

긴 텍스트 정책:

- 목록과 표에서는 2-3줄 clamp.
- 상세/편집 context에서는 원문 표시 또는 펼침을 제공한다.

## 4. 컴포넌트와 상호작용

### 4.1 Buttons

- Primary: blue background, white text, 6-8px radius.
- Secondary: white background, gray border, dark text.
- Dark emphasis: navy/dark slate background, white text. `변경사항 검토`에 사용.
- Danger: white background, danger border/text 또는 danger background + white text. destructive confirmation의 최종 `삭제` 액션에만 사용한다.
- Disabled: pale gray 또는 pale blue background, muted text, hover 없음.
- Icon button: 36-44px 정사각, border, 8px radius, 중앙 정렬.

아이콘 사용:

- back arrow
- trash/delete
- plus/add
- chevron down/right
- reset/regenerate
- comment/help
- notification
- overflow menu
- edit pencil
- search
- calendar
- refresh

### 4.2 Tabs

- AI Forecast 하위 page tabs: active blue text + blue underline.
- Scenario Group detail tabs: active black text + black underline.
- inactive tab은 배경 없이 neutral text만 사용한다.
- keyboard focus 시 underline과 별도로 focus ring을 제공한다.

### 4.3 Stepper

상태:

- pending: gray outline number, neutral text.
- active: blue filled number, blue text, light blue `진행중` badge.
- complete: pale blue circle 또는 blue-tinted circle + check icon.

규칙:

- 단계 사이는 thin light gray connector line.
- 현재 단계명은 줄바꿈이 되더라도 번호와 badge 정렬을 유지한다.
- 모바일에서는 label을 축약하거나 2줄까지 허용한다.

### 4.4 Tables

- Header text: 14-16px, 600, neutral gray.
- Read-only row height: 56-64px.
- Editable row height: 64-72px.
- Horizontal divider 중심, vertical grid line은 사용하지 않는다.
- editable table input 높이: 40-44px.
- 넓은 테이블은 viewport가 좁아지면 horizontal scroll을 사용한다.
- 행 액션 아이콘은 36px 이상 hit area를 확보한다.

### 4.5 Inputs, Selects, Textareas

- Border: neutral border.
- Radius: 6-8px.
- Focus: blue border와 2px ring.
- Placeholder: muted text.
- Generated editable content: light gray filled surface.
- Character counter: field 하단 우측.
- Textarea resize handle이 보이면 카드 내부 간격을 침범하지 않게 한다.
- Select는 chevron down을 우측에 고정한다.

### 4.6 Badges와 Indicators

- `BC`: blue filled rounded rectangle, white text.
- `진행중`: light blue background, blue dot, blue text.
- Event status `U`/`N`: compact pastel badge.
- Scenario number: gray outline rounded badge.
- Active scenario number 또는 current step number: blue filled badge.
- 시장 mini-bar:
  - green: 가능성 강화/상승/긍정.
  - red: 약화/하락/부정.
  - gray: 중립/데이터 없음.

### 4.7 Callouts

Warning:

- Background: pale orange.
- Border: orange.
- Text: orange-brown.
- 아이콘과 라벨을 포함한다.
- 사용자에게 수정 방향을 짧게 제시한다.

Error:

- Background: pale red.
- Border: red.
- Text: dark red.
- 재시도 또는 수정 가능한 위치를 안내한다.

Info:

- Background: light blue.
- Border: pale blue.
- Text: brand blue 또는 dark text.

### 4.8 Loading

- content shape가 명확하면 skeleton을 먼저 사용한다.
- agent 단계 대기처럼 shape를 확정할 수 없으면 중앙 spinner와 짧은 메시지를 사용한다.
- overlay loading은 기존 입력값을 보존하고 mutation만 막는다.
- loading 메시지:
  - `시나리오 설계를 불러오는 중입니다.`
  - `변경사항을 검토하고 있습니다.`
  - `데이터를 로드 중입니다`
  - `시나리오 그룹을 생성하고 있습니다.`

### 4.9 Empty

- Event List empty: 필터 바는 유지하고 table body 중앙에 empty message와 필터 초기화 액션을 제공한다.
- Scenario Group List empty: 생성 시작을 위해 Event List로 이동하는 액션을 제공한다.
- Step 1 empty: add row control을 유지하고 최소 3개 권장 기준을 안내한다.
- Step 2 empty: one-view 데이터 없음 메시지와 재생성/재시도 액션을 제공한다.

### 4.10 Dialogs

- 삭제 확인처럼 되돌리기 어려운 액션은 modal dialog를 사용한다.
- dialog width는 420-520px 범위를 기본으로 한다.
- 제목, 대상 요약, 설명, error callout, action row 순서로 구성한다.
- 배경 overlay는 검정 20-32% opacity로 충분히 구분하되 본문을 과하게 어둡게 하지 않는다.
- Esc와 close button은 요청 전에는 허용하고, 요청 중에는 중복 작업 방지를 위해 disabled 처리할 수 있다.
- destructive primary action은 항상 우측에 두고 `삭제`처럼 동작을 직접 표현한다.

### 4.11 Validation

- field 단위 오류는 해당 input 아래에 표시한다.
- row 조합 오류는 row highlight 또는 table 아래 callout으로 표시한다.
- table 전체 오류는 action bar 바로 위나 table 아래에 persistent callout으로 표시한다.
- 확률 입력은 숫자 범위 0-100, 전체 합계 100 여부를 검증한다.
- 오류가 있어도 사용자의 입력값을 삭제하지 않는다.

## 5. 시각 스타일 토큰

기존 프론트엔드 토큰이 있다면 우선 사용하되, 스크린샷 기준 기본값은 아래와 같다.

### 5.1 Color

```css
:root {
  --color-brand-blue: #2f55d4;
  --color-brand-blue-hover: #2446b8;
  --color-brand-blue-soft: #eaf2ff;
  --color-dark-emphasis: #243a5a;

  --color-text-primary: #111827;
  --color-text-secondary: #4b5563;
  --color-text-muted: #8a95a3;
  --color-text-disabled: #b8c0cc;

  --color-bg-page: #ffffff;
  --color-bg-soft: #f7f9fb;
  --color-bg-header-utility: #d6dee9;
  --color-bg-disabled: #f1f4f8;

  --color-border: #dde3ea;
  --color-divider: #e7ebf0;

  --color-success: #2f9e44;
  --color-danger: #d64545;
  --color-danger-hover: #b93636;
  --color-danger-bg: #fff1f1;
  --color-warning: #f97316;
  --color-warning-bg: #fff7ed;
}
```

### 5.2 Typography

```css
font-family: Inter, Pretendard, "Noto Sans KR", system-ui, -apple-system,
  BlinkMacSystemFont, "Segoe UI", sans-serif;
```

- Page title: 32-36px, 700.
- Detail title: 28-32px, 700.
- Section title: 20-24px, 700.
- Subsection title: 16-18px, 700.
- Table/header label: 14-16px, 600.
- Body: 15-16px, 500.
- Meta/helper: 13-14px, 500.
- Button: 14-16px, 600.
- Korean body line-height: 1.55-1.7.
- Dense table line-height: 1.35-1.45.
- Letter spacing은 0을 기본으로 한다.
- viewport width 기반 font-size scaling은 사용하지 않는다.

### 5.3 Spacing

```css
:root {
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
  --space-10: 40px;
  --space-12: 48px;
  --space-14: 56px;
}
```

### 5.4 Radius, Border, Shadow

- Standard radius: 8px.
- Compact controls: 6px.
- Icon buttons: 8px.
- Avatar/status badge: circular 또는 small pill.
- Border: 1px solid neutral border.
- Shadow는 최소화한다. 하단 고정 액션 바에는 subtle top shadow 또는 border만 사용한다.
- 중첩 카드는 피한다.

### 5.5 Sizing

- Header utility bar height: 32px 내외.
- Main header height: 80-88px.
- Icon button: 36-44px.
- Text input/select height: 40-44px.
- Editable table row: 64-72px.
- Bottom action bar height: 72-88px.
- Scenario card width: 440-520px.
- Scenario detail sidebar width: 320-360px.

## 6. 반응형 기준

### 6.1 Desktop >= 1200px

- 전역 내비게이션을 모두 노출한다.
- Event List와 상세 표는 전체 폭을 사용한다.
- Step 1 editable table은 컬럼을 모두 표시한다.
- Step 2 scenario cards는 가로 보드로 표시한다.
- Scenario Detail은 좌측 sidebar + 우측 detail 2컬럼을 유지한다.
- 하단 액션 바는 fixed로 유지하고 body bottom padding을 충분히 둔다.

### 6.2 Tablet 768-1199px

- page padding을 24px로 줄인다.
- 긴 테이블은 horizontal scroll container로 감싼다.
- editable table 컬럼을 억지로 압축하지 않는다.
- scenario card는 최소 폭을 유지하고 가로 스크롤한다.
- Scenario Detail sidebar는 280-320px까지 축소 가능하다.

### 6.3 Mobile < 768px

- 전역 내비게이션은 menu 또는 compact nav로 접는다.
- page padding은 16px.
- page title은 28-32px 범위로 낮춘다.
- stepper label은 2줄까지 허용하거나 단계 번호 중심 compact 표시로 전환한다.
- Event List와 editable table은 horizontal scroll을 기본으로 한다.
- 필터 바는 1열 stack 또는 2열 grid로 재배치한다.
- 하단 액션 바는 2줄 또는 full-width primary + secondary row로 전환한다.
- Scenario Detail은 sidebar 대신 dropdown 또는 horizontal chips로 시나리오를 선택하고, 상세 콘텐츠를 아래에 배치한다.

## 7. 접근성 기준

- 모든 icon-only button에는 accessible label과 hover/focus tooltip을 제공한다.
- keyboard로 tabs, buttons, inputs, dropdowns, row actions에 접근 가능해야 한다.
- focus state는 색상 변화만이 아니라 outline/ring으로 표시한다.
- warning/error/success는 색상만으로 구분하지 않고 아이콘과 텍스트를 함께 사용한다.
- 텍스트와 배경 contrast는 WCAG AA를 목표로 한다.
- disabled 버튼은 시각적으로 구분하되, disabled 사유는 인접 helper text 또는 tooltip으로 설명할 수 있어야 한다.
- loading overlay는 `aria-busy` 또는 live region으로 상태를 알린다.
- spinner만 단독으로 두지 않고 짧은 문구를 함께 제공한다.
- form validation 오류는 `aria-describedby`로 해당 field와 연결한다.
- row action hit target은 최소 36px, 권장 40px 이상이다.
- 가로 스크롤 영역은 keyboard 조작과 스크롤 가능성 시각 단서를 제공한다.

## 8. 구현 메모

- 우선 재사용 쉘 컴포넌트를 분리한다: `AppHeader`, `PageTabs`, `Stepper`, `BottomActionBar`.
- Step 1 editable table과 Step 2 scenario card board는 별도 컴포넌트로 관리한다.
- wide workflow는 축소보다 horizontal scroll을 우선한다.
- agent/API 호출 중에는 기존 생성 결과와 사용자 수정값을 유지한다.
- reset/regenerate icon은 해당 섹션 단위로만 작동하도록 범위를 명확히 한다.
- 로컬 테스트용 raw JSON/debug panel이 필요하면 primary workflow 아래에 접힌 영역으로 둔다.
- 이 문서는 화면 설계 기준이다. API body, callback, status/stage 전이는 별도 아키텍처 문서를 따른다.
