"""AIFlow CLI - evaluation commands.

Named eval_cmd.py to avoid shadowing Python's built-in ``eval``.

Usage:
    aiflow eval run --skill <name>
    aiflow eval report --skill <name>
"""


import structlog
import typer

__all__ = ["app"]

logger = structlog.get_logger(__name__)

app = typer.Typer(help="Run evaluations and view reports.")


@app.command("run")
def run_eval(
    skill: str = typer.Option(
        ...,
        "--skill",
        "-s",
        help="Skill name to evaluate.",
    ),
    dataset: str | None = typer.Option(
        None,
        "--dataset",
        "-d",
        help="Path to evaluation dataset (JSON/YAML).",
    ),
    concurrency: int = typer.Option(
        4,
        "--concurrency",
        "-c",
        help="Number of parallel evaluation workers.",
    ),
) -> None:
    """Run an evaluation suite for a skill."""
    logger.info("cli_eval_run", skill=skill, dataset=dataset, concurrency=concurrency)
    typer.echo(f"Running evaluation for skill '{skill}'...")

    if dataset:
        typer.echo(f"  Dataset: {dataset}")
    else:
        typer.echo("  Dataset: (using skill's default test cases)")

    typer.echo(f"  Concurrency: {concurrency}")
    typer.echo("  [placeholder] Evaluation execution not yet implemented.")
    typer.echo("  Expected: load test cases -> run skill -> score outputs -> store results.")


@app.command("report")
def eval_report(
    skill: str = typer.Option(
        ...,
        "--skill",
        "-s",
        help="Skill name to report on.",
    ),
    run_id: str | None = typer.Option(
        None,
        "--run-id",
        help="Specific evaluation run ID (default: latest).",
    ),
    fmt: str = typer.Option(
        "table",
        "--format",
        "-f",
        help="Output format: table, json, csv.",
    ),
) -> None:
    """Show evaluation report for a skill."""
    logger.info("cli_eval_report", skill=skill, run_id=run_id, format=fmt)

    if fmt not in ("table", "json", "csv"):
        typer.echo(f"Error: format must be 'table', 'json', or 'csv', got '{fmt}'", err=True)
        raise typer.Exit(code=1)

    target_run = f"run '{run_id}'" if run_id else "latest run"
    typer.echo(f"Evaluation report for skill '{skill}' ({target_run}):")
    typer.echo(f"  Format: {fmt}")
    typer.echo("  [placeholder] Report generation not yet implemented.")
    typer.echo("  Expected: load results from DB -> compute aggregate scores -> render.")
