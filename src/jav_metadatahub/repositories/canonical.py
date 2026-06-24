from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from jav_metadatahub.db.models import Company, Person, Series, Tag, Work


def _validate_limit(value: int) -> int:
    if isinstance(value, bool) or value <= 0:
        raise ValueError("limit must be a positive integer")
    return value


def _validate_offset(value: int) -> int:
    if isinstance(value, bool) or value < 0:
        raise ValueError("offset must be a non-negative integer")
    return value


class WorkRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_page(self, limit: int, offset: int) -> tuple[list[Work], int]:
        cleaned_limit = _validate_limit(limit)
        cleaned_offset = _validate_offset(offset)
        total = self.session.scalar(select(func.count()).select_from(Work)) or 0
        statement = (
            select(Work)
            .order_by(Work.created_at.desc(), Work.id.desc())
            .limit(cleaned_limit)
            .offset(cleaned_offset)
        )
        return list(self.session.scalars(statement).all()), total

    def get_by_id(self, entity_id: int) -> Work | None:
        return self.session.get(Work, entity_id)


class PersonRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_page(self, limit: int, offset: int) -> tuple[list[Person], int]:
        cleaned_limit = _validate_limit(limit)
        cleaned_offset = _validate_offset(offset)
        total = self.session.scalar(select(func.count()).select_from(Person)) or 0
        statement = (
            select(Person)
            .order_by(Person.created_at.desc(), Person.id.desc())
            .limit(cleaned_limit)
            .offset(cleaned_offset)
        )
        return list(self.session.scalars(statement).all()), total

    def get_by_id(self, entity_id: int) -> Person | None:
        return self.session.get(Person, entity_id)


class CompanyRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_page(self, limit: int, offset: int) -> tuple[list[Company], int]:
        cleaned_limit = _validate_limit(limit)
        cleaned_offset = _validate_offset(offset)
        total = self.session.scalar(select(func.count()).select_from(Company)) or 0
        statement = (
            select(Company)
            .order_by(Company.created_at.desc(), Company.id.desc())
            .limit(cleaned_limit)
            .offset(cleaned_offset)
        )
        return list(self.session.scalars(statement).all()), total

    def get_by_id(self, entity_id: int) -> Company | None:
        return self.session.get(Company, entity_id)


class SeriesRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_page(self, limit: int, offset: int) -> tuple[list[Series], int]:
        cleaned_limit = _validate_limit(limit)
        cleaned_offset = _validate_offset(offset)
        total = self.session.scalar(select(func.count()).select_from(Series)) or 0
        statement = (
            select(Series)
            .order_by(Series.created_at.desc(), Series.id.desc())
            .limit(cleaned_limit)
            .offset(cleaned_offset)
        )
        return list(self.session.scalars(statement).all()), total

    def get_by_id(self, entity_id: int) -> Series | None:
        return self.session.get(Series, entity_id)


class TagRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_page(self, limit: int, offset: int) -> tuple[list[Tag], int]:
        cleaned_limit = _validate_limit(limit)
        cleaned_offset = _validate_offset(offset)
        total = self.session.scalar(select(func.count()).select_from(Tag)) or 0
        statement = (
            select(Tag)
            .order_by(Tag.created_at.desc(), Tag.id.desc())
            .limit(cleaned_limit)
            .offset(cleaned_offset)
        )
        return list(self.session.scalars(statement).all()), total

    def get_by_id(self, entity_id: int) -> Tag | None:
        return self.session.get(Tag, entity_id)


__all__ = [
    "CompanyRepository",
    "PersonRepository",
    "SeriesRepository",
    "TagRepository",
    "WorkRepository",
]
