-- =========================================================
-- Initialize tmm_mi_event_type_l1_m
-- =========================================================

INSERT INTO `tmm_mi_event_type_l1_m` (
    `level_1_code`,
    `level_1_label`,
    `crt_usr_logn_id`,
    `mod_usr_logn_id`,
    `del_yn`
) VALUES
('supply',              '공급',           'system', 'system', 'N'),
('demand',              '수요',           'system', 'system', 'N'),
('inventory_logistics', '재고/운송/시장', 'system', 'system', 'N'),
('exogenous_shock',     '외생충격',       'system', 'system', 'N')
ON DUPLICATE KEY UPDATE
    `level_1_label`   = VALUES(`level_1_label`),
    `mod_usr_logn_id` = VALUES(`mod_usr_logn_id`),
    `del_yn`          = VALUES(`del_yn`),
    `mod_dtm`         = CURRENT_TIMESTAMP(6);

-- =========================================================
-- Initialize tmm_mi_event_type_l2_m
-- =========================================================

INSERT INTO `tmm_mi_event_type_l2_m` (
    `event_type_l1_id`,
    `level_2_code`,
    `level_2_label`,
    `crt_usr_logn_id`,
    `mod_usr_logn_id`,
    `del_yn`
)
SELECT
    l1.event_type_l1_id,
    v.level_2_code,
    v.level_2_label,
    'system',
    'system',
    'N'
FROM (
    -- 공급
    SELECT 'supply' AS level_1_code, 'upstream_utilization_change'     AS level_2_code, 'Upstream Utilization 변동'        AS level_2_label
    UNION ALL SELECT 'supply', 'terminal_utilization_change',                            '터미널 Utilization 변동'
    UNION ALL SELECT 'supply', 'new_terminal_cod_rampup_change',                         '신규 터미널 COD 및 Ramp-up 계획 변경'
    UNION ALL SELECT 'supply', 'pipeline_utilization_change',                            '파이프라인 Utilization 변동'

    -- 수요
    UNION ALL SELECT 'demand', 'power_plant_utilization_change',                         '발전소 Utilization 변동'
    UNION ALL SELECT 'demand', 'winter_cold_wave',                                       '겨울 한파'
    UNION ALL SELECT 'demand', 'summer_heat_wave',                                       '여름 폭염'
    UNION ALL SELECT 'demand', 'nuclear_power',                                          '원자력 발전'
    UNION ALL SELECT 'demand', 'renewable_energy',                                       '재생에너지'
    UNION ALL SELECT 'demand', 'coal_power',                                             '석탄 발전'
    UNION ALL SELECT 'demand', 'natural_disaster',                                       '자연재해'

    -- 재고/운송/시장
    UNION ALL SELECT 'inventory_logistics', 'inventory_level',                           '재고 수준'
    UNION ALL SELECT 'inventory_logistics', 'ocean_freight',                             '해상 운임'
    UNION ALL SELECT 'inventory_logistics', 'supply_chain_cargo_flow',                   '공급망 및 화물 흐름'
    UNION ALL SELECT 'inventory_logistics', 'transaction_hedging',                       '거래 및 헷징'
    UNION ALL SELECT 'inventory_logistics', 'index_spread',                              '인덱스 Spread'

    -- 외생충격
    UNION ALL SELECT 'exogenous_shock', 'geopolitical_tension_war',                      '지정학적 긴장 및 전쟁·군사분쟁'
    UNION ALL SELECT 'exogenous_shock', 'economic_sanctions_trade_restrictions',          '경제 제재 및 무역 제한'
    UNION ALL SELECT 'exogenous_shock', 'policy_regulatory_change',                      '정책/규제 변화'
    UNION ALL SELECT 'exogenous_shock', 'interest_rate_fx',                              '금리 및 통화'
    UNION ALL SELECT 'exogenous_shock', 'country_economic_condition',                    '국가별 경기'
) v
JOIN `tmm_mi_event_type_l1_m` l1
  ON l1.level_1_code = v.level_1_code
 AND l1.del_yn = 'N'
ON DUPLICATE KEY UPDATE
    `level_2_label`   = VALUES(`level_2_label`),
    `mod_usr_logn_id` = VALUES(`mod_usr_logn_id`),
    `del_yn`          = VALUES(`del_yn`),
    `mod_dtm`         = CURRENT_TIMESTAMP(6);


-- =========================================================
-- Driver Tree Master 시드 (tmd_drivertreem)
-- =========================================================
INSERT INTO `tmd_drivertreem`
  (`lv1_id`, `lv2_id`, `lv3_id`, `lv1_label_ko`, `lv2_label_ko`, `lv3_label_ko`, `lv1_label_en`, `lv2_label_en`, `lv3_label_en`, `direction_hint`, `crt_user_id`, `mod_user_id`, `del_yn`)
VALUES
  ('country_lng_supply',      'existing_infra_supply',          'supply_gasfield_capa',                '국가별 LNG 공급량', '기존 인프라 공급량',    '가스전 생산 Capa',                'Country LNG Supply',      'Existing Infra Supply',           'Gasfield Production Capa',          'bearish_if_up',  'SYSTEM', 'SYSTEM', 'N'),
  ('country_lng_supply',      'existing_infra_supply',          'supply_gasfield_utilization',         '국가별 LNG 공급량', '기존 인프라 공급량',    '가스전 가동률',                   'Country LNG Supply',      'Existing Infra Supply',           'Gasfield Utilization Rate',         'bearish_if_up',  'SYSTEM', 'SYSTEM', 'N'),
  ('country_lng_supply',      'existing_infra_supply',          'supply_liquefaction_rate',            '국가별 LNG 공급량', '기존 인프라 공급량',    'Liquefaction rate',               'Country LNG Supply',      'Existing Infra Supply',           'Liquefaction Rate',                 'bearish_if_up',  'SYSTEM', 'SYSTEM', 'N'),
  ('country_lng_supply',      'existing_infra_supply',          'supply_spot_sales_share',             '국가별 LNG 공급량', '기존 인프라 공급량',    'Spot 판매 비중(공급)',             'Country LNG Supply',      'Existing Infra Supply',           'Spot Sales Share (Supply)',          'contextual',     'SYSTEM', 'SYSTEM', 'N'),
  ('country_lng_supply',      'new_project_supply',             'new_project_total_capa',              '국가별 LNG 공급량', '신규 프로젝트 공급량',  '프로젝트 LNG 총 Capa.',           'Country LNG Supply',      'New Project Supply',               'New Project Total Capa',            'bearish_if_up',  'SYSTEM', 'SYSTEM', 'N'),
  ('country_lng_supply',      'new_project_supply',             'new_project_startup_schedule',        '국가별 LNG 공급량', '신규 프로젝트 공급량',  '프로젝트 시점별 공급 계획',       'Country LNG Supply',      'New Project Supply',               'Project Startup Schedule',          'contextual',     'SYSTEM', 'SYSTEM', 'N'),
  ('country_lng_supply',      'new_project_supply',             'new_project_ramp_pattern',            '국가별 LNG 공급량', '신규 프로젝트 공급량',  '초기 가동률(램프업)',              'Country LNG Supply',      'New Project Supply',               'Initial Utilization (Ramp-up)',     'contextual',     'SYSTEM', 'SYSTEM', 'N'),
  ('country_lng_supply',      'new_project_supply',             'new_project_spot_sales_share',        '국가별 LNG 공급량', '신규 프로젝트 공급량',  'Spot 판매 비중(신규)',             'Country LNG Supply',      'New Project Supply',               'Spot Sales Share (New)',             'contextual',     'SYSTEM', 'SYSTEM', 'N'),
  ('country_lng_demand',      'power_demand',                   'demand_power_total_load',             '국가별 LNG 수요량', '발전 수요',             '총 발전 수요',                    'Country LNG Demand',      'Power Demand',                    'Total Power Load',                  'bullish_if_up',  'SYSTEM', 'SYSTEM', 'N'),
  ('country_lng_demand',      'power_demand',                   'demand_power_lng_share',              '국가별 LNG 수요량', '발전 수요',             'LNG 활용 비중(발전)',              'Country LNG Demand',      'Power Demand',                    'LNG Share in Power',                'bullish_if_up',  'SYSTEM', 'SYSTEM', 'N'),
  ('country_lng_demand',      'heating_cooling_demand',         'demand_heating_total',                '국가별 LNG 수요량', '냉/난방 수요',          '총 냉/난방 수요',                 'Country LNG Demand',      'Heating/Cooling Demand',          'Total Heating/Cooling Demand',      'bullish_if_up',  'SYSTEM', 'SYSTEM', 'N'),
  ('country_lng_demand',      'heating_cooling_demand',         'demand_heating_lng_share',            '국가별 LNG 수요량', '냉/난방 수요',          'LNG 활용 비중(냉난방)',            'Country LNG Demand',      'Heating/Cooling Demand',          'LNG Share in Heating/Cooling',      'bullish_if_up',  'SYSTEM', 'SYSTEM', 'N'),
  ('country_lng_demand',      'industrial_demand',              'demand_industrial_total',             '국가별 LNG 수요량', '산업용 수요',           '산업 업종별 LNG 수요',            'Country LNG Demand',      'Industrial Demand',               'Industrial LNG Demand by Sector',   'bullish_if_up',  'SYSTEM', 'SYSTEM', 'N'),
  ('country_lng_demand',      'industrial_demand',              'demand_industrial_lng_share',         '국가별 LNG 수요량', '산업용 수요',           'LNG 활용 비중(산업)',              'Country LNG Demand',      'Industrial Demand',               'LNG Share in Industry',             'bullish_if_up',  'SYSTEM', 'SYSTEM', 'N'),
  ('country_lng_demand',      'other_demand',                   'demand_other_lng',                    '국가별 LNG 수요량', '기타(수송용 등)',        '기타 LNG 수요',                   'Country LNG Demand',      'Other Demand (Transport, etc.)',   'Other LNG Demand',                  'bullish_if_up',  'SYSTEM', 'SYSTEM', 'N'),
  ('country_lng_inventory',   'terminal_total_capa',            'inventory_terminal_total_capa',       '국가별 LNG 재고량', '터미널별 총 Capa',      '터미널별 총 Capa',                'Country LNG Inventory',   'Terminal Total Capa',             'Terminal Total Capacity',           'bearish_if_up',  'SYSTEM', 'SYSTEM', 'N'),
  ('country_lng_inventory',   'terminal_utilization',           'inventory_strategic_storage',         '국가별 LNG 재고량', '터미널별 적재율',       '전략적 비축량',                   'Country LNG Inventory',   'Terminal Utilization',            'Strategic Storage',                 'bullish_if_up',  'SYSTEM', 'SYSTEM', 'N'),
  ('country_lng_inventory',   'terminal_utilization',           'inventory_industrial_storage',        '국가별 LNG 재고량', '터미널별 적재율',       '산업용 비축량',                   'Country LNG Inventory',   'Terminal Utilization',            'Industrial Storage',                'contextual',     'SYSTEM', 'SYSTEM', 'N'),
  ('interregional_transport', 'shipping_availability',          'transport_vessel_availability',       '지역 간 운송',      '선박 가용성/운임',      '선박 가용성',                     'Interregional Transport',  'Shipping Availability/Freight',   'Vessel Availability',               'bearish_if_up',  'SYSTEM', 'SYSTEM', 'N'),
  ('interregional_transport', 'shipping_availability',          'transport_shipping_cost',             '지역 간 운송',      '선박 가용성/운임',      '운임/용선료',                     'Interregional Transport',  'Shipping Availability/Freight',   'Shipping Cost / Charter Rate',      'bullish_if_up',  'SYSTEM', 'SYSTEM', 'N'),
  ('interregional_transport', 'transit_time',                   'transport_route_distance_time',       '지역 간 운송',      '운송 시간',             '항로 거리/운하 소요시간',         'Interregional Transport',  'Transit Time',                    'Route Distance / Canal Transit',    'bullish_if_up',  'SYSTEM', 'SYSTEM', 'N'),
  ('interregional_transport', 'transit_time',                   'transport_port_congestion',           '지역 간 운송',      '운송 시간',             '항만 혼잡/대기시간',              'Interregional Transport',  'Transit Time',                    'Port Congestion / Waiting Time',    'bullish_if_up',  'SYSTEM', 'SYSTEM', 'N'),
  ('market_player_dynamics',  'actual_trade_activity',          'market_spot_activity',                '시장/Player 동향',  '실제 거래 활동',        '현물 거래 활동',                  'Market/Player Dynamics',   'Actual Trade Activity',           'Spot Market Activity',              'contextual',     'SYSTEM', 'SYSTEM', 'N'),
  ('market_player_dynamics',  'actual_trade_activity',          'market_emergency_procurement',        '시장/Player 동향',  '실제 거래 활동',        '긴급 조달 거래 발생 여부',        'Market/Player Dynamics',   'Actual Trade Activity',           'Emergency Procurement',             'bullish_if_up',  'SYSTEM', 'SYSTEM', 'N'),
  ('market_player_dynamics',  'position_constraint_behavior',   'market_inventory_limit_access',       '시장/Player 동향',  '포지션/제약 기반 행동', '재고 한계 접근',                  'Market/Player Dynamics',   'Position/Constraint Behavior',    'Inventory Limit Access',            'bullish_if_up',  'SYSTEM', 'SYSTEM', 'N'),
  ('market_player_dynamics',  'position_constraint_behavior',   'market_position_adjust_pressure',     '시장/Player 동향',  '포지션/제약 기반 행동', '포지션 조정 압력',                'Market/Player Dynamics',   'Position/Constraint Behavior',    'Position Adjustment Pressure',      'contextual',     'SYSTEM', 'SYSTEM', 'N'),
  ('market_player_dynamics',  'expectation_formation',          'market_expectation_narrative_shift',  '시장/Player 동향',  '기대 형성',             '시장 내 Bull/Bear 내러티브 변화', 'Market/Player Dynamics',   'Expectation Formation',           'Bull/Bear Narrative Shift',         'contextual',     'SYSTEM', 'SYSTEM', 'N'),
  ('market_player_dynamics',  'expectation_formation',          'market_major_player_action',          '시장/Player 동향',  '기대 형성',             'Major 플레이어 행동',             'Market/Player Dynamics',   'Expectation Formation',           'Major Player Action',               'contextual',     'SYSTEM', 'SYSTEM', 'N')
ON DUPLICATE KEY UPDATE
    `lv1_label_ko` = VALUES(`lv1_label_ko`),
    `lv2_label_ko` = VALUES(`lv2_label_ko`),
    `lv3_label_ko` = VALUES(`lv3_label_ko`),
    `lv1_label_en` = VALUES(`lv1_label_en`),
    `lv2_label_en` = VALUES(`lv2_label_en`),
    `lv3_label_en` = VALUES(`lv3_label_en`),
    `direction_hint` = VALUES(`direction_hint`),
    `mod_user_id` = VALUES(`mod_user_id`),
    `del_yn` = VALUES(`del_yn`),
    `mod_dtm` = NOW();