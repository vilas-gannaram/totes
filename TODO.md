# TODO

Build roadmap for Totes (IMS). See `schema.md` for the full ERD and
rationale behind each model. `AUDIT.md` has the detail behind the audit and
UI items below.

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
- [x] `inventory` — `Inventory` (real FK to product + warehouse, unique
      together, quantity_available/reserved), `StockMovement` audit ledger,
      admin registration, SSR list view + template at `/inventory/`
- [x] `customers` — `Customer` (name, email, optional phone), admin
      registration
- [x] `orders` — `Order` (status choices, total_amount), `OrderItem`
      (unit_price_at_order, unique with order+product), admin with items
      inline
- [x] `suppliers` — `Supplier` (name, email, optional phone; email not
      unique), admin registration
- [x] `purchasing` — `PurchaseOrder` (status choices, supplier, warehouse,
      optional expected_at), `PurchaseOrderItem` (quantity_ordered/received,
      unit_cost, unique with purchase_order+product), admin with items inline

## Schema constraints

- [x] Real FK from `Inventory.warehouse` → `Warehouse`
- [x] Real FK from `Order.customer` → `Customer`
- [x] Choices for `Order.status` (`TextChoices`)
- [x] Choices for `PurchaseOrder.status` (`TextChoices`)
- [x] Unique constraint on `(product_id, warehouse_id)` in `Inventory`
- [x] Quantity check constraints (`quantity_available >= 0`, etc.) on
      `Inventory`
- [x] `updated_at` timestamp on `Order` (`Product` and `Inventory` have it)

## Frontend

- [x] Use Django templates for SSR (internal-tool style); revisit a CSR
      frontend + DRF API later for any customer-facing UI
- [x] Root-level `templates/` dir for shared `base.html`, kept alongside
      per-app `templates/<app>/` dirs for per-app content
- [x] `base.html` with common layout (nav + `{% block content %}`),
      existing templates converted to `{% extends %}` it
- [x] Use [daisyUI](https://daisyui.com/docs/install/django/) (standalone
      `tailwindcss` binary + `.mjs` bundle, no Node.js) for styling views
      instead of hand-rolled CSS
- [x] Self-host Manrope / Geist Mono (`static/fonts/`) as `--font-sans` /
      `--font-mono`, instead of a font CDN

### UI redesign (from the Claude design: Dashboard, Inventory, Product detail)

- [x] Custom light daisyUI theme (`depot`) + dark sidebar layout in
      `base.html`, active nav state via `request.resolver_match`
- [x] Inventory list restyle: status tabs (All / In stock / Low / Out),
      search, category + warehouse filters as `?status=&q=&category=&warehouse=`
      query params handled in the view, `Paginator`, status badges,
      `font-mono` on SKU/quantity/money columns
- [x] Derive stock status (in stock / low / out) from `quantity_available`
      vs `Product.reorder_point`; shown as "Unit price" (no separate cost field)
- [x] Dashboard page (`/`): KPI cards (SKUs, stock value, low stock, out of
      stock, open purchase orders), "Needs reorder" table, stock value by
      category, recent `StockMovement` list; nav link
- [ ] Dashboard: warehouse filter and search from the design, "Reorder"
      button (needs the purchasing workflow)
- [x] Placeholder pages for every sidebar link (Customers, Orders,
      Suppliers, Purchasing); replace each with the real page
- [x] Product detail page (`/products/<id>/`): per-warehouse stock,
      movement history; linked from the products and inventory lists
- [x] Restyle products list: search, category filter, pagination, stock
      totals and status (shared `partials/pagination.html`)
- [x] Restyle warehouses list page to match (SKUs, units, stock value per warehouse)
- [x] Nav entries for Customers / Orders / Suppliers / Purchasing as each
      app gets its pages (Shipments and Reports are in the design but not
      scoped); dashboard "Open purchase orders" card depends on `purchasing`
- [x] List pages for the new apps (see `AUDIT.md` §3): customers, orders
      (status tabs), suppliers, purchase orders (status tabs)
- [x] Detail pages: order, purchase order (read-only; items + ledger movements)
- [x] New order form (`/orders/new/`): customer + up to 6 lines, reserves stock via `place_order`, writes RESERVE ledger rows
- [ ] Decide the design's action buttons: New product, Reorder, Export CSV,
      Scan barcode (build or drop each)
- [ ] `ModelForm`s for create/edit, plus flash messages
- [ ] Mobile pass: sidebar collapse, tables scroll in a box

## Features

- [x] Admin registration for every model (fast internal CRUD); line items
      (`OrderItem`, `PurchaseOrderItem`) are edited as inlines on their parent
- [ ] Stock movement ledger: every inventory change writes a
      `StockMovement` row (receipt, reserve, release, ship, adjust) instead
      of just overwriting the counter
- [x] Low-stock "Needs reorder" panel on the dashboard (status logic in
      `inventory.views.with_status`)
- [x] Order lifecycle: place → reserve stock → pay → ship (or cancel and
      release), transitions validated server-side in `orders.services`
- [ ] `seed_demo` shipped orders log `SHIP -qty`, but the real flow logs
      `SHIP 0` after `RESERVE -qty`; align the seed with the real flow
- [ ] Purchase order lifecycle: draft → ordered → received, receiving
      increments inventory via `StockMovement`

## Dev tooling

- [x] `seed_demo` management command: deterministic demo data with a
      consistent stock ledger (`--reset` to wipe and reseed); see `README.md`
- [ ] `make seed` / `make reseed` shortcuts in the `Makefile`
- [ ] Keep `seed_demo` in step with the models as they change (new fields,
      the order and purchasing workflows)

## Audit fixes (see `AUDIT.md` §1)

- [ ] `Inventory` `verbose_name_plural = "inventory"` (admin shows
      "Inventorys")
- [x] `list_select_related` on `InventoryAdmin` and `StockMovementAdmin`
- [x] `search_fields` on `InventoryAdmin` and `StockMovementAdmin`
- [x] Make the `StockMovement` admin add-only (no change/delete)
- [x] Default `Meta.ordering` on `Product`, `Warehouse`, `Customer`,
      `StockMovement`
- [ ] Admin add of `StockMovement` doesn't update the `Inventory` counter;
      route adjustments through code that writes both together
- [ ] `unit_price >= 0` check constraint on `Product`
- [ ] Tests for `products` and `warehouses` (inventory list view is covered)
- [ ] Consider a `Category` model instead of free-text `Product.category`

## Later / not yet scoped

- [ ] API layer (DRF or plain views) if anything outside the web UI needs it
- [ ] Auth / permissions model (who can adjust stock, approve POs, etc.)
- [ ] Tests for model constraints and order/PO state transitions
- [ ] Deployment (prod WSGI/ASGI server — dev server warns it's not for
      production use)
