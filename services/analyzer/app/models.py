"""LiteLLM integration for vision model inference."""

import json
import logging
from typing import Optional

import litellm

from shared.config import ModelConfig
from shared.schemas import AnalysisResult
from app.prompts import SYSTEM_PROMPT, USER_PROMPT

logger = logging.getLogger("analyzer.models")


def _build_model_name(config: ModelConfig) -> str:
    """Build LiteLLM model string from config."""
    if config.provider == "ollama":
        return f"ollama/{config.model}"
    elif config.provider == "openai":
        return config.model
    elif config.provider == "anthropic":
        return f"anthropic/{config.model}"
    else:
        return f"{config.provider}/{config.model}"


async def analyze_image(
    image_base64: str,
    frame_id: str,
    source_id: str,
    config: ModelConfig,
    custom_prompt: Optional[str] = None,
) -> AnalysisResult:
    """Send image to vision model via LiteLLM and return structured result."""
    model_name = _build_model_name(config)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": custom_prompt or USER_PROMPT},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"},
                },
            ],
        },
    ]

    logger.info(f"Calling {model_name} for frame {frame_id}")

    response = await litellm.acompletion(
        model=model_name,
        messages=messages,
        api_base=config.api_base,
        api_key=config.api_key,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
    )

    raw_content = response.choices[0].message.content
    logger.debug(f"Raw model response: {raw_content}")

    parsed = _parse_response(raw_content, frame_id, source_id)
    return parsed


def _extract_json(raw: str) -> Optional[str]:
    """Extract JSON from model response, handling markdown fences and extra text."""
    import re

    # Try raw string first
    stripped = raw.strip()
    if stripped.startswith("{"):
        return stripped

    # Try extracting from markdown code fences
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", stripped, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Try finding first { to last }
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start != -1 and end != -1 and end > start:
        return stripped[start : end + 1]

    return None


def _parse_response(raw: str, frame_id: str, source_id: str) -> AnalysisResult:
    """Parse model JSON response into AnalysisResult."""
    json_str = _extract_json(raw) if raw else None

    if json_str:
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            data = None
    else:
        data = None

    if data is None:
        logger.warning(f"Failed to parse JSON from model response: {raw[:200] if raw else 'None'}")
        return AnalysisResult(
            frame_id=frame_id,
            source_id=source_id,
            description="[Parse error] Model returned invalid JSON",
            severity=0,
            is_alert=False,
            tags=["error"],
        )

    return AnalysisResult(
        frame_id=frame_id,
        source_id=source_id,
        description=str(data.get("description", "No description"))[:500],
        severity=max(0, min(10, int(data.get("severity", 0)))),
        is_alert=bool(data.get("is_alert", False)),
        tags=data.get("tags", []),
    )
