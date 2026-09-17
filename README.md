# OneDrop

**AI-powered Telegram life planner** that turns text, voice and photos into structured
tasks, events, expenses, meals, habits and notes.

OneDrop is an original product. It is not affiliated with, and does not copy the name,
branding, texts, design or code of any other planner application.

---

## 1. What the product does

You drop anything into a Telegram chat — a sentence, a voice message, a photo of your
lunch — and OneDrop turns it into structured records in one pass:

> «Завтра в 15:00 встреча с Андреем, потратил 45 злотых на такси, а вечером нужно
> оплатить интернет»

becomes

1. **Event** — "Встреча с Андреем", tomorrow 15:00 (user timezone)
2. **Expense** — 4500 minor units PLN, category `transport`
3. **Task** — "Оплатить интернет", due tonight

All three records are linked to a single inbox item, so a single tap on **Отменить всё**
removes them atomically.

## 2. Screens and flow (text form, no fake screenshots)

```
Telegram message (text | voice | photo)
  -> webhook (secret header check)  ->  telegram_updates idempotency row
  -> "Принято, разбираю сообщение…"  (instant ack, message_id stored)
  -> ARQ job: transcribe / vision / structured LLM -> strict JSON
  -> Pydantic discriminated-union validation
  -> capture service: one PostgreSQL transaction, all-or-nothing
  -> bot edits the ack message: result cards + [Открыть] [Исправить] [Отменить всё]
  -> records visible in Mini App (Today / Inbox / entity screens)
  -> edit or undo
```

Mini App screens: Onboarding, Today, Inbox, Universal Capture, Tasks, Events, Expenses,
Meals, Habits, Notes, Analytics, Subscription, Settings, Privacy & account deletion.
Bottom navigation has five items only: Today, Inbox, Add, Analytics, Profile.

## 3. Key features

- Universal capture: text, voice (STT), food photo (vision), multi-intent in one message
- Domain modules: tasks, events, expenses, meals, habits + habit logs, notes
- Inbox with `received / queued / processing / needs_confirmation / completed / failed / undone`
- Retry, edit, feedback and atomic undo per capture
- Reminders: task, event, habit, morning digest, budget warning (UTC storage, IANA timezone)
- Analytics computed in SQL/Python only — never by the LLM
- Free plan (15 onboarding AI actions, then 3/day) and Pro plan via Telegram Stars (`XTR`)
- Demo mode: runs with zero AI and zero Telegram credentials
- i18n: English, Russian, Polish, Ukrainian

## 4. Architecture

Modular monolith, separate runtime processes (api, bot, worker, scheduler, frontend).
Layers: API/transport -> application services -> domain -> repositories -> infrastructure.
Routers are thin; SQLAlchemy models never leave the repository layer.

See [docs/architecture.md](docs/architecture.md), [docs/domain-model.md](docs/domain-model.md)
and [docs/ai-pipeline.md](docs/ai-pipeline.md).

## 5. Quick start

```bash
git clone https://github.com/softK1T/onedrop.git
cd onedrop
cp .env.example .env
docker compose up --build
```

Services: API <http://localhost:8000>, Mini App <http://localhost:5173>,
MinIO console <http://localhost:9001>, PostgreSQL `5432`, Redis `6379`.
OpenAPI docs: <http://localhost:8000/docs> (disabled when `APP_ENV=production`).

## 6. Demo mode

Defaults in `.env.example` are already demo-safe: `AI_PROVIDER_MODE=fake`,
`DEV_LOGIN_ENABLED=true`, empty `TELEGRAM_BOT_TOKEN`.

```bash
make up        # start the stack
make migrate   # alembic upgrade head
make seed      # demo user + sample records
```

Then open the Mini App and press **Dev login** (only available when `APP_ENV != production`),
or call the API directly:

```bash
curl -X POST http://localhost:8000/api/v1/auth/dev -H 'content-type: application/json' \
  -d '{"telegram_user_id": 100001}'
```

The fake providers include a deterministic parser that resolves the acceptance example
(event + expense + task) without any network call. With no bot token the bot process logs
a warning and idles in `disabled` state instead of crash-looping.

## 7. Telegram setup

See [docs/telegram-setup.md](docs/telegram-setup.md). Short version:

1. Create a bot with @BotFather, put the token into `TELEGRAM_BOT_TOKEN`.
2. Local development: keep `BOT_MODE=polling`.
3. Production: set `BOT_MODE=webhook`, `TELEGRAM_WEBHOOK_URL=https://your.domain/api/v1/telegram/webhook`
   and a random `TELEGRAM_WEBHOOK_SECRET`; the app validates
   `X-Telegram-Bot-Api-Secret-Token` on every update.
4. Register the Mini App URL in @BotFather (`/newapp`) pointing to your frontend origin.

## 8. AI provider setup

Set `AI_PROVIDER_MODE=real` and fill `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL`,
`OPENROUTER_MODEL` for structured parsing, `STT_*` for voice transcription and
`VISION_MODEL` for food photos. The model only ever receives text/audio/image and returns
JSON — it has no database credentials and never executes SQL.

## 9. Telegram Stars setup

Stars invoices use `currency = XTR` and require no payment provider token. Configure
`PRO_PRICE_STARS`, `PRO_MONTHLY_AI_LIMIT`, `PRO_PERIOD_DAYS`. Flow:
`POST /billing/invoice` -> `pre_checkout_query` -> `successful_payment` ->
`telegram_payment_charge_id` stored uniquely -> subscription activated.
See [docs/telegram-stars.md](docs/telegram-stars.md).

## 10. Environment variables

All variables are documented in [.env.example](.env.example). Nothing secret is committed;
the file contains placeholders only.

## 11. Migrations

```bash
make migrate                     # alembic upgrade head
docker compose run --rm migrate  # same, one-off job
```

Alembic lives in `backend/alembic`. CI runs `alembic upgrade head` against a real
PostgreSQL 16 service and then checks that models and migrations do not drift.

## 12. Tests

```bash
make test            # backend pytest (unit + integration + acceptance)
make frontend-test   # vitest
make ci              # lint + typecheck + both test suites
```

Backend integration tests need PostgreSQL and Redis (provided by Compose and by CI
services). No test calls a real AI API. See [docs/testing.md](docs/testing.md).

## 13. Deployment

[docs/deployment.md](docs/deployment.md) describes the production profile: non-root
containers, health checks, nginx reverse proxy, webhook mode, `DEV_LOGIN_ENABLED=false`.
Production deployment has **not** been executed or verified by the authors — treat the
guide as a reference, not as a tested runbook.

## 14. Security notes

Secrets only via environment variables, Telegram init data signature + `auth_date`
validation, webhook secret token, ownership checks on every query, JWT expiry and refresh
revocation, rate limits, MIME and size validation on uploads, parameterized SQL,
CORS allowlist, trusted hosts, security headers, structured logs that never contain the
bot token, AI keys, raw init data or full JWTs. Details: [docs/security.md](docs/security.md).

## 15. MVP limitations

- No Google/Apple Calendar sync, no Lifetime plan.
- Currency conversion uses a static rate table snapshot stored per record; a missing rate
  never blocks saving the original amount.
- Nutrition numbers from photos are rough estimates, always flagged `estimated=true`.
  OneDrop makes no medical claims.
- Legal texts in `docs/privacy.md` and the terms template are drafts and require review by
  a lawyer before any production launch.
- Analytics are per-user aggregates only; no cohort/product analytics warehouse.

## 16. Roadmap

Recurring tasks and events, calendar sync, shared/family spaces, richer budget rules,
receipt OCR, weekly review digest, on-device caching, native web app outside Telegram.

## 17. License

MIT — see [LICENSE](LICENSE).
