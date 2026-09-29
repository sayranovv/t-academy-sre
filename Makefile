.PHONY: dev stop migrate seed test lint build logs types test-e2e

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

logs:
	docker compose logs --follow api web db migrate

types:
	docker compose run --build --rm web npm run types:api

test-e2e:
	docker compose --profile test rm -sf e2e-web e2e-api test-seed test-migrate db-test
	docker compose --profile test up --build --wait e2e-web
	cd frontend && npm run test:e2e
