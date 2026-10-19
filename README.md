# Totes

Inventory management system, built with Django.

## Stack

- Python 3.14, [uv](https://docs.astral.sh/uv/) for dependency management
- Django 6.1
- Postgres (Supabase) — not yet wired up, currently running on sqlite for
  local development
- Server-rendered templates (Django templates)
- [daisyUI](https://daisyui.com/docs/install/django/) + Tailwind CSS
  (standalone binary, no Node.js) and self-hosted Manrope/Geist Mono fonts
  for styling

## Getting started

```
make install     # uv sync
make css-install  # download tailwindcss + daisyUI (one-time; no Node.js needed)
make css-build    # compile static/css/output.css
make migrate      # apply migrations
make superuser    # create an admin login
make run          # start the dev server at http://127.0.0.1:8000/
```

While actively changing styles, run `make css-watch` instead of `css-build`
to recompile on save.

Admin panel: `http://127.0.0.1:8000/admin/`

## Demo data

To fill an empty database with believable sample data (3 warehouses, 40
products, stock, customers, suppliers, orders and purchase orders):

```
uv run python manage.py seed_demo
```

It is deterministic (fixed random seed), so every run builds the same data,
and the stock ledger is consistent: each inventory row's
`quantity_available` equals the sum of its `StockMovement` deltas. It
refuses to run on a database that already has data. To wipe the domain data
(users are kept) and reseed:

```
uv run python manage.py seed_demo --reset      # asks for confirmation
uv run python manage.py seed_demo --reset --yes
```

The command lives in `config/management/commands/seed_demo.py`.

## Project structure

Each domain area is its own Django app, with its own models, admin
registration, views, urls, and templates. Further work is tracked in
`TODO.md`.

| App          | Models                         | Pages                                  |
| ------------ | ------------------------------ | -------------------------------------- |
| `products`   | `Product`                      | list (filters, stock totals), detail   |
| `warehouses` | `Warehouse`                    | list                                   |
| `inventory`  | `Inventory`, `StockMovement`   | list (status tabs, filters, pagination) |
| `customers`  | `Customer`                     | list                                   |
| `orders`     | `Order`, `OrderItem`           | list                                   |
| `suppliers`  | `Supplier`                     | list                                   |
| `purchasing` | `PurchaseOrder`, `PurchaseOrderItem` | list                             |

The dashboard lives at `/`, served from `config`.

```
config/       project settings, root URLs, dashboard view, seed_demo command
<app>/        the seven domain apps above
templates/    shared base.html, dashboard, placeholder, partials/ (root-level;
              per-app templates live in <app>/templates/<app>/)
static/       css/ (Tailwind + daisyUI build), fonts/ (Manrope + Geist Mono, self-hosted)
manage.py     Django's CLI entrypoint
```

## Common commands

See `make help` for the full list (`migrate`, `makemigrations`, `shell`,
`superuser`, `test`, ...).

## Docs

- `schema.md` — data model (ERD), app grouping, and user journeys
- `TODO.md` — build roadmap
- `AUDIT.md` — audit findings and the UI page plan
- `LEARNING.md` — Django learning notes
