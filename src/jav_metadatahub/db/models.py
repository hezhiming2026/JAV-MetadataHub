from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from jav_metadatahub.db.base import Base

type JsonValue = dict[str, Any] | list[Any] | str | int | float | bool | None


class CollectorRun(Base):
    __tablename__ = "collector_runs"
    __table_args__ = (
        Index("idx_collector_runs_source_started", "source", text("started_at DESC")),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'unknown'"))
    run_type: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'running'"))
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    request_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    success_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    config: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class SourceRecord(Base):
    __tablename__ = "source_records"
    __table_args__ = (
        UniqueConstraint(
            "source",
            "source_key",
            "record_type",
            name="uq_source_records_source_key_record_type",
        ),
        Index("idx_source_records_source_key", "source", "source_key"),
        Index("idx_source_records_record_type", "record_type"),
        Index("idx_source_records_fetched_at", text("fetched_at DESC")),
        Index("idx_source_records_raw_json_gin", "raw_json", postgresql_using="gin"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'unknown'"))
    source_key: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text)
    record_type: Mapped[str] = mapped_column(Text, nullable=False)
    payload_type: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'json'"))
    raw_json: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSONB)
    raw_html: Mapped[str | None] = mapped_column(Text)
    raw_text: Mapped[str | None] = mapped_column(Text)
    http_status: Mapped[int | None] = mapped_column(Integer)
    fetch_status: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'success'")
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    parser_version: Mapped[str | None] = mapped_column(Text)
    checksum: Mapped[str | None] = mapped_column(Text)
    collector_run_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("javhub.collector_runs.id")
    )
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class Work(Base):
    __tablename__ = "works"
    __table_args__ = (
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="confidence_range",
        ),
        Index("idx_works_code_norm", "code_norm"),
        Index("idx_works_code_prefix_number", "code_prefix", "code_number"),
        Index("idx_works_release_date", text("release_date DESC")),
        Index(
            "idx_works_title_ja_trgm",
            "title_ja",
            postgresql_using="gin",
            postgresql_ops={"title_ja": "gin_trgm_ops"},
        ),
        Index(
            "idx_works_title_en_trgm",
            "title_en",
            postgresql_using="gin",
            postgresql_ops={"title_en": "gin_trgm_ops"},
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    code_original: Mapped[str | None] = mapped_column(Text)
    code_norm: Mapped[str | None] = mapped_column(Text)
    code_prefix: Mapped[str | None] = mapped_column(Text)
    code_number: Mapped[str | None] = mapped_column(Text)
    title_ja: Mapped[str | None] = mapped_column(Text)
    title_en: Mapped[str | None] = mapped_column(Text)
    title_zh: Mapped[str | None] = mapped_column(Text)
    release_date: Mapped[date | None] = mapped_column(Date)
    runtime_minutes: Mapped[int | None] = mapped_column(Integer)
    censor_type: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'unknown'"))
    work_type: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'unknown'"))
    primary_source: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[Decimal] = mapped_column(
        Numeric(4, 3), nullable=False, server_default=text("0.000")
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class WorkExternalId(Base):
    __tablename__ = "work_external_ids"
    __table_args__ = (
        UniqueConstraint(
            "source",
            "external_id",
            "id_type",
            name="uq_work_external_ids_source_external_id_type",
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="confidence_range",
        ),
        Index("idx_work_external_ids_work_id", "work_id"),
        Index("idx_work_external_ids_source_external", "source", "external_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    work_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("javhub.works.id", ondelete="CASCADE"), nullable=False
    )
    source: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'unknown'"))
    external_id: Mapped[str] = mapped_column(Text, nullable=False)
    external_url: Mapped[str | None] = mapped_column(Text)
    id_type: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[Decimal] = mapped_column(
        Numeric(4, 3), nullable=False, server_default=text("0.000")
    )
    source_record_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("javhub.source_records.id")
    )
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class Person(Base):
    __tablename__ = "people"
    __table_args__ = (
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="confidence_range",
        ),
        Index(
            "idx_people_canonical_name_trgm",
            "canonical_name",
            postgresql_using="gin",
            postgresql_ops={"canonical_name": "gin_trgm_ops"},
        ),
        Index(
            "idx_people_name_ja_trgm",
            "name_ja",
            postgresql_using="gin",
            postgresql_ops={"name_ja": "gin_trgm_ops"},
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    canonical_name: Mapped[str] = mapped_column(Text, nullable=False)
    name_ja: Mapped[str | None] = mapped_column(Text)
    name_en: Mapped[str | None] = mapped_column(Text)
    name_zh: Mapped[str | None] = mapped_column(Text)
    name_kana: Mapped[str | None] = mapped_column(Text)
    person_type: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'unknown'"))
    gender_role: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'unknown'"))
    primary_source: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[Decimal] = mapped_column(
        Numeric(4, 3), nullable=False, server_default=text("0.000")
    )
    is_active: Mapped[bool | None] = mapped_column(Boolean)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class PersonAlias(Base):
    __tablename__ = "person_aliases"
    __table_args__ = (
        UniqueConstraint(
            "person_id",
            "alias",
            "alias_type",
            "source",
            name="uq_person_aliases_person_alias_type_source",
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="confidence_range",
        ),
        Index("idx_person_aliases_alias_norm", "alias_norm"),
        Index(
            "idx_person_aliases_alias_trgm",
            "alias",
            postgresql_using="gin",
            postgresql_ops={"alias": "gin_trgm_ops"},
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    person_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("javhub.people.id", ondelete="CASCADE"), nullable=False
    )
    alias: Mapped[str] = mapped_column(Text, nullable=False)
    alias_norm: Mapped[str | None] = mapped_column(Text)
    alias_type: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'unknown'"))
    source: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'unknown'"))
    confidence: Mapped[Decimal] = mapped_column(
        Numeric(4, 3), nullable=False, server_default=text("0.000")
    )
    source_record_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("javhub.source_records.id")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class PersonExternalId(Base):
    __tablename__ = "person_external_ids"
    __table_args__ = (
        UniqueConstraint(
            "source",
            "external_id",
            "id_type",
            name="uq_person_external_ids_source_external_id_type",
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="confidence_range",
        ),
        Index("idx_person_external_ids_person_id", "person_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    person_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("javhub.people.id", ondelete="CASCADE"), nullable=False
    )
    source: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'unknown'"))
    external_id: Mapped[str] = mapped_column(Text, nullable=False)
    external_url: Mapped[str | None] = mapped_column(Text)
    id_type: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'database_id'"))
    confidence: Mapped[Decimal] = mapped_column(
        Numeric(4, 3), nullable=False, server_default=text("0.000")
    )
    source_record_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("javhub.source_records.id")
    )
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class WorkPerson(Base):
    __tablename__ = "work_people"
    __table_args__ = (
        UniqueConstraint(
            "work_id",
            "person_id",
            "role",
            "source",
            name="uq_work_people_work_person_role_source",
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="confidence_range",
        ),
        Index("idx_work_people_work_role", "work_id", "role"),
        Index("idx_work_people_person_role", "person_id", "role"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    work_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("javhub.works.id", ondelete="CASCADE"), nullable=False
    )
    person_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("javhub.people.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(Text, nullable=False)
    billing_order: Mapped[int | None] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'unknown'"))
    confidence: Mapped[Decimal] = mapped_column(
        Numeric(4, 3), nullable=False, server_default=text("0.000")
    )
    source_record_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("javhub.source_records.id")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class Company(Base):
    __tablename__ = "companies"
    __table_args__ = (
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="confidence_range",
        ),
        Index("idx_companies_name_norm", "name_norm"),
        Index(
            "idx_companies_name_trgm",
            "name",
            postgresql_using="gin",
            postgresql_ops={"name": "gin_trgm_ops"},
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    name_norm: Mapped[str | None] = mapped_column(Text)
    company_type: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'unknown'")
    )
    primary_source: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[Decimal] = mapped_column(
        Numeric(4, 3), nullable=False, server_default=text("0.000")
    )
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class CompanyExternalId(Base):
    __tablename__ = "company_external_ids"
    __table_args__ = (
        UniqueConstraint(
            "source",
            "external_id",
            "id_type",
            name="uq_company_external_ids_source_external_id_type",
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="confidence_range",
        ),
        Index("idx_company_external_ids_company_id", "company_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("javhub.companies.id", ondelete="CASCADE"), nullable=False
    )
    source: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'unknown'"))
    external_id: Mapped[str] = mapped_column(Text, nullable=False)
    external_url: Mapped[str | None] = mapped_column(Text)
    id_type: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'database_id'"))
    confidence: Mapped[Decimal] = mapped_column(
        Numeric(4, 3), nullable=False, server_default=text("0.000")
    )
    source_record_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("javhub.source_records.id")
    )
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class WorkCompany(Base):
    __tablename__ = "work_companies"
    __table_args__ = (
        UniqueConstraint(
            "work_id",
            "company_id",
            "role",
            "source",
            name="uq_work_companies_work_company_role_source",
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="confidence_range",
        ),
        Index("idx_work_companies_work_role", "work_id", "role"),
        Index("idx_work_companies_company_role", "company_id", "role"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    work_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("javhub.works.id", ondelete="CASCADE"), nullable=False
    )
    company_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("javhub.companies.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'unknown'"))
    confidence: Mapped[Decimal] = mapped_column(
        Numeric(4, 3), nullable=False, server_default=text("0.000")
    )
    source_record_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("javhub.source_records.id")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class Series(Base):
    __tablename__ = "series"
    __table_args__ = (
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="confidence_range",
        ),
        Index("idx_series_name_norm", "name_norm"),
        Index(
            "idx_series_name_trgm",
            "name",
            postgresql_using="gin",
            postgresql_ops={"name": "gin_trgm_ops"},
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    name_norm: Mapped[str | None] = mapped_column(Text)
    primary_source: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[Decimal] = mapped_column(
        Numeric(4, 3), nullable=False, server_default=text("0.000")
    )
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class SeriesExternalId(Base):
    __tablename__ = "series_external_ids"
    __table_args__ = (
        UniqueConstraint(
            "source",
            "external_id",
            "id_type",
            name="uq_series_external_ids_source_external_id_type",
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="confidence_range",
        ),
        Index("idx_series_external_ids_series_id", "series_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    series_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("javhub.series.id", ondelete="CASCADE"), nullable=False
    )
    source: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'unknown'"))
    external_id: Mapped[str] = mapped_column(Text, nullable=False)
    external_url: Mapped[str | None] = mapped_column(Text)
    id_type: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'database_id'"))
    confidence: Mapped[Decimal] = mapped_column(
        Numeric(4, 3), nullable=False, server_default=text("0.000")
    )
    source_record_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("javhub.source_records.id")
    )
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class WorkSeries(Base):
    __tablename__ = "work_series"
    __table_args__ = (
        UniqueConstraint(
            "work_id",
            "series_id",
            "source",
            name="uq_work_series_work_series_source",
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="confidence_range",
        ),
        Index("idx_work_series_work_id", "work_id"),
        Index("idx_work_series_series_id", "series_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    work_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("javhub.works.id", ondelete="CASCADE"), nullable=False
    )
    series_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("javhub.series.id", ondelete="CASCADE"), nullable=False
    )
    source: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'unknown'"))
    confidence: Mapped[Decimal] = mapped_column(
        Numeric(4, 3), nullable=False, server_default=text("0.000")
    )
    source_record_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("javhub.source_records.id")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class Tag(Base):
    __tablename__ = "tags"
    __table_args__ = (
        UniqueConstraint(
            "name_norm",
            "tag_type",
            "language",
            "source",
            name="uq_tags_name_norm_type_language_source",
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="confidence_range",
        ),
        Index("idx_tags_name_norm", "name_norm"),
        Index(
            "idx_tags_name_trgm",
            "name",
            postgresql_using="gin",
            postgresql_ops={"name": "gin_trgm_ops"},
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    name_norm: Mapped[str | None] = mapped_column(Text)
    tag_type: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'unknown'"))
    language: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'unknown'"))
    source: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'unknown'"))
    confidence: Mapped[Decimal] = mapped_column(
        Numeric(4, 3), nullable=False, server_default=text("0.000")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class WorkTag(Base):
    __tablename__ = "work_tags"
    __table_args__ = (
        UniqueConstraint(
            "work_id",
            "tag_id",
            "source",
            name="uq_work_tags_work_tag_source",
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="confidence_range",
        ),
        Index("idx_work_tags_work_id", "work_id"),
        Index("idx_work_tags_tag_id", "tag_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    work_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("javhub.works.id", ondelete="CASCADE"), nullable=False
    )
    tag_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("javhub.tags.id", ondelete="CASCADE"), nullable=False
    )
    source: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'unknown'"))
    confidence: Mapped[Decimal] = mapped_column(
        Numeric(4, 3), nullable=False, server_default=text("0.000")
    )
    source_record_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("javhub.source_records.id")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class FieldObservation(Base):
    __tablename__ = "field_observations"
    __table_args__ = (
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="confidence_range",
        ),
        Index("idx_field_observations_entity", "entity_type", "entity_id"),
        Index("idx_field_observations_field", "field_name"),
        Index("idx_field_observations_source", "source"),
        Index(
            "idx_field_observations_value_text_trgm",
            "field_value_text",
            postgresql_using="gin",
            postgresql_ops={"field_value_text": "gin_trgm_ops"},
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    entity_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    field_name: Mapped[str] = mapped_column(Text, nullable=False)
    field_value: Mapped[JsonValue] = mapped_column(JSONB)
    field_value_text: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'unknown'"))
    source_record_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("javhub.source_records.id")
    )
    confidence: Mapped[Decimal] = mapped_column(
        Numeric(4, 3), nullable=False, server_default=text("0.000")
    )
    observation_status: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'active'")
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class EntityMatchCandidate(Base):
    __tablename__ = "entity_match_candidates"
    __table_args__ = (
        UniqueConstraint(
            "entity_type",
            "left_entity_id",
            "right_entity_id",
            name="uq_entity_match_candidates_entity_left_right",
        ),
        CheckConstraint(
            "match_score >= 0 AND match_score <= 1",
            name="match_score_range",
        ),
        Index("idx_entity_match_candidates_entity_status", "entity_type", "status"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    left_entity_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    right_entity_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    match_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    match_reason: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'pending'"))
    reviewed_by: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class EntityMergeLog(Base):
    __tablename__ = "entity_merge_logs"
    __table_args__ = (
        CheckConstraint(
            "merge_confidence >= 0 AND merge_confidence <= 1",
            name="merge_confidence_range",
        ),
        Index(
            "idx_entity_merge_logs_entity",
            "entity_type",
            "from_entity_id",
            "to_entity_id",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    from_entity_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    to_entity_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    merge_reason: Mapped[str | None] = mapped_column(Text)
    merge_confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    merged_by: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'manual'"))
    merged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class MediaAsset(Base):
    __tablename__ = "media_assets"
    __table_args__ = (
        UniqueConstraint("source", "url", name="uq_media_assets_source_url"),
        Index("idx_media_assets_work_id", "work_id"),
        Index("idx_media_assets_person_id", "person_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    work_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("javhub.works.id", ondelete="CASCADE")
    )
    person_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("javhub.people.id", ondelete="CASCADE")
    )
    asset_type: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'unknown'"))
    url: Mapped[str] = mapped_column(Text, nullable=False)
    local_path: Mapped[str | None] = mapped_column(Text)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    hash: Mapped[str | None] = mapped_column(Text)
    download_status: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'url_only'")
    )
    copyright_note: Mapped[str | None] = mapped_column(Text)
    source_record_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("javhub.source_records.id")
    )
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


__all__ = [
    "CollectorRun",
    "Company",
    "CompanyExternalId",
    "EntityMatchCandidate",
    "EntityMergeLog",
    "FieldObservation",
    "MediaAsset",
    "Person",
    "PersonAlias",
    "PersonExternalId",
    "Series",
    "SeriesExternalId",
    "SourceRecord",
    "Tag",
    "Work",
    "WorkCompany",
    "WorkExternalId",
    "WorkPerson",
    "WorkSeries",
    "WorkTag",
]
