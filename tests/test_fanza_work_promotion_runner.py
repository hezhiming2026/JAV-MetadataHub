from __future__ import annotations

from unittest.mock import Mock

import pytest
from sqlalchemy.orm import Session

from jav_metadatahub.runners import fanza_work_promotion as runner_module
from jav_metadatahub.runners.fanza_work_promotion import run_fanza_work_promotion
from jav_metadatahub.services.work_promotion import WorkPromotionResult


class FakePromotionService:
    def __init__(
        self,
        result: WorkPromotionResult | None = None,
        exc: Exception | None = None,
    ) -> None:
        self.result = result or WorkPromotionResult()
        self.exc = exc
        self.call_kwargs: dict[str, object] | None = None

    def promote_fanza_works(self, **kwargs: object) -> WorkPromotionResult:
        self.call_kwargs = kwargs
        if self.exc is not None:
            raise self.exc
        return self.result


def patch_promotion_service(
    monkeypatch: pytest.MonkeyPatch,
    service: FakePromotionService,
) -> None:
    monkeypatch.setattr(runner_module, "_build_promotion_service", lambda _session: service)


def test_runner_rolls_back_by_default_and_passes_options(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = Mock(spec=Session)
    service = FakePromotionService(WorkPromotionResult(scanned_count=1, promoted_count=1))
    patch_promotion_service(monkeypatch, service)

    result = run_fanza_work_promotion(
        session,
        limit=25,
        offset=5,
        dry_run=False,
        commit=False,
        continue_on_error=False,
    )

    assert result.mode == "rollback"
    assert result.promotion_result.promoted_count == 1
    assert service.call_kwargs == {
        "limit": 25,
        "offset": 5,
        "dry_run": False,
        "continue_on_error": False,
    }
    session.rollback.assert_called_once_with()
    session.commit.assert_not_called()


def test_runner_commits_only_when_requested_and_no_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = Mock(spec=Session)
    patch_promotion_service(monkeypatch, FakePromotionService(WorkPromotionResult()))

    result = run_fanza_work_promotion(session, commit=True)

    assert result.mode == "commit"
    session.commit.assert_called_once_with()
    session.rollback.assert_not_called()


def test_runner_rolls_back_commit_request_when_failures_exist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = Mock(spec=Session)
    patch_promotion_service(
        monkeypatch,
        FakePromotionService(WorkPromotionResult(failed_count=1)),
    )

    result = run_fanza_work_promotion(session, commit=True)

    assert result.mode == "rollback-due-to-errors"
    session.rollback.assert_called_once_with()
    session.commit.assert_not_called()


def test_runner_dry_run_always_rolls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    session = Mock(spec=Session)
    service = FakePromotionService(WorkPromotionResult())
    patch_promotion_service(monkeypatch, service)

    result = run_fanza_work_promotion(session, dry_run=True)

    assert result.mode == "dry-run"
    assert service.call_kwargs["dry_run"] is True
    session.rollback.assert_called_once_with()
    session.commit.assert_not_called()


def test_runner_rejects_dry_run_commit_without_transaction() -> None:
    session = Mock(spec=Session)

    with pytest.raises(ValueError, match="dry-run"):
        run_fanza_work_promotion(session, dry_run=True, commit=True)

    session.rollback.assert_not_called()
    session.commit.assert_not_called()


def test_runner_rolls_back_on_unhandled_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    session = Mock(spec=Session)
    patch_promotion_service(monkeypatch, FakePromotionService(exc=RuntimeError("boom")))

    with pytest.raises(RuntimeError, match="boom"):
        run_fanza_work_promotion(session)

    session.rollback.assert_called_once_with()
    session.commit.assert_not_called()


def test_runner_constructs_repository_and_service_graph(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = Mock(spec=Session)
    constructed: list[tuple[str, object]] = []

    class FakeFieldObservationRepository:
        def __init__(self, received_session: Session) -> None:
            constructed.append(("field_observations", received_session))

    class FakeSourceRecordRepository:
        def __init__(self, received_session: Session) -> None:
            constructed.append(("source_records", received_session))

    class FakeWorkRepository:
        def __init__(self, received_session: Session) -> None:
            constructed.append(("works", received_session))

    class FakeWorkExternalIdRepository:
        def __init__(self, received_session: Session) -> None:
            constructed.append(("work_external_ids", received_session))

    class FakeWorkPromotionService:
        def __init__(
            self,
            *,
            field_observations: FakeFieldObservationRepository,
            source_records: FakeSourceRecordRepository,
            works: FakeWorkRepository,
            work_external_ids: FakeWorkExternalIdRepository,
        ) -> None:
            constructed.append(
                (
                    "promotion",
                    (field_observations, source_records, works, work_external_ids),
                )
            )

        def promote_fanza_works(self, **_kwargs: object) -> WorkPromotionResult:
            return WorkPromotionResult()

    monkeypatch.setattr(
        runner_module,
        "FieldObservationRepository",
        FakeFieldObservationRepository,
    )
    monkeypatch.setattr(runner_module, "SourceRecordRepository", FakeSourceRecordRepository)
    monkeypatch.setattr(runner_module, "WorkRepository", FakeWorkRepository)
    monkeypatch.setattr(
        runner_module,
        "WorkExternalIdRepository",
        FakeWorkExternalIdRepository,
    )
    monkeypatch.setattr(runner_module, "WorkPromotionService", FakeWorkPromotionService)

    run_fanza_work_promotion(session)

    assert [name for name, _value in constructed] == [
        "field_observations",
        "source_records",
        "works",
        "work_external_ids",
        "promotion",
    ]
