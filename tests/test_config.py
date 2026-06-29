"""Tests for job_hunt.utils.config module."""

import os
import pytest
from job_hunt.utils.config import Config


class TestConfig:
    def test_config_creation(self, temp_config):
        cfg = Config(str(temp_config))
        assert cfg.config_path == str(temp_config)

    def test_default_cities(self, temp_config):
        cfg = Config(str(temp_config))
        assert cfg.get("preferences", "cities") == "南宁,广州"

    def test_default_gxrc_enabled(self, temp_config):
        cfg = Config(str(temp_config))
        assert cfg.get("platforms", "gxrc") in (True, "true")

    def test_default_min_score(self, temp_config):
        cfg = Config(str(temp_config))
        assert cfg.get("advanced", "min_apply_score") in ("4.0", 4.0)

    def test_get_set_config(self, temp_config):
        cfg = Config(str(temp_config))
        cfg.set("test", "key", "value")
        assert cfg.get("test", "key") == "value"

    def test_get_all_section(self, temp_config):
        cfg = Config(str(temp_config))
        section = cfg.get_all("preferences")
        assert isinstance(section, dict)
        assert "cities" in section

    def test_is_configured_with_api_key(self, temp_config):
        cfg = Config(str(temp_config))
        cfg.set("ai", "api_key", "test-key")
        assert cfg.is_configured is True

    def test_is_configured_with_env_var(self, temp_config, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "env-key")
        cfg = Config(str(temp_config))
        assert cfg.is_configured is True

    def test_get_api_key_from_config(self, temp_config):
        cfg = Config(str(temp_config))
        cfg.set("ai", "api_key", "config-key")
        assert cfg.get_api_key() == "config-key"

    def test_get_api_key_from_env(self, temp_config, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "env-key")
        cfg = Config(str(temp_config))
        assert cfg.get_api_key() == "env-key"

    def test_keywords_property(self, temp_config):
        cfg = Config(str(temp_config))
        assert isinstance(cfg.keywords, str)

    def test_cities_property(self, temp_config):
        cfg = Config(str(temp_config))
        assert cfg.cities == "南宁,广州"
