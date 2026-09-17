"""OpenRouter-compatible structured LLM and vision adapters."""

from __future__ import annotations

import base64
import json
import time
from typing import Any

import httpx
from pydantic import ValidationError

from onedrop.ai.prompts import (
    VISION_SYSTEM_PROMPT,
    build_system_prompt,
    build_user_prompt,
)
from onedrop.ai.providers.base import (
    ALLOWED_IMAGE_MIME,
    CaptureContext,
    MealVisionOutcome,
    ParseOutcome,
    ProviderUsage,
)
from onedrop.ai.schemas import MealFields, parse_capture_result
from onedrop.config import Settings
from onedrop.errors import ProviderError, UnsupportedMediaError
from onedrop.logging import get_logger

logger = get_logger(__name__)
PROVIDER_NAME = "openrouter"


def _strip_code_fence(content: str) -> str:
    text = content.strip()
    if text.startswith("```"):
        lines = [line for line in text.splitlines() if not line.startswith("```")]
        text = "\n".join(lines).strip()
    return text


def _usage_from_response(payload: dict[str, Any], model: str, duration_ms: int) -> ProviderUsage:
    usage = payload.get("usage") or {}
    return ProviderUsage(
        provider=PROVIDER_NAME,
        model=model,
        input_tokens=int(usage.get("prompt_tokens", 0) or 0),
        output_tokens=int(usage.get("completion_tokens", 0) or 0),
        cost_micro=int(round(float(usage.get("total_cost", 0) or 0) * 1_000_000)),
        duration_ms=duration_ms,
    )


def _first_message_content(payload: dict[str, Any]) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ProviderError("model response contained no choices")
    message = choices[0].get("message") or {}
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise ProviderError("model response contained no content")
    return content


class OpenRouterStructuredProvider:
    """Chat-completions adapter that requires JSON output."""

    name = PROVIDER_NAME

    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        if not settings.openrouter_api_key:
            raise ProviderError("OPENROUTER_API_KEY is not configured")
        self._settings = settings
        self._client = client

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._settings.openrouter_api_key}",
            "Content-Type": "application/json",
            "X-Title": "OneDrop",
        }

    async def _post(self, body: dict[str, Any]) -> dict[str, Any]:
        url = f"{self._settings.openrouter_base_url.rstrip('/')}/chat/completions"
        timeout = self._settings.ai_request_timeout_seconds
        try:
            if self._client is not None:
                response = await self._client.post(
                    url, json=body, headers=self._headers(), timeout=timeout
                )
            else:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.post(url, json=body, headers=self._headers())
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.warning("ai.provider_http_error", status=exc.response.status_code)
            raise ProviderError("AI provider returned an error") from exc
        except httpx.HTTPError as exc:
            logger.warning("ai.provider_transport_error", error_type=type(exc).__name__)
            raise ProviderError("AI provider is unreachable") from exc
        parsed: dict[str, Any] = response.json()
        return parsed

    async def parse(self, text: str, context: CaptureContext) -> ParseOutcome:
        body = {
            "model": self._settings.openrouter_model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": build_system_prompt()},
                {
                    "role": "user",
                    "content": build_user_prompt(
                        text=text,
                        timezone=context.timezone,
                        local_now=context.now_local.isoformat(timespec="minutes"),
                        base_currency=context.base_currency,
                        locale=context.locale,
                        habits=list(context.habits),
                    ),
                },
            ],
        }
        started = time.perf_counter()
        payload = await self._post(body)
        duration_ms = int((time.perf_counter() - started) * 1000)
        content = _strip_code_fence(_first_message_content(payload))
        try:
            raw = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ProviderError("model did not return valid JSON") from exc
        if not isinstance(raw, dict):
            raise ProviderError("model returned JSON that is not an object")
        try:
            result = parse_capture_result(raw)
        except ValidationError as exc:
            logger.warning("ai.schema_violation", error_count=len(exc.errors()))
            raise ProviderError("model output did not match the schema") from exc
        usage = _usage_from_response(payload, self._settings.openrouter_model, duration_ms)
        return ParseOutcome(result=result, usage=usage)


class OpenRouterVisionProvider(OpenRouterStructuredProvider):
    """Vision adapter estimating meal nutrition from an image."""

    async def analyze_meal(
        self, image: bytes, mime_type: str, context: CaptureContext
    ) -> MealVisionOutcome:
        if mime_type not in ALLOWED_IMAGE_MIME:
            raise UnsupportedMediaError(f"unsupported image type: {mime_type}")
        encoded = base64.b64encode(image).decode("ascii")
        body = {
            "model": self._settings.vision_model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": VISION_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Estimate the nutrition of this meal."},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime_type};base64,{encoded}"},
                        },
                    ],
                },
            ],
        }
        started = time.perf_counter()
        payload = await self._post(body)
        duration_ms = int((time.perf_counter() - started) * 1000)
        content = _strip_code_fence(_first_message_content(payload))
        try:
            raw = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ProviderError("vision model did not return valid JSON") from exc
        if not isinstance(raw, dict):
            raise ProviderError("vision model returned JSON that is not an object")
        confidence = float(raw.pop("confidence", 0.5) or 0.0)
        raw["estimated"] = True
        raw.setdefault("title", "Meal")
        try:
            fields = MealFields.model_validate(raw)
        except ValidationError as exc:
            raise ProviderError("vision output did not match the schema") from exc
        usage = _usage_from_response(payload, self._settings.vision_model, duration_ms)
        return MealVisionOutcome(
            fields=fields, confidence=min(max(confidence, 0.0), 1.0), usage=usage
        )
