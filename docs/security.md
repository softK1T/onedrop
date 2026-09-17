# Security

## Authentication

- Telegram Mini App `initData` is verified server-side: HMAC-SHA256 with a key derived from
  the bot token (`HMAC("WebAppData", bot_token)`), constant-time comparison, `auth_date`
  must be newer than `INIT_DATA_MAX_AGE_SECONDS`.
- `initDataUnsafe` from the client is never trusted for identity.
- Successful validation upserts the user and returns a short-lived access JWT
  (`ACCESS_TOKEN_TTL_SECONDS`, default 15 min) plus an opaque refresh token whose hash is
  stored in `sessions`.
- Refresh rotates the session and can be revoked (`POST /auth/logout`).
- `POST /auth/dev` exists for local development only and returns `404` when
  `APP_ENV=production` or `DEV_LOGIN_ENABLED=false`.
- No passwords anywhere.

## Authorization

Every repository method takes `user_id` and filters on it. A record belonging to another
user is indistinguishable from a missing record (`404`). Integration tests assert ownership
isolation.

## Webhook

`POST /api/v1/telegram/webhook` requires the `X-Telegram-Bot-Api-Secret-Token` header to
match `TELEGRAM_WEBHOOK_SECRET` (constant-time compare). Updates are inserted with
`ON CONFLICT DO NOTHING` on `update_id`, so redelivery cannot create duplicates. Heavy work
is queued; the handler returns immediately. Failed jobs retry with backoff and land in a
dead-letter list after the final attempt.

## Input and uploads

- Pydantic v2 validates every request body; unknown fields are rejected.
- Uploads are limited by `MAX_UPLOAD_BYTES` and an allowlist of MIME types
  (`audio/ogg`, `audio/mpeg`, `audio/mp4`, `audio/wav`, `image/jpeg`, `image/png`,
  `image/webp`).
- Object keys are generated (`{user_id}/{uuid4}.{ext}`); user-supplied file names never
  reach storage paths.
- Media is served through a backend proxy endpoint or presigned URLs with short TTL.
- Rate limiting: `RATE_LIMIT_PER_MINUTE` per user/IP on capture and auth endpoints, backed
  by Redis.

## Transport and headers

CORS allowlist from `CORS_ALLOW_ORIGINS`, `TrustedHostMiddleware` from `TRUSTED_HOSTS`,
plus `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`,
`Strict-Transport-Security` (production) and a restrictive `Content-Security-Policy` on the
nginx layer.

## Data layer

SQLAlchemy Core/ORM with bound parameters only — no string-built SQL. Soft delete keeps an
audit trail; hard delete is available through account deletion.

## Logging

structlog JSON logs. Never logged: bot token, AI API keys, full `initData`, full JWTs,
voice/photo contents, payment secrets. Sensitive values are redacted by a processor;
identifiers are logged as hashes or UUIDs.

## Supply chain

Dependencies are pinned; Dependabot watches pip, npm, Docker and Actions. CodeQL scans
Python and TypeScript. Docker images run as a non-root user. Workflows declare minimal
`permissions`.

## Secret rotation

If a secret leaks: revoke the bot token in @BotFather, rotate `SECRET_KEY` (invalidates all
sessions), rotate provider API keys, rotate MinIO/S3 credentials, then redeploy. Never
rewrite history with force-push to "hide" a leak — rotate instead.
