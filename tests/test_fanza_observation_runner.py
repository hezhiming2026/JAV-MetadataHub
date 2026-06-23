from datetime import UTC, datetime
from unittest.mock import Mock

import pytest
from sqlalchemy.orm import Session

from jav_metadatahub.runners import fanza_observation_ingestion as runner_module
from jav_metadatahub.runners.fanza_observation_ingestion import (
    run_fanza_observation_ingestion,
)
from jav_metadatahub.services.fanza_batch_ingestion import FanzaObservationBatchResult


class FakeBatchService:
    def __init__(
        self,
        result: FanzaObservationBatchResult | None = None,
        exc: Exception | None = None,
    ) -> None:
        self.result = result or FanzaObservationBatchResult()
        self.exc = exc
        self.call_kwargs: dict[str, object] | None = None

    def ingest_batch(self, **kwargs: object) -> FanzaObservationBatchResult:
        self.call_kwargs = kwargs
        if self.exc is not None:
            raise self.exc
        return self.result


def patch_batch_service(
    monkeypatch: pytest.MonkeyPatch,
    batch_service: FakeBatchService,
) -> None:
    monkeypatch.setattr(
        runner_module,
        "_build_batch_service",
        lambda _session: batch_service,
    )


def test_runner_rolls_back_by_default_and_passes_batch_options(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = Mock(spec=Session)
    batch_service = FakeBatchService(
        FanzaObservationBatchResult(processed_count=1, observation_count=3)
    )
    patch_batch_service(monkeypatch, batch_service)
    observed_at = datetime(2026, 6, 22, 12, 0, tzinfo=UTC)

    result = run_fanza_observation_ingestion(
        session,
        limit=25,
        offset=5,
        dry_run=False,
        commit=False,
        idempotent=False,
        continue_on_error=False,
        observed_at=observed_at,
    )

    assert result.mode == "rollback"
    assert result.batch_result.processed_count == 1
    assert batch_service.call_kwargs == {
        "limit": 25,
        "offset": 5,
        "dry_run": False,
        "idempotent": False,
        "continue_on_error": False,
        "observed_at": observed_at,
    }
    session.rollback.assert_called_once_with()
    session.commit.assert_not_called()


def test_runner_commits_only_when_requested_and_no_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = Mock(spec=Session)
    patch_batch_service(monkeypatch, FakeBatchService(FanzaObservationBatchResult()))

    result = run_fanza_observation_ingestion(session, commit=True)

    assert result.mode == "commit"
    session.commit.assert_called_once_with()
    session.rollback.assert_not_called()


def test_runner_rolls_back_commit_request_when_batch_has_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = Mock(spec=Session)
    patch_batch_service(
        monkeypatch,
        FakeBatchService(FanzaObservationBatchResult(failed_count=1)),
    )

    result = run_fanza_observation_ingestion(session, commit=True)

    assert result.mode == "rollback-due-to-errors"
    session.rollback.assert_called_once_with()
    session.commit.assert_not_called()


def test_runner_dry_run_always_rolls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    session = Mock(spec=Session)
    patch_batch_service(monkeypatch, FakeBatchService(FanzaObservationBatchResult()))

    result = run_fanza_observation_ingestion(session, dry_run=True)

    assert result.mode == "dry-run"
    session.rollback.assert_called_once_with()
    session.commit.assert_not_called()


def test_runner_rejects_dry_run_commit_without_transaction() -> None:
    session = Mock(spec=Session)

    with pytest.raises(ValueError, match="dry-run"):
        run_fanza_observation_ingestion(session, dry_run=True, commit=True)

    session.rollback.assert_not_called()
    session.commit.assert_not_called()


def test_runner_rolls_back_on_unhandled_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    session = Mock(spec=Session)
    patch_batch_service(monkeypatch, FakeBatchService(exc=RuntimeError("boom")))

    with pytest.raises(RuntimeError, match="boom"):
        run_fanza_observation_ingestion(session)

    session.rollback.assert_called_once_with()
    session.commit.assert_not_called()


def test_runner_constructs_repository_and_service_graph(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = Mock(spec=Session)
    constructed: list[tuple[str, object]] = []

    class FakeSourceRecordRepository:
        def __init__(self, received_session: Session) -> None:
            constructed.append(("source_records", received_session))

    class FakeFieldObservationRepository:
        def __init__(self, received_session: Session) -> None:
            constructed.append(("field_observations", received_session))

    class FakeFieldObservationService:
        def __init__(self, repository: FakeFieldObservationRepository) -> None:
            constructed.append(("observation_service", repository))

    class FakeFanzaObservationIngestionService:
        def __init__(self, observation_service: FakeFieldObservationService) -> None:
            constructed.append(("fanza_ingestion", observation_service))

    class FakeFanzaObservationBatchIngestionService:
        def __init__(
            self,
            source_records: FakeSourceRecordRepository,
            fanza_ingestion: FakeFanzaObservationIngestionService,
        ) -> None:
            constructed.append(("batch", (source_records, fanza_ingestion)))

        def ingest_batch(self, **_kwargs: object) -> FanzaObservationBatchResult:
            return FanzaObservationBatchResult()

    monkeypatch.setattr(runner_module, "SourceRecordRepository", FakeSourceRecordRepository)
    monkeypatch.setattr(
        runner_module,
        "FieldObservationRepository",
        FakeFieldObservationRepository,
    )
    monkeypatch.setattr(runner_module, "FieldObservationService", FakeFieldObservationService)
    monkeypatch.setattr(
        runner_module,
        "FanzaObservationIngestionService",
        FakeFanzaObservationIngestionService,
    )
    monkeypatch.setattr(
        runner_module,
        "FanzaObservationBatchIngestionService",
        FakeFanzaObservationBatchIngestionService,
    )

    run_fanza_observation_ingestion(session)

    assert [name for name, _value in constructed] == [
        "source_records",
        "field_observations",
        "observation_service",
        "fanza_ingestion",
        "batch",
    ]
    assert constructed[0] == ("source_records", session)
    assert constructed[1] == ("field_observations", session)
