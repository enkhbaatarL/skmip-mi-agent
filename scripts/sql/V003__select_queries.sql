-- =========================================================
-- 이벤트 유형 정보 조회
-- =========================================================
SELECT
    l1.event_type_l1_id,
    l1.level_1_code,
    l1.level_1_label,
    l2.event_type_l2_id,
    l2.level_2_code,
    l2.level_2_label
FROM `tmm_mi_event_type_l1_m` l1
JOIN `tmm_mi_event_type_l2_m` l2
  ON l1.event_type_l1_id = l2.event_type_l1_id
WHERE l1.del_yn = 'N'
  AND l2.del_yn = 'N'
ORDER BY
    l1.event_type_l1_id,
    l2.event_type_l2_id;   

-- =========================================================
-- 이벤트 리스트
-- =========================================================
SELECT
    DATE_FORMAT(evt.mod_dtm, '%m-%y %H:%i') AS mod_dtm_format,
    CASE
        WHEN evt.new_yn = 'Y' THEN '신규'
        ELSE '갱신'
    END AS event_change_type,
    evt_tp_l2.level_2_label,
    evt.event_title,
    CASE 
    	WHEN evt.scenario_suggest_yn = 'Y' THEN '시나리오화 추천'
    END
FROM tmm_mi_mievent_m evt
JOIN tmm_mi_event_type_l2_m evt_tp_l2
    ON evt.event_type_l2_id = evt_tp_l2.event_type_l2_id
JOIN tmm_mi_mievent_record_map evt_map
    ON evt.mi_event_id = evt_map.mi_event_id
   AND evt_map.del_yn = 'N'
WHERE evt.del_yn = 'N'
GROUP BY
    evt.mi_event_id,
    evt_tp_l2.level_2_label,
    evt.event_title,
    evt.mod_dtm
ORDER BY evt.mod_dtm DESC;

-- =========================================================
-- 이벤트 상세
-- =========================================================
SELECT
    evt.mi_event_id AS '이벤트 ID',
    evt_type_l1.level_1_label AS '이벤트 유형 레벨1',
    evt_type_l2.level_2_label AS '이벤트 유형 레벨2',
    evt.event_title AS '이벤트 제목',
    evt.key_bullets_json AS '이벤트 핵심요약',
    evt.detail_analysis AS '이벤트 상세분석',
    inst_view.view_date AS '기관전망 (일시)',
    inst_view.institution_name AS '기관전망 (기관명)',
    inst_view.view_summary AS '기관전망 (전망 요약)',
    GROUP_CONCAT(
        DISTINCT evt_record_map.mi_record_id
        ORDER BY evt_record_map.mi_record_id
        SEPARATOR ', '
    ) AS mi_record_ids,
    evt.crt_dtm,
    evt.mod_dtm
FROM tmm_mi_mievent_m evt
JOIN tmm_mi_event_type_l2_m evt_type_l2
    ON evt.event_type_l2_id = evt_type_l2.event_type_l2_id
   AND evt_type_l2.del_yn = 'N'
JOIN tmm_mi_event_type_l1_m evt_type_l1
    ON evt_type_l2.event_type_l1_id = evt_type_l1.event_type_l1_id
   AND evt_type_l1.del_yn = 'N'
LEFT JOIN tmm_mi_mievent_record_map evt_record_map
    ON evt.mi_event_id = evt_record_map.mi_event_id
   AND evt_record_map.del_yn = 'N'
LEFT JOIN tmm_mi_institution_view inst_view
    ON inst_view.mi_event_id = evt.mi_event_id
   AND inst_view.mi_record_id = evt_record_map.mi_record_id
   AND inst_view.del_yn = 'N'
WHERE evt.del_yn = 'N'
GROUP BY
    evt.mi_event_id,
    evt_type_l1.level_1_label,
    evt_type_l2.level_2_label,
    evt.event_title,
    evt.key_bullets_json,
    evt.detail_analysis,
    inst_view.view_date,
    inst_view.institution_name,
    inst_view.view_summary,
    evt.crt_dtm,
    evt.mod_dtm
ORDER BY evt.mod_dtm DESC;



-- =========================================================
-- 이벤트별 단기/중기/장기 분석 결과 전체 (9셀)
--      : 이벤트 1건의 JKM·TTF·HH × 단기·중기·장기를 행으로 조회
-- =========================================================
SELECT
    i.mi_event_id
  , i.impact_id
  , r.target_id
  , r.impact_short   AS 단기
  , r.impact_mid     AS 중기
  , r.impact_long    AS 장기
  , r.confidence     AS 신뢰도
  , r.completed
  , r.analysis_time
FROM tmm_mi_impact_m         i
JOIN tmm_mi_impact_result_m  r  ON r.impact_id = i.impact_id
WHERE i.del_yn  = 'N'
  AND r.del_yn  = 'N'
  AND r.completed = 'Y'
ORDER BY i.mi_event_id
       , FIELD(r.target_id, 'JKM', 'TTF', 'HH');

-- =========================================================
-- 시나리오화 추천 이벤트 + 9셀 결과 함께 조회 (REQ-15)
--     : scenario_recommended = 1
-- =========================================================
SELECT
    i.mi_event_id
  , bc.uncertainty_level
  , bc.conflict_detected
  , bc.scenario_recommend_reason
  , r.target_id
  , r.impact_short   AS 단기
  , r.impact_mid     AS 중기
  , r.impact_long    AS 장기
  , r.confidence
FROM tmm_mi_impact_base_case_m     bc
JOIN tmm_mi_impact_m               i   ON i.impact_id  = bc.impact_id
JOIN tmm_mi_impact_result_m        r   ON r.impact_id  = i.impact_id
WHERE bc.scenario_recommended = 1
  AND bc.del_yn = 'N'
  AND i.del_yn  = 'N'
  AND r.del_yn  = 'N'
ORDER BY bc.uncertainty_level DESC
       , i.mi_event_id
       , FIELD(r.target_id, 'JKM', 'TTF', 'HH');

-- =========================================================
-- Driver 기여 목록 조회 (REQ-6 Traceability)
--     : 특정 이벤트의 가격별 driver 평가 내역
-- =========================================================
SELECT
    i.mi_event_id
  , r.target_id
  , d.lv1_id
  , d.lv1_label
  , d.lv2_id
  , d.lv2_label
  , d.lv3_id
  , d.lv3_label
  , d.direction_hint
  , d.match_score
  , d.impact_short   AS driver_단기
  , d.impact_mid     AS driver_중기
  , d.impact_long    AS driver_장기
  , d.driver_reason
FROM tmm_mi_impact_m          i
JOIN tmm_mi_impact_result_m   r  ON r.impact_id       = i.impact_id
JOIN tmm_mi_impact_driver_m   d  ON d.impact_result_id = r.impact_result_id
WHERE i.del_yn = 'N'
  AND r.del_yn = 'N'
  AND d.del_yn = 'N'
  AND i.mi_event_id = IFNULL(@mi_event_id, i.mi_event_id)
ORDER BY FIELD(r.target_id, 'JKM', 'TTF', 'HH')
       , d.match_score DESC;

-- =========================================================
-- lv3 driver별 영향 집계
--     : 특정 driver가 어떤 이벤트에서 얼마나 자주 상승/하락에 기여했는지
-- =========================================================
SELECT
    d.lv3_id
  , d.lv3_label
  , d.direction_hint
  , COUNT(*)                                        AS 사용횟수
  , SUM(CASE WHEN d.impact_short LIKE '상승%' THEN 1 ELSE 0 END) AS 단기_상승
  , SUM(CASE WHEN d.impact_short LIKE '하락%' THEN 1 ELSE 0 END) AS 단기_하락
  , SUM(CASE WHEN d.impact_short = '영향없음'  THEN 1 ELSE 0 END) AS 단기_영향없음
  , ROUND(AVG(d.match_score), 2)                   AS 평균_match_score
FROM tmm_mi_impact_driver_m  d
JOIN tmm_mi_impact_result_m  r  ON r.impact_result_id = d.impact_result_id
WHERE d.del_yn = 'N'
  AND r.del_yn = 'N'
  AND r.target_id = 'JKM'   -- 원하는 가격 지표 지정
GROUP BY d.lv3_id, d.lv3_label, d.direction_hint
ORDER BY 사용횟수 DESC, 평균_match_score DESC;


-- #########################################################
-- # 시나리오 / Signpost (화면별 조회 쿼리)
-- #########################################################

-- =========================================================
-- 1) mi_event_id 기준 시나리오 그룹 + 시나리오 목록 조회
-- =========================================================
SELECT
    sg.scenario_group_id,
    sg.event_type_l2_id,
    sg.title         AS group_title,
    sg.summary,
    sg.dimension_selected,
    s.*
FROM tmm_mi_scenario_group_m sg
JOIN tmm_mi_scenario_m s
    ON s.scenario_group_id = sg.scenario_group_id
WHERE sg.mi_event_id = IFNULL(@mi_event_id, sg.mi_event_id)
  AND sg.del_yn = 'N'
  AND s.del_yn = 'N'
ORDER BY s.display_order, s.scenario_id;

-- =========================================================
-- 2) 시나리오 그룹 생성 화면: dimension template 조회
--     : template_json 기준으로 사용자가 선택한 dim_key 목록을
--       tmm_mi_scenario_group_m.dimension_selected 에 저장
-- =========================================================
SELECT
    dt.template_json
FROM tmm_mi_scenario_dimension_template_m dt
WHERE dt.event_type_l2_id = IFNULL(@event_type_l2_id, dt.event_type_l2_id)
  AND dt.del_yn = 'N';

-- =========================================================
-- 3) 시나리오 그룹 리스트 + 시나리오 수
-- =========================================================
SELECT
    sg.scenario_group_id,
    sg.mi_event_id,
    sg.event_type_l2_id,
    sg.title,
    sg.summary,
    sg.dimension_selected,
    sg.scenario_count,
    sg.crt_dtm
FROM tmm_mi_scenario_group_m sg
WHERE sg.del_yn = 'N'
ORDER BY sg.crt_dtm DESC;

-- =========================================================
-- 4) 시나리오 그룹 상세: 그룹 + base event + event type
-- =========================================================
SELECT
    sg.*,
    e.*,
    et2.level_2_code,
    et2.level_2_label
FROM tmm_mi_scenario_group_m sg
JOIN tmm_mi_mievent_m e
    ON e.mi_event_id = sg.mi_event_id
JOIN tmm_mi_event_type_l2_m et2
    ON et2.event_type_l2_id = sg.event_type_l2_id
WHERE sg.scenario_group_id = IFNULL(@scenario_group_id, sg.scenario_group_id)
  AND sg.del_yn = 'N';

-- =========================================================
-- 5) 시나리오 그룹 상세 하단: 가정 및 실현가능성 (scenario list)
-- =========================================================
SELECT *
FROM tmm_mi_scenario_m
WHERE scenario_group_id = IFNULL(@scenario_group_id, scenario_group_id)
  AND del_yn = 'N'
ORDER BY display_order, scenario_id;

-- =========================================================
-- 6) 시나리오 상세: scenario + signpost + signpost_event
-- =========================================================
SELECT
    s.scenario_id,
    s.title                         AS scenario_title,
    s.narrative,
    s.dimension_values,
    s.probability_score,
    s.probability_level,
    s.probability_delta,
    sp.signpost_id,
    sp.label                        AS signpost_label,
    sp.probability_direction_code,
    sp.probability_impact_score,
    sp.signpost_reason,
    spe.signpost_event_id,
    spe.mod_dtm                     AS signpost_event_updated_at,
    spe.summary                     AS signpost_event_summary,
    spe.probability_score,
    spe.probability_delta           AS signpost_event_probability_delta,
    spe.matching_reason
FROM tmm_mi_scenario_m s
LEFT JOIN tmm_mi_signpost_m sp
    ON sp.scenario_id = s.scenario_id
    AND sp.del_yn = 'N'
LEFT JOIN tmm_mi_signpost_event_m spe
    ON spe.signpost_id = sp.signpost_id
    AND spe.del_yn = 'N'
WHERE s.scenario_id = IFNULL(@scenario_id, s.scenario_id)
  AND s.del_yn = 'N'
ORDER BY sp.display_order, spe.mod_dtm DESC;