from unittest.mock import Mock

from typer.testing import CliRunner

from jav_metadatahub.cli import app
from jav_metadatahub.runners.fanza_work_promotion import FanzaWorkPromotionRunResult
from jav_metadatahub.services.work_promotion import WorkPromotionError, WorkPromotionResult

runner = CliRunner()


def make_run_result(
    *,
    mode: str = "rollback",
    failed_count: int = 0,
    errors: list[WorkPromotionError] | None = None,
) -> FanzaWorkPromotionRunResult:
    return FanzaWorkPromotionRunResult(
        mode=mode,  # type: ignore[arg-type]
        promotion_result=WorkPromotionResult(
            scanned_count=2,
            promoted_count=2 - failed_count,
            skipped_count=0,
            duplicate_count=1,
            failed_count=failed_count,
            created_work_count=1,
            created_external_id_count=3,
            updated_work_count=1,
            conflict_count=0,
            invalid_field_count=0,
            errors=errors or [],
        ),
    )


def patch_cli_dependencies(
    monkeypatch,
    result: FanzaWorkPromotionRunResult | None = None,
) -> tuple[Mock, Mock]:
    session = Mock()
    session_local = Mock(return_value=session)
    run = Mock(return_value=result or make_run_result())
    monkeypatch.setattr("jav_metadatahub.cli.SessionLocal", session_local)
    monkeypatch.setattr("jav_metadatahub.cli.run_fanza_work_promotion", run)
    return session_local, run


def test_cli_promotes_works_with_default_rollback_options(monkeypatch) -> None:
    session_local, run = patch_cli_dependencies(monkeypatch)

    result = runner.invoke(app, ["fanza-promote-works"])

    assert result.exit_code == 0
    assert "mode: rollback" in result.output
    assert "scanned_count: 2" in result.output
    assert "promoted_count: 2" in result.output
    assert "created_external_id_count: 3" in result.output
    run.assert_called_once_with(
        session_local.return_value,
        limit=100,
        offset=0,
        dry_run=False,
        commit=False,
        continue_on_error=True,
    )
    session_local.return_value.close.assert_called_once_with()


def test_cli_passes_commit_dry_run_and_error_options(monkeypatch) -> None:
    session_local, run = patch_cli_dependencies(monkeypatch, make_run_result(mode="commit"))

    result = runner.invoke(
        app,
        [
            "fanza-promote-works",
            "--limit",
            "25",
            "--offset",
            "5",
            "--commit",
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
        continue_on_error=False,
    )


def test_cli_dry_run_commit_fails_before_session_creation(monkeypatch) -> None:
    session_local, run = patch_cli_dependencies(monkeypatch)

    result = runner.invoke(app, ["fanza-promote-works", "--dry-run", "--commit"])

    assert result.exit_code == 1
    assert "--dry-run cannot be combined with --commit" in result.output
    session_local.assert_not_called()
    run.assert_not_called()


def test_cli_outputs_errors_and_returns_failure_exit_code(monkeypatch) -> None:
    error = WorkPromotionError(
        entity_id=123,
        error_class="ValueError",
        error_message="bad observations",
    )
    session_local, _run = patch_cli_dependencies(
        monkeypatch,
        make_run_result(mode="rollback-due-to-errors", failed_count=1, errors=[error]),
    )

    result = runner.invoke(app, ["fanza-promote-works", "--commit"])

    assert result.exit_code == 1
    assert "mode: rollback-due-to-errors" in result.output
    assert "failed_count: 1" in result.output
    assert "errors_count: 1" in result.output
    assert "entity_id=123" in result.output
    assert "error_class=ValueError" in result.output
    assert "error_message=bad observations" in result.output
    session_local.return_value.close.assert_called_once_with()


def test_cli_closes_session_when_runner_raises(monkeypatch) -> None:
    session = Mock()
    session_local = Mock(return_value=session)
    run = Mock(side_effect=RuntimeError("boom"))
    monkeypatch.setattr("jav_metadatahub.cli.SessionLocal", session_local)
    monkeypatch.setattr("jav_metadatahub.cli.run_fanza_work_promotion", run)

    result = runner.invoke(app, ["fanza-promote-works"])

    assert result.exit_code == 1
    assert "Error: boom" in result.output
    session.close.assert_called_once_with()
