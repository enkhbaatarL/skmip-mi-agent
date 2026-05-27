-- =========================================================
-- MI Agent ERD MySQL DDL
-- =========================================================

-- =========================================================
-- Drop existing tables (FK-safe order: child tables first)
-- =========================================================
DROP TABLE IF EXISTS `tmm_mi_mievent_candidate_record_map`;
DROP TABLE IF EXISTS `tmm_mi_mievent_record_map`;
DROP TABLE IF EXISTS `tmm_mi_mievent_candidate_m`;
DROP TABLE IF EXISTS `tmm_mi_mievent_m`;
DROP TABLE IF EXISTS `tmm_mi_record_metacuration_item`;
DROP TABLE IF EXISTS `tmm_mi_record_metacuration_m`;
DROP TABLE IF EXISTS `tmm_mi_event_type_l2_m`;
DROP TABLE IF EXISTS `tmm_mi_event_type_l1_m`;

DROP TABLE IF EXISTS `tmm_signpostm`;
DROP TABLE IF EXISTS `tmm_scenarioversionm`;
DROP TABLE IF EXISTS `tmm_scenariom`;
DROP TABLE IF EXISTS `tmm_drivertagm`;
DROP TABLE IF EXISTS `tmm_timebucketm`;
DROP TABLE IF EXISTS `tmm_priceforecastm`;
DROP TABLE IF EXISTS `tmm_drivertreenodem`;
DROP TABLE IF EXISTS `tmm_impactresultm`;
DROP TABLE IF EXISTS `tmm_impactm`;
DROP TABLE IF EXISTS `tmm_mi_impact_driver_m`;
DROP TABLE IF EXISTS `tmm_mi_impact_result_m`;
DROP TABLE IF EXISTS `tmm_mi_impact_base_case_m`;
DROP TABLE IF EXISTS `tmm_mi_impact_m`;
DROP TABLE IF EXISTS `tmd_drivertreem`;

-- =========================================================
-- GROUP 1: Core MI Event Tables (COLLATE utf8mb4_bin)
-- =========================================================

-- =========================================================
-- Table: tmm_mi_event_type_l1_m
-- =========================================================
CREATE TABLE `tmm_mi_event_type_l1_m` (
    `event_type_l1_id` INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '이벤트 유형 L1 PK',
    `level_1_code` VARCHAR(100) NOT NULL COMMENT '이벤트 유형 L1 코드',
    `level_1_label` VARCHAR(200) NOT NULL COMMENT '이벤트 유형 L1 한글명',
    `crt_usr_logn_id` VARCHAR(100) NOT NULL DEFAULT 'system' COMMENT '생성자',
    `crt_dtm` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) COMMENT '생성일시',
    `mod_usr_logn_id` VARCHAR(100) NOT NULL DEFAULT 'system' COMMENT '수정자',
    `mod_dtm` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6) COMMENT '수정일시',
    `del_yn` CHAR(1) NOT NULL DEFAULT 'N' COMMENT '삭제여부',
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
    `level_2_code` VARCHAR(150) NOT NULL COMMENT '이벤트 유형 L2 코드',
    `level_2_label` VARCHAR(200) NOT NULL COMMENT '이벤트 유형 L2 한글명',
    `crt_usr_logn_id` VARCHAR(100) NOT NULL DEFAULT 'system' COMMENT '생성자',
    `crt_dtm` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) COMMENT '생성일시',
    `mod_usr_logn_id` VARCHAR(100) NOT NULL DEFAULT 'system' COMMENT '수정자',
    `mod_dtm` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6) COMMENT '수정일시',
    `del_yn` CHAR(1) NOT NULL DEFAULT 'N' COMMENT '삭제여부',
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
        REFERENCES `midb`.`tmd_mi_record` (`mi_record_id`)
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

    `supply_demand_side` VARCHAR(20) COLLATE utf8mb4_bin NOT NULL DEFAULT 'unclear' COMMENT 'supply/demand/both/none/unclear',
    `score` DECIMAL(4, 1) NOT NULL COMMENT 'Record와 이벤트 유형 후보의 연관 점수',
    `reason` TEXT COLLATE utf8mb4_bin NULL COMMENT '점수 근거',

    `entities_json` JSON NULL COMMENT '엔티티 목록 JSON',
    `regions_json` JSON NULL COMMENT '지역 목록 JSON',
    `event_signature_json` JSON NULL COMMENT 'Event 매칭/중복 제거를 위한 식별 정보 JSON',
    `event_timing_json` JSON NULL COMMENT '사건 발생 시각 정보 JSON',

    `lng_relevance` VARCHAR(30) COLLATE utf8mb4_bin NOT NULL DEFAULT 'unclear' COMMENT 'LNG 관련성 (direct_lng/gas_market_direct/energy_indirect/non_lng_noise)',
    `lng_relevance_reason` TEXT COLLATE utf8mb4_bin NULL COMMENT 'LNG 관련성 판단 근거',

    `crt_usr_logn_id` VARCHAR(100) COLLATE utf8mb4_bin NOT NULL DEFAULT 'system' COMMENT '생성자',
    `crt_dtm` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) COMMENT '생성일시',
    `mod_usr_logn_id` VARCHAR(100) COLLATE utf8mb4_bin NOT NULL DEFAULT 'system' COMMENT '수정자',
    `mod_dtm` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6) COMMENT '수정일시',
    `del_yn` CHAR(1) COLLATE utf8mb4_bin NOT NULL DEFAULT 'N' COMMENT '삭제여부',

    PRIMARY KEY (`mi_record_metacuration_item_id`),

    UNIQUE KEY `uk_tmm_mi_record_metacuration_item_01` (
        `mi_record_metacuration_id`,
        `event_type_l2_id`
    ),

    KEY `idx_tmm_mi_record_metacuration_item_01` (`mi_record_metacuration_id`),
    KEY `idx_tmm_mi_record_metacuration_item_02` (`event_type_l2_id`),
    KEY `idx_tmm_mi_record_metacuration_item_03` (`score`),
    KEY `idx_tmm_mi_record_metacuration_item_04` (`supply_demand_side`),
    KEY `idx_tmm_mi_record_metacuration_item_05` (`lng_relevance`),

    CONSTRAINT `fk_tmm_mi_record_metacuration_item_01`
        FOREIGN KEY (`mi_record_metacuration_id`)
        REFERENCES `midb`.`tmm_mi_record_metacuration_m` (`mi_record_metacuration_id`),

    CONSTRAINT `fk_tmm_mi_record_metacuration_item_02`
        FOREIGN KEY (`event_type_l2_id`)
        REFERENCES `midb`.`tmm_mi_event_type_l2_m` (`event_type_l2_id`)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_bin
  COMMENT='MI Record Metadata Curation Item';


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
    `market_and_institution_view` LONGTEXT COLLATE utf8mb4_bin NULL COMMENT '시장 반응 및 기관 전망',
    `tags_json` JSON NULL COMMENT '이벤트 태그 목록 JSON',
    `occurred_at` DATETIME(6) NULL COMMENT '이벤트 실제 발생 일시',

    `decision` VARCHAR(30) COLLATE utf8mb4_bin NOT NULL DEFAULT 'raw' COMMENT '후보 처리 상태(RAW, MATCH_EXISTING, CREATE_NEW, AMBIGUOUS_REVIEW)',
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
        REFERENCES `midb`.`tmm_mi_event_type_l2_m` (`event_type_l2_id`),

    CONSTRAINT `fk_tmm_mi_mievent_candidate_m_02`
        FOREIGN KEY (`mi_event_id`)
        REFERENCES `midb`.`tmm_mi_mievent_m` (`mi_event_id`)
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

    UNIQUE KEY `uk_tmm_mi_mievent_candidate_record_map_01` (
        `mi_event_candidate_id`,
        `mi_record_id`
    ),

    KEY `idx_tmm_mi_mievent_candidate_record_map_01` (`mi_event_candidate_id`),
    KEY `idx_tmm_mi_mievent_candidate_record_map_02` (`mi_record_id`),
    KEY `idx_tmm_mi_mievent_candidate_record_map_03` (`lng_relevance`),

    CONSTRAINT `fk_tmm_mi_mievent_candidate_record_map_01`
        FOREIGN KEY (`mi_event_candidate_id`)
        REFERENCES `midb`.`tmm_mi_mievent_candidate_m` (`mi_event_candidate_id`),

    CONSTRAINT `fk_tmm_mi_mievent_candidate_record_map_02`
        FOREIGN KEY (`mi_record_id`)
        REFERENCES `midb`.`tmd_mi_record` (`mi_record_id`)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_bin
  COMMENT='MI Event 후보 - MI Record 매핑';

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
    `market_and_institution_view` LONGTEXT COLLATE utf8mb4_bin NULL COMMENT '시장 반응 및 기관 전망',
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
        REFERENCES `midb`.`tmm_mi_event_type_l2_m` (`event_type_l2_id`)
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

    UNIQUE KEY `uk_tmm_mi_mievent_record_map_01` (
        `mi_event_id`,
        `mi_record_id`
    ),

    KEY `idx_tmm_mi_mievent_record_map_01` (`mi_record_id`),

    CONSTRAINT `fk_tmm_mi_mievent_record_map_01`
        FOREIGN KEY (`mi_event_id`)
        REFERENCES `midb`.`tmm_mi_mievent_m` (`mi_event_id`),

    CONSTRAINT `fk_tmm_mi_mievent_record_map_02`
        FOREIGN KEY (`mi_record_id`)
        REFERENCES `midb`.`tmd_mi_record` (`mi_record_id`)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_bin
  COMMENT='MI Event - MI Record 매핑';

-- =========================================================
-- GROUP 2: Impact / Scenario / Driver Tables
-- =========================================================

-- =========================================================
-- Table: tmm_mi_impact_m
-- =========================================================
DROP TABLE IF EXISTS `tmm_mi_impact_m`;
CREATE TABLE `tmm_mi_impact_m` (
  `impact_id`          VARCHAR(40)   NOT NULL                   COMMENT 'Impact ID PK impact_ev_[a-z0-9_]+',
  `mi_event_id`        VARCHAR(20)   NOT NULL                   COMMENT 'MI Event ID FK',
  `base_case_id`       VARCHAR(60)   NULL                       COMMENT 'MI Event Base Case ID FK',
  `base_case_skip`     TINYINT(1)    NOT NULL DEFAULT 0         COMMENT 'Base Case 미명시로 단기만 산출한 경우 1',
  `crt_usr_logn_id`    VARCHAR(50)   NOT NULL DEFAULT 'SYSTEM'  COMMENT '생성자',
  `crt_dtm`            DATETIME      NOT NULL DEFAULT NOW()     COMMENT '생성 일시',
  `mod_usr_logn_id`    VARCHAR(50)   NOT NULL DEFAULT 'SYSTEM'  COMMENT '수정 사용자 ID',
  `mod_dtm`            DATETIME      NULL DEFAULT NOW()         COMMENT '수정 일시',
  `del_yn`             CHAR(1)       NOT NULL DEFAULT 'N'       COMMENT '삭제 여부 Y/N',
  PRIMARY KEY (`impact_id`),
  INDEX `tmm_mi_impact_m_ix01` (`mi_event_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='MI Event Impact Master';

-- ============================================================
-- Table: tmm_mi_impact_base_case_m
-- ============================================================
DROP TABLE IF EXISTS `tmm_mi_impact_base_case_m`;
CREATE TABLE `tmm_mi_impact_base_case_m` (
  `base_case_id`            VARCHAR(60)   NOT NULL               COMMENT 'Base Case 고유 ID PK',
  `impact_id`               VARCHAR(40)   NOT NULL               COMMENT 'Impact ID FK',
  `base_case_available`     TINYINT(1)    NOT NULL DEFAULT 0     COMMENT 'Base Case 명시 여부 (0=미명시, 1=명시)',
  `base_case_text`          TEXT                                 COMMENT '추출된 Base Case 전망 텍스트',
  `source_record_ids`       JSON                                 COMMENT '근거 Record ID 목록 (최대 5건)',
  `uncertainty_level`       ENUM('n/a','none','low','medium','high') NOT NULL DEFAULT 'n/a'              COMMENT 'Base Case 충돌 수준',
  `conflict_detected`       TINYINT(1)    NOT NULL DEFAULT 0     COMMENT '충돌 감지 여부',
  `conflict_detail`         JSON                                 COMMENT '충돌 claim 목록 [{record_id, publish_date, claim}]',
  `reconciliation_note`     VARCHAR(500)                         COMMENT '충돌 해소 방식 설명',
  `scenario_recommended`    TINYINT(1)    NOT NULL DEFAULT 0     COMMENT 'uncertainty medium/high → 1',
  `scenario_recommend_reason` VARCHAR(500)                       COMMENT '충돌 정보 기반 자동 생성 사유 텍스트',
  `crt_usr_logn_id`         VARCHAR(50)   NOT NULL DEFAULT 'SYSTEM' COMMENT '생성 사용자 ID',
  `crt_dtm`                 DATETIME      NOT NULL DEFAULT NOW() COMMENT '생성 일시',
  `mod_usr_logn_id`         VARCHAR(50)   NOT NULL DEFAULT 'SYSTEM' COMMENT '수정 사용자 ID',
  `mod_dtm`                 DATETIME      NOT NULL DEFAULT NOW() COMMENT '수정 일시',
  `del_yn`                  CHAR(1)       NOT NULL DEFAULT 'N'   COMMENT '삭제 여부 Y/N',
  PRIMARY KEY (`base_case_id`),
  INDEX `tmm_mi_impact_base_case_m_ix01`    (`uncertainty_level`),
  INDEX `tmm_mi_impact_base_case_m_ix02`    (`base_case_available`),
  INDEX `tmm_mi_impact_base_case_m_ix03`    (`scenario_recommended`)     COMMENT '시나리오화 추천 대상 조회'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='MI Event Impact Base Case Master';

-- =========================================================
-- Table: tmm_mi_impact_result_m
-- =========================================================
DROP TABLE IF EXISTS `tmm_mi_impact_result_m`;
CREATE TABLE `tmm_mi_impact_result_m` (
  `impact_result_id`       VARCHAR(64)   NOT NULL               COMMENT 'Impact Result ID PK',
  `impact_id`              VARCHAR(64)   NOT NULL               COMMENT 'Impact ID FK impact_ev_*',
  `target_type`            VARCHAR(20)   NOT NULL               COMMENT '대상 유형 price|spread',
  `target_id`              VARCHAR(20)   NOT NULL               COMMENT 'JKM / TTF / HH',
  `impact_short`           ENUM('상승_상','상승_중','상승_하','영향없음','하락_하','하락_중','하락_상') NOT NULL DEFAULT '영향없음'          COMMENT '단기 영향 (0~1M)',
  `impact_mid`             ENUM('상승_상','상승_중','상승_하','영향없음','하락_하','하락_중','하락_상') NULL DEFAULT NULL                  COMMENT '중기 영향 (6M). Base Case 없으면 NULL',
  `impact_long`            ENUM('상승_상','상승_중','상승_하','영향없음','하락_하','하락_중','하락_상') NULL DEFAULT NULL                  COMMENT '장기 영향 (1Y+). Base Case 없으면 NULL',
  `confidence`             DECIMAL(5,4)  NULL                   COMMENT '신뢰도 0~1',
  `rationale_base_case`    TEXT                                 COMMENT '사용한 Base Case 가정',
  `rationale_driver_map`   TEXT                                 COMMENT 'Step 1 driver 영향 요약',
  `rationale_synthesis`    TEXT                                 COMMENT '종합 판단 logic',
  `completed`              CHAR(1)       NOT NULL DEFAULT 'N'   COMMENT '분석 완료 여부 Y/N',
  `analysis_time`          DATETIME      NULL                   COMMENT '분석 완료 일시 ISO-8601',
  `crt_usr_logn_id`        VARCHAR(50)   NOT NULL DEFAULT 'SYSTEM' COMMENT '생성 사용자 ID',
  `crt_dtm`                DATETIME      NOT NULL DEFAULT NOW() COMMENT '생성 일시',
  `mod_usr_logn_id`        VARCHAR(50)   NOT NULL DEFAULT 'SYSTEM' COMMENT '수정 사용자 ID',
  `mod_dtm`                DATETIME      NOT NULL DEFAULT NOW() COMMENT '수정 일시',
  `del_yn`                 CHAR(1)       NOT NULL DEFAULT 'N'   COMMENT '삭제 여부 Y/N',
  PRIMARY KEY (`impact_result_id`),
  INDEX `tmm_mi_impact_result_m_ix01` (`impact_id`),
  INDEX `tmm_mi_impact_result_m_ix02` (`target_id`),
  INDEX `tmm_mi_impact_result_m_ix03` (`target_id`, `impact_short`),
  INDEX `tmm_mi_impact_result_m_ix04` (`target_id`, `impact_mid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Impact Result Master';

-- =========================================================
-- Table: tmm_mi_impact_driver_m
-- =========================================================
DROP TABLE IF EXISTS `tmm_mi_impact_driver_m`;
CREATE TABLE tmm_mi_impact_driver_m (
  `driver_id`        VARCHAR(64)   NOT NULL               COMMENT 'Driver Tag ID PK',
  `impact_result_id` VARCHAR(64)   NOT NULL               COMMENT 'Impact Result ID FK',
  `lv1_id`           VARCHAR(50)   NOT NULL               COMMENT 'Driver Tree 1단계 코드',
  `lv1_label`        VARCHAR(100)  NULL                   COMMENT 'Driver Tree 1단계 명칭',
  `lv2_id`           VARCHAR(50)   NOT NULL               COMMENT 'Driver Tree 2단계 코드',
  `lv2_label`        VARCHAR(100)  NULL                   COMMENT 'Driver Tree 2단계 명칭',
  `lv3_id`           VARCHAR(50)   NOT NULL               COMMENT 'Driver Tree 3단계 코드',
  `lv3_label`        VARCHAR(100)  NULL                   COMMENT 'Driver Tree 3단계 명칭',
  `direction_hint`   VARCHAR(50)   NULL                   COMMENT '방향 힌트 bullish_if_up/bearish_if_up/contextual',
  `match_score`      DECIMAL(5,4)  NULL                   COMMENT 'Event-Driver 매핑 신뢰도 점수 0~1',
  `matched_keywords` JSON          NULL                   COMMENT '매칭된 키워드 목록',
  `driver_reason`    TEXT          NULL                   COMMENT 'Driver 영향 발생 사유',
  `impact_short`     ENUM('상승_상','상승_중','상승_하','영향없음','하락_하','하락_중','하락_상') NOT NULL DEFAULT '영향없음'          COMMENT 'driver의 단기 영향',
  `impact_mid`       ENUM('상승_상','상승_중','상승_하','영향없음','하락_하','하락_중','하락_상') NULL DEFAULT NULL                    COMMENT 'driver의 중기 영향',
  `impact_long`      ENUM('상승_상','상승_중','상승_하','영향없음','하락_하','하락_중','하락_상') NULL DEFAULT NULL                    COMMENT 'driver의 장기 영향',
  `crt_usr_logn_id`  VARCHAR(50)   NOT NULL DEFAULT 'SYSTEM' COMMENT '생성 사용자 ID',
  `crt_dtm`          DATETIME      NOT NULL DEFAULT NOW() COMMENT '생성 일시',
  `mod_usr_logn_id`  VARCHAR(50)   NOT NULL DEFAULT 'SYSTEM' COMMENT '수정 사용자 ID',
  `mod_dtm`          DATETIME      NOT NULL DEFAULT NOW() COMMENT '수정 일시',
  `del_yn`           CHAR(1)       NOT NULL DEFAULT 'N'   COMMENT '삭제 여부 Y/N',
  PRIMARY KEY (`driver_id`),
  INDEX `tmm_mi_impact_driver_m_ix01` (`impact_result_id`),
  INDEX `tmm_mi_impact_driver_m_ix02` (`lv3_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Driver Tag Master';

-- =========================================================
-- Table: tmm_timebucketm
-- =========================================================
DROP TABLE IF EXISTS `tmm_timebucketm`;
CREATE TABLE `tmm_timebucketm` (
  `time_bucket_id`        VARCHAR(64)     NOT NULL COMMENT 'Time Bucket ID PK',
  `crt_user_id`           VARCHAR(50)     NOT NULL DEFAULT 'SYSTEM' COMMENT '생성 사용자 ID',
  `crt_dtm`               DATETIME        NOT NULL DEFAULT NOW() COMMENT '생성 일시',
  `mod_user_id`           VARCHAR(50)     NOT NULL DEFAULT 'SYSTEM' COMMENT '수정 사용자 ID',
  `mod_dtm`               DATETIME        NOT NULL DEFAULT NOW() COMMENT '수정 일시',
  `del_yn`                CHAR(1)         NOT NULL DEFAULT 'N' COMMENT '삭제 여부 Y/N',
  `qualitative_impact_id` VARCHAR(64)     NOT NULL COMMENT 'Qualitative Impact ID FK',
  `horizon`               VARCHAR(20)     NULL COMMENT '시간대 구분 immediate/short/medium/long',
  `expected_peak`         VARCHAR(20)     NULL COMMENT '최대 영향 크기 low/medium/high/extreme',
  `start_at`              DATETIME        NULL COMMENT '기간 시작 일시',
  `end_at`                DATETIME        NULL COMMENT '기간 종료 일시',
  `notes`                 TEXT            NULL COMMENT '특이사항 설명',
  PRIMARY KEY (`time_bucket_id`),
  INDEX `tmm_timebucketm_ix01` (`qualitative_impact_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Time Bucket Master';

-- =========================================================
-- Table: tmm_scenariom
-- =========================================================
DROP TABLE IF EXISTS `tmm_scenariom`;
CREATE TABLE `tmm_scenariom` (
    `scenario_id`           INT UNSIGNED    NOT NULL AUTO_INCREMENT COMMENT '시나리오 일련번호 (PK)',
    `crt_dtm`               DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '시나리오 최초생성일시',
    `scenario_group_id`     VARCHAR(200)    NOT NULL COMMENT '시나리오 그룹 키 (scg_[A-Za-z0-9]{10})',
    `crt_usr_logn_id`       VARCHAR(50)     NOT NULL DEFAULT 'SYSTEM' COMMENT '생성사용자로그인ID',
    `mod_usr_logn_id`       VARCHAR(50)     NOT NULL DEFAULT 'SYSTEM' COMMENT '수정사용자로그인ID',
    `mod_dtm`               DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '수정일시',
    `del_yn`                CHAR(1)         NOT NULL DEFAULT 'N' COMMENT '삭제여부 (Y/N)',
    `name`                  VARCHAR(500)    NOT NULL COMMENT '시나리오 명칭 (Base Event title 기반)',
    `description`           TEXT            NOT NULL COMMENT '시나리오 설명 / one_line_summary',
    `mi_event_id`           INT UNSIGNED    NOT NULL COMMENT 'Base MI Event FK (tmm_mi_mievent_m)',
    `status_code`           VARCHAR(30)     NOT NULL DEFAULT 'draft' COMMENT '시나리오 상태 (draft/active/archived)',
    `valid_from`            DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '유효기간 시작 일시',
    `valid_to`              DATETIME        NULL COMMENT '유효기간 종료 일시',
    `language`              VARCHAR(10)     NOT NULL DEFAULT 'ko' COMMENT '문서 언어',
    `dimension_values`      JSON            NOT NULL COMMENT 'Stage 4 결과 (dimension_values + price_direction)',
    `likelihood`            VARCHAR(10)     NOT NULL COMMENT '시나리오 발생 가능성 (very_high/high/medium/low/very_low 5단계)',
    `price_direction`       JSON            NOT NULL COMMENT '시나리오 가격 영향 강도 (strong_bull/bull/…/strong_bear 7단계)',
    PRIMARY KEY (`scenario_id`, `crt_dtm`),
    INDEX `tmm_scenariom_ix01` (`scenario_group_id`),
    INDEX `tmm_scenariom_ix02` (`mi_event_id`),
    INDEX `tmm_scenariom_ix03` (`status_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='시나리오 마스터 (5-Stage Pipeline 산출물 저장)';

-- =========================================================
-- Table: tmm_signpostm
-- =========================================================
DROP TABLE IF EXISTS `tmm_signpostm`;
CREATE TABLE `tmm_signpostm` (
    `signpost_id`             BIGINT          NOT NULL AUTO_INCREMENT COMMENT 'Signpost 일련번호 (PK)',
    `crt_dtm`                 DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '최초생성일시',
    `scenario_id`             INT UNSIGNED    NOT NULL COMMENT '시나리오 FK (tmm_scenariom)',
    `crt_usr_logn_id`         VARCHAR(50)     NOT NULL DEFAULT 'SYSTEM' COMMENT '생성사용자로그인ID',
    `mod_usr_logn_id`         VARCHAR(50)     DEFAULT 'SYSTEM' COMMENT '수정사용자로그인ID',
    `mod_dtm`                 DATETIME        DEFAULT CURRENT_TIMESTAMP COMMENT '수정일시',
    `del_yn`                  CHAR(1)         NOT NULL DEFAULT 'N' COMMENT '삭제여부 (Y/N)',
    `status_code`             VARCHAR(30)     NOT NULL DEFAULT 'draft' COMMENT 'Signpost 상태 (draft/active/triggered/expired/archived)',
    `language`                VARCHAR(10)     NOT NULL DEFAULT 'ko' COMMENT '문서 언어',
    `label`                   VARCHAR(500)    NOT NULL COMMENT 'Signpost 레이블 (관측 가능한 사건 기술)',
    `signpost_class`          VARCHAR(30)     DEFAULT 'observation' COMMENT 'Signpost 분류 (observation 등)',
    `signpost_source`         VARCHAR(30)     NOT NULL DEFAULT 'mi_record' COMMENT 'Signpost 출처 유형 (mi_record 등)',
    `direction`               VARCHAR(10)     NOT NULL DEFAULT 'SUP' COMMENT '시나리오 영향 방향 (SUP=지지)',
    `strength`                VARCHAR(10)     COMMENT '신호 강도 (STRONG/MEDIUM/WEAK 3단계)',
    `keyword_hints`           JSON            NOT NULL COMMENT '모니터링용 검색 키워드 리스트',
    PRIMARY KEY (`signpost_id`, `crt_dtm`),
    INDEX `tmm_signpostm_ix01` (`scenario_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Signpost 마스터 (관측 가능한 사건 신호 저장)';

-- =========================================================
-- Table: tmm_scenarioversionm
-- =========================================================
DROP TABLE IF EXISTS `tmm_scenarioversionm`;
CREATE TABLE `tmm_scenarioversionm` (
  `version_id`            INT             NOT NULL AUTO_INCREMENT COMMENT '시나리오 버전 ID PK',
  `crt_user_id`           VARCHAR(50)     NOT NULL DEFAULT 'SYSTEM' COMMENT '생성 사용자 ID',
  `crt_dtm`               DATETIME        NOT NULL DEFAULT NOW() COMMENT '생성 일시',
  `mod_user_id`           VARCHAR(50)     NOT NULL DEFAULT 'SYSTEM' COMMENT '수정 사용자 ID',
  `mod_dtm`               DATETIME        NOT NULL DEFAULT NOW() COMMENT '수정 일시',
  `del_yn`                CHAR(1)         NOT NULL DEFAULT 'N' COMMENT '삭제 여부 Y/N',
  `scenario_id`           INT             NOT NULL COMMENT '시나리오 ID FK',
  `version_number`        INT             NOT NULL COMMENT '버전 번호',
  `scenario_snapshot`     JSON            NULL COMMENT '시나리오 스냅샷 데이터',
  `change_summary`        VARCHAR(1000)   NULL COMMENT '변경 사항 요약',
  `created_by`            VARCHAR(50)     NULL COMMENT '버전 생성 사용자',
  PRIMARY KEY (`version_id`),
  INDEX `tmm_scenarioversionm_ix01` (`scenario_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Scenario Version Master';

-- =========================================================
-- Table: tmm_drivertreenodem
-- =========================================================
DROP TABLE IF EXISTS `tmm_drivertreenodem`;
CREATE TABLE `tmm_drivertreenodem` (
  `node_id`               INT             NOT NULL AUTO_INCREMENT COMMENT 'Driver Tree 노드 ID PK',
  `crt_user_id`           VARCHAR(50)     NOT NULL DEFAULT 'SYSTEM' COMMENT '생성 사용자 ID',
  `crt_dtm`               DATETIME        NOT NULL DEFAULT NOW() COMMENT '생성 일시',
  `mod_user_id`           VARCHAR(50)     NOT NULL DEFAULT 'SYSTEM' COMMENT '수정 사용자 ID',
  `mod_dtm`               DATETIME        NOT NULL DEFAULT NOW() COMMENT '수정 일시',
  `del_yn`                CHAR(1)         NOT NULL DEFAULT 'N' COMMENT '삭제 여부 Y/N',
  `scenario_id`           INT             NOT NULL COMMENT '시나리오 ID FK',
  `driver_name`           VARCHAR(100)    NOT NULL COMMENT 'Driver 명칭',
  `driver_type`           VARCHAR(50)     NULL COMMENT 'Driver 유형',
  `impact_level`          VARCHAR(20)     NULL COMMENT '영향 레벨 low/medium/high/extreme',
  `weight`                DECIMAL(8,4)    NULL COMMENT '가중치',
  `description`           TEXT            NULL COMMENT 'Driver 설명',
  `sort_order`            INT             NULL COMMENT '정렬 순서',
  PRIMARY KEY (`node_id`),
  INDEX `tmm_drivertreenodem_ix01` (`scenario_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Driver Tree Node Master';

-- =========================================================
-- Table: tmm_priceforecastm
-- =========================================================
DROP TABLE IF EXISTS `tmm_priceforecastm`;
CREATE TABLE `tmm_priceforecastm` (
  `forecast_id`           INT             NOT NULL AUTO_INCREMENT COMMENT '가격 예측 ID PK',
  `crt_user_id`           VARCHAR(50)     NOT NULL DEFAULT 'SYSTEM' COMMENT '생성 사용자 ID',
  `crt_dtm`               DATETIME        NOT NULL DEFAULT NOW() COMMENT '생성 일시',
  `mod_user_id`           VARCHAR(50)     NOT NULL DEFAULT 'SYSTEM' COMMENT '수정 사용자 ID',
  `mod_dtm`               DATETIME        NOT NULL DEFAULT NOW() COMMENT '수정 일시',
  `del_yn`                CHAR(1)         NOT NULL DEFAULT 'N' COMMENT '삭제 여부 Y/N',
  `scenario_id`           INT             NOT NULL COMMENT '시나리오 ID FK',
  `benchmark`             VARCHAR(20)     NOT NULL COMMENT '벤치마크 JKM/TTF/HH 등',
  `base_price`            DECIMAL(12,4)   NULL COMMENT '기준 가격',
  `forecast_low`          DECIMAL(12,4)   NULL COMMENT '예측 가격 하한',
  `forecast_high`         DECIMAL(12,4)   NULL COMMENT '예측 가격 상한',
  `forecast_median`       DECIMAL(12,4)   NULL COMMENT '예측 가격 중간값',
  `currency`              VARCHAR(10)     NOT NULL DEFAULT 'USD' COMMENT '통화 단위',
  `unit`                  VARCHAR(10)     NOT NULL DEFAULT 'MMBtu' COMMENT '에너지 단위',
  `forecast_date`         DATETIME        NULL COMMENT '예측 일시',
  `valid_until`           DATETIME        NULL COMMENT '유효 기간',
  `confidence_interval`   DECIMAL(5,4)    NULL COMMENT '신뢰 구간 0~1',
  PRIMARY KEY (`forecast_id`),
  INDEX `tmm_priceforecastm_ix01` (`scenario_id`),
  INDEX `tmm_priceforecastm_ix02` (`benchmark`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Price Forecast Master';

-- =========================================================
-- Table: tmd_drivertreem
-- =========================================================
CREATE TABLE `tmd_drivertreem` (
  `lv1_id`                VARCHAR(50)     NOT NULL COMMENT 'Driver Tree 1단계 코드 PK',
  `lv2_id`                VARCHAR(50)     NOT NULL COMMENT 'Driver Tree 2단계 코드 PK',
  `lv3_id`                VARCHAR(50)     NOT NULL COMMENT 'Driver Tree 3단계 코드 PK',
  `crt_user_id`           VARCHAR(50)     NOT NULL DEFAULT 'SYSTEM' COMMENT '생성 사용자 ID',
  `crt_dtm`               DATETIME        NOT NULL DEFAULT NOW() COMMENT '생성 일시',
  `mod_user_id`           VARCHAR(50)     NOT NULL DEFAULT 'SYSTEM' COMMENT '수정 사용자 ID',
  `mod_dtm`               DATETIME        NOT NULL DEFAULT NOW() COMMENT '수정 일시',
  `del_yn`                CHAR(1)         NOT NULL DEFAULT 'N' COMMENT '삭제 여부 Y/N',
  `lv1_label_ko`          VARCHAR(100)    NULL COMMENT 'Driver Tree 1단계 한국어 명칭',
  `lv2_label_ko`          VARCHAR(100)    NULL COMMENT 'Driver Tree 2단계 한국어 명칭',
  `lv3_label_ko`          VARCHAR(100)    NULL COMMENT 'Driver Tree 3단계 한국어 명칭',
  `lv1_label_en`          VARCHAR(100)    NULL COMMENT 'Driver Tree 1단계 영어 명칭',
  `lv2_label_en`          VARCHAR(100)    NULL COMMENT 'Driver Tree 2단계 영어 명칭',
  `lv3_label_en`          VARCHAR(100)    NULL COMMENT 'Driver Tree 3단계 영어 명칭',
  `direction_hint`        VARCHAR(50)     NULL COMMENT '방향 힌트 bullish_if_up/bearish_if_up/contextual',
  PRIMARY KEY (`lv1_id`, `lv2_id`, `lv3_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Driver Tree Master';

-- =========================================================
-- Auto Update Triggers (all tables)
-- =========================================================

DELIMITER //

DROP TRIGGER IF EXISTS `tr_tmm_mi_mievent_m_upd` //
CREATE TRIGGER `tr_tmm_mi_mievent_m_upd` BEFORE UPDATE ON `tmm_mi_mievent_m`
FOR EACH ROW BEGIN SET NEW.mod_dtm = NOW(); END //

DROP TRIGGER IF EXISTS `tr_tmm_impactm_upd` //
CREATE TRIGGER `tr_tmm_impactm_upd` BEFORE UPDATE ON `tmm_impactm`
FOR EACH ROW BEGIN SET NEW.mod_dtm = NOW(); END //

DROP TRIGGER IF EXISTS `tr_tmm_impactresultm_upd` //
CREATE TRIGGER `tr_tmm_impactresultm_upd` BEFORE UPDATE ON `tmm_impactresultm`
FOR EACH ROW BEGIN SET NEW.mod_dtm = NOW(); END //

DROP TRIGGER IF EXISTS `tr_tmm_drivertagm_upd` //
CREATE TRIGGER `tr_tmm_drivertagm_upd` BEFORE UPDATE ON `tmm_drivertagm`
FOR EACH ROW BEGIN SET NEW.mod_dtm = NOW(); END //

DROP TRIGGER IF EXISTS `tr_tmm_timebucketm_upd` //
CREATE TRIGGER `tr_tmm_timebucketm_upd` BEFORE UPDATE ON `tmm_timebucketm`
FOR EACH ROW BEGIN SET NEW.mod_dtm = NOW(); END //

DROP TRIGGER IF EXISTS `tr_tmm_scenariom_upd` //
CREATE TRIGGER `tr_tmm_scenariom_upd` BEFORE UPDATE ON `tmm_scenariom`
FOR EACH ROW BEGIN SET NEW.mod_dtm = NOW(); END //

DROP TRIGGER IF EXISTS `tr_tmm_signpostm_upd` //
CREATE TRIGGER `tr_tmm_signpostm_upd` BEFORE UPDATE ON `tmm_signpostm`
FOR EACH ROW BEGIN SET NEW.mod_dtm = NOW(); END //

DROP TRIGGER IF EXISTS `tr_tmm_scenarioversionm_upd` //
CREATE TRIGGER `tr_tmm_scenarioversionm_upd` BEFORE UPDATE ON `tmm_scenarioversionm`
FOR EACH ROW BEGIN SET NEW.mod_dtm = NOW(); END //

DROP TRIGGER IF EXISTS `tr_tmm_drivertreenodem_upd` //
CREATE TRIGGER `tr_tmm_drivertreenodem_upd` BEFORE UPDATE ON `tmm_drivertreenodem`
FOR EACH ROW BEGIN SET NEW.mod_dtm = NOW(); END //

DROP TRIGGER IF EXISTS `tr_tmm_priceforecastm_upd` //
CREATE TRIGGER `tr_tmm_priceforecastm_upd` BEFORE UPDATE ON `tmm_priceforecastm`
FOR EACH ROW BEGIN SET NEW.mod_dtm = NOW(); END //

DROP TRIGGER IF EXISTS `tr_tmd_drivertreem_upd` //
CREATE TRIGGER `tr_tmd_drivertreem_upd` BEFORE UPDATE ON `tmd_drivertreem`
FOR EACH ROW BEGIN SET NEW.mod_dtm = NOW(); END //

DELIMITER ;