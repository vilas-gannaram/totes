# TODO

Roadmap for the Django rewrite of Totes (IMS). See `schema.md` for the full
ERD and rationale behind each model.

## Foundation

- [x] Init `uv` project, add Django/psycopg2/python-dotenv
- [x] Scaffold Django project (`config/`)
- [x] Makefile for common dev commands
- [ ] Wire `settings.py` to Supabase Postgres via env vars (currently still
      on sqlite3)
- [ ] `.env` / `.env.example` for `DATABASE_URL` (or `POSTGRES_*` split),
      `SECRET_KEY`
- [ ] Split settings into base/dev/prod if needed, or keep single file with
      env-driven `DEBUG`/`ALLOWED_HOSTS`

## Apps (domain modules)

- [x] `products` — `Product` (sku, name, category, unit_price, reorder_point),
      admin registration, SSR list view + template at `/products/`
- [x] `warehouses` — `Warehouse` (name, location_code), admin registration,
      SSR list view + template at `/warehouses/`
- [ ] `inventory` — `Inventory` (real FK to product + warehouse, unique
      together, quantity_available/reserved), `StockMovement` audit ledger
- [ ] `customers` — `Customer` (name, email, phone)
- [ ] `orders` — `Order` (status enum, total_amount), `OrderItem`
      (unit_price_at_order, unique with order+product)
- [ ] `suppliers` — `Supplier` (name, email, phone)
- [ ] `purchasing` — `PurchaseOrder` (status enum, warehouse, expected_at),
      `PurchaseOrderItem` (quantity_ordered/received, unit_cost)

## Schema fixes carried over from the old backend

- [ ] Real FK from `Inventory.warehouse_id` → `Warehouse` (was a plain string)
- [ ] Real FK from `Order.customer_id` → `Customer` (was a plain string)
- [ ] DB-level enum/choices for `Order.status` and `PurchaseOrder.status`
- [ ] Unique constraint on `(product_id, warehouse_id)` in `Inventory`
- [ ] Quantity check constraints (`quantity_available >= 0`, etc.)
- [ ] `updated_at` timestamps on `Inventory`, `Order`, `Product`

## Frontend

- [x] Use Django templates for SSR (internal-tool style); revisit a CSR
      frontend + DRF API later for any customer-facing UI
- [ ] Decide: root-level `templates/` dir (shared `base.html`, per-app
      subfolders) vs. current per-app `templates/<app>/` layout
- [ ] `base.html` with common layout, convert existing templates to
      `{% extends %}` it
- [ ] Consider [daisyUI via CDN](https://daisyui.com/docs/cdn/) for styling
      views instead of hand-rolled CSS

## Features

- [ ] Django admin registration for all models (fast internal CRUD)
- [ ] Stock movement ledger: every inventory change writes a
      `StockMovement` row (receipt, reserve, release, ship, adjust) instead
      of just overwriting the counter
- [ ] Low-stock alerting off `Product.reorder_point`
- [ ] Order lifecycle: place → reserve stock → pay → ship, with status
      transitions validated server-side
- [ ] Purchase order lifecycle: draft → ordered → received, receiving
      increments inventory via `StockMovement`
- [ ] API layer (DRF or plain views — TBD) for the above
- [ ] Migrate/replace any FastAPI endpoints still referenced elsewhere

## Later / not yet scoped

- [ ] Auth / permissions model (who can adjust stock, approve POs, etc.)
- [ ] Tests for model constraints and order/PO state transitions
- [ ] Deployment (prod WSGI/ASGI server — dev server warns it's not for
      production use)
