.PHONY: help install css-install css-build css-watch run migrate makemigrations shell superuser seed reseed test

help:
	@echo "install         install python dependencies via uv"
	@echo "css-install     download the tailwindcss binary + daisyUI (one-time)"
	@echo "css-build       compile static/css/output.css once"
	@echo "css-watch       compile static/css/output.css, watching for changes"
	@echo "run             run the dev server (needs css-build/css-install first)"
	@echo "migrate         apply migrations"
	@echo "makemigrations  generate migrations"
	@echo "shell           open the django shell"
	@echo "superuser       create a django superuser"
	@echo "seed            fill an empty database with demo data"
	@echo "reseed          wipe the domain data and reseed (asks first)"
	@echo "test            run tests"

install:
	uv sync

css-install:
	cd static/css && curl -sL daisyui.com/fast | bash

css-build:
	static/css/tailwindcss -i static/css/input.css -o static/css/output.css

css-watch:
	static/css/tailwindcss -i static/css/input.css -o static/css/output.css --watch

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

seed:
	uv run python manage.py seed_demo

reseed:
	uv run python manage.py seed_demo --reset

test:
	# empty DATABASE_URL keeps the tests on sqlite instead of creating a test database on Postgres
	DATABASE_URL= uv run python manage.py test
