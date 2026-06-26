from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from jav_metadatahub.db.models import Company, Person, Series, Tag, Work, WorkExternalId


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

    def create(
        self,
        *,
        code_original: str | None = None,
        code_norm: str | None = None,
        code_prefix: str | None = None,
        code_number: str | None = None,
        title_ja: str | None = None,
        release_date: date | None = None,
        runtime_minutes: int | None = None,
        censor_type: str = "unknown",
        work_type: str = "unknown",
        primary_source: str | None = None,
        confidence: Decimal = Decimal("0.000"),
        is_active: bool = True,
    ) -> Work:
        work = Work(
            code_original=code_original,
            code_norm=code_norm,
            code_prefix=code_prefix,
            code_number=code_number,
            title_ja=title_ja,
            release_date=release_date,
            runtime_minutes=runtime_minutes,
            censor_type=censor_type,
            work_type=work_type,
            primary_source=primary_source,
            confidence=confidence,
            is_active=is_active,
        )
        self.session.add(work)
        self.session.flush()
        return work

    def compute_fillable_fields(self, work: Work, values: dict[str, Any]) -> dict[str, Any]:
        fillable: dict[str, Any] = {}
        for field_name in (
            "code_original",
            "code_norm",
            "code_prefix",
            "code_number",
            "title_ja",
            "release_date",
            "runtime_minutes",
            "primary_source",
        ):
            incoming = values.get(field_name)
            if incoming is not None and getattr(work, field_name) is None:
                fillable[field_name] = incoming
        return fillable

    def apply_fillable_fields(self, work: Work, fields: dict[str, Any]) -> bool:
        if not fields:
            return False
        for field_name, value in fields.items():
            setattr(work, field_name, value)
        self.session.flush()
        return True


class WorkExternalIdRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_source_external_id(
        self,
        *,
        source: str,
        external_id: str,
        id_type: str,
    ) -> WorkExternalId | None:
        statement = select(WorkExternalId).where(
            WorkExternalId.source == source,
            WorkExternalId.external_id == external_id,
            WorkExternalId.id_type == id_type,
        )
        return self.session.scalar(statement)

    def create(
        self,
        *,
        work_id: int,
        source: str,
        external_id: str,
        id_type: str,
        external_url: str | None = None,
        confidence: Decimal = Decimal("0.000"),
        source_record_id: int | None = None,
        fetched_at: datetime | None = None,
    ) -> WorkExternalId:
        external_id_record = WorkExternalId(
            work_id=work_id,
            source=source,
            external_id=external_id,
            external_url=external_url,
            id_type=id_type,
            confidence=confidence,
            source_record_id=source_record_id,
            fetched_at=fetched_at,
        )
        self.session.add(external_id_record)
        self.session.flush()
        return external_id_record


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
    "WorkExternalIdRepository",
    "WorkRepository",
]
