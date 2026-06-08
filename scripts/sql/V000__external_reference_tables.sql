-- =========================================================
-- External Reference Tables Bootstrap
-- =========================================================
-- This migration prepares minimal external dependency tables
-- that are referenced by MI domain foreign keys.
-- In production, these tables are owned by external domains.

CREATE TABLE IF NOT EXISTS `tmd_mi_record` (
    `mi_record_id` INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT 'MI Record 일련번호',
    `first_created` DATETIME NOT NULL COMMENT 'Record 최초생성일시',
    `crt_usr_logn_id` VARCHAR(50) COLLATE utf8mb4_bin NOT NULL DEFAULT 'SYSTEM' COMMENT '생성사용자로그인ID',
    `crt_dtm` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '생성일시',
    `mod_usr_logn_id` VARCHAR(50) COLLATE utf8mb4_bin NOT NULL DEFAULT 'SYSTEM' COMMENT '수정사용자로그인ID',
    `mod_dtm` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '수정일시',
    `del_yn` CHAR(1) COLLATE utf8mb4_bin NOT NULL DEFAULT 'N' COMMENT '삭제여부',
    `record_type` VARCHAR(20) COLLATE utf8mb4_bin NOT NULL COMMENT '데이터 유형 -NEWS, REPORT, EMAIL',
    `source_obj_id` INT UNSIGNED NOT NULL COMMENT '데이터 소스 ID',
    `ref_nm` VARCHAR(50) COLLATE utf8mb4_bin NULL COMMENT '데이터 소스 출처이름',
    PRIMARY KEY (`mi_record_id`, `first_created`),
    UNIQUE KEY `uk_tmd_mi_record_01` (`record_type`, `source_obj_id`),
    UNIQUE KEY `uk_tmd_mi_record_02` (`mi_record_id`)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_bin
  COMMENT='외부 데이터로부터 수집된 MI Record 단위 (뉴스, 리포트, 이메일)';
