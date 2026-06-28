.PHONY: install test test-integration lint serve docker-up docker-down verify smoke

install:
	poetry install --with dev

test:
	poetry run python -m pytest tests/ -q -m "not integration"

test-integration:
	poetry run python -m pytest tests/ -q -m integration

lint:
	poetry run ruff check src tests

serve:
	poetry run polomni serve --host 0.0.0.0 --port 8091

docker-up:
	docker compose -f docker/docker-compose.yml up -d polomni-lab

docker-down:
	docker compose -f docker/docker-compose.yml down

verify:
	bash scripts/verify-stack.sh

smoke:
	bash scripts/smoke-pipeline.sh
