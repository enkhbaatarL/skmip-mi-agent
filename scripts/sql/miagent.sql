-- =========================================================
-- MI Agent ERD MySQL DDL
-- =========================================================

-- =========================================================
-- Table: tmm_mieventm
-- =========================================================
DROP TABLE IF EXISTS `tmm_mieventm`;
CREATE TABLE `tmm_mieventm` (
    `mi_event_id`             INT UNSIGNED AUTO_INCREMENT COMMENT 'MI Event 일련번호 (PK)',
    `first_created`           DATETIME NOT NULL COMMENT 'Event 최초생성일시',
    `crt_usr_logn_id`         VARCHAR(50) DEFAULT 'SYSTEM' NOT NULL COMMENT '생성사용자로그인ID',
    `crt_dtm`                 DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL COMMENT '생성일시',
    `mod_usr_logn_id`         VARCHAR(50) DEFAULT 'SYSTEM' NOT NULL COMMENT '수정사용자로그인ID',
    `mod_dtm`                 DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL COMMENT '수정일시',
    `del_yn`                  CHAR(1) DEFAULT 'N' NOT NULL COMMENT '삭제여부',

    `event_title_ko`          VARCHAR(500) NOT NULL COMMENT '이벤트 제목 (한국어)',
    `one_line_summary`        VARCHAR(200) NOT NULL COMMENT '1줄 요약 [토픽] 에피소드 → 영향',
    `detail_analysis`         TEXT COMMENT '상세 분석 내용',
    `market_and_institution_view` TEXT COMMENT '시장 반응 및 기관 전망',

    `language`                VARCHAR(10) DEFAULT 'ko' COMMENT '문서 언어',
    `occurred_at`             DATETIME COMMENT '이벤트 실제 발생일시',
    `probability`             DECIMAL(3,2) COMMENT '이벤트 발생 확률 0.00 ~ 1.00',
    `dedup_state`             VARCHAR(30) COMMENT '중복처리 상태 (canonical, duplicate, merged)',

    `level_1_code`            VARCHAR(100) COMMENT '이벤트 유형 레벨1 코드',
    `level_2_code`            VARCHAR(100) COMMENT '이벤트 유형 레벨2 코드',
    `taxonomy_version`        VARCHAR(30) COMMENT '분류체계 버전',

    `status_code`             VARCHAR(30) COMMENT '이벤트 상태 코드',
    `status_label_ko`         VARCHAR(100) COMMENT '이벤트 상태 라벨 (한국어)',
    `status_taxonomy_version` VARCHAR(30) COMMENT '상태 분류체계 버전',

    PRIMARY KEY (`mi_event_id`, `first_created`),
    INDEX `tmm_mieventm_ix01` (`occurred_at`),
    INDEX `tmm_mieventm_ix02` (`level_1_code`),
    INDEX `tmm_mieventm_ix03` (`level_2_code`),
    INDEX `tmm_mieventm_ix04` (`status_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='MI Event 단위 (뉴스/리포트로부터 추출된 시장 사건)';


-- =========================================================
-- Table: tmd_mievent_source_mapm
-- =========================================================
DROP TABLE IF EXISTS `tmd_mievent_source_mapm`;
CREATE TABLE `tmd_mievent_source_mapm` (
    `map_id`                  INT UNSIGNED AUTO_INCREMENT COMMENT '매핑 일련번호',
    `mi_event_id`             INT UNSIGNED NOT NULL COMMENT 'MI Event ID (FK)',
    `mi_record_id`            INT UNSIGNED NOT NULL COMMENT '소스 MI Record ID (FK)',
    `crt_dtm`                 DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL COMMENT '생성일시',

    PRIMARY KEY (`map_id`),
    UNIQUE KEY `tmd_mievent_source_mapm_uk01` (`mi_event_id`, `mi_record_id`),
    INDEX `tmd_mievent_source_mapm_ix01` (`mi_event_id`),
    INDEX `tmd_mievent_source_mapm_ix02` (`mi_record_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='MI Event ↔ MI Record 소스 매핑';

-- =========================================================
-- Table: tmd_mievent_key_bulletsm
-- =========================================================
DROP TABLE IF EXISTS `tmd_mievent_key_bulletsm`;
CREATE TABLE `tmd_mievent_key_bulletsm` (
    `bullet_id`               INT UNSIGNED AUTO_INCREMENT COMMENT '키 불릿 일련번호',
    `mi_event_id`             INT UNSIGNED NOT NULL COMMENT 'MI Event ID (FK)',
    `bullet_order`            SMALLINT UNSIGNED NOT NULL COMMENT '표시 순서',
    `bullet_text`             VARCHAR(500) NOT NULL COMMENT '불릿 내용',
    `category_type`           CHAR(1) COMMENT '분류 유형 (A:사건상태, B:실물수급, C:가격영향)',

    PRIMARY KEY (`bullet_id`),
    INDEX `tmd_mievent_key_bulletsm_ix01` (`mi_event_id`),
    UNIQUE KEY `tmd_mievent_key_bulletsm_uk01` (`mi_event_id`, `bullet_order`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='MI Event Key Bullet 항목';

-- =========================================================
-- Table: tmm_impactm
-- =========================================================
DROP TABLE IF EXISTS `tmm_impactm`;
CREATE TABLE `tmm_impactm` (
  `impact_id`             VARCHAR(64)     NOT NULL COMMENT 'Impact ID PK impact_ev_[a-z0-9_]+',
  `crt_user_id`           VARCHAR(50)     NOT NULL DEFAULT 'SYSTEM' COMMENT '생성 사용자 ID',
  `crt_dtm`               DATETIME        NOT NULL DEFAULT NOW() COMMENT '생성 일시',
  `mod_user_id`           VARCHAR(50)     NOT NULL DEFAULT 'SYSTEM' COMMENT '수정 사용자 ID',
  `mod_dtm`               DATETIME        NOT NULL DEFAULT NOW() COMMENT '수정 일시',
  `del_yn`                CHAR(1)         NOT NULL DEFAULT 'N' COMMENT '삭제 여부 Y/N',
  `mi_event_id`           INT UNSIGNED    NOT NULL COMMENT 'MI Event ID FK',
  `updated_at`            DATETIME        NULL COMMENT '업데이트 일시 ISO-8601',
  PRIMARY KEY (`impact_id`),
  INDEX `tmm_impactm_ix01` (`mi_event_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Impact Master';

-- =========================================================
-- Table: tmm_impactresultm
-- =========================================================
DROP TABLE IF EXISTS `tmm_impactresultm`;
CREATE TABLE `tmm_impactresultm` (
  `impact_result_id`      VARCHAR(64)     NOT NULL COMMENT 'Impact Result ID PK',
  `crt_user_id`           VARCHAR(50)     NOT NULL DEFAULT 'SYSTEM' COMMENT '생성 사용자 ID',
  `crt_dtm`               DATETIME        NOT NULL DEFAULT NOW() COMMENT '생성 일시',
  `mod_user_id`           VARCHAR(50)     NOT NULL DEFAULT 'SYSTEM' COMMENT '수정 사용자 ID',
  `mod_dtm`               DATETIME        NOT NULL DEFAULT NOW() COMMENT '수정 일시',
  `del_yn`                CHAR(1)         NOT NULL DEFAULT 'N' COMMENT '삭제 여부 Y/N',
  `impact_id`             VARCHAR(64)     NOT NULL COMMENT 'Impact ID FK impact_ev_*',
  `target_type`           VARCHAR(20)     NOT NULL COMMENT '대상 유형 price|spread',
  `target_id`             VARCHAR(20)     NOT NULL COMMENT '대상 ID JKM|TTF|HH|JKM-HH',
  `direction`             VARCHAR(20)     NULL COMMENT '방향 bullish|bearish|negligible',
  `confidence`            DECIMAL(5,4)    NULL COMMENT '신뢰도 0~1',
  `impact_assessment_reason` TEXT         NULL COMMENT '임팩트 평가 사유',
  `completed`             CHAR(1)         NOT NULL DEFAULT 'N' COMMENT '분석 완료 여부 Y/N',
  `analysis_time`         DATETIME        NULL COMMENT '분석 완료 일시 ISO-8601',
  PRIMARY KEY (`impact_result_id`),
  INDEX `tmm_impactresultm_ix01` (`impact_id`),
  INDEX `tmm_impactresultm_ix02` (`target_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Impact Result Master';

-- =========================================================
-- Table: tmm_drivertagm
-- =========================================================
DROP TABLE IF EXISTS `tmm_drivertagm`;
CREATE TABLE `tmm_drivertagm` (
  `driver_id`             VARCHAR(64)     NOT NULL COMMENT 'Driver Tag ID PK',
  `crt_user_id`           VARCHAR(50)     NOT NULL DEFAULT 'SYSTEM' COMMENT '생성 사용자 ID',
  `crt_dtm`               DATETIME        NOT NULL DEFAULT NOW() COMMENT '생성 일시',
  `mod_user_id`           VARCHAR(50)     NOT NULL DEFAULT 'SYSTEM' COMMENT '수정 사용자 ID',
  `mod_dtm`               DATETIME        NOT NULL DEFAULT NOW() COMMENT '수정 일시',
  `del_yn`                CHAR(1)         NOT NULL DEFAULT 'N' COMMENT '삭제 여부 Y/N',
  `impact_result_id`      VARCHAR(64)     NOT NULL COMMENT 'Impact Result ID FK',
  `lv1_id`                VARCHAR(50)     NOT NULL COMMENT 'Driver Tree 1단계 코드',
  `lv1_label`             VARCHAR(100)    NULL COMMENT 'Driver Tree 1단계 명칭',
  `lv2_id`                VARCHAR(50)     NOT NULL COMMENT 'Driver Tree 2단계 코드',
  `lv2_label`             VARCHAR(100)    NULL COMMENT 'Driver Tree 2단계 명칭',
  `lv3_id`                VARCHAR(50)     NOT NULL COMMENT 'Driver Tree 3단계 코드',
  `lv3_label`             VARCHAR(100)    NULL COMMENT 'Driver Tree 3단계 명칭',
  `direction_hint`        VARCHAR(50)     NULL COMMENT '방향 힌트 bullish_if_up/bearish_if_up/contextual',
  `direction`             VARCHAR(20)     NULL COMMENT '실제 영향 방향 bullish/bearish/negligible',
  `match_score`           DECIMAL(5,4)    NULL COMMENT 'Event-Driver 매핑 신뢰도 점수 0~1',
  `driver_magnitude`      VARCHAR(20)     NULL COMMENT 'Driver 영향 강도 low/medium/high/extreme',
  `driver_reason`         TEXT            NULL COMMENT 'Driver 영향 발생 사유',
  `matched_keywords`      JSON            NULL COMMENT '매칭된 키워드 목록',
  PRIMARY KEY (`driver_id`),
  INDEX `tmm_drivertagm_ix01` (`impact_result_id`),
  INDEX `tmm_drivertagm_ix02` (`lv3_id`)
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
  `scenario_id`           INT             NOT NULL AUTO_INCREMENT COMMENT '시나리오 ID PK',
  `crt_user_id`           VARCHAR(50)     NOT NULL DEFAULT 'SYSTEM' COMMENT '생성 사용자 ID',
  `crt_dtm`               DATETIME        NOT NULL DEFAULT NOW() COMMENT '생성 일시',
  `mod_user_id`           VARCHAR(50)     NOT NULL DEFAULT 'SYSTEM' COMMENT '수정 사용자 ID',
  `mod_dtm`               DATETIME        NOT NULL DEFAULT NOW() COMMENT '수정 일시',
  `del_yn`                CHAR(1)         NOT NULL DEFAULT 'N' COMMENT '삭제 여부 Y/N',
  `user_id`               INT             NULL COMMENT '시나리오 생성 사용자 ID',
  `name`                  VARCHAR(200)    NOT NULL COMMENT '시나리오 명칭',
  `description`           TEXT            NULL COMMENT '시나리오 설명',
  `status`                VARCHAR(20)     NOT NULL DEFAULT 'draft' COMMENT '시나리오 상태 draft/active/archived',
  `valid_from`            DATETIME        NULL COMMENT '유효기간 시작 일시',
  `valid_to`              DATETIME        NULL COMMENT '유효기간 종료 일시',
  `base_event_context`    TEXT            NULL COMMENT '기본 이벤트 컨텍스트',
  PRIMARY KEY (`scenario_id`),
  INDEX `tmm_scenariom_ix01` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Scenario Master';

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
DROP TABLE IF EXISTS `tmd_drivertreem`;
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

DROP TRIGGER IF EXISTS `tr_tmm_mieventm_upd` //
CREATE TRIGGER `tr_tmm_mieventm_upd` BEFORE UPDATE ON `tmm_mieventm`
FOR EACH ROW BEGIN SET NEW.mod_dtm = NOW(); END //

DROP TRIGGER IF EXISTS `tr_tmm_impactm_upd` //
CREATE TRIGGER `tr_tmm_impactm_upd` BEFORE UPDATE ON `tmm_impactm`
FOR EACH ROW BEGIN SET NEW.mod_dtm = NOW(); END //

DROP TRIGGER IF EXISTS `tr_tmm_impactresultm_upd` //
CREATE TRIGGER `tr_tmm_impactresultm_upd` BEFORE UPDATE ON `tmm_impactresultm`
FOR EACH ROW BEGIN SET NEW.mod_dtm = NOW(); END //

DROP TRIGGER IF EXISTS `tr_tmm_qualimpactm_upd` //
CREATE TRIGGER `tr_tmm_qualimpactm_upd` BEFORE UPDATE ON `tmm_qualimpactm`
FOR EACH ROW BEGIN SET NEW.mod_dtm = NOW(); END //

DROP TRIGGER IF EXISTS `tr_tmm_quantimpactm_upd` //
CREATE TRIGGER `tr_tmm_quantimpactm_upd` BEFORE UPDATE ON `tmm_quantimpactm`
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
