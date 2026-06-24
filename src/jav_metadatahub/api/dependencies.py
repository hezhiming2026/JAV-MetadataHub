from __future__ import annotations

from collections.abc import Generator

from sqlalchemy.orm import Session

from jav_metadatahub.db.session import SessionLocal


def get_db_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
