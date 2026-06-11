-- =========================================================
-- MI Agent ERD MySQL DDL
-- =========================================================

-- =========================================================
-- Drop existing tables (FK-safe order: child tables first)
-- =========================================================

DROP TABLE IF EXISTS `tmm_mi_institution_view`;
DROP TABLE IF EXISTS `tmm_mi_mievent_candidate_record_map`;
DROP TABLE IF EXISTS `tmm_mi_mievent_record_map`;
DROP TABLE IF EXISTS `tmm_mi_mievent_candidate_m`;
DROP TABLE IF EXISTS `tmm_mi_mievent_m`;
DROP TABLE IF EXISTS `tmm_mi_record_metacuration_item`;
DROP TABLE IF EXISTS `tmm_mi_record_metacuration_m`;
DROP TABLE IF EXISTS `tmm_mi_event_type_l2_m`;
DROP TABLE IF EXISTS `tmm_mi_event_type_l1_m`;

DROP TABLE IF EXISTS `tmm_drivertagm`;
DROP TABLE IF EXISTS `tmm_priceforecastm`;
DROP TABLE IF EXISTS `tmm_drivertreenodem`;
DROP TABLE IF EXISTS `tmm_impactresultm`;
DROP TABLE IF EXISTS `tmm_impactm`;
DROP TABLE IF EXISTS `tmm_mi_impact_driver_m`;
DROP TABLE IF EXISTS `tmm_mi_impact_result_m`;
DROP TABLE IF EXISTS `tmm_mi_impact_base_case_m`;
DROP TABLE IF EXISTS `tmm_mi_impact_m`;
DROP TABLE IF EXISTS `tmd_drivertreem`;

DROP TABLE IF EXISTS `tmm_mi_signpost_snap_m`;
DROP TABLE IF EXISTS `tmm_mi_scenario_snap_m`;
DROP TABLE IF EXISTS `tmm_mi_snapshot_m`;
DROP TABLE IF EXISTS `tmm_mi_signpost_event_m`;
DROP TABLE IF EXISTS `tmm_mi_signpost_m`;
DROP TABLE IF EXISTS `tmm_mi_scenario_m`;
DROP TABLE IF EXISTS `tmm_mi_scenario_dimension_template_m`;
DROP TABLE IF EXISTS `tmm_mi_scenario_group_m`;

-- =========================================================
-- GROUP 1: Core MI Event Tables (COLLATE utf8mb4_bin)
-- =========================================================

-- =========================================================
-- Table: tmm_mi_event_type_l1_m
-- =========================================================

-- =========================================================
-- Table: tmm_mi_event_type_l1_m
-- =========================================================

CREATE TABLE `tmm_mi_event_type_l1_m` (
    `event_type_l1_id` INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '이벤트 유형 L1 PK',
    `level_1_code` VARCHAR(100) COLLATE utf8mb4_bin NOT NULL COMMENT '이벤트 유형 L1 코드',
    `level_1_label` VARCHAR(200) COLLATE utf8mb4_bin NOT NULL COMMENT '이벤트 유형 L1 한글명',

    `crt_usr_logn_id` VARCHAR(100) COLLATE utf8mb4_bin NOT NULL DEFAULT 'system' COMMENT '생성자',
    `crt_dtm` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) COMMENT '생성일시',
    `mod_usr_logn_id` VARCHAR(100) COLLATE utf8mb4_bin NOT NULL DEFAULT 'system' COMMENT '수정자',
    `mod_dtm` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6) COMMENT '수정일시',
    `del_yn` CHAR(1) COLLATE utf8mb4_bin NOT NULL DEFAULT 'N' COMMENT '삭제여부',

    PRIMARY KEY (`event_type_l1_id`),
    UNIQUE KEY `uk_tmm_mi_event_type_l1_m_01` (`level_1_code`)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_bin
  COMMENT='MI 이벤트 유형 L1 마스터';


-- =========================================================
-- Table: tmm_mi_event_type_l2_m
-- =========================================================
 
CREATE TABLE `tmm_mi_event_type_l2_m` (
    `event_type_l2_id` INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '이벤트 유형 L2 PK',
    `event_type_l1_id` INT UNSIGNED NOT NULL COMMENT '이벤트 유형 L1 FK',
    `level_2_code` VARCHAR(150) COLLATE utf8mb4_bin NOT NULL COMMENT '이벤트 유형 L2 코드',
    `level_2_label` VARCHAR(200) COLLATE utf8mb4_bin NOT NULL COMMENT '이벤트 유형 L2 한글명',

    `crt_usr_logn_id` VARCHAR(100) COLLATE utf8mb4_bin NOT NULL DEFAULT 'system' COMMENT '생성자',
    `crt_dtm` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) COMMENT '생성일시',
    `mod_usr_logn_id` VARCHAR(100) COLLATE utf8mb4_bin NOT NULL DEFAULT 'system' COMMENT '수정자',
    `mod_dtm` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6) COMMENT '수정일시',
    `del_yn` CHAR(1) COLLATE utf8mb4_bin NOT NULL DEFAULT 'N' COMMENT '삭제여부',

    PRIMARY KEY (`event_type_l2_id`),
    UNIQUE KEY `uk_tmm_mi_event_type_l2_m_01` (`event_type_l1_id`, `level_2_code`),
    KEY `idx_tmm_mi_event_type_l2_m_01` (`event_type_l1_id`),

    CONSTRAINT `fk_tmm_mi_event_type_l2_m_01`
        FOREIGN KEY (`event_type_l1_id`)
        REFERENCES `tmm_mi_event_type_l1_m` (`event_type_l1_id`)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_bin
  COMMENT='MI 이벤트 유형 L2 마스터';


-- =========================================================
-- Table: tmm_mi_record_metacuration_m
-- =========================================================
 
CREATE TABLE `tmm_mi_record_metacuration_m` (
    `mi_record_metacuration_id` INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT 'Record metadata curation PK',
    `mi_record_id` INT UNSIGNED NOT NULL COMMENT '원본 MI Record ID',

    `crt_usr_logn_id` VARCHAR(100) COLLATE utf8mb4_bin NOT NULL DEFAULT 'system' COMMENT '생성자',
    `crt_dtm` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) COMMENT '생성일시',
    `mod_usr_logn_id` VARCHAR(100) COLLATE utf8mb4_bin NOT NULL DEFAULT 'system' COMMENT '수정자',
    `mod_dtm` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6) COMMENT '수정일시',
    `del_yn` CHAR(1) COLLATE utf8mb4_bin NOT NULL DEFAULT 'N' COMMENT '삭제여부',

    PRIMARY KEY (`mi_record_metacuration_id`),

    UNIQUE KEY `uk_tmm_mi_record_metacuration_m_01` (`mi_record_id`),

    CONSTRAINT `fk_tmm_mi_record_metacuration_m_01`
        FOREIGN KEY (`mi_record_id`)
        REFERENCES `tmd_mi_record` (`mi_record_id`)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_bin
  COMMENT='MI Record Metadata Curation 마스터';


-- =========================================================
-- Table: tmm_mi_record_metacuration_item
-- =========================================================
 
CREATE TABLE `tmm_mi_record_metacuration_item` (
    `mi_record_metacuration_item_id` INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT 'Record metadata curation item PK',
    `mi_record_metacuration_id` INT UNSIGNED NOT NULL COMMENT 'Record metadata curation FK',
    `event_type_l2_id` INT UNSIGNED NOT NULL COMMENT '이벤트 유형 L2 FK',

    `signature_text` VARCHAR(500) COLLATE utf8mb4_bin NOT NULL COMMENT '정규화된 사건 식별 텍스트',
    `score` DECIMAL(4, 1) NOT NULL COMMENT 'Record와 이벤트 유형 후보의 연관 점수',
    `reason` TEXT COLLATE utf8mb4_bin NULL COMMENT '점수 근거',
    `lng_relevance` VARCHAR(30) COLLATE utf8mb4_bin NOT NULL DEFAULT 'unclear' COMMENT 'LNG 관련성 (direct_lng/gas_market_direct/energy_indirect/non_lng_noise)',
    `lng_relevance_reason` TEXT COLLATE utf8mb4_bin NULL COMMENT 'LNG 관련성 판단 근거',

    `crt_usr_logn_id` VARCHAR(100) COLLATE utf8mb4_bin NOT NULL DEFAULT 'system' COMMENT '생성자',
    `crt_dtm` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) COMMENT '생성일시',
    `mod_usr_logn_id` VARCHAR(100) COLLATE utf8mb4_bin NOT NULL DEFAULT 'system' COMMENT '수정자',
    `mod_dtm` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6) COMMENT '수정일시',
    `del_yn` CHAR(1) COLLATE utf8mb4_bin NOT NULL DEFAULT 'N' COMMENT '삭제여부',

    PRIMARY KEY (`mi_record_metacuration_item_id`),

    UNIQUE KEY `uk_tmm_mi_record_metacuration_item_01` (`mi_record_metacuration_id`, `event_type_l2_id`),
    KEY `idx_tmm_mi_record_metacuration_item_01` (`mi_record_metacuration_id`),
    KEY `idx_tmm_mi_record_metacuration_item_02` (`event_type_l2_id`),
    KEY `idx_tmm_mi_record_metacuration_item_03` (`score`),
    KEY `idx_tmm_mi_record_metacuration_item_04` (`lng_relevance`),

    CONSTRAINT `fk_tmm_mi_record_metacuration_item_01`
        FOREIGN KEY (`mi_record_metacuration_id`)
        REFERENCES `tmm_mi_record_metacuration_m` (`mi_record_metacuration_id`),

    CONSTRAINT `fk_tmm_mi_record_metacuration_item_02`
        FOREIGN KEY (`event_type_l2_id`)
        REFERENCES `tmm_mi_event_type_l2_m` (`event_type_l2_id`)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_bin
  COMMENT='MI Record Metadata Curation Item';

-- =========================================================
-- Table: tmm_mi_mievent_m
-- =========================================================
 
CREATE TABLE `tmm_mi_mievent_m` (
    `mi_event_id` INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT 'MI Event PK',
    `event_type_l2_id` INT UNSIGNED NOT NULL COMMENT '이벤트 유형 L2 FK',

    `event_title` VARCHAR(500) COLLATE utf8mb4_bin NOT NULL COMMENT '이벤트 제목',
    `one_line_summary` VARCHAR(300) COLLATE utf8mb4_bin NOT NULL COMMENT '한줄 요약',
    `key_bullets_json` JSON NOT NULL COMMENT '핵심 bullet 목록 JSON',
    `detail_analysis` LONGTEXT COLLATE utf8mb4_bin NOT NULL COMMENT '이벤트 상세 분석 본문',
    `tags_json` JSON NULL COMMENT '이벤트 태그 목록 JSON',
    `occurred_at` DATETIME(6) NULL COMMENT '이벤트 실제 발생 일시',

    `estimated_impact_id` VARCHAR(100) COLLATE utf8mb4_bin NULL COMMENT 'Impact ID',
    `signal_yn` CHAR(1) COLLATE utf8mb4_bin NOT NULL DEFAULT 'Y' COMMENT '신호 여부',
    `signal_confidence` DECIMAL(5, 4) NULL DEFAULT 0 COMMENT '신호 신뢰도',
    `signal_reason` VARCHAR(100) COLLATE utf8mb4_bin NULL COMMENT '신호 판정 근거',
    `scenario_suggest_yn` CHAR(1) COLLATE utf8mb4_bin NOT NULL DEFAULT 'N' COMMENT '시나리오화 추천 여부',
    `scenario_suggest_reason` VARCHAR(100) COLLATE utf8mb4_bin NULL COMMENT '시나리오화 추천 근거',
    `new_yn` CHAR(1) COLLATE utf8mb4_bin NOT NULL DEFAULT 'Y' COMMENT '신규생성 여부 (Y: 신규생성, N: 갱신)',

    `crt_usr_logn_id` VARCHAR(100) COLLATE utf8mb4_bin NOT NULL DEFAULT 'system' COMMENT '생성자',
    `crt_dtm` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) COMMENT '생성일시',
    `mod_usr_logn_id` VARCHAR(100) COLLATE utf8mb4_bin NOT NULL DEFAULT 'system' COMMENT '수정자',
    `mod_dtm` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6) COMMENT '수정일시',
    `del_yn` CHAR(1) COLLATE utf8mb4_bin NOT NULL DEFAULT 'N' COMMENT '삭제여부',

    PRIMARY KEY (`mi_event_id`),

    KEY `idx_tmm_mi_mievent_m_01` (`event_type_l2_id`),
    KEY `idx_tmm_mi_mievent_m_02` (`occurred_at`),

    CONSTRAINT `fk_tmm_mi_mievent_m_01`
        FOREIGN KEY (`event_type_l2_id`)
        REFERENCES `tmm_mi_event_type_l2_m` (`event_type_l2_id`)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_bin
  COMMENT='MI Event 마스터';


-- =========================================================
-- Table: tmm_mi_mievent_record_map
-- =========================================================
 
CREATE TABLE `tmm_mi_mievent_record_map` (
    `mi_event_record_map_id` INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT 'Event-Record 매핑 PK',
    `mi_event_id` INT UNSIGNED NOT NULL COMMENT 'MI Event ID',
    `mi_record_id` INT UNSIGNED NOT NULL COMMENT 'MI Record ID',

    `crt_usr_logn_id` VARCHAR(100) COLLATE utf8mb4_bin NOT NULL DEFAULT 'system' COMMENT '생성자',
    `crt_dtm` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) COMMENT '생성일시',
    `mod_usr_logn_id` VARCHAR(100) COLLATE utf8mb4_bin NOT NULL DEFAULT 'system' COMMENT '수정자',
    `mod_dtm` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6) COMMENT '수정일시',
    `del_yn` CHAR(1) COLLATE utf8mb4_bin NOT NULL DEFAULT 'N' COMMENT '삭제여부',

    PRIMARY KEY (`mi_event_record_map_id`),

    UNIQUE KEY `uk_tmm_mi_mievent_record_map_01` (`mi_event_id`, `mi_record_id`),
    KEY `idx_tmm_mi_mievent_record_map_01` (`mi_record_id`),

    CONSTRAINT `fk_tmm_mi_mievent_record_map_01`
        FOREIGN KEY (`mi_event_id`)
        REFERENCES `tmm_mi_mievent_m` (`mi_event_id`),

    CONSTRAINT `fk_tmm_mi_mievent_record_map_02`
        FOREIGN KEY (`mi_record_id`)
        REFERENCES `tmd_mi_record` (`mi_record_id`)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_bin
  COMMENT='MI Event - MI Record 매핑';
 
 
-- =========================================================
-- Table: tmm_mi_mievent_candidate_m
-- =========================================================
 
CREATE TABLE `tmm_mi_mievent_candidate_m` (
    `mi_event_candidate_id` INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT 'MI Event 후보 PK',
    `event_type_l2_id` INT UNSIGNED NOT NULL COMMENT '이벤트 유형 L2 FK',

    `event_title` VARCHAR(500) COLLATE utf8mb4_bin NOT NULL COMMENT '이벤트 제목',
    `one_line_summary` VARCHAR(300) COLLATE utf8mb4_bin NOT NULL COMMENT '한줄 요약',
    `key_bullets_json` JSON NOT NULL COMMENT '핵심 bullet 목록 JSON',
    `detail_analysis` LONGTEXT COLLATE utf8mb4_bin NOT NULL COMMENT '이벤트 상세 분석 본문',
    `tags_json` JSON NULL COMMENT '이벤트 태그 목록 JSON',
    `occurred_at` DATETIME(6) NULL COMMENT '이벤트 실제 발생 일시',

    `decision` VARCHAR(30) COLLATE utf8mb4_bin NOT NULL DEFAULT 'CREATE_NEW' COMMENT '후보 처리 상태(MATCH_EXISTING, CREATE_NEW, AMBIGUOUS_REVIEW)',
    `mi_event_id` INT UNSIGNED NULL COMMENT '최종 반영된 MI Event ID',
    `match_confidence` DECIMAL(3, 2) NULL COMMENT '후보 처리/매칭 신뢰도 (0.00~1.00)',
    `match_reason` TEXT COLLATE utf8mb4_bin NULL COMMENT '후보 처리/매칭 판단 근거',
    `same_event_check_json` JSON NULL COMMENT '기존 Event와 동일 사건 여부 판단 체크리스트 JSON',
    `lng_relevance` VARCHAR(30) COLLATE utf8mb4_bin NOT NULL DEFAULT 'unclear' COMMENT 'LNG 관련성 (direct_lng/gas_market_direct/energy_indirect/non_lng_noise)',
    `lng_relevance_reason` TEXT COLLATE utf8mb4_bin NULL COMMENT 'LNG 관련성 판단 근거',

    `crt_usr_logn_id` VARCHAR(100) COLLATE utf8mb4_bin NOT NULL DEFAULT 'system' COMMENT '생성자',
    `crt_dtm` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) COMMENT '생성일시',
    `mod_usr_logn_id` VARCHAR(100) COLLATE utf8mb4_bin NOT NULL DEFAULT 'system' COMMENT '수정자',
    `mod_dtm` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6) COMMENT '수정일시',
    `del_yn` CHAR(1) COLLATE utf8mb4_bin NOT NULL DEFAULT 'N' COMMENT '삭제여부',

    PRIMARY KEY (`mi_event_candidate_id`),

    KEY `idx_tmm_mi_mievent_candidate_m_01` (`event_type_l2_id`),
    KEY `idx_tmm_mi_mievent_candidate_m_02` (`decision`),
    KEY `idx_tmm_mi_mievent_candidate_m_03` (`mi_event_id`),
    KEY `idx_tmm_mi_mievent_candidate_m_04` (`occurred_at`),

    CONSTRAINT `fk_tmm_mi_mievent_candidate_m_01`
        FOREIGN KEY (`event_type_l2_id`)
        REFERENCES `tmm_mi_event_type_l2_m` (`event_type_l2_id`),

    CONSTRAINT `fk_tmm_mi_mievent_candidate_m_02`
        FOREIGN KEY (`mi_event_id`)
        REFERENCES `tmm_mi_mievent_m` (`mi_event_id`)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_bin
  COMMENT='MI Event 후보';


-- =========================================================
-- Table: tmm_mi_mievent_candidate_record_map
-- =========================================================
 
CREATE TABLE `tmm_mi_mievent_candidate_record_map` (
    `mi_event_candidate_record_map_id` INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT 'Event 후보-Record 매핑 PK',
    `mi_event_candidate_id` INT UNSIGNED NOT NULL COMMENT 'MI Event 후보 ID',
    `mi_record_id` INT UNSIGNED NOT NULL COMMENT 'MI Record ID',

    `mapping_confidence` DECIMAL(3, 2) NULL COMMENT '후보 Event-Record 매핑 신뢰도 (0.00~1.00)',
    `mapping_reason` TEXT COLLATE utf8mb4_bin NULL COMMENT '후보 Event-Record 매핑 근거',
    `lng_relevance` VARCHAR(30) COLLATE utf8mb4_bin NOT NULL DEFAULT 'unclear' COMMENT 'LNG 관련성 (direct_lng/gas_market_direct/energy_indirect/non_lng_noise)',
    `lng_relevance_reason` TEXT COLLATE utf8mb4_bin NULL COMMENT 'LNG 관련성 판단 근거',

    `crt_usr_logn_id` VARCHAR(100) COLLATE utf8mb4_bin NOT NULL DEFAULT 'system' COMMENT '생성자',
    `crt_dtm` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) COMMENT '생성일시',
    `mod_usr_logn_id` VARCHAR(100) COLLATE utf8mb4_bin NOT NULL DEFAULT 'system' COMMENT '수정자',
    `mod_dtm` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6) COMMENT '수정일시',
    `del_yn` CHAR(1) COLLATE utf8mb4_bin NOT NULL DEFAULT 'N' COMMENT '삭제여부',

    PRIMARY KEY (`mi_event_candidate_record_map_id`),

    UNIQUE KEY `uk_tmm_mi_mievent_candidate_record_map_01` (`mi_event_candidate_id`, `mi_record_id`),
    KEY `idx_tmm_mi_mievent_candidate_record_map_01` (`mi_event_candidate_id`),
    KEY `idx_tmm_mi_mievent_candidate_record_map_02` (`mi_record_id`),
    KEY `idx_tmm_mi_mievent_candidate_record_map_03` (`lng_relevance`),

    CONSTRAINT `fk_tmm_mi_mievent_candidate_record_map_01`
        FOREIGN KEY (`mi_event_candidate_id`)
        REFERENCES `tmm_mi_mievent_candidate_m` (`mi_event_candidate_id`),

    CONSTRAINT `fk_tmm_mi_mievent_candidate_record_map_02`
        FOREIGN KEY (`mi_record_id`)
        REFERENCES `tmd_mi_record` (`mi_record_id`)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_bin
  COMMENT='MI Event 후보 - MI Record 매핑';


-- =========================================================
-- Table: tmm_mi_institution_view
-- =========================================================
 
CREATE TABLE `tmm_mi_institution_view` (
    `institution_view_id` INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '기관전망 PK',
    `mi_event_id` INT UNSIGNED NOT NULL COMMENT 'MI Event ID',
    `mi_record_id` INT UNSIGNED NOT NULL COMMENT '추출 원본 MI Record ID',

    `institution_name` VARCHAR(200) COLLATE utf8mb4_bin NOT NULL COMMENT '기관명',
    `view_date` DATE NOT NULL COMMENT '기관전망일자',
    `view_summary` LONGTEXT COLLATE utf8mb4_bin NOT NULL COMMENT '기관전망 요약',

    `crt_usr_logn_id` VARCHAR(100) COLLATE utf8mb4_bin NOT NULL DEFAULT 'system' COMMENT '생성자',
    `crt_dtm` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) COMMENT '생성일시',
    `mod_usr_logn_id` VARCHAR(100) COLLATE utf8mb4_bin NOT NULL DEFAULT 'system' COMMENT '수정자',
    `mod_dtm` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6) COMMENT '수정일시',
    `del_yn` CHAR(1) COLLATE utf8mb4_bin NOT NULL DEFAULT 'N' COMMENT '삭제여부',

    PRIMARY KEY (`institution_view_id`),

    UNIQUE KEY `uk_tmm_mi_institution_view_01` (
        `mi_event_id`,
        `mi_record_id`,
        `institution_name`,
        `view_date`
    ),
    KEY `idx_tmm_mi_institution_view_01` (`mi_event_id`, `del_yn`),
    KEY `idx_tmm_mi_institution_view_02` (`mi_record_id`),

    CONSTRAINT `fk_tmm_mi_institution_view_01`
        FOREIGN KEY (`mi_event_id`)
        REFERENCES `tmm_mi_mievent_m` (`mi_event_id`),

    CONSTRAINT `fk_tmm_mi_institution_view_02`
        FOREIGN KEY (`mi_record_id`)
        REFERENCES `tmd_mi_record` (`mi_record_id`)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_bin
  COMMENT='MI Event 기관전망 상세 (이벤트/원본레코드 연결)';
;


-- =========================================================
-- GROUP 2: Impact / Scenario / Driver Tables
-- =========================================================

-- =========================================================
-- Table: tmm_mi_impact_m
-- =========================================================
DROP TABLE IF EXISTS `tmm_mi_impact_m`;
CREATE TABLE `tmm_mi_impact_m` (
  `impact_id`          VARCHAR(40) COLLATE utf8mb4_bin NOT NULL COMMENT 'Impact ID PK impact_ev_[a-z0-9_]+',
  `mi_event_id`        INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT 'MI Event ID FK',
  `base_case_id`       VARCHAR(60) COLLATE utf8mb4_bin NULL COMMENT 'MI Event Base Case ID FK',
  `base_case_skip`     TINYINT(1) NOT NULL DEFAULT 0 COMMENT 'Base Case 미명시로 단기만 산출한 경우 1',
  `impact_summary`     TEXT COLLATE utf8mb4_bin COMMENT 'JKM/TTF/HH 영향도 분석 결과 종합 요약 텍스트',
  `crt_usr_logn_id`    VARCHAR(50) COLLATE utf8mb4_bin NOT NULL DEFAULT 'SYSTEM' COMMENT '생성자',
  `crt_dtm`            DATETIME NOT NULL DEFAULT NOW() COMMENT '생성 일시',
  `mod_usr_logn_id`    VARCHAR(50) COLLATE utf8mb4_bin NOT NULL DEFAULT 'SYSTEM' COMMENT '수정 사용자 ID',
  `mod_dtm`            DATETIME NULL DEFAULT NOW() COMMENT '수정 일시',
  `del_yn`             CHAR(1) COLLATE utf8mb4_bin NOT NULL DEFAULT 'N' COMMENT '삭제 여부 Y/N',
  PRIMARY KEY (`impact_id`),
  INDEX `tmm_mi_impact_m_ix01` (`mi_event_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin
  COMMENT='MI Event Impact Master';

-- ============================================================
-- Table: tmm_mi_impact_base_case_m
-- ============================================================
DROP TABLE IF EXISTS `tmm_mi_impact_base_case_m`;
CREATE TABLE `tmm_mi_impact_base_case_m` (
  `base_case_id`               VARCHAR(60) COLLATE utf8mb4_bin NOT NULL COMMENT 'Base Case 고유 ID PK',
  `impact_id`                  VARCHAR(40) COLLATE utf8mb4_bin NOT NULL COMMENT 'Impact ID FK',
  `base_case_available`        TINYINT(1) NOT NULL DEFAULT 0 COMMENT 'Base Case 명시 여부 (0=미명시, 1=명시)',
  `base_case_text`             TEXT COLLATE utf8mb4_bin COMMENT '추출된 Base Case 전망 텍스트',
  `source_record_ids`          JSON COMMENT '근거 Record ID 목록 (최대 5건)',
  `uncertainty_level`          ENUM('n/a','none','low','medium','high') COLLATE utf8mb4_bin NOT NULL DEFAULT 'n/a' COMMENT 'Base Case 충돌 수준',
  `conflict_detected`          TINYINT(1) NOT NULL DEFAULT 0 COMMENT '충돌 감지 여부',
  `conflict_detail`            JSON COMMENT '충돌 claim 목록 [{record_id, publish_date, claim}]',
  `reconciliation_note`        VARCHAR(500) COLLATE utf8mb4_bin COMMENT '충돌 해소 방식 설명',
  `scenario_recommended`       TINYINT(1) NOT NULL DEFAULT 0 COMMENT 'uncertainty medium/high → 1',
  `scenario_recommend_reason`  VARCHAR(500) COLLATE utf8mb4_bin COMMENT '충돌 정보 기반 자동 생성 사유 텍스트',
  `crt_usr_logn_id`            VARCHAR(50) COLLATE utf8mb4_bin NOT NULL DEFAULT 'SYSTEM' COMMENT '생성 사용자 ID',
  `crt_dtm`                    DATETIME NOT NULL DEFAULT NOW() COMMENT '생성 일시',
  `mod_usr_logn_id`            VARCHAR(50) COLLATE utf8mb4_bin NOT NULL DEFAULT 'SYSTEM' COMMENT '수정 사용자 ID',
  `mod_dtm`                    DATETIME NOT NULL DEFAULT NOW() COMMENT '수정 일시',
  `del_yn`                     CHAR(1) COLLATE utf8mb4_bin NOT NULL DEFAULT 'N' COMMENT '삭제 여부 Y/N',
  PRIMARY KEY (`base_case_id`),
  INDEX `tmm_mi_impact_base_case_m_ix01` (`uncertainty_level`),
  INDEX `tmm_mi_impact_base_case_m_ix02` (`base_case_available`),
  INDEX `tmm_mi_impact_base_case_m_ix03` (`scenario_recommended`) COMMENT '시나리오화 추천 대상 조회'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin
  COMMENT='MI Event Impact Base Case Master';

-- =========================================================
-- Table: tmm_mi_impact_result_m
-- =========================================================
DROP TABLE IF EXISTS `tmm_mi_impact_result_m`;
CREATE TABLE `tmm_mi_impact_result_m` (
  `impact_result_id`       VARCHAR(64) COLLATE utf8mb4_bin NOT NULL COMMENT 'Impact Result ID PK',
  `impact_id`              VARCHAR(64) COLLATE utf8mb4_bin NOT NULL COMMENT 'Impact ID FK impact_ev_*',
  `target_type`            VARCHAR(20) COLLATE utf8mb4_bin NOT NULL COMMENT '대상 유형 price|spread',
  `target_id`              VARCHAR(20) COLLATE utf8mb4_bin NOT NULL COMMENT 'JKM / TTF / HH',
  `impact_short`           ENUM('상승_상','상승_중','상승_하','영향없음','하락_하','하락_중','하락_상') COLLATE utf8mb4_bin NOT NULL DEFAULT '영향없음' COMMENT '단기 영향 (0~1M)',
  `impact_mid`             ENUM('상승_상','상승_중','상승_하','영향없음','하락_하','하락_중','하락_상') COLLATE utf8mb4_bin NULL DEFAULT NULL COMMENT '중기 영향 (6M). Base Case 없으면 NULL',
  `impact_long`            ENUM('상승_상','상승_중','상승_하','영향없음','하락_하','하락_중','하락_상') COLLATE utf8mb4_bin NULL DEFAULT NULL COMMENT '장기 영향 (1Y+). Base Case 없으면 NULL',
  `confidence`             DECIMAL(5,4) NULL COMMENT '신뢰도 0~1',
  `rationale_base_case`    TEXT COLLATE utf8mb4_bin COMMENT '사용한 Base Case 가정',
  `rationale_driver_map`   TEXT COLLATE utf8mb4_bin COMMENT 'Step 1 driver 영향 요약',
  `rationale_synthesis`    TEXT COLLATE utf8mb4_bin COMMENT '종합 판단 logic',
  `completed`              CHAR(1) COLLATE utf8mb4_bin NOT NULL DEFAULT 'N' COMMENT '분석 완료 여부 Y/N',
  `analysis_time`          DATETIME NULL COMMENT '분석 완료 일시 ISO-8601',
  `crt_usr_logn_id`        VARCHAR(50) COLLATE utf8mb4_bin NOT NULL DEFAULT 'SYSTEM' COMMENT '생성 사용자 ID',
  `crt_dtm`                DATETIME NOT NULL DEFAULT NOW() COMMENT '생성 일시',
  `mod_usr_logn_id`        VARCHAR(50) COLLATE utf8mb4_bin NOT NULL DEFAULT 'SYSTEM' COMMENT '수정 사용자 ID',
  `mod_dtm`                DATETIME NOT NULL DEFAULT NOW() COMMENT '수정 일시',
  `del_yn`                 CHAR(1) COLLATE utf8mb4_bin NOT NULL DEFAULT 'N' COMMENT '삭제 여부 Y/N',
  PRIMARY KEY (`impact_result_id`),
  INDEX `tmm_mi_impact_result_m_ix01` (`impact_id`),
  INDEX `tmm_mi_impact_result_m_ix02` (`target_id`),
  INDEX `tmm_mi_impact_result_m_ix03` (`target_id`, `impact_short`),
  INDEX `tmm_mi_impact_result_m_ix04` (`target_id`, `impact_mid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin
  COMMENT='Impact Result Master';

-- =========================================================
-- Table: tmm_mi_impact_driver_m
-- =========================================================
DROP TABLE IF EXISTS `tmm_mi_impact_driver_m`;
CREATE TABLE `tmm_mi_impact_driver_m` (
  `driver_id`         VARCHAR(200) COLLATE utf8mb4_bin NOT NULL COMMENT 'Driver Tag ID PK',
  `impact_result_id`  VARCHAR(200) COLLATE utf8mb4_bin NOT NULL COMMENT 'Impact Result ID FK',
  `lv1_id`            VARCHAR(50) COLLATE utf8mb4_bin NOT NULL COMMENT 'Driver Tree 1단계 코드',
  `lv1_label`         VARCHAR(100) COLLATE utf8mb4_bin NULL COMMENT 'Driver Tree 1단계 명칭',
  `lv2_id`            VARCHAR(50) COLLATE utf8mb4_bin NOT NULL COMMENT 'Driver Tree 2단계 코드',
  `lv2_label`         VARCHAR(100) COLLATE utf8mb4_bin NULL COMMENT 'Driver Tree 2단계 명칭',
  `lv3_id`            VARCHAR(50) COLLATE utf8mb4_bin NOT NULL COMMENT 'Driver Tree 3단계 코드',
  `lv3_label`         VARCHAR(100) COLLATE utf8mb4_bin NULL COMMENT 'Driver Tree 3단계 명칭',
  `direction_hint`    VARCHAR(50) COLLATE utf8mb4_bin NULL COMMENT '방향 힌트 bullish_if_up/bearish_if_up/contextual',
  `match_score`       DECIMAL(5,4) NULL COMMENT 'Event-Driver 매핑 신뢰도 점수 0~1',
  `matched_keywords`  JSON NULL COMMENT '매칭된 키워드 목록',
  `driver_reason`     TEXT COLLATE utf8mb4_bin NULL COMMENT 'Driver 영향 발생 사유',
  `impact_short`      ENUM('상승_상','상승_중','상승_하','영향없음','하락_하','하락_중','하락_상') COLLATE utf8mb4_bin NOT NULL DEFAULT '영향없음' COMMENT 'driver의 단기 영향',
  `impact_mid`        ENUM('상승_상','상승_중','상승_하','영향없음','하락_하','하락_중','하락_상') COLLATE utf8mb4_bin NULL DEFAULT NULL COMMENT 'driver의 중기 영향',
  `impact_long`       ENUM('상승_상','상승_중','상승_하','영향없음','하락_하','하락_중','하락_상') COLLATE utf8mb4_bin NULL DEFAULT NULL COMMENT 'driver의 장기 영향',
  `crt_usr_logn_id`   VARCHAR(50) COLLATE utf8mb4_bin NOT NULL DEFAULT 'SYSTEM' COMMENT '생성 사용자 ID',
  `crt_dtm`           DATETIME NOT NULL DEFAULT NOW() COMMENT '생성 일시',
  `mod_usr_logn_id`   VARCHAR(50) COLLATE utf8mb4_bin NOT NULL DEFAULT 'SYSTEM' COMMENT '수정 사용자 ID',
  `mod_dtm`           DATETIME NOT NULL DEFAULT NOW() COMMENT '수정 일시',
  `del_yn`            CHAR(1) COLLATE utf8mb4_bin NOT NULL DEFAULT 'N' COMMENT '삭제 여부 Y/N',
  PRIMARY KEY (`driver_id`),
  INDEX `tmm_mi_impact_driver_m_ix01` (`impact_result_id`),
  INDEX `tmm_mi_impact_driver_m_ix02` (`lv3_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin
  COMMENT='Driver Tag Master';

-- =========================================================
-- Table: tmm_drivertreenodem
-- =========================================================
DROP TABLE IF EXISTS `tmm_drivertreenodem`;
CREATE TABLE `tmm_drivertreenodem` (
  `node_id`               INT NOT NULL AUTO_INCREMENT COMMENT 'Driver Tree 노드 ID PK',
  `crt_user_id`           VARCHAR(50) COLLATE utf8mb4_bin NOT NULL DEFAULT 'SYSTEM' COMMENT '생성 사용자 ID',
  `crt_dtm`               DATETIME NOT NULL DEFAULT NOW() COMMENT '생성 일시',
  `mod_user_id`           VARCHAR(50) COLLATE utf8mb4_bin NOT NULL DEFAULT 'SYSTEM' COMMENT '수정 사용자 ID',
  `mod_dtm`               DATETIME NOT NULL DEFAULT NOW() COMMENT '수정 일시',
  `del_yn`                CHAR(1) COLLATE utf8mb4_bin NOT NULL DEFAULT 'N' COMMENT '삭제 여부 Y/N',
  `scenario_id`           INT NOT NULL COMMENT '시나리오 ID FK',
  `driver_name`           VARCHAR(100) COLLATE utf8mb4_bin NOT NULL COMMENT 'Driver 명칭',
  `driver_type`           VARCHAR(50) COLLATE utf8mb4_bin NULL COMMENT 'Driver 유형',
  `impact_level`          VARCHAR(20) COLLATE utf8mb4_bin NULL COMMENT '영향 레벨 low/medium/high/extreme',
  `weight`                DECIMAL(8,4) NULL COMMENT '가중치',
  `description`           TEXT COLLATE utf8mb4_bin NULL COMMENT 'Driver 설명',
  `sort_order`            INT NULL COMMENT '정렬 순서',
  PRIMARY KEY (`node_id`),
  INDEX `tmm_drivertreenodem_ix01` (`scenario_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin
COMMENT='Driver Tree Node Master';

-- =========================================================
-- Table: tmm_priceforecastm
-- =========================================================
DROP TABLE IF EXISTS `tmm_priceforecastm`;
CREATE TABLE `tmm_priceforecastm` (
  `forecast_id`           INT NOT NULL AUTO_INCREMENT COMMENT '가격 예측 ID PK',
  `crt_user_id`           VARCHAR(50) COLLATE utf8mb4_bin NOT NULL DEFAULT 'SYSTEM' COMMENT '생성 사용자 ID',
  `crt_dtm`               DATETIME NOT NULL DEFAULT NOW() COMMENT '생성 일시',
  `mod_user_id`           VARCHAR(50) COLLATE utf8mb4_bin NOT NULL DEFAULT 'SYSTEM' COMMENT '수정 사용자 ID',
  `mod_dtm`               DATETIME NOT NULL DEFAULT NOW() COMMENT '수정 일시',
  `del_yn`                CHAR(1) COLLATE utf8mb4_bin NOT NULL DEFAULT 'N' COMMENT '삭제 여부 Y/N',
  `scenario_id`           INT NOT NULL COMMENT '시나리오 ID FK',
  `benchmark`             VARCHAR(20) COLLATE utf8mb4_bin NOT NULL COMMENT '벤치마크 JKM/TTF/HH 등',
  `base_price`            DECIMAL(12,4) NULL COMMENT '기준 가격',
  `forecast_low`          DECIMAL(12,4) NULL COMMENT '예측 가격 하한',
  `forecast_high`         DECIMAL(12,4) NULL COMMENT '예측 가격 상한',
  `forecast_median`       DECIMAL(12,4) NULL COMMENT '예측 가격 중간값',
  `currency`              VARCHAR(10) COLLATE utf8mb4_bin NOT NULL DEFAULT 'USD' COMMENT '통화 단위',
  `unit`                  VARCHAR(10) COLLATE utf8mb4_bin NOT NULL DEFAULT 'MMBtu' COMMENT '에너지 단위',
  `forecast_date`         DATETIME NULL COMMENT '예측 일시',
  `valid_until`           DATETIME NULL COMMENT '유효 기간',
  `confidence_interval`   DECIMAL(5,4) NULL COMMENT '신뢰 구간 0~1',
  PRIMARY KEY (`forecast_id`),
  INDEX `tmm_priceforecastm_ix01` (`scenario_id`),
  INDEX `tmm_priceforecastm_ix02` (`benchmark`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin
COMMENT='Price Forecast Master';

-- =========================================================
-- Table: tmd_drivertreem
-- =========================================================
CREATE TABLE `tmd_drivertreem` (
  `lv1_id`                VARCHAR(50) COLLATE utf8mb4_bin NOT NULL COMMENT 'Driver Tree 1단계 코드 PK',
  `lv2_id`                VARCHAR(50) COLLATE utf8mb4_bin NOT NULL COMMENT 'Driver Tree 2단계 코드 PK',
  `lv3_id`                VARCHAR(50) COLLATE utf8mb4_bin NOT NULL COMMENT 'Driver Tree 3단계 코드 PK',
  `crt_user_id`           VARCHAR(50) COLLATE utf8mb4_bin NOT NULL DEFAULT 'SYSTEM' COMMENT '생성 사용자 ID',
  `crt_dtm`               DATETIME NOT NULL DEFAULT NOW() COMMENT '생성 일시',
  `mod_user_id`           VARCHAR(50) COLLATE utf8mb4_bin NOT NULL DEFAULT 'SYSTEM' COMMENT '수정 사용자 ID',
  `mod_dtm`               DATETIME NOT NULL DEFAULT NOW() COMMENT '수정 일시',
  `del_yn`                CHAR(1) COLLATE utf8mb4_bin NOT NULL DEFAULT 'N' COMMENT '삭제 여부 Y/N',
  `lv1_label_ko`          VARCHAR(100) COLLATE utf8mb4_bin NULL COMMENT 'Driver Tree 1단계 한국어 명칭',
  `lv2_label_ko`          VARCHAR(100) COLLATE utf8mb4_bin NULL COMMENT 'Driver Tree 2단계 한국어 명칭',
  `lv3_label_ko`          VARCHAR(100) COLLATE utf8mb4_bin NULL COMMENT 'Driver Tree 3단계 한국어 명칭',
  `lv1_label_en`          VARCHAR(100) COLLATE utf8mb4_bin NULL COMMENT 'Driver Tree 1단계 영어 명칭',
  `lv2_label_en`          VARCHAR(100) COLLATE utf8mb4_bin NULL COMMENT 'Driver Tree 2단계 영어 명칭',
  `lv3_label_en`          VARCHAR(100) COLLATE utf8mb4_bin NULL COMMENT 'Driver Tree 3단계 영어 명칭',
  `direction_hint`        VARCHAR(50) COLLATE utf8mb4_bin NULL COMMENT '방향 힌트 bullish_if_up/bearish_if_up/contextual',
  PRIMARY KEY (`lv1_id`, `lv2_id`, `lv3_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin
COMMENT='Driver Tree Master';


-- =========================================================
-- GROUP 3: Scenario Group / Snapshot Tables (COLLATE utf8mb4_bin)
-- =========================================================

-- =========================================================
-- Table: tmm_mi_scenario_group_m
-- =========================================================

CREATE TABLE `tmm_mi_scenario_group_m` (
    `scenario_group_id` INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '시나리오 그룹 ID',
    `mi_event_id` INT UNSIGNED NOT NULL COMMENT 'MI 이벤트 ID (1:1 기준 키)',
    `event_type_l2_id` INT UNSIGNED NOT NULL COMMENT '이벤트 유형 L2 ID (분류 기준)',
    `request_usr_id` INT UNSIGNED NULL COMMENT '요청 사용자 ID',
    `title` VARCHAR(255) COLLATE utf8mb4_bin NOT NULL COMMENT '시나리오 그룹명',
    `summary` TEXT COLLATE utf8mb4_bin NULL COMMENT '시나리오 그룹 요약',
    `description` TEXT COLLATE utf8mb4_bin NULL COMMENT '시나리오 그룹 설명',
    `dimension_selected` JSON NOT NULL COMMENT '표시 컬럼 선택 (dim_key 배열)',
    `scenario_count` INT NOT NULL DEFAULT 0 COMMENT '시나리오 수',

    `crt_usr_logn_id` VARCHAR(100) COLLATE utf8mb4_bin NOT NULL DEFAULT 'system' COMMENT '생성자',
    `crt_dtm` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) COMMENT '생성일시',
    `mod_usr_logn_id` VARCHAR(100) COLLATE utf8mb4_bin NOT NULL DEFAULT 'system' COMMENT '수정자',
    `mod_dtm` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6) COMMENT '수정일시',
    `del_yn` CHAR(1) COLLATE utf8mb4_bin NOT NULL DEFAULT 'N' COMMENT '삭제여부',

    PRIMARY KEY (`scenario_group_id`),
    UNIQUE KEY `uk_tmm_mi_scenario_group_m_01` (`mi_event_id`),
    KEY `idx_tmm_mi_scenario_group_m_01` (`event_type_l2_id`),

    CONSTRAINT `ck_tmm_mi_scenario_group_m_01`
        CHECK (JSON_TYPE(dimension_selected) = 'ARRAY'),
    CONSTRAINT `fk_tmm_mi_scenario_group_m_01`
        FOREIGN KEY (`mi_event_id`)
        REFERENCES `tmm_mi_mievent_m` (`mi_event_id`),
    CONSTRAINT `fk_tmm_mi_scenario_group_m_02`
        FOREIGN KEY (`event_type_l2_id`)
        REFERENCES `tmm_mi_event_type_l2_m` (`event_type_l2_id`)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_bin
  COMMENT='시나리오 그룹';


-- =========================================================
-- Table: tmm_mi_scenario_dimension_template_m
-- =========================================================

CREATE TABLE `tmm_mi_scenario_dimension_template_m` (
    `scenario_dimension_template_id` INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '시나리오 Dimension Template ID',
    `event_type_l2_id` INT UNSIGNED NOT NULL COMMENT '이벤트 유형 L2 ID',
    `template_json` JSON NOT NULL COMMENT 'Dimension 정의 배열 JSON',

    `crt_usr_logn_id` VARCHAR(100) COLLATE utf8mb4_bin NOT NULL DEFAULT 'system' COMMENT '생성자',
    `crt_dtm` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) COMMENT '생성일시',
    `mod_usr_logn_id` VARCHAR(100) COLLATE utf8mb4_bin NOT NULL DEFAULT 'system' COMMENT '수정자',
    `mod_dtm` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6) COMMENT '수정일시',
    `del_yn` CHAR(1) COLLATE utf8mb4_bin NOT NULL DEFAULT 'N' COMMENT '삭제여부',

    PRIMARY KEY (`scenario_dimension_template_id`),
    UNIQUE KEY `uk_tmm_mi_scenario_dimension_template_m_01` (`event_type_l2_id`),

    CONSTRAINT `ck_tmm_mi_scenario_dimension_template_m_01`
        CHECK (JSON_TYPE(template_json) = 'ARRAY'),
    CONSTRAINT `fk_tmm_mi_scenario_dimension_template_m_01`
        FOREIGN KEY (`event_type_l2_id`)
        REFERENCES `tmm_mi_event_type_l2_m` (`event_type_l2_id`)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_bin
  COMMENT='시나리오 Dimension Template';


-- =========================================================
-- Table: tmm_mi_scenario_m
-- =========================================================

CREATE TABLE `tmm_mi_scenario_m` (
    `scenario_id` INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '시나리오 ID',
    `scenario_group_id` INT UNSIGNED NOT NULL COMMENT '시나리오 그룹 ID',
    `title` VARCHAR(255) COLLATE utf8mb4_bin NOT NULL COMMENT '시나리오명',
    `narrative` TEXT COLLATE utf8mb4_bin NULL COMMENT '시나리오 내러티브',
    `dimension_values` JSON NOT NULL COMMENT '시나리오 주요 가정 (dimension values)',
    `probability_score` DECIMAL(5,2) NULL COMMENT '시나리오 발생확률',
    `probability_level` VARCHAR(50) COLLATE utf8mb4_bin NULL COMMENT '시나리오 확률 레벨',
    `probability_delta` DECIMAL(5,2) NULL COMMENT '시나리오 확률 증감',
    `impact_jkm` VARCHAR(50) COLLATE utf8mb4_bin NULL COMMENT '이벤트 임팩트(JKM)',
    `impact_ttf` VARCHAR(50) COLLATE utf8mb4_bin NULL COMMENT '이벤트 임팩트(TTF)',
    `impact_hh` VARCHAR(50) COLLATE utf8mb4_bin NULL COMMENT '이벤트 임팩트(HH)',
    `feasibility_score` SMALLINT NULL COMMENT '실현가능성 점수',
    `judgment_status_code` VARCHAR(50) COLLATE utf8mb4_bin NULL DEFAULT '대기' COMMENT '판정 상태 코드',
    `display_order` INT NOT NULL DEFAULT 0 COMMENT '표시 순서',
    `baseline_yn` CHAR(1) COLLATE utf8mb4_bin NOT NULL DEFAULT 'N' COMMENT '기준 시나리오 여부',

    `crt_usr_logn_id` VARCHAR(100) COLLATE utf8mb4_bin NOT NULL DEFAULT 'system' COMMENT '생성자',
    `crt_dtm` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) COMMENT '생성일시',
    `mod_usr_logn_id` VARCHAR(100) COLLATE utf8mb4_bin NOT NULL DEFAULT 'system' COMMENT '수정자',
    `mod_dtm` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6) COMMENT '수정일시',
    `del_yn` CHAR(1) COLLATE utf8mb4_bin NOT NULL DEFAULT 'N' COMMENT '삭제여부',

    PRIMARY KEY (`scenario_id`),
    KEY `idx_tmm_mi_scenario_m_01` (`scenario_group_id`),

    CONSTRAINT `ck_tmm_mi_scenario_m_01`
        CHECK (JSON_TYPE(dimension_values) = 'ARRAY'),
    CONSTRAINT `fk_tmm_mi_scenario_m_01`
        FOREIGN KEY (`scenario_group_id`)
        REFERENCES `tmm_mi_scenario_group_m` (`scenario_group_id`)
        ON DELETE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_bin
  COMMENT='시나리오';


-- =========================================================
-- Table: tmm_mi_signpost_m
-- =========================================================

CREATE TABLE `tmm_mi_signpost_m` (
    `signpost_id` INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT 'Signpost ID',
    `scenario_id` INT UNSIGNED NOT NULL COMMENT '시나리오 ID',
    `label` VARCHAR(500) COLLATE utf8mb4_bin NOT NULL COMMENT 'signpost label',
    `probability_direction_code` VARCHAR(50) COLLATE utf8mb4_bin NULL COMMENT '확률 변화 방향',
    `probability_impact_score` DECIMAL(5,2) NULL COMMENT '확률 변화 강도',
    `signpost_reason` TEXT COLLATE utf8mb4_bin NULL COMMENT 'signpost 근거',
    `display_order` INT NOT NULL DEFAULT 0 COMMENT '표시 순서',

    `crt_usr_logn_id` VARCHAR(100) COLLATE utf8mb4_bin NOT NULL DEFAULT 'system' COMMENT '생성자',
    `crt_dtm` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) COMMENT '생성일시',
    `mod_usr_logn_id` VARCHAR(100) COLLATE utf8mb4_bin NOT NULL DEFAULT 'system' COMMENT '수정자',
    `mod_dtm` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6) COMMENT '수정일시',
    `del_yn` CHAR(1) COLLATE utf8mb4_bin NOT NULL DEFAULT 'N' COMMENT '삭제여부',

    PRIMARY KEY (`signpost_id`),
    KEY `idx_tmm_mi_signpost_m_01` (`scenario_id`),

    CONSTRAINT `fk_tmm_mi_signpost_m_01`
        FOREIGN KEY (`scenario_id`)
        REFERENCES `tmm_mi_scenario_m` (`scenario_id`)
        ON DELETE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_bin
  COMMENT='Signpost';


-- =========================================================
-- Table: tmm_mi_signpost_event_m
-- =========================================================

CREATE TABLE `tmm_mi_signpost_event_m` (
    `signpost_event_id` INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT 'Signpost 이벤트 ID',
    `signpost_id` INT UNSIGNED NOT NULL COMMENT 'Signpost ID',
    `mi_event_id` INT UNSIGNED NULL COMMENT '연결 MI 이벤트 ID',
    `occurred_at` DATETIME NULL COMMENT 'Signpost 이벤트 발생일시',
    `summary` TEXT COLLATE utf8mb4_bin NOT NULL COMMENT 'signpost 이벤트 요약',
    `probability_score` DECIMAL(5,2) NULL COMMENT '시나리오 확률 업데이트 확률',
    `probability_delta` DECIMAL(5,2) NULL COMMENT '시나리오 확률 업데이트 조정',
    `matching_reason` TEXT COLLATE utf8mb4_bin NULL COMMENT '상세내역 (signpost 매칭 근거)',

    `crt_usr_logn_id` VARCHAR(100) COLLATE utf8mb4_bin NOT NULL DEFAULT 'system' COMMENT '생성자',
    `crt_dtm` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) COMMENT '생성일시',
    `mod_usr_logn_id` VARCHAR(100) COLLATE utf8mb4_bin NOT NULL DEFAULT 'system' COMMENT '수정자',
    `mod_dtm` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6) COMMENT '수정일시',
    `del_yn` CHAR(1) COLLATE utf8mb4_bin NOT NULL DEFAULT 'N' COMMENT '삭제여부',

    PRIMARY KEY (`signpost_event_id`),
    KEY `idx_tmm_mi_signpost_event_m_01` (`signpost_id`),
    KEY `idx_tmm_mi_signpost_event_m_02` (`mi_event_id`),

    CONSTRAINT `fk_tmm_mi_signpost_event_m_01`
        FOREIGN KEY (`signpost_id`)
        REFERENCES `tmm_mi_signpost_m` (`signpost_id`)
        ON DELETE CASCADE,
    CONSTRAINT `fk_tmm_mi_signpost_event_m_02`
        FOREIGN KEY (`mi_event_id`)
        REFERENCES `tmm_mi_mievent_m` (`mi_event_id`)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_bin
  COMMENT='Signpost 이벤트';


-- =========================================================
-- Table: tmm_mi_snapshot_m
-- =========================================================

CREATE TABLE `tmm_mi_snapshot_m` (
    `snapshot_id` INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '스냅샷 ID',
    `scenario_group_id` INT UNSIGNED NOT NULL COMMENT '시나리오 그룹 ID',
    `stage_no` SMALLINT NOT NULL COMMENT '단계 번호 (1·2)',
    `phase_code` VARCHAR(50) COLLATE utf8mb4_bin NOT NULL COMMENT '단계 구분 (BEFORE/AFTER)',

    `crt_usr_logn_id` VARCHAR(100) COLLATE utf8mb4_bin NOT NULL DEFAULT 'system' COMMENT '생성자',
    `crt_dtm` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) COMMENT '생성일시',
    `mod_usr_logn_id` VARCHAR(100) COLLATE utf8mb4_bin NOT NULL DEFAULT 'system' COMMENT '수정자',
    `mod_dtm` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6) COMMENT '수정일시',
    `del_yn` CHAR(1) COLLATE utf8mb4_bin NOT NULL DEFAULT 'N' COMMENT '삭제여부',

    PRIMARY KEY (`snapshot_id`),
    UNIQUE KEY `uk_tmm_mi_snapshot_m_01` (`scenario_group_id`, `stage_no`, `phase_code`),

    CONSTRAINT `fk_tmm_mi_snapshot_m_01`
        FOREIGN KEY (`scenario_group_id`)
        REFERENCES `tmm_mi_scenario_group_m` (`scenario_group_id`)
        ON DELETE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_bin
  COMMENT='스냅샷';


-- =========================================================
-- Table: tmm_mi_scenario_snap_m
-- =========================================================

CREATE TABLE `tmm_mi_scenario_snap_m` (
    `scenario_snap_id` INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '시나리오 스냅샷 ID',
    `snapshot_id` INT UNSIGNED NOT NULL COMMENT '스냅샷 ID',
    `src_scenario_id` INT UNSIGNED NOT NULL COMMENT '원본 시나리오 ID (추적용, FK 미설정)',
    `dimension_values` JSON NOT NULL COMMENT 'dimension 값 (스냅샷 시점 동결)',
    `probability_score` DECIMAL(5,2) NULL COMMENT '발생확률 (동결)',
    `judgment_status_code` VARCHAR(50) COLLATE utf8mb4_bin NULL COMMENT '판정 상태 코드 (동결)',
    `baseline_yn` CHAR(1) COLLATE utf8mb4_bin NOT NULL DEFAULT 'N' COMMENT '기준 시나리오 여부 (동결)',

    `crt_usr_logn_id` VARCHAR(100) COLLATE utf8mb4_bin NOT NULL DEFAULT 'system' COMMENT '생성자',
    `crt_dtm` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) COMMENT '생성일시',
    `mod_usr_logn_id` VARCHAR(100) COLLATE utf8mb4_bin NOT NULL DEFAULT 'system' COMMENT '수정자',
    `mod_dtm` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6) COMMENT '수정일시',
    `del_yn` CHAR(1) COLLATE utf8mb4_bin NOT NULL DEFAULT 'N' COMMENT '삭제여부',

    PRIMARY KEY (`scenario_snap_id`),
    KEY `idx_tmm_mi_scenario_snap_m_01` (`snapshot_id`),

    CONSTRAINT `ck_tmm_mi_scenario_snap_m_01`
        CHECK (JSON_TYPE(dimension_values) = 'ARRAY'),
    CONSTRAINT `fk_tmm_mi_scenario_snap_m_01`
        FOREIGN KEY (`snapshot_id`)
        REFERENCES `tmm_mi_snapshot_m` (`snapshot_id`)
        ON DELETE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_bin
  COMMENT='시나리오 스냅샷';


-- =========================================================
-- Table: tmm_mi_signpost_snap_m
-- =========================================================

CREATE TABLE `tmm_mi_signpost_snap_m` (
    `signpost_snap_id` INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT 'Signpost 스냅샷 ID',
    `snapshot_id` INT UNSIGNED NOT NULL COMMENT '스냅샷 ID',
    `scenario_snap_id` INT UNSIGNED NOT NULL COMMENT '시나리오 스냅샷 ID (스냅샷 내부 부모)',
    `src_signpost_id` INT UNSIGNED NOT NULL COMMENT '원본 Signpost ID (추적용, FK 미설정)',
    `label` VARCHAR(500) COLLATE utf8mb4_bin NOT NULL COMMENT 'signpost label (동결)',
    `probability_direction_code` VARCHAR(50) COLLATE utf8mb4_bin NULL COMMENT '확률 변화 방향 (동결)',
    `probability_impact_score` DECIMAL(5,2) NULL COMMENT '확률 변화 강도 (동결)',

    `crt_usr_logn_id` VARCHAR(100) COLLATE utf8mb4_bin NOT NULL DEFAULT 'system' COMMENT '생성자',
    `crt_dtm` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) COMMENT '생성일시',
    `mod_usr_logn_id` VARCHAR(100) COLLATE utf8mb4_bin NOT NULL DEFAULT 'system' COMMENT '수정자',
    `mod_dtm` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6) COMMENT '수정일시',
    `del_yn` CHAR(1) COLLATE utf8mb4_bin NOT NULL DEFAULT 'N' COMMENT '삭제여부',

    PRIMARY KEY (`signpost_snap_id`),
    KEY `idx_tmm_mi_signpost_snap_m_01` (`snapshot_id`),
    KEY `idx_tmm_mi_signpost_snap_m_02` (`scenario_snap_id`),

    CONSTRAINT `fk_tmm_mi_signpost_snap_m_01`
        FOREIGN KEY (`snapshot_id`)
        REFERENCES `tmm_mi_snapshot_m` (`snapshot_id`)
        ON DELETE CASCADE,
    CONSTRAINT `fk_tmm_mi_signpost_snap_m_02`
        FOREIGN KEY (`scenario_snap_id`)
        REFERENCES `tmm_mi_scenario_snap_m` (`scenario_snap_id`)
        ON DELETE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_bin
  COMMENT='Signpost 스냅샷';


-- =========================================================
-- Auto Update Triggers (all tables)
-- =========================================================

DROP TRIGGER IF EXISTS `tr_tmm_mi_mievent_m_upd`;
CREATE TRIGGER `tr_tmm_mi_mievent_m_upd` BEFORE UPDATE ON `tmm_mi_mievent_m`
FOR EACH ROW SET NEW.mod_dtm = NOW();

DROP TRIGGER IF EXISTS `tr_tmm_mi_impact_m_upd`;
CREATE TRIGGER `tr_tmm_mi_impact_m_upd` BEFORE UPDATE ON `tmm_mi_impact_m`
FOR EACH ROW SET NEW.mod_dtm = NOW();

DROP TRIGGER IF EXISTS `tr_tmm_mi_impact_base_case_m_upd`;
CREATE TRIGGER `tr_tmm_mi_impact_base_case_m_upd` BEFORE UPDATE ON `tmm_mi_impact_base_case_m`
FOR EACH ROW SET NEW.mod_dtm = NOW();
    
DROP TRIGGER IF EXISTS `tr_tmm_mi_impact_result_m_upd`;
CREATE TRIGGER `tr_tmm_mi_impact_result_m_upd` BEFORE UPDATE ON `tmm_mi_impact_result_m`
FOR EACH ROW SET NEW.mod_dtm = NOW();

DROP TRIGGER IF EXISTS `tr_tmm_mi_impact_driver_m_upd`;
CREATE TRIGGER `tr_tmm_mi_impact_driver_m_upd` BEFORE UPDATE ON `tmm_mi_impact_driver_m`
FOR EACH ROW SET NEW.mod_dtm = NOW();

DROP TRIGGER IF EXISTS `tr_tmm_drivertreenodem_upd`;
CREATE TRIGGER `tr_tmm_drivertreenodem_upd` BEFORE UPDATE ON `tmm_drivertreenodem`
FOR EACH ROW SET NEW.mod_dtm = NOW();

DROP TRIGGER IF EXISTS `tr_tmm_priceforecastm_upd`;
CREATE TRIGGER `tr_tmm_priceforecastm_upd` BEFORE UPDATE ON `tmm_priceforecastm`
FOR EACH ROW SET NEW.mod_dtm = NOW();

DROP TRIGGER IF EXISTS `tr_tmd_drivertreem_upd`;
CREATE TRIGGER `tr_tmd_drivertreem_upd` BEFORE UPDATE ON `tmd_drivertreem`
FOR EACH ROW SET NEW.mod_dtm = NOW();
