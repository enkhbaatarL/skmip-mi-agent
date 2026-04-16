from sqlalchemy.orm import Session as SQLAlchemySession


class BaseSyncSQLRepository:
    """Sync Repository 베이스 클래스."""

    def __init__(self, session: SQLAlchemySession) -> None:
        self.session = session
