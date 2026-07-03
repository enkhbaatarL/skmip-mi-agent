# Model Parameter Proposal Evaluation - Single Scenario

- 실행 시작: 2026-07-04T03:14:22
- 실행 종료: 2026-07-04T03:15:25
- 시나리오 실행시간: 01:02.443 (62.443)
- scenario_id: 281
- maxCandidates: 30
- allowLlmFallback: False
- status: PASS

## Loaded DB Context

```json
{
  "dimension_template": [
    {
      "dim_key": "period",
      "label": "기간",
      "required": true,
      "value_count": 7
    },
    {
      "dim_key": "implementation_stage",
      "label": "시행 확실성·단계",
      "required": true,
      "value_count": 4
    },
    {
      "dim_key": "impact_intensity",
      "label": "영향 강도",
      "required": false,
      "value_count": 3
    },
    {
      "dim_key": "structural_change_yn",
      "label": "구조적 변동 여부",
      "required": false,
      "value_count": 2
    }
  ],
  "event": {
    "created_at": "2026-06-19T23:18:59.770700",
    "detail_analysis_chars": 1374,
    "detail_analysis_preview": "사건 요약:\nIMO Net-Zero Framework의 채택 일정과 회원국별 입장 차이가 기존 핵심 사건으로 유지됨. 그리스의 회의적 입장, EU·미국·사우디 등 회원국 간 견해 차이, 향후 결정 회의의 불확실성이 주요 내용임. 2026-06-01 Platts Daily Report는 호르무즈발 공급 제약, 강한 운임, 타이트한 LNG-TTF basis, EU 저장률 40.09%, Golden Pass 시운전 차질, Bulgargaz·Enarsa 조달, 아시아와 유럽의 카고 경쟁을 당일 LNG 시장 요인으로 제시함. 신규 연결 Record는 기존 요약에 이미 반영된 2026-06-01 시장 환경 업데이트와 동일한 내용으로, IMO Net-Zero Framework 정책 논의 자체의 추가 상태 변경은 확인되지 않음.\n\n영향 경로:\n국제 해운 온실가스 배출 비용 부과와 저탄소 연료 전환 유도는 선박 운항비 구조에 영향을 주는 정책 변수임. LNG선 연료 선택과 bio-LNG 등 저탄소 ",
    "event_title_ko": "IMO Net-Zero Framework 논의",
    "event_type_l2_id": 19,
    "key_bullet_count": 0,
    "key_bullets": [],
    "latest_record_first_created": "2026-06-01T00:00:00",
    "mi_event_id": "1155",
    "occurred_at": "",
    "oldest_record_first_created": "",
    "one_line_summary": "[해운 규제] IMO 탄소비용 논의 지속 → LNG 운송비·연료비 변수 유지",
    "source_mi_record_ids": [
      2271
    ],
    "tag_count": 0
  },
  "event_type": {
    "event_type_l1_id": 4,
    "event_type_l2_id": 19,
    "level_1_code": "exogenous_shock",
    "level_1_label": "외생충격",
    "level_2_code": "policy_regulatory_change",
    "level_2_label": "정책/규제 변화"
  },
  "scenario": {
    "baseline_yn": "N",
    "impact": {
      "hh": "중립",
      "jkm": "상승",
      "ttf": "상승"
    },
    "probability_score": 45.0,
    "scenario_group_id": 48,
    "scenario_id": 281,
    "title": "[model_parameter_agent_test] IMO 운송 규제 보통 강도"
  },
  "scenario_group": {
    "dimension_selected": [
      "period",
      "implementation_stage",
      "impact_intensity",
      "structural_change_yn"
    ],
    "event_type_l2_id": 19,
    "mi_event_id": 1155,
    "scenario_count": 2,
    "scenario_group_id": 48,
    "stage": "scenario_created",
    "status": "created",
    "title": "[model_parameter_agent_test] 정책/규제 routing 검증"
  }
}
```

## Scenario Dimensions

```json
{
  "impact_intensity": "보통",
  "implementation_stage": "시행 확정",
  "period": "3개월",
  "structural_change_yn": "단발적/한시"
}
```

## Validation Summary

- expected_parameters: `["Gas Futures Price"]`
- selected_parameters: `["Gas Futures Price"]`
- mapping_candidate_coverage: PASS
- selected_result: PASS
- routing_result: PASS
- response_warnings: `[]`


##### 모델 호출별 소요시간

| step | success | model_name | 소요시간 | elapsed_seconds | prompt_tokens | completion_tokens | total_tokens |
|---|---|---|---:|---:|---:|---:|---:|
| Step1.5 candidate validation | True |  | 00:09.886 | 9.886 | 2020 | 389 | 2409 |
| Step2 slot proposal | True |  | 00:12.593 | 12.593 | 4584 | 876 | 5460 |
| Step3 value proposal | True |  | 00:24.961 | 24.961 | 4231 | 1374 | 5605 |

## Final Response JSON

```json
{
  "data": {
    "eventId": 1155,
    "modelParamProposalId": 94,
    "proposalParameters": [
      {
        "modelTarget": {
          "modelFile": "Demand",
          "modelSheet": "CoalGasAdjustment",
          "slotAxesFieldNames": [
            "Month-Year",
            "Region"
          ],
          "tableName": "table1",
          "valueFieldNames": [
            "Gas Futures Price"
          ]
        },
        "parameterName": "Gas Futures Price",
        "rationale": "영향 강도 '보통'은 IMO 운송 규제에 따른 LNG 운송비·연료비 프리미엄이 가스 가격 및 Gas↔Coal 전환 유인에 반영될 수 있다는 매핑 설명과 연결되어 Gas Futures Price 조정 대상으로 해석된다. 기간은 3개월, 시행 확정이나 단발적/한시 성격이므로 구조적 가격 재평가가 아니라 단기 선물 strip에 보수적인 상향 delta를 적용하며, LNG 해상운송 노출도가 큰 지역에 상대적으로 더 큰 프리미엄을 둔다.",
        "values": [
          {
            "Month-Year": "2026-07",
            "Region": "Asia",
            "basecaseValue": null,
            "proposedValue": 0.2,
            "rationale": "해당 좌표는 3개월 영향 기간의 시작 월이자 Asia=JKM 선물가격 구간이다. 기준값 record가 제공되지 않았으므로 IMO 운송 규제의 보통 강도 비용 프리미엄을 직접적인 가격 상향분으로 보수 적용해 +0.20 USD/mmbtu delta로 산정했다."
          },
          {
            "Month-Year": "2026-08",
            "Region": "Asia",
            "basecaseValue": null,
            "proposedValue": 0.2,
            "rationale": "해당 좌표는 3개월 영향 기간 내 Asia=JKM 선물가격 구간이다. 한시적 규제 비용이 기간 중 유지되는 것으로 보고, 기준값 없이도 동일 강도의 LNG 운송·연료비 프리미엄을 반영해 +0.20 USD/mmbtu delta로 산정했다."
          },
          {
            "Month-Year": "2026-09",
            "Region": "Asia",
            "basecaseValue": null,
            "proposedValue": 0.15,
            "rationale": "해당 좌표는 3개월 영향 기간의 마지막 월에 해당하는 Asia=JKM 선물가격 구간이다. 단발적/한시 영향의 말월에는 일부 적응과 비용 전가 완화를 반영해 앞선 월보다 낮은 +0.15 USD/mmbtu delta로 산정했다."
          },
          {
            "Month-Year": "2026-07",
            "Region": "Europe",
            "basecaseValue": null,
            "proposedValue": 0.15,
            "rationale": "해당 좌표는 3개월 영향 기간의 시작 월이자 Europe=TTF 선물가격 구간이다. 운송 규제 비용은 유럽 LNG 조달에도 상방 압력이나, TTF는 배관가스와 저장 요인의 비중도 있어 Asia 대비 보수적으로 +0.15 USD/mmbtu delta를 적용했다."
          },
          {
            "Month-Year": "2026-08",
            "Region": "Europe",
            "basecaseValue": null,
            "proposedValue": 0.15,
            "rationale": "해당 좌표는 3개월 영향 기간 내 Europe=TTF 선물가격 구간이다. 시행 확정된 운송비·연료비 프리미엄이 단기적으로 유지된다고 보되, 기준값이 없으므로 보통 강도의 최소 상방 충격으로 +0.15 USD/mmbtu delta를 산정했다."
          },
          {
            "Month-Year": "2026-09",
            "Region": "Europe",
            "basecaseValue": null,
            "proposedValue": 0.1,
            "rationale": "해당 좌표는 3개월 영향 기간의 마지막 월에 해당하는 Europe=TTF 선물가격 구간이다. 한시적 영향의 말월에는 비용 전가가 완화되는 것으로 보아 Europe 구간의 보수적 상향분을 +0.10 USD/mmbtu delta로 낮춰 산정했다."
          }
        ]
      }
    ],
    "scenarioGroupId": 48,
    "scenarioId": 281
  },
  "message": "model parameter proposal completed",
  "status": "success"
}
```
