"""모델 실행 결과(예측 가격) read-only 조회 repository.

대상 테이블(`tmd_mdl_scnrcasem`, `tmd_mdl_scnrcaseh`, `tmd_mdl_scnrcaseprcl`)은
이 repo/mgmt repo 어디에도 ORM/관리 대상이 아니다. 스타트업 스키마 검증
(`APPLICATION_TABLES`)에 얽매이지 않도록 ORM 모델 없이 `text()` raw SQL 로만
읽는다(읽기 전용, 스키마 변경 없음). 가격 결과는 항상 monthly(`perd_unit_spt_cd='M'`)
이며, 지수 → `prc_rgn_nm` 매핑은 호출 측(`INDEX_PRICE_REGION`)이 결정한다.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import text

from apps.common.configs.database.sync_database.base import BaseSyncSQLRepository


# MI Base(최신 완료 MI_BASE case)의 base_case_prc 시계열.
_MI_BASE_PRICE_SQL = text(
    """
    SELECT p.perd_key AS period_key,
           p.base_case_prc AS value
    FROM tmd_mdl_scnrcasem c
    JOIN tmd_mdl_scnrcaseh h ON h.run_id = c.last_run_id
    JOIN tmd_mdl_scnrcaseprcl p ON p.run_seq = h.run_seq
    WHERE c.case_id = (
        SELECT MAX(mb.case_id)
        FROM tmd_mdl_scnrcasem mb
        JOIN tmd_mdl_scnrcaseh mh ON mh.run_id = mb.last_run_id
        WHERE mb.exec_type_cd = 'MI_BASE'
          AND mb.del_yn = 'N'
          AND mb.case_stat_cd = 'COMPLETED'
          AND mh.exec_stat_cd = 'COMPLETED'
          AND mh.del_yn = 'N'
    )
    AND p.prc_rgn_nm = :prc_rgn_nm
    AND p.perd_unit_spt_cd = 'M'
    AND p.del_yn = 'N'
    ORDER BY p.perd_key ASC
    """
)

# 그룹 소속 시나리오들의 최신 완료 실행 user_adj_prc 시계열.
_SCENARIO_PRICE_BY_GROUP_SQL = text(
    """
    SELECT c.scnr_id AS scenario_id,
           p.perd_key AS period_key,
           p.user_adj_prc AS value
    FROM tmd_mdl_scnrcasem c
    JOIN tmd_mdl_scnrcaseh h ON h.run_id = c.last_run_id
    JOIN tmd_mdl_scnrcaseprcl p ON p.run_seq = h.run_seq
    WHERE c.scnr_id IN (
        SELECT s.scenario_id
        FROM tmm_mi_scenario_m s
        WHERE s.scenario_group_id = :scenario_group_id AND s.del_yn = 'N'
    )
    AND h.run_seq = (
        SELECT MAX(lr.run_seq)
        FROM tmd_mdl_scnrcasem lc
        JOIN tmd_mdl_scnrcaseh lr ON lr.run_id = lc.last_run_id
        WHERE lc.scnr_id = c.scnr_id AND lc.del_yn = 'N'
          AND lc.case_stat_cd = 'COMPLETED'
          AND lr.exec_stat_cd = 'COMPLETED'
          AND lr.del_yn = 'N'
    )
    AND p.prc_rgn_nm = :prc_rgn_nm
    AND p.perd_unit_spt_cd = 'M'
    AND p.del_yn = 'N'
    ORDER BY c.scnr_id ASC, p.perd_key ASC
    """
)

def _normalize_period_key(raw: object) -> str | None:
    """perd_key(정수형 YYYYMM 등)를 표시용 'YYYY-MM'으로 정규화한다."""
    if raw is None:
        return None
    text_value = str(raw).strip()
    if not text_value:
        return None
    if len(text_value) >= 6 and text_value[:6].isdigit():
        return f"{text_value[:4]}-{text_value[4:6]}"
    return text_value


def _to_float(raw: object) -> float | None:
    if raw is None:
        return None
    if isinstance(raw, Decimal):
        return float(raw)
    return float(raw)


def _rows_to_series(rows: list[dict]) -> list[dict]:
    series: list[dict] = []
    for row in rows:
        period_key = _normalize_period_key(row.get("period_key"))
        value = _to_float(row.get("value"))
        if period_key is None or value is None:
            continue
        series.append({"period_key": period_key, "value": value})
    return series


class ModelResultRepository(BaseSyncSQLRepository):
    """모델 실행 결과 가격(read-only).

    가격 결과 테이블에 조회 데이터가 없으면(빈 결과) 상위 서비스에서 에러로
    처리한다. 이 repository는 조회만 담당하며 결과를 그대로 반환한다.
    """

    def fetch_mi_base_prices(self, prc_rgn_nm: str) -> list[dict]:
        rows = self.session.execute(
            _MI_BASE_PRICE_SQL, {"prc_rgn_nm": prc_rgn_nm}
        ).mappings().all()
        return _rows_to_series([dict(row) for row in rows])

    def fetch_scenario_prices(
        self, scenario_group_id: int, prc_rgn_nm: str
    ) -> dict[int, list[dict]]:
        rows = self.session.execute(
            _SCENARIO_PRICE_BY_GROUP_SQL,
            {"scenario_group_id": scenario_group_id, "prc_rgn_nm": prc_rgn_nm},
        ).mappings().all()
        return self._group_rows_by_scenario(rows)

    @staticmethod
    def _group_rows_by_scenario(mappings: list) -> dict[int, list[dict]]:
        grouped: dict[int, list[dict]] = {}
        for row in mappings:
            data = dict(row)
            scenario_id = int(data["scenario_id"])
            period_key = _normalize_period_key(data.get("period_key"))
            value = _to_float(data.get("value"))
            if period_key is None or value is None:
                continue
            grouped.setdefault(scenario_id, []).append(
                {"period_key": period_key, "value": value}
            )
        return grouped
