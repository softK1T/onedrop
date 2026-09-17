# Security Policy

## Supported versions

OneDrop is pre-1.0. Only the `main` branch receives security fixes.

## Reporting a vulnerability

Please **do not** open a public issue. Use GitHub private vulnerability reporting
(Security -> Report a vulnerability) on this repository. Include reproduction steps,
affected endpoint or component, and impact. Expect an acknowledgement within a few days.

## Scope

In scope: Telegram init data validation, webhook secret handling, session/JWT handling,
ownership checks, upload handling, billing idempotency, injection issues.

Out of scope: findings that require a leaked `.env`, denial of service through raw traffic
volume, or issues in third-party services (Telegram, OpenRouter, MinIO).

## Handling secrets

The repository contains no real credentials. `.env.example` holds placeholders only.
If you believe a secret was committed, report it privately; rotation instructions are in
[docs/security.md](docs/security.md).
