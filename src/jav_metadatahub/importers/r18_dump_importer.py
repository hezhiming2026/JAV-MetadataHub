"""
R18.dev dump importer v1.

This importer intentionally supports only local structured JSON / JSONL records
that were already derived from a dump. It does not parse real .sql or .sql.gz
dumps, download remote dumps, or access any network resource.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from jav_metadatahub.db.models import SourceRecord
from jav_metadatahub.parsers.r18_parser import R18DumpParser, R18Row
from jav_metadatahub.repositories.source_records import SourceRecordRepository
from jav_metadatahub.services.observations import FieldObservationService


@dataclass(frozen=True)
class R18ImportResult:
    records_seen: int
    source_records_upserted: int
    observations_written: int


class R18DumpImporter:
    source = "r18"
    record_type = "work"
    confidence = Decimal("0.750")

    def __init__(
        self,
        source_records: SourceRecordRepository,
        observations: FieldObservationService,
        parser: R18DumpParser | None = None,
    ) -> None:
        self.source_records = source_records
        self.observations = observations
        self.parser = parser or R18DumpParser()

    def import_records(
        self,
        records: Iterable[R18Row],
        *,
        dump_version: str | None = None,
        imported_at: datetime | None = None,
    ) -> R18ImportResult:
        del dump_version
        records_seen = 0
        source_records_upserted = 0
        observations_written = 0

        for row in records:
            records_seen += 1
            parsed = self.parser.parse_work(row)
            source_record = self.source_records.upsert(
                source=self.source,
                source_key=parsed.source_key,
                record_type=self.record_type,
                source_url=parsed.source_url,
                payload_type="json",
                raw_json=row,
                fetch_status="success",
                parser_version=self.parser.parser_version,
                checksum=parsed.checksum,
                fetched_at=imported_at,
            )
            source_records_upserted += 1

            source_record_id = self._source_record_id(source_record)
            for candidate in parsed.observations:
                self.observations.record_observation(
                    entity_type="r18_work",
                    entity_id=source_record_id,
                    field_name=candidate.field_name,
                    field_value=candidate.field_value,
                    source=self.source,
                    source_record_id=source_record_id,
                    confidence=self.confidence,
                    observation_status="active",
                    observed_at=imported_at,
                )
                observations_written += 1

        return R18ImportResult(
            records_seen=records_seen,
            source_records_upserted=source_records_upserted,
            observations_written=observations_written,
        )

    def import_file(
        self,
        path: str | Path,
        *,
        dump_version: str | None = None,
        imported_at: datetime | None = None,
    ) -> R18ImportResult:
        file_path = Path(path)
        if file_path.suffix.lower() not in {".json", ".jsonl"}:
            raise ValueError("Only .json and .jsonl structured R18 dump records are supported")

        records, file_dump_version = self._load_records(file_path)
        return self.import_records(
            records,
            dump_version=dump_version or file_dump_version,
            imported_at=imported_at,
        )

    def _load_records(self, path: Path) -> tuple[list[R18Row], str | None]:
        if path.suffix.lower() == ".jsonl":
            return self._load_jsonl_records(path), None
        return self._load_json_records(path)

    def _load_json_records(self, path: Path) -> tuple[list[R18Row], str | None]:
        with path.open("r", encoding="utf-8") as file:
            payload = json.load(file)

        if isinstance(payload, list):
            return self._validate_records(payload), None

        if isinstance(payload, dict):
            records = payload.get("records")
            if not isinstance(records, list):
                raise ValueError("JSON object input must contain a records list")
            dump_version = payload.get("dump_version")
            parsed_dump_version = dump_version if isinstance(dump_version, str) else None
            return self._validate_records(records), parsed_dump_version

        raise ValueError("JSON input must be a records list or an object with records")

    def _load_jsonl_records(self, path: Path) -> list[R18Row]:
        records: list[Any] = []
        with path.open("r", encoding="utf-8") as file:
            for line in file:
                stripped = line.strip()
                if stripped:
                    records.append(json.loads(stripped))
        return self._validate_records(records)

    def _validate_records(self, records: list[Any]) -> list[R18Row]:
        validated: list[R18Row] = []
        for record in records:
            if not isinstance(record, dict):
                raise ValueError("Each R18 structured record must be a JSON object")
            validated.append(record)
        return validated

    def _source_record_id(self, source_record: SourceRecord) -> int:
        record_id = source_record.id
        if isinstance(record_id, bool) or not isinstance(record_id, int) or record_id <= 0:
            raise ValueError("source_record.id must be available before writing observations")
        return record_id
