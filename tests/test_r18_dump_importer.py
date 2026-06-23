from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock

import pytest

from jav_metadatahub.db.models import FieldObservation, SourceRecord
from jav_metadatahub.importers.r18_dump_importer import R18DumpImporter
from jav_metadatahub.repositories.source_records import SourceRecordRepository
from jav_metadatahub.services.observations import FieldObservationService

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "r18_dump"


def make_importer() -> tuple[R18DumpImporter, Mock, Mock]:
    source_records = Mock(spec=SourceRecordRepository)
    observations = Mock(spec=FieldObservationService)
    observations.record_observation.return_value = FieldObservation(
        entity_type="r18_work",
        entity_id=1,
        field_name="title_ja",
        source="r18",
    )
    return R18DumpImporter(source_records, observations), source_records, observations


def test_import_records_upserts_source_record_before_writing_observations() -> None:
    importer, source_records, observations = make_importer()
    source_records.upsert.return_value = SourceRecord(
        id=101,
        source="r18",
        source_key="r18-content-001",
        record_type="work",
    )
    imported_at = datetime(2026, 6, 22, 12, 0, tzinfo=UTC)
    row = {
        "content_id": "r18-content-001",
        "dvd_id": "ABP-477",
        "title_ja": "日本語タイトル",
        "runtime_minutes": "120",
    }

    result = importer.import_records([row], dump_version="dump-v1", imported_at=imported_at)

    assert result.records_seen == 1
    assert result.source_records_upserted == 1
    assert result.observations_written > 0
    source_records.upsert.assert_called_once()
    upsert_kwargs = source_records.upsert.call_args.kwargs
    assert upsert_kwargs["source"] == "r18"
    assert upsert_kwargs["source_key"] == "r18-content-001"
    assert upsert_kwargs["record_type"] == "work"
    assert upsert_kwargs["payload_type"] == "json"
    assert upsert_kwargs["raw_json"] == row
    assert upsert_kwargs["parser_version"] == "r18_dump_parser_v1"
    assert upsert_kwargs["fetch_status"] == "success"
    assert upsert_kwargs["fetched_at"] == imported_at
    assert isinstance(upsert_kwargs["checksum"], str)

    first_observation_kwargs = observations.record_observation.call_args_list[0].kwargs
    assert first_observation_kwargs["entity_type"] == "r18_work"
    assert first_observation_kwargs["entity_id"] == 101
    assert first_observation_kwargs["source_record_id"] == 101
    assert first_observation_kwargs["source"] == "r18"
    assert first_observation_kwargs["observed_at"] == imported_at


def test_import_records_uses_source_record_upsert_and_observation_idempotency() -> None:
    importer, source_records, observations = make_importer()
    source_records.upsert.return_value = SourceRecord(
        id=102,
        source="r18",
        source_key="IPX-001",
        record_type="work",
    )

    importer.import_records([{"content_id": " ", "dvd_id": "IPX-001", "title_en": "Title"}])

    assert source_records.upsert.call_count == 1
    assert observations.record_observation.call_count > 0
    assert all(call.kwargs["entity_type"] == "r18_work" for call in observations.method_calls)
    assert all(call.kwargs["entity_id"] == 102 for call in observations.method_calls)


def test_import_file_reads_json_object_records_fixture() -> None:
    importer, source_records, observations = make_importer()
    source_records.upsert.side_effect = [
        SourceRecord(id=201, source="r18", source_key="r18-content-001", record_type="work"),
        SourceRecord(id=202, source="r18", source_key="IPX-001", record_type="work"),
    ]

    result = importer.import_file(FIXTURE_DIR / "work_records.json")

    assert result.records_seen == 2
    assert source_records.upsert.call_count == 2
    assert observations.record_observation.call_count > 0


def test_import_file_reads_jsonl_fixture() -> None:
    importer, source_records, _observations = make_importer()
    source_records.upsert.side_effect = [
        SourceRecord(id=301, source="r18", source_key="jsonl-content-001", record_type="work"),
        SourceRecord(id=302, source="r18", source_key="row_sha256:test", record_type="work"),
    ]

    result = importer.import_file(FIXTURE_DIR / "work_records.jsonl")

    assert result.records_seen == 2
    assert source_records.upsert.call_count == 2


@pytest.mark.parametrize(
    "filename",
    [
        "dump.sql",
        "dump.sql.gz",
        "dump.gz",
        "dump.zip",
        "dump.txt",
    ],
)
def test_import_file_rejects_unsupported_suffixes(tmp_path: Path, filename: str) -> None:
    importer, _source_records, _observations = make_importer()
    path = tmp_path / filename
    path.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="Only .json and .jsonl"):
        importer.import_file(path)
