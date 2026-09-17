.DEFAULT_GOAL := help
COMPOSE ?= docker compose
BACKEND ?= cd backend &&

.PHONY: help up down logs ps migrate seed shell test lint typecheck format frontend-test frontend-build ci build

help: ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

up: ## Start the whole stack
	$(COMPOSE) up --build -d

down: ## Stop the stack and remove containers
	$(COMPOSE) down

logs: ## Follow logs of all services
	$(COMPOSE) logs -f --tail=100

ps: ## Show service status
	$(COMPOSE) ps

build: ## Build images without starting them
	$(COMPOSE) build

migrate: ## Apply database migrations
	$(COMPOSE) run --rm migrate

seed: ## Create the demo user with sample records
	$(COMPOSE) run --rm api python scripts/seed_demo.py

shell: ## Open a shell in the api container
	$(COMPOSE) run --rm api sh

test: ## Run backend tests
	$(BACKEND) pytest -q

lint: ## Lint backend sources
	$(BACKEND) ruff check .

typecheck: ## Type-check backend sources
	$(BACKEND) mypy

format: ## Format backend sources
	$(BACKEND) ruff format .

frontend-test: ## Run Mini App tests
	cd frontend && npm run test

frontend-build: ## Build the Mini App for production
	cd frontend && npm run build

ci: ## Everything CI runs for the backend
	$(BACKEND) ruff format --check . && ruff check . && mypy && pytest -q
