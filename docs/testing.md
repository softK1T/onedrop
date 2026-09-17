# Testing

```bash
make test            # backend: unit + integration + acceptance
make frontend-test   # vitest
make lint            # ruff check + eslint
make typecheck       # mypy + tsc --noEmit
make ci              # everything CI runs
```

Integration tests require PostgreSQL and Redis. Locally they come from Docker Compose
(`docker compose up -d postgres redis`); in CI they are service containers. Tests that need
those services are marked `@pytest.mark.integration` and are skipped only when the services
are genuinely unavailable locally — CI always runs them.

## Backend unit tests (`backend/tests/unit`)

- Telegram init data signature, tampering and expiry
- date and time normalization ("завтра в 15:00", "вечером") against IANA timezones
- money representation: minor units, currency parsing, no floats
- usage limits: onboarding bonus, daily free limit, Pro monthly limit, non-charged cases
- AI intent schemas: discriminated union, extra fields rejected, bad enums rejected
- low-confidence behaviour -> `needs_confirmation` + clarification question
- capture rollback when one intent is invalid
- reminder scheduling and de-duplication keys
- subscription state machine (active, expired, cancelled, restored)
- payment idempotency on redelivered `successful_payment`

## Integration tests (`backend/tests/integration`)

Against real PostgreSQL + Redis: repositories, ownership isolation, capture transaction,
Telegram `update_id` idempotency, retry, undo, duplicate payment, usage counters, reminder
persistence across restart, soft deletion filters.

## Acceptance test (`backend/tests/e2e/test_acceptance_capture.py`)

Input: «Завтра в 15:00 встреча с Андреем, потратил 45 злотых на такси и нужно оплатить
интернет».

Asserts: exactly one event, one expense, one task; `amount_minor == 4500`;
`currency == "PLN"`; all three linked to one inbox item; redelivery of the same Telegram
update creates nothing new; undo reverts all three records.

## Frontend tests (`frontend/src/**/__tests__`)

Telegram auth initialization, loading/skeleton state, Today dashboard rendering, capture
form submission, result cards, correction flow, empty state, API error state, paywall,
theme handling (light/dark + Telegram theme variables).

## AI eval fixtures

`backend/tests/fixtures/ai_eval/` contains 50+ deterministic cases. `test_ai_eval.py`
iterates them through the fake provider and asserts intent types and key fields. No
external AI API is contacted in CI.
