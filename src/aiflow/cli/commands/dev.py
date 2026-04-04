"""AIFlow CLI - developer environment commands.

Usage:
    aiflow dev up
    aiflow dev down
    aiflow dev logs
"""

import subprocess

import structlog
import typer

__all__ = ["app"]

logger = structlog.get_logger(__name__)

app = typer.Typer(help="Manage local development environment (Docker services).")

_COMPOSE_FILE = "docker-compose.dev.yml"


def _run_compose(args: list[str], capture: bool = False) -> subprocess.CompletedProcess[str]:
    """Run a docker compose command with standard error handling."""
    cmd = ["docker", "compose", "-f", _COMPOSE_FILE, *args]
    logger.debug("cli_dev_compose", command=" ".join(cmd))
    try:
        return subprocess.run(
            cmd,
            check=True,
            capture_output=capture,
            text=True,
        )
    except FileNotFoundError:
        typer.echo("Error: 'docker' not found. Install Docker Desktop first.", err=True)
        raise typer.Exit(code=1)
    except subprocess.CalledProcessError as exc:
        typer.echo(f"Error: docker compose failed (exit {exc.returncode}).", err=True)
        if exc.stderr:
            typer.echo(exc.stderr, err=True)
        raise typer.Exit(code=exc.returncode)


@app.command("up")
def dev_up(
    detach: bool = typer.Option(
        True,
        "--detach/--no-detach",
        "-d",
        help="Run containers in the background.",
    ),
    build: bool = typer.Option(
        False,
        "--build",
        "-b",
        help="Rebuild images before starting.",
    ),
) -> None:
    """Start local development services (PostgreSQL, Redis, Langfuse)."""
    logger.info("cli_dev_up", detach=detach, build=build)
    typer.echo("Starting AIFlow development services...")

    args = ["up"]
    if detach:
        args.append("-d")
    if build:
        args.append("--build")

    _run_compose(args)
    typer.echo("Development services started.")


@app.command("down")
def dev_down(
    volumes: bool = typer.Option(
        False,
        "--volumes",
        "-v",
        help="Remove named volumes (WARNING: deletes data).",
    ),
) -> None:
    """Stop local development services."""
    logger.info("cli_dev_down", volumes=volumes)
    typer.echo("Stopping AIFlow development services...")

    args = ["down"]
    if volumes:
        args.append("-v")

    _run_compose(args)
    typer.echo("Development services stopped.")


@app.command("logs")
def dev_logs(
    service: str | None = typer.Argument(
        None,
        help="Specific service name (e.g., postgres, redis). Default: all.",
    ),
    follow: bool = typer.Option(
        False,
        "--follow",
        "-f",
        help="Follow log output (stream).",
    ),
    tail: int = typer.Option(
        100,
        "--tail",
        "-n",
        help="Number of lines to show from the end.",
    ),
) -> None:
    """Show logs for development services."""
    logger.info("cli_dev_logs", service=service, follow=follow, tail=tail)

    args = ["logs", f"--tail={tail}"]
    if follow:
        args.append("-f")
    if service:
        args.append(service)

    _run_compose(args)
