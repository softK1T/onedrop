# Privacy

> **Template.** This document and the terms of service draft are starting points written by
> engineers, not lawyers. Have them reviewed by a qualified lawyer before any production
> launch, and adapt them to GDPR and your local law.

## What OneDrop stores

| Data | Why | Retention |
| --- | --- | --- |
| Telegram user id, first name, username, language | identity and localisation | until account deletion |
| Settings (timezone, currency, budget, reminders, consent) | product behaviour | until account deletion |
| Captured text, transcripts, AI results | to create and explain your records | until account deletion |
| Voice and photo files | to transcribe / estimate a meal | `MEDIA_RETENTION_DAYS` (default 30 days) |
| Tasks, events, expenses, meals, habits, notes | the product itself | until you delete them |
| AI operation metadata (model, tokens, cost, duration) | quotas and cost control | until account deletion |
| Payments (Stars charge id, amount, status) | subscription and accounting | as required for accounting |

No advertising trackers, no data selling, no cross-user analytics profiles.

## Consent

Onboarding asks for explicit consent before the first AI processing and records
`user_settings.consent_at`. Training on user content is **off by default**
(`allow_training=false`) and only happens with an explicit opt-in toggle in Settings.

## Third parties

- **Telegram** — messaging transport and payments.
- **AI providers** (OpenRouter-compatible LLM, OpenAI-compatible STT/vision) — receive the
  content you capture, only when `AI_PROVIDER_MODE=real`. In demo mode nothing leaves the
  deployment.
- **Your own infrastructure** — PostgreSQL, Redis, S3/MinIO.

Self-hosting operators are the data controllers for their instance.

## Your rights

- **Export**: `POST /api/v1/me/export` produces a JSON/CSV bundle of your records.
- **Delete**: `DELETE /api/v1/me` erases user rows, all domain records, inbox items and
  stored media. Deletion is irreversible; a confirmation step is required in the Mini App
  (Profile -> Privacy).
- **Correction**: every record is editable in the Mini App, and every capture can be
  corrected or undone.
- **Access**: the export covers everything the product stores about you.

## Nutrition disclaimer

Calories and macronutrients — especially from photos — are rough estimates flagged
`estimated=true`. OneDrop is not a medical device and gives no medical, dietary or health
advice.

## Contact

Use GitHub issues for product questions and private vulnerability reporting for security or
privacy incidents.
