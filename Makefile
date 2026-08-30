.PHONY: help install run migrate makemigrations shell superuser test

help:
	@echo "install         install python dependencies via uv"
	@echo "run             run the dev server"
	@echo "migrate         apply migrations"
	@echo "makemigrations  generate migrations"
	@echo "shell           open the django shell"
	@echo "superuser       create a django superuser"
	@echo "test            run tests"

install:
	uv sync

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
