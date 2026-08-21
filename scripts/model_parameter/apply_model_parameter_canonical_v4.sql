-- Copyright (c) 2026 SK Innovation E&S.
-- Canonical versions: model-parameter-canonical-v4 + model-impact-lever-canonical-v4
-- Source evidence: snapshots/external_dev_before_model_parameter_v4_20260813.json
--
-- This MySQL 8.0 procedure updates the 21-row Model Parameter master and the
-- 16-row Impact Lever catalog in one transaction. The 128-row AS-IS
-- legacy dimension mapping is locked and verified exactly but is never updated.

DELIMITER //

DROP PROCEDURE IF EXISTS apply_model_parameter_canonical_v4//
CREATE PROCEDURE apply_model_parameter_canonical_v4()
BEGIN
    DECLARE v_bad BIGINT DEFAULT 0;
    DECLARE v_count BIGINT DEFAULT 0;
    DECLARE v_checksum CHAR(64) DEFAULT NULL;
    DECLARE v_expected_checksum CHAR(64) DEFAULT NULL;

    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        DROP TEMPORARY TABLE IF EXISTS _mpv4_snapshot_master;
        DROP TEMPORARY TABLE IF EXISTS _mpv4_canonical_master;
        DROP TEMPORARY TABLE IF EXISTS _mpv4_snapshot_mapping;
        DROP TEMPORARY TABLE IF EXISTS _mpv4_snapshot_lever;
        DROP TEMPORARY TABLE IF EXISTS _mpv4_canonical_lever;
        RESIGNAL;
    END;

    START TRANSACTION;

    SELECT model_param_id
      FROM tmm_mi_model_param_m
     ORDER BY model_param_id
       FOR UPDATE;

    SELECT model_param_dimension_map_id
      FROM tmm_mi_model_param_dimension_map
     ORDER BY model_param_dimension_map_id
       FOR SHARE;

    SELECT impact_lever_id
      FROM tmm_mi_model_impact_lever_m
     ORDER BY impact_lever_id
       FOR UPDATE;

    SELECT scenario_dimension_template_id
      FROM tmm_mi_scenario_dimension_template_m
     ORDER BY scenario_dimension_template_id
       FOR SHARE;

    CREATE TEMPORARY TABLE _mpv4_snapshot_master AS
    SELECT `model_param_id`, `use_yn`, `parameter_name`, `parameter_hint`, `model_file`, `model_sheet`, `model_table`, `semantic_axes`, `basecase_read_mode`, `basecase_header_row`, `basecase_data_start_row`, `basecase_column_roles`, `basecase_row_filter`, `basecase_year_row`, `basecase_month_row`, `basecase_period_row`, `basecase_value_start_col`, `basecase_value_end_col`, `basecase_stop_rule`, `mod_usr_logn_id`, `del_yn`, `crt_usr_logn_id`, `crt_dtm`
      FROM tmm_mi_model_param_m
     WHERE 1 = 0;

    INSERT INTO _mpv4_snapshot_master (
        `model_param_id`, `use_yn`, `parameter_name`, `parameter_hint`, `model_file`, `model_sheet`, `model_table`, `semantic_axes`, `basecase_read_mode`, `basecase_header_row`, `basecase_data_start_row`, `basecase_column_roles`, `basecase_row_filter`, `basecase_year_row`, `basecase_month_row`, `basecase_period_row`, `basecase_value_start_col`, `basecase_value_end_col`, `basecase_stop_rule`, `mod_usr_logn_id`, `del_yn`, `crt_usr_logn_id`, `crt_dtm`
    ) VALUES
        (1, 'N', 'CDD', 'Country/year-month CDD value (degree-day)', 'Demand', 'WeatherAdjustment', 'table1', '평년 대비 기온편차 변환 — 국가·연·월', 'fixed_columns', 6, 12, 'B:Year,C:Month,D:Country,E:HDD/CDD,G:HDD/CDD', 'E=CDD', NULL, NULL, NULL, NULL, NULL, 'stop_when_all_key_columns_empty', 'system', 'N', 'system', '2026-07-06T11:14:02.203729'),
        (2, 'N', 'Coal Futures Price', 'Monthly coal futures price by region (USD/t)', 'Demand', 'CoalGasAdjustment', 'table1', '석탄 선물가격 strip — 지역·월 (Asia=Newcastle, EU=ARA)', 'fixed_columns', 6, 12, 'B:Month-Year,C:Region,E:Coal Futures Price (USD/t)', NULL, NULL, NULL, NULL, NULL, NULL, 'stop_when_all_key_columns_empty', 'system', 'N', 'system', '2026-07-06T11:14:02.203729'),
        (3, 'N', 'Gas Futures Price', 'Monthly gas futures price by region (USD/mmbtu)', 'Demand', 'CoalGasAdjustment', 'table2', '가스 선물가격 strip — 지역·월 (Asia=JKM, EU=TTF)', 'fixed_columns', 6, 12, 'H:Month-Year,I:Region,K:Gas Futures Price (USD/mmbtu)', NULL, NULL, NULL, NULL, NULL, NULL, 'stop_when_all_key_columns_empty', 'system', 'N', 'system', '2026-07-06T11:14:02.203729'),
        (4, 'Y', 'GDP', '국가·연도별 실질 GDP 전년 대비 성장률의 최종 입력값이다. value는 % change를 소수로 입력한다(0.042=4.2%, -0.015=-1.5%). proposedValue는 basecase 대비 증감폭이 아니라 해당 Country/Year에 적용할 성장률 자체다. basecase가 있으면 기존 성장률과 이벤트에 명시된 GDP 전망·조정폭을 비교해 최종 성장률로 제안한다.', 'Demand', 'GDPPopulationAdjustment', 'table1', 'slot=B:Year(YYYY, 2026~2030), C:Country(국가명; basecase 예: United States, China, Japan, South Korea, Taiwan (China), Belgium, France, Germany, Italy, Netherlands, Spain, India); value=F:% change(+/-), 소수형 전년대비 실질 GDP 성장률', 'fixed_columns', 6, 12, 'B:Year,C:Country,F:% change (+/-)', NULL, NULL, NULL, NULL, NULL, NULL, 'stop_when_all_key_columns_empty', 'system', 'N', 'system', '2026-07-06T11:14:02.203729'),
        (5, 'N', 'HDD', 'Country/year-month HDD value (degree-day)', 'Demand', 'WeatherAdjustment', 'table1', '평년 대비 기온편차 변환 — 국가·연·월', 'fixed_columns', 6, 12, 'B:Year,C:Month,D:Country,E:HDD/CDD,G:HDD/CDD', 'E=HDD', NULL, NULL, NULL, NULL, NULL, 'stop_when_all_key_columns_empty', 'system', 'N', 'system', '2026-07-06T11:14:02.203729'),
        (6, 'Y', 'PMI', '국가·연월별 PMI 지수의 최종 입력값이다. value는 PMI index 절대값으로 입력한다(예: 49.5). PMI 기준값은 보통 50이며, 50 초과는 경기 확장/생산활동 증가, 50은 중립, 50 미만은 경기 위축/생산활동 감소를 의미한다. 이 모델에서 PMI는 주로 industrial demand, 즉 산업용 가스 수요를 조정하는 경기 민감도 변수다. proposedValue는 basecase 대비 증감폭이 아니라 해당 Country/Year/Month에 적용할 PMI 값 자체다.', 'Demand', 'PMIAdjustment', 'table1', 'slot=B:Year(YYYY, 2026~2030), C:Month(1~12), D:Country(국가명; basecase 예: China, Philippines); value=F:PMI, PMI index 절대값', 'fixed_columns', 6, 13, 'B:Year,C:Month,D:Country,F:PMI', NULL, NULL, NULL, NULL, NULL, NULL, 'stop_when_all_key_columns_empty', 'system', 'N', 'system', '2026-07-06T11:14:02.203729'),
        (7, 'Y', 'PowerMix', '국가·연도·에너지원별 발전 믹스 비중의 최종 입력값이다. value는 전체 발전량에서 해당 Energy Source가 차지하는 비중을 소수로 입력한다(0.30=30%). proposedValue는 basecase 대비 증감폭이 아니라 해당 Country/Year/Energy Source에 적용할 최종 비중이다. 현재 basecase는 Gas 위주로 제공되므로, 명확한 전원별 사유가 없으면 Gas 비중 조정을 우선 검토하고 상쇄 전원은 rationale에 설명한다.', 'Demand', 'PowerMixAdjustment', 'table1', 'slot=B:Year(YYYY, 2026~2030), C:Country(국가명; basecase 예: China, Japan, South Korea, Taiwan (China), Germany, France, Italy, Spain, Netherlands, Belgium, United Kingdom), D:Energy Source(Liquids/Hydro/Solar/Wind/Bioenergy/Gas/Coal/Nuclear/Geothermal/Other; basecase 예: Gas); value=F:% Power Mix, 소수형 발전 비중', 'fixed_columns', 6, 12, 'B:Year,C:Country,D:Energy Source,F:% Power Mix', NULL, NULL, NULL, NULL, NULL, NULL, 'stop_when_all_key_columns_empty', 'system', 'N', 'system', '2026-07-06T11:14:02.203729'),
        (8, 'Y', 'Temperature', '국가·연월별 평균 기온의 최종 입력값이다. value는 섭씨(°C) 절대값으로 입력한다(예: 2.3, -1.5, 31.0). proposedValue는 basecase 대비 편차가 아니라 해당 Country/Year/Month에 적용할 기온 자체다. 한파는 정상 기온 대비 하향, 폭염은 정상 기온 대비 상향 방향으로 조정한다. 국가별 기후 차이가 크므로 basecase가 없는 경우 다른 국가의 기온 수준을 기준값으로 삼지 않는다.', 'Demand', 'WeatherAdjustment', 'table2', 'slot=K:Year(YYYY, 2026~2030), L:Month(1~12; basecase 예: 1~3), M:Country(국가명; basecase 예: China, Japan, South Korea, Germany, France, Netherlands, Spain, Italy, Belgium, United Kingdom); value=O:Temperature (°C), 섭씨 절대 기온', 'fixed_columns', 6, 12, 'K:Year,L:Month,M:Country,O:Temperature (°C)', NULL, NULL, NULL, NULL, NULL, NULL, 'stop_when_all_key_columns_empty', 'system', 'N', 'system', '2026-07-06T11:14:02.203729'),
        (9, 'N', 'User-Adjusted Gas Demand', 'Country/year-month/sub-sector demand overwrite value (BCM)', 'Demand', 'DemandOutputOverwrite', 'table1', '수요 출력 직접 덮어쓰기 — 국가·연·월·Sub-Sector', 'fixed_columns', 7, 8, 'D:Country,E:Year,F:Month,G:Demand Sub-Sector,H:User-Adjusted Gas Demand [BCM]', NULL, NULL, NULL, NULL, NULL, NULL, 'stop_when_all_key_columns_empty', 'system', 'N', 'system', '2026-07-06T11:14:02.203729'),
        (10, 'N', 'ElectrificationRate', 'Country/year transportation electrification rate (% new car sales)', 'Demand', 'ElectrificationRateAdjustment', 'table1', '수송 전기화율 (본 21종 직접 해당 적음)', 'fixed_columns', 6, 12, 'B:Year,C:Country,D:Drive Train,F:% New Car Sales', NULL, NULL, NULL, NULL, NULL, NULL, 'stop_when_all_key_columns_empty', 'system', 'N', 'system', '2026-07-06T11:14:02.203729'),
        (11, 'N', 'Population', 'Country/year population value (thousands)', 'Demand', 'GDPPopulationAdjustment', 'table2', '인구 — 국가·연', 'fixed_columns', 6, 12, 'J:Year,K:Country,M:Population (Thousands)', NULL, NULL, NULL, NULL, NULL, NULL, 'stop_when_all_key_columns_empty', 'system', 'N', 'system', '2026-07-06T11:14:02.203729'),
        (12, 'N', 'HurricaneIntensity', 'US hurricane intensity integer (1-4; blank or 0 means no impact)', 'Supply', '{USA}Hurricanes', 'table1', '美 액화시설 허리케인 차질 — 연·월', 'fixed_columns', 7, 13, 'B:Year,C:Month,D:Hurricane intensity', NULL, NULL, NULL, NULL, NULL, NULL, 'stop_when_all_key_columns_empty', 'system', 'N', 'system', '2026-07-06T11:14:02.203729'),
        (13, 'N', 'LiqProdAdjustment', 'Train/month LNG production absolute value (Mt LNG/month; >= 0)', 'Supply', 'LiqProdAdjustment', 'table1', '액화시설 생산량 override — Country>Plant>Train·연·월', 'matrix_time_columns', 10, 11, 'B:Country,C:LNG Plant,D:LNG Plant Train,E:Life Cycle Category,F:Nameplate Capacity (MTPA)', NULL, 7, 8, 9, 'G', 'DA', 'stop_when_all_key_columns_empty', 'system', 'N', 'system', '2026-07-06T11:14:02.203729'),
        (14, 'Y', 'LiqUtilAdjustment', '액화 Plant Train·월별 가동률의 최종 입력값이다. value는 0~1 소수로 입력한다(1.0=100%, 0.7=70%). 100 같은 percent 표기는 사용하지 않는다. proposedValue는 basecase 대비 증감폭이 아니라 해당 Train/Year/Month에 적용할 가동률 자체다. 기본 범위는 0~1이며, 1 초과는 명확한 근거가 있을 때만 제안한다. Base Case에 존재하는 LNG Plant Train만 수정하고, Country/LNG Plant/Life Cycle Category/Nameplate Capacity는 해당 Train에 종속된 식별 속성으로 맞춘다.', 'Supply', 'LiqUtilAdjustment', 'table1', 'slot=Country(국가명; 예: Algeria, Angola), LNG Plant(예: Arzew GL1Z, Angola LNG), LNG Plant Train(348개 basecase Train 중 선택; 예: Arzew GL1Z T1-T6, Angola LNG T1, Gorgon LNG T1, North West Shelf LNG T1, Sabine Pass LNG Stage 5 Expansion T1), Life Cycle Category(예: Operational), Nameplate Capacity MTPA(숫자; 예: 7.9, 5.2), Year(YYYY), Month(1~12), Period(숫자); value=Utilization Rate, 0~1 소수형 월별 가동률', 'matrix_time_columns', 10, 11, 'B:Country,C:LNG Plant,D:LNG Plant Train,E:Life Cycle Category,F:Nameplate Capacity (MTPA)', NULL, 7, 8, 9, 'G', 'DA', 'stop_when_all_key_columns_empty', 'system', 'N', 'system', '2026-07-06T11:14:02.203729'),
        (15, 'N', 'PipelineAdjustment', 'Pipeline/year-month sendout capacity absolute value (Bcm/y; >= 0)', 'Supply', 'PipelineAdjustment', 'table1', 'PNG 송출 capa override — Pipeline·From·To·연·월', 'fixed_columns', 7, 13, 'B:Year,C:Month,D:Pipeline name,H:User adjusted capacity (Bcm/y)', NULL, NULL, NULL, NULL, NULL, NULL, 'stop_when_all_key_columns_empty', 'system', 'N', 'system', '2026-07-06T11:14:02.203729'),
        (16, 'N', 'RegasAdjustment', 'Regasification plant/month capacity absolute value (Mt LNG; >= 0)', 'Supply', 'RegasAdjustment', 'table1', '재기화(수입) 설비 capa override — Continent>Region>Country>Plant·연·월', 'matrix_time_columns', 10, 11, 'B:Continent,C:Region,D:Country,E:Regasification plant,F:Life Cycle Category,G:Nameplate capacity (MTPA)', NULL, 9, 10, NULL, 'H', 'DK', 'stop_when_all_key_columns_empty', 'system', 'N', 'system', '2026-07-06T11:14:02.203729'),
        (17, 'N', 'SupplyDisruption', 'Province/country/year supply volume absolute value (Bcm; >= 0)', 'Supply', 'VolumeAdjustment', 'table2', 'Upstream 공급량 override — Country·연·월', 'fixed_columns', 7, 8, 'I:Year,J:Month,K:Country,M:Volumes (Bcm)', NULL, NULL, NULL, NULL, NULL, NULL, 'stop_when_all_key_columns_empty', 'system', 'N', 'system', '2026-07-06T11:14:02.203729'),
        (18, 'N', 'PNG Contract Volume', 'From/to country/year PNG contract volume (BCM)', 'Trade', 'MidstreamContractInput', 'table1', 'PNG 계약 물량(Nord Stream 재가동·Pipeline Disruption) — From·To·연', 'fixed_columns', 4, 5, 'A:Year,B:From Country,C:To Country,D:Unadjusted Gross Gas Import [BCM]', NULL, NULL, NULL, NULL, NULL, NULL, 'stop_when_all_key_columns_empty', 'system', 'N', 'system', '2026-07-06T11:14:02.203729'),
        (19, 'N', 'RemainingUnrestrictedAmount', 'From/to country/year remaining unrestricted trade volume (BCM)', 'Trade', 'TradeRestrictionInput', 'table1', '계약 취소·통과 제약 — From·To·연', 'fixed_columns', 5, 6, 'B:Year,C:From Country,D:To Country,J:Remaining Unrestricted Amount [BCM]', NULL, NULL, NULL, NULL, NULL, NULL, 'stop_when_all_key_columns_empty', 'system', 'N', 'system', '2026-07-06T11:14:02.203729'),
        (20, 'N', 'ShippingCost', 'Yearly user input absolute shipping cost value ($/d)', 'Trade', 'ShippingCostInput', 'table1', 'Charter·Fuel·Suez/Panama Crossing 비용·Disruption 여부 — impact_scope·연', 'fixed_columns', 5, 6, 'B:Year,F:User Input Absolute Value ($/d)', NULL, NULL, NULL, NULL, NULL, NULL, 'stop_when_all_key_columns_empty', 'system', 'N', 'system', '2026-07-06T11:14:02.203729'),
        (21, 'N', 'VolumeCancelled', 'From/to country/year cancelled trade volume (BCM)', 'Trade', 'TradeRestrictionInput', 'table1', '계약 취소·통과 제약 — From·To·연', 'fixed_columns', 5, 6, 'B:Year,C:From Country,D:To Country,F:Volume [BCM]', NULL, NULL, NULL, NULL, NULL, NULL, 'stop_when_all_key_columns_empty', 'system', 'N', 'system', '2026-07-06T11:14:02.203729');

    CREATE TEMPORARY TABLE _mpv4_canonical_master AS
    SELECT * FROM _mpv4_snapshot_master WHERE 1 = 0;

    INSERT INTO _mpv4_canonical_master (
        `model_param_id`, `use_yn`, `parameter_name`, `parameter_hint`, `model_file`, `model_sheet`, `model_table`, `semantic_axes`, `basecase_read_mode`, `basecase_header_row`, `basecase_data_start_row`, `basecase_column_roles`, `basecase_row_filter`, `basecase_year_row`, `basecase_month_row`, `basecase_period_row`, `basecase_value_start_col`, `basecase_value_end_col`, `basecase_stop_rule`, `mod_usr_logn_id`, `del_yn`, `crt_usr_logn_id`, `crt_dtm`
    ) VALUES
        (1, 'N', 'CDD', 'Country/year-month CDD value (degree-day)', 'Demand', 'WeatherAdjustment', 'table1', '평년 대비 기온편차 변환 — 국가·연·월', 'fixed_columns', 6, 12, 'B:Year,C:Month,D:Country,E:HDD/CDD,G:HDD/CDD', 'E=CDD', NULL, NULL, NULL, NULL, NULL, 'stop_when_all_key_columns_empty', 'model-parameter-canonical-v4', 'N', 'system', '2026-07-06T11:14:02.203729'),
        (2, 'N', 'Coal Futures Price', 'Monthly coal futures price by region (USD/t)', 'Demand', 'CoalGasAdjustment', 'table1', '석탄 선물가격 strip — 지역·월 (Asia=Newcastle, EU=ARA)', 'fixed_columns', 6, 12, 'B:Month-Year,C:Region,E:Coal Futures Price (USD/t)', NULL, NULL, NULL, NULL, NULL, NULL, 'stop_when_all_key_columns_empty', 'model-parameter-canonical-v4', 'N', 'system', '2026-07-06T11:14:02.203729'),
        (3, 'N', 'Gas Futures Price', 'Monthly gas futures price by region (USD/mmbtu)', 'Demand', 'CoalGasAdjustment', 'table2', '가스 선물가격 strip — 지역·월 (Asia=JKM, EU=TTF)', 'fixed_columns', 6, 12, 'H:Month-Year,I:Region,K:Gas Futures Price (USD/mmbtu)', NULL, NULL, NULL, NULL, NULL, NULL, 'stop_when_all_key_columns_empty', 'model-parameter-canonical-v4', 'N', 'system', '2026-07-06T11:14:02.203729'),
        (4, 'Y', 'GDP', '국가·연도별 실질 GDP 전년 대비 성장률의 최종 입력값이다. value는 % change를 소수로 입력한다(0.042=4.2%, -0.015=-1.5%). proposedValue는 basecase 대비 증감폭이 아니라 해당 Country/Year에 적용할 성장률 자체다. basecase가 있으면 기존 성장률과 이벤트에 명시된 GDP 전망·조정폭을 비교해 최종 성장률로 제안한다.', 'Demand', 'GDPPopulationAdjustment', 'table1', 'slot=B:Year(YYYY, 2026~2030), C:Country(국가명; basecase 예: United States, China, Japan, South Korea, Taiwan (China), Belgium, France, Germany, Italy, Netherlands, Spain, India); value=F:% change(+/-), 소수형 전년대비 실질 GDP 성장률', 'fixed_columns', 6, 12, 'B:Year,C:Country,F:% change (+/-)', NULL, NULL, NULL, NULL, NULL, NULL, 'stop_when_all_key_columns_empty', 'model-parameter-canonical-v4', 'N', 'system', '2026-07-06T11:14:02.203729'),
        (5, 'N', 'HDD', 'Country/year-month HDD value (degree-day)', 'Demand', 'WeatherAdjustment', 'table1', '평년 대비 기온편차 변환 — 국가·연·월', 'fixed_columns', 6, 12, 'B:Year,C:Month,D:Country,E:HDD/CDD,G:HDD/CDD', 'E=HDD', NULL, NULL, NULL, NULL, NULL, 'stop_when_all_key_columns_empty', 'model-parameter-canonical-v4', 'N', 'system', '2026-07-06T11:14:02.203729'),
        (6, 'Y', 'PMI', '국가·연월별 PMI 지수의 최종 입력값이다. value는 PMI index 절대값으로 입력한다(예: 49.5). PMI 기준값은 보통 50이며, 50 초과는 경기 확장/생산활동 증가, 50은 중립, 50 미만은 경기 위축/생산활동 감소를 의미한다. 이 모델에서 PMI는 주로 industrial demand, 즉 산업용 가스 수요를 조정하는 경기 민감도 변수다. proposedValue는 basecase 대비 증감폭이 아니라 해당 Country/Year/Month에 적용할 PMI 값 자체다.', 'Demand', 'PMIAdjustment', 'table1', 'slot=B:Year(YYYY, 2026~2030), C:Month(1~12), D:Country(국가명; basecase 예: China, Philippines); value=F:PMI, PMI index 절대값', 'fixed_columns', 6, 13, 'B:Year,C:Month,D:Country,F:PMI', NULL, NULL, NULL, NULL, NULL, NULL, 'stop_when_all_key_columns_empty', 'model-parameter-canonical-v4', 'N', 'system', '2026-07-06T11:14:02.203729'),
        (7, 'Y', 'PowerMix', '국가·연도·에너지원별 발전 믹스 비중의 최종 입력값이다. value는 전체 발전량에서 해당 Energy Source가 차지하는 비중을 소수로 입력한다(0.30=30%). proposedValue는 basecase 대비 증감폭이 아니라 해당 Country/Year/Energy Source에 적용할 최종 비중이다. 현재 basecase는 Gas 위주로 제공되므로, 명확한 전원별 사유가 없으면 Gas 비중 조정을 우선 검토하고 상쇄 전원은 rationale에 설명한다.', 'Demand', 'PowerMixAdjustment', 'table1', 'slot=B:Year(YYYY, 2026~2030), C:Country(국가명; basecase 예: China, Japan, South Korea, Taiwan (China), Germany, France, Italy, Spain, Netherlands, Belgium, United Kingdom), D:Energy Source(Liquids/Hydro/Solar/Wind/Bioenergy/Gas/Coal/Nuclear/Geothermal/Other; basecase 예: Gas); value=F:% Power Mix, 소수형 발전 비중', 'fixed_columns', 6, 12, 'B:Year,C:Country,D:Energy Source,F:% Power Mix', NULL, NULL, NULL, NULL, NULL, NULL, 'stop_when_all_key_columns_empty', 'model-parameter-canonical-v4', 'N', 'system', '2026-07-06T11:14:02.203729'),
        (8, 'Y', 'Temperature', '국가·연월별 평균 기온의 최종 입력값이다. value는 섭씨(°C) 절대값으로 입력한다(예: 2.3, -1.5, 31.0). proposedValue는 basecase 대비 편차가 아니라 해당 Country/Year/Month에 적용할 기온 자체다. 한파는 정상 기온 대비 하향, 폭염은 정상 기온 대비 상향 방향으로 조정한다. 국가별 기후 차이가 크므로 basecase가 없는 경우 다른 국가의 기온 수준을 기준값으로 삼지 않는다.', 'Demand', 'WeatherAdjustment', 'table2', 'slot=K:Year(YYYY, 2026~2030), L:Month(1~12; basecase 예: 1~3), M:Country(국가명; basecase 예: China, Japan, South Korea, Germany, France, Netherlands, Spain, Italy, Belgium, United Kingdom); value=O:Temperature (°C), 섭씨 절대 기온', 'fixed_columns', 6, 12, 'K:Year,L:Month,M:Country,O:Temperature (°C)', NULL, NULL, NULL, NULL, NULL, NULL, 'stop_when_all_key_columns_empty', 'model-parameter-canonical-v4', 'N', 'system', '2026-07-06T11:14:02.203729'),
        (9, 'Y', 'User-Adjusted Gas Demand', '국가·연월·수요 하위부문별 가스 수요의 최종 절대값이다. value는 BCM 단위이며 0 이상이다. proposedValue는 basecase 대비 증감폭이 아니라 해당 Country/Year/Month/Demand Sub-Sector에 적용할 최종 수요량이다. 경제 활동이나 발전 믹스 파라미터로 설명되지 않는 직접 수요 정책·절감·연료 전환이 명시된 경우에 사용한다.', 'Demand', 'DemandOutputOverwrite', 'table1', 'slot=D:Country, E:Year(YYYY, 2026~2030), F:Month(1~12), G:Demand Sub-Sector; value=H:User-Adjusted Gas Demand [BCM], 직접 수요 절대값', 'fixed_columns', 7, 8, 'D:Country,E:Year,F:Month,G:Demand Sub-Sector,H:User-Adjusted Gas Demand [BCM]', NULL, NULL, NULL, NULL, NULL, NULL, 'stop_when_all_key_columns_empty', 'model-parameter-canonical-v4', 'N', 'system', '2026-07-06T11:14:02.203729'),
        (10, 'N', 'ElectrificationRate', 'Country/year transportation electrification rate (% new car sales)', 'Demand', 'ElectrificationRateAdjustment', 'table1', '수송 전기화율 (본 21종 직접 해당 적음)', 'fixed_columns', 6, 12, 'B:Year,C:Country,D:Drive Train,F:% New Car Sales', NULL, NULL, NULL, NULL, NULL, NULL, 'stop_when_all_key_columns_empty', 'model-parameter-canonical-v4', 'N', 'system', '2026-07-06T11:14:02.203729'),
        (11, 'Y', 'Population', '국가·연도별 인구의 최종 입력값이다. value는 천 명 단위 절대값으로 입력한다. proposedValue는 basecase 대비 증감폭이 아니라 해당 Country/Year에 적용할 인구 자체다. 인구·이민·인구전망 변화가 event에 명시된 경우에만 사용하고, 일반 경기 변화에는 GDP·PMI를 우선한다.', 'Demand', 'GDPPopulationAdjustment', 'table2', 'slot=J:Year(YYYY, 2026~2030), K:Country(국가명), value=M:Population (Thousands), 천 명 단위 인구 절대값', 'fixed_columns', 6, 12, 'J:Year,K:Country,M:Population (Thousands)', NULL, NULL, NULL, NULL, NULL, NULL, 'stop_when_all_key_columns_empty', 'model-parameter-canonical-v4', 'N', 'system', '2026-07-06T11:14:02.203729'),
        (12, 'Y', 'HurricaneIntensity', '미국 Gulf of Mexico 허리케인의 월별 강도 최종 입력값이다. value는 0~4 정수이며 0은 허리케인 영향 없음, 1~4는 승인된 강도 단계다. event가 GoM 허리케인과 적용 Year/Month를 명시하고 영향 대상 액화 또는 upstream 시설과 연결되는 경우에만 1~4를 제안한다.', 'Supply', '{USA}Hurricanes', 'table1', 'slot=B:Year(YYYY, 2026~2030), C:Month(1~12); value=D:Hurricane intensity(0~4 정수, 0=no hurricane)', 'fixed_columns', 7, 13, 'B:Year,C:Month,D:Hurricane intensity', NULL, NULL, NULL, NULL, NULL, NULL, 'stop_when_all_key_columns_empty', 'model-parameter-canonical-v4', 'N', 'system', '2026-07-06T11:14:02.203729'),
        (13, 'Y', 'LiqProdAdjustment', '액화 Plant Train·월별 LNG 생산량의 최종 절대값이다. value는 Mt LNG/month 단위이며 0 이상이다. LUT 기준값은 월 생산능력 × 이용률로 계산한다. proposedValue는 증감폭이 아니라 해당 Country/LNG Plant/LNG Plant Train/Year/Month의 최종 생산량이며, 대폭·영구 차질이나 신규 Train ramp-up처럼 생산량 직접 override가 필요한 경우에 사용한다.', 'Supply', 'LiqProdAdjustment', 'table1', 'slot=Country, LNG Plant, LNG Plant Train, Year(YYYY), Month(1~12); metadata=Life Cycle Category, Nameplate Capacity (MTPA), Period; value=Production (Mt LNG/month), 월 생산능력×이용률', 'matrix_time_columns', 10, 11, 'B:Country,C:LNG Plant,D:LNG Plant Train,E:Life Cycle Category,F:Nameplate Capacity (MTPA)', NULL, 7, 8, 9, 'G', 'DA', 'stop_when_all_key_columns_empty', 'model-parameter-canonical-v4', 'N', 'system', '2026-07-06T11:14:02.203729'),
        (14, 'Y', 'LiqUtilAdjustment', '액화 Plant Train·월별 가동률의 최종 입력값이다. value는 0~1 소수로 입력한다(1.0=100%, 0.7=70%). 100 같은 percent 표기는 사용하지 않는다. proposedValue는 basecase 대비 증감폭이 아니라 해당 Train/Year/Month에 적용할 가동률 자체다. 기본 범위는 0~1이며, 1 초과는 명확한 근거가 있을 때만 제안한다. Base Case에 존재하는 LNG Plant Train만 수정하고, Country/LNG Plant/Life Cycle Category/Nameplate Capacity는 해당 Train에 종속된 식별 속성으로 맞춘다.', 'Supply', 'LiqUtilAdjustment', 'table1', 'slot=Country(국가명; 예: Algeria, Angola), LNG Plant(예: Arzew GL1Z, Angola LNG), LNG Plant Train(348개 basecase Train 중 선택; 예: Arzew GL1Z T1-T6, Angola LNG T1, Gorgon LNG T1, North West Shelf LNG T1, Sabine Pass LNG Stage 5 Expansion T1), Life Cycle Category(예: Operational), Nameplate Capacity MTPA(숫자; 예: 7.9, 5.2), Year(YYYY), Month(1~12), Period(숫자); value=Utilization Rate, 0~1 소수형 월별 가동률', 'matrix_time_columns', 10, 11, 'B:Country,C:LNG Plant,D:LNG Plant Train,E:Life Cycle Category,F:Nameplate Capacity (MTPA)', NULL, 7, 8, 9, 'G', 'DA', 'stop_when_all_key_columns_empty', 'model-parameter-canonical-v4', 'N', 'system', '2026-07-06T11:14:02.203729'),
        (15, 'Y', 'PipelineAdjustment', '파이프라인·월별 송출능력의 최종 절대값이다. value는 Bcm/y 단위이며 0 이상이다. 연간 LUT capacity를 동일 연도의 12개월 기준값으로 확장한다. proposedValue는 증감폭이 아니라 해당 Pipeline Name/From Country/To Country/Year/Month에 적용할 최종 송출능력이다.', 'Supply', 'PipelineAdjustment', 'table1', 'slot=B:Year(YYYY, 2026~2030), C:Month(1~12), D:Pipeline Name, routing=From Country, To Country; value=H:User adjusted capacity (Bcm/y)', 'fixed_columns', 7, 13, 'B:Year,C:Month,D:Pipeline name,H:User adjusted capacity (Bcm/y)', NULL, NULL, NULL, NULL, NULL, NULL, 'stop_when_all_key_columns_empty', 'model-parameter-canonical-v4', 'N', 'system', '2026-07-06T11:14:02.203729'),
        (16, 'Y', 'RegasAdjustment', '재기화 플랜트·월별 처리용량의 최종 절대값이다. value는 Mt LNG/month 단위이며 0 이상이다. proposedValue는 증감폭이 아니라 해당 Continent/Region/Country/Regasification plant/Life Cycle Category/Nameplate capacity/Year/Month에 적용할 최종 처리용량이다. Basecase exact slot만 사용하고 서로 다른 설비나 lifecycle 행을 합치지 않는다.', 'Supply', 'RegasAdjustment', 'table1', 'slot=B:Continent, C:Region, D:Country, E:Regasification plant, F:Life Cycle Category, G:Nameplate capacity (MTPA), Year(YYYY, 2026~2030), Month(1~12); value=RegasAdjustment (Mt LNG/month), 재기화 처리용량 절대값', 'matrix_time_columns', 10, 11, 'B:Continent,C:Region,D:Country,E:Regasification plant,F:Life Cycle Category,G:Nameplate capacity (MTPA)', NULL, 9, 10, NULL, 'H', 'DK', 'stop_when_all_key_columns_empty', 'model-parameter-canonical-v4', 'N', 'system', '2026-07-06T11:14:02.203729'),
        (17, 'Y', 'SupplyDisruption', '국가·연월별 upstream 가스 공급량의 최종 절대값이다. value는 Bcm 단위이며 0 이상이다. LUT 기준값은 BCProduction의 연간 Base case supply를 동일 Province/PNG-LNG의 원본 월별 Seasonality 계수와 곱한 뒤 Country/Year/Month로 합산한다. 계수를 재정규화하지 않는다. proposedValue는 차질량이 아니라 해당 월에 적용할 최종 공급량이다.', 'Supply', 'VolumeAdjustment', 'table2', 'slot=I:Year(YYYY, 2026~2030), J:Month(1~12), K:Country; value=M:Volumes (Bcm), Country별 월 공급량 절대값', 'fixed_columns', 7, 8, 'I:Year,J:Month,K:Country,M:Volumes (Bcm)', NULL, NULL, NULL, NULL, NULL, NULL, 'stop_when_all_key_columns_empty', 'model-parameter-canonical-v4', 'N', 'system', '2026-07-06T11:14:02.203729'),
        (18, 'Y', 'PNG Contract Volume', 'From/To 국가·연도별 PNG 계약 물량의 최종 절대값이다. value는 BCM 단위이며 0 이상이다. proposedValue는 증감폭이 아니라 해당 Year/From Country/To Country에 적용할 Unadjusted Gross Gas Import 계약 물량이다. Basecase exact slot만 사용한다.', 'Trade', 'MidstreamContractInput', 'table1', 'slot=A:Year(YYYY, 2026~2030), B:From Country, C:To Country; value=D:Unadjusted Gross Gas Import [BCM], PNG 계약 물량 절대값', 'fixed_columns', 4, 5, 'A:Year,B:From Country,C:To Country,D:Unadjusted Gross Gas Import [BCM]', NULL, NULL, NULL, NULL, NULL, NULL, 'stop_when_all_key_columns_empty', 'model-parameter-canonical-v4', 'N', 'system', '2026-07-06T11:14:02.203729'),
        (19, 'Y', 'RemainingUnrestrictedAmount', 'From/To 국가·연도별 거래 제한 이후 남은 무제한 거래 가능 물량의 최종 절대값이다. value는 BCM 단위이며 0 이상이다. proposedValue는 증감폭이 아니라 해당 Year/From Country/To Country에 적용할 Remaining Unrestricted Amount다. Basecase exact slot만 사용한다.', 'Trade', 'TradeRestrictionInput', 'table1', 'slot=B:Year(YYYY, 2026~2030), C:From Country, D:To Country; value=J:Remaining Unrestricted Amount [BCM], 거래 가능 물량 절대값', 'fixed_columns', 5, 6, 'B:Year,C:From Country,D:To Country,J:Remaining Unrestricted Amount [BCM]', NULL, NULL, NULL, NULL, NULL, NULL, 'stop_when_all_key_columns_empty', 'model-parameter-canonical-v4', 'N', 'system', '2026-07-06T11:14:02.203729'),
        (20, 'Y', 'ShippingCost', '연도별 해상 운송비 사용자 입력의 최종 절대값이다. value는 $/d 단위이며 0 이상이다. proposedValue는 basecase 대비 증감폭이 아니라 해당 Year에 적용할 User Input Absolute Value다. Basecase가 제공하는 Year exact slot만 사용하고 영향 범위는 rationale에 보존한다.', 'Trade', 'ShippingCostInput', 'table1', 'slot=B:Year(YYYY, 2026~2030); value=F:User Input Absolute Value ($/d), 연도별 해상 운송비 절대값', 'fixed_columns', 5, 6, 'B:Year,F:User Input Absolute Value ($/d)', NULL, NULL, NULL, NULL, NULL, NULL, 'stop_when_all_key_columns_empty', 'model-parameter-canonical-v4', 'N', 'system', '2026-07-06T11:14:02.203729'),
        (21, 'Y', 'VolumeCancelled', 'From/To 국가·연도별 취소 계약 물량의 최종 절대값이다. value는 BCM 단위이며 0 이상이다. proposedValue는 증감폭이 아니라 해당 Year/From Country/To Country에 적용할 취소 물량이다. Basecase exact slot만 사용한다.', 'Trade', 'TradeRestrictionInput', 'table1', 'slot=B:Year(YYYY, 2026~2030), C:From Country, D:To Country; value=F:Volume [BCM], 취소 계약 물량 절대값', 'fixed_columns', 5, 6, 'B:Year,C:From Country,D:To Country,F:Volume [BCM]', NULL, NULL, NULL, NULL, NULL, NULL, 'stop_when_all_key_columns_empty', 'model-parameter-canonical-v4', 'N', 'system', '2026-07-06T11:14:02.203729');

    CREATE TEMPORARY TABLE _mpv4_snapshot_mapping AS
    SELECT `model_param_dimension_map_id`, `use_yn`, `event_type_l2_id`, `dimension_key`, `dimension_label`, `mapping_method`, `model_param_id`, `comment`, `crt_usr_logn_id`, `crt_dtm`, `mod_usr_logn_id`, `mod_dtm`, `del_yn`
      FROM tmm_mi_model_param_dimension_map
     WHERE 1 = 0;

    INSERT INTO _mpv4_snapshot_mapping (
        `model_param_dimension_map_id`, `use_yn`, `event_type_l2_id`, `dimension_key`, `dimension_label`, `mapping_method`, `model_param_id`, `comment`, `crt_usr_logn_id`, `crt_dtm`, `mod_usr_logn_id`, `mod_dtm`, `del_yn`
    ) VALUES
        (1, 'Y', 1, 'period', '기간', 'indirect', NULL, 'LiqUtilAdjustment의 Year/Month 적용 기간 판단에 사용한다.', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-08T07:47:28.015707', 'N'),
        (2, 'Y', 1, 'utilization_change_amount', 'Utilization 변화 폭', 'na', NULL, 'Province/Basin 생산 차질량(Bcm 또는 %); 증산은 음(-)', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-08T07:47:31.960951', 'N'),
        (3, 'Y', 1, 'onset_pattern', '발생 패턴', 'indirect', NULL, '가동률 변화가 급격히 반영되는지 점진적으로 반영되는지 월별 시계열 형태 판단에 사용한다.', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-08T07:47:28.091708', 'N'),
        (4, 'Y', 1, 'recovery_pattern', '회복 패턴', 'indirect', NULL, '가동률이 basecase 수준으로 회복되는 시점과 월별 회복 경로 판단에 사용한다.', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-08T07:47:28.166594', 'N'),
        (5, 'Y', 1, 'alt_gas_supply_availability', '대체 가스 공급 가능성', 'na', NULL, NULL, 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-08T07:47:31.960951', 'N'),
        (6, 'Y', 1, 'alt_gas_supply_availability', '대체 가스 공급 가능성', 'direct', 14, '대체 공급이 LNG 전환으로 설명되는 경우, 대체 가능한 공급국의 기존 LNG Plant Train 가동률을 상향 조정한다. alt_gas_supply_availability는 상향 조정 가능한 물량과 배분 강도의 근거로 사용하고, period/onset_pattern/recovery_pattern은 적용 월과 시계열 형태에 반영한다. Train별 가동률은 0~1 범위와 기존 basecase 수준을 고려해 산정한다.', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-08T07:47:28.301373', 'N'),
        (7, 'Y', 2, 'period', '기간', 'indirect', NULL, 'LiqUtilAdjustment의 Year/Month 적용 기간 판단에 사용한다.', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-08T07:47:28.384916', 'N'),
        (8, 'Y', 2, 'utilization_change_amount', 'Utilization 변화량', 'direct', 14, '차질 또는 회복 대상 LNG Plant Train의 가동률 최종값을 산정한다. utilization_change_amount는 basecase 대비 가동률 하향·상향 조정폭의 주된 근거로 사용하고, period/onset_pattern/recovery_pattern은 적용 월과 월별 변화 경로에 반영한다. 단기·부분 차질은 생산량 직접 입력보다 Train 가동률 조정을 우선한다.', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-08T07:47:28.478683', 'N'),
        (9, 'Y', 2, 'utilization_change_amount', 'Utilization 변화량', 'na', NULL, NULL, 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-08T07:47:31.960951', 'N'),
        (10, 'Y', 2, 'onset_pattern', '발생 패턴', 'indirect', NULL, '가동률 변화가 급격히 반영되는지 점진적으로 반영되는지 월별 시계열 형태 판단에 사용한다.', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-08T07:47:28.674845', 'N'),
        (11, 'Y', 2, 'recovery_pattern', '회복 패턴', 'indirect', NULL, '가동률이 basecase 수준으로 회복되는 시점과 월별 회복 경로 판단에 사용한다.', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-08T07:47:28.743606', 'N'),
        (12, 'Y', 2, 'alt_lng_supply_availability', '대체 LNG 공급 가능성', 'direct', 14, '차질로 감소한 LNG 공급을 대체 가능한 다른 공급국/Plant Train의 가동률 상향으로 일부 상쇄한다. alt_lng_supply_availability는 대체 가능 물량과 배분 강도의 근거로 사용하고, 기존 basecase 가동률이 높은 Train에는 추가 상향을 제한한다.', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-08T07:47:28.811700', 'N'),
        (13, 'Y', 3, 'cod_timing', 'COD 시점', 'indirect', NULL, '신규 생산량 투입 시작 시간축(기존 대비 ±N월)', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (14, 'Y', 3, 'ramp_up_completion_timing', 'Ramp-up 완료 시점', 'indirect', NULL, '단계 투입 완료 시간축', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (15, 'Y', 3, 'ramp_up_pattern', 'Ramp-up 패턴', 'indirect', NULL, '급격/점진; FID 무산 시 투입 없음', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (16, 'Y', 3, 'target_utilization_at_ramp_up', 'Ramp-up 완료 시 도달 가동률 (Nameplate Capa 대비)', 'na', NULL, '신규 Plant>Train 생산량 추가(Mt); FID무산=0 : COD 지연·Ramp-up 단계에 맞춰 신규 Plant/Train 생산량을 월별로 반영하고, FID 무산은 추가 생산량 0으로 처리', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-08T07:47:31.960951', 'N'),
        (17, 'Y', 4, 'period', '기간', 'indirect', NULL, 'LiqUtilAdjustment의 Year/Month 적용 기간 판단에 사용한다.', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-08T07:47:28.878756', 'N'),
        (18, 'Y', 4, 'utilization_change_amount', 'Utilization 변화 폭 (송출용량 대비)', 'na', NULL, NULL, 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-08T07:47:31.960951', 'N'),
        (19, 'Y', 4, 'utilization_change_amount', 'Utilization 변화 폭 (송출용량 대비)', 'na', NULL, NULL, 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-08T07:47:29.020660', 'N'),
        (20, 'Y', 4, 'structural_change_yn', '구조적 변동 여부', 'indirect', NULL, '가동률 조정이 한시적인지 구조적·장기적으로 지속되는지 판단에 사용한다.', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-08T07:47:29.111810', 'N'),
        (21, 'Y', 4, 'onset_pattern', '발생 패턴', 'indirect', NULL, '가동률 변화가 급격히 반영되는지 점진적으로 반영되는지 월별 시계열 형태 판단에 사용한다.', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-08T07:47:29.177483', 'N'),
        (22, 'Y', 4, 'recovery_pattern', '회복 패턴', 'indirect', NULL, '가동률이 basecase 수준으로 회복되는 시점과 월별 회복 경로 판단에 사용한다.', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-08T07:47:29.254158', 'N'),
        (23, 'Y', 4, 'alt_supply_availability', '대체 공급원 가능성 (타 노선·LNG 전환)', 'na', NULL, NULL, 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-08T07:47:31.960951', 'N'),
        (24, 'Y', 4, 'alt_supply_availability', '대체 공급원 가능성 (타 노선·LNG 전환)', 'direct', 14, '파이프라인 공급 차질을 LNG 전환으로 대체하는 경우, 대체 가능한 공급국의 기존 LNG Plant Train 가동률을 상향 조정한다. alt_supply_availability는 LNG 전환 가능 물량과 배분 강도의 근거로 사용하고, period/onset_pattern/recovery_pattern/structural_change_yn은 적용 월과 지속성 판단에 반영한다. Train별 가동률은 0~1 범위와 기존 basecase 수준을 고려해 산정한다.', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-08T07:47:29.405649', 'N'),
        (25, 'Y', 5, 'affected_period', '영향 기간', 'indirect', NULL, '시간축', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (26, 'Y', 5, 'capacity_change_scale', 'Capacity 변화 규모', 'direct', 7, '발전소 용량·가동 변화 규모를 근거로 해당 Country/Year의 Gas PowerMix 최종 비중을 산정한다. capacity_change_scale은 조정폭의 주된 근거로 사용하고, affected_period와 structural_change_yn은 적용 연도와 지속성 판단에 반영한다.', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-08T07:47:29.478952', 'N'),
        (27, 'Y', 5, 'capacity_change_scale', 'Capacity 변화 규모', 'na', NULL, NULL, 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-08T07:47:29.547182', 'N'),
        (28, 'Y', 5, 'structural_change_yn', '구조적 변동 여부', 'indirect', NULL, '단발(정비·사고)/구조적(COD·폐쇄)', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (29, 'Y', 5, 'alt_energy_absorption', '타 에너지원 흡수 가능성', 'direct', 7, '발전소 용량·가동 변화로 발생한 전력 공백 또는 증분을 타 에너지원이 얼마나 흡수하는지 반영해 Gas PowerMix 최종 비중을 산정한다. alt_energy_absorption이 낮을수록 Gas 비중 변화를 크게 반영하고, 높을수록 Gas 비중 변화는 작게 둔다.', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-08T07:47:29.627389', 'N'),
        (30, 'Y', 5, 'onset_pattern', '발생 패턴', 'indirect', NULL, '급격/점진', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (31, 'Y', 5, 'recovery_pattern', '회복 패턴', 'indirect', NULL, '원상복귀 속도', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (32, 'Y', 6, 'period', '기간', 'indirect', NULL, '동절기 월 슬롯', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (33, 'Y', 6, 'cold_wave_intensity', '한파 강도', 'na', NULL, NULL, 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-08T07:47:29.697430', 'N'),
        (34, 'Y', 6, 'cold_wave_intensity', '한파 강도', 'direct', 8, 'event에 명시된 한파 강도와 적용 기간을 근거로 해당 Country/Year/Month의 Temperature 최종값을 산정한다. 한파는 정상 기온 대비 하향 방향으로 반영하고, 해당 국가 기준 겨울 또는 한파가 발생 가능한 계절의 월을 선택한다. cold_wave_intensity의 온도 편차 범위와 peak_timing_pattern을 참고해 월별 조정폭을 차등 적용한다.', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-08T07:47:29.771078', 'N'),
        (35, 'Y', 6, 'entry_gas_inventory', '진입 시점 가스 재고 (평년 대비)', 'indirect', NULL, '재고는 수급모델 input 아님(Annual Balancing) — 영향 증폭/완화 해석 맥락', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (36, 'Y', 6, 'alt_energy_absorption', '타 에너지원 흡수 가능성', 'direct', 7, '석탄·석유 등 흡수 비율', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (37, 'Y', 6, 'peak_timing_pattern', 'Peak 시점, 패턴', 'indirect', NULL, '월별 수요 분배', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (38, 'Y', 7, 'period', '기간', 'indirect', NULL, '하절기 월 슬롯(동남아·인도 4~5월 포함)', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (39, 'Y', 7, 'heatwave_intensity', '폭염 강도', 'na', NULL, NULL, 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-08T07:47:29.834854', 'N'),
        (40, 'Y', 7, 'heatwave_intensity', '폭염 강도', 'direct', 8, 'event에 명시된 폭염 강도와 적용 기간을 근거로 해당 Country/Year/Month의 Temperature 최종값을 산정한다. 폭염은 정상 기온 대비 상향 방향으로 반영하고, 해당 국가 기준 여름 또는 폭염이 발생 가능한 계절의 월을 선택한다. heatwave_intensity의 온도 편차 범위와 peak_timing_pattern을 참고해 월별 조정폭을 차등 적용한다.', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-08T07:47:29.917633', 'N'),
        (41, 'Y', 7, 'entry_gas_inventory', '진입 시점 가스 재고 (평년 대비)', 'indirect', NULL, '재고는 수급모델 input 아님 — 해석 맥락', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (42, 'Y', 7, 'injection_pattern', 'Injection 패턴', 'indirect', NULL, '재고 회복 속도 = 재고 개념 — 수급모델 input 아님(맥락)', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (43, 'Y', 7, 'alt_energy_absorption', '타 에너지원 흡수 가능성', 'direct', 7, '재생E·원전 등 흡수', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (44, 'Y', 7, 'peak_timing_pattern', 'Peak 시점, 패턴', 'indirect', NULL, '월별 분배', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (45, 'Y', 8, 'affected_period', '영향 기간', 'indirect', NULL, '정비=Shoulder/사고·정책=단발 OR 영구', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (46, 'Y', 8, 'capacity_change_scale', 'Capacity 변화 규모', 'direct', 7, '원전 비중 변동→가스 비중 대체(원전 전용 input 없음)', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (47, 'Y', 8, 'capacity_change_scale', 'Capacity 변화 규모', 'na', NULL, '발전 가스 수요 직접 강제 시 : User-Adjusted Gas Demand는 미대상 수동 overwrite이므로 직접 쓰지 말고, 발전 설비 변화는 PowerMix의 Gas 비중 조정으로 반영', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (48, 'Y', 8, 'structural_change_yn', '구조적 변동 여부', 'indirect', NULL, '단발(정비)/구조적(COD·폐쇄·수명연장)', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (49, 'Y', 8, 'alt_energy_absorption', '타 에너지원 흡수 가능성', 'direct', 7, '재생E·석탄 등 흡수', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (50, 'Y', 8, 'onset_pattern', '발생 패턴', 'indirect', NULL, '급격(사고)/점진(정비)', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (51, 'Y', 8, 'recovery_pattern', '회복 패턴', 'indirect', NULL, '급격(재가동)/점진(COD)', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (52, 'Y', 9, 'affected_period', '영향 기간', 'indirect', NULL, '동절기 둔켈플라우테/하절기 열파 풍력 약화', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (53, 'Y', 9, 'capacity_change_scale', 'Capacity 변화 규모', 'direct', 7, '재생 출력 변동→가스 비중 대체(재생 전용 input 없음)', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (54, 'Y', 9, 'capacity_change_scale', 'Capacity 변화 규모', 'na', NULL, '발전 가스 수요 직접 강제 시 : User-Adjusted Gas Demand는 미대상 수동 overwrite이므로 직접 쓰지 말고, 발전 설비 변화는 PowerMix의 Gas 비중 조정으로 반영', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (55, 'Y', 9, 'structural_change_yn', '구조적 변동 여부', 'indirect', NULL, '단발(기상)/구조적(신규 Farm·정책)', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (56, 'Y', 9, 'alt_energy_absorption', '타 에너지원 흡수 가능성', 'direct', 7, '석탄·원전 등 흡수', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (57, 'Y', 9, 'onset_pattern', '발생 패턴', 'indirect', NULL, '급격(무풍)/점진(정책 phase-out)', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (58, 'Y', 9, 'recovery_pattern', '회복 패턴', 'indirect', NULL, '급격(기상)/점진(COD)', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (59, 'Y', 10, 'affected_period', '영향 기간', 'indirect', NULL, '단발(가격)/중기(계약)/장기(정책)', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (60, 'Y', 10, 'lng_demand_impact_intensity', 'LNG 수요 영향 강도', 'na', NULL, '가격기반 석탄↔가스 스위칭(Asia=Newcastle/JKM, EU=ARA/TTF) : 지역별 기준 가격쌍을 사용해 석탄-가스 전환 유인을 판단하고, 단기 가격 이벤트는 CoalGasAdjustment를 우선 사용', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-08T07:47:31.960951', 'N'),
        (61, 'Y', 10, 'lng_demand_impact_intensity', 'LNG 수요 영향 강도', 'na', NULL, '가격기반 석탄↔가스 스위칭(Asia=Newcastle/JKM, EU=ARA/TTF) : 지역별 기준 가격쌍을 사용해 석탄-가스 전환 유인을 판단하고, 단기 가격 이벤트는 CoalGasAdjustment를 우선 사용', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-08T07:47:31.960951', 'N'),
        (62, 'Y', 10, 'lng_demand_impact_intensity', 'LNG 수요 영향 강도', 'direct', 7, '구조적 비중 변화(정책·폐쇄) : 정책·폐쇄·설비 변화처럼 구조적 전환이면 PowerMix에서 Gas/Coal 비중을 연 단위로 조정', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (63, 'Y', 10, 'structural_change_yn', '구조적 변동 여부', 'indirect', NULL, '단발(가격→CoalGas)/구조적(정책→PowerMix) 결정', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (64, 'Y', 10, 'alt_energy_absorption', '타 에너지원 흡수 가능성', 'direct', 7, '원전·재생E 등 흡수', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (65, 'Y', 11, 'period', '기간', 'indirect', NULL, '시간축', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (66, 'Y', 11, 'affected_facility_type', '영향 시설 유형', 'na', NULL, NULL, 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-08T07:47:31.960951', 'N'),
        (67, 'Y', 11, 'affected_facility_type', '영향 시설 유형', 'routing', 14, '자연재해가 수출(액화) 시설의 단기·부분 가동 차질을 유발하는 경우 LiqUtilAdjustment를 선택한다. 선택된 경우 설비 용량 자체가 아니라 정전·침수·정비·운영 제약 등으로 기존 LNG Plant Train의 이용률이 낮아지는 상황을 해당 Train/Year/Month의 가동률 하향 조정으로 반영한다. affected_facility_type은 대상 시설이 액화 Plant/Train인지 판단하는 근거로 사용한다.', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-08T07:47:30.069714', 'N'),
        (68, 'Y', 11, 'affected_facility_type', '영향 시설 유형', 'na', NULL, NULL, 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-08T07:47:31.960951', 'N'),
        (69, 'Y', 11, 'affected_facility_type', '영향 시설 유형', 'na', NULL, NULL, 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-08T07:47:30.213202', 'N'),
        (70, 'Y', 11, 'affected_facility_type', '영향 시설 유형', 'na', NULL, NULL, 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-08T07:47:31.960951', 'N'),
        (71, 'Y', 11, 'supply_disruption_intensity', '공급 차질 강도', 'indirect', NULL, '시설 가동률 감소율로 변환 — 강도가 값 크기 결정 : routing으로 선택된 시설·파라미터의 감소율 또는 감소량을 결정하며, 강도 단계에 따라 조정폭을 차등 적용', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (72, 'Y', 11, 'supply_disruption_pattern', '공급 차질 - 발생/회복 패턴', 'indirect', NULL, 'Ref. 공급 차질 패턴 — 시계열 형태', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (73, 'Y', 11, 'alt_lng_supply_availability', '대체 LNG 공급 가능성', 'direct', 14, '자연재해로 감소한 LNG 공급을 대체 가능한 다른 공급국/Plant Train의 가동률 상향으로 일부 상쇄한다. alt_lng_supply_availability는 대체 가능 물량과 배분 강도의 근거로 사용하고, 기존 basecase 가동률이 높은 Train에는 추가 상향을 제한한다.', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-08T07:47:30.351463', 'N'),
        (74, 'Y', 12, 'inventory_level', '재고 수준 (평년 대비)', 'na', NULL, 'Annual Balancing — 재고/timing은 수급모델 input 아님; 시장·가격 해석 단계 : 재고 수준은 수급모델 input이 아니므로 직접 조정하지 않고, 공급 부족의 완충·증폭 맥락으로 기간·강도 판단에만 사용', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (75, 'Y', 12, 'duration_recovery_timing', '지속 기간 / 회복 시점', 'na', NULL, '재고 자체가 대상 아님 → 해당 없음 : 재고 회복 시점은 직접 입력하지 않고, 필요 시 이벤트 기간·회복 패턴 dimension으로만 반영', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (76, 'Y', 12, 'stockpile_policy_change', '비축 정책 변화', 'na', NULL, '비축 정책 변화가 그 해 LNG 구매량(연간 수요)을 바꾸는 부분만 — 재고 수준 자체는 아님 : 비축 정책이 실제 연간 LNG 구매량을 바꾸는 경우에만 수요·수입 방향성 판단에 사용하고, 재고 수준 자체 조정은 제외', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (77, 'Y', 12, 'spot_purchase_impact', 'Spot 구매 영향', 'na', NULL, 'Spot 가격 반응 = 가격 Output 단계 : Spot 구매·가격 반응은 가격 output·시장 해석 영역이므로 수급모델 input으로 직접 반영하지 않음', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (78, 'Y', 13, 'period', '기간', 'indirect', NULL, '시간축', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (79, 'Y', 13, 'freight_change_magnitude', '운임 변동 폭', 'na', NULL, '용선료·연료비 — impact_scope축 : 운임·연료비는 Trade/ShippingCost 미대상으로 직접 조정하지 않고, 물리적 운송 차질이 공급량·기간에 영향을 줄 때만 별도 dimension으로 해석', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (80, 'Y', 13, 'freight_change_pattern', '변화 진행 패턴', 'indirect', NULL, '급격/점진', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (81, 'Y', 13, 'structural_change_yn', '구조적 변동 여부', 'indirect', NULL, '단발/구조적', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (82, 'Y', 14, 'period', '기간', 'indirect', NULL, '시간축', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (83, 'Y', 14, 'cargo_flow_disruption_intensity', '화물 흐름 차질 강도', 'na', NULL, '항로 통과비용·차단 여부 : 화물 흐름·항로 비용 이슈는 ShippingCost 미대상이라 직접 반영하지 않고, 실제 공급 지연·물량 차질이 명시될 때 기간·강도 판단에만 사용', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (84, 'Y', 14, 'rerouting_availability', '우회·재라우팅 가능성', 'na', NULL, '우회 비용 상승; 높을수록 완화 : 우회 가능성은 비용 파라미터가 아니라 공급 차질 완화계수로 해석하고, 직접 수급모델 입력은 하지 않음', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (85, 'Y', 14, 'rerouting_availability', '우회·재라우팅 가능성', 'na', NULL, '봉쇄 시 통과 제약 : 봉쇄·통과 제한은 TradeRestrictionInput 미대상으로 직접 조정하지 않고, 실제 물량 차단이 확인될 때 공급 차질 이벤트로 별도 반영', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (86, 'Y', 14, 'transit_delay', '운송 지연 규모', 'indirect', NULL, '납기 지연 — ShippingCost 경유 간접', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (87, 'Y', 15, 'period', '기간', 'indirect', NULL, '시간축', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (88, 'Y', 15, 'transaction_scale', '규모', 'na', NULL, '대규모 계약 분쟁·취소 물량 From-To (단순 헷지 포지션 재편은 실물 수급 아님→case) : 거래 분쟁·취소 물량은 TradeRestriction 미대상으로 직접 입력하지 않고, 실물 공급 또는 수요 변화가 명확한 경우 해당 공급·수요 파라미터로만 우회 반영', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (89, 'Y', 15, 'market_impact_persistence', '시장 영향 지속성', 'indirect', NULL, '일시/단기/구조적', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (90, 'Y', 16, 'period', '기간', 'na', NULL, '수급모델 Input 해당 없음 : 인덱스 Spread 이벤트는 가격·시장 해석 영역이므로 기간도 수급모델 파라미터 적용 기간으로 사용하지 않음', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (91, 'Y', 16, 'spread_change_magnitude', 'Spread 변동 폭', 'na', NULL, '가격 인덱스 간 관계 = 가격 Output 단계 — 수급모델 input으로 건드리지 않음 : 가격 spread 변화는 가격 output·시장 신호로만 사용하고 수급모델 input 값을 직접 변경하지 않음', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (92, 'Y', 16, 'structural_change_yn', '구조적 변동 여부', 'na', NULL, '상동 — 본 매핑 대상 외 : 구조적 여부도 spread 해석 구분용이며 수급모델 input 선정 조건으로 사용하지 않음', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (93, 'Y', 17, 'period', '기간', 'indirect', NULL, 'LiqUtilAdjustment의 Year/Month 적용 기간 판단에 사용한다.', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-08T07:47:30.426504', 'N'),
        (94, 'Y', 17, 'transport_disruption', '운송 차질', 'na', NULL, NULL, 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-08T07:47:30.497141', 'N'),
        (95, 'Y', 17, 'supply_disruption_intensity', '공급 차질 - 강도', 'direct', 14, '지정학적 긴장·전쟁으로 영향권 액화시설의 단기·부분 가동 제약이 발생하는 경우, 기존 LNG Plant Train의 가동률을 하향 조정한다. supply_disruption_intensity는 하향 조정폭의 주된 근거로 사용하고, period/supply_disruption_pattern은 적용 월과 월별 변화 경로에 반영한다. Train별 가동률은 0~1 범위와 기존 basecase 수준을 고려해 산정한다.', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-08T07:47:30.573698', 'N'),
        (96, 'Y', 17, 'supply_disruption_intensity', '공급 차질 - 강도', 'na', NULL, NULL, 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-08T07:47:31.960951', 'N'),
        (97, 'Y', 17, 'supply_disruption_intensity', '공급 차질 - 강도', 'na', NULL, NULL, 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-08T07:47:31.960951', 'N'),
        (98, 'Y', 17, 'supply_disruption_pattern', '공급 차질 - 발생/회복 패턴', 'indirect', NULL, '가동률 변화가 급격히 반영되는지 점진적으로 반영되는지 월별 시계열 형태 판단에 사용한다.', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-08T07:47:30.797504', 'N'),
        (99, 'Y', 17, 'demand_response_alternative_lng', '수요측 대응 - 타 공급원 경유 LNG 확보량', 'direct', 14, '수요측이 타 공급원 경유 LNG를 확보하는 경우, 대체 가능한 공급국의 기존 LNG Plant Train 가동률을 상향 조정한다. demand_response_alternative_lng는 대체 가능 물량과 배분 강도의 근거로 사용하고, 기존 basecase 가동률이 높은 Train에는 추가 상향을 제한한다.', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-08T07:47:30.875210', 'N'),
        (100, 'Y', 17, 'demand_response_powermix_reduction', '수요측 대응 - PowerMix 조정 등을 통한 LNG 수요 감소량', 'direct', 7, '자체 PowerMix 조정으로 LNG 수요 감소(SPR/대체 효과 포함) : 수요국의 정책·비상 대응으로 LNG 발전 수요가 줄면 PowerMix의 Gas 비중을 낮추고 대체 전원 비중을 조정', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (101, 'Y', 17, 'demand_response_powermix_reduction', '수요측 대응 - PowerMix 조정 등을 통한 LNG 수요 감소량', 'na', NULL, '해당 섹터 수요 직접 감소 강제 시 : User-Adjusted Gas Demand 미대상 수동 overwrite는 직접 쓰지 않고, 수요 감소는 PowerMix Gas 비중 또는 대상 섹터 proxy로 환산', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (102, 'Y', 17, 'trade_restriction', '거래 제한 (계약 취소 등)', 'na', NULL, NULL, 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-08T07:47:30.949195', 'N'),
        (103, 'Y', 18, 'period', '기간', 'indirect', NULL, 'LiqUtilAdjustment의 Year/Month 적용 기간 판단에 사용한다.', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-08T07:47:31.035250', 'N'),
        (104, 'Y', 18, 'transport_disruption', '운송 차질', 'na', NULL, NULL, 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-08T07:47:31.100015', 'N'),
        (105, 'Y', 18, 'supply_disruption_intensity', '공급 차질 - 강도', 'direct', 14, '경제 제재·무역 제한으로 영향권 액화시설의 단기·부분 가동 제약이 발생하는 경우, 기존 LNG Plant Train의 가동률을 하향 조정한다. supply_disruption_intensity는 하향 조정폭의 주된 근거로 사용하고, period/supply_disruption_pattern은 적용 월과 월별 변화 경로에 반영한다. Train별 가동률은 0~1 범위와 기존 basecase 수준을 고려해 산정한다.', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-08T07:47:31.173687', 'N'),
        (106, 'Y', 18, 'supply_disruption_intensity', '공급 차질 - 강도', 'na', NULL, NULL, 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-08T07:47:31.960951', 'N'),
        (107, 'Y', 18, 'supply_disruption_intensity', '공급 차질 - 강도', 'na', NULL, NULL, 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-08T07:47:31.960951', 'N'),
        (108, 'Y', 18, 'supply_disruption_pattern', '공급 차질 - 발생/회복 패턴', 'indirect', NULL, '가동률 변화가 급격히 반영되는지 점진적으로 반영되는지 월별 시계열 형태 판단에 사용한다.', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-08T07:47:31.369200', 'N'),
        (109, 'Y', 18, 'demand_response_alternative_lng', '수요측 대응 - 타 공급원 경유 LNG 확보량', 'direct', 14, '수요측이 타 공급원 경유 LNG를 확보하는 경우, 대체 가능한 공급국의 기존 LNG Plant Train 가동률을 상향 조정한다. demand_response_alternative_lng는 대체 가능 물량과 배분 강도의 근거로 사용하고, 기존 basecase 가동률이 높은 Train에는 추가 상향을 제한한다. 제재·무역 제한에서는 대체 공급 형성에 일부 지연이 있을 수 있음을 월별 배분 시 보조적으로 고려한다.', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-08T07:47:31.445254', 'N'),
        (110, 'Y', 18, 'demand_response_powermix_reduction', '수요측 대응 - PowerMix 조정 등을 통한 LNG 수요 감소량', 'direct', 7, '자체 PowerMix 조정 수요 감소', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (111, 'Y', 18, 'demand_response_powermix_reduction', '수요측 대응 - PowerMix 조정 등을 통한 LNG 수요 감소량', 'na', NULL, '해당 섹터 수요 직접 감소 강제 시 : User-Adjusted Gas Demand 미대상 수동 overwrite는 직접 쓰지 않고, 수요 감소는 PowerMix Gas 비중 또는 대상 섹터 proxy로 환산', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (112, 'Y', 18, 'trade_restriction', '거래 제한 (계약 취소 등)', 'na', NULL, NULL, 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-08T07:47:31.513101', 'N'),
        (113, 'Y', 19, 'period', '기간', 'indirect', NULL, '시간축', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (114, 'Y', 19, 'implementation_stage', '시행 확실성·단계', 'indirect', NULL, '검토/루머~시행 — 반영 시점·확률 weighting', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (115, 'Y', 19, 'impact_intensity', '영향 강도', 'routing', 7, '전원믹스·탄소규제·발전설비·연료전환 정책처럼 에너지원별 발전 비중이 구조적으로 변하는 경우 PowerMix를 적용한다. impact_intensity는 영향 국가·연도와 Gas 발전 비중 조정폭을 판단하는 근거로 사용한다.', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-13T04:49:29.959834', 'N'),
        (116, 'Y', 19, 'impact_intensity', '영향 강도', 'na', NULL, '정책 영향 라우팅 후보(3개 중 선택) : 석탄 가격·세금·보조금·수입규제 등으로 석탄 발전 경제성이 변해 Gas↔Coal 전환 유인이 생기면 Coal Futures Price 선택', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-08T07:47:31.960951', 'N'),
        (117, 'Y', 19, 'impact_intensity', '영향 강도', 'na', NULL, '정책 영향 라우팅 후보(3개 중 선택) : 가스/LNG 가격·세금·보조금·구매규제 등으로 가스 발전 경제성이 변해 Gas↔Coal 전환 유인이 생기면 Gas Futures Price 선택', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-08T07:47:31.960951', 'N'),
        (118, 'Y', 19, 'impact_intensity', '영향 강도', 'na', NULL, '발전·수요 정책 (탄소·전환 등) : User-Adjusted Gas Demand 미대상 수동 overwrite는 쓰지 않고, 발전·수요 정책은 PowerMix/CoalGasAdjustment 등 대상 파라미터로만 라우팅', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (119, 'Y', 19, 'impact_intensity', '영향 강도', 'na', NULL, '수출입 규제(관세·금수) : 관세·금수 등 TradeRestrictionInput 미대상 항목은 직접 반영하지 않고, 실제 물량 차질이 명확할 때 Supply 파라미터로 별도 반영', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (120, 'Y', 19, 'impact_intensity', '영향 강도', 'na', NULL, '운송 규제(FuelEU 등) : 운송 규제·비용은 ShippingCost 미대상이라 직접 반영하지 않고, 물리적 운송 지연·제약이 공급량에 연결될 때만 기간·강도 판단에 사용', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (121, 'Y', 19, 'structural_change_yn', '구조적 변동 여부', 'indirect', NULL, '단발/한시 vs 구조적/영구', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (122, 'Y', 20, 'period', '기간', 'indirect', NULL, '시간축', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (123, 'Y', 20, 'change_magnitude', '변동 폭', 'indirect', NULL, '환율·금리 직접 input 없음 — 구매력→수요 효과는 간접(필요 시 경기(PMI) 변동으로 대용 해석)', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (124, 'Y', 20, 'persistence', '지속성', 'indirect', NULL, '일시/단기/구조적', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-06T11:14:02.354122', 'N'),
        (125, 'Y', 21, 'period', '기간', 'indirect', NULL, '파라미터의 시간축으로 사용될 수 있다(PMI:Year/Month, GDP:Year)', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-08T07:47:31.581705', 'N'),
        (126, 'Y', 21, 'economic_intensity', '강도', 'direct', 6, 'event에 명시된 제조업/서비스업 경기, 생산활동 증가·감소, 산업활동 둔화·회복, 단기 경기 강도를 근거로 해당 Country/Year/Month의 PMI 지수 최종값을 산정한다. basecase가 있으면 기존 PMI 수준과 이벤트 방향을 비교해 보수적으로 조정한다. basecase가 없으면 다른 국가의 PMI 수준을 기준값으로 삼지 않고, 이벤트에 제시된 해당 국가의 경기 방향과 PMI 기준값 50을 중심으로 산정한다.', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-08T07:47:31.656112', 'N'),
        (127, 'Y', 21, 'economic_intensity', '강도', 'direct', 4, 'event에 명시된 국가별 GDP 성장률 전망, 전망치 수정폭, 하방/상방 시나리오를 우선 사용해 해당 Country/Year의 최종 성장률을 산정한다. 성장률 전망이 정량으로 제시되지 않으면 경기 둔화/회복 강도와 기간을 근거로 basecase 대비 보수적으로 조정한다. LNG 수요 영향률이나 가격 영향률을 GDP 성장률 multiplier로 사용하지 않는다.', 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-08T07:47:31.726171', 'N'),
        (128, 'Y', 21, 'demand_impact', 'LNG 수요 영향 규모', 'na', NULL, NULL, 'system', '2026-07-06T11:14:02.354122', 'system', '2026-07-08T07:47:31.795311', 'N');

    CREATE TEMPORARY TABLE _mpv4_snapshot_lever AS
    SELECT `impact_lever_id`, `lever_code`, `domain`, `label`, `description`, `applicability_hint`, `parent_lever_code`, `parameter_bindings`, `catalog_version`, `use_yn`, `mod_usr_logn_id`, `del_yn`, `crt_usr_logn_id`, `crt_dtm`
      FROM tmm_mi_model_impact_lever_m
     WHERE 1 = 0;

    INSERT INTO _mpv4_snapshot_lever (
        `impact_lever_id`, `lever_code`, `domain`, `label`, `description`, `applicability_hint`, `parent_lever_code`, `parameter_bindings`, `catalog_version`, `use_yn`, `mod_usr_logn_id`, `del_yn`, `crt_usr_logn_id`, `crt_dtm`
    ) VALUES
        (1, 'weather_demand', 'demand', '기상 기반 수요', '평년 대비 기온 변동으로 난방·냉방 및 가스발전용 LNG 수요가 변하는 영향', '겨울 한파·따뜻한 겨울 또는 여름 폭염의 기간, Temperature·HDD·CDD 기반 강도, 진입 재고, 타 에너지원 흡수 가능성, Peak 시점·패턴이 불확실할 때 사용', NULL, '[{"applicability":"국가·연·월 기온 직접 조정","parameter_name":"Temperature","role":"primary","support_status":"executable"},{"applicability":"난방도일로 표현 가능한 한파","parameter_name":"HDD","role":"alternative","support_status":"executable"},{"applicability":"냉방도일로 표현 가능한 폭염","parameter_name":"CDD","role":"alternative","support_status":"executable"}]', 'v2', 'Y', 'system', 'N', 'system', '2026-08-11T10:34:41.803263'),
        (2, 'power_generation_mix', 'demand', '발전 믹스', '가스·원자력·재생에너지·석탄 발전의 가동률, 설비용량 또는 발전 비중 변화에 따른 LNG 발전 수요 변화', '발전원별 영향 기간, Capacity 변화 규모, 단발·구조적 변동, 타 에너지원 흡수 가능성, 발생·회복 패턴을 분기할 때 사용', NULL, '[{"applicability":"국가·연·에너지원별 발전 비중 조정","parameter_name":"PowerMix","role":"primary","support_status":"executable"}]', 'v2', 'Y', 'system', 'N', 'system', '2026-08-11T10:34:41.803263'),
        (3, 'economic_activity', 'demand', '경제 활동', 'GDP·PMI 등 국가별 경기 변동에 따른 산업·발전 부문의 LNG 수요 변화', '대상 국가의 경기 확장·둔화 방향과 기간, 경기 강도, LNG 수요 영향 규모가 불확실할 때 사용', NULL, '[{"applicability":"국가별 연간 경제 성장 경로","parameter_name":"GDP","role":"primary","support_status":"executable"},{"applicability":"국가별 월간 경기 강도","parameter_name":"PMI","role":"alternative","support_status":"executable"}]', 'v2', 'Y', 'system', 'N', 'system', '2026-08-11T10:34:41.803263'),
        (4, 'direct_gas_demand', 'demand', '직접 가스 수요', '산업·도시가스·수송 부문의 직접 LNG·가스 소비 변화', '21개 Event Type 중 직접 대응 유형은 없으며, 경제 활동이나 발전 믹스로 설명되지 않는 수요 정책·절감·연료 전환의 기간, 영향 강도, 구조성이 핵심일 때 제한적으로 사용', NULL, '[]', 'v2', 'Y', 'system', 'N', 'system', '2026-08-11T10:34:41.803263'),
        (5, 'upstream_production', 'supply', 'Upstream 생산', '기존 가스전의 생산량·가동률 증감과 차질 후 회복에 따른 LNG 공급 변화', '기간, Nameplate 대비 Utilization 변화 폭, 급격·점진 발생, 급격·점진·영구 회복, 대체 가스 공급 가능성을 분기할 때 사용', NULL, '[{"applicability":"생산 지역별 연간 공급 차질","parameter_name":"SupplyDisruption","role":"primary","support_status":"executable"}]', 'v2', 'Y', 'system', 'N', 'system', '2026-08-11T10:34:41.803263'),
        (6, 'liquefaction_availability', 'supply', '액화시설 가용성', '기존 LNG 액화·수출 터미널의 가동률·생산량 변동과 신규 수출 터미널의 COD·Ramp-up 일정 변화', '기존 플랜트·Train의 기간, Utilization 변화량, 발생·회복 패턴, 대체 LNG 공급 가능성 또는 신규 설비의 COD, Ramp-up 완료 시점·패턴·도달 가동률이 불확실할 때 사용', NULL, '[{"applicability":"플랜트·Train별 가동률 조정","parameter_name":"LiqUtilAdjustment","role":"primary","support_status":"executable"},{"applicability":"플랜트·Train별 생산량 직접 조정","parameter_name":"LiqProdAdjustment","role":"alternative","support_status":"executable"}]', 'v2', 'Y', 'system', 'N', 'system', '2026-08-11T10:34:41.803263'),
        (7, 'regasification_capacity', 'supply', '재기화 수용력', '수입 터미널의 재기화 처리 가능 물량과 신규 수입 터미널의 COD·Ramp-up 일정 변화', '신규 수입 터미널의 COD·Ramp-up 완료 시점과 도달 가동률 또는 자연재해로 인한 수입 시설의 차질 강도·회복 패턴이 수요 흡수력을 제한할 때 사용', NULL, '[{"applicability":"재기화 플랜트별 용량 조정","parameter_name":"RegasAdjustment","role":"primary","support_status":"executable"}]', 'v2', 'Y', 'system', 'N', 'system', '2026-08-11T10:34:41.803263'),
        (8, 'natural_disaster_disruption', 'supply', '자연재해 공급 차질', '허리케인·태풍·지진 등 자연재해가 생산·수출·수입 LNG 인프라에 일으키는 물리적 공급 차질', '기간, 영향 시설 유형, 공급 차질 강도, P1~P9 발생·회복 패턴, 대체 LNG 공급 가능성을 분기할 때 사용', NULL, '[{"applicability":"미국 액화시설 허리케인 차질","parameter_name":"HurricaneIntensity","role":"primary","support_status":"executable"}]', 'v2', 'Y', 'system', 'N', 'system', '2026-08-11T10:34:41.803263'),
        (9, 'pipeline_capacity', 'supply', '파이프라인 수송력', 'PNG 파이프라인 송출 가동률과 수송용량의 단발적·구조적 변화', '기간, 송출용량 대비 Utilization 변화 폭, 단발·구조적 여부, 발생·회복 패턴, 타 노선·LNG 전환 가능성을 분기할 때 사용', NULL, '[]', 'v2', 'Y', 'system', 'N', 'system', '2026-08-11T10:34:41.803263'),
        (10, 'shipping_cost', 'trade', '해상 운송비', '선복 수급, 항로 차질, 연료비, 계절성, 지정학·제재로 인한 LNG·원유 선박 운임과 부대 운송비 변화', '해상 운임의 기간, 변동 폭, 급격·점진 진행, 단발·구조적 여부를 분기하거나 항로·지정학·제재 충격의 운송비 효과를 정량 반영할 때 사용', NULL, '[{"applicability":"영향 범위별 연간 운송비 조정","parameter_name":"ShippingCost","role":"primary","support_status":"executable"}]', 'v2', 'Y', 'system', 'N', 'system', '2026-08-11T10:34:41.803263'),
        (11, 'route_disruption', 'trade', '항로 제약', '운하·해협·항만의 혼잡·봉쇄·운항 차질·우회로 발생하는 LNG 화물 흐름의 지연과 왜곡', '기간, 화물 흐름 차질 강도, 우회·재라우팅 가능성, 운송 지연 규모 또는 지정학·제재에 따른 운송 차질 강도가 불확실할 때 사용', NULL, '[{"applicability":"우회로 인한 비용 효과만 직접 반영","parameter_name":"ShippingCost","role":"primary","support_status":"executable"}]', 'v2', 'Y', 'system', 'N', 'system', '2026-08-11T10:34:41.803263'),
        (12, 'contract_volume', 'trade', '계약 물량', '대규모 장기계약의 분쟁·취소·재협상과 거래 제한으로 현물시장에 유입되거나 이탈하는 계약 물량 변화', '거래 규모와 시장 영향 지속성 또는 지정학·제재 시 일부·전체 계약 취소 여부가 지역별 가용 화물을 바꿀 때 사용', NULL, '[]', 'v2', 'Y', 'system', 'N', 'system', '2026-08-11T10:34:41.803263'),
        (13, 'trade_restriction', 'trade', '거래 제한', '지정학적 갈등, 정부 제재, 관세, 수출입·목적지 제한 및 정책·규제로 인한 LNG 거래 가능 물량 변화', '적용 기간, 시행 단계, 운송·공급 차질 강도와 회복 패턴, 대체 공급·PowerMix 대응, 계약 취소 범위가 지역 간 화물 흐름을 제한할 때 사용', NULL, '[]', 'v2', 'Y', 'system', 'N', 'system', '2026-08-11T10:34:41.803263'),
        (14, 'inventory_condition', 'price_only', '재고 여건', '평년 대비 LNG·PNG 재고 수준, 주입·인출 여력과 비축 정책 변화가 현물 구매 압력 및 가격 민감도에 미치는 영향', '평년 대비 5단계 재고 수준, 지속·회복 기간, 비축 정책, Spot 구매 영향 또는 한파·폭염 진입 재고와 Injection 패턴을 가격 조건으로 반영할 때 사용', NULL, '[]', 'v2', 'Y', 'system', 'N', 'system', '2026-08-11T10:34:41.803263'),
        (15, 'regional_price_spread', 'price_only', '지역 가격 스프레드', 'JKM·TTF·Henry Hub 등 가격 인덱스 간 Spread의 비정상적·구조적 변화와 그에 따른 차익거래 유인 변화', '기간, 대상 Spread의 확대·축소 방향, 변동 폭, 단발·구조적 여부가 화물 유인과 지역별 가격을 차별화할 때 사용', NULL, '[]', 'v2', 'Y', 'system', 'N', 'system', '2026-08-11T10:34:41.803263'),
        (16, 'financial_market_sentiment', 'price_only', '금융시장 심리', '헷지 포지션 재편, 환율·금리 변동과 위험 프리미엄이 시장 유동성, 수입국 구매력 및 단기 LNG 가격에 미치는 간접 영향', '거래·헷징의 규모·지속성 또는 금리·통화의 변동 폭·지속성이 실물 수급모델 입력으로 직접 연결되지 않지만 가격 범위와 구매 여건을 바꿀 때 사용', NULL, '[]', 'v2', 'Y', 'system', 'N', 'system', '2026-08-11T10:34:41.803263');

    CREATE TEMPORARY TABLE _mpv4_canonical_lever AS
    SELECT * FROM _mpv4_snapshot_lever WHERE 1 = 0;

    INSERT INTO _mpv4_canonical_lever (
        `impact_lever_id`, `lever_code`, `domain`, `label`, `description`, `applicability_hint`, `parent_lever_code`, `parameter_bindings`, `catalog_version`, `use_yn`, `mod_usr_logn_id`, `del_yn`, `crt_usr_logn_id`, `crt_dtm`
    ) VALUES
        (1, 'weather_demand', 'demand', '기상 기반 수요', '평년 대비 기온 변동으로 난방·냉방 및 가스발전용 LNG 수요가 변하는 영향', '겨울 한파·따뜻한 겨울 또는 여름 폭염의 기간, Temperature·HDD·CDD 기반 강도, 진입 재고, 타 에너지원 흡수 가능성, Peak 시점·패턴이 불확실할 때 사용', NULL, '[{"parameter_name":"Temperature","role":"primary","applicability":"국가·연·월별 평균 기온(°C) 최종 절대값 조정","support_status":"executable"},{"parameter_name":"HDD","role":"alternative","applicability":"국가·연·월별 난방도일 조정 경로","support_status":"executable"},{"parameter_name":"CDD","role":"alternative","applicability":"국가·연·월별 냉방도일 조정 경로","support_status":"executable"}]', 'v4', 'Y', 'model-impact-lever-canonical-v4', 'N', 'system', '2026-08-11T10:34:41.803263'),
        (2, 'power_generation_mix', 'demand', '발전 믹스', '가스·원자력·재생에너지·석탄 발전의 가동률, 설비용량 또는 발전 비중 변화에 따른 LNG 발전 수요 변화', '발전원별 영향 기간, Capacity 변화 규모, 단발·구조적 변동, 타 에너지원 흡수 가능성, 발생·회복 패턴을 분기할 때 사용', NULL, '[{"parameter_name":"PowerMix","role":"primary","applicability":"국가·연·에너지원별 발전 비중 최종값 조정","support_status":"executable"}]', 'v4', 'Y', 'model-impact-lever-canonical-v4', 'N', 'system', '2026-08-11T10:34:41.803263'),
        (3, 'economic_activity', 'demand', '경제 활동', 'GDP·PMI 등 국가별 경기 변동에 따른 산업·발전 부문의 LNG 수요 변화', '대상 국가의 경기 확장·둔화 방향과 기간, 경기 강도, LNG 수요 영향 규모가 불확실할 때 사용', NULL, '[{"parameter_name":"GDP","role":"primary","applicability":"국가·연도별 실질 GDP 성장률 최종값 조정","support_status":"executable"},{"parameter_name":"PMI","role":"alternative","applicability":"국가·연·월별 산업 경기 PMI 절대지수 조정","support_status":"executable"},{"parameter_name":"Population","role":"alternative","applicability":"인구·이민·인구전망 변화가 Scenario 또는 Event 근거에 명시된 경우에만 국가·연도별 인구(천 명) 최종 절대값을 조정; 일반 경기 변화에는 GDP·PMI를 우선","support_status":"executable"}]', 'v4', 'Y', 'model-impact-lever-canonical-v4', 'N', 'system', '2026-08-11T10:34:41.803263'),
        (4, 'direct_gas_demand', 'demand', '직접 가스 수요', '산업·도시가스·수송 부문의 직접 LNG·가스 소비 변화', '21개 Event Type 중 직접 대응 유형은 없으며, 경제 활동이나 발전 믹스로 설명되지 않는 수요 정책·절감·연료 전환의 기간, 영향 강도, 구조성이 핵심일 때 제한적으로 사용', NULL, '[{"parameter_name":"User-Adjusted Gas Demand","role":"primary","applicability":"경제 활동·발전 믹스로 설명되지 않는 직접 수요 정책, 절감 또는 연료 전환을 국가·연·월·수요 하위부문별 가스 수요(BCM) 최종 절대값으로 조정","support_status":"executable"}]', 'v4', 'Y', 'model-impact-lever-canonical-v4', 'N', 'system', '2026-08-11T10:34:41.803263'),
        (5, 'upstream_production', 'supply', 'Upstream 생산', '기존 가스전의 생산량·가동률 증감과 차질 후 회복에 따른 LNG 공급 변화', '기간, Nameplate 대비 Utilization 변화 폭, 급격·점진 발생, 급격·점진·영구 회복, 대체 가스 공급 가능성을 분기할 때 사용', NULL, '[{"parameter_name":"SupplyDisruption","role":"primary","applicability":"국가·연·월별 upstream 가스 공급량(Bcm) 최종값 조정","support_status":"executable"}]', 'v4', 'Y', 'model-impact-lever-canonical-v4', 'N', 'system', '2026-08-11T10:34:41.803263'),
        (6, 'liquefaction_availability', 'supply', '액화시설 가용성', '기존 LNG 액화·수출 터미널의 가동률·생산량 변동과 신규 수출 터미널의 COD·Ramp-up 일정 변화', '기존 플랜트·Train의 기간, Utilization 변화량, 발생·회복 패턴, 대체 LNG 공급 가능성 또는 신규 설비의 COD, Ramp-up 완료 시점·패턴·도달 가동률이 불확실할 때 사용', NULL, '[{"parameter_name":"LiqUtilAdjustment","role":"primary","applicability":"기존 액화 Plant Train의 단기·부분 차질 또는 회복을 월별 가동률 최종값으로 조정","support_status":"executable"},{"parameter_name":"LiqProdAdjustment","role":"alternative","applicability":"대폭·영구 생산 손실 또는 신규 Train ramp-up을 월별 생산량 최종값으로 직접 조정","support_status":"executable"}]', 'v4', 'Y', 'model-impact-lever-canonical-v4', 'N', 'system', '2026-08-11T10:34:41.803263'),
        (7, 'regasification_capacity', 'supply', '재기화 수용력', '수입 터미널의 재기화 처리 가능 물량과 신규 수입 터미널의 COD·Ramp-up 일정 변화', '신규 수입 터미널의 COD·Ramp-up 완료 시점과 도달 가동률 또는 자연재해로 인한 수입 시설의 차질 강도·회복 패턴이 수요 흡수력을 제한할 때 사용', NULL, '[{"parameter_name":"RegasAdjustment","role":"primary","applicability":"재기화 플랜트·연·월별 처리용량 최종값 조정 경로","support_status":"executable"}]', 'v4', 'Y', 'model-impact-lever-canonical-v4', 'N', 'system', '2026-08-11T10:34:41.803263'),
        (8, 'natural_disaster_disruption', 'supply', '미국 GoM 허리케인 차질', '미국 Gulf of Mexico 허리케인이 승인된 액화 또는 upstream 시설에 일으키는 월별 물리적 공급 차질', '미국 Gulf of Mexico 허리케인으로 강도 1~4, 적용 Year/Month, 승인된 영향 시설을 식별할 수 있을 때만 사용한다. 태풍·지진 등 기타 자연재해는 영향 시설에 따라 upstream 생산, 액화시설, 재기화 또는 파이프라인 레버를 사용한다.', NULL, '[{"parameter_name":"HurricaneIntensity","role":"primary","applicability":"미국 Gulf of Mexico 허리케인의 강도 1~4와 적용 Year/Month를, 승인된 액화 또는 upstream 영향 시설에 한해 조정","support_status":"executable"}]', 'v4', 'Y', 'model-impact-lever-canonical-v4', 'N', 'system', '2026-08-11T10:34:41.803263'),
        (9, 'pipeline_capacity', 'supply', '파이프라인 수송력', 'PNG 파이프라인 송출 가동률·수송용량의 단발적·구조적 변화와 타 파이프라인 노선 대체', '기간, 대상 Pipeline과 From/To, 송출용량 대비 변화 폭, 단발·구조적 여부, 발생·회복 패턴 또는 타 파이프라인 대체를 분기할 때 사용한다. LNG 전환만 설명된 경우 액화시설 가용성 레버를 사용한다.', NULL, '[{"parameter_name":"PipelineAdjustment","role":"primary","applicability":"Pipeline·From/To·연·월별 송출용량(Bcm/y) 최종값 또는 타 파이프라인 대체를 조정; LNG 전환만인 경우 액화시설 가용성 경로를 사용","support_status":"executable"}]', 'v4', 'Y', 'model-impact-lever-canonical-v4', 'N', 'system', '2026-08-11T10:34:41.803263'),
        (10, 'shipping_cost', 'trade', '해상 운송비', '선복 수급, 항로 차질, 연료비, 계절성, 지정학·제재로 인한 LNG·원유 선박 운임과 부대 운송비 변화', '해상 운임의 기간, 변동 폭, 급격·점진 진행, 단발·구조적 여부를 분기하거나 항로·지정학·제재 충격의 운송비 효과를 정량 반영할 때 사용', NULL, '[{"parameter_name":"ShippingCost","role":"primary","applicability":"영향 범위·연도별 해상 운송비 절대값 조정 경로","support_status":"executable"}]', 'v4', 'Y', 'model-impact-lever-canonical-v4', 'N', 'system', '2026-08-11T10:34:41.803263'),
        (11, 'route_disruption', 'trade', '항로 제약', '운하·해협·항만의 혼잡·봉쇄·운항 차질·우회로 발생하는 LNG 화물 흐름의 지연과 왜곡', '기간, 화물 흐름 차질 강도, 우회·재라우팅 가능성, 운송 지연 규모 또는 지정학·제재에 따른 운송 차질 강도가 불확실할 때 사용', NULL, '[{"parameter_name":"ShippingCost","role":"primary","applicability":"항로 우회·지연에 따른 영향 범위·연도별 운송비 효과 조정 경로","support_status":"executable"}]', 'v4', 'Y', 'model-impact-lever-canonical-v4', 'N', 'system', '2026-08-11T10:34:41.803263'),
        (12, 'contract_volume', 'trade', '계약 물량', '대규모 장기계약의 분쟁·취소·재협상과 거래 제한으로 현물시장에 유입되거나 이탈하는 계약 물량 변화', '거래 규모와 시장 영향 지속성 또는 지정학·제재 시 일부·전체 계약 취소 여부가 지역별 가용 화물을 바꿀 때 사용', NULL, '[{"parameter_name":"VolumeCancelled","role":"primary","applicability":"계약 취소·해지로 시장에서 이탈하는 물량을 From/To 국가·연도별 취소 물량(BCM) 최종 절대값으로 조정","support_status":"executable"},{"parameter_name":"PNG Contract Volume","role":"alternative","applicability":"PNG 장기계약의 재협상·재개·감액처럼 취소가 아닌 계약 총량 변화를 From/To 국가·연도별 PNG 계약 물량(BCM) 최종 절대값으로 조정","support_status":"executable"}]', 'v4', 'Y', 'model-impact-lever-canonical-v4', 'N', 'system', '2026-08-11T10:34:41.803263'),
        (13, 'trade_restriction', 'trade', '거래 제한', '지정학적 갈등, 정부 제재, 관세, 수출입·목적지 제한 및 정책·규제로 인한 LNG 거래 가능 물량 변화', '적용 기간, 시행 단계, 운송·공급 차질 강도와 회복 패턴, 대체 공급·PowerMix 대응, 계약 취소 범위가 지역 간 화물 흐름을 제한할 때 사용', NULL, '[{"parameter_name":"RemainingUnrestrictedAmount","role":"primary","applicability":"제재·관세·수출입 또는 목적지 제한 이후 남는 거래 가능 물량을 From/To 국가·연도별 BCM 최종 절대값으로 조정","support_status":"executable"},{"parameter_name":"VolumeCancelled","role":"alternative","applicability":"거래 제한이 일부 또는 전체 계약의 명시적 취소로 이어지는 경우 From/To 국가·연도별 취소 물량(BCM) 최종 절대값으로 조정","support_status":"executable"}]', 'v4', 'Y', 'model-impact-lever-canonical-v4', 'N', 'system', '2026-08-11T10:34:41.803263'),
        (14, 'inventory_condition', 'price_only', '재고 여건', '평년 대비 LNG·PNG 재고 수준, 주입·인출 여력과 비축 정책 변화가 현물 구매 압력 및 가격 민감도에 미치는 영향', '평년 대비 5단계 재고 수준, 지속·회복 기간, 비축 정책, Spot 구매 영향 또는 한파·폭염 진입 재고와 Injection 패턴을 가격 조건으로 반영할 때 사용', NULL, '[]', 'v4', 'Y', 'model-impact-lever-canonical-v4', 'N', 'system', '2026-08-11T10:34:41.803263'),
        (15, 'regional_price_spread', 'price_only', '지역 가격 스프레드', 'JKM·TTF·Henry Hub 등 가격 인덱스 간 Spread의 비정상적·구조적 변화와 그에 따른 차익거래 유인 변화', '기간, 대상 Spread의 확대·축소 방향, 변동 폭, 단발·구조적 여부가 화물 유인과 지역별 가격을 차별화할 때 사용', NULL, '[]', 'v4', 'Y', 'model-impact-lever-canonical-v4', 'N', 'system', '2026-08-11T10:34:41.803263'),
        (16, 'financial_market_sentiment', 'price_only', '금융시장 심리', '헷지 포지션 재편, 환율·금리 변동과 위험 프리미엄이 시장 유동성, 수입국 구매력 및 단기 LNG 가격에 미치는 간접 영향', '거래·헷징의 규모·지속성 또는 금리·통화의 변동 폭·지속성이 실물 수급모델 입력으로 직접 연결되지 않지만 가격 범위와 구매 여건을 바꿀 때 사용', NULL, '[]', 'v4', 'Y', 'model-impact-lever-canonical-v4', 'N', 'system', '2026-08-11T10:34:41.803263');

    SELECT COUNT(*) INTO v_count FROM tmm_mi_model_param_m;
    IF v_count <> 21 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'master precondition: expected 21 rows';
    END IF;

    SELECT COUNT(*) INTO v_bad
      FROM tmm_mi_model_param_m AS live
      LEFT JOIN _mpv4_snapshot_master AS old USING (model_param_id)
      LEFT JOIN _mpv4_canonical_master AS final USING (model_param_id)
     WHERE old.model_param_id IS NULL OR final.model_param_id IS NULL
        OR NOT (live.`crt_usr_logn_id` <=> old.`crt_usr_logn_id` AND live.`crt_dtm` <=> old.`crt_dtm`)
        OR NOT (
            (live.`use_yn` <=> old.`use_yn` AND live.`parameter_name` <=> old.`parameter_name` AND live.`parameter_hint` <=> old.`parameter_hint` AND live.`model_file` <=> old.`model_file` AND live.`model_sheet` <=> old.`model_sheet` AND live.`model_table` <=> old.`model_table` AND live.`semantic_axes` <=> old.`semantic_axes` AND live.`basecase_read_mode` <=> old.`basecase_read_mode` AND live.`basecase_header_row` <=> old.`basecase_header_row` AND live.`basecase_data_start_row` <=> old.`basecase_data_start_row` AND live.`basecase_column_roles` <=> old.`basecase_column_roles` AND live.`basecase_row_filter` <=> old.`basecase_row_filter` AND live.`basecase_year_row` <=> old.`basecase_year_row` AND live.`basecase_month_row` <=> old.`basecase_month_row` AND live.`basecase_period_row` <=> old.`basecase_period_row` AND live.`basecase_value_start_col` <=> old.`basecase_value_start_col` AND live.`basecase_value_end_col` <=> old.`basecase_value_end_col` AND live.`basecase_stop_rule` <=> old.`basecase_stop_rule` AND live.`mod_usr_logn_id` <=> old.`mod_usr_logn_id` AND live.`del_yn` <=> old.`del_yn`)
            OR (live.`use_yn` <=> final.`use_yn` AND live.`parameter_name` <=> final.`parameter_name` AND live.`parameter_hint` <=> final.`parameter_hint` AND live.`model_file` <=> final.`model_file` AND live.`model_sheet` <=> final.`model_sheet` AND live.`model_table` <=> final.`model_table` AND live.`semantic_axes` <=> final.`semantic_axes` AND live.`basecase_read_mode` <=> final.`basecase_read_mode` AND live.`basecase_header_row` <=> final.`basecase_header_row` AND live.`basecase_data_start_row` <=> final.`basecase_data_start_row` AND live.`basecase_column_roles` <=> final.`basecase_column_roles` AND live.`basecase_row_filter` <=> final.`basecase_row_filter` AND live.`basecase_year_row` <=> final.`basecase_year_row` AND live.`basecase_month_row` <=> final.`basecase_month_row` AND live.`basecase_period_row` <=> final.`basecase_period_row` AND live.`basecase_value_start_col` <=> final.`basecase_value_start_col` AND live.`basecase_value_end_col` <=> final.`basecase_value_end_col` AND live.`basecase_stop_rule` <=> final.`basecase_stop_rule` AND live.`mod_usr_logn_id` <=> final.`mod_usr_logn_id` AND live.`del_yn` <=> final.`del_yn`)
        );
    IF v_bad <> 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'master precondition: row is neither pre-v4 nor canonical-v4';
    END IF;

    SELECT COUNT(*) INTO v_count FROM tmm_mi_model_param_dimension_map;
    IF v_count <> 128 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'mapping precondition: AS-IS row count changed';
    END IF;

    SELECT COUNT(*) INTO v_bad
      FROM tmm_mi_model_param_dimension_map AS live
      LEFT JOIN _mpv4_snapshot_mapping AS old
        ON live.model_param_dimension_map_id = old.model_param_dimension_map_id
     WHERE old.model_param_dimension_map_id IS NULL
        OR NOT (live.`use_yn` <=> old.`use_yn` AND live.`event_type_l2_id` <=> old.`event_type_l2_id` AND live.`dimension_key` <=> old.`dimension_key` AND live.`dimension_label` <=> old.`dimension_label` AND live.`mapping_method` <=> old.`mapping_method` AND live.`model_param_id` <=> old.`model_param_id` AND live.`comment` <=> old.`comment` AND live.`crt_usr_logn_id` <=> old.`crt_usr_logn_id` AND live.`crt_dtm` <=> old.`crt_dtm` AND live.`mod_usr_logn_id` <=> old.`mod_usr_logn_id` AND live.`mod_dtm` <=> old.`mod_dtm` AND live.`del_yn` <=> old.`del_yn`);
    IF v_bad <> 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'mapping precondition: AS-IS legacy mapping changed';
    END IF;

    SELECT COUNT(*) INTO v_count FROM tmm_mi_model_impact_lever_m;
    IF v_count <> 16 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Impact Lever precondition: expected 16 rows';
    END IF;

    SELECT COUNT(*) INTO v_bad
      FROM tmm_mi_model_impact_lever_m AS live
      LEFT JOIN _mpv4_snapshot_lever AS old USING (impact_lever_id, lever_code)
      LEFT JOIN _mpv4_canonical_lever AS final USING (impact_lever_id, lever_code)
     WHERE old.impact_lever_id IS NULL OR final.impact_lever_id IS NULL
        OR NOT (live.`crt_usr_logn_id` <=> old.`crt_usr_logn_id` AND live.`crt_dtm` <=> old.`crt_dtm`)
        OR NOT (
            (live.`domain` <=> old.`domain` AND live.`label` <=> old.`label` AND live.`description` <=> old.`description` AND live.`applicability_hint` <=> old.`applicability_hint` AND live.`parent_lever_code` <=> old.`parent_lever_code` AND live.`parameter_bindings` <=> old.`parameter_bindings` AND live.`catalog_version` <=> old.`catalog_version` AND live.`use_yn` <=> old.`use_yn` AND live.`mod_usr_logn_id` <=> old.`mod_usr_logn_id` AND live.`del_yn` <=> old.`del_yn`)
            OR (live.`domain` <=> final.`domain` AND live.`label` <=> final.`label` AND live.`description` <=> final.`description` AND live.`applicability_hint` <=> final.`applicability_hint` AND live.`parent_lever_code` <=> final.`parent_lever_code` AND live.`parameter_bindings` <=> final.`parameter_bindings` AND live.`catalog_version` <=> final.`catalog_version` AND live.`use_yn` <=> final.`use_yn` AND live.`mod_usr_logn_id` <=> final.`mod_usr_logn_id` AND live.`del_yn` <=> final.`del_yn`)
        );
    IF v_bad <> 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Impact Lever precondition: row is neither pre-v4 nor canonical-v4';
    END IF;

    UPDATE tmm_mi_model_param_m AS live
    JOIN _mpv4_canonical_master AS final USING (model_param_id)
       SET live.use_yn = final.use_yn,
           live.parameter_name = final.parameter_name,
           live.parameter_hint = final.parameter_hint,
           live.model_file = final.model_file,
           live.model_sheet = final.model_sheet,
           live.model_table = final.model_table,
           live.semantic_axes = final.semantic_axes,
           live.basecase_read_mode = final.basecase_read_mode,
           live.basecase_header_row = final.basecase_header_row,
           live.basecase_data_start_row = final.basecase_data_start_row,
           live.basecase_column_roles = final.basecase_column_roles,
           live.basecase_row_filter = final.basecase_row_filter,
           live.basecase_year_row = final.basecase_year_row,
           live.basecase_month_row = final.basecase_month_row,
           live.basecase_period_row = final.basecase_period_row,
           live.basecase_value_start_col = final.basecase_value_start_col,
           live.basecase_value_end_col = final.basecase_value_end_col,
           live.basecase_stop_rule = final.basecase_stop_rule,
           live.mod_usr_logn_id = final.mod_usr_logn_id,
           live.mod_dtm = CURRENT_TIMESTAMP(6),
           live.del_yn = final.del_yn;

    UPDATE tmm_mi_model_impact_lever_m AS live
    JOIN _mpv4_canonical_lever AS final USING (impact_lever_id, lever_code)
       SET live.domain = final.domain,
           live.label = final.label,
           live.description = final.description,
           live.applicability_hint = final.applicability_hint,
           live.parent_lever_code = final.parent_lever_code,
           live.parameter_bindings = final.parameter_bindings,
           live.catalog_version = final.catalog_version,
           live.use_yn = final.use_yn,
           live.mod_usr_logn_id = final.mod_usr_logn_id,
           live.mod_dtm = CURRENT_TIMESTAMP(6),
           live.del_yn = final.del_yn;

    SELECT COUNT(*) INTO v_bad
      FROM tmm_mi_model_param_m AS live
      JOIN _mpv4_canonical_master AS final USING (model_param_id)
     WHERE NOT (live.`use_yn` <=> final.`use_yn` AND live.`parameter_name` <=> final.`parameter_name` AND live.`parameter_hint` <=> final.`parameter_hint` AND live.`model_file` <=> final.`model_file` AND live.`model_sheet` <=> final.`model_sheet` AND live.`model_table` <=> final.`model_table` AND live.`semantic_axes` <=> final.`semantic_axes` AND live.`basecase_read_mode` <=> final.`basecase_read_mode` AND live.`basecase_header_row` <=> final.`basecase_header_row` AND live.`basecase_data_start_row` <=> final.`basecase_data_start_row` AND live.`basecase_column_roles` <=> final.`basecase_column_roles` AND live.`basecase_row_filter` <=> final.`basecase_row_filter` AND live.`basecase_year_row` <=> final.`basecase_year_row` AND live.`basecase_month_row` <=> final.`basecase_month_row` AND live.`basecase_period_row` <=> final.`basecase_period_row` AND live.`basecase_value_start_col` <=> final.`basecase_value_start_col` AND live.`basecase_value_end_col` <=> final.`basecase_value_end_col` AND live.`basecase_stop_rule` <=> final.`basecase_stop_rule` AND live.`mod_usr_logn_id` <=> final.`mod_usr_logn_id` AND live.`del_yn` <=> final.`del_yn`);
    IF v_bad <> 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'read-back: master canonical-v4 values mismatch';
    END IF;

    SELECT COUNT(*) INTO v_bad
      FROM tmm_mi_model_impact_lever_m AS live
      JOIN _mpv4_canonical_lever AS final USING (impact_lever_id, lever_code)
     WHERE NOT (live.`domain` <=> final.`domain` AND live.`label` <=> final.`label` AND live.`description` <=> final.`description` AND live.`applicability_hint` <=> final.`applicability_hint` AND live.`parent_lever_code` <=> final.`parent_lever_code` AND live.`parameter_bindings` <=> final.`parameter_bindings` AND live.`catalog_version` <=> final.`catalog_version` AND live.`use_yn` <=> final.`use_yn` AND live.`mod_usr_logn_id` <=> final.`mod_usr_logn_id` AND live.`del_yn` <=> final.`del_yn`);
    IF v_bad <> 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'read-back: Impact Lever canonical-v4 values mismatch';
    END IF;

    SELECT COUNT(*) INTO v_bad
      FROM tmm_mi_model_param_dimension_map AS live
      LEFT JOIN _mpv4_snapshot_mapping AS old USING (model_param_dimension_map_id)
     WHERE old.model_param_dimension_map_id IS NULL
        OR NOT (live.`use_yn` <=> old.`use_yn` AND live.`event_type_l2_id` <=> old.`event_type_l2_id` AND live.`dimension_key` <=> old.`dimension_key` AND live.`dimension_label` <=> old.`dimension_label` AND live.`mapping_method` <=> old.`mapping_method` AND live.`model_param_id` <=> old.`model_param_id` AND live.`comment` <=> old.`comment` AND live.`crt_usr_logn_id` <=> old.`crt_usr_logn_id` AND live.`crt_dtm` <=> old.`crt_dtm` AND live.`mod_usr_logn_id` <=> old.`mod_usr_logn_id` AND live.`mod_dtm` <=> old.`mod_dtm` AND live.`del_yn` <=> old.`del_yn`);
    IF v_bad <> 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'read-back: AS-IS legacy mapping changed';
    END IF;

    SELECT COUNT(*) INTO v_count
      FROM tmm_mi_model_param_m
     WHERE use_yn = 'Y' AND del_yn = 'N';
    IF v_count <> 16 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'invariant: expected exactly 16 active parameters';
    END IF;

    SELECT COUNT(*) INTO v_bad
      FROM tmm_mi_model_param_m
     WHERE (use_yn = 'Y' AND del_yn = 'N')
       <> (parameter_name IN ('GDP', 'HurricaneIntensity', 'LiqProdAdjustment', 'LiqUtilAdjustment', 'PMI', 'PNG Contract Volume', 'PipelineAdjustment', 'Population', 'PowerMix', 'RegasAdjustment', 'RemainingUnrestrictedAmount', 'ShippingCost', 'SupplyDisruption', 'Temperature', 'User-Adjusted Gas Demand', 'VolumeCancelled'));
    IF v_bad <> 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'invariant: active parameter name set mismatch';
    END IF;

    SELECT COUNT(*) INTO v_bad
      FROM tmm_mi_model_param_dimension_map AS d
      LEFT JOIN tmm_mi_model_param_m AS m ON m.model_param_id = d.model_param_id
     WHERE d.use_yn <> 'Y' OR d.del_yn <> 'N'
        OR (d.model_param_id IS NOT NULL
            AND (m.model_param_id IS NULL OR m.use_yn <> 'Y' OR m.del_yn <> 'N'))
        OR (d.mapping_method IN ('direct', 'routing') AND d.model_param_id IS NULL);
    IF v_bad <> 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'invariant: invalid legacy mapping reference/state';
    END IF;

    SELECT COUNT(*) INTO v_bad
      FROM tmm_mi_model_param_dimension_map AS d
     WHERE NOT EXISTS (
            SELECT 1
              FROM tmm_mi_scenario_dimension_template_m AS t
              JOIN JSON_TABLE(
                    t.template_json,
                    '$[*]' COLUMNS (dimension_key VARCHAR(150) PATH '$.dim_key')
                   ) AS jt
                ON jt.dimension_key = d.dimension_key
             WHERE t.event_type_l2_id = d.event_type_l2_id
               AND t.del_yn = 'N'
       );
    IF v_bad <> 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'invariant: mapping key missing from active template';
    END IF;

    SELECT COUNT(*) INTO v_bad
      FROM tmm_mi_model_impact_lever_m
     WHERE catalog_version <> 'v4' OR use_yn <> 'Y' OR del_yn <> 'N'
        OR domain NOT IN ('demand', 'supply', 'trade', 'price_only')
        OR JSON_TYPE(parameter_bindings) <> 'ARRAY';
    IF v_bad <> 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'invariant: invalid Impact Lever v4 row';
    END IF;

    SELECT COUNT(*) INTO v_count
      FROM tmm_mi_model_impact_lever_m AS lever
      JOIN JSON_TABLE(
            lever.parameter_bindings,
            '$[*]' COLUMNS (
                parameter_name VARCHAR(150) PATH '$.parameter_name',
                binding_role VARCHAR(30) PATH '$.role',
                applicability TEXT PATH '$.applicability',
                support_status VARCHAR(30) PATH '$.support_status'
            )
           ) AS binding;
    IF v_count <> 20 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'invariant: expected 20 raw binding occurrences';
    END IF;

    SELECT COUNT(*) INTO v_bad
      FROM tmm_mi_model_impact_lever_m AS lever
      JOIN JSON_TABLE(
            lever.parameter_bindings,
            '$[*]' COLUMNS (
                parameter_name VARCHAR(150) PATH '$.parameter_name',
                binding_role VARCHAR(30) PATH '$.role',
                applicability TEXT PATH '$.applicability',
                support_status VARCHAR(30) PATH '$.support_status'
            )
           ) AS binding
      LEFT JOIN tmm_mi_model_param_m AS parameter_master
        ON parameter_master.parameter_name = binding.parameter_name
     WHERE parameter_master.model_param_id IS NULL
        OR parameter_master.del_yn <> 'N'
        OR binding.binding_role NOT IN ('primary', 'alternative')
        OR binding.applicability IS NULL OR TRIM(binding.applicability) = ''
        OR binding.support_status <> 'executable';
    IF v_bad <> 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'invariant: invalid Impact Lever binding';
    END IF;

    SELECT COUNT(*) INTO v_count
      FROM tmm_mi_model_impact_lever_m AS lever
      JOIN JSON_TABLE(
            lever.parameter_bindings,
            '$[*]' COLUMNS (parameter_name VARCHAR(150) PATH '$.parameter_name')
           ) AS binding
      JOIN tmm_mi_model_param_m AS parameter_master
        ON parameter_master.parameter_name = binding.parameter_name
       AND parameter_master.use_yn = 'Y'
       AND parameter_master.del_yn = 'N';
    IF v_count <> 18 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'invariant: expected 18 effective executable bindings';
    END IF;

    SELECT COUNT(DISTINCT binding.parameter_name) INTO v_count
      FROM tmm_mi_model_impact_lever_m AS lever
      JOIN JSON_TABLE(
            lever.parameter_bindings,
            '$[*]' COLUMNS (parameter_name VARCHAR(150) PATH '$.parameter_name')
           ) AS binding
      JOIN tmm_mi_model_param_m AS parameter_master
        ON parameter_master.parameter_name = binding.parameter_name
       AND parameter_master.use_yn = 'Y'
       AND parameter_master.del_yn = 'N';
    IF v_count <> 16 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'invariant: expected 16 unique executable parameters';
    END IF;

    SELECT COUNT(*) INTO v_count
      FROM tmm_mi_model_impact_lever_m AS lever
      JOIN JSON_TABLE(
            lever.parameter_bindings,
            '$[*]' COLUMNS (parameter_name VARCHAR(150) PATH '$.parameter_name')
           ) AS binding
      JOIN tmm_mi_model_param_m AS parameter_master
        ON parameter_master.parameter_name = binding.parameter_name
       AND parameter_master.use_yn = 'N'
       AND parameter_master.del_yn = 'N';
    IF v_count <> 2 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'invariant: expected two inactive capability bindings';
    END IF;

    SELECT SHA2(
               GROUP_CONCAT(
                   SHA2(CAST(JSON_OBJECT(
                       'applicability_hint', lever.applicability_hint,
                       'catalog_version', lever.catalog_version,
                       'description', lever.description,
                       'domain', lever.domain,
                       'label', lever.label,
                       'lever_code', lever.lever_code,
                       'parameter_bindings', JSON_EXTRACT(lever.parameter_bindings, '$'),
                       'parent_lever_code', lever.parent_lever_code
                   ) AS CHAR), 256)
                   ORDER BY lever.domain, lever.lever_code SEPARATOR ''
               ),
               256
           )
      INTO v_checksum
      FROM tmm_mi_model_impact_lever_m AS lever;

    SELECT SHA2(
               GROUP_CONCAT(
                   SHA2(CAST(JSON_OBJECT(
                       'applicability_hint', lever.applicability_hint,
                       'catalog_version', lever.catalog_version,
                       'description', lever.description,
                       'domain', lever.domain,
                       'label', lever.label,
                       'lever_code', lever.lever_code,
                       'parameter_bindings', JSON_EXTRACT(lever.parameter_bindings, '$'),
                       'parent_lever_code', lever.parent_lever_code
                   ) AS CHAR), 256)
                   ORDER BY lever.domain, lever.lever_code SEPARATOR ''
               ),
               256
           )
      INTO v_expected_checksum
      FROM _mpv4_canonical_lever AS lever;
    -- The Python runner verifies the exact hydrated service checksum
    -- a4af2e5bbb90f3a76e9e0aab3a16091015898031a97a271ebcf35ca67f4dc6cd; this SQL additionally verifies the canonical rows
    -- through exact read-back and all binding invariants above.
    IF v_checksum IS NULL OR v_expected_checksum IS NULL OR v_checksum <> v_expected_checksum THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'invariant: Impact Lever read-back checksum mismatch';
    END IF;

    COMMIT;
    DROP TEMPORARY TABLE IF EXISTS _mpv4_snapshot_master;
    DROP TEMPORARY TABLE IF EXISTS _mpv4_canonical_master;
    DROP TEMPORARY TABLE IF EXISTS _mpv4_snapshot_mapping;
    DROP TEMPORARY TABLE IF EXISTS _mpv4_snapshot_lever;
    DROP TEMPORARY TABLE IF EXISTS _mpv4_canonical_lever;
END//

CALL apply_model_parameter_canonical_v4()//
DROP PROCEDURE apply_model_parameter_canonical_v4//

DELIMITER ;
