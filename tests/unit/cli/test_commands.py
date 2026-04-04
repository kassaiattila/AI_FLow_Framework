"""
@test_registry:
    suite: cli-unit
    component: cli.commands
    covers:
        - src/aiflow/cli/commands/workflow.py
        - src/aiflow/cli/commands/skill.py
        - src/aiflow/cli/commands/prompt.py
        - src/aiflow/cli/commands/eval_cmd.py
        - src/aiflow/cli/commands/dev.py
    phase: 6
    priority: medium
    estimated_duration_ms: 800
    requires_services: []
    tags: [cli, typer, commands, workflow, skill, prompt, eval, dev]
"""
from typer.testing import CliRunner

from aiflow.cli.main import app

runner = CliRunner()


class TestWorkflowCommands:
    """Verify the workflow command group has expected subcommands."""

    def test_workflow_help(self):
        result = runner.invoke(app, ["workflow", "--help"])
        assert result.exit_code == 0
        assert "list" in result.output
        assert "run" in result.output

    def test_workflow_list(self):
        result = runner.invoke(app, ["workflow", "list"])
        assert result.exit_code == 0

    def test_workflow_run_requires_name(self):
        result = runner.invoke(app, ["workflow", "run"])
        # Should fail because name argument is required
        assert result.exit_code != 0

    def test_workflow_run_with_name(self):
        result = runner.invoke(app, ["workflow", "run", "my-workflow"])
        assert result.exit_code == 0
        assert "my-workflow" in result.output


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


class TestPromptCommands:
    """Verify the prompt command group has expected subcommands."""

    def test_prompt_help(self):
        result = runner.invoke(app, ["prompt", "--help"])
        assert result.exit_code == 0
        assert "list" in result.output
        assert "sync" in result.output

    def test_prompt_list(self):
        result = runner.invoke(app, ["prompt", "list"])
        assert result.exit_code == 0


class TestEvalCommands:
    """Verify the eval command group has expected subcommands."""

    def test_eval_help(self):
        result = runner.invoke(app, ["eval", "--help"])
        assert result.exit_code == 0

    def test_eval_group_registered(self):
        """Eval command group is accessible via the main app."""
        result = runner.invoke(app, ["--help"])
        assert "eval" in result.output


class TestDevCommands:
    """Verify the dev command group has expected subcommands."""

    def test_dev_help(self):
        result = runner.invoke(app, ["dev", "--help"])
        assert result.exit_code == 0

    def test_dev_group_registered(self):
        """Dev command group is accessible via the main app."""
        result = runner.invoke(app, ["--help"])
        assert "dev" in result.output
