# Copyright (c) 2026 SK Innovation E&S.

from __future__ import annotations

from pydantic import Field

from apps.persistence.schema_base import ApiModel


class MiBaseFilePayload(ApiModel):
    file_no: int
    org_file_nm: str | None = None
    strg_file_nm: str | None = None
    strg_path_nm: str | None = None
    file_size: int | None = None
    filex_nm: str | None = None
    mime_type_nm: str | None = None
    file_rel_obj_spt_cd: str
    file_rel_obj_dstg_no: int


class MiBaseSnapshot(ApiModel):
    case_id: int
    files: list[MiBaseFilePayload] = Field(default_factory=list)

    def files_for(self, relation_code: str) -> tuple[MiBaseFilePayload, ...]:
        return tuple(file for file in self.files if file.file_rel_obj_spt_cd == relation_code)
