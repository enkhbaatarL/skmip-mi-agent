from __future__ import annotations

# Copyright (c) 2026 SK Innovation E&S.
# ruff: noqa: S608 -- this script renders a fixed, reviewable SQL artifact from canonical JSON.
from collections.abc import Iterable, Mapping
from datetime import date, datetime
import json
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[2]
MODEL_PARAMETER_CANONICAL_PATH = ROOT_DIR / "scripts/model_parameter/model-parameter-canonical-v4.json"
IMPACT_LEVER_CANONICAL_PATH = ROOT_DIR / "scripts/model_parameter/model-impact-lever-canonical-v4.json"
SNAPSHOT_PATH = ROOT_DIR / "scripts/model_parameter/snapshots/external_dev_before_model_parameter_v4_20260813.json"
OUTPUT_PATH = ROOT_DIR / "scripts/model_parameter/apply_model_parameter_canonical_v4.sql"

MASTER_VALUE_COLUMNS = (
    "model_param_id",
    "use_yn",
    "parameter_name",
    "parameter_hint",
    "model_file",
    "model_sheet",
    "model_table",
    "semantic_axes",
    "basecase_read_mode",
    "basecase_header_row",
    "basecase_data_start_row",
    "basecase_column_roles",
    "basecase_row_filter",
    "basecase_year_row",
    "basecase_month_row",
    "basecase_period_row",
    "basecase_value_start_col",
    "basecase_value_end_col",
    "basecase_stop_rule",
    "mod_usr_logn_id",
    "del_yn",
)
MASTER_CREATION_COLUMNS = (
    "model_param_id",
    "crt_usr_logn_id",
    "crt_dtm",
)
MAPPING_VALUE_COLUMNS = (
    "model_param_dimension_map_id",
    "use_yn",
    "event_type_l2_id",
    "dimension_key",
    "dimension_label",
    "mapping_method",
    "model_param_id",
    "comment",
    "crt_usr_logn_id",
    "crt_dtm",
    "mod_usr_logn_id",
    "mod_dtm",
    "del_yn",
)
IMPACT_VALUE_COLUMNS = (
    "impact_lever_id",
    "lever_code",
    "domain",
    "label",
    "description",
    "applicability_hint",
    "parent_lever_code",
    "parameter_bindings",
    "catalog_version",
    "use_yn",
    "mod_usr_logn_id",
    "del_yn",
)
IMPACT_CREATION_COLUMNS = (
    "impact_lever_id",
    "lever_code",
    "crt_usr_logn_id",
    "crt_dtm",
)


def _load_json(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        message = f"JSON root must be an object: {path}"
        raise TypeError(message)
    return document


def _sql_literal(value: Any) -> str:  # noqa: ANN401
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, int | float):
        return str(value)
    if isinstance(value, date | datetime):
        value = value.isoformat(sep=" ")
    if isinstance(value, list | dict):
        value = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    text = str(value).replace("'", "''")
    return f"'{text}'"


def _values_sql(rows: Iterable[Mapping[str, Any]], columns: tuple[str, ...]) -> str:
    return ",\n".join(
        "        (" + ", ".join(_sql_literal(row.get(column)) for column in columns) + ")" for row in rows
    )


def _null_safe_clause(
    left_alias: str,
    right_alias: str,
    columns: Iterable[str],
) -> str:
    return " AND ".join(f"{left_alias}.`{column}` <=> {right_alias}.`{column}`" for column in columns)


def _render_sql(
    model_parameter: Mapping[str, Any],
    impact_lever: Mapping[str, Any],
    snapshot: Mapping[str, Any],
) -> str:
    canonical_master = model_parameter["master"]
    canonical_levers = impact_lever["impact_levers"]
    snapshot_master = snapshot["master"]
    snapshot_mappings = snapshot["dimension_mappings"]
    snapshot_levers = snapshot["impact_levers"]
    active_names = sorted(model_parameter["active_parameter_names"])
    active_name_sql = ", ".join(_sql_literal(name) for name in active_names)
    canonical_checksum = str(impact_lever["hydrated_catalog_checksum"])
    master_compare_columns = tuple(column for column in MASTER_VALUE_COLUMNS if column != "model_param_id")
    impact_compare_columns = tuple(
        column for column in IMPACT_VALUE_COLUMNS if column not in {"impact_lever_id", "lever_code"}
    )
    mapping_compare_columns = tuple(
        column for column in MAPPING_VALUE_COLUMNS if column != "model_param_dimension_map_id"
    )
    mapping_count = len(snapshot_mappings)
    return f"""-- Copyright (c) 2026 SK Innovation E&S.
-- Canonical versions: model-parameter-canonical-v4 + model-impact-lever-canonical-v4
-- Source evidence: snapshots/external_dev_before_model_parameter_v4_20260813.json
--
-- This MySQL 8.0 procedure updates the 21-row Model Parameter master and the
-- 16-row Impact Lever catalog in one transaction. The {mapping_count}-row AS-IS
-- legacy dimension mapping is locked and verified exactly but is never updated.

DELIMITER //

DROP PROCEDURE IF EXISTS apply_model_parameter_canonical_v4//
CREATE PROCEDURE apply_model_parameter_canonical_v4()
BEGIN
    DECLARE v_bad BIGINT DEFAULT 0;
    DECLARE v_count BIGINT DEFAULT 0;
    DECLARE v_checksum CHAR(64) DEFAULT NULL;
    DECLARE v_expected_checksum CHAR(64) DEFAULT NULL;

    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        DROP TEMPORARY TABLE IF EXISTS _mpv4_snapshot_master;
        DROP TEMPORARY TABLE IF EXISTS _mpv4_canonical_master;
        DROP TEMPORARY TABLE IF EXISTS _mpv4_snapshot_mapping;
        DROP TEMPORARY TABLE IF EXISTS _mpv4_snapshot_lever;
        DROP TEMPORARY TABLE IF EXISTS _mpv4_canonical_lever;
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
       FOR SHARE;

    SELECT impact_lever_id
      FROM tmm_mi_model_impact_lever_m
     ORDER BY impact_lever_id
       FOR UPDATE;

    SELECT scenario_dimension_template_id
      FROM tmm_mi_scenario_dimension_template_m
     ORDER BY scenario_dimension_template_id
       FOR SHARE;

    CREATE TEMPORARY TABLE _mpv4_snapshot_master AS
    SELECT {", ".join(f"`{column}`" for column in (*MASTER_VALUE_COLUMNS, *MASTER_CREATION_COLUMNS[1:]))}
      FROM tmm_mi_model_param_m
     WHERE 1 = 0;

    INSERT INTO _mpv4_snapshot_master (
        {", ".join(f"`{column}`" for column in (*MASTER_VALUE_COLUMNS, *MASTER_CREATION_COLUMNS[1:]))}
    ) VALUES
{_values_sql(snapshot_master, (*MASTER_VALUE_COLUMNS, *MASTER_CREATION_COLUMNS[1:]))};

    CREATE TEMPORARY TABLE _mpv4_canonical_master AS
    SELECT * FROM _mpv4_snapshot_master WHERE 1 = 0;

    INSERT INTO _mpv4_canonical_master (
        {", ".join(f"`{column}`" for column in (*MASTER_VALUE_COLUMNS, *MASTER_CREATION_COLUMNS[1:]))}
    ) VALUES
{_values_sql(canonical_master, (*MASTER_VALUE_COLUMNS, *MASTER_CREATION_COLUMNS[1:]))};

    CREATE TEMPORARY TABLE _mpv4_snapshot_mapping AS
    SELECT {", ".join(f"`{column}`" for column in MAPPING_VALUE_COLUMNS)}
      FROM tmm_mi_model_param_dimension_map
     WHERE 1 = 0;

    INSERT INTO _mpv4_snapshot_mapping (
        {", ".join(f"`{column}`" for column in MAPPING_VALUE_COLUMNS)}
    ) VALUES
{_values_sql(snapshot_mappings, MAPPING_VALUE_COLUMNS)};

    CREATE TEMPORARY TABLE _mpv4_snapshot_lever AS
    SELECT {", ".join(f"`{column}`" for column in (*IMPACT_VALUE_COLUMNS, *IMPACT_CREATION_COLUMNS[2:]))}
      FROM tmm_mi_model_impact_lever_m
     WHERE 1 = 0;

    INSERT INTO _mpv4_snapshot_lever (
        {", ".join(f"`{column}`" for column in (*IMPACT_VALUE_COLUMNS, *IMPACT_CREATION_COLUMNS[2:]))}
    ) VALUES
{_values_sql(snapshot_levers, (*IMPACT_VALUE_COLUMNS, *IMPACT_CREATION_COLUMNS[2:]))};

    CREATE TEMPORARY TABLE _mpv4_canonical_lever AS
    SELECT * FROM _mpv4_snapshot_lever WHERE 1 = 0;

    INSERT INTO _mpv4_canonical_lever (
        {", ".join(f"`{column}`" for column in (*IMPACT_VALUE_COLUMNS, *IMPACT_CREATION_COLUMNS[2:]))}
    ) VALUES
{_values_sql(canonical_levers, (*IMPACT_VALUE_COLUMNS, *IMPACT_CREATION_COLUMNS[2:]))};

    SELECT COUNT(*) INTO v_count FROM tmm_mi_model_param_m;
    IF v_count <> 21 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'master precondition: expected 21 rows';
    END IF;

    SELECT COUNT(*) INTO v_bad
      FROM tmm_mi_model_param_m AS live
      LEFT JOIN _mpv4_snapshot_master AS old USING (model_param_id)
      LEFT JOIN _mpv4_canonical_master AS final USING (model_param_id)
     WHERE old.model_param_id IS NULL OR final.model_param_id IS NULL
        OR NOT ({_null_safe_clause("live", "old", MASTER_CREATION_COLUMNS[1:])})
        OR NOT (
            ({_null_safe_clause("live", "old", master_compare_columns)})
            OR ({_null_safe_clause("live", "final", master_compare_columns)})
        );
    IF v_bad <> 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'master precondition: row is neither pre-v4 nor canonical-v4';
    END IF;

    SELECT COUNT(*) INTO v_count FROM tmm_mi_model_param_dimension_map;
    IF v_count <> {mapping_count} THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'mapping precondition: AS-IS row count changed';
    END IF;

    SELECT COUNT(*) INTO v_bad
      FROM tmm_mi_model_param_dimension_map AS live
      LEFT JOIN _mpv4_snapshot_mapping AS old
        ON live.model_param_dimension_map_id = old.model_param_dimension_map_id
     WHERE old.model_param_dimension_map_id IS NULL
        OR NOT ({_null_safe_clause("live", "old", mapping_compare_columns)});
    IF v_bad <> 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'mapping precondition: AS-IS legacy mapping changed';
    END IF;

    SELECT COUNT(*) INTO v_count FROM tmm_mi_model_impact_lever_m;
    IF v_count <> 16 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Impact Lever precondition: expected 16 rows';
    END IF;

    SELECT COUNT(*) INTO v_bad
      FROM tmm_mi_model_impact_lever_m AS live
      LEFT JOIN _mpv4_snapshot_lever AS old USING (impact_lever_id, lever_code)
      LEFT JOIN _mpv4_canonical_lever AS final USING (impact_lever_id, lever_code)
     WHERE old.impact_lever_id IS NULL OR final.impact_lever_id IS NULL
        OR NOT ({_null_safe_clause("live", "old", IMPACT_CREATION_COLUMNS[2:])})
        OR NOT (
            ({_null_safe_clause("live", "old", impact_compare_columns)})
            OR ({_null_safe_clause("live", "final", impact_compare_columns)})
        );
    IF v_bad <> 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Impact Lever precondition: row is neither pre-v4 nor canonical-v4';
    END IF;

    UPDATE tmm_mi_model_param_m AS live
    JOIN _mpv4_canonical_master AS final USING (model_param_id)
       SET live.use_yn = final.use_yn,
           live.parameter_name = final.parameter_name,
           live.parameter_hint = final.parameter_hint,
           live.model_file = final.model_file,
           live.model_sheet = final.model_sheet,
           live.model_table = final.model_table,
           live.semantic_axes = final.semantic_axes,
           live.basecase_read_mode = final.basecase_read_mode,
           live.basecase_header_row = final.basecase_header_row,
           live.basecase_data_start_row = final.basecase_data_start_row,
           live.basecase_column_roles = final.basecase_column_roles,
           live.basecase_row_filter = final.basecase_row_filter,
           live.basecase_year_row = final.basecase_year_row,
           live.basecase_month_row = final.basecase_month_row,
           live.basecase_period_row = final.basecase_period_row,
           live.basecase_value_start_col = final.basecase_value_start_col,
           live.basecase_value_end_col = final.basecase_value_end_col,
           live.basecase_stop_rule = final.basecase_stop_rule,
           live.mod_usr_logn_id = final.mod_usr_logn_id,
           live.mod_dtm = CURRENT_TIMESTAMP(6),
           live.del_yn = final.del_yn;

    UPDATE tmm_mi_model_impact_lever_m AS live
    JOIN _mpv4_canonical_lever AS final USING (impact_lever_id, lever_code)
       SET live.domain = final.domain,
           live.label = final.label,
           live.description = final.description,
           live.applicability_hint = final.applicability_hint,
           live.parent_lever_code = final.parent_lever_code,
           live.parameter_bindings = final.parameter_bindings,
           live.catalog_version = final.catalog_version,
           live.use_yn = final.use_yn,
           live.mod_usr_logn_id = final.mod_usr_logn_id,
           live.mod_dtm = CURRENT_TIMESTAMP(6),
           live.del_yn = final.del_yn;

    SELECT COUNT(*) INTO v_bad
      FROM tmm_mi_model_param_m AS live
      JOIN _mpv4_canonical_master AS final USING (model_param_id)
     WHERE NOT ({_null_safe_clause("live", "final", master_compare_columns)});
    IF v_bad <> 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'read-back: master canonical-v4 values mismatch';
    END IF;

    SELECT COUNT(*) INTO v_bad
      FROM tmm_mi_model_impact_lever_m AS live
      JOIN _mpv4_canonical_lever AS final USING (impact_lever_id, lever_code)
     WHERE NOT ({_null_safe_clause("live", "final", impact_compare_columns)});
    IF v_bad <> 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'read-back: Impact Lever canonical-v4 values mismatch';
    END IF;

    SELECT COUNT(*) INTO v_bad
      FROM tmm_mi_model_param_dimension_map AS live
      LEFT JOIN _mpv4_snapshot_mapping AS old USING (model_param_dimension_map_id)
     WHERE old.model_param_dimension_map_id IS NULL
        OR NOT ({_null_safe_clause("live", "old", mapping_compare_columns)});
    IF v_bad <> 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'read-back: AS-IS legacy mapping changed';
    END IF;

    SELECT COUNT(*) INTO v_count
      FROM tmm_mi_model_param_m
     WHERE use_yn = 'Y' AND del_yn = 'N';
    IF v_count <> 16 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'invariant: expected exactly 16 active parameters';
    END IF;

    SELECT COUNT(*) INTO v_bad
      FROM tmm_mi_model_param_m
     WHERE (use_yn = 'Y' AND del_yn = 'N')
       <> (parameter_name IN ({active_name_sql}));
    IF v_bad <> 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'invariant: active parameter name set mismatch';
    END IF;

    SELECT COUNT(*) INTO v_bad
      FROM tmm_mi_model_param_dimension_map AS d
      LEFT JOIN tmm_mi_model_param_m AS m ON m.model_param_id = d.model_param_id
     WHERE d.use_yn <> 'Y' OR d.del_yn <> 'N'
        OR (d.model_param_id IS NOT NULL
            AND (m.model_param_id IS NULL OR m.use_yn <> 'Y' OR m.del_yn <> 'N'))
        OR (d.mapping_method IN ('direct', 'routing') AND d.model_param_id IS NULL);
    IF v_bad <> 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'invariant: invalid legacy mapping reference/state';
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

    SELECT COUNT(*) INTO v_bad
      FROM tmm_mi_model_impact_lever_m
     WHERE catalog_version <> 'v4' OR use_yn <> 'Y' OR del_yn <> 'N'
        OR domain NOT IN ('demand', 'supply', 'trade', 'price_only')
        OR JSON_TYPE(parameter_bindings) <> 'ARRAY';
    IF v_bad <> 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'invariant: invalid Impact Lever v4 row';
    END IF;

    SELECT COUNT(*) INTO v_count
      FROM tmm_mi_model_impact_lever_m AS lever
      JOIN JSON_TABLE(
            lever.parameter_bindings,
            '$[*]' COLUMNS (
                parameter_name VARCHAR(150) PATH '$.parameter_name',
                binding_role VARCHAR(30) PATH '$.role',
                applicability TEXT PATH '$.applicability',
                support_status VARCHAR(30) PATH '$.support_status'
            )
           ) AS binding;
    IF v_count <> 20 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'invariant: expected 20 raw binding occurrences';
    END IF;

    SELECT COUNT(*) INTO v_bad
      FROM tmm_mi_model_impact_lever_m AS lever
      JOIN JSON_TABLE(
            lever.parameter_bindings,
            '$[*]' COLUMNS (
                parameter_name VARCHAR(150) PATH '$.parameter_name',
                binding_role VARCHAR(30) PATH '$.role',
                applicability TEXT PATH '$.applicability',
                support_status VARCHAR(30) PATH '$.support_status'
            )
           ) AS binding
      LEFT JOIN tmm_mi_model_param_m AS parameter_master
        ON parameter_master.parameter_name = binding.parameter_name
     WHERE parameter_master.model_param_id IS NULL
        OR parameter_master.del_yn <> 'N'
        OR binding.binding_role NOT IN ('primary', 'alternative')
        OR binding.applicability IS NULL OR TRIM(binding.applicability) = ''
        OR binding.support_status <> 'executable';
    IF v_bad <> 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'invariant: invalid Impact Lever binding';
    END IF;

    SELECT COUNT(*) INTO v_count
      FROM tmm_mi_model_impact_lever_m AS lever
      JOIN JSON_TABLE(
            lever.parameter_bindings,
            '$[*]' COLUMNS (parameter_name VARCHAR(150) PATH '$.parameter_name')
           ) AS binding
      JOIN tmm_mi_model_param_m AS parameter_master
        ON parameter_master.parameter_name = binding.parameter_name
       AND parameter_master.use_yn = 'Y'
       AND parameter_master.del_yn = 'N';
    IF v_count <> 18 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'invariant: expected 18 effective executable bindings';
    END IF;

    SELECT COUNT(DISTINCT binding.parameter_name) INTO v_count
      FROM tmm_mi_model_impact_lever_m AS lever
      JOIN JSON_TABLE(
            lever.parameter_bindings,
            '$[*]' COLUMNS (parameter_name VARCHAR(150) PATH '$.parameter_name')
           ) AS binding
      JOIN tmm_mi_model_param_m AS parameter_master
        ON parameter_master.parameter_name = binding.parameter_name
       AND parameter_master.use_yn = 'Y'
       AND parameter_master.del_yn = 'N';
    IF v_count <> 16 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'invariant: expected 16 unique executable parameters';
    END IF;

    SELECT COUNT(*) INTO v_count
      FROM tmm_mi_model_impact_lever_m AS lever
      JOIN JSON_TABLE(
            lever.parameter_bindings,
            '$[*]' COLUMNS (parameter_name VARCHAR(150) PATH '$.parameter_name')
           ) AS binding
      JOIN tmm_mi_model_param_m AS parameter_master
        ON parameter_master.parameter_name = binding.parameter_name
       AND parameter_master.use_yn = 'N'
       AND parameter_master.del_yn = 'N';
    IF v_count <> 2 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'invariant: expected two inactive capability bindings';
    END IF;

    SELECT SHA2(
               GROUP_CONCAT(
                   SHA2(CAST(JSON_OBJECT(
                       'applicability_hint', lever.applicability_hint,
                       'catalog_version', lever.catalog_version,
                       'description', lever.description,
                       'domain', lever.domain,
                       'label', lever.label,
                       'lever_code', lever.lever_code,
                       'parameter_bindings', JSON_EXTRACT(lever.parameter_bindings, '$'),
                       'parent_lever_code', lever.parent_lever_code
                   ) AS CHAR), 256)
                   ORDER BY lever.domain, lever.lever_code SEPARATOR ''
               ),
               256
           )
      INTO v_checksum
      FROM tmm_mi_model_impact_lever_m AS lever;

    SELECT SHA2(
               GROUP_CONCAT(
                   SHA2(CAST(JSON_OBJECT(
                       'applicability_hint', lever.applicability_hint,
                       'catalog_version', lever.catalog_version,
                       'description', lever.description,
                       'domain', lever.domain,
                       'label', lever.label,
                       'lever_code', lever.lever_code,
                       'parameter_bindings', JSON_EXTRACT(lever.parameter_bindings, '$'),
                       'parent_lever_code', lever.parent_lever_code
                   ) AS CHAR), 256)
                   ORDER BY lever.domain, lever.lever_code SEPARATOR ''
               ),
               256
           )
      INTO v_expected_checksum
      FROM _mpv4_canonical_lever AS lever;
    -- The Python runner verifies the exact hydrated service checksum
    -- {canonical_checksum}; this SQL additionally verifies the canonical rows
    -- through exact read-back and all binding invariants above.
    IF v_checksum IS NULL OR v_expected_checksum IS NULL OR v_checksum <> v_expected_checksum THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'invariant: Impact Lever read-back checksum mismatch';
    END IF;

    COMMIT;
    DROP TEMPORARY TABLE IF EXISTS _mpv4_snapshot_master;
    DROP TEMPORARY TABLE IF EXISTS _mpv4_canonical_master;
    DROP TEMPORARY TABLE IF EXISTS _mpv4_snapshot_mapping;
    DROP TEMPORARY TABLE IF EXISTS _mpv4_snapshot_lever;
    DROP TEMPORARY TABLE IF EXISTS _mpv4_canonical_lever;
END//

CALL apply_model_parameter_canonical_v4()//
DROP PROCEDURE apply_model_parameter_canonical_v4//

DELIMITER ;
"""


def main() -> int:
    model_parameter = _load_json(MODEL_PARAMETER_CANONICAL_PATH)
    impact_lever = _load_json(IMPACT_LEVER_CANONICAL_PATH)
    snapshot = _load_json(SNAPSHOT_PATH)
    OUTPUT_PATH.write_text(
        _render_sql(model_parameter, impact_lever, snapshot),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
