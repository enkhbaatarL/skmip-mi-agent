# Copyright (c) 2026 SK Innovation E&S.

from __future__ import annotations

from sqlalchemy.orm import Session

from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode
from apps.persistence.mi_base.repository import MiBaseRepository
from apps.persistence.mi_base.schema import MiBaseSnapshot


class MiBaseService:
    """Resolve and hydrate the MI Base selected for a proposal request."""

    def __init__(self, *, session: Session | None = None) -> None:
        self._session = session

    def load_active_case_id(self) -> int | None:
        if self._session is not None:
            return self._load_active_case_id(
                MiBaseRepository(session=self._session),
            )

        from apps.common.configs.database.sync_database.connection import (
            get_sync_session,
        )

        session = get_sync_session()
        try:
            return self._load_active_case_id(MiBaseRepository(session=session))
        finally:
            session.close()

    def load_snapshot(self, case_id: int) -> MiBaseSnapshot:
        if self._session is not None:
            return self._load_snapshot(
                MiBaseRepository(session=self._session),
                case_id=case_id,
            )

        from apps.common.configs.database.sync_database.connection import (
            get_sync_session,
        )

        session = get_sync_session()
        try:
            return self._load_snapshot(
                MiBaseRepository(session=session),
                case_id=case_id,
            )
        finally:
            session.close()

    @staticmethod
    def _load_active_case_id(repository: MiBaseRepository) -> int | None:
        candidates = repository.fetch_active_candidates()
        if not candidates:
            return None
        if len(candidates) > 1:
            case_ids = [int(candidate["case_id"]) for candidate in candidates]
            raise MIBaseError(
                ErrorCode.INVALID_REQUEST,
                detail=(f"Multiple active MI Base cases were found: case_ids={case_ids}"),
            )
        return int(candidates[0]["case_id"])

    @staticmethod
    def _load_snapshot(
        repository: MiBaseRepository,
        *,
        case_id: int,
    ) -> MiBaseSnapshot:
        row = repository.fetch_by_case_id(case_id)
        if row is None:
            raise MIBaseError(
                ErrorCode.ENTITY_NOT_FOUND,
                detail=f"MI Base case not found: case_id={case_id}",
            )
        selected_case_id = int(row["case_id"])
        return MiBaseSnapshot(
            case_id=selected_case_id,
            files=repository.fetch_linked_files(case_id=selected_case_id),
        )


__all__ = ["MiBaseService"]
