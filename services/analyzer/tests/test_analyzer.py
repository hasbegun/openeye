"""Unit tests for analyzer service — prompt construction and response parsing."""

from pathlib import Path

import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock

from shared.config import ModelConfig
from shared.schemas import AnalysisResult

# Add analyzer root to sys.path so its `app` package is importable
import sys
_SERVICE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_SERVICE_ROOT))

# Remove any cached `app` module from other services
for key in list(sys.modules.keys()):
    if key == "app" or key.startswith("app."):
        del sys.modules[key]

from app.models import _parse_response, _build_model_name, analyze_image as _analyze_image
import app.models as _models


class TestParseResponse:
    """Test the _parse_response function."""

    def test_valid_json_response(self):
        raw = json.dumps({
            "description": "A person walking in a parking lot",
            "severity": 2,
            "is_alert": False,
            "tags": ["person", "normal"],
        })
        result = _parse_response(raw, "frame-1", "cam-1")
        assert result.description == "A person walking in a parking lot"
        assert result.severity == 2
        assert result.is_alert is False
        assert "person" in result.tags

    def test_high_severity_alert(self):
        raw = json.dumps({
            "description": "Person holding a gun",
            "severity": 9,
            "is_alert": True,
            "tags": ["person", "weapon", "gun"],
        })
        result = _parse_response(raw, "frame-2", "cam-1")
        assert result.severity == 9
        assert result.is_alert is True
        assert "weapon" in result.tags

    def test_severity_clamped_to_max(self):
        raw = json.dumps({
            "description": "test",
            "severity": 15,
            "is_alert": True,
            "tags": [],
        })
        result = _parse_response(raw, "frame-3", "cam-1")
        assert result.severity == 10

    def test_severity_clamped_to_min(self):
        raw = json.dumps({
            "description": "test",
            "severity": -5,
            "is_alert": False,
            "tags": [],
        })
        result = _parse_response(raw, "frame-4", "cam-1")
        assert result.severity == 0

    def test_invalid_json_returns_error_result(self):
        result = _parse_response("not json at all", "frame-5", "cam-1")
        assert "Parse error" in result.description
        assert result.severity == 0
        assert result.is_alert is False
        assert "error" in result.tags

    def test_description_truncated_at_500(self):
        raw = json.dumps({
            "description": "x" * 600,
            "severity": 1,
            "is_alert": False,
            "tags": [],
        })
        result = _parse_response(raw, "frame-6", "cam-1")
        assert len(result.description) == 500


class TestBuildModelName:
    def test_ollama_provider(self):
        config = ModelConfig(provider="ollama", model="llava")
        assert _build_model_name(config) == "ollama/llava"

    def test_openai_provider(self):
        config = ModelConfig(provider="openai", model="gpt-4o")
        assert _build_model_name(config) == "gpt-4o"

    def test_anthropic_provider(self):
        config = ModelConfig(provider="anthropic", model="claude-3-5-sonnet-20241022")
        assert _build_model_name(config) == "anthropic/claude-3-5-sonnet-20241022"


class TestAnalyzeImage:
    @pytest.mark.asyncio
    async def test_calls_litellm(self):
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content=json.dumps({
                "description": "Empty hallway",
                "severity": 0,
                "is_alert": False,
                "tags": ["empty", "normal"],
            })))
        ]

        with patch.object(_models.litellm, "acompletion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            config = ModelConfig(provider="ollama", model="llava")
            result = await _analyze_image(
                image_base64="fakebase64data",
                frame_id="frame-test",
                source_id="cam-test",
                config=config,
            )

        assert isinstance(result, AnalysisResult)
        assert result.description == "Empty hallway"
        assert result.severity == 0
        mock_llm.assert_called_once()
