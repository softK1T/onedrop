# Architecture

OneDrop is a **modular monolith** with several runtime processes. There is one codebase,
one database and no microservices, no Kubernetes.

## Processes

| Process | Entry point | Responsibility |
| --- | --- | --- |
| `api` | `onedrop.main:app` (uvicorn) | REST API `/api/v1`, Telegram webhook endpoint |
| `bot` | `onedrop.bot.run` | aiogram 3 polling or webhook consumer |
| `worker` | `arq onedrop.workers.settings.WorkerSettings` | AI processing, media handling, notifications |
| `scheduler` | `onedrop.workers.scheduler` | reminder scanning, digests, retention cleanup |
| `frontend` | Vite dev server / static build behind nginx | Telegram Mini App |
| `migrate` | `alembic upgrade head` | one-off migration job |

All processes share PostgreSQL 16, Redis 7 and S3-compatible storage (MinIO in dev).

## Layers

```
api/            transport only: routing, request/response schemas, dependencies
<module>/service.py   application services: use cases, transactions, orchestration
<module>/domain.py    pure domain rules: validation, normalization, calculations
db/repositories/      data access, SQLAlchemy queries, ownership filters
ai/, storage, bot/    infrastructure adapters
workers/              background execution
```

Rules enforced in review:

- Routers contain no business logic and no direct SQL.
- SQLAlchemy model instances never cross the API boundary; Pydantic schemas do.
- Repositories always scope queries by `user_id` and by `deleted_at IS NULL`.
- Services own the transaction boundary. A capture is one transaction.

## Capture flow

```
Telegram update
 -> POST /api/v1/telegram/webhook  (secret token header validated)
 -> telegram_updates INSERT ... ON CONFLICT DO NOTHING   (idempotency by update_id)
 -> inbox_items row (status=received) + instant ack message
 -> enqueue ARQ job process_capture(inbox_item_id) with job_id = idempotency key
 -> worker: media download -> STT/vision if needed -> structured LLM -> JSON
 -> Pydantic discriminated union validation (ai/schemas.py)
 -> CaptureService.apply(): single transaction creating N entities + inbox_entity_links
 -> ai_operations row (tokens, cost, duration, status)
 -> bot edits the ack message with result cards and action buttons
```

Failure of any entity rolls the whole capture transaction back and marks the inbox item
`failed` with a user-visible error. Low confidence marks it `needs_confirmation` and asks a
clarification question instead of guessing.

## Data ownership and multi-tenancy

Every user-owned table carries `user_id`. There is no cross-user endpoint. Attempting to
read another user's record returns 404, never 403 with data.

## Scaling notes

The API is stateless; scale horizontally. Worker concurrency is controlled by ARQ settings.
Redis holds the job queue, rate-limit counters and reminder de-duplication keys. Long-term
media lives in object storage, not in the database.
