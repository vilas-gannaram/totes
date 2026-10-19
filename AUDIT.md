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
5. **No default ordering** (done: `sku`, `location_code`, `name, email`,
   `-created_at`) on `Product`, `Warehouse`, `Customer`,
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
| Layout | all | `templates/base.html` | dark sticky sidebar, theme picker (nord default), flash messages |
| Dashboard | `/` | `config.views.dashboard` | KPI cards, needs-reorder, stock value by category, recent movements, open POs |
| Inventory list | `/inventory/` | `inventory.views.inventory_list` | status tabs, search, category/warehouse filters, pagination |
| Products list | `/products/` | `products.views.product_list` | search, category filter, stock totals and status |
| Product detail | `/products/<uuid:pk>/` | `products.views.product_detail` | stock per warehouse, movement history |
| Warehouses list | `/warehouses/` | `warehouses.views.warehouse_list` | SKUs, units, stock value per warehouse |
| Customers list | `/customers/` | `customers.views.customer_list` | search, order count, last order |
| Suppliers list | `/suppliers/` | `suppliers.views.supplier_list` | search, PO count, last PO |
| Orders list | `/orders/` | `orders.views.order_list` | status tabs, customer search |
| Order detail | `/orders/<uuid:pk>/` | `orders.views.order_detail` | items, movements, pay / ship / cancel buttons |
| New order | `/orders/new/` | `orders.views.order_new` | customer + up to 6 lines, reserves stock |
| Purchase orders list | `/purchasing/` | `purchasing.views.purchase_order_list` | status tabs, supplier/warehouse search |
| Purchase order detail | `/purchasing/<uuid:pk>/` | `purchasing.views.purchase_order_detail` | items, movements, status buttons, receive form |
| New / edit purchase order | `/purchasing/new/`, `/purchasing/<uuid:pk>/edit/` | `purchasing.views.purchase_order_new`, `purchase_order_edit` | supplier, warehouse, expected date, lines; drafts only |

Status workflows live in `orders/services.py` and `purchasing/services.py`
(see `README.md`, "Workflows").

### Still to build

- Dashboard warehouse filter and search from the design, and the "Reorder"
  button.
- Create/edit forms (`ModelForm`) for products, warehouses, customers and
  suppliers.
- Design actions with no backend: "New product", "Reorder", "Export CSV",
  "Scan barcode". Decide per button whether to build (create form, CSV
  response) or drop.
- Mobile pass: sidebar collapse, tables scroll in a box.

## 4. Order of work

Steps 1-4 and the stock-changing flows (reserve, pay, ship, cancel,
receive) are done. What is left of step 5 is the create/edit forms.

1. Audit fixes 1-5 (small, one commit). Done.
2. Models: `suppliers`, `orders`, `purchasing` (one app at a time). Done.
3. Dashboard, Product detail, restyle products/warehouses. Done.
4. List/detail pages for the new apps. Done.
5. Forms, then stock-changing flows (reserve, ship, receive) through
   `StockMovement`. Flows done; forms done for orders and purchase orders,
   still to do for products, warehouses, customers and suppliers.
