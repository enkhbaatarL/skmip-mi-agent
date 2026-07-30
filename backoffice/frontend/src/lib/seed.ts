import type { EventItem, ScenarioDesignModel } from "../types";

export const seedEvents: EventItem[] = [
  {
    miEventId: 12,
    title: "[이란 제재] 미국이 걸프 피해 복구에 이란 자산 활용 검토",
    eventTime: "2026-07-02 16:55",
    category: "Geopolitical Risk",
    status: "갱신",
    recommended: true
  },
  {
    miEventId: 18,
    title: "카타르 LNG 정비 기간 연장 가능성 점검",
    eventTime: "2026-07-01 10:20",
    category: "Supply",
    status: "신규",
    recommended: true
  },
  {
    miEventId: 21,
    title: "동북아 전력 수요 하향 조정과 현물 LNG 입찰 변화",
    eventTime: "2026-06-30 08:40",
    category: "Demand",
    status: "갱신",
    recommended: false
  }
];

export const initialDesignModel: ScenarioDesignModel = {
  groupName: "이란 자산 활용 검토 이후 호르무즈 LNG 리스크 프리미엄 경로",
  description:
    "이 그룹은 미국의 이란 자산 활용 검토가 걸프 복구·제재 갈등으로 확산될 때 LNG 시장이 겪을 호르무즈 리스크 프리미엄의 지속성과 완충 여부를 본다.",
  baseEvent: seedEvents[0],
  headers: [
    { key: "period", label: "기간", displayOrder: 1 },
    { key: "supply_disruption_intensity", label: "공급 차질 - 강도", displayOrder: 2 },
    { key: "supply_disruption_pattern", label: "공급 차질 - 발생/회복 패턴", displayOrder: 3 },
    { key: "demand_response_alternative_lng", label: "대체 LNG 공급 가능성", displayOrder: 4 },
    { key: "demand_response_powermix_reduction", label: "PowerMix 수요 감소량", displayOrder: 5 }
  ],
  rows: [
    {
      localId: "scenario-1",
      scenarioId: 285,
      displayOrder: 1,
      title: "한 달 안에 잦아드는 저강도 호르무즈 경계",
      narrative:
        "한 달을 넘기지 않는 짧은 국면에서 실제 공급 차질은 낮은 수준에 그치며, 이란 자산 활용 논의는 주로 정치적 긴장으로 소비된다.",
      cells: {
        period: "1개월 이하",
        supply_disruption_intensity: "낮음",
        supply_disruption_pattern: "급차질-급회복",
        demand_response_alternative_lng: "100%",
        demand_response_powermix_reduction: "100%"
      },
      probability: "25.00",
      baselineYn: "Y",
      status: "Draft",
      signposts: [
        {
          id: "sp-1",
          label: "호르무즈 항로 보험료 상승폭",
          direction: "상승",
          impact: "JKM mild bull",
          evidence: "항로 리스크 프리미엄과 단기 선박 대기 증가 여부"
        }
      ]
    },
    {
      localId: "scenario-2",
      scenarioId: 286,
      displayOrder: 2,
      title: "반년 재건 부담이 남기는 완만한 조달 프리미엄",
      narrative:
        "여섯 달 동안 영향이 이어지지만 공급 차질 자체는 낮은 수준에 머무는 흐름이다. 운임, 보험료, 일정 지연을 가격에 나눠 반영한다.",
      cells: {
        period: "6개월",
        supply_disruption_intensity: "낮음",
        supply_disruption_pattern: "급손상-장기재건",
        demand_response_alternative_lng: "50%",
        demand_response_powermix_reduction: "50%"
      },
      probability: "15.00",
      baselineYn: "N",
      status: "Draft",
      signposts: []
    },
    {
      localId: "scenario-3",
      scenarioId: 287,
      displayOrder: 3,
      title: "빠른 복구에도 장기 불확실성이 현물 노출을 키운다",
      narrative:
        "일 년을 넘는 긴 국면이지만 개별 공급 차질의 강도는 낮고, 비슷한 항로 경계가 반복되며 현물 시장 의존도가 높아진다.",
      cells: {
        period: "1년 초과",
        supply_disruption_intensity: "낮음",
        supply_disruption_pattern: "급차질-급회복",
        demand_response_alternative_lng: "0%",
        demand_response_powermix_reduction: "0%"
      },
      probability: "7.00",
      baselineYn: "N",
      status: "Draft",
      signposts: []
    }
  ]
};
