from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from sqlalchemy.orm import Session

from jav_metadatahub.repositories.field_observations import FieldObservationRepository
from jav_metadatahub.repositories.source_records import SourceRecordRepository
from jav_metadatahub.services.fanza_batch_ingestion import (
    FanzaObservationBatchIngestionService,
    FanzaObservationBatchResult,
)
from jav_metadatahub.services.fanza_ingestion import FanzaObservationIngestionService
from jav_metadatahub.services.observations import FieldObservationService

type FanzaIngestionRunMode = Literal[
    "dry-run",
    "rollback",
    "commit",
    "rollback-due-to-errors",
]


@dataclass(frozen=True)
class FanzaObservationIngestionRunResult:
    mode: FanzaIngestionRunMode
    batch_result: FanzaObservationBatchResult


def run_fanza_observation_ingestion(
    session: Session,
    *,
    limit: int = 100,
    offset: int = 0,
    dry_run: bool = False,
    commit: bool = False,
    idempotent: bool = True,
    continue_on_error: bool = True,
    observed_at: datetime | None = None,
) -> FanzaObservationIngestionRunResult:
    if dry_run and commit:
        raise ValueError("dry-run cannot be combined with commit")

    try:
        batch_service = _build_batch_service(session)
        batch_result = batch_service.ingest_batch(
            limit=limit,
            offset=offset,
            dry_run=dry_run,
            idempotent=idempotent,
            continue_on_error=continue_on_error,
            observed_at=observed_at,
        )

        mode = _finalize_transaction(
            session,
            dry_run=dry_run,
            commit=commit,
            failed_count=batch_result.failed_count,
        )
        return FanzaObservationIngestionRunResult(mode=mode, batch_result=batch_result)
    except Exception:
        session.rollback()
        raise


def _build_batch_service(session: Session) -> FanzaObservationBatchIngestionService:
    source_records = SourceRecordRepository(session)
    field_observations = FieldObservationRepository(session)
    observation_service = FieldObservationService(field_observations)
    fanza_ingestion = FanzaObservationIngestionService(observation_service)
    return FanzaObservationBatchIngestionService(source_records, fanza_ingestion)


def _finalize_transaction(
    session: Session,
    *,
    dry_run: bool,
    commit: bool,
    failed_count: int,
) -> FanzaIngestionRunMode:
    if dry_run:
        session.rollback()
        return "dry-run"

    if commit and failed_count == 0:
        session.commit()
        return "commit"

    session.rollback()
    if commit and failed_count > 0:
        return "rollback-due-to-errors"
    return "rollback"
