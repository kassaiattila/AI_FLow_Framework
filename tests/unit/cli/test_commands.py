"""
@test_registry:
    suite: cli-unit
    component: cli.commands
    covers:
        - src/aiflow/cli/commands/skill.py
        - src/aiflow/cli/commands/dev.py
    phase: 6
    priority: medium
    estimated_duration_ms: 400
    requires_services: []
    tags: [cli, typer, commands, skill, dev]
"""

from typer.testing import CliRunner

from aiflow.cli.main import app

runner = CliRunner()


class TestSkillCommands:
    """Verify the skill command group has expected subcommands."""

    def test_skill_help(self):
        result = runner.invoke(app, ["skill", "--help"])
        assert result.exit_code == 0
        assert "list" in result.output
        assert "install" in result.output

    def test_skill_list(self):
        result = runner.invoke(app, ["skill", "list"])
        assert result.exit_code == 0

    def test_skill_install_requires_path(self):
        result = runner.invoke(app, ["skill", "install"])
        assert result.exit_code != 0


class TestDevCommands:
    """Verify the dev command group has expected subcommands."""

    def test_dev_help(self):
        result = runner.invoke(app, ["dev", "--help"])
        assert result.exit_code == 0

    def test_dev_group_registered(self):
        """Dev command group is accessible via the main app."""
        result = runner.invoke(app, ["--help"])
        assert "dev" in result.output
