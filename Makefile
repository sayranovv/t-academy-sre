.PHONY: dev stop migrate seed test lint build logs types test-e2e prod prod-stop prod-seed prod-logs

PROD_COMPOSE = docker compose --env-file .env.production -f compose.production.yaml

dev:
	docker compose up --build --wait --wait-timeout 180

stop:
	docker compose down

migrate:
	docker compose run --build --rm migrate

seed:
	docker compose run --rm api python -m app.seed

test:
	docker compose --profile test run --build --rm test-api
	docker compose run --build --rm --no-deps web npm test

lint:
	docker compose run --build --rm --no-deps api ruff check .
	docker compose run --rm --no-deps api ruff format --check .
	docker compose run --build --rm --no-deps web npm run typecheck
	docker compose run --rm --no-deps web npm run lint

build:
	docker compose build
	docker compose run --rm --no-deps web npm run build
	POSTGRES_PASSWORD=build_only docker compose -f compose.production.yaml build

logs:
	docker compose logs --follow api web db migrate

types:
	docker compose run --build --rm web npm run types:api

test-e2e:
	docker compose --profile test rm -sf e2e-web e2e-api test-seed test-migrate db-test
	docker compose --profile test up --build --wait e2e-web
	cd frontend && npm run test:e2e

prod:
	$(PROD_COMPOSE) up --build --wait --wait-timeout 180

prod-stop:
	$(PROD_COMPOSE) down

prod-seed:
	$(PROD_COMPOSE) run --rm api python -m app.seed

prod-logs:
	$(PROD_COMPOSE) logs --follow api web db migrate
