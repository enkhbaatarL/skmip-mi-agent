-- Copyright (c) 2026 SK Innovation E&S.
-- Canonical version: model-parameter-canonical-v1
-- Source snapshot: snapshots/external_dev_before_20260807.json
--
-- Run scripts/model_parameter/apply_canonical.py without --apply first for a
-- transactional preflight/diff-safe rollback. This SQL is the explicit commit
-- path for MySQL 8.0 and is safe to rerun only from the captured snapshot or
-- the canonical final state.

DELIMITER //

DROP PROCEDURE IF EXISTS apply_model_parameter_canonical_v1//
CREATE PROCEDURE apply_model_parameter_canonical_v1()
BEGIN
    DECLARE v_bad BIGINT DEFAULT 0;
    DECLARE v_count BIGINT DEFAULT 0;

    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        DROP TEMPORARY TABLE IF EXISTS _mp_canonical_master;
        DROP TEMPORARY TABLE IF EXISTS _mp_master_hash;
        DROP TEMPORARY TABLE IF EXISTS _mp_mapping_hash;
        DROP TEMPORARY TABLE IF EXISTS _mp_canonical_mapping;
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
       FOR UPDATE;

    SELECT scenario_dimension_template_id
      FROM tmm_mi_scenario_dimension_template_m
     ORDER BY scenario_dimension_template_id
       FOR SHARE;

    CREATE TEMPORARY TABLE _mp_canonical_master AS
    SELECT model_param_id, use_yn, parameter_name, parameter_hint, model_file, model_sheet, model_table, semantic_axes, basecase_read_mode, basecase_header_row, basecase_data_start_row, basecase_column_roles, basecase_row_filter, basecase_year_row, basecase_month_row, basecase_period_row, basecase_value_start_col, basecase_value_end_col, basecase_stop_rule, mod_usr_logn_id, del_yn
      FROM tmm_mi_model_param_m
     WHERE 1 = 0;

    INSERT INTO _mp_canonical_master (
        model_param_id, use_yn, parameter_name, parameter_hint, model_file, model_sheet, model_table, semantic_axes, basecase_read_mode, basecase_header_row, basecase_data_start_row, basecase_column_roles, basecase_row_filter, basecase_year_row, basecase_month_row, basecase_period_row, basecase_value_start_col, basecase_value_end_col, basecase_stop_rule, mod_usr_logn_id, del_yn
    ) VALUES
        (1, 'N', 'CDD', 'Country/year-month CDD value (degree-day)', 'Demand', 'WeatherAdjustment', 'table1', '평년 대비 기온편차 변환 — 국가·연·월', 'fixed_columns', 6, 12, 'B:Year,C:Month,D:Country,E:HDD/CDD,G:HDD/CDD', 'E=CDD', NULL, NULL, NULL, NULL, NULL, 'stop_when_all_key_columns_empty', 'model-parameter-canonical-v1', 'N'),
        (2, 'N', 'Coal Futures Price', 'Monthly coal futures price by region (USD/t)', 'Demand', 'CoalGasAdjustment', 'table1', '석탄 선물가격 strip — 지역·월 (Asia=Newcastle, EU=ARA)', 'fixed_columns', 6, 12, 'B:Month-Year,C:Region,E:Coal Futures Price (USD/t)', NULL, NULL, NULL, NULL, NULL, NULL, 'stop_when_all_key_columns_empty', 'model-parameter-canonical-v1', 'N'),
        (3, 'N', 'Gas Futures Price', 'Monthly gas futures price by region (USD/mmbtu)', 'Demand', 'CoalGasAdjustment', 'table2', '가스 선물가격 strip — 지역·월 (Asia=JKM, EU=TTF)', 'fixed_columns', 6, 12, 'H:Month-Year,I:Region,K:Gas Futures Price (USD/mmbtu)', NULL, NULL, NULL, NULL, NULL, NULL, 'stop_when_all_key_columns_empty', 'model-parameter-canonical-v1', 'N'),
        (4, 'Y', 'GDP', '국가·연도별 실질 GDP 전년 대비 성장률의 최종 입력값이다. value는 % change를 소수로 입력한다(0.042=4.2%, -0.015=-1.5%). proposedValue는 basecase 대비 증감폭이 아니라 해당 Country/Year에 적용할 성장률 자체다. basecase가 있으면 기존 성장률과 이벤트에 명시된 GDP 전망·조정폭을 비교해 최종 성장률로 제안한다.', 'Demand', 'GDPPopulationAdjustment', 'table1', 'slot=B:Year(YYYY, 2026~2030), C:Country(국가명; basecase 예: United States, China, Japan, South Korea, Taiwan (China), Belgium, France, Germany, Italy, Netherlands, Spain, India); value=F:% change(+/-), 소수형 전년대비 실질 GDP 성장률', 'fixed_columns', 6, 12, 'B:Year,C:Country,F:% change (+/-)', NULL, NULL, NULL, NULL, NULL, NULL, 'stop_when_all_key_columns_empty', 'model-parameter-canonical-v1', 'N'),
        (5, 'N', 'HDD', 'Country/year-month HDD value (degree-day)', 'Demand', 'WeatherAdjustment', 'table1', '평년 대비 기온편차 변환 — 국가·연·월', 'fixed_columns', 6, 12, 'B:Year,C:Month,D:Country,E:HDD/CDD,G:HDD/CDD', 'E=HDD', NULL, NULL, NULL, NULL, NULL, 'stop_when_all_key_columns_empty', 'model-parameter-canonical-v1', 'N'),
        (6, 'Y', 'PMI', '국가·연월별 PMI 지수의 최종 입력값이다. value는 PMI index 절대값으로 입력한다(예: 49.5). PMI 기준값은 보통 50이며, 50 초과는 경기 확장/생산활동 증가, 50은 중립, 50 미만은 경기 위축/생산활동 감소를 의미한다. 이 모델에서 PMI는 주로 industrial demand, 즉 산업용 가스 수요를 조정하는 경기 민감도 변수다. proposedValue는 basecase 대비 증감폭이 아니라 해당 Country/Year/Month에 적용할 PMI 값 자체다.', 'Demand', 'PMIAdjustment', 'table1', 'slot=B:Year(YYYY, 2026~2030), C:Month(1~12), D:Country(국가명; basecase 예: China, Philippines); value=F:PMI, PMI index 절대값', 'fixed_columns', 6, 13, 'B:Year,C:Month,D:Country,F:PMI', NULL, NULL, NULL, NULL, NULL, NULL, 'stop_when_all_key_columns_empty', 'model-parameter-canonical-v1', 'N'),
        (7, 'Y', 'PowerMix', '국가·연도·에너지원별 발전 믹스 비중의 최종 입력값이다. value는 전체 발전량에서 해당 Energy Source가 차지하는 비중을 소수로 입력한다(0.30=30%). proposedValue는 basecase 대비 증감폭이 아니라 해당 Country/Year/Energy Source에 적용할 최종 비중이다. 현재 basecase는 Gas 위주로 제공되므로, 명확한 전원별 사유가 없으면 Gas 비중 조정을 우선 검토하고 상쇄 전원은 rationale에 설명한다.', 'Demand', 'PowerMixAdjustment', 'table1', 'slot=B:Year(YYYY, 2026~2030), C:Country(국가명; basecase 예: China, Japan, South Korea, Taiwan (China), Germany, France, Italy, Spain, Netherlands, Belgium, United Kingdom), D:Energy Source(Liquids/Hydro/Solar/Wind/Bioenergy/Gas/Coal/Nuclear/Geothermal/Other; basecase 예: Gas); value=F:% Power Mix, 소수형 발전 비중', 'fixed_columns', 6, 12, 'B:Year,C:Country,D:Energy Source,F:% Power Mix', NULL, NULL, NULL, NULL, NULL, NULL, 'stop_when_all_key_columns_empty', 'model-parameter-canonical-v1', 'N'),
        (8, 'Y', 'Temperature', '국가·연월별 평균 기온의 최종 입력값이다. value는 섭씨(°C) 절대값으로 입력한다(예: 2.3, -1.5, 31.0). proposedValue는 basecase 대비 편차가 아니라 해당 Country/Year/Month에 적용할 기온 자체다. 한파는 정상 기온 대비 하향, 폭염은 정상 기온 대비 상향 방향으로 조정한다. 국가별 기후 차이가 크므로 basecase가 없는 경우 다른 국가의 기온 수준을 기준값으로 삼지 않는다.', 'Demand', 'WeatherAdjustment', 'table2', 'slot=K:Year(YYYY, 2026~2030), L:Month(1~12; basecase 예: 1~3), M:Country(국가명; basecase 예: China, Japan, South Korea, Germany, France, Netherlands, Spain, Italy, Belgium, United Kingdom); value=O:Temperature (°C), 섭씨 절대 기온', 'fixed_columns', 6, 12, 'K:Year,L:Month,M:Country,O:Temperature (°C)', NULL, NULL, NULL, NULL, NULL, NULL, 'stop_when_all_key_columns_empty', 'model-parameter-canonical-v1', 'N'),
        (9, 'N', 'User-Adjusted Gas Demand', 'Country/year-month/sub-sector demand overwrite value (BCM)', 'Demand', 'DemandOutputOverwrite', 'table1', '수요 출력 직접 덮어쓰기 — 국가·연·월·Sub-Sector', 'fixed_columns', 7, 8, 'D:Country,E:Year,F:Month,G:Demand Sub-Sector,H:User-Adjusted Gas Demand [BCM]', NULL, NULL, NULL, NULL, NULL, NULL, 'stop_when_all_key_columns_empty', 'model-parameter-canonical-v1', 'N'),
        (10, 'N', 'ElectrificationRate', 'Country/year transportation electrification rate (% new car sales)', 'Demand', 'ElectrificationRateAdjustment', 'table1', '수송 전기화율 (본 21종 직접 해당 적음)', 'fixed_columns', 6, 12, 'B:Year,C:Country,D:Drive Train,F:% New Car Sales', NULL, NULL, NULL, NULL, NULL, NULL, 'stop_when_all_key_columns_empty', 'model-parameter-canonical-v1', 'N'),
        (11, 'Y', 'Population', '국가·연도별 인구의 최종 입력값이다. value는 천 명 단위 절대값으로 입력한다. proposedValue는 basecase 대비 증감폭이 아니라 해당 Country/Year에 적용할 인구 자체다. 인구·이민·인구전망 변화가 event에 명시된 경우에만 사용하고, 일반 경기 변화에는 GDP·PMI를 우선한다.', 'Demand', 'GDPPopulationAdjustment', 'table2', 'slot=J:Year(YYYY, 2026~2030), K:Country(국가명), value=M:Population (Thousands), 천 명 단위 인구 절대값', 'fixed_columns', 6, 12, 'J:Year,K:Country,M:Population (Thousands)', NULL, NULL, NULL, NULL, NULL, NULL, 'stop_when_all_key_columns_empty', 'model-parameter-canonical-v1', 'N'),
        (12, 'Y', 'HurricaneIntensity', '미국 Gulf of Mexico 허리케인의 월별 강도 최종 입력값이다. value는 0~4 정수이며 0은 허리케인 영향 없음, 1~4는 승인된 강도 단계다. event가 GoM 허리케인과 적용 Year/Month를 명시하고 영향 대상 액화 또는 upstream 시설과 연결되는 경우에만 1~4를 제안한다.', 'Supply', '{USA}Hurricanes', 'table1', 'slot=B:Year(YYYY, 2026~2030), C:Month(1~12); value=D:Hurricane intensity(0~4 정수, 0=no hurricane)', 'fixed_columns', 7, 13, 'B:Year,C:Month,D:Hurricane intensity', NULL, NULL, NULL, NULL, NULL, NULL, 'stop_when_all_key_columns_empty', 'model-parameter-canonical-v1', 'N'),
        (13, 'Y', 'LiqProdAdjustment', '액화 Plant Train·월별 LNG 생산량의 최종 절대값이다. value는 Mt LNG/month 단위이며 0 이상이다. LUT 기준값은 월 생산능력 × 이용률로 계산한다. proposedValue는 증감폭이 아니라 해당 Country/LNG Plant/LNG Plant Train/Year/Month의 최종 생산량이며, 대폭·영구 차질이나 신규 Train ramp-up처럼 생산량 직접 override가 필요한 경우에 사용한다.', 'Supply', 'LiqProdAdjustment', 'table1', 'slot=Country, LNG Plant, LNG Plant Train, Year(YYYY), Month(1~12); metadata=Life Cycle Category, Nameplate Capacity (MTPA), Period; value=Production (Mt LNG/month), 월 생산능력×이용률', 'matrix_time_columns', 10, 11, 'B:Country,C:LNG Plant,D:LNG Plant Train,E:Life Cycle Category,F:Nameplate Capacity (MTPA)', NULL, 7, 8, 9, 'G', 'DA', 'stop_when_all_key_columns_empty', 'model-parameter-canonical-v1', 'N'),
        (14, 'Y', 'LiqUtilAdjustment', '액화 Plant Train·월별 가동률의 최종 입력값이다. value는 0~1 소수로 입력한다(1.0=100%, 0.7=70%). 100 같은 percent 표기는 사용하지 않는다. proposedValue는 basecase 대비 증감폭이 아니라 해당 Train/Year/Month에 적용할 가동률 자체다. 기본 범위는 0~1이며, 1 초과는 명확한 근거가 있을 때만 제안한다. Base Case에 존재하는 LNG Plant Train만 수정하고, Country/LNG Plant/Life Cycle Category/Nameplate Capacity는 해당 Train에 종속된 식별 속성으로 맞춘다.', 'Supply', 'LiqUtilAdjustment', 'table1', 'slot=Country(국가명; 예: Algeria, Angola), LNG Plant(예: Arzew GL1Z, Angola LNG), LNG Plant Train(348개 basecase Train 중 선택; 예: Arzew GL1Z T1-T6, Angola LNG T1, Gorgon LNG T1, North West Shelf LNG T1, Sabine Pass LNG Stage 5 Expansion T1), Life Cycle Category(예: Operational), Nameplate Capacity MTPA(숫자; 예: 7.9, 5.2), Year(YYYY), Month(1~12), Period(숫자); value=Utilization Rate, 0~1 소수형 월별 가동률', 'matrix_time_columns', 10, 11, 'B:Country,C:LNG Plant,D:LNG Plant Train,E:Life Cycle Category,F:Nameplate Capacity (MTPA)', NULL, 7, 8, 9, 'G', 'DA', 'stop_when_all_key_columns_empty', 'model-parameter-canonical-v1', 'N'),
        (15, 'Y', 'PipelineAdjustment', '파이프라인·월별 송출능력의 최종 절대값이다. value는 Bcm/y 단위이며 0 이상이다. 연간 LUT capacity를 동일 연도의 12개월 기준값으로 확장한다. proposedValue는 증감폭이 아니라 해당 Pipeline Name/From Country/To Country/Year/Month에 적용할 최종 송출능력이다.', 'Supply', 'PipelineAdjustment', 'table1', 'slot=B:Year(YYYY, 2026~2030), C:Month(1~12), D:Pipeline Name, routing=From Country, To Country; value=H:User adjusted capacity (Bcm/y)', 'fixed_columns', 7, 13, 'B:Year,C:Month,D:Pipeline name,H:User adjusted capacity (Bcm/y)', NULL, NULL, NULL, NULL, NULL, NULL, 'stop_when_all_key_columns_empty', 'model-parameter-canonical-v1', 'N'),
        (16, 'N', 'RegasAdjustment', 'Regasification plant/month capacity absolute value (Mt LNG; >= 0)', 'Supply', 'RegasAdjustment', 'table1', '재기화(수입) 설비 capa override — Continent>Region>Country>Plant·연·월', 'matrix_time_columns', 10, 11, 'B:Continent,C:Region,D:Country,E:Regasification plant,F:Life Cycle Category,G:Nameplate capacity (MTPA)', NULL, 9, 10, NULL, 'H', 'DK', 'stop_when_all_key_columns_empty', 'model-parameter-canonical-v1', 'N'),
        (17, 'Y', 'SupplyDisruption', '국가·연월별 upstream 가스 공급량의 최종 절대값이다. value는 Bcm 단위이며 0 이상이다. LUT 기준값은 BCProduction의 연간 Base case supply를 동일 Province/PNG-LNG의 원본 월별 Seasonality 계수와 곱한 뒤 Country/Year/Month로 합산한다. 계수를 재정규화하지 않는다. proposedValue는 차질량이 아니라 해당 월에 적용할 최종 공급량이다.', 'Supply', 'VolumeAdjustment', 'table2', 'slot=I:Year(YYYY, 2026~2030), J:Month(1~12), K:Country; value=M:Volumes (Bcm), Country별 월 공급량 절대값', 'fixed_columns', 7, 8, 'I:Year,J:Month,K:Country,M:Volumes (Bcm)', NULL, NULL, NULL, NULL, NULL, NULL, 'stop_when_all_key_columns_empty', 'model-parameter-canonical-v1', 'N'),
        (18, 'N', 'PNG Contract Volume', 'From/to country/year PNG contract volume (BCM)', 'Trade', 'MidstreamContractInput', 'table1', 'PNG 계약 물량(Nord Stream 재가동·Pipeline Disruption) — From·To·연', 'fixed_columns', 4, 5, 'A:Year,B:From Country,C:To Country,D:Unadjusted Gross Gas Import [BCM]', NULL, NULL, NULL, NULL, NULL, NULL, 'stop_when_all_key_columns_empty', 'model-parameter-canonical-v1', 'N'),
        (19, 'N', 'RemainingUnrestrictedAmount', 'From/to country/year remaining unrestricted trade volume (BCM)', 'Trade', 'TradeRestrictionInput', 'table1', '계약 취소·통과 제약 — From·To·연', 'fixed_columns', 5, 6, 'B:Year,C:From Country,D:To Country,J:Remaining Unrestricted Amount [BCM]', NULL, NULL, NULL, NULL, NULL, NULL, 'stop_when_all_key_columns_empty', 'model-parameter-canonical-v1', 'N'),
        (20, 'N', 'ShippingCost', 'Yearly user input absolute shipping cost value ($/d)', 'Trade', 'ShippingCostInput', 'table1', 'Charter·Fuel·Suez/Panama Crossing 비용·Disruption 여부 — impact_scope·연', 'fixed_columns', 5, 6, 'B:Year,F:User Input Absolute Value ($/d)', NULL, NULL, NULL, NULL, NULL, NULL, 'stop_when_all_key_columns_empty', 'model-parameter-canonical-v1', 'N'),
        (21, 'N', 'VolumeCancelled', 'From/to country/year cancelled trade volume (BCM)', 'Trade', 'TradeRestrictionInput', 'table1', '계약 취소·통과 제약 — From·To·연', 'fixed_columns', 5, 6, 'B:Year,C:From Country,D:To Country,F:Volume [BCM]', NULL, NULL, NULL, NULL, NULL, NULL, 'stop_when_all_key_columns_empty', 'model-parameter-canonical-v1', 'N');

    CREATE TEMPORARY TABLE _mp_master_hash (
        model_param_id INT UNSIGNED NOT NULL PRIMARY KEY,
        snapshot_hash CHAR(64) NOT NULL,
        canonical_hash CHAR(64) NOT NULL
    );
    INSERT INTO _mp_master_hash VALUES
        (1, '3be54a74a2ba6a4aca722c145dc413490a57e06e7b11d89f3c827d128731a131', '3a70278f93338e053f97d956448f5bf4ac5120ce3c62dbf6460d8614afa57794'),
        (2, '3bcf32611b4aa7d0b41a403305db00d16be291f0e675e1940f83fcb513a99a0c', '1452e67a6080bfcbad4b5b73af2aa850889b3ee02a23ed9a36982d1cb536d378'),
        (3, 'bec48718c824ad78e6886fadd26eb0d2ab13d47886a7ebe235b69061ee48c417', 'b7b2aeec049265333f33cf6a02b0a0b633591a5c9610d560c912af0ff4308fb3'),
        (4, '4a03fd2628a8261af0adf421f27c2c804943173be7ed456ebe63d10cd1a80ecd', '47b29dfc1d314a5e062394fe26f20dc1c3a299c1e2e5b82764fc5e113c409878'),
        (5, 'fdf795753a172f6d5ad4fe7b8da42ee7f2722c9d1127e86cdeb2f78866972884', '208bd3ba354e9120799a76f7efad6483565b1f0405bfa2e4027d4941e7db8319'),
        (6, '08cf821baccbd5096bf64b4104b59d6a4a2610bdb7887b2a73ce7b117263302b', '9d0c6e0fb46c9fb41f25eb48621d6ad92b1bb0bd46b294c2a8d2b7c096f653c0'),
        (7, '1f3825fbf63b095ba9c399193ba2c541388b764055d0a3239d756e2ff0e2e647', 'f87a0fab815ef0f884cef9fa3fbabfd252ae526f71858607075625cf716138c3'),
        (8, '2a187a78975a1bbf768bf4b2b1bc02b47630cb4f093fff8f8fb64545e1a02a73', '258a9e8e2ed5928ce17789dbc5357714ed69aeb2fa7f91b57f06561a06155297'),
        (9, 'dee7e0de3c6ee4b251ebbd1dcc39acb45bbc6b01db86c371be582eee2a9c20cd', '06c6e4cb21c5688bca4758513b714459338992431767ffe7d34327ec19c2aa0a'),
        (10, '31d39315a99f7ec0c8aed79ea71235908a8247b6a84bcc51d28380a45d8baf06', 'f64f0d60fb02d41ca7bd1c33be926bf8f703ab1f9d62dfd706bd23ad331d9792'),
        (11, 'c3f834340a696d1e5bf7af403613b6a96239334332ce14da5dd01fbdd0a3ed1e', 'e5704d0c380b1e314a0a9a9ebb503d85277cfe4f9a63aa1e9d957a043eb9b39d'),
        (12, '82282ff7d67104fe3aa4000bfb56ea60573d678d1691365b767067bf2b9b2765', '8f4507888ab48d0fccacc00856d52311be8aaa82ddad17b4b3df98b344ce0373'),
        (13, 'b65edb03ad659dfc6b2ae81f88359aad02830c6e41d1217712d3e8d4ab422bde', '7c5378858693c5491e1592669daedff332560c101d10d423bfa699c4687e8e8e'),
        (14, 'c8a2b44530e728d9714b7af6d2f1778597323f079e70e9a4646013d80b45cd44', '8be9af7f2e07e7c5363575cdb428fec9428a0af240667470a4bd9fa443f2738a'),
        (15, 'b45fb6d242097d8c8e71559e949a5f9fad46058e907ddc292aa988eba241832f', '872003ccee38158040308cdf8af9fba3dff63d98e075615526b772e45dcd6ed4'),
        (16, 'd10fb8c5e86147783b72bd5c6b4cdd6706901003125f621f18ef3533aecc8bf6', '08344a1232ad33d940581697161e26f89ce6673e77f87c3ee05b17cbf16f3622'),
        (17, '782782ce4f49f23db839691940dd0fc35be35c8fffefb7f7f3d0609741e3ce8c', 'cdc20301072fe57b8700b63aa8d92e7601c13a055cae8ca64e8d3b24c4985980'),
        (18, 'e7fcf9b26f380fe88b2fe4c78b50696a366de4b2d054560787eb5d0c37d725ae', 'c8a274e8350a03e02cbf2c42de13d73134e101593f3b1be903900a66fabdb38a'),
        (19, '7dfba7851b047078658fca5594e8f78be52ad4e4ca97e524f104354ac4d7e472', 'f92cb64a6dee57a56fe2386a418377d68a4f970d3491f41198de206a97bbbe67'),
        (20, 'fd0b805d6fafbf27e4d09d75ba1c57dffdba6c20fe56f4d709556fbda83a73cf', 'fcf912b27b035e9dba1b951f778f9fcdc7fd88388115ae3789bb64c8f2b63f06'),
        (21, '6b041710cccdc83b5e89f52cbfa4e7fbfd609fae74a925f8617122a24b07e429', 'aab4c84e560b1a1538643ea8ae482dfe4b4273022bd7e193c96b78aa73752e1a');

    SELECT COUNT(*) INTO v_count FROM tmm_mi_model_param_m;
    IF v_count <> 21 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'master precondition: expected 21 rows';
    END IF;

    SELECT COUNT(*) INTO v_bad
      FROM tmm_mi_model_param_m AS m
      LEFT JOIN _mp_master_hash AS h ON h.model_param_id = m.model_param_id
     WHERE h.model_param_id IS NULL
        OR SHA2(CONCAT_WS(CHAR(31),
                        COALESCE(CAST(m.use_yn AS CHAR CHARACTER SET utf8mb4), '<NULL>'),
                        COALESCE(CAST(m.parameter_name AS CHAR CHARACTER SET utf8mb4), '<NULL>'),
                        COALESCE(CAST(m.parameter_hint AS CHAR CHARACTER SET utf8mb4), '<NULL>'),
                        COALESCE(CAST(m.model_file AS CHAR CHARACTER SET utf8mb4), '<NULL>'),
                        COALESCE(CAST(m.model_sheet AS CHAR CHARACTER SET utf8mb4), '<NULL>'),
                        COALESCE(CAST(m.model_table AS CHAR CHARACTER SET utf8mb4), '<NULL>'),
                        COALESCE(CAST(m.semantic_axes AS CHAR CHARACTER SET utf8mb4), '<NULL>'),
                        COALESCE(CAST(m.basecase_read_mode AS CHAR CHARACTER SET utf8mb4), '<NULL>'),
                        COALESCE(CAST(m.basecase_header_row AS CHAR CHARACTER SET utf8mb4), '<NULL>'),
                        COALESCE(CAST(m.basecase_data_start_row AS CHAR CHARACTER SET utf8mb4), '<NULL>'),
                        COALESCE(CAST(m.basecase_column_roles AS CHAR CHARACTER SET utf8mb4), '<NULL>'),
                        COALESCE(CAST(m.basecase_row_filter AS CHAR CHARACTER SET utf8mb4), '<NULL>'),
                        COALESCE(CAST(m.basecase_year_row AS CHAR CHARACTER SET utf8mb4), '<NULL>'),
                        COALESCE(CAST(m.basecase_month_row AS CHAR CHARACTER SET utf8mb4), '<NULL>'),
                        COALESCE(CAST(m.basecase_period_row AS CHAR CHARACTER SET utf8mb4), '<NULL>'),
                        COALESCE(CAST(m.basecase_value_start_col AS CHAR CHARACTER SET utf8mb4), '<NULL>'),
                        COALESCE(CAST(m.basecase_value_end_col AS CHAR CHARACTER SET utf8mb4), '<NULL>'),
                        COALESCE(CAST(m.basecase_stop_rule AS CHAR CHARACTER SET utf8mb4), '<NULL>'),
                        COALESCE(CAST(m.mod_usr_logn_id AS CHAR CHARACTER SET utf8mb4), '<NULL>'),
                        COALESCE(CAST(m.del_yn AS CHAR CHARACTER SET utf8mb4), '<NULL>')
                    ), 256) NOT IN (h.snapshot_hash, h.canonical_hash);
    IF v_bad <> 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'master precondition: row is neither snapshot nor canonical';
    END IF;

    SELECT COUNT(*) INTO v_bad
      FROM tmm_mi_model_param_m
     WHERE crt_usr_logn_id <> 'system'
        OR crt_dtm <> TIMESTAMP('2026-08-05 08:30:07.057833');
    IF v_bad <> 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'master precondition: creation audit mismatch';
    END IF;

    CREATE TEMPORARY TABLE _mp_mapping_hash (
        model_param_dimension_map_id INT UNSIGNED NOT NULL PRIMARY KEY,
        snapshot_hash CHAR(64) NOT NULL,
        canonical_hash CHAR(64) NOT NULL
    );
    INSERT INTO _mp_mapping_hash VALUES
        (1, '90a75088121f626f2ffbc0b3ab4d42e87b198044d48bb39574392cc837a44f0c', '90a75088121f626f2ffbc0b3ab4d42e87b198044d48bb39574392cc837a44f0c'),
        (2, 'c1861d0fb29ed17d13c1c11152c772c3c61e1e266d3695882cb8166ff62a2e83', '8dbe9d6319a55f566ca56c136043136bc9c86f58773223ffb52dbbac5bb8763f'),
        (3, '73e387ebf96e7d4b46963c7594219940d60dbe79a014b4a775c62f6ab5e40921', '73e387ebf96e7d4b46963c7594219940d60dbe79a014b4a775c62f6ab5e40921'),
        (4, 'b1d9b7d421af63e7f7d7771f78cc0c83d84126b927b2701eb214be97fc9ad631', 'b1d9b7d421af63e7f7d7771f78cc0c83d84126b927b2701eb214be97fc9ad631'),
        (5, '143265db33aa5bbd79755a231709cc70df3e70ab857db3be14cfbcf687d11eb5', 'c7432f34793e961de8365e6d1ade882c2c190e91b46f0c9c8efddb6858c68a99'),
        (6, '3d288f0abe9719b58a27a181215fd7fbf1c9cdd8b54d1d423b469ce179e02d9d', '3d288f0abe9719b58a27a181215fd7fbf1c9cdd8b54d1d423b469ce179e02d9d'),
        (7, '1ca62315a1ec9ec0e7336412bd623a85ea8985cabd0a1b0b38c1951719298ee0', '1ca62315a1ec9ec0e7336412bd623a85ea8985cabd0a1b0b38c1951719298ee0'),
        (8, '8df7fd285ff59870a5533e450671847d061324704130c9d2b3c74753b85562c0', '8df7fd285ff59870a5533e450671847d061324704130c9d2b3c74753b85562c0'),
        (9, '373df400557f67492abff1247647a7784156bad868a098a6461bee056f12423c', '56a2daa5b183ecb8064165bcca577fb9b1e63ce9ffddb4f9af656d459d331282'),
        (10, '2868c85fb137f39c0dbc4233e3098bdd5630fd3397562b8baf7a4a61f8d1ecfb', '2868c85fb137f39c0dbc4233e3098bdd5630fd3397562b8baf7a4a61f8d1ecfb'),
        (11, 'ab120c3d79340a1100fdc61c66c334137e967953b41c013a3a7427c2d0a0de5d', 'ab120c3d79340a1100fdc61c66c334137e967953b41c013a3a7427c2d0a0de5d'),
        (12, '5867c2121d1ef98a5a6f04a1a65068f57c4d06c52e81c8ca9211bce10fa48027', '5867c2121d1ef98a5a6f04a1a65068f57c4d06c52e81c8ca9211bce10fa48027'),
        (13, 'a0683fff5922032a1195895d01607195f2a2cc23d09be9f7ae42a97e165ce393', 'a0683fff5922032a1195895d01607195f2a2cc23d09be9f7ae42a97e165ce393'),
        (14, '12660b2bffc13f0a529ca628c347d9c9d584f6de8eb6999a52173ae6f2df47e2', '12660b2bffc13f0a529ca628c347d9c9d584f6de8eb6999a52173ae6f2df47e2'),
        (15, 'c5b20fdc68804f8704f862761b42a7557f8ec75232d1b8dcc04b25c4b8d615b9', 'c5b20fdc68804f8704f862761b42a7557f8ec75232d1b8dcc04b25c4b8d615b9'),
        (16, 'ebf2714f26e7619744fb9a07d7d54157725a3eb1b44c1b509ffe6c0194c95464', '19adf7d418a22e349bdced6cf02da0ce6ab71b93f802aaf4475d796631784f4b'),
        (17, 'c78d6e5a5107e5f66f74b193bddf7df244094e6de9bb11c24588fa5f22270cb9', 'c78d6e5a5107e5f66f74b193bddf7df244094e6de9bb11c24588fa5f22270cb9'),
        (18, '3acfd1cdd09159c0ac3ca6f8731e481ce86b91789ed005d1211d0e2b249d9aed', 'c394b5d5d66e89f44e9fcfa4efc9a1a6c8eecbdfb857aba9c2f56793844fd0f7'),
        (19, '3acfd1cdd09159c0ac3ca6f8731e481ce86b91789ed005d1211d0e2b249d9aed', '3acfd1cdd09159c0ac3ca6f8731e481ce86b91789ed005d1211d0e2b249d9aed'),
        (20, 'f03158db020f819e2b648f79c8682db6c955151e8b8f6f46a3edadaa748aff29', 'f03158db020f819e2b648f79c8682db6c955151e8b8f6f46a3edadaa748aff29'),
        (21, 'd7c1dbb47823c40eaf4c6b15b2c85fbb428242a60934cd5e1cd5af7063cad37a', 'd7c1dbb47823c40eaf4c6b15b2c85fbb428242a60934cd5e1cd5af7063cad37a'),
        (22, 'd7d03bbcd1e4ccfbdcdbb14dc056d28c575095111e5e0cbed94fc9dbf2a92347', 'd7d03bbcd1e4ccfbdcdbb14dc056d28c575095111e5e0cbed94fc9dbf2a92347'),
        (23, 'a45e764b26b5c4f1a2ae565eb4b97fdc3ecac4f12617dd5c66fb39f1a26853d2', '320cf1b386bff19df2a5edbed811658af3caa59254e9e758791e6592bbed54b6'),
        (24, 'a347b164b036c647d855d88afe1f49c1c001e7dfb693f06a51461a737f4327b6', 'a347b164b036c647d855d88afe1f49c1c001e7dfb693f06a51461a737f4327b6'),
        (25, '2aea74ce7782d8102f9863fdb184d2d79d04b43e0369d525c94d6e8e7ed83266', '2aea74ce7782d8102f9863fdb184d2d79d04b43e0369d525c94d6e8e7ed83266'),
        (26, '441e8755d9cd0c6c889cc503b508da93b6de30d5963f09768bda31e66d9633a9', '441e8755d9cd0c6c889cc503b508da93b6de30d5963f09768bda31e66d9633a9'),
        (27, '029f9a7b6839ddbfb232e067789f0cfff5bb5b95beb1cd6cc9101d839b838eb1', '029f9a7b6839ddbfb232e067789f0cfff5bb5b95beb1cd6cc9101d839b838eb1'),
        (28, 'f10b41e0730b620a4bbdb57e5636dffd970c8c784a467c4a191ecf48ff73c713', 'f10b41e0730b620a4bbdb57e5636dffd970c8c784a467c4a191ecf48ff73c713'),
        (29, '9b1d86b0da2eb1baa6dec6657ae19296d7c04a78081f5a929c88c38ec8607ae6', '9b1d86b0da2eb1baa6dec6657ae19296d7c04a78081f5a929c88c38ec8607ae6'),
        (30, '9c0c3b33c171185a632fd4b809d35b2b26a4a985bf6b99d6bde99059e03c4b78', '9c0c3b33c171185a632fd4b809d35b2b26a4a985bf6b99d6bde99059e03c4b78'),
        (31, 'c243982a10e6b194dbbd29480aa113091909b55dac45ce74ed5705d70aff9448', 'c243982a10e6b194dbbd29480aa113091909b55dac45ce74ed5705d70aff9448'),
        (32, 'ccc17193e5a7a80db7243111cc91fbc20fa19aaedc2e078e7483a52533edefeb', 'ccc17193e5a7a80db7243111cc91fbc20fa19aaedc2e078e7483a52533edefeb'),
        (33, '22722286bb755a1dd24456fc7b6f005368ac222c8d93469b7ce4c99c5b0aa036', '22722286bb755a1dd24456fc7b6f005368ac222c8d93469b7ce4c99c5b0aa036'),
        (34, 'f619870a6a15867ec169f7590a9d1fce81c0c49c497150f1dce64e185501b2ad', 'f619870a6a15867ec169f7590a9d1fce81c0c49c497150f1dce64e185501b2ad'),
        (35, '318e101eddc5fa1e2bc006987b39e4329e400909c2a6acd82f8e46928cf5f620', '318e101eddc5fa1e2bc006987b39e4329e400909c2a6acd82f8e46928cf5f620'),
        (36, '1a1281f11e3804e393793d88927991e80f4699ca6f3dd33ade7e9509b6645b7d', '1a1281f11e3804e393793d88927991e80f4699ca6f3dd33ade7e9509b6645b7d'),
        (37, '934823d3a7b81c8f54ba29841e919d55ea16a6662b28503d81f8da65f1692cd1', '934823d3a7b81c8f54ba29841e919d55ea16a6662b28503d81f8da65f1692cd1'),
        (38, '30becb078131427da168b34c7f06c32afa52060ca13ffb51ac2648ad93a592ad', '30becb078131427da168b34c7f06c32afa52060ca13ffb51ac2648ad93a592ad'),
        (39, 'c18dfcdced3cb424416758c43932e3602ebd1337d480517fd1a5fe5c214c2d14', 'c18dfcdced3cb424416758c43932e3602ebd1337d480517fd1a5fe5c214c2d14'),
        (40, '1086c5a90f054d3d23b9972128b5c44f94965b6d0b0ac711533d63774520d64e', '1086c5a90f054d3d23b9972128b5c44f94965b6d0b0ac711533d63774520d64e'),
        (41, '7404c5912161c46c251c9d9c16baf03711e274f5e2fc0c20d774ac4ba96f9972', '7404c5912161c46c251c9d9c16baf03711e274f5e2fc0c20d774ac4ba96f9972'),
        (42, '50f5b2c2655f2d49932c9c85c13f0adf29729ac98fb67cea593a0548e6c5328d', '50f5b2c2655f2d49932c9c85c13f0adf29729ac98fb67cea593a0548e6c5328d'),
        (43, '0b0271213ed68001418f0d23487a8c327a718b81022a96697c953009ff178109', '0b0271213ed68001418f0d23487a8c327a718b81022a96697c953009ff178109'),
        (44, '6633d5d88b67bda3fe81eb7d28c638c4cf5227ae4840e913680d37185d4f96e9', '6633d5d88b67bda3fe81eb7d28c638c4cf5227ae4840e913680d37185d4f96e9'),
        (45, '65d49ebdcd3e390be86b47a4e4745e7c425eacff0d42e67f7336806a68533422', '65d49ebdcd3e390be86b47a4e4745e7c425eacff0d42e67f7336806a68533422'),
        (46, '7ac7aa0f48599486980d999755f513ee1f5e3ca630e278928a4c7a25846864e1', '7ac7aa0f48599486980d999755f513ee1f5e3ca630e278928a4c7a25846864e1'),
        (47, '904a1ff0cf54d20ebc2d48042861c00e05e25125030cb267a85f58da8e664c94', '904a1ff0cf54d20ebc2d48042861c00e05e25125030cb267a85f58da8e664c94'),
        (48, '907454241ff4e0685f02fbb83097e7507531e3699666e46c1b958049ec45169b', '907454241ff4e0685f02fbb83097e7507531e3699666e46c1b958049ec45169b'),
        (49, 'e6ce31d2418ee8d5ca7b000c373792fc441951d5ae787abcebc54c43a890e8d1', 'e6ce31d2418ee8d5ca7b000c373792fc441951d5ae787abcebc54c43a890e8d1'),
        (50, '0f54a9af621d8eaa45f4ba3e13484fcb043382ad8d0555a2f19d4dc7f813bdb5', '0f54a9af621d8eaa45f4ba3e13484fcb043382ad8d0555a2f19d4dc7f813bdb5'),
        (51, 'd256f466165d1f7c15a079de440176e33dadf19bf588f2ac0bdfb8ff3e8fe01f', 'd256f466165d1f7c15a079de440176e33dadf19bf588f2ac0bdfb8ff3e8fe01f'),
        (52, 'b3dc06130b0f530771dd99b4cf32e584a47a5c4f236fc028c7c852d44d3d8f38', 'b3dc06130b0f530771dd99b4cf32e584a47a5c4f236fc028c7c852d44d3d8f38'),
        (53, 'f9bcd06373d5b7e8d3cc29f22cf79fa5935c8e08c5b8270e73a13fa2e395031c', 'f9bcd06373d5b7e8d3cc29f22cf79fa5935c8e08c5b8270e73a13fa2e395031c'),
        (54, '87cdc88e3fc613be1b57d6c0082c79625e7c551c681e75d03383e872ac1aeec1', '87cdc88e3fc613be1b57d6c0082c79625e7c551c681e75d03383e872ac1aeec1'),
        (55, '01508992d6aae4431ce3caf2d886e478a1ae800f05f7ba4458290d3aacd82ca5', '01508992d6aae4431ce3caf2d886e478a1ae800f05f7ba4458290d3aacd82ca5'),
        (56, '0615a0a76334c104573e93756c3a8ada403b600d40651426b3127613c4e9acc0', '0615a0a76334c104573e93756c3a8ada403b600d40651426b3127613c4e9acc0'),
        (57, '96b89960e48dd4b7256260c868ef7e3b76bd77a6591fd1d00af41e4fc960ce52', '96b89960e48dd4b7256260c868ef7e3b76bd77a6591fd1d00af41e4fc960ce52'),
        (58, 'f3f6f05da2e7f326191e9b8880c7075a2e686fc86bb6aacb99c6ca8eb28a9430', 'f3f6f05da2e7f326191e9b8880c7075a2e686fc86bb6aacb99c6ca8eb28a9430'),
        (59, 'f1c9f4f3c011234d37ee30eb3cbb99056c36ddd9622462fe19c0f78a428df2d1', 'f1c9f4f3c011234d37ee30eb3cbb99056c36ddd9622462fe19c0f78a428df2d1'),
        (60, '9fba3e12767f6018230bced559829bd3168d2afa02e0bc782c8efa9a7f5d543e', '9fba3e12767f6018230bced559829bd3168d2afa02e0bc782c8efa9a7f5d543e'),
        (61, '9fba3e12767f6018230bced559829bd3168d2afa02e0bc782c8efa9a7f5d543e', '9fba3e12767f6018230bced559829bd3168d2afa02e0bc782c8efa9a7f5d543e'),
        (62, '9071ec46c989e58eb2bfa0d9624fbc3da72e14548f5e64e6683dd8bcfce23f60', '9071ec46c989e58eb2bfa0d9624fbc3da72e14548f5e64e6683dd8bcfce23f60'),
        (63, 'ee37d0adf6fae7812cdb379937c19b5a32d40d28c1f5f8770be02d45c42fb1e6', 'ee37d0adf6fae7812cdb379937c19b5a32d40d28c1f5f8770be02d45c42fb1e6'),
        (64, 'e584669831a40c4c01b16063c161f57375b21d316df64ca8e344ef61abdf2829', 'e584669831a40c4c01b16063c161f57375b21d316df64ca8e344ef61abdf2829'),
        (65, '5611435115674b49bebe78d6258a84beaf47cb57d3e38eadeb2b97d4c105dbd2', '5611435115674b49bebe78d6258a84beaf47cb57d3e38eadeb2b97d4c105dbd2'),
        (66, 'a560310de81327eff605798a078af770b6ea9178a889a66bfbd8d02524239d76', 'ac9dd774e7a9d5722146f4de11f722a3730a534a224025faa16f56cc77e3c159'),
        (67, '469ae5011ac31124a5190d845572f3732b6ac757bdef6a163b2cf9c89e261a9f', '469ae5011ac31124a5190d845572f3732b6ac757bdef6a163b2cf9c89e261a9f'),
        (68, 'a560310de81327eff605798a078af770b6ea9178a889a66bfbd8d02524239d76', '1fe810d04fe0ba13533d6153886cf587357e1ffd00d66cd5741c7cd2b241403e'),
        (69, 'a560310de81327eff605798a078af770b6ea9178a889a66bfbd8d02524239d76', 'a560310de81327eff605798a078af770b6ea9178a889a66bfbd8d02524239d76'),
        (70, 'a560310de81327eff605798a078af770b6ea9178a889a66bfbd8d02524239d76', '1587352e5226af311602bfdc8e44efd9470621d831abdee8e2f0f5756c324946'),
        (71, '9fd3732180f95b631cc7fba9b5dd78c55573a708b60f09f6a56a2d1c0fad1ded', '9fd3732180f95b631cc7fba9b5dd78c55573a708b60f09f6a56a2d1c0fad1ded'),
        (72, '45d2e82423ac8e02e48c5c8abe9925e4c12494bb20edbbd16c48f00b2d31ca40', '45d2e82423ac8e02e48c5c8abe9925e4c12494bb20edbbd16c48f00b2d31ca40'),
        (73, '099665378a94945dc390238217bfe783b84a692b49126f0bdfa7fe8b4f6d2020', '099665378a94945dc390238217bfe783b84a692b49126f0bdfa7fe8b4f6d2020'),
        (74, '9def61947a5239bbb5cec407a70aace1bfd161bd58911073c62d899a17d6ba2b', '9def61947a5239bbb5cec407a70aace1bfd161bd58911073c62d899a17d6ba2b'),
        (75, '596417db4ef8609efc90038d1e63303a8ffac8262fbeee7642e12a615d22efe3', '596417db4ef8609efc90038d1e63303a8ffac8262fbeee7642e12a615d22efe3'),
        (76, '0c7845f8c8a990d321f8bdcbb613ea144d60a7891f1cbe51d2f38782484a2a5e', '0c7845f8c8a990d321f8bdcbb613ea144d60a7891f1cbe51d2f38782484a2a5e'),
        (77, '32a5de6693fe3fe0832de3efbc6ae5fc7bd21ef77add349642c6c054e70ec3b4', '32a5de6693fe3fe0832de3efbc6ae5fc7bd21ef77add349642c6c054e70ec3b4'),
        (78, 'a83790655d7f983b6bde097f538358ab97406122b56f3c5238dd9e8a269037d1', 'a83790655d7f983b6bde097f538358ab97406122b56f3c5238dd9e8a269037d1'),
        (79, 'aadd1e41d53b2ca51f962a9864759c7bd2ad29f28a3212e7f7e7bd0bb3ceaae0', 'aadd1e41d53b2ca51f962a9864759c7bd2ad29f28a3212e7f7e7bd0bb3ceaae0'),
        (80, '8ef7d0235028ba3968f58972215451c39f26c7c9a3377bea38c987f33b6d695b', '8ef7d0235028ba3968f58972215451c39f26c7c9a3377bea38c987f33b6d695b'),
        (81, '99b47ee15826d11d84ca150bca7ffb28fba4d688f7d4a75960758d8e2b7c0faa', '99b47ee15826d11d84ca150bca7ffb28fba4d688f7d4a75960758d8e2b7c0faa'),
        (82, '654f17c163737e8d34d97652f46b77359651b3f81563ee306c19bd0940164252', '654f17c163737e8d34d97652f46b77359651b3f81563ee306c19bd0940164252'),
        (83, 'd3a8cb18abe05e5a37dd75f6415a7743f3ecf2e89d60ed979b049d5e2dee64e1', 'd3a8cb18abe05e5a37dd75f6415a7743f3ecf2e89d60ed979b049d5e2dee64e1'),
        (84, 'bb8c0374e3153da1e1bba639fef2f09d40327786071520bfc6cbe447562d36e6', 'bb8c0374e3153da1e1bba639fef2f09d40327786071520bfc6cbe447562d36e6'),
        (85, '0eabf45ac8a69d02d6e32f33962c84e676ed82d040b47584c08667619831f150', '0eabf45ac8a69d02d6e32f33962c84e676ed82d040b47584c08667619831f150'),
        (86, '9e83ad4f9523485667921862ba807c82114677d7e437623cac25551a3a4316a8', '9e83ad4f9523485667921862ba807c82114677d7e437623cac25551a3a4316a8'),
        (87, 'ecfd7e72ff3fad4f9d618f0ec2c04179806208fc29148258c3a7909d62c0225c', 'ecfd7e72ff3fad4f9d618f0ec2c04179806208fc29148258c3a7909d62c0225c'),
        (88, '6f363759a46e03a6b7c7269b4b626d235fea11050f917a80cbb81ada5a9e5d6a', '6f363759a46e03a6b7c7269b4b626d235fea11050f917a80cbb81ada5a9e5d6a'),
        (89, '9efd69534947fa1f383de353ad6e3bb937e694154239f4fffaf8890a1f761030', '9efd69534947fa1f383de353ad6e3bb937e694154239f4fffaf8890a1f761030'),
        (90, '3203c4a6f1ecaa082a7348b5522a50a0012d6f4b28ce04fd4a5615e756979df3', '3203c4a6f1ecaa082a7348b5522a50a0012d6f4b28ce04fd4a5615e756979df3'),
        (91, '7efc3e7dad70bc7900aade3a7a11e8bde4b884d60101cab5068a6bbd88a9a057', '7efc3e7dad70bc7900aade3a7a11e8bde4b884d60101cab5068a6bbd88a9a057'),
        (92, '6b5d9dfa97ad045216ac586caa712eeddf4d9bbd04ad54a174166ea5474d1f19', '6b5d9dfa97ad045216ac586caa712eeddf4d9bbd04ad54a174166ea5474d1f19'),
        (93, 'ef3934f469ef7c7ff13796449797537e27f4cb4378e89ea2957cb4e021c1b0b4', 'ef3934f469ef7c7ff13796449797537e27f4cb4378e89ea2957cb4e021c1b0b4'),
        (94, '90c3747c97352d29ff036cda7224cc1612da23737f60fcb440c651d528409abe', '90c3747c97352d29ff036cda7224cc1612da23737f60fcb440c651d528409abe'),
        (95, 'affb278fd7711b24fd34c13d4e441539d6739f0f76c1897f6e6da948f02c4d6b', 'affb278fd7711b24fd34c13d4e441539d6739f0f76c1897f6e6da948f02c4d6b'),
        (96, '491162d0ffa2656159b361e0f3dd3d5b9ed65fde6af5512da8d97d90f7a9a112', 'd8b6db89076f156df9c3af23fb34987ab0cbd6a168ac987316fd20ad408e3e02'),
        (97, '491162d0ffa2656159b361e0f3dd3d5b9ed65fde6af5512da8d97d90f7a9a112', 'ca0fd87aadbc1e28dca6d912ea624b4243114d3dfee10ac3c4b0316b2b75b6ea'),
        (98, '8b2ba93ca81605af998c78925a4d6cf633efa7403f28f8f05f011071df1181b9', '8b2ba93ca81605af998c78925a4d6cf633efa7403f28f8f05f011071df1181b9'),
        (99, 'cd530145d1e81702a5c20549af42c67a17a2d4d76708a4d77fc0714a1c5f802e', 'cd530145d1e81702a5c20549af42c67a17a2d4d76708a4d77fc0714a1c5f802e'),
        (100, '58747799fa99443dae717f6ed4f4fb4ec0df2d835a9700aedd4bd5899b80a963', '58747799fa99443dae717f6ed4f4fb4ec0df2d835a9700aedd4bd5899b80a963'),
        (101, 'faa403c6dc8e9e9337ec8109bcb27850883ce29f5908aa22aedb58433e12a4db', 'faa403c6dc8e9e9337ec8109bcb27850883ce29f5908aa22aedb58433e12a4db'),
        (102, 'e22a10bc5024f1e6e6794312a0c8f43a8000b18396c32a3a22aa1cab32d35b4d', 'e22a10bc5024f1e6e6794312a0c8f43a8000b18396c32a3a22aa1cab32d35b4d'),
        (103, 'bc761c78ce5795714260456417311e2d42376fa7ee72d92c32bfe3a9b2a603b7', 'bc761c78ce5795714260456417311e2d42376fa7ee72d92c32bfe3a9b2a603b7'),
        (104, 'a7f575cc6d70fd23926f098a2d396b09c9a1b32683d88bc03bc8c7b53bd4930e', 'a7f575cc6d70fd23926f098a2d396b09c9a1b32683d88bc03bc8c7b53bd4930e'),
        (105, 'be4745229b6f96a823ad89d5428178c3f8599c17d61ccaf28563a163cbe4ea9f', 'be4745229b6f96a823ad89d5428178c3f8599c17d61ccaf28563a163cbe4ea9f'),
        (106, 'e5e9224f970b06a970c03cab6657862524c2a429c17949336179f19ac83fb462', 'e89480a989a19a473e6828fc903b08c101f5cc3f80603b52bb23a491c1ecf983'),
        (107, 'e5e9224f970b06a970c03cab6657862524c2a429c17949336179f19ac83fb462', 'a9fb03d22b4257bc834d5c6f42772fe1b2500ddf87a2d5c63d454848f03b0a05'),
        (108, 'a89c1cb2142469cc3f27a94711d2c94df341dabf7b3c1ad344a5b36512d63855', 'a89c1cb2142469cc3f27a94711d2c94df341dabf7b3c1ad344a5b36512d63855'),
        (109, 'd0de696dca4e504b14fed2056afd113a0bc34da4713662b68fcd0820bd943117', 'd0de696dca4e504b14fed2056afd113a0bc34da4713662b68fcd0820bd943117'),
        (110, '4bd5a7ade1511a4727b16edeccc80872b201213c3f1034bd56d580c2ddfa029e', '4bd5a7ade1511a4727b16edeccc80872b201213c3f1034bd56d580c2ddfa029e'),
        (111, '859d694fd617042f9b6a11ef64a7242a31d8bd56e53f50272925c99287bbd3a8', '859d694fd617042f9b6a11ef64a7242a31d8bd56e53f50272925c99287bbd3a8'),
        (112, '5f543656ff9293d1ecf95f8c9cf4fe412ebe929adb0c3e452ddfa1b9f4616650', '5f543656ff9293d1ecf95f8c9cf4fe412ebe929adb0c3e452ddfa1b9f4616650'),
        (113, 'f01feeea7bedc8b65c81265a41f572158f80e9a8da6860d0f407270412b75af0', 'f01feeea7bedc8b65c81265a41f572158f80e9a8da6860d0f407270412b75af0'),
        (114, '91acebf05333a7fbed8b6c26a03d4479090b3ff8be2f20d311186beec005f800', '91acebf05333a7fbed8b6c26a03d4479090b3ff8be2f20d311186beec005f800'),
        (115, '10ab7597e1b42c0c3c7e3dee60dc7d53684c8f8e984561a0fa493da3cccb2edd', '10ab7597e1b42c0c3c7e3dee60dc7d53684c8f8e984561a0fa493da3cccb2edd'),
        (116, '2de9e6b215cc806dd0cd70a79e13cff7e2b115da16fab70f79548eb018f10f48', '2de9e6b215cc806dd0cd70a79e13cff7e2b115da16fab70f79548eb018f10f48'),
        (117, '63a754c3f7e422cfea12bd2cff32d951f5b5fcf2f3d00c5978b54805a829d09b', '63a754c3f7e422cfea12bd2cff32d951f5b5fcf2f3d00c5978b54805a829d09b'),
        (118, 'fff4b7fb2b673fa24a35e38dbf227ae44470a13c343541cbe800c787744920ec', 'fff4b7fb2b673fa24a35e38dbf227ae44470a13c343541cbe800c787744920ec'),
        (119, '44e9d71c50b3e32ec1a229cf752b1e5edf00656f05f5d2cbb9d81eaabbad78dd', '44e9d71c50b3e32ec1a229cf752b1e5edf00656f05f5d2cbb9d81eaabbad78dd'),
        (120, 'f6b94e7070d741032510c2789c70e93ea7f88b91841b7bfa969c7f123be74172', 'f6b94e7070d741032510c2789c70e93ea7f88b91841b7bfa969c7f123be74172'),
        (121, 'd349c084879ceb3939b46e2cf71fb158e4fa36a601ccc41f8b47b4e5f97c089c', 'd349c084879ceb3939b46e2cf71fb158e4fa36a601ccc41f8b47b4e5f97c089c'),
        (122, '8958bf4fdddad875279e0a5d4fe035e8f43c090c3fefa621db483bf31657b983', '8958bf4fdddad875279e0a5d4fe035e8f43c090c3fefa621db483bf31657b983'),
        (123, '9881ec52cb109a692c5ca7113b06b65cf3ff06a11e1f81c6e519ef74013ac92c', '9881ec52cb109a692c5ca7113b06b65cf3ff06a11e1f81c6e519ef74013ac92c'),
        (124, '0261a8af29c807194cc3acf25a422f7c4f5d78e77406f149f1de4d5c9d30b454', '0261a8af29c807194cc3acf25a422f7c4f5d78e77406f149f1de4d5c9d30b454'),
        (125, '5015f26f43954f38c49dcdff3fd843bd389f22652c439d1c2ac9582dbe7a36c1', '5015f26f43954f38c49dcdff3fd843bd389f22652c439d1c2ac9582dbe7a36c1'),
        (126, '18a490eba9ffde91f6b1ffa7fca21c56d8bb7e55d37bbd88a8dca247ad894bd4', '18a490eba9ffde91f6b1ffa7fca21c56d8bb7e55d37bbd88a8dca247ad894bd4'),
        (127, '7af2c748456cf9c2cc197518505dd7fdd031d508844985681052a6b882958fce', '7af2c748456cf9c2cc197518505dd7fdd031d508844985681052a6b882958fce'),
        (128, '491c6c4a951ad87cb3d66e2444335ba945265e61be1d3ba82b2c560c6db03d90', '491c6c4a951ad87cb3d66e2444335ba945265e61be1d3ba82b2c560c6db03d90');

    SELECT COUNT(*) INTO v_count FROM tmm_mi_model_param_dimension_map;
    IF v_count NOT IN (128, 129) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'mapping precondition: expected 128 or 129 rows';
    END IF;

    SELECT COUNT(*) INTO v_bad
      FROM _mp_mapping_hash AS h
      LEFT JOIN tmm_mi_model_param_dimension_map AS d
        ON d.model_param_dimension_map_id = h.model_param_dimension_map_id
     WHERE d.model_param_dimension_map_id IS NULL
        OR SHA2(CONCAT_WS(CHAR(31),
                        COALESCE(CAST(d.use_yn AS CHAR CHARACTER SET utf8mb4), '<NULL>'),
                        COALESCE(CAST(d.event_type_l2_id AS CHAR CHARACTER SET utf8mb4), '<NULL>'),
                        COALESCE(CAST(d.dimension_key AS CHAR CHARACTER SET utf8mb4), '<NULL>'),
                        COALESCE(CAST(d.dimension_label AS CHAR CHARACTER SET utf8mb4), '<NULL>'),
                        COALESCE(CAST(d.mapping_method AS CHAR CHARACTER SET utf8mb4), '<NULL>'),
                        COALESCE(CAST(d.model_param_id AS CHAR CHARACTER SET utf8mb4), '<NULL>'),
                        COALESCE(CAST(d.`comment` AS CHAR CHARACTER SET utf8mb4), '<NULL>'),
                        COALESCE(CAST(d.mod_usr_logn_id AS CHAR CHARACTER SET utf8mb4), '<NULL>'),
                        COALESCE(CAST(d.del_yn AS CHAR CHARACTER SET utf8mb4), '<NULL>')
                    ), 256) NOT IN (h.snapshot_hash, h.canonical_hash);
    IF v_bad <> 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'mapping precondition: IDs 1..128 differ from snapshot/final';
    END IF;

    SELECT COUNT(*) INTO v_bad
     FROM tmm_mi_model_param_dimension_map AS d
      LEFT JOIN _mp_mapping_hash AS h
        ON h.model_param_dimension_map_id = d.model_param_dimension_map_id
     WHERE h.model_param_dimension_map_id IS NULL
       AND NOT (d.event_type_l2_id <=> 21
                AND d.dimension_key <=> 'economic_intensity'
                AND d.dimension_label <=> '강도'
                AND d.model_param_id <=> 11
                AND d.use_yn <=> 'Y'
                AND d.mapping_method <=> 'routing'
                AND d.`comment` <=> 'event에 인구·이민·인구전망 변화가 명시되어 Country/Year별 인구 절대값이 직접 달라지는 경우에만 Population을 선택한다. 일반 경기 변화나 산업활동 변화에는 GDP·PMI를 우선하고 Population을 선택하지 않는다.'
                AND d.crt_usr_logn_id <=> 'model-parameter-canonical-v1'
                AND d.mod_usr_logn_id <=> 'model-parameter-canonical-v1'
                AND d.del_yn <=> 'N');
    IF v_bad <> 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'mapping precondition: unexpected row outside IDs 1..128';
    END IF;

    SELECT COUNT(*) INTO v_bad
      FROM tmm_mi_model_param_dimension_map
     WHERE model_param_dimension_map_id <= 128
       AND (crt_usr_logn_id <> 'system'
            OR crt_dtm <> TIMESTAMP('2026-08-05 08:30:07.073416'));
    IF v_bad <> 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'mapping precondition: creation audit mismatch';
    END IF;

    UPDATE tmm_mi_model_param_m AS m
    JOIN _mp_canonical_master AS c USING (model_param_id)
       SET m.use_yn = c.use_yn,
           m.parameter_name = c.parameter_name,
           m.parameter_hint = c.parameter_hint,
           m.model_file = c.model_file,
           m.model_sheet = c.model_sheet,
           m.model_table = c.model_table,
           m.semantic_axes = c.semantic_axes,
           m.basecase_read_mode = c.basecase_read_mode,
           m.basecase_header_row = c.basecase_header_row,
           m.basecase_data_start_row = c.basecase_data_start_row,
           m.basecase_column_roles = c.basecase_column_roles,
           m.basecase_row_filter = c.basecase_row_filter,
           m.basecase_year_row = c.basecase_year_row,
           m.basecase_month_row = c.basecase_month_row,
           m.basecase_period_row = c.basecase_period_row,
           m.basecase_value_start_col = c.basecase_value_start_col,
           m.basecase_value_end_col = c.basecase_value_end_col,
           m.basecase_stop_rule = c.basecase_stop_rule,
           m.del_yn = c.del_yn,
           m.mod_usr_logn_id = c.mod_usr_logn_id,
           m.mod_dtm = CURRENT_TIMESTAMP(6);

    CREATE TEMPORARY TABLE _mp_canonical_mapping AS
    SELECT model_param_dimension_map_id, use_yn, event_type_l2_id, dimension_key, dimension_label, mapping_method, model_param_id, `comment`, mod_usr_logn_id, del_yn
      FROM tmm_mi_model_param_dimension_map
     WHERE 1 = 0;

    INSERT INTO _mp_canonical_mapping (
        model_param_dimension_map_id, use_yn, event_type_l2_id, dimension_key, dimension_label, mapping_method, model_param_id, `comment`, mod_usr_logn_id, del_yn
    ) VALUES
        (2, 'Y', 1, 'utilization_change_amount', 'Utilization 변화 폭', 'direct', 17, '생산시설 가동 변화가 upstream 공급량에 직접 연결되면 SupplyDisruption을 적용한다. utilization_change_amount는 영향 Country와 최종 월 공급량 조정폭의 근거로 사용하고, period/onset_pattern/recovery_pattern은 적용 Year/Month와 변화 경로에 반영한다.', 'model-parameter-canonical-v1', 'N'),
        (5, 'Y', 1, 'alt_gas_supply_availability', '대체 가스 공급 가능성', 'direct', 17, '대체 가스전 증산이나 다른 upstream 공급이 명시되면 대체 Country의 SupplyDisruption 최종 공급량을 상향 조정한다. alt_gas_supply_availability는 상쇄 가능한 물량과 월별 배분의 근거로 사용한다.', 'model-parameter-canonical-v1', 'N'),
        (9, 'Y', 2, 'utilization_change_amount', 'Utilization 변화량', 'direct', 13, '액화 Plant Train의 대폭·영구 생산 손실 또는 회복을 월 생산량 최종값으로 직접 반영한다. utilization_change_amount와 period/onset_pattern/recovery_pattern을 생산량의 크기와 월별 경로에 사용하며, 단기·부분 차질은 LiqUtilAdjustment를 우선한다.', 'model-parameter-canonical-v1', 'N'),
        (16, 'Y', 3, 'target_utilization_at_ramp_up', 'Ramp-up 완료 시 도달 가동률 (Nameplate Capa 대비)', 'direct', 13, '신규 액화 Train의 COD와 ramp-up 완료 가동률을 기준으로 월 생산량을 산정한다. target_utilization_at_ramp_up은 nameplate 월 생산능력에 곱하고 cod_timing/ramp_up_pattern은 적용 월에 반영한다. FID 무산이 명시되면 신규 생산량은 0으로 처리한다.', 'model-parameter-canonical-v1', 'N'),
        (18, 'Y', 4, 'utilization_change_amount', 'Utilization 변화 폭 (송출용량 대비)', 'direct', 15, '파이프라인 송출능력 변화가 명시되면 해당 Pipeline/From/To/Year/Month의 최종 Bcm/y capacity를 산정한다. utilization_change_amount는 capacity 조정폭에, period/onset/recovery/structural_change는 적용 월과 지속성에 반영한다.', 'model-parameter-canonical-v1', 'N'),
        (23, 'Y', 4, 'alt_supply_availability', '대체 공급원 가능성 (타 노선·LNG 전환)', 'direct', 15, '타 파이프라인 노선으로 대체 공급이 가능한 경우 해당 대체 Pipeline의 최종 송출능력을 상향 조정한다. LNG 전환만 설명된 경우에는 PipelineAdjustment 대신 LiqUtilAdjustment 경로를 사용한다.', 'model-parameter-canonical-v1', 'N'),
        (66, 'Y', 11, 'affected_facility_type', '영향 시설 유형', 'routing', 17, 'affected_facility_type이 생산·upstream 시설이고 자연재해가 Country별 가스 생산량을 직접 훼손하는 경우 SupplyDisruption을 선택한다. 액화·수입 시설 피해에는 해당 시설 파라미터를 우선한다.', 'model-parameter-canonical-v1', 'N'),
        (68, 'Y', 11, 'affected_facility_type', '영향 시설 유형', 'routing', 13, 'affected_facility_type이 수출·액화 시설이고 자연재해가 Train 생산량의 대폭·영구 손실 또는 ramp-up 변경을 명시하는 경우 LiqProdAdjustment를 선택한다. 단기 가동률 차질은 LiqUtilAdjustment를 우선한다.', 'model-parameter-canonical-v1', 'N'),
        (70, 'Y', 11, 'affected_facility_type', '영향 시설 유형', 'routing', 12, 'event가 미국 Gulf of Mexico 허리케인이고 강도 1~4와 영향 Year/Month를 식별할 수 있으며 승인된 GoM 액화 또는 upstream 영향 시설과 연결되는 경우에만 HurricaneIntensity를 선택한다. 일반 자연재해에는 선택하지 않는다.', 'model-parameter-canonical-v1', 'N'),
        (96, 'Y', 17, 'supply_disruption_intensity', '공급 차질 - 강도', 'direct', 13, '지정학적 긴장·전쟁이 액화 Plant Train 생산량의 대폭·영구 감소를 유발하면 LiqProdAdjustment로 월별 최종 생산량을 직접 조정한다. 부분·단기 가동률 차질은 LiqUtilAdjustment를 우선한다.', 'model-parameter-canonical-v1', 'N'),
        (97, 'Y', 17, 'supply_disruption_intensity', '공급 차질 - 강도', 'direct', 17, '지정학적 긴장·전쟁이 upstream 가스 생산을 훼손하면 supply_disruption_intensity와 period/pattern을 근거로 해당 Country/Year/Month의 최종 공급량을 조정한다.', 'model-parameter-canonical-v1', 'N'),
        (106, 'Y', 18, 'supply_disruption_intensity', '공급 차질 - 강도', 'direct', 13, '경제 제재·무역 제한이 액화 Plant Train 생산량의 직접 감소를 유발하면 LiqProdAdjustment로 월별 최종 생산량을 조정한다. 부분·단기 가동률 차질은 LiqUtilAdjustment를 우선한다.', 'model-parameter-canonical-v1', 'N'),
        (107, 'Y', 18, 'supply_disruption_intensity', '공급 차질 - 강도', 'direct', 17, '경제 제재·무역 제한이 upstream 가스 생산을 직접 제한하면 supply_disruption_intensity와 period/pattern을 근거로 해당 Country/Year/Month의 최종 공급량을 조정한다.', 'model-parameter-canonical-v1', 'N');

    UPDATE tmm_mi_model_param_dimension_map AS d
    JOIN _mp_canonical_mapping AS c USING (model_param_dimension_map_id)
       SET d.use_yn = c.use_yn,
           d.event_type_l2_id = c.event_type_l2_id,
           d.dimension_key = c.dimension_key,
           d.dimension_label = c.dimension_label,
           d.mapping_method = c.mapping_method,
           d.model_param_id = c.model_param_id,
           d.`comment` = c.`comment`,
           d.del_yn = c.del_yn,
           d.mod_usr_logn_id = c.mod_usr_logn_id,
           d.mod_dtm = CURRENT_TIMESTAMP(6);

    INSERT INTO tmm_mi_model_param_dimension_map (
        use_yn, event_type_l2_id, dimension_key, dimension_label, mapping_method, model_param_id, `comment`, crt_usr_logn_id, mod_usr_logn_id, del_yn
    ) VALUES (
        'Y', 21, 'economic_intensity', '강도', 'routing', 11, 'event에 인구·이민·인구전망 변화가 명시되어 Country/Year별 인구 절대값이 직접 달라지는 경우에만 Population을 선택한다. 일반 경기 변화나 산업활동 변화에는 GDP·PMI를 우선하고 Population을 선택하지 않는다.', 'model-parameter-canonical-v1', 'model-parameter-canonical-v1', 'N'
    )
    ON DUPLICATE KEY UPDATE
        use_yn = VALUES(use_yn),
        dimension_label = VALUES(dimension_label),
        mapping_method = VALUES(mapping_method),
        `comment` = VALUES(`comment`),
        mod_usr_logn_id = VALUES(mod_usr_logn_id),
        mod_dtm = CURRENT_TIMESTAMP(6),
        del_yn = VALUES(del_yn);

    SELECT COUNT(*) INTO v_bad
      FROM tmm_mi_model_param_m AS m
      JOIN _mp_canonical_master AS c USING (model_param_id)
     WHERE NOT (m.use_yn <=> c.use_yn AND m.parameter_name <=> c.parameter_name AND m.parameter_hint <=> c.parameter_hint AND m.model_file <=> c.model_file AND m.model_sheet <=> c.model_sheet AND m.model_table <=> c.model_table AND m.semantic_axes <=> c.semantic_axes AND m.basecase_read_mode <=> c.basecase_read_mode AND m.basecase_header_row <=> c.basecase_header_row AND m.basecase_data_start_row <=> c.basecase_data_start_row AND m.basecase_column_roles <=> c.basecase_column_roles AND m.basecase_row_filter <=> c.basecase_row_filter AND m.basecase_year_row <=> c.basecase_year_row AND m.basecase_month_row <=> c.basecase_month_row AND m.basecase_period_row <=> c.basecase_period_row AND m.basecase_value_start_col <=> c.basecase_value_start_col AND m.basecase_value_end_col <=> c.basecase_value_end_col AND m.basecase_stop_rule <=> c.basecase_stop_rule AND m.mod_usr_logn_id <=> c.mod_usr_logn_id AND m.del_yn <=> c.del_yn);
    IF v_bad <> 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'read-back: master canonical values mismatch';
    END IF;

    SELECT COUNT(*) INTO v_count FROM tmm_mi_model_param_dimension_map;
    IF v_count <> 129 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'invariant: expected 129 mappings';
    END IF;

    SELECT COUNT(*) INTO v_bad
      FROM tmm_mi_model_param_dimension_map AS d
      JOIN _mp_canonical_mapping AS c USING (model_param_dimension_map_id)
     WHERE NOT (d.use_yn <=> c.use_yn AND d.event_type_l2_id <=> c.event_type_l2_id AND d.dimension_key <=> c.dimension_key AND d.dimension_label <=> c.dimension_label AND d.mapping_method <=> c.mapping_method AND d.model_param_id <=> c.model_param_id AND d.`comment` <=> c.`comment` AND d.mod_usr_logn_id <=> c.mod_usr_logn_id AND d.del_yn <=> c.del_yn);
    IF v_bad <> 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'read-back: restored mapping values mismatch';
    END IF;

    SELECT COUNT(*) INTO v_count
      FROM tmm_mi_model_param_m
     WHERE use_yn = 'Y' AND del_yn = 'N';
    IF v_count <> 10 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'invariant: expected exactly 10 active parameters';
    END IF;

    SELECT COUNT(*) INTO v_bad
      FROM tmm_mi_model_param_m
     WHERE (use_yn = 'Y' AND del_yn = 'N')
       <> (parameter_name IN ('GDP', 'HurricaneIntensity', 'LiqProdAdjustment', 'LiqUtilAdjustment', 'PMI', 'PipelineAdjustment', 'Population', 'PowerMix', 'SupplyDisruption', 'Temperature'));
    IF v_bad <> 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'invariant: active parameter name set mismatch';
    END IF;

    SELECT COUNT(*) INTO v_count
      FROM tmm_mi_model_param_dimension_map
     WHERE mapping_method = 'direct';
    IF v_count <> 35 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'invariant: direct mapping count mismatch';
    END IF;

    SELECT COUNT(*) INTO v_count
      FROM tmm_mi_model_param_dimension_map
     WHERE mapping_method = 'routing';
    IF v_count <> 6 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'invariant: routing mapping count mismatch';
    END IF;

    SELECT COUNT(*) INTO v_count
      FROM tmm_mi_model_param_dimension_map
     WHERE mapping_method = 'indirect';
    IF v_count <> 55 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'invariant: indirect mapping count mismatch';
    END IF;

    SELECT COUNT(*) INTO v_count
      FROM tmm_mi_model_param_dimension_map
     WHERE mapping_method = 'na';
    IF v_count <> 33 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'invariant: na mapping count mismatch';
    END IF;

    SELECT COUNT(*) INTO v_bad
      FROM tmm_mi_model_param_dimension_map AS d
      LEFT JOIN tmm_mi_model_param_m AS m ON m.model_param_id = d.model_param_id
     WHERE d.use_yn <> 'Y' OR d.del_yn <> 'N'
        OR (d.model_param_id IS NOT NULL
            AND (m.model_param_id IS NULL OR m.use_yn <> 'Y' OR m.del_yn <> 'N'))
        OR (d.mapping_method IN ('direct', 'routing') AND d.model_param_id IS NULL);
    IF v_bad <> 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'invariant: invalid mapping reference/state';
    END IF;

    SELECT COUNT(*) INTO v_bad
      FROM (
            SELECT event_type_l2_id, dimension_key, model_param_id
              FROM tmm_mi_model_param_dimension_map
             WHERE model_param_id IS NOT NULL
             GROUP BY event_type_l2_id, dimension_key, model_param_id
            HAVING COUNT(*) > 1
           ) AS duplicate_keys;
    IF v_bad <> 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'invariant: duplicate non-null mapping key';
    END IF;

    SELECT COUNT(*) INTO v_bad
      FROM tmm_mi_model_param_m AS m
     WHERE m.use_yn = 'Y' AND m.del_yn = 'N'
       AND NOT EXISTS (
            SELECT 1
              FROM tmm_mi_model_param_dimension_map AS d
             WHERE d.model_param_id = m.model_param_id
               AND d.mapping_method IN ('direct', 'routing')
               AND d.use_yn = 'Y' AND d.del_yn = 'N'
       );
    IF v_bad <> 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'invariant: active parameter without candidate mapping';
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

    SELECT COUNT(*) INTO v_count
      FROM tmm_mi_model_param_dimension_map
     WHERE event_type_l2_id = 21
       AND dimension_key = 'economic_intensity'
       AND model_param_id = 11
       AND use_yn = 'Y'
       AND dimension_label = '강도'
       AND mapping_method = 'routing'
       AND `comment` = 'event에 인구·이민·인구전망 변화가 명시되어 Country/Year별 인구 절대값이 직접 달라지는 경우에만 Population을 선택한다. 일반 경기 변화나 산업활동 변화에는 GDP·PMI를 우선하고 Population을 선택하지 않는다.'
       AND crt_usr_logn_id = 'model-parameter-canonical-v1'
       AND mod_usr_logn_id = 'model-parameter-canonical-v1'
       AND del_yn = 'N';
    IF v_count <> 1 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'read-back: Population routing mapping mismatch';
    END IF;

    COMMIT;
    DROP TEMPORARY TABLE IF EXISTS _mp_canonical_master;
    DROP TEMPORARY TABLE IF EXISTS _mp_master_hash;
    DROP TEMPORARY TABLE IF EXISTS _mp_mapping_hash;
    DROP TEMPORARY TABLE IF EXISTS _mp_canonical_mapping;
END//

CALL apply_model_parameter_canonical_v1()//
DROP PROCEDURE apply_model_parameter_canonical_v1//

DELIMITER ;
