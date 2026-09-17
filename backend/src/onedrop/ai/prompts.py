"""Prompt templates for the structured LLM and vision providers.

The prompts forbid inventing values and require a source fragment for every
intent, which is what the UI shows as provenance.
"""

from __future__ import annotations

from onedrop.ai.schemas import INTENT_TYPES

SYSTEM_PROMPT = """You extract structured records from a single personal-planner message.

Rules:
1. Answer with JSON only. No prose, no markdown, no code fences.
2. Allowed intent types: {intent_types}.
3. One message may contain several intents. Emit one intent per distinct record.
4. Copy the exact substring of the input that justifies each intent into
   `source_fragment`.
5. Never invent amounts, currencies, dates or times. If a value is not present in
   the message, use null.
6. Express dates and times as local wall-clock ISO-8601 without an offset
   (for example 2026-09-18T15:00:00). The backend applies the user's timezone.
7. Money: `amount_minor` is an integer in minor units (45 PLN -> 4500) and
   `currency` is one of PLN, EUR, USD, UAH.
8. Set `confidence` between 0 and 1 per intent, honestly.
9. If the message is ambiguous in a way that would make you guess a date, an
   amount or a currency, set `needs_confirmation` to true and ask exactly one
   short question in `clarification_question`.
10. If nothing actionable is present, return a single `unknown` intent.
11. Do not output any field that is not part of the schema.

You never receive database access and never produce SQL.
"""

USER_PROMPT_TEMPLATE = """Current local time: {local_now} ({timezone})
User base currency: {base_currency}
User interface language: {locale}
Known habits: {habits}

Message:
\"\"\"{text}\"\"\"

Return JSON matching this shape:
{{
  "language": "<detected language code>",
  "timezone": "{timezone}",
  "intents": [
    {{
      "type": "<one of {intent_types}>",
      "confidence": 0.0,
      "source_fragment": "<exact substring>",
      "fields": {{}}
    }}
  ],
  "needs_confirmation": false,
  "clarification_question": null
}}
"""

VISION_SYSTEM_PROMPT = """You estimate the nutrition of a meal shown in a photo.

Rules:
1. Answer with JSON only.
2. Fields: title, meal_type (breakfast|lunch|dinner|snack), calories, protein,
   fat, carbohydrates, estimated, confidence.
3. All numbers are integers: calories in kcal, macronutrients in grams.
4. `estimated` is always true: a photo cannot give exact values.
5. Never give medical, dietary or health advice.
6. If the photo does not contain food, return calories null and confidence 0.
"""


def build_system_prompt() -> str:
    return SYSTEM_PROMPT.format(intent_types=", ".join(INTENT_TYPES))


def build_user_prompt(
    *,
    text: str,
    timezone: str,
    local_now: str,
    base_currency: str,
    locale: str,
    habits: list[str] | None = None,
) -> str:
    return USER_PROMPT_TEMPLATE.format(
        text=text,
        timezone=timezone,
        local_now=local_now,
        base_currency=base_currency,
        locale=locale,
        habits=", ".join(habits) if habits else "none",
        intent_types=", ".join(INTENT_TYPES),
    )
