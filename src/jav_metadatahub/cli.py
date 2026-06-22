from typing import Annotated

import typer

from jav_metadatahub import __version__
from jav_metadatahub.db.session import SessionLocal
from jav_metadatahub.runners.fanza_observation_ingestion import (
    FanzaObservationIngestionRunResult,
    run_fanza_observation_ingestion,
)

app = typer.Typer(
    name="javhub",
    help="JAV-MetadataHub command line interface.",
    no_args_is_help=True,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"javhub {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            callback=_version_callback,
            help="Show the javhub version and exit.",
            is_eager=True,
        ),
    ] = False,
) -> None:
    """Project utilities for public metadata workflows."""


@app.command("fanza-ingest-observations")
def fanza_ingest_observations(
    limit: Annotated[
        int,
        typer.Option("--limit", min=1, help="Maximum source_records to process."),
    ] = 100,
    offset: Annotated[
        int,
        typer.Option("--offset", min=0, help="Offset for source_records pagination."),
    ] = 0,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Read records and report counts without writing."),
    ] = False,
    commit: Annotated[
        bool,
        typer.Option("--commit", help="Commit only when the batch has no failures."),
    ] = False,
    idempotent: Annotated[
        bool,
        typer.Option(
            "--idempotent/--no-idempotent",
            help="Use observation-level idempotency checks.",
        ),
    ] = True,
    continue_on_error: Annotated[
        bool,
        typer.Option(
            "--continue-on-error/--stop-on-error",
            help="Continue after per-record failures.",
        ),
    ] = True,
) -> None:
    """Batch-ingest FANZA work source_records into field_observations."""
    if dry_run and commit:
        typer.secho("Error: --dry-run cannot be combined with --commit.", err=True, fg="red")
        raise typer.Exit(code=1)

    session = SessionLocal()
    try:
        run_result = run_fanza_observation_ingestion(
            session,
            limit=limit,
            offset=offset,
            dry_run=dry_run,
            commit=commit,
            idempotent=idempotent,
            continue_on_error=continue_on_error,
        )
    except Exception as exc:
        typer.secho(f"Error: {exc}", err=True, fg="red")
        raise typer.Exit(code=1) from exc
    finally:
        session.close()

    _echo_fanza_ingestion_summary(run_result)
    if run_result.batch_result.failed_count > 0:
        raise typer.Exit(code=1)


def _echo_fanza_ingestion_summary(result: FanzaObservationIngestionRunResult) -> None:
    batch = result.batch_result
    typer.echo(f"mode: {result.mode}")
    typer.echo(f"processed_count: {batch.processed_count}")
    typer.echo(f"succeeded_count: {batch.succeeded_count}")
    typer.echo(f"failed_count: {batch.failed_count}")
    typer.echo(f"observation_count: {batch.observation_count}")
    typer.echo(f"skipped_count: {batch.skipped_count}")
    typer.echo(f"errors_count: {len(batch.errors)}")

    if not batch.errors:
        return

    typer.echo("errors:")
    for error in batch.errors:
        typer.echo(
            "- "
            f"source_record_id={error.source_record_id} "
            f"source_key={error.source_key} "
            f"error_class={error.error_class} "
            f"error_message={error.error_message}"
        )
