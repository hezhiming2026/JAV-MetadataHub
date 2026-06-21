from typing import Annotated

import typer

from jav_metadatahub import __version__

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
