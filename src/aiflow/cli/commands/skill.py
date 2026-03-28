"""AIFlow CLI - skill commands.

Usage:
    aiflow skill list
    aiflow skill install <path>
    aiflow skill validate <name>
    aiflow skill uninstall <name>
"""

import structlog
import typer

__all__ = ["app"]

logger = structlog.get_logger(__name__)

app = typer.Typer(help="Manage AI skills (install, validate, list).")


@app.command("list")
def list_skills() -> None:
    """List all installed skills."""
    logger.info("cli_skill_list")
    typer.echo("Installed skills:")
    typer.echo("  (none)")
    typer.echo("")
    typer.echo("Install skills with: aiflow skill install <path-to-manifest>")


@app.command("install")
def install_skill(
    path: str = typer.Argument(..., help="Path to skill manifest or package."),
) -> None:
    """Install a skill from a manifest or package path."""
    logger.info("cli_skill_install", path=path)
    typer.echo(f"Installing skill from '{path}'...")
    typer.echo("  [placeholder] Skill installation not yet implemented.")
    typer.echo("  Expected: validate manifest -> copy to skills/ -> register in catalog.")


@app.command("validate")
def validate_skill(
    name: str = typer.Argument(..., help="Skill name to validate."),
) -> None:
    """Validate a skill manifest and dependencies."""
    logger.info("cli_skill_validate", skill=name)
    typer.echo(f"Validating skill '{name}'...")
    typer.echo("  [placeholder] Manifest validation not yet implemented.")
    typer.echo("  Checks: schema, required fields, dependency resolution, test suite.")


@app.command("uninstall")
def uninstall_skill(
    name: str = typer.Argument(..., help="Skill name to uninstall."),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force removal without confirmation.",
    ),
) -> None:
    """Uninstall a skill by name."""
    logger.info("cli_skill_uninstall", skill=name, force=force)

    if not force:
        confirmed = typer.confirm(f"Uninstall skill '{name}'?")
        if not confirmed:
            typer.echo("Aborted.")
            raise typer.Exit()

    typer.echo(f"Uninstalling skill '{name}'...")
    typer.echo("  [placeholder] Skill removal not yet implemented.")
