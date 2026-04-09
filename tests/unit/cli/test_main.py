"""
@test_registry:
    suite: cli-unit
    component: cli.main
    covers: [src/aiflow/cli/main.py]
    phase: 6
    priority: high
    estimated_duration_ms: 500
    requires_services: []
    tags: [cli, typer, main, version]
"""

from typer.testing import CliRunner

from aiflow.cli.main import app

runner = CliRunner()


class TestCLIAppExists:
    """Verify the Typer app is properly configured."""

    def test_app_is_typer_instance(self):
        import typer

        assert isinstance(app, typer.Typer)

    def test_app_name(self):
        assert app.info.name == "aiflow"


class TestVersionFlag:
    """Verify --version flag prints version and exits."""

    def test_version_flag_long(self):
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "AIFlow v" in result.output

    def test_version_flag_short(self):
        result = runner.invoke(app, ["-v"])
        assert result.exit_code == 0
        assert "AIFlow v" in result.output


class TestHelpText:
    """Verify help output shows expected information."""

    def test_help_shows_description(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "AIFlow" in result.output

    def test_help_shows_subcommands(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "skill" in result.output
        assert "dev" in result.output

    def test_no_args_shows_help(self):
        result = runner.invoke(app, [])
        # no_args_is_help=True causes typer to show help and exit with code 0 or 2
        assert result.exit_code in (0, 2)


class TestSubcommandInvocation:
    """Verify key subcommands can be invoked without error."""

    def test_skill_list_runs(self):
        result = runner.invoke(app, ["skill", "list"])
        assert result.exit_code == 0
        assert "skill" in result.output.lower() or "Installed" in result.output
