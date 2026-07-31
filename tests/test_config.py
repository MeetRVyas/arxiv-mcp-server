"""Tests for arxiv_mcp.config."""

from __future__ import annotations

import pytest

from arxiv_mcp.config import Settings


class TestSettings:
    def test_defaults(self, monkeypatch):
        monkeypatch.delenv("PORT", raising=False)
        monkeypatch.delenv("HOST", raising=False)
        settings = Settings(_env_file=None)
        assert settings.port == 8000
        assert settings.host == "0.0.0.0"
        assert settings.log_level == "INFO"

    def test_env_vars_are_read(self, monkeypatch):
        monkeypatch.setenv("PORT", "9999")
        monkeypatch.setenv("HOST", "127.0.0.1")
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        settings = Settings(_env_file=None)
        assert settings.port == 9999
        assert settings.host == "127.0.0.1"
        assert settings.log_level == "DEBUG"

    def test_invalid_log_level_raises(self, monkeypatch):
        monkeypatch.setenv("LOG_LEVEL", "NOT_A_LEVEL")
        with pytest.raises(ValueError):
            Settings(_env_file=None)

    def test_log_level_case_insensitive(self, monkeypatch):
        monkeypatch.setenv("LOG_LEVEL", "debug")
        settings = Settings(_env_file=None)
        assert settings.log_level == "DEBUG"

    def test_allowed_origins_list_parsing(self, monkeypatch):
        monkeypatch.setenv("ALLOWED_ORIGINS", "https://a.com, https://b.com")
        settings = Settings(_env_file=None)
        assert settings.allowed_origins_list == ["https://a.com", "https://b.com"]

    def test_allowed_origins_empty_by_default(self, monkeypatch):
        monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
        settings = Settings(_env_file=None)
        assert settings.allowed_origins_list == []

    def test_has_semantic_scholar_key(self, monkeypatch):
        monkeypatch.setenv("SEMANTIC_SCHOLAR_API_KEY", "abc123")
        settings = Settings(_env_file=None)
        assert settings.has_semantic_scholar_key is True

    def test_no_semantic_scholar_key(self, monkeypatch):
        monkeypatch.delenv("SEMANTIC_SCHOLAR_API_KEY", raising=False)
        settings = Settings(_env_file=None)
        assert settings.has_semantic_scholar_key is False

    def test_get_settings_is_cached(self):
        from arxiv_mcp.config import get_settings

        assert get_settings() is get_settings()
