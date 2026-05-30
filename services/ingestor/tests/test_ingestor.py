"""Unit tests for ingestor capture module."""

import sys
import asyncio
import base64
from pathlib import Path
from unittest.mock import patch, MagicMock

_SERVICE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_SERVICE_ROOT))

for key in list(sys.modules.keys()):
    if key == "app" or key.startswith("app."):
        del sys.modules[key]

import pytest
import numpy as np

from shared.config import IngestorConfig
from app.capture import _resize_frame, _encode_frame, capture_frames


class TestResizeFrame:
    def test_no_resize_if_smaller(self):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        result = _resize_frame(frame, max_width=1280)
        assert result.shape == (480, 640, 3)

    def test_resize_if_wider(self):
        frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        result = _resize_frame(frame, max_width=1280)
        assert result.shape[1] == 1280
        # Aspect ratio preserved: 1080 * (1280/1920) = 720
        assert result.shape[0] == 720

    def test_square_resize(self):
        frame = np.zeros((2000, 2000, 3), dtype=np.uint8)
        result = _resize_frame(frame, max_width=500)
        assert result.shape == (500, 500, 3)


class TestEncodeFrame:
    def test_returns_valid_base64(self):
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        b64 = _encode_frame(frame, quality=50)
        # Should be valid base64
        decoded = base64.b64decode(b64)
        # JPEG magic bytes
        assert decoded[:2] == b"\xff\xd8"

    def test_quality_affects_size(self):
        frame = np.random.randint(0, 255, (200, 200, 3), dtype=np.uint8)
        low_q = _encode_frame(frame, quality=10)
        high_q = _encode_frame(frame, quality=95)
        assert len(low_q) < len(high_q)


class TestCaptureFrames:
    @pytest.mark.asyncio
    async def test_yields_frames_from_source(self):
        config = IngestorConfig(fps=10.0, jpeg_quality=50, max_width=640)
        stop_event = asyncio.Event()

        fake_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, fake_frame)

        frames_received = []

        with patch("app.capture.cv2.VideoCapture", return_value=mock_cap):
            async for frame_id, image_b64 in capture_frames("0", config, stop_event):
                frames_received.append((frame_id, image_b64))
                if len(frames_received) >= 3:
                    stop_event.set()

        assert len(frames_received) == 3
        for frame_id, image_b64 in frames_received:
            assert len(frame_id) == 36  # UUID
            decoded = base64.b64decode(image_b64)
            assert decoded[:2] == b"\xff\xd8"

        mock_cap.release.assert_called()

    @pytest.mark.asyncio
    async def test_reconnects_on_failure(self):
        config = IngestorConfig(fps=10.0, reconnect_delay=0.01)
        stop_event = asyncio.Event()

        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = False

        frames_received = []

        async def stop_after_delay():
            await asyncio.sleep(0.05)
            stop_event.set()

        with patch("app.capture.cv2.VideoCapture", return_value=mock_cap):
            task = asyncio.create_task(stop_after_delay())
            async for frame_id, image_b64 in capture_frames("0", config, stop_event):
                frames_received.append(frame_id)
            await task

        # No frames should be yielded since source never opened
        assert len(frames_received) == 0


class TestIngestorConfig:
    def test_source_list_parsing(self):
        config = IngestorConfig(sources="0,rtsp://cam1/stream,rtsp://cam2/stream")
        assert config.source_list == ["0", "rtsp://cam1/stream", "rtsp://cam2/stream"]

    def test_empty_sources(self):
        config = IngestorConfig(sources="")
        assert config.source_list == []

    def test_default_fps(self):
        config = IngestorConfig()
        assert config.fps == 1.0
