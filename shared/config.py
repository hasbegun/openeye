"""Shared configuration loader for all services."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class NATSConfig(BaseSettings):
    """NATS connection configuration."""
    model_config = SettingsConfigDict(env_prefix="NATS_")

    url: str = "nats://nats:4222"


class DatabaseConfig(BaseSettings):
    """PostgreSQL configuration."""
    model_config = SettingsConfigDict(env_prefix="DB_")

    host: str = "postgres"
    port: int = 5432
    user: str = "openeye"
    password: str = "openeye_dev"
    database: str = "openeye"

    @property
    def dsn(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"

    @property
    def async_dsn(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


class RedisConfig(BaseSettings):
    """Redis configuration (optional)."""
    model_config = SettingsConfigDict(env_prefix="REDIS_")

    url: str = "redis://redis:6379/0"


class ModelConfig(BaseSettings):
    """LLM/Vision model configuration."""
    model_config = SettingsConfigDict(env_prefix="MODEL_")

    provider: str = "ollama"
    model: str = "llava"
    api_base: str = "http://host.docker.internal:11434"
    api_key: Optional[str] = None
    temperature: float = 0.1
    max_tokens: int = 500


class GuardrailsConfig(BaseSettings):
    """Guardrails policy configuration."""
    model_config = SettingsConfigDict(env_prefix="GUARDRAILS_")

    max_resolution_width: int = 1920
    max_resolution_height: int = 1080
    max_file_size_mb: int = 5
    strip_metadata: bool = True
    rate_limit_per_source: float = 2.0
    severity_min: int = 0
    severity_max: int = 10
    max_description_length: int = 500
    pii_redaction: bool = True
    false_positive_window: int = 60
    false_positive_threshold: float = 0.8


class AlertConfig(BaseSettings):
    """Alerter configuration."""
    model_config = SettingsConfigDict(env_prefix="ALERT_")

    severity_threshold: int = 6
    dedup_window_seconds: int = 30
    webhook_urls: str = ""  # Comma-separated URLs
    webhook_retry_count: int = 3
    webhook_retry_delay: float = 1.0

    @property
    def webhook_url_list(self) -> list[str]:
        if not self.webhook_urls:
            return []
        return [url.strip() for url in self.webhook_urls.split(",") if url.strip()]


class IngestorConfig(BaseSettings):
    """Ingestor configuration for video source management."""
    model_config = SettingsConfigDict(env_prefix="INGESTOR_")

    sources: str = ""  # Comma-separated RTSP URLs or device indices (e.g. "0,rtsp://cam1/stream")
    fps: float = 1.0  # Frames per second to extract
    jpeg_quality: int = 85  # JPEG encoding quality (0-100)
    max_width: int = 1280  # Resize frames wider than this
    reconnect_delay: float = 5.0  # Seconds to wait before reconnecting on failure

    @property
    def source_list(self) -> list[str]:
        if not self.sources:
            return []
        return [s.strip() for s in self.sources.split(",") if s.strip()]


class ServiceConfig(BaseSettings):
    """Base service configuration."""
    model_config = SettingsConfigDict(env_prefix="OPENEYE_", protected_namespaces=("settings_",))

    service_name: str = "openeye"
    version: str = "0.1.0"
    debug: bool = False
    log_level: str = "INFO"

    nats: NATSConfig = NATSConfig()
    database: DatabaseConfig = DatabaseConfig()
    redis: RedisConfig = RedisConfig()
    model: ModelConfig = ModelConfig()
    guardrails: GuardrailsConfig = GuardrailsConfig()
    alert: AlertConfig = AlertConfig()
    ingestor: IngestorConfig = IngestorConfig()
