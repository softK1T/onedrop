# Telegram setup

## 1. Create the bot

1. Open @BotFather -> `/newbot`, choose a name and username.
2. Copy the token into `TELEGRAM_BOT_TOKEN` in your `.env`. Never commit it.
3. Optional: `/setcommands` with

```
start - Start and onboarding
today - Today overview
plan - Plan your day
settings - Preferences and reminders
help - How OneDrop works
```

## 2. Local development (polling)

```env
BOT_MODE=polling
TELEGRAM_BOT_TOKEN=123456:your-token
```

`docker compose up` starts the `bot` process, which long-polls Telegram. No public URL is
required. With an empty token the process logs `bot disabled: no token` and idles — it does
not crash-loop, so demo mode stays usable.

## 3. Production (webhook)

```env
BOT_MODE=webhook
TELEGRAM_WEBHOOK_URL=https://your.domain/api/v1/telegram/webhook
TELEGRAM_WEBHOOK_SECRET=<random 32+ chars>
```

The API validates the `X-Telegram-Bot-Api-Secret-Token` header on every request and returns
`403` when it does not match. Registration happens on bot startup, or manually:

```bash
curl -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook" \
  -d "url=$TELEGRAM_WEBHOOK_URL" \
  -d "secret_token=$TELEGRAM_WEBHOOK_SECRET" \
  -d 'allowed_updates=["message","callback_query","pre_checkout_query"]'
```

The webhook handler only stores the update and enqueues a job, then returns `200` quickly.
Duplicate `update_id` values are ignored.

## 4. Mini App

1. @BotFather -> `/newapp`, select the bot, set the Web App URL to your frontend origin
   (`https://your.domain/` in production, or an HTTPS tunnel to `localhost:5173` in dev).
2. The Mini App sends `initData` to `POST /api/v1/auth/telegram`. The backend verifies the
   HMAC signature with the bot token, checks `auth_date` freshness against
   `INIT_DATA_MAX_AGE_SECONDS`, and never trusts `initDataUnsafe`.
3. Add a menu button: @BotFather -> `/setmenubutton`.

## 5. Voice and photos

Voice messages (`voice`, `audio`) and photos are downloaded through the Bot API file
endpoint by the worker, size- and MIME-checked, stored under a generated safe object key in
S3/MinIO, and deleted after `MEDIA_RETENTION_DAYS`.

## Troubleshooting

| Symptom | Cause |
| --- | --- |
| Mini App shows "auth failed" | wrong bot token, stale `initData`, or clock skew |
| Webhook returns 403 | secret token mismatch |
| Bot silent in webhook mode | `getWebhookInfo` shows pending errors; check TLS chain |
| Nothing happens after a voice message | worker not running; check `docker compose logs worker` |
