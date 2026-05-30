"""Input and output validation logic for the guardrails service."""

import base64
import io
import time
import logging
from collections import defaultdict
from typing import Optional

from PIL import Image

from shared.config import GuardrailsConfig
from shared.schemas import FrameMessage, AnalysisResult, GuardrailViolation

logger = logging.getLogger("guardrails.validators")


class RateLimiter:
    """Token-bucket rate limiter per source_id."""

    def __init__(self, max_rate: float):
        self._max_rate = max_rate  # frames per second
        self._last_time: dict[str, float] = defaultdict(float)
        self._min_interval = 1.0 / max_rate if max_rate > 0 else 0

    def allow(self, source_id: str) -> bool:
        now = time.monotonic()
        elapsed = now - self._last_time[source_id]
        if elapsed < self._min_interval:
            return False
        self._last_time[source_id] = now
        return True


class InputValidator:
    """Validates incoming frames before analysis."""

    def __init__(self, config: GuardrailsConfig):
        self.config = config
        self.rate_limiter = RateLimiter(config.rate_limit_per_source)

    def validate(self, frame: FrameMessage) -> Optional[GuardrailViolation]:
        """Validate a frame message. Returns violation if invalid, None if OK."""

        # Rate limiting
        if not self.rate_limiter.allow(frame.source_id):
            return GuardrailViolation(
                violation_id=f"rate-{frame.frame_id}",
                frame_id=frame.frame_id,
                violation_type="input",
                rule="rate_limit",
                details=f"Source {frame.source_id} exceeded {self.config.rate_limit_per_source} fps limit",
                action_taken="rejected",
            )

        # File size check (base64 → bytes ~ 3/4 of string length)
        raw_size = len(frame.image_base64) * 3 // 4
        max_bytes = self.config.max_file_size_mb * 1024 * 1024
        if raw_size > max_bytes:
            return GuardrailViolation(
                violation_id=f"size-{frame.frame_id}",
                frame_id=frame.frame_id,
                violation_type="input",
                rule="max_file_size",
                details=f"Image size {raw_size // 1024}KB exceeds {self.config.max_file_size_mb}MB limit",
                action_taken="rejected",
            )

        # Resolution check
        try:
            img_data = base64.b64decode(frame.image_base64)
            img = Image.open(io.BytesIO(img_data))
            width, height = img.size

            if width > self.config.max_resolution_width or height > self.config.max_resolution_height:
                return GuardrailViolation(
                    violation_id=f"res-{frame.frame_id}",
                    frame_id=frame.frame_id,
                    violation_type="input",
                    rule="max_resolution",
                    details=f"Image {width}x{height} exceeds max {self.config.max_resolution_width}x{self.config.max_resolution_height}",
                    action_taken="rejected",
                )
        except Exception as e:
            return GuardrailViolation(
                violation_id=f"decode-{frame.frame_id}",
                frame_id=frame.frame_id,
                violation_type="input",
                rule="image_decode",
                details=f"Failed to decode image: {str(e)[:200]}",
                action_taken="rejected",
            )

        return None


class OutputValidator:
    """Validates analysis results before delivery."""

    def __init__(self, config: GuardrailsConfig):
        self.config = config

    def validate(self, result: AnalysisResult) -> tuple[AnalysisResult, Optional[GuardrailViolation]]:
        """Validate and clamp analysis output. Returns (clamped_result, violation_or_none)."""
        violation = None
        clamped = result.model_copy()

        # Severity bounds
        if result.severity < self.config.severity_min:
            clamped.severity = self.config.severity_min
        elif result.severity > self.config.severity_max:
            clamped.severity = self.config.severity_max

        # Description length
        if len(result.description) > self.config.max_description_length:
            clamped.description = result.description[: self.config.max_description_length]
            violation = GuardrailViolation(
                violation_id=f"desc-{result.frame_id}",
                frame_id=result.frame_id,
                violation_type="output",
                rule="max_description_length",
                details=f"Description truncated from {len(result.description)} to {self.config.max_description_length} chars",
                action_taken="clamped",
            )

        # Consistency check: is_alert should match severity threshold
        if clamped.severity < 6 and clamped.is_alert:
            clamped.is_alert = False

        return clamped, violation
