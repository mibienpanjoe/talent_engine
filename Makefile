UV ?= uv
PNPM ?= pnpm
COMPOSE ?= docker compose

.PHONY: install api-test lint typecheck build contracts contracts-check up migrate down check
install:
	$(UV) sync --project apps/api --locked
	$(PNPM) install --frozen-lockfile
api-test:
	$(UV) run --project apps/api --locked pytest apps/api/tests
lint:
	$(UV) run --project apps/api --locked ruff check --config apps/api/pyproject.toml apps/api scripts
	$(UV) run --project apps/api --locked ruff format --check --config apps/api/pyproject.toml apps/api scripts
	$(PNPM) --filter @talent-engine/web lint
typecheck:
	$(PNPM) typecheck
build:
	$(PNPM) build
contracts:
	$(PNPM) contracts:generate
contracts-check:
	$(PNPM) contracts:check
up:
	$(COMPOSE) up --build -d
migrate:
	$(COMPOSE) run --rm migrate
down:
	$(COMPOSE) down
check: api-test lint contracts-check typecheck build

.PHONY: integration-test
integration-test:
	$(UV) run --project apps/api --locked pytest apps/api/integration

.PHONY: seed-access
seed-access:
	$(COMPOSE) run --rm seed-access

.PHONY: seed-demo
seed-demo:
	$(COMPOSE) run --rm seed-demo
