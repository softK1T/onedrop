# Domain model

All primary keys are UUIDs. All timestamps are `timestamptz` stored in UTC. User timezone is
an IANA string (for example `Europe/Warsaw`). User-owned entities use soft delete
(`deleted_at`).

## Tables

| Table | Purpose | Notable columns / constraints |
| --- | --- | --- |
| `users` | Telegram identity | unique `telegram_user_id` (bigint), `locale`, `is_blocked` |
| `user_settings` | preferences | `timezone`, `base_currency`, `monthly_budget_minor`, reminder toggles, `consent_at`, `allow_training` |
| `telegram_updates` | webhook idempotency | unique `update_id`, `received_at`, `processed_at` |
| `sessions` | refresh sessions | `refresh_token_hash`, `expires_at`, `revoked_at` |
| `inbox_items` | every capture | `input_type`, `raw_text`, `transcript`, `telegram_update_id`, `status`, `error`, `ai_result` JSONB, `processing_ms`, `ai_cost_micro`, `provider`, `model`, `idempotency_key` unique |
| `inbox_entity_links` | capture -> entity | `inbox_item_id`, `entity_type`, `entity_id`, unique together |
| `ai_operations` | usage ledger | `operation_type`, `provider`, `model`, `input_tokens`, `output_tokens`, `cost_micro`, `duration_ms`, `status`, unique `idempotency_key` |
| `tasks` | tasks | `title`, `description`, `due_at`, `priority`, `status`, `category`, `completed_at`, `source_inbox_item_id` |
| `events` | events | `title`, `starts_at`, `ends_at`, `location`, `description`, `status`, check `ends_at >= starts_at` |
| `expenses` | money | `amount_minor` bigint, `currency`, `base_amount_minor`, `base_currency`, `fx_rate` numeric, `category`, `merchant`, `occurred_at`, check `amount_minor >= 0` |
| `meals` | nutrition | `meal_type`, `eaten_at`, `title`, `calories`, `protein`, `fat`, `carbohydrates`, `estimated` |
| `habits` | habits | `name`, `measurement_type` (`boolean`/`numeric`), `target_value`, `unit`, `schedule` JSONB, `active`, `reminder_hour` |
| `habit_logs` | habit events | `habit_id`, `value`, `logged_at`, `source_inbox_item_id` |
| `notes` | notes | `title`, `content`, `tags` (text[]), `pinned` |
| `scheduled_notification` | durable outbound notifications | `kind`, `payload` JSONB, `run_at`, `status`, `attempts`, `last_error`, unique `dedup_key`, worker lock columns |
| `subscriptions` | plans | `plan`, `status`, `started_at`, `expires_at`, `source` |
| `payments` | Stars payments | unique `telegram_payment_charge_id`, `amount_stars`, `payload`, `status` |
| `usage_counters` | limits | `user_id`, `period_key`, `scope` (`daily`/`monthly`/`bonus`), `used`, unique together |
| `user_feedback` | capture quality | `inbox_item_id`, `rating`, `comment` |
| `audit_events` | traceability | `user_id`, `action`, `entity_type`, `entity_id`, `payload` JSONB |

## Enums (Python enums + PostgreSQL check constraints)

- `InputType`: `text`, `voice`, `photo`
- `InboxStatus`: `received`, `queued`, `processing`, `needs_confirmation`, `completed`, `failed`, `undone`
- `TaskStatus`: `open`, `done`, `cancelled`
- `EventStatus`: `planned`, `done`, `cancelled`
- `Priority`: `low`, `normal`, `high`
- `MealType`: `breakfast`, `lunch`, `dinner`, `snack`
- `NotificationKind`: `morning_digest`, `task_reminder`, `event_reminder`, `habit_reminder`, `budget_warning`
- `DeliveryStatus`: `pending`, `sent`, `failed`, `cancelled`
- `Plan`: `free`, `pro`
- `SubscriptionStatus`: `active`, `expired`, `cancelled`
- `ExpenseCategory`: `food`, `transport`, `housing`, `health`, `entertainment`, `shopping`, `bills`, `education`, `travel`, `other`

## Reminder rules

Task reminders are derived from `due_at` and the user's configured lead time. Event reminders
are derived from `starts_at` and the event lead time. Habit reminders retain their per-habit
`reminder_hour`. The planning pass stores deliveries in `scheduled_notification`; completion,
cancellation, deletion or schedule changes cancel matching pending rows before the next pass.

## Money rules

`amount_minor` is an integer count of minor units (4500 = 45.00 PLN). Conversion to the
user base currency stores both `base_amount_minor` and the `fx_rate` used, so historical
reports never change. If no rate is available, `base_amount_minor` and `fx_rate` stay
`NULL` and the original amount is still saved. Supported currencies: PLN, EUR, USD, UAH.

## Indexes

`(user_id, due_at)` on tasks, `(user_id, starts_at)` on events, `(user_id, occurred_at)` on
expenses, `(user_id, eaten_at)` on meals, `(habit_id, logged_at)` on habit logs,
`(user_id, created_at)` on inbox items and notes, `(status, run_at)` and `(user_id, run_at)`
on scheduled notifications.
