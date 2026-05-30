"""Unit tests for shared Pydantic schemas."""

import pytest
from datetime import datetime
from pydantic import ValidationError

from shared.schemas import (
    FrameMessage,
    AnalysisResult,
    AlertMessage,
    GuardrailViolation,
    HealthResponse,
)


class TestFrameMessage:
    def test_valid_frame(self):
        frame = FrameMessage(
            frame_id="test-123",
            source_id="webcam-1",
            source_type="webcam",
            image_base64="base64data",
        )
        assert frame.frame_id == "test-123"
        assert frame.source_type == "webcam"
        assert frame.timestamp is not None

    def test_missing_required_fields(self):
        with pytest.raises(ValidationError):
            FrameMessage(frame_id="test-123")

    def test_optional_dimensions(self):
        frame = FrameMessage(
            frame_id="test-123",
            source_id="webcam-1",
            source_type="webcam",
            image_base64="base64data",
            width=1920,
            height=1080,
        )
        assert frame.width == 1920
        assert frame.height == 1080


class TestAnalysisResult:
    def test_valid_result(self):
        result = AnalysisResult(
            frame_id="frame-1",
            source_id="webcam-1",
            description="A person walking",
            severity=0,
            is_alert=False,
            tags=["person"],
        )
        assert result.severity == 0
        assert result.is_alert is False

    def test_severity_bounds(self):
        with pytest.raises(ValidationError):
            AnalysisResult(
                frame_id="frame-1",
                source_id="webcam-1",
                description="test",
                severity=11,
                is_alert=False,
            )

        with pytest.raises(ValidationError):
            AnalysisResult(
                frame_id="frame-1",
                source_id="webcam-1",
                description="test",
                severity=-1,
                is_alert=False,
            )

    def test_description_max_length(self):
        with pytest.raises(ValidationError):
            AnalysisResult(
                frame_id="frame-1",
                source_id="webcam-1",
                description="x" * 501,
                severity=5,
                is_alert=False,
            )

    def test_alert_with_tags(self):
        result = AnalysisResult(
            frame_id="frame-1",
            source_id="webcam-1",
            description="Person with weapon detected",
            severity=9,
            is_alert=True,
            tags=["weapon", "violence"],
        )
        assert result.is_alert is True
        assert "weapon" in result.tags


class TestAlertMessage:
    def test_valid_alert(self):
        alert = AlertMessage(
            alert_id="alert-1",
            frame_id="frame-1",
            source_id="webcam-1",
            description="Weapon detected",
            severity=9,
            tags=["weapon"],
        )
        assert alert.alert_id == "alert-1"
        assert alert.severity == 9

    def test_optional_thumbnail(self):
        alert = AlertMessage(
            alert_id="alert-1",
            frame_id="frame-1",
            source_id="webcam-1",
            description="Weapon detected",
            severity=9,
        )
        assert alert.thumbnail_base64 is None


class TestGuardrailViolation:
    def test_valid_violation(self):
        violation = GuardrailViolation(
            violation_id="v-1",
            frame_id="frame-1",
            violation_type="input",
            rule="max_file_size",
            details="Frame exceeds 5MB limit",
            action_taken="rejected",
        )
        assert violation.violation_type == "input"
        assert violation.action_taken == "rejected"

    def test_output_violation(self):
        violation = GuardrailViolation(
            violation_id="v-2",
            violation_type="output",
            rule="severity_bounds",
            details="Severity 15 clamped to 10",
            action_taken="clamped",
        )
        assert violation.frame_id is None
        assert violation.action_taken == "clamped"


class TestHealthResponse:
    def test_health_response(self):
        health = HealthResponse(service="gateway")
        assert health.service == "gateway"
        assert health.status == "ok"
        assert health.version == "0.1.0"
        assert isinstance(health.timestamp, datetime)
