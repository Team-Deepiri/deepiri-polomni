.PHONY: install test test-integration lint serve prove prove-strict falsify reproduce-p1 docker-up docker-down verify smoke frontend-install frontend-dev frontend-build

install:
	poetry install --with dev

test:
	poetry run python -m pytest tests/ -q -m "not integration"

test-integration:
	poetry run python -m pytest tests/ -q -m integration

lint:
	poetry run ruff check src tests

prove:
	poetry run polomni math prove

prove-strict:
	poetry run polomni math prove --strict

falsify:
	poetry run polomni falsify --real --fetch

reproduce-p1:
	bash scripts/reproduce-p1.sh

p1-gates:
	bash scripts/p1-gates.sh

p1-blind:
	poetry run polomni study run p1 --blind

serve:
	poetry run polomni serve --host 0.0.0.0 --port 8091

frontend-install:
	cd frontend && npm install

frontend-dev:
	cd frontend && npm run dev

frontend-build:
	cd frontend && npm run build

docker-up:
	docker compose -f docker/docker-compose.yml up -d polomni-lab

docker-down:
	docker compose -f docker/docker-compose.yml down

docker-reproduce:
	docker compose -f docker/docker-compose.yml --profile reproduce run --rm polomni-reproduce

verify:
	bash scripts/verify-stack.sh

smoke:
	bash scripts/smoke-pipeline.sh
