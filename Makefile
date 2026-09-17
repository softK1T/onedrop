.DEFAULT_GOAL := help
COMPOSE ?= docker compose
BACKEND ?= cd backend &&
.PHONY: help up down logs ps migrate seed shell test lint typecheck format frontend-test frontend-build ci build
help: ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'
up: ## Start the whole stack
	$(COMPOSE) up --build -d
down: ## Stop the stack
	$(COMPOSE) down
logs: ## Follow logs
	$(COMPOSE) logs -f --tail=100
ps: ## Show status
	$(COMPOSE) ps
build: ## Build all images
	$(COMPOSE) build
migrate: ## Apply migrations
	$(COMPOSE) run --rm migrate
seed: ## Seed demo data
	$(COMPOSE) run --rm api python scripts/seed_demo.py
shell: ## Open API shell
	$(COMPOSE) run --rm api sh
test: ## Backend tests
	$(BACKEND) pytest -q
lint: ## Backend lint
	$(BACKEND) ruff check .
typecheck: ## Backend typecheck
	$(BACKEND) mypy
format: ## Format backend
	$(BACKEND) ruff format .
frontend-test: ## Mini App tests
	cd frontend && npm run test
frontend-build: ## Build Mini App
	cd frontend && npm run build
ci: ## Backend quality suite
	$(BACKEND) ruff format --check . && ruff check . && mypy && pytest -q
