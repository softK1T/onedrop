# AI pipeline

## Provider abstraction

Three protocols in `onedrop/ai/providers/base.py`:

- `StructuredLLMProvider.parse(text, context) -> CaptureResult`
- `SpeechToTextProvider.transcribe(audio, mime) -> Transcript`
- `VisionProvider.analyze_meal(image, mime) -> MealVisionResult`

Implementations:

| Mode | Structured LLM | STT | Vision |
| --- | --- | --- | --- |
| `fake` | deterministic rule parser | canned transcript per fixture hash | canned meal estimate |
| `real` | OpenRouter-compatible chat completions with JSON response format | OpenAI-compatible `/audio/transcriptions` | OpenRouter/OpenAI vision chat |

`AI_PROVIDER_MODE=fake` is the default so the project runs with no API key. The fake
providers are deterministic: same input, same output, no randomness, no network.

## Contract

The model returns **only** JSON. It never receives database credentials and never emits
SQL. Output is validated by a strict Pydantic v2 discriminated union
(`onedrop/ai/schemas.py`), discriminated on `type`:

`task.create`, `event.create`, `expense.create`, `meal.create`, `note.create`,
`habit.create`, `habit.log`, `unknown`.

```json
{
  "language": "ru",
  "timezone": "Europe/Warsaw",
  "intents": [
    {
      "type": "expense.create",
      "confidence": 0.97,
      "source_fragment": "потратил 45 злотых на такси",
      "fields": {
        "amount_minor": 4500,
        "currency": "PLN",
        "category": "transport",
        "merchant": null,
        "occurred_at": "2026-09-17T18:00:00+02:00"
      }
    }
  ],
  "needs_confirmation": false,
  "clarification_question": null
}
```

Unknown fields are rejected (`extra="forbid"`). Every intent must carry a
`source_fragment` copied from the user input, which is how the UI highlights provenance.

## Guarantees

1. Model has no DB access and executes no SQL.
2. JSON only; malformed output fails the capture with a retryable error.
3. Dates are normalized against the user's IANA timezone by backend code, not by the model.
4. Amounts, currencies and dates that are not present in the input stay `null` — the prompt
   forbids inventing them, and the backend drops intents with impossible values.
5. Confidence below `AI_MIN_CONFIDENCE` (or `needs_confirmation=true`) puts the inbox item
   into `needs_confirmation` and asks `clarification_question` instead of writing records.
6. Several intents per message are supported and applied in one transaction.
7. Repeated AI responses cannot duplicate records: the capture idempotency key plus
   `inbox_entity_links` uniqueness make re-application a no-op.
8. Any per-entity failure rolls back the entire capture transaction.

## Usage accounting

Each provider call writes an `ai_operations` row (operation type, provider, model, input and
output tokens, provider cost in micro-units, duration, status, idempotency key). Quota is
**not** consumed when the format is unsupported, when an internal error happens before the
model call, on a repeated Telegram update, or on a repeated idempotency key.

## Evaluation fixtures

`backend/tests/fixtures/ai_eval/*.json` holds 50+ deterministic cases across tasks, events,
expenses, meals, habits, notes, multi-intent, ambiguous and unsupported inputs. The eval
test runs the fake provider only — CI never calls an external AI API.
