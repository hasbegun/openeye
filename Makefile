.PHONY: help up down build logs test test-gateway test-guardrails test-analyzer test-ingestor test-alerter lint clean init-nats ps

COMPOSE := docker compose

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# --- Docker ---

up: ## Start all services
	$(COMPOSE) up --build -d

up-infra: ## Start infrastructure only (nats, postgres, redis)
	$(COMPOSE) up -d nats postgres redis

down: ## Stop all services
	$(COMPOSE) down

build: ## Build all service images
	$(COMPOSE) build

ps: ## Show running containers
	$(COMPOSE) ps

logs: ## Tail logs for all services
	$(COMPOSE) logs -f

logs-gateway: ## Tail gateway logs
	$(COMPOSE) logs -f gateway

logs-analyzer: ## Tail analyzer logs
	$(COMPOSE) logs -f analyzer

logs-guardrails: ## Tail guardrails logs
	$(COMPOSE) logs -f guardrails

restart: ## Restart all application services
	$(COMPOSE) restart gateway guardrails analyzer ingestor alerter

clean: ## Stop and remove all containers, volumes, and images
	$(COMPOSE) down -v --rmi local

# --- Init ---

init-nats: ## Initialize NATS JetStream streams
	$(COMPOSE) up nats-init

init-db: ## Re-run database migrations
	$(COMPOSE) exec postgres psql -U openeye -f /docker-entrypoint-initdb.d/001_init.sql

# --- Testing (all in Docker) ---

COMPOSE_TEST := docker compose -f docker-compose.test.yml

test: ## Run all unit tests in Docker
	$(COMPOSE_TEST) up --build --abort-on-container-exit --exit-code-from test test
	$(COMPOSE_TEST) down

test-gateway: ## Run gateway unit tests in Docker
	$(COMPOSE_TEST) run --rm test pytest services/gateway/tests/ -v
	$(COMPOSE_TEST) down

test-guardrails: ## Run guardrails unit tests in Docker
	$(COMPOSE_TEST) run --rm test pytest services/guardrails/tests/ -v
	$(COMPOSE_TEST) down

test-analyzer: ## Run analyzer unit tests in Docker
	$(COMPOSE_TEST) run --rm test pytest services/analyzer/tests/ -v
	$(COMPOSE_TEST) down

test-ingestor: ## Run ingestor unit tests in Docker
	$(COMPOSE_TEST) run --rm test pytest services/ingestor/tests/ -v
	$(COMPOSE_TEST) down

test-alerter: ## Run alerter unit tests in Docker
	$(COMPOSE_TEST) run --rm test pytest services/alerter/tests/ -v
	$(COMPOSE_TEST) down

test-shared: ## Run shared module tests in Docker
	$(COMPOSE_TEST) run --rm test pytest shared/tests/ -v
	$(COMPOSE_TEST) down

# --- Development (all in Docker) ---

lint: ## Run linting in Docker
	$(COMPOSE_TEST) run --rm --no-deps test ruff check services/ shared/
	$(COMPOSE_TEST) down

format: ## Auto-format code in Docker
	$(COMPOSE_TEST) run --rm --no-deps test ruff format services/ shared/
	$(COMPOSE_TEST) down

health: ## Check health of running services
	@echo "Gateway:" && curl -s http://localhost:8000/health | python3 -m json.tool || echo "DOWN"
	@echo "NATS:" && curl -s http://localhost:8222/healthz || echo "DOWN"

shell-gateway: ## Open a shell in the gateway container
	$(COMPOSE) exec gateway /bin/bash

shell-db: ## Open psql in the postgres container
	$(COMPOSE) exec postgres psql -U openeye
