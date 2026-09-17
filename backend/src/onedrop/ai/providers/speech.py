"""OpenAI-compatible speech-to-text adapter."""

from __future__ import annotations

import time
from typing import Any

import httpx

from onedrop.ai.providers.base import ALLOWED_AUDIO_MIME, ProviderUsage, TranscriptOutcome
from onedrop.config import Settings
from onedrop.errors import ProviderError, UnsupportedMediaError
from onedrop.logging import get_logger

logger = get_logger(__name__)
PROVIDER_NAME = "openai-compatible-stt"

EXTENSION_BY_MIME: dict[str, str] = {
    "audio/ogg": "ogg",
    "audio/oga": "oga",
    "audio/mpeg": "mp3",
    "audio/mp4": "m4a",
    "audio/m4a": "m4a",
    "audio/wav": "wav",
    "audio/x-wav": "wav",
}


class OpenAiSpeechToTextProvider:
    """Posts audio to an OpenAI-compatible `/audio/transcriptions` endpoint."""

    name = PROVIDER_NAME

    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        if not settings.stt_api_key:
            raise ProviderError("STT_API_KEY is not configured")
        self._settings = settings
        self._client = client

    async def transcribe(
        self, audio: bytes, mime_type: str, *, language: str | None = None
    ) -> TranscriptOutcome:
        if mime_type not in ALLOWED_AUDIO_MIME:
            raise UnsupportedMediaError(f"unsupported audio type: {mime_type}")
        url = f"{self._settings.stt_base_url.rstrip('/')}/audio/transcriptions"
        headers = {"Authorization": f"Bearer {self._settings.stt_api_key}"}
        extension = EXTENSION_BY_MIME.get(mime_type, "ogg")
        files = {"file": (f"voice.{extension}", audio, mime_type)}
        data: dict[str, str] = {"model": self._settings.stt_model}
        if language:
            data["language"] = language
        timeout = self._settings.ai_request_timeout_seconds

        started = time.perf_counter()
        try:
            if self._client is not None:
                response = await self._client.post(
                    url, headers=headers, files=files, data=data, timeout=timeout
                )
            else:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.post(url, headers=headers, files=files, data=data)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.warning("ai.stt_http_error", status=exc.response.status_code)
            raise ProviderError("speech-to-text provider returned an error") from exc
        except httpx.HTTPError as exc:
            logger.warning("ai.stt_transport_error", error_type=type(exc).__name__)
            raise ProviderError("speech-to-text provider is unreachable") from exc
        duration_ms = int((time.perf_counter() - started) * 1000)

        payload: dict[str, Any] = response.json()
        text = payload.get("text")
        if not isinstance(text, str) or not text.strip():
            raise ProviderError("speech-to-text provider returned an empty transcript")
        return TranscriptOutcome(
            text=text.strip(),
            language=payload.get("language") if isinstance(payload.get("language"), str) else language,
            usage=ProviderUsage(
                provider=PROVIDER_NAME,
                model=self._settings.stt_model,
                input_tokens=0,
                output_tokens=max(1, len(text) // 4),
                cost_micro=0,
                duration_ms=duration_ms,
            ),
        )
