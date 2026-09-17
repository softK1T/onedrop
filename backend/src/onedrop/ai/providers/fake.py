"""Deterministic fake providers for tests and demo mode.

These never reach the network. They are selected only when
`AI_PROVIDER_MODE=fake`, so a production deployment with `real` mode can never
serve canned answers.
"""

from __future__ import annotations

import hashlib

from onedrop.ai.providers.base import (
    ALLOWED_AUDIO_MIME,
    ALLOWED_IMAGE_MIME,
    CaptureContext,
    MealVisionOutcome,
    ParseOutcome,
    ProviderUsage,
    TranscriptOutcome,
)
from onedrop.ai.providers.fake_rules import parse_text
from onedrop.ai.schemas import MealFields
from onedrop.errors import UnsupportedMediaError

FAKE_PROVIDER_NAME = "fake"
FAKE_PARSE_MODEL = "fake-rules-v1"
FAKE_STT_MODEL = "fake-stt-v1"
FAKE_VISION_MODEL = "fake-vision-v1"

DEMO_TRANSCRIPT = (
    "\u0417\u0430\u0432\u0442\u0440\u0430 \u0432 15:00 \u0432\u0441\u0442\u0440\u0435\u0447\u0430 \u0441 "
    "\u0410\u043d\u0434\u0440\u0435\u0435\u043c, \u043f\u043e\u0442\u0440\u0430\u0442\u0438\u043b 45 "
    "\u0437\u043b\u043e\u0442\u044b\u0445 \u043d\u0430 \u0442\u0430\u043a\u0441\u0438 \u0438 "
    "\u043d\u0443\u0436\u043d\u043e \u043e\u043f\u043b\u0430\u0442\u0438\u0442\u044c "
    "\u0438\u043d\u0442\u0435\u0440\u043d\u0435\u0442"
)

TRANSCRIPT_VARIANTS: tuple[str, ...] = (
    DEMO_TRANSCRIPT,
    "\u041f\u0440\u043e\u0431\u0435\u0436\u0430\u043b 5 \u043a\u043c \u0443\u0442\u0440\u043e\u043c",
    "\u0417\u0430\u043c\u0435\u0442\u043a\u0430: \u043f\u0435\u0440\u0435\u0447\u0438\u0442\u0430\u0442\u044c "
    "\u043a\u043e\u043d\u0441\u043f\u0435\u043a\u0442 \u043f\u043e \u0441\u0435\u0442\u044f\u043c",
    "Spent 12 euro on lunch",
)

MEAL_VARIANTS: tuple[tuple[str, str, int, int, int, int], ...] = (
    ("Chicken with rice and salad", "lunch", 620, 45, 18, 62),
    ("Oatmeal with banana", "breakfast", 380, 12, 8, 65),
    ("Pasta with tomato sauce", "dinner", 540, 17, 14, 84),
    ("Greek yoghurt with nuts", "snack", 260, 15, 12, 20),
)


def _digest_index(payload: bytes, modulo: int) -> int:
    digest = hashlib.sha256(payload).digest()
    return digest[0] % modulo


class FakeStructuredLLMProvider:
    """Rule-based parser with the same interface as the real LLM provider."""

    name = FAKE_PROVIDER_NAME

    async def parse(self, text: str, context: CaptureContext) -> ParseOutcome:
        result = parse_text(text, context)
        usage = ProviderUsage(
            provider=FAKE_PROVIDER_NAME,
            model=FAKE_PARSE_MODEL,
            input_tokens=max(1, len(text) // 4),
            output_tokens=max(1, len(result.intents) * 24),
            cost_micro=0,
            duration_ms=1,
        )
        return ParseOutcome(result=result, usage=usage)


class FakeSpeechToTextProvider:
    """Returns a canned transcript chosen deterministically from the audio bytes."""

    name = FAKE_PROVIDER_NAME

    async def transcribe(
        self, audio: bytes, mime_type: str, *, language: str | None = None
    ) -> TranscriptOutcome:
        if mime_type not in ALLOWED_AUDIO_MIME:
            raise UnsupportedMediaError(f"unsupported audio type: {mime_type}")
        text = TRANSCRIPT_VARIANTS[_digest_index(audio, len(TRANSCRIPT_VARIANTS))]
        return TranscriptOutcome(
            text=text,
            language=language or "ru",
            usage=ProviderUsage(
                provider=FAKE_PROVIDER_NAME,
                model=FAKE_STT_MODEL,
                input_tokens=0,
                output_tokens=max(1, len(text) // 4),
                cost_micro=0,
                duration_ms=1,
            ),
        )


class FakeVisionProvider:
    """Returns an approximate meal estimate chosen deterministically."""

    name = FAKE_PROVIDER_NAME

    async def analyze_meal(
        self, image: bytes, mime_type: str, context: CaptureContext
    ) -> MealVisionOutcome:
        if mime_type not in ALLOWED_IMAGE_MIME:
            raise UnsupportedMediaError(f"unsupported image type: {mime_type}")
        title, meal_type, calories, protein, fat, carbs = MEAL_VARIANTS[
            _digest_index(image, len(MEAL_VARIANTS))
        ]
        fields = MealFields(
            title=title,
            meal_type=meal_type,  # type: ignore[arg-type]
            eaten_at=context.now_local.replace(tzinfo=None),
            calories=calories,
            protein=protein,
            fat=fat,
            carbohydrates=carbs,
            estimated=True,
        )
        return MealVisionOutcome(
            fields=fields,
            confidence=0.7,
            usage=ProviderUsage(
                provider=FAKE_PROVIDER_NAME,
                model=FAKE_VISION_MODEL,
                input_tokens=0,
                output_tokens=32,
                cost_micro=0,
                duration_ms=1,
            ),
        )
