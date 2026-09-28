.PHONY: dev stop migrate seed test lint build logs

dev:
	docker compose up --build --wait --wait-timeout 180

stop:
	docker compose down

migrate:
	docker compose run --build --rm migrate

seed:
	@echo 'Seed появится на этапе 3 вместе с предметными таблицами.'
	@exit 1

test:
	docker compose run --build --rm api pytest
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
