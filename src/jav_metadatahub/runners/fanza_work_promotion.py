from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from sqlalchemy.orm import Session

from jav_metadatahub.repositories import (
    FieldObservationRepository,
    SourceRecordRepository,
    WorkExternalIdRepository,
    WorkRepository,
)
from jav_metadatahub.services.work_promotion import WorkPromotionResult, WorkPromotionService

type FanzaWorkPromotionRunMode = Literal[
    "dry-run",
    "rollback",
    "commit",
    "rollback-due-to-errors",
]


@dataclass(frozen=True)
class FanzaWorkPromotionRunResult:
    mode: FanzaWorkPromotionRunMode
    promotion_result: WorkPromotionResult


def run_fanza_work_promotion(
    session: Session,
    *,
    limit: int = 100,
    offset: int = 0,
    dry_run: bool = False,
    commit: bool = False,
    continue_on_error: bool = True,
) -> FanzaWorkPromotionRunResult:
    if dry_run and commit:
        raise ValueError("dry-run cannot be combined with commit")

    try:
        service = _build_promotion_service(session)
        promotion_result = service.promote_fanza_works(
            limit=limit,
            offset=offset,
            dry_run=dry_run,
            continue_on_error=continue_on_error,
        )
        mode = _finalize_transaction(
            session,
            dry_run=dry_run,
            commit=commit,
            failed_count=promotion_result.failed_count,
        )
        return FanzaWorkPromotionRunResult(mode=mode, promotion_result=promotion_result)
    except Exception:
        session.rollback()
        raise


def _build_promotion_service(session: Session) -> WorkPromotionService:
    return WorkPromotionService(
        field_observations=FieldObservationRepository(session),
        source_records=SourceRecordRepository(session),
        works=WorkRepository(session),
        work_external_ids=WorkExternalIdRepository(session),
    )


def _finalize_transaction(
    session: Session,
    *,
    dry_run: bool,
    commit: bool,
    failed_count: int,
) -> FanzaWorkPromotionRunMode:
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


__all__ = [
    "FanzaWorkPromotionRunResult",
    "run_fanza_work_promotion",
]
