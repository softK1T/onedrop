"""Provider selection. `fake` never appears in real mode and vice versa."""

from __future__ import annotations

from onedrop.ai.providers.base import (
    SpeechToTextProvider,
    StructuredLLMProvider,
    VisionProvider,
)
from onedrop.ai.providers.fake import (
    FakeSpeechToTextProvider,
    FakeStructuredLLMProvider,
    FakeVisionProvider,
)
from onedrop.ai.providers.openrouter import (
    OpenRouterStructuredProvider,
    OpenRouterVisionProvider,
)
from onedrop.ai.providers.speech import OpenAiSpeechToTextProvider
from onedrop.config import Settings, get_settings


def build_structured_provider(settings: Settings | None = None) -> StructuredLLMProvider:
    active = settings or get_settings()
    if active.ai_real_mode:
        return OpenRouterStructuredProvider(active)
    return FakeStructuredLLMProvider()


def build_stt_provider(settings: Settings | None = None) -> SpeechToTextProvider:
    active = settings or get_settings()
    if active.ai_real_mode:
        return OpenAiSpeechToTextProvider(active)
    return FakeSpeechToTextProvider()


def build_vision_provider(settings: Settings | None = None) -> VisionProvider:
    active = settings or get_settings()
    if active.ai_real_mode:
        return OpenRouterVisionProvider(active)
    return FakeVisionProvider()
