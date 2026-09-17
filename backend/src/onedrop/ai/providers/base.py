"""Provider protocols and transport-neutral result types."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol, runtime_checkable

from onedrop.ai.schemas import CaptureResult, MealFields

ALLOWED_AUDIO_MIME: frozenset[str] = frozenset(
    {"audio/ogg", "audio/oga", "audio/mpeg", "audio/mp4", "audio/m4a", "audio/wav", "audio/x-wav"}
)
ALLOWED_IMAGE_MIME: frozenset[str] = frozenset({"image/jpeg", "image/png", "image/webp"})


@dataclass(frozen=True, slots=True)
class ProviderUsage:
    """What one provider call cost. Persisted in `ai_operations`."""

    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_micro: int = 0
    duration_ms: int = 0


@dataclass(frozen=True, slots=True)
class CaptureContext:
    """Everything a provider may know about the user. No credentials, no ids."""

    timezone: str
    locale: str
    base_currency: str
    now_local: datetime
    habits: tuple[str, ...] = field(default=())


@dataclass(frozen=True, slots=True)
class ParseOutcome:
    result: CaptureResult
    usage: ProviderUsage


@dataclass(frozen=True, slots=True)
class TranscriptOutcome:
    text: str
    language: str | None
    usage: ProviderUsage


@dataclass(frozen=True, slots=True)
class MealVisionOutcome:
    fields: MealFields
    confidence: float
    usage: ProviderUsage


@runtime_checkable
class StructuredLLMProvider(Protocol):
    """Turns text into a validated `CaptureResult`. Returns JSON only."""

    name: str

    async def parse(self, text: str, context: CaptureContext) -> ParseOutcome: ...


@runtime_checkable
class SpeechToTextProvider(Protocol):
    """Transcribes a voice message."""

    name: str

    async def transcribe(
        self, audio: bytes, mime_type: str, *, language: str | None = None
    ) -> TranscriptOutcome: ...


@runtime_checkable
class VisionProvider(Protocol):
    """Estimates nutrition from a food photo. Values are always approximate."""

    name: str

    async def analyze_meal(
        self, image: bytes, mime_type: str, context: CaptureContext
    ) -> MealVisionOutcome: ...
