from unittest.mock import Mock

from typer.testing import CliRunner

from jav_metadatahub.cli import app
from jav_metadatahub.runners.fanza_observation_ingestion import (
    FanzaObservationIngestionRunResult,
)
from jav_metadatahub.services.fanza_batch_ingestion import (
    FanzaObservationBatchError,
    FanzaObservationBatchResult,
)

runner = CliRunner()


def make_run_result(
    *,
    mode: str = "rollback",
    failed_count: int = 0,
    errors: list[FanzaObservationBatchError] | None = None,
) -> FanzaObservationIngestionRunResult:
    return FanzaObservationIngestionRunResult(
        mode=mode,  # type: ignore[arg-type]
        batch_result=FanzaObservationBatchResult(
            processed_count=2,
            succeeded_count=2 - failed_count,
            failed_count=failed_count,
            observation_count=11,
            skipped_count=1,
            errors=errors or [],
        ),
    )


def patch_cli_dependencies(
    monkeypatch,
    result: FanzaObservationIngestionRunResult | None = None,
) -> tuple[Mock, Mock]:
    session = Mock()
    session_local = Mock(return_value=session)
    run = Mock(return_value=result or make_run_result())
    monkeypatch.setattr("jav_metadatahub.cli.SessionLocal", session_local)
    monkeypatch.setattr("jav_metadatahub.cli.run_fanza_observation_ingestion", run)
    return session_local, run


def test_cli_runs_with_default_rollback_options(monkeypatch) -> None:
    session_local, run = patch_cli_dependencies(monkeypatch)

    result = runner.invoke(app, ["fanza-ingest-observations"])

    assert result.exit_code == 0
    assert "mode: rollback" in result.output
    assert "processed_count: 2" in result.output
    assert "observation_count: 11" in result.output
    session = session_local.return_value
    run.assert_called_once_with(
        session,
        limit=100,
        offset=0,
        dry_run=False,
        commit=False,
        idempotent=True,
        continue_on_error=True,
    )
    session.close.assert_called_once_with()


def test_cli_passes_commit_dry_run_idempotency_and_error_options(monkeypatch) -> None:
    session_local, run = patch_cli_dependencies(monkeypatch, make_run_result(mode="commit"))

    result = runner.invoke(
        app,
        [
            "fanza-ingest-observations",
            "--limit",
            "25",
            "--offset",
            "5",
            "--commit",
            "--no-idempotent",
            "--stop-on-error",
        ],
    )

    assert result.exit_code == 0
    assert "mode: commit" in result.output
    run.assert_called_once_with(
        session_local.return_value,
        limit=25,
        offset=5,
        dry_run=False,
        commit=True,
        idempotent=False,
        continue_on_error=False,
    )
    session_local.return_value.close.assert_called_once_with()


def test_cli_dry_run_commit_fails_before_session_creation(monkeypatch) -> None:
    session_local, run = patch_cli_dependencies(monkeypatch)

    result = runner.invoke(app, ["fanza-ingest-observations", "--dry-run", "--commit"])

    assert result.exit_code == 1
    assert "--dry-run cannot be combined with --commit" in result.output
    session_local.assert_not_called()
    run.assert_not_called()


def test_cli_outputs_errors_and_returns_failure_exit_code(monkeypatch) -> None:
    error = FanzaObservationBatchError(
        source_record_id=123,
        source_key="cid-001",
        error_class="ValueError",
        error_message="bad raw_json",
    )
    session_local, _run = patch_cli_dependencies(
        monkeypatch,
        make_run_result(mode="rollback-due-to-errors", failed_count=1, errors=[error]),
    )

    result = runner.invoke(app, ["fanza-ingest-observations", "--commit"])

    assert result.exit_code == 1
    assert "mode: rollback-due-to-errors" in result.output
    assert "failed_count: 1" in result.output
    assert "errors_count: 1" in result.output
    assert "source_record_id=123" in result.output
    assert "source_key=cid-001" in result.output
    assert "error_class=ValueError" in result.output
    assert "error_message=bad raw_json" in result.output
    session_local.return_value.close.assert_called_once_with()


def test_cli_closes_session_when_runner_raises(monkeypatch) -> None:
    session = Mock()
    session_local = Mock(return_value=session)
    run = Mock(side_effect=RuntimeError("boom"))
    monkeypatch.setattr("jav_metadatahub.cli.SessionLocal", session_local)
    monkeypatch.setattr("jav_metadatahub.cli.run_fanza_observation_ingestion", run)

    result = runner.invoke(app, ["fanza-ingest-observations"])

    assert result.exit_code == 1
    assert "Error: boom" in result.output
    session.close.assert_called_once_with()
