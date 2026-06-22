from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from jav_metadatahub.db.models import CollectorRun


class CollectorRunRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def start(
        self,
        *,
        source: str,
        run_type: str,
        config: dict[str, Any] | None = None,
    ) -> CollectorRun:
        run = CollectorRun(
            source=source,
            run_type=run_type,
            status="running",
            request_count=0,
            success_count=0,
            failed_count=0,
            config=config,
        )
        self.session.add(run)
        self.session.flush()
        return run

    def finish(
        self,
        run: CollectorRun,
        *,
        status: str,
        request_count: int,
        success_count: int,
        failed_count: int,
        error_message: str | None = None,
    ) -> CollectorRun:
        run.status = status
        run.request_count = request_count
        run.success_count = success_count
        run.failed_count = failed_count
        run.error_message = error_message
        run.finished_at = datetime.now(UTC)
        self.session.flush()
        return run
