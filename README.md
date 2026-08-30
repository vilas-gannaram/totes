# Totes

Inventory management system, built with Django.

## Stack

- Python 3.14, [uv](https://docs.astral.sh/uv/) for dependency management
- Django 6.1
- Postgres (Supabase) — not yet wired up, currently running on sqlite for
  local development
- Server-rendered templates (Django templates)

## Getting started

```
make install    # uv sync
make migrate    # apply migrations
make superuser  # create an admin login
make run        # start the dev server at http://127.0.0.1:8000/
```

Admin panel: `http://127.0.0.1:8000/admin/`

## Project structure

Each domain area is its own Django app (`products`, and more to come per
`TODO.md`), with its own models, admin registration, views, urls, and
templates.

```
config/       project settings, root URL config
products/     product catalog app
manage.py     Django's CLI entrypoint
```

## Common commands

See `make help` for the full list (`migrate`, `makemigrations`, `shell`,
`superuser`, `test`, ...).

## Docs

- `schema.md` — current and proposed data model (ERDs)
- `TODO.md` — build roadmap
