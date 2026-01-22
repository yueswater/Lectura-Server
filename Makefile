.PHONY: lint run migrate tree help

.DEFAULT_GOAL := help

help:
	@echo "Available commands:"
	@echo "  make lint    - Run Ruff linter and formatter"
	@echo "  make run     - Start Django development server"
	@echo "  make migrate - Generate and apply database migrations"
	@echo "  make tree    - Display project structure (excluding junk)"

lint:
	poetry run ruff check . --fix
	poetry run ruff format .

run:
	poetry run python manage.py runserver

migrate:
	poetry run python manage.py makemigrations
	poetry run python manage.py migrate

tree:
	tree -I "migrations|__pycache__|fonts|*.jpg|*.pyc|.git|.venv|.*ttf|*.otf"

test:
	poetry run pytest

test-coverage:
	poetry run pytest --cov=. --cov-report=html

docker-up:
	$(MAKE) lint
	docker-compose up -d --build
	@echo "Waiting for database to be ready..."
	$(MAKE) docker-migrate

docker-migrate:
	docker-compose exec web python manage.py makemigrations
	docker-compose exec web python manage.py migrate

docker-test:
	docker-compose exec web pytest

docker-stop:
	docker-compose down

docker-logs:
	docker-compose logs -f web

docker-setup: docker-up docker-migrate docker-test