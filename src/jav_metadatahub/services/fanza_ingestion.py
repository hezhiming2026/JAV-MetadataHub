from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from jav_metadatahub.db.models import SourceRecord
from jav_metadatahub.parsers.fanza_parser import FanzaParser, ObservationValue
from jav_metadatahub.services.observations import FieldObservationService

SOURCE = "fanza"
ENTITY_TYPE = "fanza_work"
OBSERVATION_CONFIDENCE = Decimal("0.950")


@dataclass(frozen=True)
class FanzaIngestionResult:
    source_record_id: int
    entity_type: str
    entity_id: int
    observation_count: int
    skipped_count: int


def _validate_source_record(source_record: SourceRecord) -> tuple[int, dict[str, Any]]:
    if source_record.source != SOURCE:
        raise ValueError("source_record.source must be fanza")
    if source_record.record_type != "work":
        raise ValueError("source_record.record_type must be work")

    source_record_id = source_record.id
    if not isinstance(source_record_id, int) or isinstance(source_record_id, bool):
        raise ValueError("source_record.id must be a positive integer")
    if source_record_id <= 0:
        raise ValueError("source_record.id must be a positive integer")

    raw_json = source_record.raw_json
    if not isinstance(raw_json, dict):
        raise ValueError("source_record.raw_json must be a dict")

    return source_record_id, raw_json


def _is_meaningful(value: ObservationValue) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list | dict):
        return bool(value)
    return True


class FanzaObservationIngestionService:
    def __init__(
        self,
        observations: FieldObservationService,
        parser: FanzaParser | None = None,
    ) -> None:
        self.observations = observations
        self.parser = parser or FanzaParser()

    def ingest_source_record(
        self,
        source_record: SourceRecord,
        *,
        observed_at: datetime | None = None,
        idempotent: bool = True,
    ) -> FanzaIngestionResult:
        source_record_id, raw_json = _validate_source_record(source_record)
        parsed = self.parser.parse_work(raw_json)

        observation_count = 0
        skipped_count = 0
        for candidate in parsed.observations:
            if not _is_meaningful(candidate.field_value):
                skipped_count += 1
                continue
            self.observations.record_observation(
                entity_type=ENTITY_TYPE,
                entity_id=source_record_id,
                field_name=candidate.field_name,
                field_value=candidate.field_value,
                source=SOURCE,
                source_record_id=source_record_id,
                confidence=OBSERVATION_CONFIDENCE,
                observation_status="active",
                observed_at=observed_at,
                idempotent=idempotent,
            )
            observation_count += 1

        return FanzaIngestionResult(
            source_record_id=source_record_id,
            entity_type=ENTITY_TYPE,
            entity_id=source_record_id,
            observation_count=observation_count,
            skipped_count=skipped_count,
        )
