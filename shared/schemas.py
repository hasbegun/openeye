"""Shared Pydantic schemas for inter-service communication."""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)

from pydantic import BaseModel, Field


class Severity(int, Enum):
    """Severity levels for analysis results."""
    NONE = 0
    LOW = 1
    MEDIUM = 5
    HIGH = 8
    CRITICAL = 10


class FrameMessage(BaseModel):
    """Message published to NATS frames.new subject."""
    frame_id: str = Field(..., description="Unique frame identifier (UUID)")
    source_id: str = Field(..., description="Source identifier (stream/upload ID)")
    source_type: str = Field(..., description="'webcam', 'video_file', or 'rtsp'")
    timestamp: datetime = Field(default_factory=_utcnow)
    image_base64: str = Field(..., description="Base64-encoded JPEG image data")
    width: Optional[int] = None
    height: Optional[int] = None


class AnalysisResult(BaseModel):
    """Structured response from the vision model."""
    frame_id: str = Field(..., description="Reference to the analyzed frame")
    source_id: str = Field(..., description="Source identifier")
    timestamp: datetime = Field(default_factory=_utcnow)
    description: str = Field(..., max_length=500, description="Scene description")
    severity: int = Field(..., ge=0, le=10, description="Danger severity 0-10")
    is_alert: bool = Field(default=False, description="Whether this triggers an alert")
    tags: list[str] = Field(default_factory=list, description="Detected categories")


class AlertMessage(BaseModel):
    """Alert published to NATS alerts.new subject."""
    alert_id: str = Field(..., description="Unique alert identifier (UUID)")
    frame_id: str = Field(..., description="Reference to the triggering frame")
    source_id: str = Field(..., description="Source identifier")
    timestamp: datetime = Field(default_factory=_utcnow)
    description: str = Field(..., description="Scene description from model")
    severity: int = Field(..., ge=0, le=10)
    tags: list[str] = Field(default_factory=list)
    thumbnail_base64: Optional[str] = Field(None, description="Compressed frame thumbnail")


class GuardrailViolation(BaseModel):
    """Logged when a guardrail rule is triggered."""
    violation_id: str
    frame_id: Optional[str] = None
    violation_type: str = Field(..., description="'input' or 'output'")
    rule: str = Field(..., description="Which guardrail rule was triggered")
    details: str = Field(..., description="Human-readable violation description")
    timestamp: datetime = Field(default_factory=_utcnow)
    action_taken: str = Field(..., description="'rejected', 'clamped', 'redacted'")


class HealthResponse(BaseModel):
    """Standard health check response."""
    service: str
    status: str = "ok"
    version: str = "0.1.0"
    timestamp: datetime = Field(default_factory=_utcnow)
