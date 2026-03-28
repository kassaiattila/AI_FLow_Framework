"""AIFlow CLI - prompt management commands.

Usage:
    aiflow prompt list
    aiflow prompt sync --label dev
    aiflow prompt diff
    aiflow prompt promote --from dev --to staging
"""

from typing import Optional

import structlog
import typer

__all__ = ["app"]

logger = structlog.get_logger(__name__)

app = typer.Typer(help="Manage prompts (Langfuse SSOT sync, promote, diff).")


@app.command("list")
def list_prompts() -> None:
    """List all local and remote prompts."""
    logger.info("cli_prompt_list")
    typer.echo("Local prompts:")
    typer.echo("  (none found in prompts/)")
    typer.echo("")
    typer.echo("Remote prompts (Langfuse):")
    typer.echo("  [placeholder] Langfuse connection not configured.")


@app.command("sync")
def sync_prompts(
    label: str = typer.Option(
        "dev",
        "--label",
        "-l",
        help="Target label/environment for sync (dev, staging, production).",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be synced without making changes.",
    ),
) -> None:
    """Sync local prompts to Langfuse."""
    logger.info("cli_prompt_sync", label=label, dry_run=dry_run)

    prefix = "[DRY RUN] " if dry_run else ""
    typer.echo(f"{prefix}Syncing prompts to Langfuse with label '{label}'...")
    typer.echo(f"  {prefix}[placeholder] Prompt sync not yet implemented.")
    typer.echo("  Expected: read prompts/ YAML -> push to Langfuse -> tag with label.")


@app.command("diff")
def diff_prompts(
    name: Optional[str] = typer.Option(
        None,
        "--name",
        "-n",
        help="Specific prompt name to diff (default: all).",
    ),
) -> None:
    """Compare local prompts vs remote (Langfuse)."""
    logger.info("cli_prompt_diff", name=name)

    target = f"prompt '{name}'" if name else "all prompts"
    typer.echo(f"Diffing {target}: local vs Langfuse remote...")
    typer.echo("  [placeholder] Diff not yet implemented.")
    typer.echo("  Expected: fetch remote versions -> compare text -> show unified diff.")


@app.command("promote")
def promote_prompts(
    from_label: str = typer.Option(
        ...,
        "--from",
        help="Source label (e.g., dev).",
    ),
    to_label: str = typer.Option(
        ...,
        "--to",
        help="Target label (e.g., staging, production).",
    ),
    name: Optional[str] = typer.Option(
        None,
        "--name",
        "-n",
        help="Specific prompt name to promote (default: all).",
    ),
) -> None:
    """Promote prompts from one label to another."""
    logger.info("cli_prompt_promote", from_label=from_label, to_label=to_label, name=name)

    target = f"prompt '{name}'" if name else "all prompts"
    typer.echo(f"Promoting {target} from '{from_label}' to '{to_label}'...")
    typer.echo("  [placeholder] Promotion not yet implemented.")
    typer.echo("  Expected: copy Langfuse prompt version -> re-tag with target label.")
