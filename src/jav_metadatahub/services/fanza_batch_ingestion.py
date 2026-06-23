from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from jav_metadatahub.db.models import SourceRecord
from jav_metadatahub.repositories.source_records import SourceRecordRepository
from jav_metadatahub.services.fanza_ingestion import (
    FanzaObservationIngestionService,
)


@dataclass(frozen=True)
class FanzaObservationBatchError:
    source_record_id: int | None
    source_key: str | None
    error_class: str
    error_message: str


@dataclass(frozen=True)
class FanzaObservationBatchResult:
    processed_count: int = 0
    succeeded_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    observation_count: int = 0
    errors: list[FanzaObservationBatchError] = field(default_factory=list)


def _source_record_id(source_record: SourceRecord) -> int | None:
    record_id = source_record.id
    return record_id if isinstance(record_id, int) and not isinstance(record_id, bool) else None


class FanzaObservationBatchIngestionService:
    def __init__(
        self,
        source_records: SourceRecordRepository,
        ingestion: FanzaObservationIngestionService,
    ) -> None:
        self.source_records = source_records
        self.ingestion = ingestion

    def ingest_batch(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        dry_run: bool = False,
        idempotent: bool = True,
        observed_at: datetime | None = None,
        continue_on_error: bool = True,
    ) -> FanzaObservationBatchResult:
        records = self.source_records.list_records(
            source="fanza",
            record_type="work",
            fetch_status="success",
            limit=limit,
            offset=offset,
        )

        processed_count = 0
        succeeded_count = 0
        failed_count = 0
        skipped_count = 0
        observation_count = 0
        errors: list[FanzaObservationBatchError] = []

        for record in records:
            processed_count += 1
            if dry_run:
                succeeded_count += 1
                continue

            try:
                result = self.ingestion.ingest_source_record(
                    record,
                    observed_at=observed_at,
                    idempotent=idempotent,
                )
            except Exception as exc:  # noqa: BLE001 - batch orchestration records per-row errors.
                failed_count += 1
                errors.append(_batch_error(record, exc))
                if not continue_on_error:
                    break
                continue

            succeeded_count += 1
            skipped_count += result.skipped_count
            observation_count += result.observation_count

        return FanzaObservationBatchResult(
            processed_count=processed_count,
            succeeded_count=succeeded_count,
            failed_count=failed_count,
            skipped_count=skipped_count,
            observation_count=observation_count,
            errors=errors,
        )


def _batch_error(source_record: SourceRecord, exc: Exception) -> FanzaObservationBatchError:
    return FanzaObservationBatchError(
        source_record_id=_source_record_id(source_record),
        source_key=source_record.source_key,
        error_class=exc.__class__.__name__,
        error_message=str(exc),
    )
