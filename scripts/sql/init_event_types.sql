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
('geopolitical_risk',       '지정학적 리스크',   'system', 'system', 'N'),
('weather_climate',         '기상 / 기후',       'system', 'system', 'N'),
('infrastructure_facility', '인프라 / 설비',     'system', 'system', 'N'),
('supply_demand_balance',   '수급 밸런스',       'system', 'system', 'N'),
('logistics_shipping',      '물류 / 해운',       'system', 'system', 'N'),
('energy_mix_transition',   '에너지 믹스 전환',  'system', 'system', 'N'),
('macroeconomy_policy',     '거시경제 / 정책',   'system', 'system', 'N'),
('market_trading_structure','시장 / 거래 구조',  'system', 'system', 'N')
ON DUPLICATE KEY UPDATE
    `level_1_label` = VALUES(`level_1_label`),
    `mod_usr_logn_id` = VALUES(`mod_usr_logn_id`),
    `del_yn` = VALUES(`del_yn`),
    `mod_dtm` = CURRENT_TIMESTAMP(6);

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
    SELECT 'geopolitical_risk' AS level_1_code, 'geopolitical_tension_instability' AS level_2_code, '지정학적 긴장 / 불안정' AS level_2_label
    UNION ALL SELECT 'geopolitical_risk', 'economic_sanctions_trade_restrictions', '경제 제재 / 무역 제한'
    UNION ALL SELECT 'geopolitical_risk', 'regime_change_political_transition', '정권 교체 / 정치 전환'
    UNION ALL SELECT 'geopolitical_risk', 'war_military_conflict', '전쟁 / 군사 분쟁'
    UNION ALL SELECT 'weather_climate', 'winter_cold_wave', '겨울 한파'
    UNION ALL SELECT 'weather_climate', 'summer_heat_wave', '여름 고온'
    UNION ALL SELECT 'weather_climate', 'natural_disaster', '자연재해'
    UNION ALL SELECT 'infrastructure_facility', 'upstream_production_facility_capacity_utilization_change', '상류 생산 시설 Capa / 가동률 변화'
    UNION ALL SELECT 'infrastructure_facility', 'liquefaction_terminal_facility_capacity_utilization_change', '액화 / 터미널 시설 Capa / 가동률 변화'
    UNION ALL SELECT 'infrastructure_facility', 'pipeline_transport_infrastructure_capacity_utilization_change', '파이프라인 / 수송 인프라 Capa / 가동률 변화'
    UNION ALL SELECT 'infrastructure_facility', 'power_plant_facility_capacity_utilization_change', '발전소 (원전, 화력) 설비 Capa / 가동률 변화'
    UNION ALL SELECT 'supply_demand_balance', 'inventory_storage_level', '재고 / 저장 수준'
    UNION ALL SELECT 'supply_demand_balance', 'regional_demand_competition', '지역간 수요 경쟁 (유럽 vs. 아시아)'
    UNION ALL SELECT 'logistics_shipping', 'ocean_freight_charter_rate_change', '해상 운임 / 용선료 변동'
    UNION ALL SELECT 'logistics_shipping', 'cargo_flow_change_port_canal_disruption', '화물 흐름 변화 / 항만·운하 차질'
    UNION ALL SELECT 'energy_mix_transition', 'nuclear_power_expansion_reduction', '원자력 발전 확대 / 축소'
    UNION ALL SELECT 'energy_mix_transition', 'renewable_power_expansion_reduction', '재생에너지 발전 확대 / 축소'
    UNION ALL SELECT 'energy_mix_transition', 'alternative_fuel_availability', '대체 연료 가용성'
    UNION ALL SELECT 'macroeconomy_policy', 'interest_rate_fx_policy_change', '금리 / 통화정책 변화'
    UNION ALL SELECT 'macroeconomy_policy', 'country_economic_condition_change', '국가별 경기 변화'
    UNION ALL SELECT 'market_trading_structure', 'transaction_hedging_cost_change', '거래 / 헷징 비용 변동'
    UNION ALL SELECT 'market_trading_structure', 'inter_index_spread_gap', '인덱스별 스프레드 Gap'
) v
JOIN `tmm_mi_event_type_l1_m` l1
  ON l1.level_1_code = v.level_1_code
 AND l1.del_yn = 'N'
ON DUPLICATE KEY UPDATE
    `level_2_label` = VALUES(`level_2_label`),
    `mod_usr_logn_id` = VALUES(`mod_usr_logn_id`),
    `del_yn` = VALUES(`del_yn`),
    `mod_dtm` = CURRENT_TIMESTAMP(6);