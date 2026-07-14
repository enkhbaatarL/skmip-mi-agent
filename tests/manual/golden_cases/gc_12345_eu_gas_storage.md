---
mi_event_id: 12345
event_title: "[유럽 가스 재고] EU 저장률 47.2% 도달 → 전년 대비 부족 속 재충전 수요 유지"
event_type: "외생충격"
source: "뉴로개발 도메인 전문가 피드백"
feedback_date: "2026-07-13"
---

## 원문 피드백

이 케이스는 구현 계획에 기록된 EU 가스 재고 전문가 피드백 예시를 초기
golden fixture로 옮긴 것이다. 실제 생성 증적을 확보하면 `mi_event_id`,
`scenario_group_id`, `artifacts`를 해당 증적으로 갱신한다.

## 정답 라벨

### GC-01

- type: A
- target: scenario
- expected_judge: J-01
- 지적: 이벤트는 저장률 47.2%와 전년 대비 부족을 말하는데, 시나리오가 평년 대비 +20%의 매우 여유로운 재고를 가정하면 이벤트와 모순된다.
- 인용: "재고는 평년 대비 +20% 이상으로 매우 여유로운 참여자군을 가정한다"

### GC-02

- type: B
- target: scenario
- expected_judge: J-02
- 지적: BC의 1개월 내 완충은 기관 전망과 인프라 제약의 외부 사실 확인 없이는 타당성을 확정할 수 없다.
- 비고: 외부 사실 필요 — judge 재발견을 보장하지 못하며 recall 분모를 별도 집계한다.
