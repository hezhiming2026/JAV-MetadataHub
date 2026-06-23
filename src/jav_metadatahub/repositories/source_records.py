from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from jav_metadatahub.db.models import SourceRecord

type JsonPayload = dict[str, Any] | list[Any] | None


def _clean_required_string(value: str | None, field_name: str) -> str:
    if value is None:
        raise ValueError(f"{field_name} is required")

    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} is required")

    return cleaned


def _validate_positive_int(value: int, field_name: str) -> int:
    if isinstance(value, bool) or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer")
    return value


def _validate_non_negative_int(value: int, field_name: str) -> int:
    if isinstance(value, bool) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer")
    return value


class SourceRecordRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        *,
        source: str | None,
        source_key: str | None,
        record_type: str | None,
        source_url: str | None = None,
        payload_type: str | None = "json",
        raw_json: JsonPayload = None,
        raw_html: str | None = None,
        raw_text: str | None = None,
        http_status: int | None = None,
        fetch_status: str = "success",
        error_message: str | None = None,
        parser_version: str | None = None,
        checksum: str | None = None,
        collector_run_id: int | None = None,
        fetched_at: datetime | None = None,
    ) -> SourceRecord:
        record_values = self._record_values(
            source=source,
            source_key=source_key,
            record_type=record_type,
            source_url=source_url,
            payload_type=payload_type,
            raw_json=raw_json,
            raw_html=raw_html,
            raw_text=raw_text,
            http_status=http_status,
            fetch_status=fetch_status,
            error_message=error_message,
            parser_version=parser_version,
            checksum=checksum,
            collector_run_id=collector_run_id,
        )
        if fetched_at is not None:
            record_values["fetched_at"] = fetched_at

        record = SourceRecord(**record_values)
        self.session.add(record)
        self.session.flush()
        return record

    def get_by_id(self, record_id: int) -> SourceRecord | None:
        return self.session.get(SourceRecord, record_id)

    def get_by_source_key(
        self,
        source: str | None,
        source_key: str | None,
        record_type: str | None,
    ) -> SourceRecord | None:
        cleaned_source = _clean_required_string(source, "source")
        cleaned_source_key = _clean_required_string(source_key, "source_key")
        cleaned_record_type = _clean_required_string(record_type, "record_type")

        statement = select(SourceRecord).where(
            SourceRecord.source == cleaned_source,
            SourceRecord.source_key == cleaned_source_key,
            SourceRecord.record_type == cleaned_record_type,
        )
        return self.session.scalar(statement)

    def list_records(
        self,
        source: str | None,
        record_type: str | None,
        *,
        fetch_status: str | None = "success",
        limit: int = 100,
        offset: int = 0,
    ) -> list[SourceRecord]:
        cleaned_source = _clean_required_string(source, "source")
        cleaned_record_type = _clean_required_string(record_type, "record_type")
        cleaned_limit = _validate_positive_int(limit, "limit")
        cleaned_offset = _validate_non_negative_int(offset, "offset")

        statement = select(SourceRecord).where(
            SourceRecord.source == cleaned_source,
            SourceRecord.record_type == cleaned_record_type,
        )

        if fetch_status is not None:
            statement = statement.where(
                SourceRecord.fetch_status
                == _clean_required_string(
                    fetch_status,
                    "fetch_status",
                )
            )

        statement = (
            statement.order_by(
                SourceRecord.fetched_at.desc(),
                SourceRecord.id.desc(),
            )
            .limit(cleaned_limit)
            .offset(cleaned_offset)
        )
        return list(self.session.scalars(statement).all())

    def upsert(
        self,
        *,
        source: str | None,
        source_key: str | None,
        record_type: str | None,
        source_url: str | None = None,
        payload_type: str | None = "json",
        raw_json: JsonPayload = None,
        raw_html: str | None = None,
        raw_text: str | None = None,
        http_status: int | None = None,
        fetch_status: str = "success",
        error_message: str | None = None,
        parser_version: str | None = None,
        checksum: str | None = None,
        collector_run_id: int | None = None,
        fetched_at: datetime | None = None,
    ) -> SourceRecord:
        fetched_at_value = fetched_at if fetched_at is not None else func.now()
        record_values = self._record_values(
            source=source,
            source_key=source_key,
            record_type=record_type,
            source_url=source_url,
            payload_type=payload_type,
            raw_json=raw_json,
            raw_html=raw_html,
            raw_text=raw_text,
            http_status=http_status,
            fetch_status=fetch_status,
            error_message=error_message,
            parser_version=parser_version,
            checksum=checksum,
            collector_run_id=collector_run_id,
        )
        record_values["fetched_at"] = fetched_at_value

        statement = insert(SourceRecord).values(**record_values)
        upsert_statement = statement.on_conflict_do_update(
            index_elements=["source", "source_key", "record_type"],
            set_={
                "source_url": statement.excluded.source_url,
                "payload_type": statement.excluded.payload_type,
                "raw_json": statement.excluded.raw_json,
                "raw_html": statement.excluded.raw_html,
                "raw_text": statement.excluded.raw_text,
                "http_status": statement.excluded.http_status,
                "fetch_status": statement.excluded.fetch_status,
                "error_message": statement.excluded.error_message,
                "parser_version": statement.excluded.parser_version,
                "checksum": statement.excluded.checksum,
                "collector_run_id": statement.excluded.collector_run_id,
                "fetched_at": statement.excluded.fetched_at,
            },
        ).returning(SourceRecord)

        return self.session.execute(upsert_statement).scalar_one()

    def _record_values(
        self,
        *,
        source: str | None,
        source_key: str | None,
        record_type: str | None,
        source_url: str | None,
        payload_type: str | None,
        raw_json: JsonPayload,
        raw_html: str | None,
        raw_text: str | None,
        http_status: int | None,
        fetch_status: str,
        error_message: str | None,
        parser_version: str | None,
        checksum: str | None,
        collector_run_id: int | None,
    ) -> dict[str, Any]:
        return {
            "source": _clean_required_string(source, "source"),
            "source_key": _clean_required_string(source_key, "source_key"),
            "record_type": _clean_required_string(record_type, "record_type"),
            "source_url": source_url,
            "payload_type": _clean_required_string(payload_type, "payload_type"),
            "raw_json": raw_json,
            "raw_html": raw_html,
            "raw_text": raw_text,
            "http_status": http_status,
            "fetch_status": fetch_status,
            "error_message": error_message,
            "parser_version": parser_version,
            "checksum": checksum,
            "collector_run_id": collector_run_id,
        }
