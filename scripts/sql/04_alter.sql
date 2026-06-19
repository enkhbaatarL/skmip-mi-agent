-- =========================================================
-- Table: tmm_mi_mievent_m
-- =========================================================
ALTER TABLE `tmm_mi_mievent_m`
    ADD COLUMN `latest_record_first_created` DATETIME(6) NULL COMMENT 'Event 관련 Record 중 최신 first_created 시각' AFTER `occurred_at`,
    ADD KEY `idx_tmm_mi_mievent_m_03` (`latest_record_first_created`);

ALTER TABLE tmm_mi_mievent_m
    ADD COLUMN signature_text VARCHAR(200) NULL COMMENT 'LLM 이벤트 매칭용 정규화 시그니처. 지역/주체/주제만 포함, 방향성·상태 제외';