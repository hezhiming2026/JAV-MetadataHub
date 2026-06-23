from datetime import UTC, datetime
from unittest.mock import Mock

from jav_metadatahub.db.models import SourceRecord
from jav_metadatahub.repositories.source_records import SourceRecordRepository
from jav_metadatahub.services.fanza_batch_ingestion import (
    FanzaObservationBatchIngestionService,
)
from jav_metadatahub.services.fanza_ingestion import (
    FanzaIngestionResult,
    FanzaObservationIngestionService,
)


def make_record(record_id: int, source_key: str | None = None) -> SourceRecord:
    return SourceRecord(
        id=record_id,
        source="fanza",
        source_key=source_key or f"cid-{record_id:03d}",
        record_type="work",
        raw_json={"content_id": source_key or f"cid-{record_id:03d}"},
    )


def make_service(
    records: list[SourceRecord],
) -> tuple[FanzaObservationBatchIngestionService, Mock, Mock]:
    source_records = Mock(spec=SourceRecordRepository)
    source_records.list_records.return_value = records
    ingestion = Mock(spec=FanzaObservationIngestionService)
    return (
        FanzaObservationBatchIngestionService(source_records, ingestion),
        source_records,
        ingestion,
    )


def ingestion_result(
    record_id: int,
    observation_count: int,
    skipped_count: int,
) -> FanzaIngestionResult:
    return FanzaIngestionResult(
        source_record_id=record_id,
        entity_type="fanza_work",
        entity_id=record_id,
        observation_count=observation_count,
        skipped_count=skipped_count,
    )


def test_ingest_batch_reads_fanza_work_records_and_accumulates_counts() -> None:
    records = [make_record(1), make_record(2)]
    service, source_records, ingestion = make_service(records)
    observed_at = datetime(2026, 6, 22, 12, 0, tzinfo=UTC)
    ingestion.ingest_source_record.side_effect = [
        ingestion_result(1, observation_count=10, skipped_count=0),
        ingestion_result(2, observation_count=8, skipped_count=1),
    ]

    result = service.ingest_batch(
        limit=50,
        offset=10,
        observed_at=observed_at,
        idempotent=False,
    )

    source_records.list_records.assert_called_once_with(
        source="fanza",
        record_type="work",
        fetch_status="success",
        limit=50,
        offset=10,
    )
    assert ingestion.ingest_source_record.call_args_list[0].kwargs == {
        "observed_at": observed_at,
        "idempotent": False,
    }
    assert ingestion.ingest_source_record.call_args_list[0].args == (records[0],)
    assert ingestion.ingest_source_record.call_args_list[1].args == (records[1],)
    assert result.processed_count == 2
    assert result.succeeded_count == 2
    assert result.failed_count == 0
    assert result.observation_count == 18
    assert result.skipped_count == 1
    assert result.errors == []


def test_dry_run_reads_records_without_calling_single_record_ingestion() -> None:
    service, _source_records, ingestion = make_service([make_record(1), make_record(2)])

    result = service.ingest_batch(dry_run=True)

    ingestion.ingest_source_record.assert_not_called()
    assert result.processed_count == 2
    assert result.succeeded_count == 2
    assert result.failed_count == 0
    assert result.observation_count == 0
    assert result.skipped_count == 0
    assert result.errors == []


def test_single_record_failure_continues_by_default_and_records_error() -> None:
    records = [make_record(1), make_record(2), make_record(3)]
    service, _source_records, ingestion = make_service(records)
    ingestion.ingest_source_record.side_effect = [
        ingestion_result(1, observation_count=5, skipped_count=0),
        ValueError("bad raw_json"),
        ingestion_result(3, observation_count=7, skipped_count=2),
    ]

    result = service.ingest_batch()

    assert ingestion.ingest_source_record.call_count == 3
    assert result.processed_count == 3
    assert result.succeeded_count == 2
    assert result.failed_count == 1
    assert result.observation_count == 12
    assert result.skipped_count == 2
    assert len(result.errors) == 1
    assert result.errors[0].source_record_id == 2
    assert result.errors[0].source_key == "cid-002"
    assert result.errors[0].error_class == "ValueError"
    assert result.errors[0].error_message == "bad raw_json"


def test_continue_on_error_false_stops_after_first_failure() -> None:
    records = [make_record(1), make_record(2), make_record(3)]
    service, _source_records, ingestion = make_service(records)
    ingestion.ingest_source_record.side_effect = [
        ingestion_result(1, observation_count=5, skipped_count=0),
        ValueError("bad raw_json"),
        ingestion_result(3, observation_count=7, skipped_count=0),
    ]

    result = service.ingest_batch(continue_on_error=False)

    assert ingestion.ingest_source_record.call_count == 2
    assert result.processed_count == 2
    assert result.succeeded_count == 1
    assert result.failed_count == 1
    assert result.observation_count == 5
    assert result.skipped_count == 0
    assert len(result.errors) == 1
