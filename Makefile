# ── Configuration ──────────────────────────────────────────────────────────
PYTHON_VERSIONS    ?= 3.11 3.12
SCENARIOS_VALIDATE  = no_auth basic_auth authentik with_beszel
SCENARIOS_COMPOSE   = no_auth basic_auth authentik

IMAGE    = traefik-copier-test
WORK_DIR = $(shell pwd)

DOCKER_BASE = docker run --rm \
    -v $(WORK_DIR):/workspace:ro \
    -w /workspace

DOCKER_FULL = $(DOCKER_BASE) \
    -v /tmp:/tmp \
    -v /var/run/docker.sock:/var/run/docker.sock

.DEFAULT_GOAL := help

.PHONY: help
help:  ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-22s\033[0m %s\n", $$1, $$2}'

# ── Image ───────────────────────────────────────────────────────────────────
.PHONY: image-build
image-build:  ## Build test Docker image (Python 3.12)
	docker build -f Dockerfile.test -t $(IMAGE) .

# ── Lint  [CI: lint] ─────────────────────────────────────────────────────────
.PHONY: lint
lint: image-build  ## [CI: lint] Lint copier.yml and scenario answer files
	$(DOCKER_BASE) $(IMAGE) sh -c \
		"yamllint -d relaxed copier.yml && yamllint -d relaxed tests/scenarios/ && echo 'lint OK'"

# ── pytest  [CI: test] ───────────────────────────────────────────────────────
.PHONY: test
test:  ## [CI: test] Run pytest on Python 3.11 and 3.12
	@for pyver in $(PYTHON_VERSIONS); do \
		echo ""; \
		echo "════════════════════════════════════════"; \
		echo "  pytest · Python $$pyver"; \
		echo "════════════════════════════════════════"; \
		docker build -f Dockerfile.test --build-arg PYTHON_VERSION=$$pyver \
			-t $(IMAGE):py$$pyver -q . && \
		$(DOCKER_FULL) $(IMAGE):py$$pyver pytest tests/ -v --tb=short -o cache_dir=/tmp/pytest-cache || exit 1; \
	done

# ── Validate output  [CI: validate-output] ───────────────────────────────────
.PHONY: validate-output
validate-output: image-build  ## [CI: validate-output] Generate + validate YAML for all scenarios
	@for scenario in $(SCENARIOS_VALIDATE); do \
		$(DOCKER_FULL) $(IMAGE) bash scripts/validate-scenario.sh $$scenario || exit 1; \
	done

# ── Compose up  [CI: compose-up] ─────────────────────────────────────────────
.PHONY: compose-up
compose-up: image-build  ## [CI: compose-up] docker compose up/down for each scenario
	@for scenario in $(SCENARIOS_COMPOSE); do \
		$(DOCKER_FULL) $(IMAGE) bash scripts/compose-scenario.sh $$scenario || exit 1; \
	done

# ── Run all CI checks ────────────────────────────────────────────────────────
.PHONY: ci
ci: lint test validate-output compose-up  ## Run all CI checks (lint + test + validate-output + compose-up)

# ── Cleanup ──────────────────────────────────────────────────────────────────
.PHONY: clean
clean:  ## Remove generated test artifacts and test images
	docker run --rm -v /tmp:/tmp alpine sh -c \
		"rm -rf /tmp/traefik-copier-validate-* /tmp/traefik-copier-compose-*" \
		2>/dev/null || rm -rf /tmp/traefik-copier-validate-* /tmp/traefik-copier-compose-* || true
	docker rmi $(IMAGE) $(IMAGE):py3.11 $(IMAGE):py3.12 2>/dev/null || true
