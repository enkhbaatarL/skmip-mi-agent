-- =========================================================
-- Table: tmm_mi_mievent_m
-- =========================================================
ALTER TABLE `tmm_mi_mievent_m`
    ADD COLUMN `latest_record_first_created` DATETIME(6) NULL COMMENT 'Event 관련 Record 중 최신 first_created 시각' AFTER `occurred_at`,
    ADD KEY `idx_tmm_mi_mievent_m_03` (`latest_record_first_created`);
