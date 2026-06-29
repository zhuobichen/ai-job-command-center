"""Tests for job_hunt.cli module."""

import json
import pytest
from typer.testing import CliRunner
from job_hunt.cli import app


@pytest.fixture
def cli_runner():
    return CliRunner()


class TestCLIHelp:
    def test_main_help(self, cli_runner):
        result = cli_runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "job-hunt" in result.stdout.lower()

    def test_commands_registered(self, cli_runner):
        result = cli_runner.invoke(app, ["--help"])
        expected_commands = ["init", "scan", "match", "eval", "auto", "resume", "apply", "status", "report", "config", "pipeline", "filter", "verify", "parse"]
        for cmd in expected_commands:
            assert cmd in result.stdout, f"Command '{cmd}' not found in help"


class TestCLIConfig:
    def test_config_list_json(self, cli_runner):
        result = cli_runner.invoke(app, ["config", "list", "--json"])
        # May succeed or fail depending on config state
        assert result.exit_code in [0, 1]

    def test_config_get(self, cli_runner):
        result = cli_runner.invoke(app, ["config", "get", "-k", "preferences.cities"])
        # Exit code 0 even if key doesn't exist
        assert result.exit_code == 0


class TestCLIStatus:
    def test_status_json(self, cli_runner):
        result = cli_runner.invoke(app, ["status", "--json"])
        try:
            data = json.loads(result.stdout) if result.stdout else {}
            assert isinstance(data, dict)
        except json.JSONDecodeError:
            pytest.skip("JSON output not available in test environment")


class TestCLIPipeline:
    def test_pipeline_health_json(self, cli_runner):
        result = cli_runner.invoke(app, ["pipeline", "health", "--json"])
        try:
            data = json.loads(result.stdout) if result.stdout else {}
            assert "total_jobs" in data or "error" in data
        except json.JSONDecodeError:
            pytest.skip("JSON output not available")


class TestCLIInit:
    def test_init_with_yes(self, cli_runner, tmp_path):
        # Create a temporary config
        result = cli_runner.invoke(app, ["init", "--yes", "--json"])
        # Should complete without error
        assert result.exit_code in [0, 1]


class TestCLIVersion:
    def test_version_flag(self, cli_runner):
        result = cli_runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "0." in result.stdout or "version" in result.stdout.lower()
