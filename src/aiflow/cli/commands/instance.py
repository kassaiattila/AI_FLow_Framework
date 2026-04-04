"""AIFlow CLI - instance commands.

Usage:
    aiflow instance list [--customer <customer>] [--skill <skill>]
    aiflow instance load <yaml-path>
    aiflow instance show <instance-name>
    aiflow instance enable <instance-name>
    aiflow instance disable <instance-name>
    aiflow instance validate <yaml-path>
"""

from pathlib import Path

import structlog
import typer

from aiflow.skills.instance_loader import load_all_instances, load_instance_config
from aiflow.skills.instance_registry import InstanceRegistry

__all__ = ["app"]

logger = structlog.get_logger(__name__)

app = typer.Typer(help="Manage skill instances (load, list, enable/disable).")

# Module-level registry (will be replaced by DI in production)
_registry = InstanceRegistry()


@app.command("list")
def list_instances(
    customer: str | None = typer.Option(None, "--customer", "-c", help="Filter by customer."),
    skill: str | None = typer.Option(None, "--skill", "-s", help="Filter by skill template."),
) -> None:
    """List loaded skill instances."""
    if customer:
        instances = _registry.list_by_customer(customer)
    elif skill:
        instances = _registry.list_by_skill(skill)
    else:
        instances = _registry.list_all()

    if not instances:
        typer.echo("No instances loaded.")
        typer.echo("Load instances with: aiflow instance load <path-to-yaml>")
        return

    typer.echo(f"{'INSTANCE':<30} {'SKILL':<25} {'CUSTOMER':<10} {'ENABLED':<8} {'MODEL'}")
    typer.echo("-" * 90)
    for inst in instances:
        typer.echo(
            f"{inst.instance_name:<30} "
            f"{inst.skill_template:<25} "
            f"{inst.customer:<10} "
            f"{'yes' if inst.enabled else 'no':<8} "
            f"{inst.models.default}"
        )


@app.command("load")
def load_instance(
    path: str = typer.Argument(..., help="Path to instance YAML or deployment.yaml."),
) -> None:
    """Load instance config(s) from YAML file."""
    file_path = Path(path)

    if file_path.name == "deployment.yaml":
        instances = load_all_instances(file_path)
        for config in instances:
            if not _registry.has(config.instance_name):
                _registry.register(config)
                typer.echo(f"  Loaded: {config.instance_name} ({config.skill_template})")
            else:
                typer.echo(f"  Skipped (already loaded): {config.instance_name}")
        typer.echo(f"\n{len(instances)} instance(s) loaded.")
    else:
        config = load_instance_config(file_path)
        if _registry.has(config.instance_name):
            typer.echo(f"Instance '{config.instance_name}' already loaded.")
            raise typer.Exit(1)
        _registry.register(config)
        typer.echo(f"Loaded: {config.instance_name} ({config.skill_template})")


@app.command("show")
def show_instance(
    name: str = typer.Argument(..., help="Instance name to show."),
) -> None:
    """Show detailed instance configuration."""
    config = _registry.get_or_none(name)
    if config is None:
        typer.echo(f"Instance '{name}' not found.")
        raise typer.Exit(1)

    typer.echo(f"Instance:       {config.instance_name}")
    typer.echo(f"Display Name:   {config.display_name}")
    typer.echo(f"Skill Template: {config.skill_template}")
    typer.echo(f"Version:        {config.version}")
    typer.echo(f"Customer:       {config.customer}")
    typer.echo(f"Enabled:        {config.enabled}")
    typer.echo("")
    typer.echo("Models:")
    typer.echo(f"  Default:      {config.models.default}")
    typer.echo(f"  Fallback:     {config.models.fallback}")
    if config.models.per_agent:
        for agent, model in config.models.per_agent.items():
            typer.echo(f"  {agent}: {model}")
    typer.echo("")
    typer.echo("Prompts:")
    typer.echo(f"  Namespace:    {config.prompts.namespace}")
    typer.echo(f"  Label:        {config.prompts.label}")
    typer.echo("")
    typer.echo("Budget:")
    typer.echo(f"  Monthly:      ${config.budget.monthly_usd:.2f}")
    typer.echo(f"  Per run:      ${config.budget.per_run_usd:.2f}")
    typer.echo(f"  Alert at:     {config.budget.alert_threshold:.0%}")
    typer.echo("")
    typer.echo("SLA:")
    typer.echo(f"  Target:       {config.sla.target_seconds}s")
    typer.echo(f"  P95:          {config.sla.p95_target_seconds}s")
    typer.echo(f"  Availability: {config.sla.availability:.1%}")
    typer.echo("")
    typer.echo("Routing:")
    typer.echo(f"  Input:        {config.routing.input_channel}")
    typer.echo(f"  Output:       {config.routing.output_channel}")
    if config.routing.queue_name:
        typer.echo(f"  Queue:        {config.routing.queue_name}")


@app.command("validate")
def validate_instance(
    path: str = typer.Argument(..., help="Path to instance YAML to validate."),
) -> None:
    """Validate an instance config YAML without loading it."""
    file_path = Path(path)
    try:
        config = load_instance_config(file_path)
        typer.echo(
            f"Valid: {config.instance_name} (skill={config.skill_template}, customer={config.customer})"
        )
    except (FileNotFoundError, ValueError) as exc:
        typer.echo(f"Invalid: {exc}", err=True)
        raise typer.Exit(1) from exc


@app.command("enable")
def enable_instance(
    name: str = typer.Argument(..., help="Instance name to enable."),
) -> None:
    """Enable a loaded instance."""
    config = _registry.get_or_none(name)
    if config is None:
        typer.echo(f"Instance '{name}' not found.")
        raise typer.Exit(1)
    config.enabled = True
    typer.echo(f"Instance '{name}' enabled.")


@app.command("disable")
def disable_instance(
    name: str = typer.Argument(..., help="Instance name to disable."),
) -> None:
    """Disable a loaded instance."""
    config = _registry.get_or_none(name)
    if config is None:
        typer.echo(f"Instance '{name}' not found.")
        raise typer.Exit(1)
    config.enabled = False
    typer.echo(f"Instance '{name}' disabled.")
