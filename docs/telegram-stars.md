# Telegram Stars billing

OneDrop Pro is sold with Telegram Stars. Stars invoices use `currency = "XTR"`, an empty
`provider_token`, and prices expressed directly in Stars.

## Configuration

```env
PRO_PRICE_STARS=250
PRO_PERIOD_DAYS=30
PRO_MONTHLY_AI_LIMIT=1000
```

No payment provider credentials exist for Stars, so nothing secret is needed beyond the bot
token.

## Flow

```
Mini App / bot paywall
 -> POST /api/v1/billing/invoice        (server creates invoice link, stores payload)
 -> user pays in Telegram
 -> pre_checkout_query   -> bot answers ok=true after validating payload and plan
 -> successful_payment   -> payments row with unique telegram_payment_charge_id
 -> subscription activated (plan=pro, expires_at = now + PRO_PERIOD_DAYS)
 -> confirmation message + refreshed limits
```

## Idempotency and safety

- `payments.telegram_payment_charge_id` is unique. A redelivered `successful_payment`
  update finds the existing row and does not extend the subscription twice.
- Invoice payloads embed `user_id` and plan; a payload that does not match the paying user
  is rejected in `pre_checkout_query`.
- The subscription is activated **only** after `successful_payment`. There is no code path
  that grants Pro on invoice creation.
- Expiration is enforced by `expires_at`; the scheduler downgrades expired subscriptions and
  the plan resolver treats `expires_at < now()` as free even before the sweep runs.
- Restarting the bot or reopening the app restores the active plan from the database.
- Test mode: set `AI_PROVIDER_MODE=fake` and use `BILLING_TEST_MODE=true` to simulate a
  successful payment through `POST /api/v1/billing/invoice?simulate=true`, which is rejected
  when `APP_ENV=production`.

## Refunds

Stars refunds are handled by Telegram support tooling and `refundStarPayment`. The MVP
stores the charge id so a refund can be reconciled manually; automated refunds are not part
of the MVP.
