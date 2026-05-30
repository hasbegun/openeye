"""Unit tests for shared configuration loader."""

import os
import pytest

from shared.config import (
    NATSConfig,
    DatabaseConfig,
    ModelConfig,
    GuardrailsConfig,
    AlertConfig,
    ServiceConfig,
)


class TestNATSConfig:
    def test_defaults(self):
        config = NATSConfig()
        assert config.url == "nats://nats:4222"

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("NATS_URL", "nats://custom:4222")
        config = NATSConfig()
        assert config.url == "nats://custom:4222"


class TestDatabaseConfig:
    def test_defaults(self):
        config = DatabaseConfig()
        assert config.host == "postgres"
        assert config.port == 5432
        assert config.user == "openeye"

    def test_dsn(self):
        config = DatabaseConfig()
        assert "postgresql://openeye:openeye_dev@postgres:5432/openeye" == config.dsn

    def test_async_dsn(self):
        config = DatabaseConfig()
        assert "postgresql+asyncpg://openeye:openeye_dev@postgres:5432/openeye" == config.async_dsn

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("DB_HOST", "mydb.example.com")
        monkeypatch.setenv("DB_PORT", "5433")
        config = DatabaseConfig()
        assert config.host == "mydb.example.com"
        assert config.port == 5433


class TestModelConfig:
    def test_defaults(self):
        config = ModelConfig()
        assert config.provider == "ollama"
        assert config.model == "llava"
        assert config.api_base == "http://host.docker.internal:11434"
        assert config.api_key is None

    def test_byok_config(self, monkeypatch):
        monkeypatch.setenv("MODEL_PROVIDER", "openai")
        monkeypatch.setenv("MODEL_MODEL", "gpt-4o")
        monkeypatch.setenv("MODEL_API_KEY", "sk-test123")
        config = ModelConfig()
        assert config.provider == "openai"
        assert config.model == "gpt-4o"
        assert config.api_key == "sk-test123"


class TestGuardrailsConfig:
    def test_defaults(self):
        config = GuardrailsConfig()
        assert config.max_resolution_width == 1920
        assert config.max_resolution_height == 1080
        assert config.max_file_size_mb == 5
        assert config.strip_metadata is True
        assert config.pii_redaction is True
        assert config.severity_min == 0
        assert config.severity_max == 10

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("GUARDRAILS_MAX_FILE_SIZE_MB", "10")
        monkeypatch.setenv("GUARDRAILS_PII_REDACTION", "false")
        config = GuardrailsConfig()
        assert config.max_file_size_mb == 10
        assert config.pii_redaction is False


class TestAlertConfig:
    def test_defaults(self):
        config = AlertConfig()
        assert config.severity_threshold == 6
        assert config.dedup_window_seconds == 30
        assert config.webhook_url_list == []

    def test_webhook_parsing(self, monkeypatch):
        monkeypatch.setenv("ALERT_WEBHOOK_URLS", "http://a.com/hook, http://b.com/hook")
        config = AlertConfig()
        assert len(config.webhook_url_list) == 2
        assert config.webhook_url_list[0] == "http://a.com/hook"
        assert config.webhook_url_list[1] == "http://b.com/hook"

    def test_empty_webhooks(self):
        config = AlertConfig()
        assert config.webhook_url_list == []
