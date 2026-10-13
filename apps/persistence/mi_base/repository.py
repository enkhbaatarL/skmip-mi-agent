# Copyright (c) 2026 SK Innovation E&S.

"""Current MI Base and linked-file read-only queries.

The owning model tables and ``tcm_filel`` are external to the Agent-managed ORM
schema. Keep these reads as raw SQL so they do not become application schema
ownership or startup-validation targets.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text

from apps.common.configs.database.sync_database.base import BaseSyncSQLRepository
from apps.persistence.mi_base.schema import MiBaseFilePayload


_ACTIVE_MI_BASE_SQL = text(
    """
    SELECT case_id, last_run_id
    FROM tmd_mdl_scnrcasem
    WHERE actv_base_yn = 'Y'
      AND del_yn = 'N'
    ORDER BY case_id DESC
    LIMIT 2
    """,
)

_MI_BASE_BY_CASE_ID_SQL = text(
    """
    SELECT case_id, last_run_id
    FROM tmd_mdl_scnrcasem
    WHERE case_id = :case_id
      AND del_yn = 'N'
    LIMIT 1
    """,
)

_RUN_SEQUENCE_SQL = text(
    """
    SELECT run_seq
    FROM tmd_mdl_scnrcaseh
    WHERE run_id = :run_id
      AND del_yn = 'N'
    ORDER BY run_seq DESC
    LIMIT 1
    """,
)

_LINKED_FILES_SQL = text(
    """
    SELECT file_no,
           org_file_nm,
           strg_file_nm,
           strg_path_nm,
           file_size,
           filex_nm,
           mime_type_nm,
           file_rel_obj_spt_cd,
           file_rel_obj_dstg_no
    FROM tcm_filel
    WHERE del_yn = 'N'
      AND (
          (file_rel_obj_spt_cd = 'SCNRCASE'
           AND file_rel_obj_dstg_no = :case_id)
          OR
          (:run_seq IS NOT NULL
           AND file_rel_obj_spt_cd IN ('SCNRCASEH', 'SCNRCASEHI', 'SCNRCASEHTF')
           AND file_rel_obj_dstg_no = :run_seq)
      )
    ORDER BY file_rel_obj_spt_cd, file_no
    """,
)


class MiBaseRepository(BaseSyncSQLRepository):
    def fetch_active_candidates(self) -> list[dict[str, Any]]:
        rows = self.session.execute(_ACTIVE_MI_BASE_SQL).mappings().all()
        return [dict(row) for row in rows]

    def fetch_by_case_id(self, case_id: int) -> dict[str, Any] | None:
        row = (
            self.session.execute(
                _MI_BASE_BY_CASE_ID_SQL,
                {"case_id": case_id},
            )
            .mappings()
            .one_or_none()
        )
        return dict(row) if row is not None else None

    def fetch_run_seq(self, run_id: str) -> int | None:
        row = (
            self.session.execute(
                _RUN_SEQUENCE_SQL,
                {"run_id": run_id},
            )
            .mappings()
            .one_or_none()
        )
        return int(row["run_seq"]) if row is not None else None

    def fetch_linked_files(
        self,
        *,
        case_id: int,
        run_seq: int | None,
    ) -> list[MiBaseFilePayload]:
        rows = (
            self.session.execute(
                _LINKED_FILES_SQL,
                {"case_id": case_id, "run_seq": run_seq},
            )
            .mappings()
            .all()
        )
        return [MiBaseFilePayload.model_validate(dict(row)) for row in rows]


__all__ = ["MiBaseRepository"]
