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
