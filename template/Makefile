.DEFAULT_GOAL := help

COMPOSE := docker compose

.PHONY: help
help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ── Lifecycle ──────────────────────────────────────────────────────────────

.PHONY: up
up: ## Start all services in detached mode
	$(COMPOSE) up -d

.PHONY: down
down: ## Stop and remove containers (keeps volumes)
	$(COMPOSE) down

.PHONY: restart
restart: ## Restart all services
	$(COMPOSE) restart

.PHONY: pull
pull: ## Pull the latest images
	$(COMPOSE) pull

# ── Observability ──────────────────────────────────────────────────────────

.PHONY: logs
logs: ## Follow logs for all services
	$(COMPOSE) logs -f

.PHONY: logs-proxy
logs-proxy: ## Follow Traefik proxy logs only
	$(COMPOSE) logs -f proxy

.PHONY: ps
ps: ## Show container status
	$(COMPOSE) ps

# ── Maintenance ────────────────────────────────────────────────────────────

.PHONY: validate
validate: ## Validate docker-compose.yml syntax
	$(COMPOSE) config -q && echo "docker-compose.yml OK"

.PHONY: update
update: pull ## Pull latest images and recreate containers
	$(COMPOSE) up -d --remove-orphans
