# Deployment

> Not verified in production. The stack has been designed and described here, but the
> authors have not executed a production deployment. Validate everything in staging first.

## Topology

```
internet -> nginx (TLS, security headers, static Mini App)
              -> api (uvicorn, /api/v1)
            postgres  redis  minio/S3
            bot        worker      scheduler
```

## Steps

1. Provision a host with Docker Engine and Compose v2, at least 2 vCPU / 4 GB RAM.
2. Copy `.env.example` to `.env` and set production values:
   - `APP_ENV=production` (disables dev login and API docs)
   - strong `SECRET_KEY`, real `DATABASE_URL`, `REDIS_URL`
   - `TELEGRAM_BOT_TOKEN`, `BOT_MODE=webhook`, `TELEGRAM_WEBHOOK_URL`, `TELEGRAM_WEBHOOK_SECRET`
   - `AI_PROVIDER_MODE=real` and provider keys, if AI is wanted
   - `CORS_ALLOW_ORIGINS` and `TRUSTED_HOSTS` limited to your domains
   - `VITE_API_BASE_URL=https://your.domain/api/v1`, `VITE_DEV_LOGIN=false`
3. Terminate TLS. Either put certificates into `infra/nginx/certs` and use the bundled
   config, or run behind an external load balancer / Cloudflare and keep nginx on HTTP.
4. Start with the production profile:

```bash
docker compose --profile production up --build -d
docker compose run --rm migrate
```

5. Register the webhook and the Mini App URL (see docs/telegram-setup.md).
6. Verify `GET /health` (liveness) and `GET /ready` (DB + Redis) and `GET /version`.

## Operations

- **Backups**: `pg_dump` on a schedule plus object storage versioning. Restore drills are
  your responsibility.
- **Logs**: JSON to stdout via structlog; ship with your log driver.
- **Migrations**: always run the `migrate` job before rolling new API/worker containers.
- **Zero-downtime**: scale `api` to two replicas behind nginx and restart one at a time.
  Migrations must stay backward compatible for one release.
- **Media retention**: the scheduler deletes objects older than `MEDIA_RETENTION_DAYS`.

## Hardening checklist

- containers run as non-root, read-only where possible
- `restart: unless-stopped` for production services
- health checks on postgres, redis, minio, api
- no ports exposed except nginx (80/443)
- secrets injected by the orchestrator, never baked into images
- pinned image tags (`postgres:16`, `redis:7-alpine`, `python:3.12-slim`, `node:20-alpine`)
