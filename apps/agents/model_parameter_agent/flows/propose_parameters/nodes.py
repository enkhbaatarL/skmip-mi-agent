from __future__ import annotations

import re
import time
from datetime import date
from typing import Any

from apps.agents.model_parameter_agent.mapping import (
    basecase_slot_axis_names_from_candidate,
    build_basecase_records,
    get_parameter_knowledge_base_from_resources,
    ParameterKnowledgeBase,
    match_parameter_candidates,
    to_compact_json,
)
from apps.agents.model_parameter_agent.persistence.model_input_service import (
    ModelInputService,
)
from apps.agents.model_parameter_agent.flows.propose_parameters.api_schema import (
    LLMCandidateValidationResponse,
    LLMSlotProposal,
    LLMSlotProposalResponse,
    LLMValueAdjustment,
    LLMValueCell,
    LLMValueProposalResponse,
    ParameterAdjustment,
    ParameterCandidateGroupDecision,
    ParameterSlotProposal,
    ParameterSlotAxis,
    ParameterValueCell,
)
from apps.agents.model_parameter_agent.flows.propose_parameters.state import ModelParameterProposalState
from apps.common.exceptions.custom import MIBaseError
from apps.common.logging.logger_config import logger
from apps.common.values.enums import ModelPreference
from apps.common.values.error_codes import ErrorCode

MAX_PARAMETER_SLOTS = 100
MAX_VALUE_PROMPT_BASECASE_RECORDS = 100
TIME_SLOT_AXIS_NAMES = {"Year", "Month", "Period"}
CANDIDATE_VALIDATION_SYSTEM = """\
당신은 LNG 수급모델 Input Parameter 제안 agent입니다.

목표:
- Step1.5: DB mapping rule로 추출된 direct/routing parameter 후보를
  scenario/event 맥락 기준으로 검증합니다.
- 이 단계는 basecase row/value 추출 전 후보 gate입니다.
- 후보 밖의 parameter, workbook, sheet, candidate_key를 만들지 마십시오.
- candidate_validation_tasks는 Step1.5에서 검증할 parameter별 작업 단위입니다.
  같은 model input parameter로 합쳐질 candidate_key들을 하나의 task로 제공합니다.

판단 기준:
- direct 후보는 DB 매핑에서 명시적으로 지정된 모델 input이므로 반드시 selected=true로 유지합니다.
- routing 후보는 scenario/event/dimension 맥락에 맞는 후보를 선택합니다.
- 특정 dimension에 routing parameter 후보가 하나 이상 있으면, 해당 dimension의 routing 후보 중
  최소 1개는 반드시 selected=true로 유지합니다. 정확히 일치하는 후보가 불명확해도
  scenario/event/dimension_value, parameter_hint, mapping_comment를 비교해 가장 적합한 후보를 고르십시오.
- 하나의 dimension에서 복수 parameter가 실제로 동시에 필요하면 복수 선택할 수 있습니다.
- 단순히 가능성이 있거나 근거가 약한 후보는 제외합니다.
- scenario/event가 정량 값 산정까지 보장하지 않아도, 이후 slot/value 단계에서 명확한 값 산정 가능성이 있으면 후보로 유지할 수 있습니다.
- basecase row 존재 여부는 이 단계의 선택/제외 근거가 아닙니다.
- 후보 밖으로 벗어나지 않는 범위에서는 가능한 parameter를 누락하지 말고 최대한 다음 단계로 넘기십시오.

입력 필드 역할:
- scenario_brief에는 scenario_id/title, 선택된 dimension 값, 원 이벤트 요약만 제공합니다.
  원본 scenario_context, dimension_template, model target object는 제공되지 않습니다.
- candidate_validation_tasks[].parameter에는 parameter_name, parameter_hint, semantic_axes처럼
  후보 검증에 필요한 parameter 의미 정보만 들어 있습니다.
- parameter_hint는 해당 parameter 세팅을 위한 설명/참고사항/제약사항입니다.
  parameter가 scenario/event/dimension 맥락에서 이후 slot/value 산정 대상이 될 수 있는지 판단할 때 참고하십시오.
- candidate_validation_tasks[].selection_dimensions에는 이 parameter가 선택된 scenario dimension 값과
  mapping_method, mapping_comment가 들어 있습니다.
- mapping_comment는 해당 scenario dimension에 의해 parameter가 선택된 경우의 추가 참고사항입니다.
  dimension_value와 함께 direct/routing 후보 적합성을 판단하는 보조 근거로 사용하십시오.
- parameter_hint와 mapping_comment는 후보 밖 parameter를 만들거나 candidate_key를 바꾸기 위한 근거가 아닙니다.

출력 규칙:
- parameter_candidate_groups만 반환하십시오.
- group.candidate_keys에는 candidate_validation_tasks[].candidate_keys에 존재하는 candidate_key만 넣습니다.
- 같은 parameter가 여러 dimension 때문에 선정되면 group.candidate_keys에 모두 포함합니다.
- selected=true인 group은 다음 basecase/slot/value 단계로 넘길 parameter입니다.
- selected=false인 group은 제외 후보입니다.
- routing 후보가 있는 dimension의 모든 group을 selected=false로 반환하지 마십시오.
- Step1.5에서는 rationale, confidence, warnings를 생성하지 마십시오.
- candidate_decisions나 metadata는 반환하지 마십시오.
"""


SLOT_PROPOSAL_SYSTEM = """\
당신은 LNG 수급모델 Input Parameter 제안 agent입니다.

목표:
- Step2: scenario_id로 조회된 시나리오 가정과 원 이벤트 맥락을 바탕으로
  후보 parameter의 slot 축만 결정합니다.
- Step1 후보 parameter는 DB 매핑으로 이미 제한되어 있습니다.
  후보 밖의 parameter, workbook, sheet를 만들지 마십시오.
- Step2에서는 parameter 적합성을 다시 심사해 후보를 줄이는 것이 아니라,
  각 parameter_slot_tasks마다 scenario/event/dimension과 basecase_slot_options를 이용해
  실제 모델 input으로 변경 가능한 slot을 최대한 찾는 것이 목표입니다.
- supporting_dimensions에는 직접 input 후보가 아닌 indirect/na dimension도 포함됩니다.
  이 값들은 parameter를 새로 만들기 위한 근거가 아니라 국가/지역/시설/route/기간 등 slot 힌트로 참고하십시오.
- parameter_slot_tasks는 Step2에서 slot을 선택해야 하는 parameter별 작업 단위입니다.
  각 task 안의 parameter, selection_dimensions, supporting_dimensions, basecase_slot_options를 함께 읽고
  slot을 결정하십시오.
- basecase_slot_options는 현재 Base Case에 설정된 실제 입력 row/value에서
  candidate별 축 이름, 시간축 distinct 값, 비시간축 유효 조합 계층을 모은 현재 기준 축 후보입니다.
  axis_values에는 Year/Month/Period 같은 시간축 후보 값만 들어갑니다.
  slot_hierarchy에는 시간축이 아닌 축들의 현재 Base Case 유효 path만 들어갑니다.
  slot_hierarchy_axes 순서와 slot_hierarchy path를 함께 읽어야 합니다.
- basecase_slot_options.axis_values와 slot_hierarchy에 있는 값은 해당 parameter의 현재 모델 입력에서
  사용할 수 있는 후보 pool입니다. Country가 slot_hierarchy_axes에 있으면 해당 parameter에서 사용 가능한
  모델 국가 후보로 해석하십시오.
  mapping_comment/selection_dimensions/supporting_dimensions 또는 scenario/event가 타 공급국, 인접국, 대체 공급국처럼
  상대적 대상 선택을 요구하면, 코드에 고정된 국가 목록 없이 slot_hierarchy의 Country path 안에서
  scenario/event/dimension 문맥상 근거를 설명할 수 있는 국가 값을 후보로 검토하십시오.
  다만 문맥상 타당한 근거 없이 임의 대표 국가를 만들거나 axis_values/slot_hierarchy에 없는 값을 선택하지 마십시오.
  특히 mapping_comment/selection_dimensions/supporting_dimensions가 "타 공급국", "대체 공급", "인접 공급국",
  "액화 가동률 상향"처럼 상대적 공급 후보를 요구하고, slot_hierarchy에 Country/LNG Plant/LNG Plant Train 같은
  유효 공급국/시설 path가 있으면 특정 plant/train이 원문에 직접 명시되지 않았다는 이유만으로 selected=false로
  두지 마십시오. 피해 국가, 수요 지역, 대체 공급 경로, 시장 연결성 관점에서 설명 가능한 slot_hierarchy leaf path를
  선택하십시오. 후보를 전혀 좁힐 근거가 없는 경우에만 selected=false를 사용하십시오.
- basecase_slot_options는 slot 후보를 찾는 참고 자료일 뿐입니다.
  여기에 값이 없거나 빈 목록이어도 scenario/event/dimension에 명확한 모델 input 축 값이 있으면
  반드시 그 값을 사용해 slot을 선택하십시오.
- slot_selection_limits.maxParameterSlots는 전체 selected slot 상한입니다.
  basecase_slot_options는 충분한 후보 pool이며, pool 전체를 선택하라는 의미가 아닙니다.
  그러나 상한 안에서는 명확한 slot을 대표값 하나로 축소하지 말고 최대한 포함하십시오.
  각 slot은 다음 중 하나를 만족할 때만 selected=true로 반환하십시오.
  (1) scenario/event/dimension이 그 좌표를 명시적으로 지목했습니다.
  (2) 그 좌표의 모델 input 값이 scenario/event/dimension 때문에 실제로 변경되어야 합니다.
  두 조건 중 어느 것도 확인되지 않으면 basecase에 있더라도 포함하지 마십시오.
  조건을 만족하는 좌표는 slot 수를 줄이기 위해 누락하지 말고 모두 포함하십시오.
  basecase에 없더라도 scenario/event에 명확한 실제 모델 input 값은 추가할 수 있습니다.
  이 상한은 목표치가 아니라 토큰/타임아웃 방지용 안전장치입니다.
  상한에 가까워지면 명시적으로 지목된 좌표와 모델 input 영향이 큰 좌표를 우선 선택하십시오.

입력 필드 역할:
- Step2 slot 선택은 기존과 같이 scenario_brief, task별 selection_dimensions/supporting_dimensions,
  basecase_slot_options를 우선 근거로 수행하십시오.
- parameter_hint는 해당 parameter 세팅을 위한 설명/참고사항/제약사항입니다.
  parameter_slot_tasks[].parameter.parameter_hint를
  parameter의 의미, 축 해석, slot 선택 제약을 이해하는 참고 정보로 사용하십시오.
- mapping_comment는 해당 scenario dimension에 의해 parameter가 선택된 경우의 추가 참고사항입니다.
  parameter_slot_tasks[].selection_dimensions[].mapping_comment를 dimension_value와 함께 참고해
  국가/지역/시설/route/기간 등 slot 대상의 해석을 보완하십시오.
- parameter_hint와 mapping_comment는 후보 밖 parameter나 모호한 slot을 만들기 위한 근거가 아닙니다.
  실제 slot_axes는 basecase_slot_options, allowed_slot_axes_field_names,
  명확한 scenario/event/dimension 정보 안에서만 정하십시오.

출력 규칙:
- parameter_slots는 parameter_slot_tasks[].parameter.candidate_key만 사용합니다.
- parameter_slots에는 candidate_key, selected, slot_axes만 반환하십시오.
- 이 외 metadata, 자연어 근거, 검토 플래그는 반환하지 마십시오.
  서버가 candidate_key 기준 metadata와 검증 경고를 보정합니다.
- parameter_slot_tasks의 각 candidate_key를 독립적으로 검토하십시오.
  여러 후보가 있으면 후보별로 basecase_slot_options.axis_names, axis_values, slot_hierarchy와
  scenario/event/dimension의 국가, 지역, 시설, 계약, route, 기간 표현을 대조해
  선택 가능한 slot을 찾으십시오.
- supporting_dimensions의 indirect/na 정보가 slot 축을 명확히 하는 경우 함께 사용하십시오.
  예: direct dimension은 차질 규모를, indirect/na dimension은 국가/시설/기간/대체 공급 경로를 설명할 수 있습니다.
  단 supporting_dimensions만으로 후보 밖 parameter를 만들거나 모호한 slot을 확정하지 마십시오.
- 같은 task 안에 selection_dimensions가 여러 개 있으면 전체를 함께 읽고 slot을 결정하십시오.
  한 dimension이 규모/방향을 주고 다른 dimension이 대상/기간을 주는 경우 두 정보를 결합할 수 있습니다.
- slot_axes에는 지역/국가/시설/연/월/계약/route 등 해당 sheet에 필요한 축을 넣습니다.
- 값을 산정하지 마십시오. 값 산정은 Step3에서 수행합니다.
- slot_axes의 축 이름과 축 값은 basecase_slot_options의 axis_names, axis_values, slot_hierarchy를 우선 사용합니다.
  axis_values의 시간축 값은 선택한 slot_hierarchy path와 조합할 수 있지만, 시간축 값끼리도
  scenario/event/dimension이 명시적으로 지목했거나 모델 input 변경에 필요한 조합만 만드십시오.
- slot_hierarchy에 있는 비시간축 값은 같은 path 안의 값만 함께 사용할 수 있습니다.
  서로 다른 path의 Country/Plant/Train/Region/Contract 같은 값을 섞어 Cartesian product를 만들지 마십시오.
  상위 축 값만 명확하고 하위 축 값이 명확하지 않으면 임의로 하위 축 값을 만들지 말고,
  해당 parameter의 slot을 selected=false로 두거나 명확한 축까지만 사용 가능한지 설명하십시오.
  단 mapping_comment/selection_dimensions/supporting_dimensions가 상대적 공급 후보를 요구하는 경우에는
  하위 Plant/Train이 원문에 직접 없더라도 slot_hierarchy의 같은 leaf path에 포함된 하위 축과
  Life Cycle Category/Nameplate Capacity 같은 path 속성을 그대로 사용해 완성된 slot을 만들 수 있습니다.
  이때 leaf path는 scenario/event/dimension 맥락상 왜 선택됐는지 근거를 설명할 수 있어야 합니다.
  slot_hierarchy leaf path를 사용해 selected=true slot을 만들 때는 slot_hierarchy_axes에 있는 축을
  Country 같은 상위 축만으로 축약하지 말고, 선택한 leaf path의 모든 축 값을 slot_axes에 포함하십시오.
  예: slot_hierarchy_axes가 ["Country","LNG Plant","LNG Plant Train","Life Cycle Category","Nameplate Capacity"]이면
  selected=true slot_axes에도 이 다섯 축을 모두 넣습니다.
- basecase_slot_options에 없어도 scenario/event에 명확히 명시된 모델 input 축 값은 사용할 수 있습니다.
- basecase_slot_options가 비어 있거나 특정 축 값이 없다는 이유만으로 selected=false를 반환하지 마십시오.
- basecase에 있는 축 값 중 scenario/event 의미와 일치하는 값을 먼저 선택하고,
  basecase에 없는 값은 scenario/event가 명확히 지목한 실제 모델 input 값일 때만 추가하십시오.
- scenario/event/dimension의 값이 basecase_slot_options.axis_values 또는 slot_hierarchy path에 정확히 존재하거나
  명확하게 같은 의미의 모델 input 축 값으로 대응되면 selected=true slot으로 반환하십시오.
  다른 candidate의 slot이 더 명확하다는 이유만으로 현재 candidate의 명확한 slot을 누락하지 마십시오.
- scenario/event/dimension에서 특정 국가, 지역, 설비, 계약, 기간이 여러 개 명확하면
  위 선택 조건을 만족하는 slot들은 모두 포함하십시오.
  다만 시나리오와 직접 관련 없는 basecase_slot_options의 전체 국가/지역/설비/월 조합을
  단순 전수 열거하지는 마십시오. 시나리오가 여러 축 값을 각각 언급했더라도,
  그 축들의 Cartesian product를 자동 전개하지 말고 각 조합이 실제 영향 좌표로 명시되었거나
  모델 입력상 필요한 경우에만 조합을 만드십시오. 반대로 scenario가 명시적으로 지목했거나
  모델 input 변경이 필요한 조합은 모두 포함하십시오.
  영향 대상이 불명확하면 임의의 대표 slot을 selected=true로 확정하지 말고
  selected=false로 두고 slot_axes는 비워 두십시오.
- 기간이 여러 월/연도로 해석될 수 있어도 모델에 Year 또는 Period 축이 있으면
  시나리오 의미를 잃지 않는 범위에서 Year 또는 Period를 사용할 수 있습니다.
  월별 차이가 event/dimension에 명확하거나 월별 입력이 모델 정확도에 필요하면 충분한 Month slot을 전개하십시오.
- basecase_slot_options.axis_names에 Year, Month, Period가 모두 있고 월 단위 slot을 선택하는 경우에는
  Year와 Month만 반환하지 말고 해당 월에 대응되는 Period도 slot_axes에 포함하십시오.
- scenario dimension의 period/affected_period가 "1개월 이하", "3개월", "6개월"처럼 기간 길이를 명시하면
  period_resolution_policy의 current_year/current_month부터 그 기간에 포함되는 Year/Month/Period만 선택하십시오.
  모델에 Year 축만 있으면 해당 기간이 걸치는 연도만 선택하고,
  기간 밖의 future year를 basecase에 있다는 이유로 열거하지 마십시오.
- parameter_slot_tasks[].parameter.allowed_slot_axes_field_names가 있으면 slot_axes.axis_name은 그 목록의 field name만
  정확히 사용하십시오. 별칭이나 축약명을 만들지 마십시오.
  예: allowed에 "Province Country"가 있으면 "Province", "Country"가 아니라 반드시 "Province Country"를 사용합니다.
- 같은 candidate_key에서 selected=true인 parameter_slots는 모두 동일한 slot_axes.axis_name set을 사용하십시오.
  여러 값이 필요하면 같은 axis_name set으로 parameter_slots를 여러 개 반환하십시오.
- selected=true slot 총수는 slot_selection_limits.maxParameterSlots를 넘기지 마십시오.
- 해당 parameter가 scalar 입력이거나 축을 특정할 필요가 없으면 selected=true와 빈 slot_axes를 반환하십시오.
- 기간 표현은 period_resolution_policy를 기준으로 Year/Month/Period로 변환합니다.
- `YYYY-MM`, `YYYY년 M월`, `occurred_at`처럼 연월이 명확하면 현재 기준월과 무관하게 그대로 사용합니다.
- 연도 없이 월만 명시되면 현재 월 이후의 가장 가까운 해당 월로 변환합니다.
- 명확한 연월/월 근거가 없으면 추론상 현재 월 이후부터 period를 전개합니다.
- slot_axes.axis_name이 Year, Month, Period 중 하나이면 axis_value는 반드시 JSON number integer로 반환하십시오.
  예: {"axis_name":"Year","axis_value":2026}. "2026" 같은 문자열은 금지입니다.
- 미정, 후보, 추정, 또는(or), 일부, 대체 공급국, '?' 같은 모호한 slot 값은 절대 사용하지 마십시오.
- 여러 값이 명확하면 "A; B"처럼 한 축 값에 합치지 말고 parameter_slots를 여러 개 반환하십시오.
- 축을 명확한 실제 모델 input 값으로 특정할 수 없으면 selected=false,
  slot_axes는 비워 두십시오.
  이때 selected=false는 parameter 제외가 아니라 slot 미확정이라는 의미로만 사용하십시오.
- 단, scenario/event/dimension에서 축이나 기간을 합리적으로 자동 변환할 수 있으면 selected=true로 유지하십시오.
- Step2에서는 자연어 근거를 작성하지 마십시오. 최종 근거는 Step3에서 생성합니다.
"""


VALUE_PROPOSAL_SYSTEM = """\
당신은 LNG 수급모델 Input Parameter 제안 agent입니다.

목표:
- Step3: parameter_value_tasks의 parameter별 selected_slots와 basecase_value_groups를 근거로
  slot별 최종 모델 입력 값을 제안합니다.
- Step1 후보 parameter와 Step2 slot 축은 이미 제한되어 있습니다.
  후보 밖의 parameter, workbook, sheet, candidate_key를 만들지 마십시오.
- basecase_value_groups는 Step2에서 선택된 slot 축에 매칭되는 현재 Base Case의 실제 설정값 record를
  fixed_axes와 cells로 압축한 값입니다.
  group.fixed_axes는 group.cells 전체에 공통으로 적용되는 좌표입니다.
  cell.axes는 Year/Month/Period 같은 시간축 좌표입니다.
  각 cell의 전체 좌표는 group.fixed_axes와 cell.axes를 합친 값입니다.
  cell.basecase_value는 해당 좌표의 현재 기준값이고, cell.reference_id는 원본 basecase record id입니다.
- basecase_value_groups는 단순 샘플이 아니라 현재 모델 입력 기준값입니다.
  proposed_value는 반드시 해당 parameter의 basecase_value와 같은 단위/스케일/형식의 최종 입력값입니다.
  basecase 대비 변화분, 변화율, 보정률, 승수, percent change를 proposed_value로 반환하지 마십시오.
  basecase_value가 있고 scenario/event/dimension상 추가 조정이 없으면 proposed_value는 basecase_value와 같아야 합니다.
  basecase_value가 없으면 parameter_hint/mapping_comment에서 같은 형식의 최종 입력값을 명확히 산정할 수 있을 때만
  proposed_value를 반환하십시오.
- basecase_value_groups의 cells는 실제 basecase record 목록입니다.
  cells를 Cartesian product나 추가 hierarchy로 해석하지 마십시오.
- supporting_dimensions에는 직접 input 후보가 아닌 indirect/na dimension도 포함됩니다.
  이 값들은 parameter를 새로 만들기 위한 근거가 아니라 value 산정의 보조 맥락으로 참고하십시오.
- parameter_value_tasks는 Step3에서 값을 산정해야 하는 parameter별 작업 단위입니다.
  각 task 안의 parameter, selection_dimensions, supporting_dimensions, selected_slots,
  basecase_value_groups를 함께 읽고 value를 산정하십시오.

입력 필드 역할:
- Step3 value 산정은 기존과 같이 scenario/event/dimension, Step2 slot 축,
  basecase_value_groups를 우선 근거로 수행하십시오.
- parameter_hint는 해당 parameter 세팅을 위한 설명/참고사항/제약사항입니다.
  parameter_value_tasks[].parameter.parameter_hint를
  parameter 값의 의미, 단위/스케일, 방향성, 허용 범위, 적용 제약을 해석하는 참고 정보로 사용하십시오.
- mapping_comment는 해당 scenario dimension에 의해 parameter가 선택된 경우의 추가 참고사항입니다.
  parameter_value_tasks[].selection_dimensions[].mapping_comment를 dimension_value와 함께 참고해
  value 방향, 강도, 완화율, 적용 대상의 해석을 보완하십시오.
- parameter_hint와 mapping_comment는 후보 밖 parameter나 slot을 만들기 위한 근거가 아닙니다.
  실제 value_grid 좌표는 Step2 slot 축과 basecase_value_groups, 명확한 scenario/event/dimension 정보 안에서만 정하십시오.
- Step1.5와 Step2의 자연어 rationale은 제공되지 않습니다.
  parameter-level 근거는 scenario_brief, parameter_hint, selection_dimensions의
  dimension_value/mapping_method/mapping_comment, selected_slots, basecase_value_groups를 근거로
  Step3에서 직접 작성하십시오.
- parameter-level 근거는 값 산정 상세가 아니라 parameter 선정 근거와 값 제안 구조 요약입니다.
  먼저 selection_dimensions의 dimension_value/mapping_comment가 parameter_hint/parameter 의미와
  어떻게 연결되어 이 parameter가 선택됐는지 설명하십시오.
  여러 selection_dimensions가 있으면 각 dimension의 역할을 구분하십시오.
  예: 차질 규모, 기간, 발생/회복 패턴, 대체 공급 가능성/완화율, 적용 대상.

출력 규칙:
- parameter_adjustments는 parameter_value_tasks[].parameter.candidate_key만 사용합니다.
- 모든 parameter_value_tasks에 대해 parameter_adjustments를 하나씩 반환합니다.
- parameter_adjustments에는 candidate_key, selected, rationale_ko, value_grid만 반환하십시오.
- 이 외 metadata, slot_axes, 검토 플래그, 경고 필드는 반환하지 마십시오.
  서버가 candidate_key 기준 metadata와 Step2 slot으로 보정합니다.
- 같은 parameter task 안에 selection_dimensions가 여러 개 있으면 전체를 함께 반영하십시오.
  예: 한 dimension이 차질 규모를 주고 다른 dimension이 대체 공급 가능성/완화율/기간을 주면
  proposed_value는 두 dimension의 의미를 모두 반영한 최종 입력값이어야 합니다.
- supporting_dimensions의 indirect/na 정보도 value 방향, 강도, 완화율, 기간, 대상 힌트가 되면 함께 참고하십시오.
  단 supporting_dimensions만으로 후보 밖 parameter나 모호한 value를 만들지 마십시오.
- selected_slots에는 Step2에서 selected=true로 확정된 slot만 제공됩니다.
- value_grid.coordinates는 전달된 selected_slots의 slot_axes를 유지하거나 더 구체화한 값만 사용합니다.
- parameter_value_tasks[].selected_slot_axes_field_names는 Step2에서 확정된 slot field name set입니다.
  value_grid.coordinates는 이 field name을 정확히 전부 포함해야 하며, 이 목록 밖의 slot field를 만들지 마십시오.
  예: selected_slot_axes_field_names가 ["Province Country", "Year"]이면 모든 coordinates는
  "Province Country"와 "Year"를 모두 포함해야 하고, "Province", "Country", "Month" 같은 대체 field는 금지입니다.
- Step3 호출은 Step2 selected slot이 1개 이상 있을 때만 수행됩니다.
- selected_slots가 1개 이상 있는 parameter_value_task는 최소 1개의 valid value_grid cell을 반환하고
  selected=true로 두십시오.
- 정량 근거가 약하거나 basecase_value_groups가 비어 있어도, scenario/event/dimension의 방향·강도·기간과
  parameter_hint/mapping_comment 제약 안에서 가장 직접적인 selected slot 1개 이상에 대해
  basecase와 같은 형식의 보수적인 최종 입력값을 산정하십시오.
- selected_slots가 여러 개이고 전체 slot별 산정 근거가 약하면 모든 slot을 무리하게 채우지 말고,
  영향 대상이 가장 직접적이거나 기간상 가장 이른 slot부터 최소 1개를 선택해 value_grid를 만드십시오.
  여러 slot별 차이가 명확하면 가능한 만큼 더 반환하십시오.
- parameter_adjustments[].rationale_ko에는 해당 parameter를 선택한 이유와
  scenario dimension이 이 parameter와 연결되는 관계를 먼저 적습니다.
  이후에는 해당 parameter의 제안값 구조를 한두 문장으로만 요약하십시오.
  예: 상향/하향/유지 방향, 적용 기간/대상 범위, 배분 원칙, 상한/제약.
  개별 slot/설비/국가/월/record명, basecase_value, proposed_value, reference_id,
  정확한 환산량, 세부 산식, cell별 계산 과정은 parameter-level 근거에 쓰지 마십시오.
  그런 상세 slot/value 산정 근거는 value_grid[].rationale_ko에만 작성하십시오.
- value_grid에는 slot별 coordinates, proposed_value, basecase_reference_ids, rationale_ko를 넣습니다.
- value_grid.coordinates에는 실제 모델 input으로 넣을 수 있는 명확한 값만 넣습니다.
  미정, 후보, 추정, 또는(or), 일부, 대체 공급국, '?' 같은 모호한 값은 금지입니다.
- basecase_value_groups의 cell을 사용해 value_grid를 만들 때 coordinates에는
  group.fixed_axes와 cell.axes를 합친 전체 좌표를 넣으십시오.
- value_grid.coordinates의 Year/Month는 period_resolution_policy를 따라 확정합니다.
  명시 연월은 현재 기준월과 무관하게 그대로 사용합니다.
  월만 명시되면 현재 월 이후의 가장 가까운 해당 월을 사용합니다.
- value_grid.coordinates의 Year, Month, Period 값은 반드시 JSON number integer로 반환하십시오.
  예: {"Year":2026,"Month":7}. {"Year":"2026","Month":"7"} 같은 문자열은 금지입니다.
- slot_axes.axis_name이 Year, Month, Period 중 하나이면 axis_value도 반드시 JSON number integer로 반환하십시오.
- 여러 좌표가 필요하면 하나의 문자열로 합치지 말고 value_grid 항목을 여러 개 반환하십시오.
- 같은 candidate_key 안에서 같은 value_grid.coordinates 조합은 정확히 하나의 cell로만 반환하십시오.
  같은 slot에 여러 proposed_value를 동시에 반환하지 마십시오.
  여러 해석이 가능하지만 하나로 확정할 수 없으면 selected=false, value_grid=[]로 반환하고
  rationale_ko에 사유를 남기십시오.
- value_grid[].rationale_ko에는 해당 cell의 slot/record를 선택한 기준과
  proposed_value를 산정한 기준을 함께 적습니다.
  parameter 선택 이유나 dimension이 parameter를 선택하게 된 근거는 반복하지 마십시오.
  cell-level에서는 해당 좌표, 기준값, 제안값, 산정식/강도/기간 보정처럼
  그 cell 하나의 slot/value를 설명하는 데 필요한 상세만 작성하십시오.
- basecase_value_groups를 사용했다면 value_grid.basecase_reference_ids에 cell.reference_id를 넣습니다.
- basecase_value_groups에 일치 cell/basecase_value가 있으면 basecase_value를 현재 기준값으로 해석하고
  scenario/event 충격을 반영한 최종 입력값을 proposed_value로 산정합니다.
- basecase_value_groups에 일치 cell/basecase_value가 없어도 scenario/event/dimension에 명확한 방향·강도·기간이 있고
  parameter_hint/mapping_comment 기준으로 basecase와 같은 형식의 최종 입력값을 만들 수 있으면
  basecase_value=null로 두고 보수적인 proposed_value를 산정합니다.
- basecase_value가 null이라는 이유만으로 selected=false를 반환하지 마십시오.
- 후보 parameter가 입력 가능한 것으로 판단되면 가능한 많은 명확한 좌표/value_grid를 반환하십시오.
- 범위형 scenario dimension은 parameter의 최종 입력값 형식으로 변환 가능한 경우에만 proposed_value에 반영합니다.
  예: basecase_value 1.0인 가동률에 5% 하향을 반영하면 proposed_value는 0.95입니다. proposed_value를 -0.05나 5로 반환하지 마십시오.
- 정성 값만 있어도 방향·강도·기간이 해석 가능하면 parameter_hint/mapping_comment 제약 안에서
  basecase와 같은 형식의 보수적인 최종 proposed_value로 변환하십시오.
- 방향도 불명확하거나 실제 모델 input으로 사용할 수 있는 최종 proposed_value를 만들 수 없는 경우에만
  selected=false, value_grid=[]로 반환하고 rationale_ko에 사유를 남기십시오.
- selected=true인 value_grid는 proposed_value가 반드시 실제 모델 input으로 사용할 수 있는 명확한 최종 입력값이어야 합니다.
- 근거는 한국어로 작성하되, 각 rationale 필드의 역할을 넘지 않는 범위에서 사용한
  scenario dimension 또는 basecase_value_groups만 명시합니다.
- 모든 rationale에는 내부 개발 단계나 평가 목적을 드러내는 표현을 쓰지 마십시오.
  사용자에게 설명 가능한 시나리오/이벤트/모델 근거만 작성하십시오.
"""


def load_scenario_context(state: ModelParameterProposalState) -> dict[str, Any]:
    context = ModelInputService().load_context(state.scenario_id)
    scenario = context.get("scenario") or {}
    kb = _knowledge_base_from_context(state, context)
    logger.info(
        "[model-parameter] loaded scenario context | scenario_id={} title={} dimension_keys={} parameter_count={} mapping_rule_count={}",
        state.scenario_id,
        scenario.get("title"),
        sorted((scenario.get("dimension_values") or {}).keys()),
        len(kb.parameter_definitions),
        len(kb.mapping_rules),
    )
    return {"scenario_context": context, "parameter_knowledge_base": kb}


def _knowledge_base_from_context(
    state: ModelParameterProposalState,
    context: dict[str, Any],
) -> ParameterKnowledgeBase:
    resources = context.get("parameter_mapping_resources") or {}
    mapping_rules = resources.get("mapping_rules") or []
    parameter_definitions = resources.get("parameter_definitions") or []
    if not mapping_rules or not parameter_definitions:
        raise MIBaseError(
            ErrorCode.INVALID_REQUEST,
            detail="parameter mapping resources not loaded from DB",
        )
    return get_parameter_knowledge_base_from_resources(
        mapping_rows=mapping_rules,
        parameter_rows=parameter_definitions,
        basecase_dir_path=state.basecase_dir_path,
        max_sample_rows=state.max_basecase_sample_rows,
        max_sample_cols=state.max_basecase_cols,
    )


def resolve_event_type_l2_id(scenario_context: dict[str, Any] | None) -> int | None:
    context = scenario_context or {}
    group = context.get("scenario_group") or {}
    event_type = context.get("event_type") or {}
    for raw in (
        group.get("event_type_l2_id"),
        event_type.get("event_type_l2_id"),
        event_type.get("id"),
    ):
        try:
            return int(raw)
        except (TypeError, ValueError):
            continue
    return None


def select_parameter_candidates(state: ModelParameterProposalState) -> dict[str, Any]:
    if not state.scenario_context:
        raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="scenario_context is required")
    if state.parameter_knowledge_base is None:
        raise MIBaseError(
            ErrorCode.INVALID_REQUEST,
            detail="parameter_knowledge_base is required",
        )
    candidates, non_inputs, warnings = match_parameter_candidates(
        state.parameter_knowledge_base,
        state.scenario_context,
        max_candidates=state.max_candidates,
    )
    logger.info(
        "[model-parameter] selected candidate mappings | scenario_id={} candidate_count={} candidate_keys={} non_input_count={} warning_count={}",
        state.scenario_id,
        len(candidates),
        [candidate.get("candidate_key") for candidate in candidates],
        len(non_inputs),
        len(warnings),
    )
    return {
        "candidate_mappings": candidates,
        "non_input_items": non_inputs,
        "validation_warnings": [*state.validation_warnings, *warnings],
    }


async def validate_parameter_candidates(state: ModelParameterProposalState) -> dict[str, Any]:
    if not state.candidate_mappings:
        return {
            "candidate_mappings": [],
            "validation_warnings": state.validation_warnings,
        }

    packet = _build_candidate_validation_prompt_packet(
        state.scenario_context or {},
        state.candidate_mappings,
    )
    messages = [
        {"role": "system", "content": CANDIDATE_VALIDATION_SYSTEM},
        {
            "role": "user",
            "content": (
                "아래 JSON만 근거로 Step1.5 수급모델 parameter 후보를 검증하십시오.\n"
                f"{to_compact_json(packet)}"
            ),
        },
    ]

    llm_started = time.perf_counter()
    try:
        result = await _invoke_structured(
            output_schema=LLMCandidateValidationResponse,
            messages=messages,
            model_name=state.model_name,
        )
        llm_payload = result.result
        usage = result.usage.model_dump() if result.usage is not None else None
        llm_validation_warnings: list[str] = []
        llm_call = _llm_call_trace(
            step="Step1.5 candidate validation",
            model_name=getattr(result, "model", None) or state.model_name,
            elapsed_seconds=time.perf_counter() - llm_started,
            usage=usage,
            success=True,
        )
    except Exception as exc:
        llm_call = _llm_call_trace(
            step="Step1.5 candidate validation",
            model_name=state.model_name,
            elapsed_seconds=time.perf_counter() - llm_started,
            usage=None,
            success=False,
            error=repr(exc),
        )
        if not state.allow_llm_fallback:
            raise
        logger.warning(
            "[model-parameter] Step1.5 LLM call failed, using fallback | scenario_id={} error={}",
            state.scenario_id,
            repr(exc),
        )
        fallback_reason = "Step1.5 LLM 후보 검증 실패로 rule-based 후보를 유지했습니다."
        llm_payload = _fallback_candidate_validation_response(
            fallback_reason,
            state.candidate_mappings,
        )
        usage = None
        llm_validation_warnings = [fallback_reason]

    candidates, validation_warnings = _sanitize_parameter_candidate_group_decisions(
        llm_payload.parameter_candidate_groups,
        state.candidate_mappings,
    )
    candidates, routing_warnings = _apply_routing_comment_overrides(
        state.candidate_mappings,
        candidates,
    )
    merged_candidates, merge_warnings = _merge_candidates_by_parameter(candidates)
    logger.info(
        "[model-parameter] validated candidate mappings | scenario_id={} before_count={} after_count={} merged_count={} selected_candidate_keys={} warning_count={}",
        state.scenario_id,
        len(state.candidate_mappings),
        len(candidates),
        len(merged_candidates),
        [candidate.get("candidate_key") for candidate in merged_candidates],
        len(llm_validation_warnings)
        + len(validation_warnings)
        + len(routing_warnings)
        + len(merge_warnings),
    )
    return {
        "candidate_mappings": merged_candidates,
        "validation_warnings": [
            *state.validation_warnings,
            *llm_validation_warnings,
            *validation_warnings,
            *routing_warnings,
            *merge_warnings,
        ],
        "llm_usage": usage,
        "llm_calls": [*state.llm_calls, llm_call],
    }


def load_basecase_samples(state: ModelParameterProposalState) -> dict[str, Any]:
    if state.parameter_knowledge_base is None:
        raise MIBaseError(
            ErrorCode.INVALID_REQUEST,
            detail="parameter_knowledge_base is required",
        )
    records, warnings = build_basecase_records(
        state.parameter_knowledge_base,
        state.candidate_mappings,
        state.scenario_context or {},
    )
    counts_by_candidate: dict[str, int] = {}
    for record in records:
        key = str(record.get("candidate_key") or "")
        counts_by_candidate[key] = counts_by_candidate.get(key, 0) + 1
    logger.info(
        "[model-parameter] loaded basecase records | scenario_id={} record_count={} counts_by_candidate={} warning_count={}",
        state.scenario_id,
        len(records),
        counts_by_candidate,
        len(warnings),
    )
    return {
        "basecase_records": records,
        "validation_warnings": [*state.validation_warnings, *warnings],
    }


def filter_basecase_records_by_slots(state: ModelParameterProposalState) -> dict[str, Any]:
    records = state.basecase_records or []
    filtered = _filter_records_by_selected_slots(records, state.parameter_slots)
    logger.info(
        "[model-parameter] filtered basecase records by slots | scenario_id={} before_count={} after_count={}",
        state.scenario_id,
        len(records),
        len(filtered),
    )
    return {
        "basecase_records": filtered,
        "validation_warnings": state.validation_warnings,
    }


def finalize_empty_parameter_values(state: ModelParameterProposalState) -> dict[str, Any]:
    if not state.candidate_mappings:
        reason = (
            "Step1/Step1.5 candidate 결과가 없어 Step2 slot proposal 및 "
            "Step3 value proposal LLM 호출을 생략했습니다."
        )
    else:
        reason = "Step2 selected slot이 없어 Step3 value proposal LLM 호출을 생략했습니다."
    logger.info(
        "[model-parameter] finalized empty parameter values | scenario_id={} candidate_count={} reason={}",
        state.scenario_id,
        len(state.candidate_mappings),
        reason,
    )
    return {
        "parameter_adjustments": _unselected_adjustments_for_missing_slots(
            state.candidate_mappings,
            reason,
        ),
        "validation_warnings": [*state.validation_warnings, reason],
    }


async def propose_parameter_values(state: ModelParameterProposalState) -> dict[str, Any]:
    if not state.candidate_mappings:
        return {
            "parameter_adjustments": [],
            "validation_warnings": [
                *state.validation_warnings,
                "Step1.5 candidate 결과가 없어 Step3 value 산정을 수행하지 않았습니다.",
            ],
        }

    selected_slots = _selected_parameter_slots(state.parameter_slots)
    if not selected_slots:
        return finalize_empty_parameter_values(state)

    packet = _build_value_proposal_prompt_packet(
        state.scenario_context or {},
        state.candidate_mappings,
        state.parameter_slots,
        state.basecase_records,
        state.non_input_items,
    )
    messages = [
        {"role": "system", "content": VALUE_PROPOSAL_SYSTEM},
        {
            "role": "user",
            "content": (
                "아래 JSON만 근거로 Step3 수급모델 parameter value_grid를 제안하십시오.\n"
                f"{to_compact_json(packet)}"
            ),
        },
    ]

    llm_started = time.perf_counter()
    try:
        result = await _invoke_structured(
            output_schema=LLMValueProposalResponse,
            messages=messages,
            model_name=state.model_name,
        )
        llm_payload = result.result
        usage = result.usage.model_dump() if result.usage is not None else None
        llm_call = _llm_call_trace(
            step="Step3 value proposal",
            model_name=getattr(result, "model", None) or state.model_name,
            elapsed_seconds=time.perf_counter() - llm_started,
            usage=usage,
            success=True,
        )
    except Exception as exc:
        llm_call = _llm_call_trace(
            step="Step3 value proposal",
            model_name=state.model_name,
            elapsed_seconds=time.perf_counter() - llm_started,
            usage=None,
            success=False,
            error=repr(exc),
        )
        if not state.allow_llm_fallback:
            raise
        logger.warning(
            "[model-parameter] Step3 LLM call failed, using fallback | scenario_id={} error={}",
            state.scenario_id,
            repr(exc),
        )
        llm_payload = _fallback_value_response(
            "Step3 LLM 호출 실패로 Step2 slot 기반의 검토 필요 응답을 생성했습니다.",
            state.candidate_mappings,
            state.parameter_slots,
        )
        usage = None

    adjustments, validation_warnings = _sanitize_llm_adjustments(
        llm_payload.parameter_adjustments,
        state.candidate_mappings,
        state.parameter_slots,
        state.basecase_records,
    )
    llm_validation_warnings = list(
        getattr(llm_payload, "validation_warnings", []) or [],
    )
    selected_adjustments = [adjustment for adjustment in adjustments if adjustment.get("selected", True)]
    logger.info(
        "[model-parameter] proposed parameter values | scenario_id={} adjustment_count={} selected_count={} value_counts_by_parameter={} warning_count={}",
        state.scenario_id,
        len(adjustments),
        len(selected_adjustments),
        _value_counts_by_parameter(selected_adjustments),
        len(llm_validation_warnings) + len(validation_warnings),
    )
    return {
        "parameter_adjustments": adjustments,
        "validation_warnings": [
            *state.validation_warnings,
            *llm_validation_warnings,
            *validation_warnings,
        ],
        "llm_usage": usage,
        "llm_calls": [*state.llm_calls, llm_call],
    }


async def propose_parameter_slots(state: ModelParameterProposalState) -> dict[str, Any]:
    if not state.candidate_mappings:
        return {
            "parameter_slots": [],
            "validation_warnings": state.validation_warnings,
        }

    packet = _build_slot_proposal_prompt_packet(
        state.scenario_context or {},
        state.candidate_mappings,
        state.basecase_records,
        state.non_input_items,
    )
    logger.info(
        "[model-parameter] built basecase slot options | scenario_id={} candidate_count={} record_count={}",
        state.scenario_id,
        len(packet["parameter_slot_tasks"]),
        len(state.basecase_records),
    )
    messages = [
        {"role": "system", "content": SLOT_PROPOSAL_SYSTEM},
        {
            "role": "user",
            "content": (
                "아래 JSON만 근거로 Step2 수급모델 parameter slot 축을 제안하십시오.\n"
                f"{to_compact_json(packet)}"
            ),
        },
    ]

    llm_started = time.perf_counter()
    try:
        result = await _invoke_structured(
            output_schema=LLMSlotProposalResponse,
            messages=messages,
            model_name=state.model_name,
        )
        llm_payload = result.result
        usage = result.usage.model_dump() if result.usage is not None else None
        llm_call = _llm_call_trace(
            step="Step2 slot proposal",
            model_name=getattr(result, "model", None) or state.model_name,
            elapsed_seconds=time.perf_counter() - llm_started,
            usage=usage,
            success=True,
        )
    except Exception as exc:
        llm_call = _llm_call_trace(
            step="Step2 slot proposal",
            model_name=state.model_name,
            elapsed_seconds=time.perf_counter() - llm_started,
            usage=None,
            success=False,
            error=repr(exc),
        )
        if not state.allow_llm_fallback:
            raise
        logger.warning(
            "[model-parameter] Step2 LLM call failed, using fallback | scenario_id={} error={}",
            state.scenario_id,
            repr(exc),
        )
        llm_payload = _fallback_slot_response(
            "Step2 LLM 호출 실패로 후보 parameter와 basecase records 기반의 "
            "검토 필요 응답을 생성했습니다.",
            state.candidate_mappings,
        )
        usage = None

    slots, validation_warnings = _sanitize_llm_slots(
        llm_payload.parameter_slots,
        state.candidate_mappings,
        max_selected_slots=MAX_PARAMETER_SLOTS,
    )
    llm_non_input_items = list(getattr(llm_payload, "non_input_items", []) or [])
    llm_validation_warnings = list(
        getattr(llm_payload, "validation_warnings", []) or [],
    )
    non_inputs = [
        item.model_dump()
        for item in llm_non_input_items
    ] or state.non_input_items
    selected_slots = [slot for slot in slots if slot.get("selected", True)]
    logger.info(
        "[model-parameter] proposed parameter slots | scenario_id={} slot_count={} selected_count={} slot_counts_by_parameter={} warning_count={}",
        state.scenario_id,
        len(slots),
        len(selected_slots),
        _slot_counts_by_parameter(selected_slots, state.candidate_mappings),
        len(llm_validation_warnings) + len(validation_warnings),
    )
    return {
        "parameter_slots": slots,
        "non_input_items": non_inputs,
        "validation_warnings": [
            *state.validation_warnings,
            *llm_validation_warnings,
            *validation_warnings,
        ],
        "llm_usage": usage,
        "llm_calls": [*state.llm_calls, llm_call],
    }


def _llm_call_trace(
    *,
    step: str,
    model_name: str | None,
    elapsed_seconds: float,
    usage: dict[str, Any] | None,
    success: bool,
    error: str | None = None,
) -> dict[str, Any]:
    trace: dict[str, Any] = {
        "step": step,
        "success": success,
        "model_name": model_name,
        "elapsed_seconds": round(max(0.0, elapsed_seconds), 3),
    }
    if usage is not None:
        trace["usage"] = usage
    if error:
        trace["error"] = error
    logger.info(
        "[model-parameter] LLM call timing | step={} model_name={} success={} elapsed_seconds={} total_tokens={}",
        step,
        model_name,
        success,
        trace["elapsed_seconds"],
        (usage or {}).get("total_tokens"),
    )
    return trace


def _slot_counts_by_parameter(
    slots: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
) -> dict[str, int]:
    parameter_by_candidate = {
        str(candidate.get("candidate_key") or ""): str(
            candidate.get("parameter_name") or "unknown",
        )
        for candidate in candidates
    }
    counts: dict[str, int] = {}
    for slot in slots:
        key = str(slot.get("candidate_key") or "")
        parameter_name = parameter_by_candidate.get(key, key or "unknown")
        counts[parameter_name] = counts.get(parameter_name, 0) + 1
    return counts


def _value_counts_by_parameter(adjustments: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for adjustment in adjustments:
        parameter_name = str(adjustment.get("parameter_name") or "unknown")
        counts[parameter_name] = counts.get(parameter_name, 0) + len(adjustment.get("value_grid") or [])
    return counts


async def _invoke_structured(
    *,
    output_schema: type[Any],
    messages: list[dict[str, str]],
    model_name: str | None,
) -> Any:
    from apps.connectors.llm.llm_client import invoke_llm_structured_output

    return await invoke_llm_structured_output(
        output_schema=output_schema,
        messages=messages,
        model_name=model_name,
        preference=ModelPreference.QUALITY,
        temperature=0.0,
        max_retries=1,
    )


def _field_key(value: Any) -> str:
    return re.sub(r"[^0-9a-zA-Z가-힣]+", "", str(value or "")).lower()


def _append_unique_text(items: list[str], value: Any) -> None:
    text = str(value or "").strip()
    if text and text not in items:
        items.append(text)


def _append_unique_source_dimension(
    items: list[dict[str, Any]],
    value: dict[str, Any],
) -> None:
    key = to_compact_json(value)
    seen = {to_compact_json(item) for item in items}
    if key not in seen:
        items.append(value)


def _column_role_names(raw: Any) -> list[str]:
    names: list[str] = []
    for part in str(raw or "").split(","):
        if ":" not in part:
            continue
        _, role = part.split(":", 1)
        role_name = str(role or "").strip()
        if role_name:
            _append_unique_text(names, role_name)
    return names


def _allowed_slot_axes_field_names(candidate: dict[str, Any]) -> list[str]:
    axis_names = basecase_slot_axis_names_from_candidate(candidate)
    if axis_names:
        return axis_names

    value_field_name = str(
        candidate.get("canonical_parameter_name")
        or candidate.get("parameter_name")
        or "",
    )
    value_field_key = _field_key(value_field_name)
    axis_names: list[str] = []
    for role_name in _column_role_names(candidate.get("basecase_column_roles")):
        if _field_key(role_name) == value_field_key:
            continue
        _append_unique_text(axis_names, role_name)

    if str(candidate.get("basecase_read_mode") or "").lower() == "matrix_time_columns":
        for axis_name in ("Year", "Month", "Period"):
            _append_unique_text(axis_names, axis_name)
    return axis_names


def _source_dimension_for_prompt(candidate: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "candidate_key": candidate.get("candidate_key"),
        "dimension_key": (
            candidate.get("dimension_key")
            or candidate.get("source_dimension_id")
        ),
        "source_dimension_id": candidate.get("source_dimension_id"),
        "source_dimension_label": candidate.get("source_dimension_label"),
        "source_dimension_value": candidate.get("source_dimension_value"),
        "mapping_method": candidate.get("mapping_method"),
        "mapping_comment": candidate.get("mapping_comment"),
    }
    return {
        key: value
        for key, value in payload.items()
        if value is not None
    }


def _source_dimensions_for_prompt(candidate: dict[str, Any]) -> list[dict[str, Any]]:
    raw = candidate.get("source_dimensions")
    if isinstance(raw, list) and raw:
        return [
            item
            for item in raw
            if isinstance(item, dict)
        ]
    return [_source_dimension_for_prompt(candidate)]


def _supporting_dimension_for_prompt(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_dimension_id": item.get("source_dimension_id"),
        "source_dimension_label": item.get("source_dimension_label"),
        "source_dimension_value": item.get("source_dimension_value"),
        "mapping_method": item.get("mapping_method"),
        "reason": item.get("reason"),
    }


def _candidate_group_key(candidate: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(candidate.get("model_file") or ""),
        str(candidate.get("model_sheet") or ""),
        str(
            candidate.get("canonical_parameter_name")
            or candidate.get("parameter_name")
            or "",
        ),
    )


def _parameter_candidate_key(candidate: dict[str, Any]) -> str:
    event_type_l2_id = candidate.get("event_type_l2_id")
    parts = [
        "parameter",
        _field_key(event_type_l2_id),
        _field_key(candidate.get("model_file")),
        _field_key(candidate.get("model_sheet")),
    ]
    parts.append(
        _field_key(
            candidate.get("canonical_parameter_name")
            or candidate.get("parameter_name"),
        ),
    )
    return "|".join(parts)


def _merge_candidates_by_parameter(
    candidates: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for candidate in candidates:
        groups.setdefault(_candidate_group_key(candidate), []).append(candidate)

    merged_candidates: list[dict[str, Any]] = []
    for group_candidates in groups.values():
        if len(group_candidates) == 1:
            candidate = dict(group_candidates[0])
            candidate["merged_candidate_keys"] = (
                candidate.get("merged_candidate_keys")
                or [candidate.get("candidate_key")]
            )
            candidate["source_dimensions"] = _source_dimensions_for_prompt(candidate)
            merged_candidates.append(candidate)
            continue

        base = dict(group_candidates[0])
        merged_candidate_keys: list[str] = []
        source_dimensions: list[dict[str, Any]] = []
        mapping_methods: list[str] = []
        mapping_comments: list[str] = []
        for candidate in group_candidates:
            for candidate_key in (
                candidate.get("merged_candidate_keys")
                or [candidate.get("candidate_key")]
            ):
                _append_unique_text(merged_candidate_keys, candidate_key)
            for source_dimension in _source_dimensions_for_prompt(candidate):
                _append_unique_source_dimension(source_dimensions, source_dimension)
            _append_unique_text(mapping_methods, candidate.get("mapping_method"))
            _append_unique_text(mapping_comments, candidate.get("mapping_comment"))

        merged_method = (
            mapping_methods[0]
            if len(mapping_methods) == 1
            else "merged"
        )
        base.update(
            {
                "candidate_key": _parameter_candidate_key(base),
                "merged_candidate_keys": merged_candidate_keys,
                "source_dimensions": source_dimensions,
                "source_dimension_id": None,
                "source_dimension_label": None,
                "source_dimension_value": None,
                "dimension_key": None,
                "mapping_method": merged_method,
                "mapping_comment": " ".join(mapping_comments),
            },
        )
        merged_candidates.append(base)

    return merged_candidates, []


def _parameter_validation_prompt_payload(candidate: dict[str, Any]) -> dict[str, Any]:
    return _drop_none_or_empty(
        {
            "parameter_name": (
                candidate.get("canonical_parameter_name")
                or candidate.get("parameter_name")
            ),
            "parameter_hint": candidate.get("parameter_hint"),
            "semantic_axes": candidate.get("semantic_axes"),
        },
    )


def _build_candidate_validation_tasks(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str], dict[str, Any]] = {}
    for candidate in candidates:
        key = _candidate_group_key(candidate)
        task = groups.setdefault(
            key,
            {
                "parameter": _parameter_validation_prompt_payload(candidate),
                "candidate_keys": [],
                "selection_dimensions": [],
            },
        )
        parameter = task["parameter"]
        if "parameter_hint" not in parameter and candidate.get("parameter_hint"):
            parameter["parameter_hint"] = candidate.get("parameter_hint")
        if "semantic_axes" not in parameter and candidate.get("semantic_axes"):
            parameter["semantic_axes"] = candidate.get("semantic_axes")

        for candidate_key in (
            candidate.get("merged_candidate_keys")
            or [candidate.get("candidate_key")]
        ):
            _append_unique_text(task["candidate_keys"], candidate_key)
        for source_dimension in _source_dimensions_for_prompt(candidate):
            dimension = _source_dimension_for_value_task(source_dimension)
            if dimension:
                _append_unique_source_dimension(task["selection_dimensions"], dimension)

    return [
        _drop_none_or_empty(task)
        for task in groups.values()
    ]


def _build_candidate_validation_prompt_packet(
    scenario_context: dict[str, Any],
    candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "scenario_brief": _scenario_brief_for_value_prompt(scenario_context),
        "candidate_validation_tasks": _build_candidate_validation_tasks(candidates),
    }


def _build_slot_proposal_prompt_packet(
    scenario_context: dict[str, Any],
    candidates: list[dict[str, Any]],
    basecase_records: list[dict[str, Any]],
    non_input_items: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "scenario_brief": _scenario_brief_for_value_prompt(scenario_context),
        "period_resolution_policy": _compact_period_resolution_policy(),
        "slot_selection_limits": {
            "maxParameterSlots": MAX_PARAMETER_SLOTS,
            "priority": [
                "parameter_slot_tasks[].basecase_slot_options에 존재하고 scenario/event 의미와 일치하는 slot",
                "basecase에는 없지만 scenario/event에 명확한 실제 모델 input slot",
            ],
        },
        "parameter_slot_tasks": _build_parameter_slot_tasks(
            candidates,
            basecase_records,
            non_input_items,
        ),
    }


def _slot_for_value_prompt(slot: dict[str, Any]) -> dict[str, Any]:
    slot_axes = slot.get("slot_axes") or []
    return {
        "candidate_key": slot.get("candidate_key"),
        "slot_axes": slot_axes,
        "selected_slot_axes_field_names": _slot_axis_names(slot_axes),
    }


def _slot_axis_names(slot_axes: list[dict[str, Any]]) -> list[str]:
    axis_names: list[str] = []
    for axis in slot_axes or []:
        axis_name = axis.get("axis_name")
        if axis_name:
            _append_unique_text(axis_names, axis_name)
    return axis_names


def _build_basecase_value_groups(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    for record in records:
        axes = record.get("axes") or {}
        fixed_axes: dict[str, Any] = {}
        cell_axes: dict[str, Any] = {}
        for axis_name, axis_value in axes.items():
            axis_name_text = str(axis_name)
            display_value = _slot_option_value(axis_value)
            if _is_time_slot_axis(axis_name_text):
                cell_axes[axis_name_text] = display_value
            else:
                fixed_axes[axis_name_text] = display_value

        group_key = to_compact_json(
            [
                record.get("candidate_key"),
                record.get("value_name"),
                fixed_axes,
            ],
        )
        group = groups.setdefault(
            group_key,
            {
                "candidate_key": record.get("candidate_key"),
                "value_name": record.get("value_name"),
                "fixed_axes": fixed_axes,
                "variable_axis_names": [],
                "cells": [],
            },
        )
        for axis_name in cell_axes:
            _append_unique_text(group["variable_axis_names"], axis_name)
        group["cells"].append(
            {
                "reference_id": record.get("reference_id"),
                "axes": cell_axes,
                "basecase_value": record.get("value"),
            },
        )
    return list(groups.values())


def _scenario_brief_for_value_prompt(scenario_context: dict[str, Any]) -> dict[str, Any]:
    scenario = scenario_context.get("scenario") or {}
    event = scenario_context.get("event") or {}
    event_brief = _drop_none_or_empty(
        {
            "title": event.get("event_title_ko"),
            "summary": event.get("one_line_summary"),
            "analysis_excerpt": _trim_prompt_text(event.get("detail_analysis"), 900),
        },
    )
    brief = {
        "scenario_id": scenario.get("scenario_id"),
        "title": scenario.get("title"),
        "selected_dimensions": _selected_dimensions_for_value_prompt(scenario_context),
        "event": event_brief,
    }
    return _drop_none_or_empty(brief)


def _selected_dimensions_for_value_prompt(
    scenario_context: dict[str, Any],
) -> list[dict[str, Any]]:
    scenario = scenario_context.get("scenario") or {}
    dimension_values = scenario.get("dimension_values") or {}
    if not isinstance(dimension_values, dict):
        return []

    label_by_key: dict[str, Any] = {}
    for item in scenario_context.get("dimension_template") or []:
        if not isinstance(item, dict):
            continue
        key = item.get("dim_key")
        if key:
            label_by_key[str(key)] = item.get("label")

    selected: list[dict[str, Any]] = []
    for key, value in dimension_values.items():
        selected.append(
            _drop_none_or_empty(
                {
                    "dimension_key": key,
                    "dimension_label": label_by_key.get(str(key)),
                    "dimension_value": value,
                },
            ),
        )
    return selected


def _trim_prompt_text(value: Any, limit: int) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    if len(text) <= limit:
        return text
    return text[:limit].rstrip()


def _drop_none_or_empty(value: dict[str, Any]) -> dict[str, Any]:
    return {
        key: item
        for key, item in value.items()
        if item is not None and item != "" and item != [] and item != {}
    }


def _source_dimension_for_value_task(item: dict[str, Any]) -> dict[str, Any]:
    return _drop_none_or_empty(
        {
            "dimension_key": (
                item.get("dimension_key")
                or item.get("source_dimension_id")
            ),
            "dimension_label": item.get("source_dimension_label"),
            "dimension_value": item.get("source_dimension_value"),
            "mapping_method": item.get("mapping_method"),
            "mapping_comment": item.get("mapping_comment"),
        },
    )


def _supporting_dimension_for_value_task(item: dict[str, Any]) -> dict[str, Any]:
    return _drop_none_or_empty(
        {
            "dimension_key": item.get("source_dimension_id"),
            "dimension_label": item.get("source_dimension_label"),
            "dimension_value": item.get("source_dimension_value"),
            "mapping_method": item.get("mapping_method"),
            "reason": item.get("reason"),
        },
    )


def _selection_dimensions_for_task(candidate: dict[str, Any]) -> list[dict[str, Any]]:
    dimensions: list[dict[str, Any]] = []
    for item in _source_dimensions_for_prompt(candidate):
        dimension = _source_dimension_for_value_task(item)
        if dimension:
            dimensions.append(dimension)
    return dimensions


def _supporting_dimensions_for_task(
    non_input_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    dimensions: list[dict[str, Any]] = []
    for item in non_input_items:
        dimension = _supporting_dimension_for_value_task(item)
        if dimension:
            dimensions.append(dimension)
    return dimensions


def _slot_for_value_task(slot: dict[str, Any]) -> dict[str, Any]:
    return {
        "slot_axes": slot.get("slot_axes") or [],
    }


def _strip_candidate_key_from_basecase_group(group: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in group.items()
        if key != "candidate_key"
    }


def _strip_candidate_key_from_slot_option(option: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in option.items()
        if key != "candidate_key"
    }


def _selected_slot_axis_names_for_task(slots: list[dict[str, Any]]) -> list[str]:
    axis_names: list[str] = []
    for slot in slots:
        for axis_name in _slot_axis_names(slot.get("slot_axes") or []):
            _append_unique_text(axis_names, axis_name)
    return axis_names


def _compact_period_resolution_policy() -> dict[str, Any]:
    policy = _period_resolution_policy()
    return {
        "current_year": policy.get("current_year"),
        "current_month": policy.get("current_month"),
        "rules": policy.get("rules") or [],
    }


def _parameter_prompt_payload(candidate: dict[str, Any]) -> dict[str, Any]:
    return _drop_none_or_empty(
        {
            "candidate_key": candidate.get("candidate_key"),
            "parameter_name": (
                candidate.get("canonical_parameter_name")
                or candidate.get("parameter_name")
            ),
            "parameter_hint": candidate.get("parameter_hint"),
            "semantic_axes": candidate.get("semantic_axes"),
            "allowed_slot_axes_field_names": _allowed_slot_axes_field_names(candidate),
        },
    )


def _build_parameter_slot_tasks(
    candidates: list[dict[str, Any]],
    basecase_records: list[dict[str, Any]],
    non_input_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    basecase_options_by_key: dict[str, list[dict[str, Any]]] = {}
    for option in _build_basecase_slot_options(basecase_records):
        candidate_key = str(option.get("candidate_key") or "")
        basecase_options_by_key.setdefault(candidate_key, []).append(
            _strip_candidate_key_from_slot_option(option),
        )

    supporting_dimensions = _supporting_dimensions_for_task(non_input_items)
    tasks: list[dict[str, Any]] = []
    for candidate in candidates:
        candidate_key = str(candidate.get("candidate_key") or "")
        task = {
            "parameter": _parameter_prompt_payload(candidate),
            "selection_dimensions": _selection_dimensions_for_task(candidate),
            "supporting_dimensions": supporting_dimensions,
            "basecase_slot_options": basecase_options_by_key.get(candidate_key, []),
        }
        tasks.append(_drop_none_or_empty(task))
    return tasks


def _build_parameter_value_tasks(
    candidates: list[dict[str, Any]],
    parameter_slots: list[dict[str, Any]],
    basecase_records: list[dict[str, Any]],
    non_input_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    selected_slots_by_key = _group_selected_slots_by_candidate(parameter_slots)
    basecase_groups_by_key: dict[str, list[dict[str, Any]]] = {}
    for group in _build_basecase_value_groups(basecase_records):
        candidate_key = str(group.get("candidate_key") or "")
        basecase_groups_by_key.setdefault(candidate_key, []).append(
            _strip_candidate_key_from_basecase_group(group),
        )

    supporting_dimensions = _supporting_dimensions_for_task(non_input_items)
    tasks: list[dict[str, Any]] = []
    for candidate in candidates:
        candidate_key = str(candidate.get("candidate_key") or "")
        selected_slots = selected_slots_by_key.get(candidate_key, [])
        task = {
            "parameter": _parameter_prompt_payload(candidate),
            "selection_dimensions": _selection_dimensions_for_task(candidate),
            "supporting_dimensions": supporting_dimensions,
            "selected_slot_axes_field_names": _selected_slot_axis_names_for_task(selected_slots),
            "selected_slots": [
                _slot_for_value_task(slot)
                for slot in selected_slots
            ],
            "basecase_value_groups": basecase_groups_by_key.get(candidate_key, []),
        }
        tasks.append(_drop_none_or_empty(task))
    return tasks


def _build_value_proposal_prompt_packet(
    scenario_context: dict[str, Any],
    candidates: list[dict[str, Any]],
    parameter_slots: list[dict[str, Any]],
    basecase_records: list[dict[str, Any]],
    non_input_items: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "scenario_brief": _scenario_brief_for_value_prompt(scenario_context),
        "period_resolution_policy": _compact_period_resolution_policy(),
        "basecase_record_selection_policy": {
            "maxRecords": MAX_VALUE_PROMPT_BASECASE_RECORDS,
        },
        "parameter_value_tasks": _build_parameter_value_tasks(
            candidates,
            parameter_slots,
            basecase_records,
            non_input_items,
        ),
    }


AMBIGUOUS_AXIS_TOKENS = (
    "미정",
    "후보",
    "추정",
    "불명",
    "미상",
    "일부",
    "대체 공급국",
    "확정 불가",
    "unknown",
    "unspecified",
    "not specified",
    "tbd",
    "n/a",
)
MULTI_VALUE_AXIS_MARKERS = (";", "；", " 또는 ", " or ")


def _axis_value_issue(axis_name: Any, axis_value: Any) -> str | None:
    if axis_value is None:
        return "빈 축 값"
    text = str(axis_value).strip()
    if not text:
        return "빈 축 값"
    normalized = " ".join(text.lower().split())
    if "?" in text:
        return "불확실성 표기 포함"
    for token in AMBIGUOUS_AXIS_TOKENS:
        if token in normalized:
            return f"모호한 축 값 포함: {token}"
    for marker in MULTI_VALUE_AXIS_MARKERS:
        if marker in normalized:
            return f"여러 축 값을 하나의 문자열로 결합함: {marker.strip()}"
    axis_name_text = str(axis_name or "").lower()
    if axis_name_text in {"year", "month", "period"} and "향후" in normalized:
        return "기간 표현을 명확한 Year/Month/Period 값으로 변환하지 않음"
    return None


def _slot_axis_issues(slot_axes: list[ParameterSlotAxis]) -> list[str]:
    issues: list[str] = []
    for axis in slot_axes:
        issue = _axis_value_issue(axis.axis_name, axis.axis_value)
        if issue:
            issues.append(f"{axis.axis_name}={axis.axis_value}: {issue}")
    return issues


def _coordinate_issues(coordinates: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for axis_name, axis_value in coordinates.items():
        issue = _axis_value_issue(axis_name, axis_value)
        if issue:
            issues.append(f"{axis_name}={axis_value}: {issue}")
    period_issue = _year_month_coordinate_issue(coordinates)
    if period_issue:
        issues.append(period_issue)
    return issues


def _int_axis_value(value: Any) -> int | None:
    try:
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return None
            return int(float(text))
        return int(value)
    except (TypeError, ValueError):
        return None


def _year_month_coordinate_issue(coordinates: dict[str, Any]) -> str | None:
    year = _int_axis_value(coordinates.get("Year"))
    month = _int_axis_value(coordinates.get("Month"))
    if year is None or month is None:
        return None
    if not 1 <= month <= 12:
        return f"Year/Month 좌표의 Month가 유효하지 않음: {month}"
    return None


def _normalize_axis_value(value: Any) -> str:
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return " ".join(str(value).strip().lower().split())


def _slot_axis_pairs(slot: dict[str, Any]) -> list[tuple[str, Any]]:
    pairs: list[tuple[str, Any]] = []
    for axis in slot.get("slot_axes") or []:
        axis_name = axis.get("axis_name")
        if axis_name:
            pairs.append((str(axis_name), axis.get("axis_value")))
    return pairs


def _record_axis_matches(
    record_axes: dict[str, Any],
    axis_name: str,
    axis_value: Any,
) -> bool:
    return (
        axis_name in record_axes
        and _normalize_axis_value(record_axes.get(axis_name))
        == _normalize_axis_value(axis_value)
    )


def _record_fully_matches_slot(record: dict[str, Any], slot: dict[str, Any]) -> bool:
    record_axes = record.get("axes") or {}
    axis_pairs = _slot_axis_pairs(slot)
    if not axis_pairs:
        return True
    for axis_name, axis_value in axis_pairs:
        if not _record_axis_matches(record_axes, axis_name, axis_value):
            return False
    return True


def _record_matches_slot_prefix_depth(
    record: dict[str, Any],
    slot: dict[str, Any],
    depth: int,
) -> bool:
    axis_pairs = _slot_axis_pairs(slot)
    if depth <= 0 or depth > len(axis_pairs):
        return False
    record_axes = record.get("axes") or {}
    return all(
        _record_axis_matches(record_axes, axis_name, axis_value)
        for axis_name, axis_value in axis_pairs[:depth]
    )


def _filter_records_by_selected_slots(
    records: list[dict[str, Any]],
    slots: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    selected_slots = _selected_parameter_slots(slots)
    if not selected_slots:
        return []

    if len(records) <= MAX_VALUE_PROMPT_BASECASE_RECORDS:
        return records

    slots_by_candidate: dict[str, list[dict[str, Any]]] = {}
    for slot in selected_slots:
        candidate_key = str(slot.get("candidate_key") or "")
        if not candidate_key:
            continue
        slots_by_candidate.setdefault(candidate_key, []).append(slot)

    filtered: list[dict[str, Any]] = []
    included_indices: set[int] = set()

    def append_record(index: int, record: dict[str, Any]) -> bool:
        if index in included_indices:
            return False
        included_indices.add(index)
        filtered.append(record)
        return len(filtered) >= MAX_VALUE_PROMPT_BASECASE_RECORDS

    for index, record in enumerate(records):
        candidate_key = str(record.get("candidate_key") or "")
        candidate_slots = slots_by_candidate.get(candidate_key) or []
        if any(_record_fully_matches_slot(record, slot) for slot in candidate_slots):
            if append_record(index, record):
                return filtered

    max_axis_count = max(
        (
            len(_slot_axis_pairs(slot))
            for candidate_slots in slots_by_candidate.values()
            for slot in candidate_slots
        ),
        default=0,
    )
    for depth in range(max_axis_count - 1, 0, -1):
        for index, record in enumerate(records):
            candidate_key = str(record.get("candidate_key") or "")
            candidate_slots = slots_by_candidate.get(candidate_key) or []
            if any(
                _record_matches_slot_prefix_depth(record, slot, depth)
                for slot in candidate_slots
            ):
                if append_record(index, record):
                    return filtered
    return filtered


def _slot_option_value(value: Any) -> Any:
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def _is_time_slot_axis(axis_name: str) -> bool:
    return axis_name in TIME_SLOT_AXIS_NAMES


def _new_hierarchy_node(value: Any) -> dict[str, Any]:
    return {"value": value, "children": {}}


def _add_hierarchy_path(root: dict[str, dict[str, Any]], path: list[Any]) -> None:
    if not path:
        return
    display_value = _slot_option_value(path[0])
    key = _normalize_axis_value(display_value)
    node = root.setdefault(key, _new_hierarchy_node(display_value))
    _add_hierarchy_path(node["children"], path[1:])


def _hierarchy_for_prompt(root: dict[str, dict[str, Any]]) -> list[Any]:
    items: list[Any] = []
    for _, node in sorted(root.items(), key=lambda item: str(item[1]["value"])):
        children = _hierarchy_for_prompt(node["children"])
        if children:
            items.append([node["value"], children])
        else:
            items.append(node["value"])
    return items


def _build_basecase_slot_options(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    options: dict[str, dict[str, Any]] = {}
    axis_values_by_candidate: dict[str, dict[str, dict[str, Any]]] = {}
    hierarchy_roots_by_candidate: dict[str, dict[str, dict[str, Any]]] = {}
    for record in records:
        candidate_key = str(record.get("candidate_key") or "")
        option = options.setdefault(
            candidate_key,
            {
                "candidate_key": candidate_key,
                "axis_names": [],
                "axis_values": {},
                "slot_hierarchy_axes": [],
                "slot_hierarchy": [],
            },
        )
        axis_values = axis_values_by_candidate.setdefault(candidate_key, {})
        for axis_name, axis_value in (record.get("axes") or {}).items():
            axis_name_text = str(axis_name)
            if axis_name_text not in option["axis_names"]:
                option["axis_names"].append(axis_name_text)
            if _is_time_slot_axis(axis_name_text):
                values = axis_values.setdefault(axis_name_text, {})
                display_value = _slot_option_value(axis_value)
                values.setdefault(_normalize_axis_value(display_value), display_value)

    for candidate_key, option in options.items():
        non_time_axes = [
            axis_name
            for axis_name in option["axis_names"]
            if not _is_time_slot_axis(axis_name)
        ]
        option["slot_hierarchy_axes"] = non_time_axes
        root = hierarchy_roots_by_candidate.setdefault(candidate_key, {})
        for record in records:
            if str(record.get("candidate_key") or "") != candidate_key:
                continue
            axes = record.get("axes") or {}
            path = [
                axes.get(axis_name)
                for axis_name in non_time_axes
            ]
            if path and all(value not in (None, "") for value in path):
                _add_hierarchy_path(root, path)
        option["slot_hierarchy"] = _hierarchy_for_prompt(root)
        axis_values = axis_values_by_candidate.get(candidate_key) or {}
        option["axis_values"] = {
            axis_name: [
                value
                for _, value in sorted(values.items(), key=lambda item: str(item[1]))
            ]
            for axis_name, values in axis_values.items()
        }
    return list(options.values())


def _sanitize_parameter_candidate_group_decisions(
    groups: list[ParameterCandidateGroupDecision],
    candidates: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    candidate_by_key = {str(candidate["candidate_key"]): candidate for candidate in candidates}
    selected_by_key: dict[str, dict[str, Any]] = {}
    warnings: list[str] = []
    returned_keys: set[str] = set()

    for group in groups:
        group_candidate_keys = [
            str(candidate_key)
            for candidate_key in group.candidate_keys
            if str(candidate_key or "").strip()
        ]
        if not group_candidate_keys:
            warnings.append("LLM parameter_candidate_groups에 빈 candidate_keys가 있어 제외했습니다.")
            continue

        known_keys = [
            candidate_key
            for candidate_key in group_candidate_keys
            if candidate_key in candidate_by_key
        ]
        unknown_keys = sorted(set(group_candidate_keys) - set(known_keys))
        if unknown_keys:
            warnings.append(
                "LLM이 알 수 없는 candidate_key를 parameter_candidate_groups에 반환해 제외했습니다: "
                f"{unknown_keys}",
            )
        returned_keys.update(known_keys)
        if not group.selected:
            continue

        for candidate_key in known_keys:
            candidate = candidate_by_key[candidate_key]
            selected_by_key[candidate_key] = dict(candidate)

    for candidate in candidates:
        candidate_key = str(candidate.get("candidate_key") or "")
        if candidate_key in selected_by_key:
            continue
        mapping_method = str(candidate.get("mapping_method") or "").lower()
        if mapping_method == "direct":
            enriched = dict(candidate)
            if candidate_key in returned_keys:
                warning = (
                    "direct 후보는 LLM parameter group selected=false와 무관하게 유지했습니다: "
                    f"{candidate_key}"
                )
            else:
                warning = (
                    "LLM parameter group 응답에 누락된 direct candidate_key는 유지했습니다: "
                    f"{candidate_key}"
                )
            selected_by_key[candidate_key] = enriched
            warnings.append(warning)

    missing_keys = sorted(
        key
        for key in set(candidate_by_key) - returned_keys
        if str(candidate_by_key[key].get("mapping_method") or "").lower() != "direct"
    )
    if missing_keys:
        warnings.append(
            "LLM parameter group 응답에 누락된 candidate_key는 제외했습니다: "
            f"{missing_keys}",
        )
    selected_candidates = [
        selected_by_key[str(candidate.get("candidate_key") or "")]
        for candidate in candidates
        if str(candidate.get("candidate_key") or "") in selected_by_key
    ]
    if candidates and not selected_candidates:
        warnings.append("LLM parameter group 검증 결과 selected=true candidate가 없습니다.")
    return selected_candidates, warnings


ROUTING_COMMENT_GENERIC_TOKENS = {
    "경우",
    "시설",
    "시",
    "영향",
    "유형",
    "피해",
    "facility",
    "impact",
    "type",
    "when",
}

def _routing_match_tokens(value: Any) -> list[str]:
    tokens = re.findall(r"[0-9a-zA-Z가-힣]+", str(value or "").lower())
    return [
        token
        for token in tokens
        if len(token) >= 2 and token not in ROUTING_COMMENT_GENERIC_TOKENS
    ]


def _routing_comment_matches_dimension_value(value: Any, comment: Any) -> bool:
    value_tokens = _routing_match_tokens(value)
    comment_tokens = _routing_match_tokens(comment)
    if not value_tokens or not comment_tokens:
        return False
    comment_text = " ".join(comment_tokens)
    return all(token in comment_text for token in value_tokens)


def _apply_routing_comment_overrides(
    all_candidates: list[dict[str, Any]],
    selected_candidates: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Use bridge-sheet routing comments as deterministic tiebreakers.

    LLM still performs the candidate gate, but when the DB dimension value
    clearly matches a routing row comment such as "생산 시설 피해 시", that row is
    the authoritative route for the dimension.
    """

    selected_by_key = {
        str(candidate.get("candidate_key") or ""): dict(candidate)
        for candidate in selected_candidates
    }
    warnings: list[str] = []
    routing_groups: dict[tuple[Any, str], list[dict[str, Any]]] = {}
    for candidate in all_candidates:
        if str(candidate.get("mapping_method") or "").lower() != "routing":
            continue
        group_key = (
            candidate.get("event_type_l2_id"),
            str(candidate.get("dimension_key") or candidate.get("source_dimension_id") or ""),
        )
        routing_groups.setdefault(group_key, []).append(candidate)

    for group_candidates in routing_groups.values():
        matched = [
            candidate
            for candidate in group_candidates
            if _routing_comment_matches_dimension_value(
                candidate.get("source_dimension_value"),
                candidate.get("mapping_comment"),
            )
        ]
        if not matched:
            continue
        matched_keys = {str(candidate.get("candidate_key") or "") for candidate in matched}
        for candidate in group_candidates:
            candidate_key = str(candidate.get("candidate_key") or "")
            if candidate_key in matched_keys:
                if candidate_key not in selected_by_key:
                    enriched = dict(candidate)
                    selected_by_key[candidate_key] = enriched
                    warnings.append(
                        "routing 후보를 DB 매핑 comment 기준으로 selected=true 보정했습니다: "
                        f"{candidate_key}",
                    )
                continue
            if candidate_key in selected_by_key:
                selected_by_key.pop(candidate_key, None)
                warnings.append(
                    "routing 후보를 DB 매핑 comment 기준으로 selected=false 보정했습니다: "
                    f"{candidate_key}",
                )

    ordered = [
        selected_by_key[str(candidate.get("candidate_key") or "")]
        for candidate in all_candidates
        if str(candidate.get("candidate_key") or "") in selected_by_key
    ]
    return ordered, warnings


def _sanitize_llm_slots(
    slots: list[LLMSlotProposal],
    candidates: list[dict[str, Any]],
    *,
    max_selected_slots: int = MAX_PARAMETER_SLOTS,
) -> tuple[list[dict[str, Any]], list[str]]:
    candidate_by_key = {str(candidate["candidate_key"]): candidate for candidate in candidates}
    sanitized: list[dict[str, Any]] = []
    warnings: list[str] = []
    selected_slot_count = 0
    for slot in slots:
        if slot.candidate_key not in candidate_by_key:
            warnings.append(
                "LLM이 알 수 없는 candidate_key를 반환해 slot을 제외했습니다: "
                f"{slot.candidate_key}",
            )
            continue
        issues = _slot_axis_issues(slot.slot_axes)
        if issues:
            reason = (
                "LLM이 실제 모델 input으로 사용할 수 없는 모호한 slot 값을 반환해 "
                f"selected=false로 보정했습니다: {', '.join(issues)}"
            )
            warnings.append(f"{reason}: {slot.candidate_key}")
            patched = slot.model_copy(
                update={
                    "selected": False,
                    "slot_axes": [],
                },
            )
            sanitized.append(_parameter_slot_from_llm(patched))
            continue
        if slot.selected is not False:
            selected_slot_count += 1
            if selected_slot_count > max_selected_slots:
                reason = (
                    "LLM이 slot_selection_limits.maxParameterSlots를 초과해 반환하여 "
                    "초과 slot을 selected=false로 보정했습니다."
                )
                warnings.append(f"{reason}: {slot.candidate_key}")
                patched = slot.model_copy(
                    update={
                        "selected": False,
                    },
                )
                sanitized.append(_parameter_slot_from_llm(patched))
                continue
        sanitized.append(_parameter_slot_from_llm(slot))
    return sanitized, warnings


def _parameter_slot_from_llm(slot: LLMSlotProposal) -> dict[str, Any]:
    return ParameterSlotProposal(
        candidate_key=slot.candidate_key,
        selected=slot.selected,
        slot_axes=[
            ParameterSlotAxis(
                axis_name=axis.axis_name,
                axis_value=axis.axis_value,
            )
            for axis in slot.slot_axes
        ],
    ).model_dump()


def _group_selected_slots_by_candidate(
    slots: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for slot in _selected_parameter_slots(slots):
        candidate_key = str(slot.get("candidate_key") or "")
        if not candidate_key:
            continue
        grouped.setdefault(candidate_key, []).append(slot)
    return grouped


def _selected_parameter_slots(slots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [slot for slot in slots if slot.get("selected", True) is not False]


def _slot_axis_value(axis_name: str, axis_value: Any) -> Any:
    if axis_name.lower() in {"year", "month"}:
        parsed = _int_axis_value(axis_value)
        if parsed is not None:
            return parsed
    return axis_value


def _slot_axes_for_candidate(slots: list[dict[str, Any]]) -> list[ParameterSlotAxis]:
    slot_axes: list[ParameterSlotAxis] = []
    seen: set[tuple[str, str]] = set()
    for slot in slots:
        for axis in slot.get("slot_axes") or []:
            axis_name = str(axis.get("axis_name") or "").strip()
            if not axis_name:
                continue
            axis_value = _slot_axis_value(axis_name, axis.get("axis_value"))
            key = (axis_name, _normalize_axis_value(axis_value))
            if key in seen:
                continue
            seen.add(key)
            slot_axes.append(
                ParameterSlotAxis(
                    axis_name=axis_name,
                    axis_value=str(axis_value),
                ),
            )
    return slot_axes


def _canonical_coordinate_key(coordinates: dict[str, Any]) -> str:
    normalized = {
        axis_name: _normalize_axis_value(_slot_axis_value(axis_name, axis_value))
        for axis_name, axis_value in sorted(
            (
                (str(raw_axis_name).strip(), axis_value)
                for raw_axis_name, axis_value in (coordinates or {}).items()
                if str(raw_axis_name).strip()
            ),
            key=lambda item: item[0],
        )
    }
    return to_compact_json(normalized)


def _value_cell_signature(cell: ParameterValueCell) -> str:
    return to_compact_json(
        {
            "basecase_value": cell.basecase_value,
            "proposed_value": cell.proposed_value,
        },
    )


def _dedupe_value_grid_by_slot(
    cells: list[ParameterValueCell],
) -> tuple[list[ParameterValueCell], list[str]]:
    deduped: list[ParameterValueCell] = []
    seen_by_slot: dict[str, tuple[str, ParameterValueCell]] = {}
    conflicts: list[str] = []

    for cell in cells:
        slot_key = _canonical_coordinate_key(cell.coordinates)
        signature = _value_cell_signature(cell)
        existing = seen_by_slot.get(slot_key)
        if existing is None:
            seen_by_slot[slot_key] = (signature, cell)
            deduped.append(cell)
            continue
        if existing[0] == signature:
            continue
        conflicts.append(
            "동일 slot 좌표에 서로 다른 value 제안이 반환되었습니다: "
            f"slot={slot_key}",
        )

    return deduped, conflicts


def _parameter_value_cell_from_llm(cell: LLMValueCell) -> ParameterValueCell:
    return ParameterValueCell(
        coordinates=cell.coordinates,
        basecase_value=None,
        proposed_value=cell.proposed_value,
        rationale_ko=cell.rationale_ko,
        basecase_reference_ids=cell.basecase_reference_ids,
    )


def _sanitize_llm_adjustments(
    adjustments: list[LLMValueAdjustment],
    candidates: list[dict[str, Any]],
    slots: list[dict[str, Any]],
    basecase_records: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    candidate_by_key = {str(candidate["candidate_key"]): candidate for candidate in candidates}
    slots_by_key = _group_selected_slots_by_candidate(slots)
    basecase_by_reference_id = {
        str(record["reference_id"]): record
        for record in basecase_records
        if record.get("reference_id") is not None
    }
    sanitized: list[dict[str, Any]] = []
    warnings: list[str] = []
    returned_candidate_keys: set[str] = set()
    for adjustment in adjustments:
        candidate = candidate_by_key.get(adjustment.candidate_key)
        if candidate is None:
            warnings.append(
                "LLM이 알 수 없는 candidate_key를 반환해 제외했습니다: "
                f"{adjustment.candidate_key}",
            )
            continue
        returned_candidate_keys.add(adjustment.candidate_key)
        slot_axes = _slot_axes_for_candidate(slots_by_key.get(adjustment.candidate_key, []))
        selected = adjustment.selected
        slot_issues = _slot_axis_issues(slot_axes)
        if slot_issues and selected:
            reason = (
                "Step3 응답 slot_axes에 실제 모델 input으로 사용할 수 없는 값이 있어 "
                f"selected=false로 보정했습니다: {', '.join(slot_issues)}"
            )
            warnings.append(f"{reason}: {adjustment.candidate_key}")
            selected = False

        value_grid: list[ParameterValueCell] = []
        for raw_cell in adjustment.value_grid:
            cell = _parameter_value_cell_from_llm(raw_cell)
            coordinate_issues = _coordinate_issues(cell.coordinates)
            if coordinate_issues:
                reason = (
                    "Step3 응답 value_grid.coordinates에 모호한 값이 있어 "
                    f"cell을 제외했습니다: {', '.join(coordinate_issues)}"
                )
                warnings.append(f"{reason}: {adjustment.candidate_key}")
                continue
            if cell.proposed_value is None:
                reason = (
                    "Step3 응답 value_grid.proposed_value가 null이라 "
                    "cell을 제외했습니다. 범위형 dimension은 자동 변환해야 합니다."
                )
                warnings.append(f"{reason}: {adjustment.candidate_key}")
                continue
            value_grid.append(_patch_basecase_value(cell, basecase_by_reference_id))

        value_grid, slot_conflicts = _dedupe_value_grid_by_slot(value_grid)
        if slot_conflicts and selected:
            reason = (
                "Step3 응답 value_grid에 동일 slot 좌표의 value 충돌이 있어 "
                "selected=false로 보정했습니다."
            )
            warnings.append(f"{reason}: {adjustment.candidate_key}")
            warnings.extend(f"{conflict}: {adjustment.candidate_key}" for conflict in slot_conflicts)
            selected = False

        if selected and not value_grid:
            reason = "명확한 value_grid 좌표/제안값이 없어 selected=false로 보정했습니다."
            warnings.append(f"{reason}: {adjustment.candidate_key}")
            selected = False

        patched = ParameterAdjustment(
            candidate_key=adjustment.candidate_key,
            model_file=str(candidate.get("model_file") or ""),
            model_sheet=str(candidate.get("model_sheet") or ""),
            parameter_name=str(
                candidate.get("canonical_parameter_name")
                or candidate.get("parameter_name")
                or "",
            ),
            selected=selected,
            slot_axes=slot_axes,
            value_grid=value_grid if selected else [],
            parameter_selection_rationale_ko=adjustment.rationale_ko,
        )
        sanitized.append(patched.model_dump())

    missing_candidate_keys = sorted(set(candidate_by_key) - returned_candidate_keys)
    for candidate_key in missing_candidate_keys:
        candidate = candidate_by_key[candidate_key]
        reason = (
            "LLM Step3 응답에 candidate_key가 누락되어 서버가 selected=false "
            "검토 항목으로 보강했습니다."
        )
        slot_axes = [
            *_slot_axes_for_candidate(slots_by_key.get(candidate_key, [])),
        ]
        sanitized.append(
            ParameterAdjustment(
                candidate_key=candidate_key,
                model_file=str(candidate.get("model_file") or ""),
                model_sheet=str(candidate.get("model_sheet") or ""),
                parameter_name=str(
                    candidate.get("canonical_parameter_name")
                    or candidate.get("parameter_name")
                    or "",
                ),
                selected=False,
                slot_axes=slot_axes,
                value_grid=[],
                parameter_selection_rationale_ko=reason,
            ).model_dump(),
        )
        warnings.append(f"{reason}: {candidate_key}")
    return sanitized, warnings


def _current_year_month() -> tuple[int, int]:
    today = date.today()
    return today.year, today.month


def _period_resolution_policy() -> dict[str, Any]:
    year, month = _current_year_month()
    return {
        "current_date": date.today().isoformat(),
        "current_year": year,
        "current_month": month,
        "rules": [
            "scenario/event에 YYYY-MM 또는 YYYY년 M월처럼 연월이 명확하면 현재 기준월과 무관하게 그대로 사용합니다.",
            "연도 없이 월만 명시되면 current_year/current_month 이후의 가장 가까운 해당 월로 변환합니다.",
            "affected_period/period가 N개월이면 current_year/current_month부터 N개월 범위의 Year/Month/Period만 사용합니다.",
            "명확한 연월/월 근거가 없으면 추론상 current_year/current_month 이후부터 필요한 period 범위만 전개합니다.",
        ],
    }


def _is_current_or_future_year_month(year: int, month: int) -> bool:
    current_year, current_month = _current_year_month()
    return (year, month) >= (current_year, current_month)


def _first_explicit_year_month(text: str) -> tuple[int, int] | None:
    patterns = (
        r"(20\d{2})\s*년\s*(1[0-2]|0?[1-9])\s*월",
        r"(20\d{2})[-./](1[0-2]|0?[1-9])(?:[-./]\d{1,2})?",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return int(match.group(1)), int(match.group(2))
    return None


def _month_only_candidates(text: str) -> list[int]:
    months: list[int] = []
    for match in re.finditer(r"(?<!\d)(1[0-2]|0?[1-9])\s*월", text):
        month = int(match.group(1))
        if month not in months:
            months.append(month)
    return months


def _nearest_current_or_future_month(months: list[int]) -> tuple[int, int] | None:
    if not months:
        return None
    current_year, current_month = _current_year_month()
    candidates = [
        (current_year if month >= current_month else current_year + 1, month)
        for month in months
    ]
    return min(candidates)


def _scenario_period_text(dimensions: dict[str, Any], scenario_context: dict[str, Any]) -> str:
    scenario = scenario_context.get("scenario") or {}
    return "\n".join(
        str(item or "")
        for item in (
            scenario.get("title"),
            scenario.get("narrative"),
            *dimensions.values(),
        )
    )


def _event_period_text(scenario_context: dict[str, Any]) -> str:
    group = scenario_context.get("scenario_group") or {}
    event = scenario_context.get("event") or {}
    return "\n".join(
        str(item or "")
        for item in (
            group.get("title"),
            group.get("summary"),
            group.get("description"),
            event.get("occurred_at"),
            event.get("latest_record_first_created"),
            event.get("oldest_record_first_created"),
            event.get("event_title_ko"),
            event.get("one_line_summary"),
            event.get("detail_analysis"),
        )
    )


def _period_start_year_month(
    dimensions: dict[str, Any],
    scenario_context: dict[str, Any],
) -> tuple[int, int, str]:
    scenario_text = _scenario_period_text(dimensions, scenario_context)
    scenario_explicit = _first_explicit_year_month(scenario_text)
    if scenario_explicit is not None:
        return (*scenario_explicit, "scenario에 명시된 연월")

    event_text = _event_period_text(scenario_context)
    event_explicit = _first_explicit_year_month(event_text)
    if event_explicit is not None:
        return (*event_explicit, "event에 명시된 연월")

    scenario_month = (
        _nearest_current_or_future_month(_month_only_candidates(scenario_text))
        if scenario_explicit is None
        else None
    )
    if scenario_month is not None:
        return (*scenario_month, "scenario에 명시된 월-only를 현재 이후 연월로 변환")

    event_month = (
        _nearest_current_or_future_month(_month_only_candidates(event_text))
        if event_explicit is None
        else None
    )
    if event_month is not None:
        return (*event_month, "event에 명시된 월-only를 현재 이후 연월로 변환")

    current_year, current_month = _current_year_month()
    return current_year, current_month, "명확한 연월 근거가 없어 현재 월부터 전개"


def _patch_basecase_value(
    cell: ParameterValueCell,
    basecase_by_reference_id: dict[str, dict[str, Any]],
) -> ParameterValueCell:
    if cell.basecase_value is not None or not cell.basecase_reference_ids:
        return cell
    matched_values = [
        basecase_by_reference_id[reference_id].get("value")
        for reference_id in cell.basecase_reference_ids
        if reference_id in basecase_by_reference_id
    ]
    if not matched_values:
        return cell
    basecase_value: Any = matched_values[0] if len(matched_values) == 1 else matched_values
    return cell.model_copy(update={"basecase_value": basecase_value})


def _fallback_candidate_validation_response(
    reason: str,
    candidates: list[dict[str, Any]],
) -> LLMCandidateValidationResponse:
    return LLMCandidateValidationResponse(
        parameter_candidate_groups=[
            ParameterCandidateGroupDecision(
                candidate_keys=[
                    str(candidate_key)
                    for candidate_key in task.get("candidate_keys") or []
                ],
                selected=True,
            )
            for task in _build_candidate_validation_tasks(candidates)
        ],
    )


def _fallback_slot_response(reason: str, candidates: list[dict[str, Any]]) -> LLMSlotProposalResponse:
    return LLMSlotProposalResponse(
        parameter_slots=[
            ParameterSlotProposal(
                candidate_key=str(candidate["candidate_key"]),
                selected=True,
                slot_axes=[
                    ParameterSlotAxis(
                        axis_name=str(
                            candidate.get("source_dimension_label") or "scenario_dimension",
                        ),
                        axis_value=str(candidate.get("source_dimension_value") or ""),
                    ),
                ],
            )
            for candidate in candidates
        ],
    )


def _fallback_value_response(
    reason: str,
    candidates: list[dict[str, Any]],
    slots: list[dict[str, Any]],
) -> LLMValueProposalResponse:
    slots_by_key = {str(slot["candidate_key"]): slot for slot in slots if "candidate_key" in slot}
    return LLMValueProposalResponse(
        parameter_adjustments=[
            ParameterAdjustment(
                candidate_key=str(candidate["candidate_key"]),
                model_file=str(candidate.get("model_file") or ""),
                model_sheet=str(candidate.get("model_sheet") or ""),
                parameter_name=str(
                    candidate.get("canonical_parameter_name")
                    or candidate.get("parameter_name")
                    or "",
                ),
                selected=True,
                slot_axes=[
                    ParameterSlotAxis.model_validate(axis)
                    for axis in (
                        slots_by_key.get(str(candidate["candidate_key"]), {}).get("slot_axes")
                        or []
                    )
                ],
                value_grid=[
                    ParameterValueCell(
                        coordinates={},
                        basecase_value=None,
                        proposed_value=None,
                        rationale_ko=reason,
                    ),
                ],
                parameter_selection_rationale_ko=reason,
            )
            for candidate in candidates
        ],
    )


def _unselected_adjustments_for_missing_slots(
    candidates: list[dict[str, Any]],
    reason: str,
) -> list[dict[str, Any]]:
    return [
        ParameterAdjustment(
            candidate_key=str(candidate["candidate_key"]),
            model_file=str(candidate.get("model_file") or ""),
            model_sheet=str(candidate.get("model_sheet") or ""),
            parameter_name=str(
                candidate.get("canonical_parameter_name")
                or candidate.get("parameter_name")
                or "",
            ),
            selected=False,
            slot_axes=[],
            value_grid=[],
            parameter_selection_rationale_ko=reason,
        ).model_dump()
        for candidate in candidates
    ]
