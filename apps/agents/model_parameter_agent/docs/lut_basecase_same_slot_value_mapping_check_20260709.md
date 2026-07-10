# Basecase 기준 동일 Slot LUT Value 매핑 검증

작성일: 2026-07-09

## 1. 목적

basecase에서 추출된 slot 좌표를 왼쪽 기준으로 두고, 동일 slot을 LUT에서 lookup했을 때 실제로 값이 매핑되는지 확인한다. basecase row가 많은 파라미터는 상세 표를 최대 100개 row로 제한했다.

## 2. 비교 기준

- basecase source: `apps/agents/model_parameter_agent/docs/basecase_load_values_full_20260630.csv`

- LUT source: `apps/agents/model_parameter_agent/resources/lut/*.csv`

- GDP LUT value: absolute GDP를 `GDP_t / GDP_t-1 - 1` 성장률로 변환

- Temperature LUT value: HDD/CDD에서 temperature 역산

- LiqUtilAdjustment LUT value: train row 단위 `LNG plant utilisation %`; lookup key는 `Country + LNG Plant + LNG Plant Train + Year + Month`, `Period`는 sanity check

- LiqUtilAdjustment slot용 `Nameplate Capacity`는 LUT의 `LNG train capacity (Million tonnes LNG per month) * 12`로 만든 MTPA 값을 사용한다. `LNG train nameplate capacity (Bcm per month)`는 단위가 달라 basecase slot의 `Nameplate Capacity`에 넣지 않는다.

- 값 비교는 `basecase_value - lut_value` 기준이다.

## 3. 매핑 결과 요약

| Parameter | Lookup key | Basecase rows | Mapped | Unmapped | Mapping rate | Same value | Different value | Max abs diff | Rows in table |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GDP | Country + Year | 93 | 93 | 0 | 100.00% | 8 | 85 | 0.06914 | 93 |
| PMI | Country + Year + Month | 48 | 48 | 0 | 100.00% | 0 | 48 | 4 | 48 |
| PowerMix | Country + Year + Energy Source | 57 | 57 | 0 | 100.00% | 0 | 57 | 0.208436 | 57 |
| Temperature | Country + Year + Month | 150 | 150 | 0 | 100.00% | 0 | 150 | 3.687375 | 100 |
| LiqUtilAdjustment | Country + LNG Plant + LNG Plant Train + Year + Month (Period sanity) | 21656 | 21569 | 87 | 99.60% | 1339 | 20230 | 2.333672 | 100 |

해석:

- GDP/PMI/PowerMix/Temperature는 basecase row가 모두 LUT value와 매핑된다.

- LiqUtilAdjustment는 business key 기준 21,569/21,656개가 매핑되고, 87개는 LUT에서 같은 slot을 찾지 못했다.

- LiqUtilAdjustment 매핑 row 중 Period mismatch는 0개, lifecycle mismatch는 4496개, capacity mismatch는 1170개다.

- capacity mismatch는 LUT lookup 실패가 아니라 basecase metadata와 LUT 환산 MTPA가 다른 경우다. LUT-only slot을 basecase 형태로 생성할 때는 LUT 환산 MTPA를 사용하고, basecase override가 있는 slot은 basecase metadata를 우선한다.

## 4. 상세 샘플

### 4.1 GDP

basecase 93개 전체를 표시한다.

| Country | Year | basecase_value | lut_value | value_diff | mapping_status | reference_id |
| --- | --- | --- | --- | --- | --- | --- |
| Germany | 2024 | -0.001 | 0.06814 | -0.06914 | MAPPED | Demand:GDPPopulationAdjustment:R66C6 |
| Belgium | 2024 | 0.009488 | 0.075772 | -0.066284 | MAPPED | Demand:GDPPopulationAdjustment:R50C6 |
| Netherlands | 2024 | 0.010011 | 0.075101 | -0.065091 | MAPPED | Demand:GDPPopulationAdjustment:R82C6 |
| France | 2024 | 0.012 | 0.052434 | -0.040434 | MAPPED | Demand:GDPPopulationAdjustment:R58C6 |
| China | 2024 | 0.05 | 0.023547 | 0.026453 | MAPPED | Demand:GDPPopulationAdjustment:R19C6 |
| Taiwan (China) | 2025 | 0.05 | 0.027635 | 0.022365 | MAPPED | Demand:GDPPopulationAdjustment:R43C6 |
| Taiwan (China) | 2024 | 0.048 | 0.029652 | 0.018348 | MAPPED | Demand:GDPPopulationAdjustment:R42C6 |
| Spain | 2024 | 0.035 | 0.051437 | -0.016437 | MAPPED | Demand:GDPPopulationAdjustment:R90C6 |
| China | 2030 | 0.04 | 0.023852 | 0.016148 | MAPPED | Demand:GDPPopulationAdjustment:R25C6 |
| China | 2031 | 0.04 | 0.023852 | 0.016148 | MAPPED | Demand:GDPPopulationAdjustment:R26C6 |
| China | 2029 | 0.041 | 0.025201 | 0.015799 | MAPPED | Demand:GDPPopulationAdjustment:R24C6 |
| Italy | 2024 | 0.007 | 0.022246 | -0.015246 | MAPPED | Demand:GDPPopulationAdjustment:R74C6 |
| Germany | 2025 | 0.005881 | 0.019932 | -0.01405 | MAPPED | Demand:GDPPopulationAdjustment:R67C6 |
| Taiwan (China) | 2029 | 0.024 | 0.010372 | 0.013628 | MAPPED | Demand:GDPPopulationAdjustment:R47C6 |
| South Korea | 2025 | 0.01 | 0.022623 | -0.012623 | MAPPED | Demand:GDPPopulationAdjustment:R35C6 |
| Taiwan (China) | 2030 | 0.022 | 0.010144 | 0.011856 | MAPPED | Demand:GDPPopulationAdjustment:R48C6 |
| France | 2025 | 0.00627 | 0.018116 | -0.011846 | MAPPED | Demand:GDPPopulationAdjustment:R59C6 |
| South Korea | 2029 | 0.02 | 0.008344 | 0.011656 | MAPPED | Demand:GDPPopulationAdjustment:R39C6 |
| South Korea | 2030 | 0.019 | 0.008135 | 0.010865 | MAPPED | Demand:GDPPopulationAdjustment:R40C6 |
| China | 2028 | 0.043 | 0.033797 | 0.009203 | MAPPED | Demand:GDPPopulationAdjustment:R23C6 |
| Germany | 2026 | 0.01 | 0.018808 | -0.008808 | MAPPED | Demand:GDPPopulationAdjustment:R68C6 |
| South Korea | 2024 | 0.024 | 0.031638 | -0.007638 | MAPPED | Demand:GDPPopulationAdjustment:R34C6 |
| France | 2026 | 0.009559 | 0.016693 | -0.007134 | MAPPED | Demand:GDPPopulationAdjustment:R60C6 |
| China | 2025 | 0.048 | 0.04117 | 0.00683 | MAPPED | Demand:GDPPopulationAdjustment:R20C6 |
| Spain | 2028 | 0.009967 | 0.016409 | -0.006442 | MAPPED | Demand:GDPPopulationAdjustment:R94C6 |
| India | 2030 | 0.06033 | 0.054046 | 0.006284 | MAPPED | Demand:GDPPopulationAdjustment:R103C6 |
| India | 2031 | 0.0603 | 0.054046 | 0.006254 | MAPPED | Demand:GDPPopulationAdjustment:R104C6 |
| China | 2027 | 0.042 | 0.036634 | 0.005366 | MAPPED | Demand:GDPPopulationAdjustment:R22C6 |
| Italy | 2027 | 0.005322 | 0.010318 | -0.004996 | MAPPED | Demand:GDPPopulationAdjustment:R77C6 |
| Germany | 2029 | 0.0053 | 0.009978 | -0.004678 | MAPPED | Demand:GDPPopulationAdjustment:R71C6 |
| India | 2029 | 0.06119 | 0.056611 | 0.004579 | MAPPED | Demand:GDPPopulationAdjustment:R102C6 |
| South Korea | 2026 | 0.018 | 0.022466 | -0.004466 | MAPPED | Demand:GDPPopulationAdjustment:R36C6 |
| Germany | 2030 | 0.0055 | 0.009667 | -0.004167 | MAPPED | Demand:GDPPopulationAdjustment:R72C6 |
| Italy | 2028 | 0.004812 | 0.008949 | -0.004137 | MAPPED | Demand:GDPPopulationAdjustment:R78C6 |
| Italy | 2026 | 0.006819 | 0.010934 | -0.004115 | MAPPED | Demand:GDPPopulationAdjustment:R76C6 |
| Italy | 2029 | 0.003831 | 0.007629 | -0.003798 | MAPPED | Demand:GDPPopulationAdjustment:R79C6 |
| Germany | 2027 | 0.0091 | 0.01289 | -0.00379 | MAPPED | Demand:GDPPopulationAdjustment:R69C6 |
| France | 2027 | 0.011653 | 0.015244 | -0.003591 | MAPPED | Demand:GDPPopulationAdjustment:R61C6 |
| Italy | 2031 | 0.00396 | 0.007399 | -0.003439 | MAPPED | Demand:GDPPopulationAdjustment:R81C6 |
| Germany | 2031 | 0.00631 | 0.009667 | -0.003357 | MAPPED | Demand:GDPPopulationAdjustment:R73C6 |
| Italy | 2030 | 0.004294 | 0.007399 | -0.003105 | MAPPED | Demand:GDPPopulationAdjustment:R80C6 |
| Belgium | 2026 | 0.014842 | 0.011924 | 0.002918 | MAPPED | Demand:GDPPopulationAdjustment:R52C6 |
| Taiwan (China) | 2028 | 0.024 | 0.021161 | 0.002839 | MAPPED | Demand:GDPPopulationAdjustment:R46C6 |
| South Korea | 2027 | 0.019 | 0.021735 | -0.002735 | MAPPED | Demand:GDPPopulationAdjustment:R37C6 |
| Taiwan (China) | 2026 | 0.024 | 0.026256 | -0.002256 | MAPPED | Demand:GDPPopulationAdjustment:R44C6 |
| Germany | 2028 | 0.0069 | 0.009146 | -0.002246 | MAPPED | Demand:GDPPopulationAdjustment:R70C6 |
| Belgium | 2027 | 0.014625 | 0.012435 | 0.00219 | MAPPED | Demand:GDPPopulationAdjustment:R53C6 |
| France | 2028 | 0.012239 | 0.014379 | -0.00214 | MAPPED | Demand:GDPPopulationAdjustment:R62C6 |
| Taiwan (China) | 2027 | 0.027 | 0.024986 | 0.002014 | MAPPED | Demand:GDPPopulationAdjustment:R45C6 |
| India | 2026 | 0.065 | 0.063154 | 0.001846 | MAPPED | Demand:GDPPopulationAdjustment:R99C6 |
| Italy | 2025 | 0.012278 | 0.010442 | 0.001837 | MAPPED | Demand:GDPPopulationAdjustment:R75C6 |
| Spain | 2026 | 0.016472 | 0.018211 | -0.001739 | MAPPED | Demand:GDPPopulationAdjustment:R92C6 |
| United States | 2026 | 0.019 | 0.020638 | -0.001638 | MAPPED | Demand:GDPPopulationAdjustment:R13C6 |
| Netherlands | 2029 | 0.012 | 0.013555 | -0.001555 | MAPPED | Demand:GDPPopulationAdjustment:R87C6 |
| Japan | 2025 | 0.00802 | 0.006498 | 0.001522 | MAPPED | Demand:GDPPopulationAdjustment:R27C6 |
| India | 2027 | 0.065 | 0.063495 | 0.001505 | MAPPED | Demand:GDPPopulationAdjustment:R100C6 |
| Spain | 2025 | 0.019355 | 0.020797 | -0.001441 | MAPPED | Demand:GDPPopulationAdjustment:R91C6 |
| Netherlands | 2028 | 0.015 | 0.016351 | -0.001351 | MAPPED | Demand:GDPPopulationAdjustment:R86C6 |
| China | 2026 | 0.042 | 0.040703 | 0.001297 | MAPPED | Demand:GDPPopulationAdjustment:R21C6 |
| Netherlands | 2025 | 0.014 | 0.01528 | -0.00128 | MAPPED | Demand:GDPPopulationAdjustment:R83C6 |
| Netherlands | 2030 | 0.012 | 0.013211 | -0.001211 | MAPPED | Demand:GDPPopulationAdjustment:R88C6 |
| Netherlands | 2031 | 0.012 | 0.013211 | -0.001211 | MAPPED | Demand:GDPPopulationAdjustment:R89C6 |
| United States | 2027 | 0.02 | 0.021203 | -0.001203 | MAPPED | Demand:GDPPopulationAdjustment:R14C6 |
| Japan | 2026 | 0.00601 | 0.004869 | 0.001141 | MAPPED | Demand:GDPPopulationAdjustment:R28C6 |
| Spain | 2027 | 0.016205 | 0.017266 | -0.001061 | MAPPED | Demand:GDPPopulationAdjustment:R93C6 |
| Netherlands | 2026 | 0.015 | 0.016045 | -0.001045 | MAPPED | Demand:GDPPopulationAdjustment:R84C6 |
| India | 2028 | 0.06159 | 0.06263 | -0.00104 | MAPPED | Demand:GDPPopulationAdjustment:R101C6 |
| Belgium | 2030 | 0.01406 | 0.013035 | 0.001024 | MAPPED | Demand:GDPPopulationAdjustment:R56C6 |
| Japan | 2028 | 0.00508 | 0.004103 | 0.000977 | MAPPED | Demand:GDPPopulationAdjustment:R30C6 |
| Japan | 2027 | 0.00505 | 0.00417 | 0.00088 | MAPPED | Demand:GDPPopulationAdjustment:R29C6 |
| South Korea | 2028 | 0.022 | 0.021137 | 0.000863 | MAPPED | Demand:GDPPopulationAdjustment:R38C6 |
| United States | 2025 | 0.019 | 0.018178 | 0.000822 | MAPPED | Demand:GDPPopulationAdjustment:R12C6 |
| Belgium | 2029 | 0.012456 | 0.013269 | -0.000813 | MAPPED | Demand:GDPPopulationAdjustment:R55C6 |
| Belgium | 2025 | 0.013 | 0.012227 | 0.000773 | MAPPED | Demand:GDPPopulationAdjustment:R51C6 |
| Belgium | 2031 | 0.01235 | 0.013035 | -0.000685 | MAPPED | Demand:GDPPopulationAdjustment:R57C6 |
| Netherlands | 2027 | 0.017 | 0.016379 | 0.000621 | MAPPED | Demand:GDPPopulationAdjustment:R85C6 |
| Belgium | 2028 | 0.012613 | 0.013038 | -0.000425 | MAPPED | Demand:GDPPopulationAdjustment:R54C6 |
| France | 2029 | 0.012447 | 0.01276 | -0.000313 | MAPPED | Demand:GDPPopulationAdjustment:R63C6 |
| Spain | 2029 | 0.009868 | 0.009561 | 0.000308 | MAPPED | Demand:GDPPopulationAdjustment:R95C6 |
| Japan | 2029 | 0.00498 | 0.005275 | -0.000295 | MAPPED | Demand:GDPPopulationAdjustment:R31C6 |
| India | 2025 | 0.063 | 0.063269 | -0.000269 | MAPPED | Demand:GDPPopulationAdjustment:R98C6 |
| Spain | 2030 | 0.009121 | 0.00936 | -0.000239 | MAPPED | Demand:GDPPopulationAdjustment:R96C6 |
| France | 2030 | 0.012294 | 0.01253 | -0.000236 | MAPPED | Demand:GDPPopulationAdjustment:R64C6 |
| Japan | 2030 | 0.00523 | 0.005049 | 0.000181 | MAPPED | Demand:GDPPopulationAdjustment:R32C6 |
| Japan | 2031 | 0.00505 | 0.005049 | 0.000001 | MAPPED | Demand:GDPPopulationAdjustment:R33C6 |
| France | 2031 | 0.01253 | 0.01253 | -0 | MAPPED | Demand:GDPPopulationAdjustment:R65C6 |
| United States | 2029 | 0.014919 | 0.014919 | -0 | MAPPED | Demand:GDPPopulationAdjustment:R16C6 |
| United States | 2030 | 0.014859 | 0.014859 | -0 | MAPPED | Demand:GDPPopulationAdjustment:R17C6 |
| United States | 2031 | 0.014859 | 0.014859 | -0 | MAPPED | Demand:GDPPopulationAdjustment:R18C6 |
| United States | 2028 | 0.021215 | 0.021215 | -0 | MAPPED | Demand:GDPPopulationAdjustment:R15C6 |
| Taiwan (China) | 2031 | 0.010144 | 0.010144 | -0 | MAPPED | Demand:GDPPopulationAdjustment:R49C6 |
| Spain | 2031 | 0.00936 | 0.00936 | -0 | MAPPED | Demand:GDPPopulationAdjustment:R97C6 |
| South Korea | 2031 | 0.008135 | 0.008135 | -0 | MAPPED | Demand:GDPPopulationAdjustment:R41C6 |

### 4.2 PMI

basecase 48개 전체를 표시한다. LUT 값은 모두 50 중립 baseline이다.

| Country | Year | Month | basecase_value | lut_value | value_diff | mapping_status | reference_id |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Philippines | 2029 | 1 | 54 | 50 | 4 | MAPPED | Demand:PMIAdjustment:R37C6 |
| Philippines | 2029 | 2 | 54 | 50 | 4 | MAPPED | Demand:PMIAdjustment:R38C6 |
| Philippines | 2029 | 3 | 54 | 50 | 4 | MAPPED | Demand:PMIAdjustment:R39C6 |
| Philippines | 2029 | 4 | 54 | 50 | 4 | MAPPED | Demand:PMIAdjustment:R40C6 |
| Philippines | 2029 | 5 | 54 | 50 | 4 | MAPPED | Demand:PMIAdjustment:R41C6 |
| Philippines | 2029 | 6 | 54 | 50 | 4 | MAPPED | Demand:PMIAdjustment:R42C6 |
| Philippines | 2029 | 7 | 54 | 50 | 4 | MAPPED | Demand:PMIAdjustment:R43C6 |
| Philippines | 2029 | 8 | 54 | 50 | 4 | MAPPED | Demand:PMIAdjustment:R44C6 |
| Philippines | 2029 | 9 | 54 | 50 | 4 | MAPPED | Demand:PMIAdjustment:R45C6 |
| Philippines | 2029 | 10 | 54 | 50 | 4 | MAPPED | Demand:PMIAdjustment:R46C6 |
| Philippines | 2029 | 11 | 54 | 50 | 4 | MAPPED | Demand:PMIAdjustment:R47C6 |
| Philippines | 2029 | 12 | 54 | 50 | 4 | MAPPED | Demand:PMIAdjustment:R48C6 |
| Philippines | 2030 | 1 | 54 | 50 | 4 | MAPPED | Demand:PMIAdjustment:R49C6 |
| Philippines | 2030 | 2 | 54 | 50 | 4 | MAPPED | Demand:PMIAdjustment:R50C6 |
| Philippines | 2030 | 3 | 54 | 50 | 4 | MAPPED | Demand:PMIAdjustment:R51C6 |
| Philippines | 2030 | 4 | 54 | 50 | 4 | MAPPED | Demand:PMIAdjustment:R52C6 |
| Philippines | 2030 | 5 | 54 | 50 | 4 | MAPPED | Demand:PMIAdjustment:R53C6 |
| Philippines | 2030 | 6 | 54 | 50 | 4 | MAPPED | Demand:PMIAdjustment:R54C6 |
| Philippines | 2030 | 7 | 54 | 50 | 4 | MAPPED | Demand:PMIAdjustment:R55C6 |
| Philippines | 2030 | 8 | 54 | 50 | 4 | MAPPED | Demand:PMIAdjustment:R56C6 |
| Philippines | 2030 | 9 | 54 | 50 | 4 | MAPPED | Demand:PMIAdjustment:R57C6 |
| Philippines | 2030 | 10 | 54 | 50 | 4 | MAPPED | Demand:PMIAdjustment:R58C6 |
| Philippines | 2030 | 11 | 54 | 50 | 4 | MAPPED | Demand:PMIAdjustment:R59C6 |
| Philippines | 2030 | 12 | 54 | 50 | 4 | MAPPED | Demand:PMIAdjustment:R60C6 |
| China | 2025 | 4 | 49 | 50 | -1 | MAPPED | Demand:PMIAdjustment:R16C6 |
| China | 2025 | 1 | 49.1 | 50 | -0.9 | MAPPED | Demand:PMIAdjustment:R13C6 |
| China | 2025 | 7 | 49.3 | 50 | -0.7 | MAPPED | Demand:PMIAdjustment:R19C6 |
| China | 2025 | 8 | 49.4 | 50 | -0.6 | MAPPED | Demand:PMIAdjustment:R20C6 |
| China | 2025 | 3 | 50.5 | 50 | 0.5 | MAPPED | Demand:PMIAdjustment:R15C6 |
| China | 2025 | 5 | 49.5 | 50 | -0.5 | MAPPED | Demand:PMIAdjustment:R17C6 |
| China | 2026 | 1 | 49.5 | 50 | -0.5 | MAPPED | Demand:PMIAdjustment:R25C6 |
| China | 2026 | 2 | 49.5 | 50 | -0.5 | MAPPED | Demand:PMIAdjustment:R26C6 |
| China | 2026 | 3 | 49.5 | 50 | -0.5 | MAPPED | Demand:PMIAdjustment:R27C6 |
| China | 2026 | 4 | 49.5 | 50 | -0.5 | MAPPED | Demand:PMIAdjustment:R28C6 |
| China | 2026 | 5 | 49.5 | 50 | -0.5 | MAPPED | Demand:PMIAdjustment:R29C6 |
| China | 2026 | 6 | 49.5 | 50 | -0.5 | MAPPED | Demand:PMIAdjustment:R30C6 |
| China | 2026 | 7 | 49.5 | 50 | -0.5 | MAPPED | Demand:PMIAdjustment:R31C6 |
| China | 2026 | 8 | 49.5 | 50 | -0.5 | MAPPED | Demand:PMIAdjustment:R32C6 |
| China | 2026 | 9 | 49.5 | 50 | -0.5 | MAPPED | Demand:PMIAdjustment:R33C6 |
| China | 2026 | 10 | 49.5 | 50 | -0.5 | MAPPED | Demand:PMIAdjustment:R34C6 |
| China | 2026 | 11 | 49.5 | 50 | -0.5 | MAPPED | Demand:PMIAdjustment:R35C6 |
| China | 2026 | 12 | 49.5 | 50 | -0.5 | MAPPED | Demand:PMIAdjustment:R36C6 |
| China | 2025 | 9 | 49.6 | 50 | -0.4 | MAPPED | Demand:PMIAdjustment:R21C6 |
| China | 2025 | 10 | 49.6 | 50 | -0.4 | MAPPED | Demand:PMIAdjustment:R22C6 |
| China | 2025 | 11 | 49.6 | 50 | -0.4 | MAPPED | Demand:PMIAdjustment:R23C6 |
| China | 2025 | 12 | 49.6 | 50 | -0.4 | MAPPED | Demand:PMIAdjustment:R24C6 |
| China | 2025 | 6 | 49.7 | 50 | -0.3 | MAPPED | Demand:PMIAdjustment:R18C6 |
| China | 2025 | 2 | 50.2 | 50 | 0.2 | MAPPED | Demand:PMIAdjustment:R14C6 |

### 4.3 PowerMix

basecase 57개 전체를 표시한다.

| Country | Year | Energy Source | basecase_value | lut_value | value_diff | mapping_status | reference_id |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Belgium | 2026 | Gas | 0.19 | 0.398436 | -0.208436 | MAPPED | Demand:PowerMixAdjustment:R59C6 |
| Belgium | 2027 | Gas | 0.18 | 0.37023 | -0.19023 | MAPPED | Demand:PowerMixAdjustment:R60C6 |
| Belgium | 2028 | Gas | 0.18 | 0.337078 | -0.157078 | MAPPED | Demand:PowerMixAdjustment:R61C6 |
| Spain | 2026 | Gas | 0.213 | 0.065111 | 0.147889 | MAPPED | Demand:PowerMixAdjustment:R49C6 |
| Spain | 2027 | Gas | 0.211 | 0.063911 | 0.147089 | MAPPED | Demand:PowerMixAdjustment:R50C6 |
| Netherlands | 2030 | Gas | 0.309692 | 0.166791 | 0.142901 | MAPPED | Demand:PowerMixAdjustment:R58C6 |
| Belgium | 2029 | Gas | 0.16 | 0.288106 | -0.128106 | MAPPED | Demand:PowerMixAdjustment:R62C6 |
| Netherlands | 2029 | Gas | 0.324409 | 0.203605 | 0.120804 | MAPPED | Demand:PowerMixAdjustment:R57C6 |
| Belgium | 2030 | Gas | 0.14 | 0.248909 | -0.108909 | MAPPED | Demand:PowerMixAdjustment:R63C6 |
| Spain | 2028 | Gas | 0.18 | 0.072174 | 0.107826 | MAPPED | Demand:PowerMixAdjustment:R51C6 |
| Netherlands | 2028 | Gas | 0.32728 | 0.233742 | 0.093538 | MAPPED | Demand:PowerMixAdjustment:R56C6 |
| Spain | 2030 | Gas | 0.148 | 0.062875 | 0.085125 | MAPPED | Demand:PowerMixAdjustment:R53C6 |
| United Kingdom | 2027 | Gas | 0.29 | 0.205408 | 0.084592 | MAPPED | Demand:PowerMixAdjustment:R65C6 |
| United Kingdom | 2030 | Gas | 0.2 | 0.119976 | 0.080024 | MAPPED | Demand:PowerMixAdjustment:R68C6 |
| Spain | 2029 | Gas | 0.15 | 0.071001 | 0.078999 | MAPPED | Demand:PowerMixAdjustment:R52C6 |
| United Kingdom | 2029 | Gas | 0.23 | 0.151788 | 0.078212 | MAPPED | Demand:PowerMixAdjustment:R67C6 |
| Taiwan (China) | 2027 | Gas | 0.495 | 0.417702 | 0.077298 | MAPPED | Demand:PowerMixAdjustment:R30C6 |
| Taiwan (China) | 2028 | Gas | 0.486 | 0.42075 | 0.06525 | MAPPED | Demand:PowerMixAdjustment:R31C6 |
| South Korea | 2030 | Gas | 0.294 | 0.23212 | 0.06188 | MAPPED | Demand:PowerMixAdjustment:R28C6 |
| Taiwan (China) | 2026 | Gas | 0.474 | 0.414856 | 0.059144 | MAPPED | Demand:PowerMixAdjustment:R29C6 |
| United Kingdom | 2028 | Gas | 0.26 | 0.2012 | 0.0588 | MAPPED | Demand:PowerMixAdjustment:R66C6 |
| Netherlands | 2027 | Gas | 0.337073 | 0.278563 | 0.05851 | MAPPED | Demand:PowerMixAdjustment:R55C6 |
| Netherlands | 2026 | Gas | 0.31819 | 0.263815 | 0.054375 | MAPPED | Demand:PowerMixAdjustment:R54C6 |
| Taiwan (China) | 2029 | Gas | 0.469 | 0.420462 | 0.048538 | MAPPED | Demand:PowerMixAdjustment:R32C6 |
| South Korea | 2029 | Gas | 0.286 | 0.238232 | 0.047768 | MAPPED | Demand:PowerMixAdjustment:R27C6 |
| Taiwan (China) | 2030 | Gas | 0.457 | 0.41663 | 0.04037 | MAPPED | Demand:PowerMixAdjustment:R33C6 |
| South Korea | 2028 | Gas | 0.276 | 0.240268 | 0.035732 | MAPPED | Demand:PowerMixAdjustment:R26C6 |
| Japan | 2025 | Gas | 0.3 | 0.334905 | -0.034905 | MAPPED | Demand:PowerMixAdjustment:R18C6 |
| South Korea | 2026 | Gas | 0.285 | 0.25467 | 0.03033 | MAPPED | Demand:PowerMixAdjustment:R24C6 |
| United Kingdom | 2026 | Gas | 0.29 | 0.259779 | 0.030221 | MAPPED | Demand:PowerMixAdjustment:R64C6 |
| France | 2030 | Gas | 0.032 | 0.05885 | -0.02685 | MAPPED | Demand:PowerMixAdjustment:R43C6 |
| Japan | 2029 | Gas | 0.294 | 0.317236 | -0.023236 | MAPPED | Demand:PowerMixAdjustment:R22C6 |
| France | 2029 | Gas | 0.031 | 0.05155 | -0.02055 | MAPPED | Demand:PowerMixAdjustment:R42C6 |
| South Korea | 2027 | Gas | 0.265 | 0.247412 | 0.017588 | MAPPED | Demand:PowerMixAdjustment:R25C6 |
| Japan | 2028 | Gas | 0.309 | 0.326225 | -0.017225 | MAPPED | Demand:PowerMixAdjustment:R21C6 |
| Germany | 2030 | Gas | 0.099 | 0.114864 | -0.015864 | MAPPED | Demand:PowerMixAdjustment:R38C6 |
| Italy | 2029 | Gas | 0.375 | 0.359497 | 0.015503 | MAPPED | Demand:PowerMixAdjustment:R47C6 |
| Italy | 2026 | Gas | 0.434 | 0.420837 | 0.013163 | MAPPED | Demand:PowerMixAdjustment:R44C6 |
| France | 2028 | Gas | 0.038 | 0.051129 | -0.013129 | MAPPED | Demand:PowerMixAdjustment:R41C6 |
| Japan | 2027 | Gas | 0.318 | 0.327673 | -0.009673 | MAPPED | Demand:PowerMixAdjustment:R20C6 |
| China | 2030 | Gas | 0.0374 | 0.04545 | -0.00805 | MAPPED | Demand:PowerMixAdjustment:R17C6 |
| Germany | 2027 | Gas | 0.13 | 0.137767 | -0.007767 | MAPPED | Demand:PowerMixAdjustment:R35C6 |
| Italy | 2028 | Gas | 0.39 | 0.382567 | 0.007433 | MAPPED | Demand:PowerMixAdjustment:R46C6 |
| Japan | 2026 | Gas | 0.323 | 0.330277 | -0.007277 | MAPPED | Demand:PowerMixAdjustment:R19C6 |
| China | 2029 | Gas | 0.0372 | 0.04415 | -0.00695 | MAPPED | Demand:PowerMixAdjustment:R16C6 |
| China | 2026 | Gas | 0.0346 | 0.04115 | -0.00655 | MAPPED | Demand:PowerMixAdjustment:R13C6 |
| Germany | 2026 | Gas | 0.135 | 0.140848 | -0.005848 | MAPPED | Demand:PowerMixAdjustment:R34C6 |
| China | 2028 | Gas | 0.0374 | 0.04291 | -0.00551 | MAPPED | Demand:PowerMixAdjustment:R15C6 |
| China | 2027 | Gas | 0.0365 | 0.04193 | -0.00543 | MAPPED | Demand:PowerMixAdjustment:R14C6 |
| Japan | 2030 | Gas | 0.306 | 0.311386 | -0.005386 | MAPPED | Demand:PowerMixAdjustment:R23C6 |
| China | 2025 | Gas | 0.036 | 0.04058 | -0.00458 | MAPPED | Demand:PowerMixAdjustment:R12C6 |
| Germany | 2028 | Gas | 0.125 | 0.120666 | 0.004334 | MAPPED | Demand:PowerMixAdjustment:R36C6 |
| Germany | 2029 | Gas | 0.111 | 0.115228 | -0.004228 | MAPPED | Demand:PowerMixAdjustment:R37C6 |
| France | 2027 | Gas | 0.034 | 0.0369 | -0.0029 | MAPPED | Demand:PowerMixAdjustment:R40C6 |
| Italy | 2030 | Gas | 0.336 | 0.337147 | -0.001147 | MAPPED | Demand:PowerMixAdjustment:R48C6 |
| Italy | 2027 | Gas | 0.422 | 0.42148 | 0.00052 | MAPPED | Demand:PowerMixAdjustment:R45C6 |
| France | 2026 | Gas | 0.042 | 0.04181 | 0.00019 | MAPPED | Demand:PowerMixAdjustment:R39C6 |

### 4.4 Temperature

basecase 150개 중 값 차이가 큰 순서로 최대 100개를 표시한다.

| Country | Year | Month | basecase_value | lut_value | value_diff | mapping_status | reference_id |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Italy | 2026 | 1 | 6.8 | 3.112625 | 3.687375 | MAPPED | Demand:WeatherAdjustment:R117C15 |
| Italy | 2027 | 1 | 6.8 | 3.112625 | 3.687375 | MAPPED | Demand:WeatherAdjustment:R120C15 |
| Italy | 2028 | 1 | 6.8 | 3.112625 | 3.687375 | MAPPED | Demand:WeatherAdjustment:R123C15 |
| Italy | 2029 | 1 | 6.8 | 3.112625 | 3.687375 | MAPPED | Demand:WeatherAdjustment:R126C15 |
| Italy | 2030 | 1 | 6.8 | 3.112625 | 3.687375 | MAPPED | Demand:WeatherAdjustment:R129C15 |
| Italy | 2026 | 2 | 7.7 | 4.58881 | 3.11119 | MAPPED | Demand:WeatherAdjustment:R118C15 |
| Italy | 2027 | 2 | 7.7 | 4.58881 | 3.11119 | MAPPED | Demand:WeatherAdjustment:R121C15 |
| Italy | 2028 | 2 | 7.7 | 4.58881 | 3.11119 | MAPPED | Demand:WeatherAdjustment:R124C15 |
| Italy | 2029 | 2 | 7.7 | 4.58881 | 3.11119 | MAPPED | Demand:WeatherAdjustment:R127C15 |
| Italy | 2030 | 2 | 7.7 | 4.58881 | 3.11119 | MAPPED | Demand:WeatherAdjustment:R130C15 |
| China | 2026 | 2 | 5 | 2.099173 | 2.900827 | MAPPED | Demand:WeatherAdjustment:R13C15 |
| China | 2027 | 2 | 5 | 2.099173 | 2.900827 | MAPPED | Demand:WeatherAdjustment:R16C15 |
| China | 2028 | 2 | 5 | 2.099173 | 2.900827 | MAPPED | Demand:WeatherAdjustment:R19C15 |
| China | 2029 | 2 | 5 | 2.099173 | 2.900827 | MAPPED | Demand:WeatherAdjustment:R22C15 |
| China | 2030 | 2 | 5 | 2.099173 | 2.900827 | MAPPED | Demand:WeatherAdjustment:R25C15 |
| Japan | 2026 | 2 | 6.1 | 3.27696 | 2.82304 | MAPPED | Demand:WeatherAdjustment:R28C15 |
| Japan | 2027 | 2 | 6.1 | 3.27696 | 2.82304 | MAPPED | Demand:WeatherAdjustment:R31C15 |
| Japan | 2028 | 2 | 6.1 | 3.27696 | 2.82304 | MAPPED | Demand:WeatherAdjustment:R34C15 |
| Japan | 2029 | 2 | 6.1 | 3.27696 | 2.82304 | MAPPED | Demand:WeatherAdjustment:R37C15 |
| Japan | 2030 | 2 | 6.1 | 3.27696 | 2.82304 | MAPPED | Demand:WeatherAdjustment:R40C15 |
| Japan | 2026 | 1 | 5.5 | 2.742657 | 2.757343 | MAPPED | Demand:WeatherAdjustment:R27C15 |
| Japan | 2027 | 1 | 5.5 | 2.742657 | 2.757343 | MAPPED | Demand:WeatherAdjustment:R30C15 |
| Japan | 2028 | 1 | 5.5 | 2.742657 | 2.757343 | MAPPED | Demand:WeatherAdjustment:R33C15 |
| Japan | 2029 | 1 | 5.5 | 2.742657 | 2.757343 | MAPPED | Demand:WeatherAdjustment:R36C15 |
| Japan | 2030 | 1 | 5.5 | 2.742657 | 2.757343 | MAPPED | Demand:WeatherAdjustment:R39C15 |
| Italy | 2026 | 3 | 10.2 | 7.523671 | 2.676329 | MAPPED | Demand:WeatherAdjustment:R119C15 |
| Italy | 2027 | 3 | 10.2 | 7.523671 | 2.676329 | MAPPED | Demand:WeatherAdjustment:R122C15 |
| Italy | 2028 | 3 | 10.2 | 7.523671 | 2.676329 | MAPPED | Demand:WeatherAdjustment:R125C15 |
| Italy | 2029 | 3 | 10.2 | 7.523671 | 2.676329 | MAPPED | Demand:WeatherAdjustment:R128C15 |
| Italy | 2030 | 3 | 10.2 | 7.523671 | 2.676329 | MAPPED | Demand:WeatherAdjustment:R131C15 |
| Japan | 2026 | 3 | 9.2 | 6.657506 | 2.542494 | MAPPED | Demand:WeatherAdjustment:R29C15 |
| Japan | 2027 | 3 | 9.2 | 6.657506 | 2.542494 | MAPPED | Demand:WeatherAdjustment:R32C15 |
| Japan | 2028 | 3 | 9.2 | 6.657506 | 2.542494 | MAPPED | Demand:WeatherAdjustment:R35C15 |
| Japan | 2029 | 3 | 9.2 | 6.657506 | 2.542494 | MAPPED | Demand:WeatherAdjustment:R38C15 |
| Japan | 2030 | 3 | 9.2 | 6.657506 | 2.542494 | MAPPED | Demand:WeatherAdjustment:R41C15 |
| China | 2026 | 3 | 10.4 | 7.877081 | 2.522919 | MAPPED | Demand:WeatherAdjustment:R14C15 |
| China | 2027 | 3 | 10.4 | 7.877081 | 2.522919 | MAPPED | Demand:WeatherAdjustment:R17C15 |
| China | 2028 | 3 | 10.4 | 7.877081 | 2.522919 | MAPPED | Demand:WeatherAdjustment:R20C15 |
| China | 2029 | 3 | 10.4 | 7.877081 | 2.522919 | MAPPED | Demand:WeatherAdjustment:R23C15 |
| China | 2030 | 3 | 10.4 | 7.877081 | 2.522919 | MAPPED | Demand:WeatherAdjustment:R26C15 |
| China | 2026 | 1 | 2.3 | 0.013969 | 2.286031 | MAPPED | Demand:WeatherAdjustment:R12C15 |
| China | 2027 | 1 | 2.3 | 0.013969 | 2.286031 | MAPPED | Demand:WeatherAdjustment:R15C15 |
| China | 2028 | 1 | 2.3 | 0.013969 | 2.286031 | MAPPED | Demand:WeatherAdjustment:R18C15 |
| China | 2029 | 1 | 2.3 | 0.013969 | 2.286031 | MAPPED | Demand:WeatherAdjustment:R21C15 |
| China | 2030 | 1 | 2.3 | 0.013969 | 2.286031 | MAPPED | Demand:WeatherAdjustment:R24C15 |
| South Korea | 2026 | 1 | -2.2 | -0.434997 | -1.765003 | MAPPED | Demand:WeatherAdjustment:R42C15 |
| South Korea | 2027 | 1 | -2.2 | -0.434997 | -1.765003 | MAPPED | Demand:WeatherAdjustment:R45C15 |
| South Korea | 2028 | 1 | -2.2 | -0.434997 | -1.765003 | MAPPED | Demand:WeatherAdjustment:R48C15 |
| South Korea | 2029 | 1 | -2.2 | -0.434997 | -1.765003 | MAPPED | Demand:WeatherAdjustment:R51C15 |
| South Korea | 2030 | 1 | -2.2 | -0.434997 | -1.765003 | MAPPED | Demand:WeatherAdjustment:R54C15 |
| Spain | 2026 | 3 | 11.3 | 9.834645 | 1.465355 | MAPPED | Demand:WeatherAdjustment:R104C15 |
| Spain | 2027 | 3 | 11.3 | 9.834645 | 1.465355 | MAPPED | Demand:WeatherAdjustment:R107C15 |
| Spain | 2028 | 3 | 11.3 | 9.834645 | 1.465355 | MAPPED | Demand:WeatherAdjustment:R110C15 |
| Spain | 2029 | 3 | 11.3 | 9.834645 | 1.465355 | MAPPED | Demand:WeatherAdjustment:R113C15 |
| Spain | 2030 | 3 | 11.3 | 9.834645 | 1.465355 | MAPPED | Demand:WeatherAdjustment:R116C15 |
| United Kingdom | 2026 | 1 | 4.8 | 6.186471 | -1.386471 | MAPPED | Demand:WeatherAdjustment:R147C15 |
| United Kingdom | 2027 | 1 | 4.8 | 6.186471 | -1.386471 | MAPPED | Demand:WeatherAdjustment:R150C15 |
| United Kingdom | 2028 | 1 | 4.8 | 6.186471 | -1.386471 | MAPPED | Demand:WeatherAdjustment:R153C15 |
| United Kingdom | 2029 | 1 | 4.8 | 6.186471 | -1.386471 | MAPPED | Demand:WeatherAdjustment:R156C15 |
| United Kingdom | 2030 | 1 | 4.8 | 6.186471 | -1.386471 | MAPPED | Demand:WeatherAdjustment:R159C15 |
| Spain | 2026 | 2 | 9 | 7.924881 | 1.075119 | MAPPED | Demand:WeatherAdjustment:R103C15 |
| Spain | 2027 | 2 | 9 | 7.924881 | 1.075119 | MAPPED | Demand:WeatherAdjustment:R106C15 |
| Spain | 2028 | 2 | 9 | 7.924881 | 1.075119 | MAPPED | Demand:WeatherAdjustment:R109C15 |
| Spain | 2029 | 2 | 9 | 7.924881 | 1.075119 | MAPPED | Demand:WeatherAdjustment:R112C15 |
| Spain | 2030 | 2 | 9 | 7.924881 | 1.075119 | MAPPED | Demand:WeatherAdjustment:R115C15 |
| United Kingdom | 2026 | 2 | 5.2 | 6.184708 | -0.984708 | MAPPED | Demand:WeatherAdjustment:R148C15 |
| United Kingdom | 2027 | 2 | 5.2 | 6.184708 | -0.984708 | MAPPED | Demand:WeatherAdjustment:R151C15 |
| United Kingdom | 2028 | 2 | 5.2 | 6.184708 | -0.984708 | MAPPED | Demand:WeatherAdjustment:R154C15 |
| United Kingdom | 2029 | 2 | 5.2 | 6.184708 | -0.984708 | MAPPED | Demand:WeatherAdjustment:R157C15 |
| United Kingdom | 2030 | 2 | 5.2 | 6.184708 | -0.984708 | MAPPED | Demand:WeatherAdjustment:R160C15 |
| South Korea | 2026 | 2 | 0.2 | 1.179342 | -0.979342 | MAPPED | Demand:WeatherAdjustment:R43C15 |
| South Korea | 2027 | 2 | 0.2 | 1.179342 | -0.979342 | MAPPED | Demand:WeatherAdjustment:R46C15 |
| South Korea | 2028 | 2 | 0.2 | 1.179342 | -0.979342 | MAPPED | Demand:WeatherAdjustment:R49C15 |
| South Korea | 2029 | 2 | 0.2 | 1.179342 | -0.979342 | MAPPED | Demand:WeatherAdjustment:R52C15 |
| South Korea | 2030 | 2 | 0.2 | 1.179342 | -0.979342 | MAPPED | Demand:WeatherAdjustment:R55C15 |
| South Korea | 2026 | 3 | 5.4 | 6.355886 | -0.955886 | MAPPED | Demand:WeatherAdjustment:R44C15 |
| South Korea | 2027 | 3 | 5.4 | 6.355886 | -0.955886 | MAPPED | Demand:WeatherAdjustment:R47C15 |
| South Korea | 2028 | 3 | 5.4 | 6.355886 | -0.955886 | MAPPED | Demand:WeatherAdjustment:R50C15 |
| South Korea | 2029 | 3 | 5.4 | 6.355886 | -0.955886 | MAPPED | Demand:WeatherAdjustment:R53C15 |
| South Korea | 2030 | 3 | 5.4 | 6.355886 | -0.955886 | MAPPED | Demand:WeatherAdjustment:R56C15 |
| Spain | 2026 | 1 | 7.9 | 7.051704 | 0.848296 | MAPPED | Demand:WeatherAdjustment:R102C15 |
| Spain | 2027 | 1 | 7.9 | 7.051704 | 0.848296 | MAPPED | Demand:WeatherAdjustment:R105C15 |
| Spain | 2028 | 1 | 7.9 | 7.051704 | 0.848296 | MAPPED | Demand:WeatherAdjustment:R108C15 |
| Spain | 2029 | 1 | 7.9 | 7.051704 | 0.848296 | MAPPED | Demand:WeatherAdjustment:R111C15 |
| Spain | 2030 | 1 | 7.9 | 7.051704 | 0.848296 | MAPPED | Demand:WeatherAdjustment:R114C15 |
| France | 2026 | 2 | 5.9 | 5.197325 | 0.702675 | MAPPED | Demand:WeatherAdjustment:R73C15 |
| France | 2027 | 2 | 5.9 | 5.197325 | 0.702675 | MAPPED | Demand:WeatherAdjustment:R76C15 |
| France | 2028 | 2 | 5.9 | 5.197325 | 0.702675 | MAPPED | Demand:WeatherAdjustment:R79C15 |
| France | 2029 | 2 | 5.9 | 5.197325 | 0.702675 | MAPPED | Demand:WeatherAdjustment:R82C15 |
| France | 2030 | 2 | 5.9 | 5.197325 | 0.702675 | MAPPED | Demand:WeatherAdjustment:R85C15 |
| France | 2026 | 1 | 5.1 | 4.439233 | 0.660767 | MAPPED | Demand:WeatherAdjustment:R72C15 |
| France | 2027 | 1 | 5.1 | 4.439233 | 0.660767 | MAPPED | Demand:WeatherAdjustment:R75C15 |
| France | 2028 | 1 | 5.1 | 4.439233 | 0.660767 | MAPPED | Demand:WeatherAdjustment:R78C15 |
| France | 2029 | 1 | 5.1 | 4.439233 | 0.660767 | MAPPED | Demand:WeatherAdjustment:R81C15 |
| France | 2030 | 1 | 5.1 | 4.439233 | 0.660767 | MAPPED | Demand:WeatherAdjustment:R84C15 |
| Germany | 2026 | 2 | 2.3 | 1.681157 | 0.618843 | MAPPED | Demand:WeatherAdjustment:R58C15 |
| Germany | 2027 | 2 | 2.3 | 1.681157 | 0.618843 | MAPPED | Demand:WeatherAdjustment:R61C15 |
| Germany | 2028 | 2 | 2.3 | 1.681157 | 0.618843 | MAPPED | Demand:WeatherAdjustment:R64C15 |
| Germany | 2029 | 2 | 2.3 | 1.681157 | 0.618843 | MAPPED | Demand:WeatherAdjustment:R67C15 |
| Germany | 2030 | 2 | 2.3 | 1.681157 | 0.618843 | MAPPED | Demand:WeatherAdjustment:R70C15 |

### 4.5 LiqUtilAdjustment

basecase 21,656개 중 UNMAPPED 87개를 우선 표시하고, 남은 공간은 값 차이가 큰 row를 표시한다.

| Country | LNG Plant | LNG Plant Train | Year | Month | Period_base | Period_lut | basecase_value | lut_value | value_diff | mapping_status | Life Cycle Category_base | Life Cycle Category_lut | Nameplate Capacity_base | Nameplate Capacity_lut | period_match | lifecycle_match | capacity_match | reference_id |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Mozambique | Coral North FLNG | Coral North FLNG | 2025 | 1 | 85 |  | 0 |  |  | UNMAPPED | Planned |  | 3.4 |  |  |  |  | Supply:LiqUtilAdjustment:R314C22 |
| Mozambique | Coral North FLNG | Coral North FLNG | 2025 | 2 | 86 |  | 0 |  |  | UNMAPPED | Planned |  | 3.4 |  |  |  |  | Supply:LiqUtilAdjustment:R314C23 |
| Mozambique | Coral North FLNG | Coral North FLNG | 2025 | 3 | 87 |  | 0 |  |  | UNMAPPED | Planned |  | 3.4 |  |  |  |  | Supply:LiqUtilAdjustment:R314C24 |
| Mozambique | Coral North FLNG | Coral North FLNG | 2025 | 4 | 88 |  | 0 |  |  | UNMAPPED | Planned |  | 3.4 |  |  |  |  | Supply:LiqUtilAdjustment:R314C25 |
| Mozambique | Coral North FLNG | Coral North FLNG | 2025 | 5 | 89 |  | 0 |  |  | UNMAPPED | Planned |  | 3.4 |  |  |  |  | Supply:LiqUtilAdjustment:R314C26 |
| Mozambique | Coral North FLNG | Coral North FLNG | 2025 | 6 | 90 |  | 0 |  |  | UNMAPPED | Planned |  | 3.4 |  |  |  |  | Supply:LiqUtilAdjustment:R314C27 |
| Mozambique | Coral North FLNG | Coral North FLNG | 2025 | 7 | 91 |  | 0 |  |  | UNMAPPED | Planned |  | 3.4 |  |  |  |  | Supply:LiqUtilAdjustment:R314C28 |
| Mozambique | Coral North FLNG | Coral North FLNG | 2025 | 8 | 92 |  | 0 |  |  | UNMAPPED | Planned |  | 3.4 |  |  |  |  | Supply:LiqUtilAdjustment:R314C29 |
| Mozambique | Coral North FLNG | Coral North FLNG | 2025 | 9 | 93 |  | 0 |  |  | UNMAPPED | Planned |  | 3.4 |  |  |  |  | Supply:LiqUtilAdjustment:R314C30 |
| Mozambique | Coral North FLNG | Coral North FLNG | 2025 | 10 | 94 |  | 0 |  |  | UNMAPPED | Planned |  | 3.4 |  |  |  |  | Supply:LiqUtilAdjustment:R314C31 |
| Mozambique | Coral North FLNG | Coral North FLNG | 2025 | 11 | 95 |  | 0 |  |  | UNMAPPED | Planned |  | 3.4 |  |  |  |  | Supply:LiqUtilAdjustment:R314C32 |
| Mozambique | Coral North FLNG | Coral North FLNG | 2025 | 12 | 96 |  | 0 |  |  | UNMAPPED | Planned |  | 3.4 |  |  |  |  | Supply:LiqUtilAdjustment:R314C33 |
| Mozambique | Coral North FLNG | Coral North FLNG | 2026 | 1 | 97 |  | 0 |  |  | UNMAPPED | Planned |  | 3.4 |  |  |  |  | Supply:LiqUtilAdjustment:R314C34 |
| Mozambique | Coral North FLNG | Coral North FLNG | 2026 | 2 | 98 |  | 0 |  |  | UNMAPPED | Planned |  | 3.4 |  |  |  |  | Supply:LiqUtilAdjustment:R314C35 |
| Mozambique | Coral North FLNG | Coral North FLNG | 2026 | 3 | 99 |  | 0 |  |  | UNMAPPED | Planned |  | 3.4 |  |  |  |  | Supply:LiqUtilAdjustment:R314C36 |
| Mozambique | Coral North FLNG | Coral North FLNG | 2026 | 4 | 100 |  | 0 |  |  | UNMAPPED | Planned |  | 3.4 |  |  |  |  | Supply:LiqUtilAdjustment:R314C37 |
| Mozambique | Coral North FLNG | Coral North FLNG | 2026 | 5 | 101 |  | 0 |  |  | UNMAPPED | Planned |  | 3.4 |  |  |  |  | Supply:LiqUtilAdjustment:R314C38 |
| Mozambique | Coral North FLNG | Coral North FLNG | 2026 | 6 | 102 |  | 0 |  |  | UNMAPPED | Planned |  | 3.4 |  |  |  |  | Supply:LiqUtilAdjustment:R314C39 |
| Mozambique | Coral North FLNG | Coral North FLNG | 2026 | 7 | 103 |  | 0 |  |  | UNMAPPED | Planned |  | 3.4 |  |  |  |  | Supply:LiqUtilAdjustment:R314C40 |
| Mozambique | Coral North FLNG | Coral North FLNG | 2026 | 8 | 104 |  | 0 |  |  | UNMAPPED | Planned |  | 3.4 |  |  |  |  | Supply:LiqUtilAdjustment:R314C41 |
| Mozambique | Coral North FLNG | Coral North FLNG | 2026 | 9 | 105 |  | 0 |  |  | UNMAPPED | Planned |  | 3.4 |  |  |  |  | Supply:LiqUtilAdjustment:R314C42 |
| Mozambique | Coral North FLNG | Coral North FLNG | 2026 | 10 | 106 |  | 0 |  |  | UNMAPPED | Planned |  | 3.4 |  |  |  |  | Supply:LiqUtilAdjustment:R314C43 |
| Mozambique | Coral North FLNG | Coral North FLNG | 2026 | 11 | 107 |  | 0 |  |  | UNMAPPED | Planned |  | 3.4 |  |  |  |  | Supply:LiqUtilAdjustment:R314C44 |
| Mozambique | Coral North FLNG | Coral North FLNG | 2026 | 12 | 108 |  | 0 |  |  | UNMAPPED | Planned |  | 3.4 |  |  |  |  | Supply:LiqUtilAdjustment:R314C45 |
| Argentina | Pan American LNG | Pan American LNG | 2023 | 10 | 70 |  | 0 |  |  | UNMAPPED | Planned |  | 2.45 |  |  |  |  | Supply:LiqUtilAdjustment:R316C7 |
| Argentina | Pan American LNG | Pan American LNG | 2023 | 11 | 71 |  | 0 |  |  | UNMAPPED | Planned |  | 2.45 |  |  |  |  | Supply:LiqUtilAdjustment:R316C8 |
| Argentina | Pan American LNG | Pan American LNG | 2023 | 12 | 72 |  | 0 |  |  | UNMAPPED | Planned |  | 2.45 |  |  |  |  | Supply:LiqUtilAdjustment:R316C9 |
| Argentina | Pan American LNG | Pan American LNG | 2024 | 1 | 73 |  | 0 |  |  | UNMAPPED | Planned |  | 2.45 |  |  |  |  | Supply:LiqUtilAdjustment:R316C10 |
| Argentina | Pan American LNG | Pan American LNG | 2024 | 2 | 74 |  | 0 |  |  | UNMAPPED | Planned |  | 2.45 |  |  |  |  | Supply:LiqUtilAdjustment:R316C11 |
| Argentina | Pan American LNG | Pan American LNG | 2024 | 3 | 75 |  | 0 |  |  | UNMAPPED | Planned |  | 2.45 |  |  |  |  | Supply:LiqUtilAdjustment:R316C12 |
| Argentina | Pan American LNG | Pan American LNG | 2024 | 4 | 76 |  | 0 |  |  | UNMAPPED | Planned |  | 2.45 |  |  |  |  | Supply:LiqUtilAdjustment:R316C13 |
| Argentina | Pan American LNG | Pan American LNG | 2024 | 5 | 77 |  | 0 |  |  | UNMAPPED | Planned |  | 2.45 |  |  |  |  | Supply:LiqUtilAdjustment:R316C14 |
| Argentina | Pan American LNG | Pan American LNG | 2024 | 6 | 78 |  | 0 |  |  | UNMAPPED | Planned |  | 2.45 |  |  |  |  | Supply:LiqUtilAdjustment:R316C15 |
| Argentina | Pan American LNG | Pan American LNG | 2024 | 7 | 79 |  | 0 |  |  | UNMAPPED | Planned |  | 2.45 |  |  |  |  | Supply:LiqUtilAdjustment:R316C16 |
| Argentina | Pan American LNG | Pan American LNG | 2024 | 8 | 80 |  | 0 |  |  | UNMAPPED | Planned |  | 2.45 |  |  |  |  | Supply:LiqUtilAdjustment:R316C17 |
| Argentina | Pan American LNG | Pan American LNG | 2024 | 9 | 81 |  | 0 |  |  | UNMAPPED | Planned |  | 2.45 |  |  |  |  | Supply:LiqUtilAdjustment:R316C18 |
| Argentina | Pan American LNG | Pan American LNG | 2024 | 10 | 82 |  | 0 |  |  | UNMAPPED | Planned |  | 2.45 |  |  |  |  | Supply:LiqUtilAdjustment:R316C19 |
| Argentina | Pan American LNG | Pan American LNG | 2024 | 11 | 83 |  | 0 |  |  | UNMAPPED | Planned |  | 2.45 |  |  |  |  | Supply:LiqUtilAdjustment:R316C20 |
| Argentina | Pan American LNG | Pan American LNG | 2024 | 12 | 84 |  | 0 |  |  | UNMAPPED | Planned |  | 2.45 |  |  |  |  | Supply:LiqUtilAdjustment:R316C21 |
| Argentina | Pan American LNG | Pan American LNG | 2025 | 1 | 85 |  | 0 |  |  | UNMAPPED | Planned |  | 2.45 |  |  |  |  | Supply:LiqUtilAdjustment:R316C22 |
| Argentina | Pan American LNG | Pan American LNG | 2025 | 2 | 86 |  | 0 |  |  | UNMAPPED | Planned |  | 2.45 |  |  |  |  | Supply:LiqUtilAdjustment:R316C23 |
| Argentina | Pan American LNG | Pan American LNG | 2025 | 3 | 87 |  | 0 |  |  | UNMAPPED | Planned |  | 2.45 |  |  |  |  | Supply:LiqUtilAdjustment:R316C24 |
| Argentina | Pan American LNG | Pan American LNG | 2025 | 4 | 88 |  | 0 |  |  | UNMAPPED | Planned |  | 2.45 |  |  |  |  | Supply:LiqUtilAdjustment:R316C25 |
| Argentina | Pan American LNG | Pan American LNG | 2025 | 5 | 89 |  | 0 |  |  | UNMAPPED | Planned |  | 2.45 |  |  |  |  | Supply:LiqUtilAdjustment:R316C26 |
| Argentina | Pan American LNG | Pan American LNG | 2025 | 6 | 90 |  | 0 |  |  | UNMAPPED | Planned |  | 2.45 |  |  |  |  | Supply:LiqUtilAdjustment:R316C27 |
| Argentina | Pan American LNG | Pan American LNG | 2025 | 7 | 91 |  | 0 |  |  | UNMAPPED | Planned |  | 2.45 |  |  |  |  | Supply:LiqUtilAdjustment:R316C28 |
| Argentina | Pan American LNG | Pan American LNG | 2025 | 8 | 92 |  | 0 |  |  | UNMAPPED | Planned |  | 2.45 |  |  |  |  | Supply:LiqUtilAdjustment:R316C29 |
| Argentina | Pan American LNG | Pan American LNG | 2025 | 9 | 93 |  | 0 |  |  | UNMAPPED | Planned |  | 2.45 |  |  |  |  | Supply:LiqUtilAdjustment:R316C30 |
| Argentina | Pan American LNG | Pan American LNG | 2025 | 10 | 94 |  | 0 |  |  | UNMAPPED | Planned |  | 2.45 |  |  |  |  | Supply:LiqUtilAdjustment:R316C31 |
| Argentina | Pan American LNG | Pan American LNG | 2025 | 11 | 95 |  | 0 |  |  | UNMAPPED | Planned |  | 2.45 |  |  |  |  | Supply:LiqUtilAdjustment:R316C32 |
| Argentina | Pan American LNG | Pan American LNG | 2025 | 12 | 96 |  | 0 |  |  | UNMAPPED | Planned |  | 2.45 |  |  |  |  | Supply:LiqUtilAdjustment:R316C33 |
| Mexico | Mexico Pacific Limited LNG | Mexico Pacific Limited LNG T3 (Phase 2) | 2026 | 1 | 97 |  | 0 |  |  | UNMAPPED | Planned |  | 4.7 |  |  |  |  | Supply:LiqUtilAdjustment:R354C34 |
| Mexico | Mexico Pacific Limited LNG | Mexico Pacific Limited LNG T3 (Phase 2) | 2026 | 2 | 98 |  | 0 |  |  | UNMAPPED | Planned |  | 4.7 |  |  |  |  | Supply:LiqUtilAdjustment:R354C35 |
| Mexico | Mexico Pacific Limited LNG | Mexico Pacific Limited LNG T3 (Phase 2) | 2026 | 3 | 99 |  | 0 |  |  | UNMAPPED | Planned |  | 4.7 |  |  |  |  | Supply:LiqUtilAdjustment:R354C36 |
| Mexico | Mexico Pacific Limited LNG | Mexico Pacific Limited LNG T3 (Phase 2) | 2026 | 4 | 100 |  | 0 |  |  | UNMAPPED | Planned |  | 4.7 |  |  |  |  | Supply:LiqUtilAdjustment:R354C37 |
| Mexico | Mexico Pacific Limited LNG | Mexico Pacific Limited LNG T3 (Phase 2) | 2026 | 5 | 101 |  | 0 |  |  | UNMAPPED | Planned |  | 4.7 |  |  |  |  | Supply:LiqUtilAdjustment:R354C38 |
| Mexico | Mexico Pacific Limited LNG | Mexico Pacific Limited LNG T3 (Phase 2) | 2026 | 6 | 102 |  | 0 |  |  | UNMAPPED | Planned |  | 4.7 |  |  |  |  | Supply:LiqUtilAdjustment:R354C39 |
| Mexico | Mexico Pacific Limited LNG | Mexico Pacific Limited LNG T3 (Phase 2) | 2026 | 7 | 103 |  | 0 |  |  | UNMAPPED | Planned |  | 4.7 |  |  |  |  | Supply:LiqUtilAdjustment:R354C40 |
| Mexico | Mexico Pacific Limited LNG | Mexico Pacific Limited LNG T3 (Phase 2) | 2026 | 8 | 104 |  | 0 |  |  | UNMAPPED | Planned |  | 4.7 |  |  |  |  | Supply:LiqUtilAdjustment:R354C41 |
| Mexico | Mexico Pacific Limited LNG | Mexico Pacific Limited LNG T3 (Phase 2) | 2026 | 9 | 105 |  | 0 |  |  | UNMAPPED | Planned |  | 4.7 |  |  |  |  | Supply:LiqUtilAdjustment:R354C42 |
| Mexico | Mexico Pacific Limited LNG | Mexico Pacific Limited LNG T3 (Phase 2) | 2026 | 10 | 106 |  | 0 |  |  | UNMAPPED | Planned |  | 4.7 |  |  |  |  | Supply:LiqUtilAdjustment:R354C43 |
| Mexico | Mexico Pacific Limited LNG | Mexico Pacific Limited LNG T3 (Phase 2) | 2026 | 11 | 107 |  | 0 |  |  | UNMAPPED | Planned |  | 4.7 |  |  |  |  | Supply:LiqUtilAdjustment:R354C44 |
| Mexico | Mexico Pacific Limited LNG | Mexico Pacific Limited LNG T3 (Phase 2) | 2026 | 12 | 108 |  | 0 |  |  | UNMAPPED | Planned |  | 4.7 |  |  |  |  | Supply:LiqUtilAdjustment:R354C45 |
| Mexico | Mexico Pacific Limited LNG | Mexico Pacific Limited LNG T3 (Phase 2) | 2027 | 1 | 109 |  | 0 |  |  | UNMAPPED | Planned |  | 4.7 |  |  |  |  | Supply:LiqUtilAdjustment:R354C46 |
| Mexico | Mexico Pacific Limited LNG | Mexico Pacific Limited LNG T3 (Phase 2) | 2027 | 2 | 110 |  | 0 |  |  | UNMAPPED | Planned |  | 4.7 |  |  |  |  | Supply:LiqUtilAdjustment:R354C47 |
| Mexico | Mexico Pacific Limited LNG | Mexico Pacific Limited LNG T3 (Phase 2) | 2027 | 3 | 111 |  | 0 |  |  | UNMAPPED | Planned |  | 4.7 |  |  |  |  | Supply:LiqUtilAdjustment:R354C48 |
| Mexico | Mexico Pacific Limited LNG | Mexico Pacific Limited LNG T3 (Phase 2) | 2027 | 4 | 112 |  | 0 |  |  | UNMAPPED | Planned |  | 4.7 |  |  |  |  | Supply:LiqUtilAdjustment:R354C49 |
| Mexico | Mexico Pacific Limited LNG | Mexico Pacific Limited LNG T3 (Phase 2) | 2027 | 5 | 113 |  | 0 |  |  | UNMAPPED | Planned |  | 4.7 |  |  |  |  | Supply:LiqUtilAdjustment:R354C50 |
| Mexico | Mexico Pacific Limited LNG | Mexico Pacific Limited LNG T3 (Phase 2) | 2027 | 6 | 114 |  | 0 |  |  | UNMAPPED | Planned |  | 4.7 |  |  |  |  | Supply:LiqUtilAdjustment:R354C51 |
| Mexico | Mexico Pacific Limited LNG | Mexico Pacific Limited LNG T3 (Phase 2) | 2027 | 7 | 115 |  | 0 |  |  | UNMAPPED | Planned |  | 4.7 |  |  |  |  | Supply:LiqUtilAdjustment:R354C52 |
| Mexico | Mexico Pacific Limited LNG | Mexico Pacific Limited LNG T3 (Phase 2) | 2027 | 8 | 116 |  | 0 |  |  | UNMAPPED | Planned |  | 4.7 |  |  |  |  | Supply:LiqUtilAdjustment:R354C53 |
| Mexico | Mexico Pacific Limited LNG | Mexico Pacific Limited LNG T3 (Phase 2) | 2027 | 9 | 117 |  | 0 |  |  | UNMAPPED | Planned |  | 4.7 |  |  |  |  | Supply:LiqUtilAdjustment:R354C54 |
| Mexico | Mexico Pacific Limited LNG | Mexico Pacific Limited LNG T3 (Phase 2) | 2027 | 10 | 118 |  | 0 |  |  | UNMAPPED | Planned |  | 4.7 |  |  |  |  | Supply:LiqUtilAdjustment:R354C55 |
| Mexico | Mexico Pacific Limited LNG | Mexico Pacific Limited LNG T3 (Phase 2) | 2027 | 11 | 119 |  | 0 |  |  | UNMAPPED | Planned |  | 4.7 |  |  |  |  | Supply:LiqUtilAdjustment:R354C56 |
| Mexico | Mexico Pacific Limited LNG | Mexico Pacific Limited LNG T3 (Phase 2) | 2027 | 12 | 120 |  | 0 |  |  | UNMAPPED | Planned |  | 4.7 |  |  |  |  | Supply:LiqUtilAdjustment:R354C57 |
| Mexico | Mexico Pacific Limited LNG | Mexico Pacific Limited LNG T3 (Phase 2) | 2028 | 1 | 121 |  | 0 |  |  | UNMAPPED | Planned |  | 4.7 |  |  |  |  | Supply:LiqUtilAdjustment:R354C58 |
| Mexico | Mexico Pacific Limited LNG | Mexico Pacific Limited LNG T3 (Phase 2) | 2028 | 2 | 122 |  | 0 |  |  | UNMAPPED | Planned |  | 4.7 |  |  |  |  | Supply:LiqUtilAdjustment:R354C59 |
| Mexico | Mexico Pacific Limited LNG | Mexico Pacific Limited LNG T3 (Phase 2) | 2028 | 3 | 123 |  | 0 |  |  | UNMAPPED | Planned |  | 4.7 |  |  |  |  | Supply:LiqUtilAdjustment:R354C60 |
| Mexico | Mexico Pacific Limited LNG | Mexico Pacific Limited LNG T3 (Phase 2) | 2028 | 4 | 124 |  | 0 |  |  | UNMAPPED | Planned |  | 4.7 |  |  |  |  | Supply:LiqUtilAdjustment:R354C61 |
| Mexico | Mexico Pacific Limited LNG | Mexico Pacific Limited LNG T3 (Phase 2) | 2028 | 5 | 125 |  | 0 |  |  | UNMAPPED | Planned |  | 4.7 |  |  |  |  | Supply:LiqUtilAdjustment:R354C62 |
| Mexico | Mexico Pacific Limited LNG | Mexico Pacific Limited LNG T3 (Phase 2) | 2028 | 6 | 126 |  | 0 |  |  | UNMAPPED | Planned |  | 4.7 |  |  |  |  | Supply:LiqUtilAdjustment:R354C63 |
| Mexico | Mexico Pacific Limited LNG | Mexico Pacific Limited LNG T3 (Phase 2) | 2028 | 7 | 127 |  | 0 |  |  | UNMAPPED | Planned |  | 4.7 |  |  |  |  | Supply:LiqUtilAdjustment:R354C64 |
| Mexico | Mexico Pacific Limited LNG | Mexico Pacific Limited LNG T3 (Phase 2) | 2028 | 8 | 128 |  | 0 |  |  | UNMAPPED | Planned |  | 4.7 |  |  |  |  | Supply:LiqUtilAdjustment:R354C65 |
| Mexico | Mexico Pacific Limited LNG | Mexico Pacific Limited LNG T3 (Phase 2) | 2028 | 9 | 129 |  | 0 |  |  | UNMAPPED | Planned |  | 4.7 |  |  |  |  | Supply:LiqUtilAdjustment:R354C66 |
| Mexico | Mexico Pacific Limited LNG | Mexico Pacific Limited LNG T3 (Phase 2) | 2028 | 10 | 130 |  | 0 |  |  | UNMAPPED | Planned |  | 4.7 |  |  |  |  | Supply:LiqUtilAdjustment:R354C67 |
| Mexico | Mexico Pacific Limited LNG | Mexico Pacific Limited LNG T3 (Phase 2) | 2028 | 11 | 131 |  | 0 |  |  | UNMAPPED | Planned |  | 4.7 |  |  |  |  | Supply:LiqUtilAdjustment:R354C68 |
| Mexico | Mexico Pacific Limited LNG | Mexico Pacific Limited LNG T3 (Phase 2) | 2028 | 12 | 132 |  | 0 |  |  | UNMAPPED | Planned |  | 4.7 |  |  |  |  | Supply:LiqUtilAdjustment:R354C69 |
| Canada | Tilbury LNG | Tilbury LNG Phase 2 | 2030 | 1 | 145 | 145 | 3.307692 | 0.97402 | 2.333672 | MAPPED | Planned | Planned | 0.65 | 0.65 | True | True | True | Supply:LiqUtilAdjustment:R264C82 |
| Canada | Tilbury LNG | Tilbury LNG Phase 2 | 2031 | 1 | 157 | 157 | 3.307692 | 0.97402 | 2.333672 | MAPPED | Planned | Planned | 0.65 | 0.65 | True | True | True | Supply:LiqUtilAdjustment:R264C94 |
| Canada | Tilbury LNG | Tilbury LNG Phase 2 | 2030 | 2 | 146 | 146 | 3.307692 | 0.97685 | 2.330842 | MAPPED | Planned | Planned | 0.65 | 0.65 | True | True | True | Supply:LiqUtilAdjustment:R264C83 |
| Canada | Tilbury LNG | Tilbury LNG Phase 2 | 2031 | 2 | 158 | 158 | 3.307692 | 0.97685 | 2.330842 | MAPPED | Planned | Planned | 0.65 | 0.65 | True | True | True | Supply:LiqUtilAdjustment:R264C95 |
| Canada | Tilbury LNG | Tilbury LNG Phase 2 | 2030 | 3 | 147 | 147 | 3.307692 | 0.980231 | 2.327462 | MAPPED | Planned | Planned | 0.65 | 0.65 | True | True | True | Supply:LiqUtilAdjustment:R264C84 |
| Canada | Tilbury LNG | Tilbury LNG Phase 2 | 2031 | 3 | 159 | 159 | 3.307692 | 0.980231 | 2.327462 | MAPPED | Planned | Planned | 0.65 | 0.65 | True | True | True | Supply:LiqUtilAdjustment:R264C96 |
| Canada | Tilbury LNG | Tilbury LNG Phase 2 | 2030 | 4 | 148 | 148 | 3.307692 | 0.981112 | 2.32658 | MAPPED | Planned | Planned | 0.65 | 0.65 | True | True | True | Supply:LiqUtilAdjustment:R264C85 |
| Canada | Tilbury LNG | Tilbury LNG Phase 2 | 2031 | 4 | 160 | 160 | 3.307692 | 0.981112 | 2.32658 | MAPPED | Planned | Planned | 0.65 | 0.65 | True | True | True | Supply:LiqUtilAdjustment:R264C97 |
| Canada | Tilbury LNG | Tilbury LNG Phase 2 | 2030 | 5 | 149 | 149 | 3.307692 | 0.984493 | 2.323199 | MAPPED | Planned | Planned | 0.65 | 0.65 | True | True | True | Supply:LiqUtilAdjustment:R264C86 |
| Canada | Tilbury LNG | Tilbury LNG Phase 2 | 2031 | 5 | 161 | 161 | 3.307692 | 0.984493 | 2.323199 | MAPPED | Planned | Planned | 0.65 | 0.65 | True | True | True | Supply:LiqUtilAdjustment:R264C98 |
| Canada | Tilbury LNG | Tilbury LNG Phase 2 | 2030 | 6 | 150 | 150 | 3.307692 | 0.98769 | 2.320002 | MAPPED | Planned | Planned | 0.65 | 0.65 | True | True | True | Supply:LiqUtilAdjustment:R264C87 |
| Canada | Tilbury LNG | Tilbury LNG Phase 2 | 2031 | 6 | 162 | 162 | 3.307692 | 0.98769 | 2.320002 | MAPPED | Planned | Planned | 0.65 | 0.65 | True | True | True | Supply:LiqUtilAdjustment:R264C99 |
| Canada | Tilbury LNG | Tilbury LNG Phase 2 | 2030 | 7 | 151 | 151 | 3.307692 | 0.993387 | 2.314306 | MAPPED | Planned | Planned | 0.65 | 0.65 | True | True | True | Supply:LiqUtilAdjustment:R264C88 |

## 5. 결론

- basecase 기준 동일 slot lookup은 GDP/PMI/PowerMix/Temperature에서 100% 성공했다.

- LiqUtilAdjustment도 99.60%가 매핑되어 business key 방식은 실사용 가능성이 높다. 다만 `Mexico Pacific Limited LNG T3 (Phase 2)`, `Pan American LNG`, `Coral North FLNG`처럼 basecase-only slot 87개는 별도 warning 또는 basecase-only override로 유지해야 한다.

- 매핑된 row 대부분은 basecase와 LUT value가 다르므로, 설계대로 `basecase override > LUT default` 우선순위를 적용해야 한다.

- LiqUtilAdjustment는 value lookup에는 Year/Month business key를 쓰고 Period는 sanity check로 두는 설계가 현재 데이터에서 정합하다.
