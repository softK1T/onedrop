# Contributing to OneDrop

Thanks for your interest. OneDrop is a modular monolith: Python 3.12 backend, React +
TypeScript Mini App, PostgreSQL, Redis, Docker Compose.

## Local setup

```bash
cp .env.example .env
docker compose up --build
make migrate && make seed
```

Backend only, without Docker:

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
uvicorn onedrop.main:app --reload
```

## Before opening a pull request

```bash
make format      # ruff format
make lint        # ruff check
make typecheck   # mypy
make test        # pytest
make frontend-test
```

`make ci` runs the same checks GitHub Actions runs.

## Rules

- Conventional Commits: `feat:`, `fix:`, `chore:`, `docs:`, `test:`, `ci:`, `refactor:`.
- Keep routers thin; business logic belongs in `application services`.
- Never return SQLAlchemy models from the API layer — map to Pydantic schemas.
- Money is integer minor units. No floats for amounts, ever.
- Timestamps are stored in UTC; user timezone is an IANA string.
- No secrets, tokens, `.env` files, build artifacts or `node_modules` in commits.
- Do not silence type errors with blanket `# type: ignore` and do not `skip` tests to make
  CI green.
- New AI behaviour needs a deterministic fixture in `backend/tests/fixtures/ai_eval`.

## Reporting bugs

Use the issue templates in `.github/ISSUE_TEMPLATE`. Security problems go to
[SECURITY.md](SECURITY.md) instead of a public issue.
