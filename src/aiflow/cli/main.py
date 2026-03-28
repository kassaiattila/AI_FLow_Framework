"""AIFlow CLI - main entry point."""

import typer

from aiflow._version import __version__

__all__ = ["app", "main"]

app = typer.Typer(
    name="aiflow",
    help="AIFlow - Enterprise AI Automation Framework",
    no_args_is_help=True,
)


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        typer.echo(f"AIFlow v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    """AIFlow - Enterprise AI Automation Framework."""


# Register sub-commands
from aiflow.cli.commands import workflow, skill, prompt, eval_cmd, dev, instance  # noqa: E402

app.add_typer(workflow.app, name="workflow")
app.add_typer(skill.app, name="skill")
app.add_typer(prompt.app, name="prompt")
app.add_typer(eval_cmd.app, name="eval")
app.add_typer(dev.app, name="dev")
app.add_typer(instance.app, name="instance")

if __name__ == "__main__":
    app()
