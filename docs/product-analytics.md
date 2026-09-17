# Product analytics

OneDrop computes analytics with SQL and Python only. The LLM never aggregates numbers — it
only extracts structured fields from a single message.

## User-facing analytics

| View | Endpoint | Computation |
| --- | --- | --- |
| Expenses by category | `GET /analytics/expenses` | `SUM(base_amount_minor)` grouped by category for the period |
| Current month spend | `GET /analytics/expenses` | month-to-date sum plus budget usage percentage |
| Month over month | `GET /analytics/expenses` | current vs previous month totals and delta |
| Daily calories and macros | `GET /analytics/nutrition` | daily `SUM` of calories/protein/fat/carbs |
| Habit completion | `GET /analytics/habits` | logs vs scheduled occurrences, percentage per habit |
| Tasks today / overdue / completed | `GET /analytics/productivity` | counts by status and `due_at` window |
| Captures per period | `GET /analytics/productivity` | inbox items grouped by day and status |
| AI usage and remaining quota | `GET /billing/usage` | `ai_operations` + `usage_counters` |

All queries are scoped by `user_id` and respect the user's timezone when bucketing days:
the backend converts the requested local range into UTC bounds before querying.

## Internal metrics worth watching

- capture success rate: `completed / (completed + failed)` per day
- clarification rate: share of captures ending in `needs_confirmation`
- undo rate: undone captures / completed captures (a proxy for extraction quality)
- median processing time per input type (`inbox_items.processing_ms`)
- AI cost per active user (`ai_operations.cost_micro`)
- free -> Pro conversion, and paywall views per conversion
- retention: days with at least one capture, per weekly cohort

## Feedback loop

`POST /inbox/{id}/feedback` stores a rating and optional comment in `user_feedback`.
Negative feedback plus the stored `ai_result` and `source_fragment` values is the input for
prompt and fixture improvements. Prompt changes must be accompanied by new fixtures in
`backend/tests/fixtures/ai_eval` so regressions are caught deterministically.

## Privacy constraints

No third-party analytics SDK is shipped in the Mini App bundle. Aggregates are computed on
data the user already owns, and account deletion removes the underlying rows.
