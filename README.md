# Totes

Inventory management system, built with Django.

## Stack

- Python 3.14, [uv](https://docs.astral.sh/uv/) for dependency management
- Django 6.1
- Postgres (Supabase) via `DATABASE_URL` in `.env` (see `.env.example`);
  without it the app falls back to sqlite (`db.sqlite3`)
- Server-rendered templates (Django templates)
- [daisyUI](https://daisyui.com/docs/install/django/) + Tailwind CSS
  (standalone binary, no Node.js) and self-hosted Manrope/Geist Mono fonts
  for styling. Several themes (Nord by default, plus Corporate, Emerald,
  Winter, Dim and the custom Depot) with a picker at the bottom of the
  sidebar; the choice is stored in the browser.

## Getting started

```
make install     # uv sync
make css-install  # download tailwindcss + daisyUI (one-time; no Node.js needed)
make css-build    # compile static/css/output.css
cp .env.example .env   # then set DATABASE_URL (skip to use sqlite)
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
make seed                                      # or: uv run python manage.py seed_demo
```

It is deterministic (fixed random seed), so every run builds the same data,
and the stock ledger is consistent: each inventory row's
`quantity_available` equals the sum of its `StockMovement` deltas. It
refuses to run on a database that already has data. To wipe the domain data
(users are kept) and reseed:

```
make reseed                                    # asks for confirmation
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
| `orders`     | `Order`, `OrderItem`           | list (status tabs), detail, new order  |
| `suppliers`  | `Supplier`                     | list                                   |
| `purchasing` | `PurchaseOrder`, `PurchaseOrderItem` | list (status tabs), detail       |

The dashboard lives at `/`, served from `config`.

```
config/       project settings, root URLs, dashboard view, seed_demo command
<app>/        the seven domain apps above
templates/    shared base.html, dashboard, placeholder, partials/ (root-level;
              per-app templates live in <app>/templates/<app>/)
static/       css/ (Tailwind + daisyUI build), fonts/ (Manrope + Geist Mono, self-hosted)
manage.py     Django's CLI entrypoint
```

## Workflows

Stock only changes through code that also writes the `StockMovement`
ledger, so every counter can be explained from history.

**Orders** (`orders/services.py`)

- *New order* (`/orders/new/`): pick a customer and up to six products. The
  order is created `PENDING` and the stock is reserved, taken from the
  warehouses holding the most first (`RESERVE` rows; available goes to
  reserved).
- *Order detail*: `PENDING` can be marked paid or cancelled, `PAID` shipped
  or cancelled. Shipping clears the reservation (a `SHIP` row with delta 0,
  since reserving already took the units out of available). Cancelling
  returns it (`RELEASE` rows). Other transitions are rejected.

**Purchase orders** (`purchasing/services.py`)

- `DRAFT` can be marked ordered or cancelled; `ORDERED` can be cancelled
  while nothing has been received.
- On an ordered PO, the *Receive now* boxes book units per line into the
  PO's warehouse (`RECEIPT` rows, creating the inventory row if needed).
  Partial receipts are fine; the PO becomes `RECEIVED` when every line is
  complete.
- *New purchase order* (`/purchasing/new/`): supplier, warehouse, optional
  expected date and product lines with quantity and unit cost. It is saved
  as a `DRAFT`; drafts (and only drafts) can be edited from their page.

## Common commands

See `make help` for the full list (`migrate`, `makemigrations`, `shell`,
`superuser`, `test`, ...). Run `make css-build` after changing templates or
`static/css/input.css`, and commit the regenerated `static/css/output.css`
(it is committed so deployments don't have to build it).

## Deploying to Vercel

Vercel detects the Django project from `manage.py` and runs the whole app as
one function; the database stays on Supabase.

1. Run `make css-build` and commit `static/css/output.css`, then push to GitHub.
2. Import the repo at vercel.com (framework: Django). `collectstatic` runs
   on deploy (`STATIC_ROOT` is set).
3. Set environment variables on the project (see `.env.example`):
   `DATABASE_URL` (use Supabase's **transaction pooler** string, port 6543),
   `SECRET_KEY` (required when `DEBUG` is off; Vercel defaults `DEBUG` to
   `False`), and optionally `ALLOWED_HOSTS` / `CSRF_TRUSTED_ORIGINS` for a
   custom domain (`*.vercel.app` is always allowed).
4. Migrations do not run on deploy: run `make migrate` from your machine
   with `DATABASE_URL` pointing at Supabase, and create the admin login with
   `make superuser`.

## Docs

- `schema.md` — data model (ERD), app grouping, and user journeys
- `TODO.md` — build roadmap
- `AUDIT.md` — audit findings and the UI page plan
- `LEARNING.md` — Django learning notes
