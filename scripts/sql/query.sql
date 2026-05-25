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
    evt.event_title
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
    evt.detail_analysis  AS '이벤트 상세분석',
    evt.market_and_institution_view AS '기관전망 (확인 후, 다시 공지 예정)',
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
WHERE evt.del_yn = 'N'
GROUP BY
    evt.mi_event_id,
    evt_type_l1.level_1_label,
    evt_type_l2.level_2_label,
    evt.event_title,
    evt.key_bullets_json,
    evt.detail_analysis ,
    evt.market_and_institution_view,
    evt.crt_dtm,
    evt.mod_dtm
ORDER BY evt.mod_dtm DESC;