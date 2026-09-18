# Changelog

All notable changes to this project are documented here. Format follows Keep a Changelog;
versioning follows Semantic Versioning once 1.0.0 is released.

## [Unreleased]

### Added
- Repository foundation: license, editor config, environment template, documentation set.
- Backend foundation: FastAPI app, configuration, structured logging, async SQLAlchemy,
  Alembic migrations, health endpoints, Telegram init-data auth and sessions.
- Capture pipeline: inbox items, strict AI intent schemas, fake and OpenRouter-compatible
  providers, ARQ worker jobs, idempotency and atomic undo.
- Domain modules: tasks, events, expenses, meals, habits, notes, reminders, analytics.
- Telegram bot: commands, text/voice/photo handlers, status messages, result keyboards,
  reminders and Stars paywall.
- Telegram Mini App: mobile-first React interface, five-item bottom navigation, i18n for
  en/ru/pl/uk.
- Billing: free plan limits, Pro plan, Telegram Stars invoices and payment idempotency.
- Infrastructure: Dockerfiles, Docker Compose stack, Makefile, GitHub Actions, Dependabot,
  CodeQL.
- Durable notification queue: `scheduled_notification` table (migration `0003_notifications`)
  with a unique `dedup_key`, attempt counter, `last_error` and worker lock columns, plus a
  repository that claims rows with `SELECT ... FOR UPDATE SKIP LOCKED` and reclaims locks
  left behind by a killed worker.
- Reminder delivery rules: deterministic dedup keys bucketed to the minute, per-period keys
  for budget warnings, quiet hours that wrap midnight, exponential retry backoff with an
  attempt limit and per-kind opt-in switches.
- Notification planning and delivery for five kinds: morning digest, task reminders, event
  reminders, habit reminders that stop once the habit is logged for the day, and budget
  warnings at the user threshold and at 100% of the monthly limit.
- Reminder preferences on `user_settings`: quiet hours window, task and event lead time and
  the budget warning threshold, exposed through `GET /me` and `PATCH /me/settings`.
- Localised notification text for en/ru/pl/uk with an English fallback and placeholder-safe
  rendering.
- Mini App settings screen for every reminder preference, with optimistic updates, rollback
  on failure and a localised label table.
- Mini App CRUD screens for tasks, notes, events, expenses, meals and habits: filters,
  search, creation, inline editing, completion, pinning, note-to-task conversion, day and
  week agendas, monthly expense summary with budget state, daily nutrition totals and habit
  check-ins with progress, each mutation applied optimistically and rolled back on failure.
- Inbox triage: status filters, thumbs feedback and conversion of a capture into a task, a
  note or an event.
- Today dashboard quick actions: complete, postpone by one day, rename a task and check in a
  habit without leaving the screen.

### Changed
- The scheduler process now plans notifications every five minutes and delivers due ones
  every minute; the ARQ worker exposes `plan_notifications` and `deliver_notifications`.
- Every Mini App collection route now renders a real screen; the read-only collection
  placeholder is no longer used.
- Prettier is configured explicitly (single quotes, 90 columns) to match the style the
  frontend is written in.

### Tests
- Unit coverage for dedup keys, quiet hours, retry backoff, planning windows, locale
  completeness, settings validation and money formatting.
- PostgreSQL integration coverage for dedup uniqueness, `SKIP LOCKED` claiming, restart
  recovery, retry backoff, permanent failure after the attempt limit, cancellation of
  disabled kinds and draining a backlog across dispatcher restarts.
- Mini App coverage for the API client, Telegram bootstrap, auth, the shell and all ten
  screens, including optimistic mutations with rollback on every CRUD screen.

### Known gaps
- Editing the AI result before it is saved is not implemented: the backend has no endpoint
  that accepts a corrected capture result, so the Mini App would have to fake it.
- The legacy `reminders` table still exists next to `scheduled_notification`; tasks and
  events write their plans to the legacy table.
