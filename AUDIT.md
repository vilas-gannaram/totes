# Audit and UI plan

Written 2026-10-18, after the `customers` app. Two parts: problems found in
the apps built so far, and the pages/views we want to build. Roadmap
checkboxes live in `TODO.md`; this file holds the detail behind them.

## 1. Audit of built apps

Apps reviewed: `products`, `warehouses`, `inventory`, `customers`.

### Fix now

1. **Wrong admin plural.** `Inventory` shows as "Inventorys" in the admin.
   Add `verbose_name_plural = "inventory"` to `Inventory.Meta` (needs a
   migration, label only, no table change).
2. **N+1 queries in admin lists.** `InventoryAdmin` shows `product` and
   `warehouse`; `StockMovementAdmin` shows `inventory`, whose `__str__`
   loads product and warehouse. Add `list_select_related`:
   - `InventoryAdmin`: `("product", "warehouse")`
   - `StockMovementAdmin`: `("inventory__product", "inventory__warehouse")`
3. **No admin search** on `InventoryAdmin` / `StockMovementAdmin`. Add
   `search_fields` (e.g. `product__sku`, `product__name`).
4. **Ledger is editable in admin.** `StockMovement` is meant to be
   append-only. Make the admin read-only (`has_change_permission` and
   `has_delete_permission` return `False`).
5. **No default ordering** on `Product`, `Warehouse`, `Customer`,
   `StockMovement`. Unordered lists are unstable, especially paginated
   ones. Add `Meta.ordering` (e.g. `["sku"]`, `["location_code"]`,
   `["name"]`, `["-created_at"]`).

### Later

6. `Product.unit_price` has no `>= 0` check constraint (the `Inventory`
   quantities do).
7. `Product.category` is free text ("Hardware" vs "hardware" are different
   categories). Consider a `Category` model.
8. `products` and `warehouses` have empty `tests.py`.
9. `check --deploy` warnings (debug on, empty `ALLOWED_HOSTS`, insecure
   secret key, no HTTPS settings). Production deployment, already in
   `TODO.md`.

## 2. Conventions

| Thing | Rule | Example |
|---|---|---|
| App name | plural noun; uncountable nouns stay as is | `products`, `inventory` |
| Model class | singular CapWords | `Product`, `StockMovement` |
| Primary key | `id = UUIDField(primary_key=True, default=uuid4, editable=False)` | |
| Foreign key | singular name of the target | `product`, `warehouse` |
| View | `<model>_<action>` | `product_list` |
| URL name | kebab-case `<model>-<action>` | `product-list` |
| URL mount | the app name | `/products/` |
| Template | `<app>/templates/<app>/<action>.html` | `products/list.html` |
| Admin class | `<Model>Admin` | `WarehouseAdmin` |
| Imports | relative inside an app, absolute across apps | `from .models import Customer` |
| Misc | every model has `__str__`; status fields use `TextChoices` | |

Exception: `inventory` stays singular because "inventory" is a mass noun.

## 3. UI plan

Source: the Claude design (Dashboard, Inventory, Product detail). Stack:
Django templates + Tailwind/daisyUI (`depot` theme), fonts Manrope and
Geist Mono. Server-rendered; filters are query params, no JS framework.

### Done

| Page | URL | View | Notes |
|---|---|---|---|
| Layout | all | `templates/base.html` | dark sidebar, light theme |
| Inventory list | `/inventory/` | `inventory.views.inventory_list` | status tabs, search, category/warehouse filters, pagination |

### From the design, still to build

| Page | URL | View | Data |
|---|---|---|---|
| Dashboard | `/` | `dashboard` (new, small app or `config`) | KPI cards: total SKUs, stock value, low, out of stock. "Needs reorder" table (reuse `with_status`). Stock value by category. Recent `StockMovement` list. "Open purchase orders" card once `purchasing` exists. |
| Product detail | `/products/<uuid:pk>/` | `products.views.product_detail` | product fields, stock per warehouse, movement history; linked from inventory rows |
| Products list restyle | `/products/` | `product_list` | match the inventory table style |
| Warehouses list restyle | `/warehouses/` | `warehouse_list` | same |

Design actions with no backend yet: "New product", "Reorder" button on the
dashboard, "Export CSV", "Scan barcode". Decide per button whether to build
(create form, CSV response) or drop.

### Proposed for the remaining apps (not in the design)

| Page | URL | App | Notes |
|---|---|---|---|
| Customers list | `/customers/` | `customers` | search by name/email |
| Orders list | `/orders/` | `orders` | status tabs (Pending/Paid/Shipped/Cancelled) |
| Order detail | `/orders/<uuid:pk>/` | `orders` | items, totals, status transitions |
| New order | `/orders/new/` | `orders` | pick customer, add items; reserves stock |
| Suppliers list | `/suppliers/` | `suppliers` | |
| Purchase orders list | `/purchasing/` | `purchasing` | status tabs (draft/ordered/received) |
| Purchase order detail | `/purchasing/<uuid:pk>/` | `purchasing` | receive action writes `StockMovement` |

Cross-cutting: forms for create/edit (Django `ModelForm`), flash messages,
sidebar entries for each new app, mobile pass (sidebar collapse, tables
scroll in a box).

## 4. Order of work

1. Audit fixes 1-5 (small, one commit).
2. Models: `suppliers`, `orders`, `purchasing` (one app at a time).
3. Dashboard, Product detail, restyle products/warehouses.
4. List/detail pages for the new apps.
5. Forms, then stock-changing flows (reserve, ship, receive) through
   `StockMovement`.
