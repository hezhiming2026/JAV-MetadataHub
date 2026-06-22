from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import Mock

import pytest

from jav_metadatahub.db.models import SourceRecord
from jav_metadatahub.parsers.fanza_parser import (
    FanzaObservationCandidate,
    FanzaParsedWork,
    FanzaParser,
)
from jav_metadatahub.services.fanza_ingestion import (
    ENTITY_TYPE,
    OBSERVATION_CONFIDENCE,
    FanzaObservationIngestionService,
)
from jav_metadatahub.services.observations import FieldObservationService


def make_source_record(**overrides: object) -> SourceRecord:
    values: dict[str, object] = {
        "id": 123,
        "source": "fanza",
        "source_key": "cid-001",
        "record_type": "work",
        "raw_json": {"content_id": "cid-001", "title": "Title"},
    }
    values.update(overrides)
    return SourceRecord(**values)


def test_ingest_source_record_records_parser_candidates_with_staging_entity() -> None:
    observations = Mock(spec=FieldObservationService)
    observed_at = datetime(2026, 6, 22, 12, 0, tzinfo=UTC)
    service = FanzaObservationIngestionService(observations)
    source_record = make_source_record()

    result = service.ingest_source_record(source_record, observed_at=observed_at)

    assert result.source_record_id == 123
    assert result.entity_type == ENTITY_TYPE
    assert result.entity_id == 123
    assert result.skipped_count == 0
    assert result.observation_count == observations.record_observation.call_count
    assert observations.record_observation.call_count > 0
    first_call = observations.record_observation.call_args_list[0].kwargs
    assert first_call["entity_type"] == "fanza_work"
    assert first_call["entity_id"] == 123
    assert first_call["source_record_id"] == 123
    assert first_call["source"] == "fanza"
    assert first_call["confidence"] == OBSERVATION_CONFIDENCE
    assert first_call["confidence"] == Decimal("0.950")
    assert first_call["observation_status"] == "active"
    assert first_call["observed_at"] == observed_at
    assert first_call["idempotent"] is True


def test_ingest_source_record_forwards_idempotent_flag() -> None:
    observations = Mock(spec=FieldObservationService)
    service = FanzaObservationIngestionService(observations)

    service.ingest_source_record(make_source_record(), idempotent=False)

    assert observations.record_observation.call_args.kwargs["idempotent"] is False


def test_ingestion_result_counts_successful_calls_and_ingestion_skips() -> None:
    observations = Mock(spec=FieldObservationService)
    parser = Mock(spec=FanzaParser)
    parser.parse_work.return_value = FanzaParsedWork(
        observations=[
            FanzaObservationCandidate(field_name="title_ja", field_value="Title"),
            FanzaObservationCandidate(field_name="empty", field_value=[]),
            FanzaObservationCandidate(field_name="content_id", field_value="cid-001"),
        ]
    )
    service = FanzaObservationIngestionService(observations, parser=parser)

    result = service.ingest_source_record(make_source_record())

    assert result.observation_count == 2
    assert result.skipped_count == 1
    assert observations.record_observation.call_count == 2


@pytest.mark.parametrize(
    ("overrides", "match"),
    [
        ({"source": "r18"}, "source_record.source"),
        ({"record_type": "search_result"}, "source_record.record_type"),
        ({"raw_json": []}, "source_record.raw_json"),
        ({"id": None}, "source_record.id"),
        ({"id": 0}, "source_record.id"),
        ({"id": -1}, "source_record.id"),
    ],
)
def test_ingest_source_record_validates_supported_source_record(
    overrides: dict[str, object],
    match: str,
) -> None:
    observations = Mock(spec=FieldObservationService)
    service = FanzaObservationIngestionService(observations)

    with pytest.raises(ValueError, match=match):
        service.ingest_source_record(make_source_record(**overrides))

    observations.record_observation.assert_not_called()
