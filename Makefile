.PHONY: help install up down logs run migrate makemigrations shell superuser test

help:
	@echo "install         install python dependencies via uv"
	@echo "up              start postgres in the background"
	@echo "down            stop postgres"
	@echo "logs            tail postgres logs"
	@echo "run             run the dev server"
	@echo "migrate         apply migrations"
	@echo "makemigrations  generate migrations"
	@echo "shell           open the django shell"
	@echo "superuser       create a django superuser"
	@echo "test            run tests"

install:
	uv sync

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f postgres

run:
	uv run python manage.py runserver

migrate:
	uv run python manage.py migrate

makemigrations:
	uv run python manage.py makemigrations

shell:
	uv run python manage.py shell

superuser:
	uv run python manage.py createsuperuser

test:
	uv run python manage.py test
