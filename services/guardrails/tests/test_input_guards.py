"""Unit tests for guardrails input and output validation."""

import sys
import base64
import io
import time
from pathlib import Path

# Add guardrails root to sys.path
_SERVICE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_SERVICE_ROOT))

for key in list(sys.modules.keys()):
    if key == "app" or key.startswith("app."):
        del sys.modules[key]

import pytest
from PIL import Image

from shared.config import GuardrailsConfig
from shared.schemas import FrameMessage, AnalysisResult
from app.validators import InputValidator, OutputValidator, RateLimiter


def _make_jpeg_b64(width: int = 100, height: int = 100) -> str:
    """Generate a valid JPEG image as base64."""
    img = Image.new("RGB", (width, height), color="blue")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return base64.b64encode(buf.getvalue()).decode()


def _make_frame(image_b64: str = None, source_id: str = "cam-1") -> FrameMessage:
    if image_b64 is None:
        image_b64 = _make_jpeg_b64()
    return FrameMessage(
        frame_id="test-frame-1",
        source_id=source_id,
        source_type="webcam",
        image_base64=image_b64,
    )


class TestRateLimiter:
    def test_allows_first_request(self):
        limiter = RateLimiter(max_rate=2.0)
        assert limiter.allow("cam-1") is True

    def test_rejects_rapid_requests(self):
        limiter = RateLimiter(max_rate=1.0)
        assert limiter.allow("cam-1") is True
        assert limiter.allow("cam-1") is False

    def test_different_sources_independent(self):
        limiter = RateLimiter(max_rate=1.0)
        assert limiter.allow("cam-1") is True
        assert limiter.allow("cam-2") is True

    def test_allows_after_interval(self):
        limiter = RateLimiter(max_rate=100.0)  # 10ms interval
        assert limiter.allow("cam-1") is True
        time.sleep(0.015)
        assert limiter.allow("cam-1") is True


class TestInputValidator:
    def setup_method(self):
        self.config = GuardrailsConfig(
            max_resolution_width=1920,
            max_resolution_height=1080,
            max_file_size_mb=5,
            rate_limit_per_source=100.0,
        )
        self.validator = InputValidator(self.config)

    def test_valid_frame_passes(self):
        frame = _make_frame()
        violation = self.validator.validate(frame)
        assert violation is None

    def test_oversized_image_rejected(self):
        config = GuardrailsConfig(max_file_size_mb=0, rate_limit_per_source=100.0)
        validator = InputValidator(config)
        frame = _make_frame()
        violation = validator.validate(frame)
        assert violation is not None
        assert violation.rule == "max_file_size"
        assert violation.action_taken == "rejected"

    def test_over_resolution_rejected(self):
        config = GuardrailsConfig(
            max_resolution_width=50,
            max_resolution_height=50,
            rate_limit_per_source=100.0,
        )
        validator = InputValidator(config)
        frame = _make_frame(_make_jpeg_b64(100, 100))
        violation = validator.validate(frame)
        assert violation is not None
        assert violation.rule == "max_resolution"

    def test_invalid_base64_rejected(self):
        frame = _make_frame("not-valid-image-data")
        violation = self.validator.validate(frame)
        assert violation is not None
        assert violation.rule == "image_decode"

    def test_rate_limited_rejected(self):
        config = GuardrailsConfig(rate_limit_per_source=1.0)
        validator = InputValidator(config)
        frame = _make_frame()
        assert validator.validate(frame) is None
        violation = validator.validate(frame)
        assert violation is not None
        assert violation.rule == "rate_limit"


class TestOutputValidator:
    def setup_method(self):
        self.config = GuardrailsConfig(max_description_length=100)
        self.validator = OutputValidator(self.config)

    def test_valid_result_passes(self):
        result = AnalysisResult(
            frame_id="f1",
            source_id="cam-1",
            description="Normal scene",
            severity=3,
            is_alert=False,
            tags=["normal"],
        )
        clamped, violation = self.validator.validate(result)
        assert violation is None
        assert clamped.description == "Normal scene"

    def test_long_description_truncated(self):
        result = AnalysisResult(
            frame_id="f1",
            source_id="cam-1",
            description="x" * 200,
            severity=5,
            is_alert=False,
            tags=[],
        )
        clamped, violation = self.validator.validate(result)
        assert violation is not None
        assert violation.rule == "max_description_length"
        assert violation.action_taken == "clamped"
        assert len(clamped.description) == 100

    def test_alert_cleared_for_low_severity(self):
        result = AnalysisResult(
            frame_id="f1",
            source_id="cam-1",
            description="Seems fine",
            severity=2,
            is_alert=True,
            tags=[],
        )
        clamped, _ = self.validator.validate(result)
        assert clamped.is_alert is False

    def test_high_severity_alert_preserved(self):
        result = AnalysisResult(
            frame_id="f1",
            source_id="cam-1",
            description="Person with weapon",
            severity=8,
            is_alert=True,
            tags=["weapon"],
        )
        clamped, violation = self.validator.validate(result)
        assert violation is None
        assert clamped.is_alert is True
        assert clamped.severity == 8
