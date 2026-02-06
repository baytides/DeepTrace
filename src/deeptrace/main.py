"""Root CLI application."""

import typer

from deeptrace import __version__

app = typer.Typer(
    name="deeptrace",
    help="Cold case investigation platform.",
    rich_markup_mode="rich",
    no_args_is_help=True,
)


@app.callback(invoke_without_command=True)
def main(
    version: bool = typer.Option(False, "--version", "-V", help="Show version and exit."),
) -> None:
    """Cold case investigation platform."""
    if version:
        typer.echo(f"deeptrace {__version__}")
        raise typer.Exit()
