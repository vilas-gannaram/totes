# AtlasIMS — Current Data Schema

Reflects `backend/app/modules/*/models.py` as of the latest commit. This is
the schema _as implemented_, including the gaps called out at the bottom.

```mermaid
erDiagram
    PRODUCTS {
        uuid id PK
        string sku UK
        string name
        datetime created_at
    }

    WAREHOUSES {
        uuid id PK
        string name
        string location_code UK
    }

    INVENTORY {
        uuid id PK
        uuid product_id FK
        string warehouse_id "not a real FK"
        int quantity_available
        int quantity_reserved
    }

    ORDERS {
        uuid id PK
        string customer_id "not a real FK"
        string status
        datetime created_at
    }

    ORDER_ITEMS {
        uuid id PK
        uuid order_id FK
        uuid product_id FK
        int quantity
    }

    PRODUCTS ||--o{ INVENTORY : "stock_levels"
    PRODUCTS ||--o{ ORDER_ITEMS : "ordered as"
    ORDERS ||--o{ ORDER_ITEMS : "items"
    WAREHOUSES ||--o{ INVENTORY : "holds (unwired)"
```

## Notes / known gaps

- `Inventory.warehouse_id` is a plain `String`, **not** a foreign key to
  `warehouses.id` — the dotted relationship above isn't enforced in the
  database today.
- `Orders.customer_id` is a plain `String` — there's no `Customer` table.
- `Order.status` is free text (`PENDING`/`PAID`/`SHIPPED`/`CANCELLED` by
  convention only, not a DB-level enum/check constraint).
- No unique constraint on `(product_id, warehouse_id)` in `inventory`, so
  duplicate stock rows for the same product/warehouse are possible.
- No quantity check constraints (e.g. `quantity_available >= 0`).
- No `unit_price` on `OrderItem`, and no price field on `Product` at all.
- No `updated_at` timestamps on `Inventory` or `Order`.

---

# Proposed Schema (Enhanced)

Fixes every gap above, and adds the pieces a real IMS needs: customers,
suppliers, purchase orders (inbound stock), and a stock-movement ledger so
inventory changes are auditable instead of just an overwritten counter.

```mermaid
erDiagram
    PRODUCTS {
        uuid id PK
        string sku UK
        string name
        string category
        numeric unit_price
        int reorder_point
        datetime created_at
        datetime updated_at
    }

    WAREHOUSES {
        uuid id PK
        string name
        string location_code UK
        datetime created_at
    }

    INVENTORY {
        uuid id PK
        uuid product_id FK
        uuid warehouse_id FK
        int quantity_available
        int quantity_reserved
        datetime updated_at
        "unique (product_id, warehouse_id)"
    }

    STOCK_MOVEMENTS {
        uuid id PK
        uuid inventory_id FK
        enum movement_type "RECEIPT, RESERVE, RELEASE, SHIP, ADJUST"
        int quantity_delta
        string reference_type "ORDER, PURCHASE_ORDER, MANUAL"
        uuid reference_id
        datetime created_at
    }

    CUSTOMERS {
        uuid id PK
        string name
        string email UK
        string phone
        datetime created_at
    }

    ORDERS {
        uuid id PK
        uuid customer_id FK
        enum status "PENDING, PAID, SHIPPED, CANCELLED"
        numeric total_amount
        datetime created_at
        datetime updated_at
    }

    ORDER_ITEMS {
        uuid id PK
        uuid order_id FK
        uuid product_id FK
        int quantity
        numeric unit_price_at_order
        "unique (order_id, product_id)"
    }

    SUPPLIERS {
        uuid id PK
        string name
        string email
        string phone
        datetime created_at
    }

    PURCHASE_ORDERS {
        uuid id PK
        uuid supplier_id FK
        uuid warehouse_id FK
        enum status "DRAFT, ORDERED, RECEIVED, CANCELLED"
        datetime expected_at
        datetime created_at
    }

    PURCHASE_ORDER_ITEMS {
        uuid id PK
        uuid purchase_order_id FK
        uuid product_id FK
        int quantity_ordered
        int quantity_received
        numeric unit_cost
    }

    PRODUCTS ||--o{ INVENTORY : "stocked as"
    WAREHOUSES ||--o{ INVENTORY : "holds"
    INVENTORY ||--o{ STOCK_MOVEMENTS : "logs"

    CUSTOMERS ||--o{ ORDERS : "places"
    ORDERS ||--o{ ORDER_ITEMS : "contains"
    PRODUCTS ||--o{ ORDER_ITEMS : "ordered as"

    SUPPLIERS ||--o{ PURCHASE_ORDERS : "fulfills"
    WAREHOUSES ||--o{ PURCHASE_ORDERS : "received at"
    PURCHASE_ORDERS ||--o{ PURCHASE_ORDER_ITEMS : "contains"
    PRODUCTS ||--o{ PURCHASE_ORDER_ITEMS : "restocks"
```

## What changed vs. the current schema

- **`Inventory.warehouse_id` is a real FK** to `warehouses.id`, with a unique
  constraint on `(product_id, warehouse_id)` so stock can't fork into
  duplicate rows.
- **`Customer` is a real table**, referenced by `Orders.customer_id` — no
  more free-text customer identifiers.
- **`Order.status` and `PurchaseOrder.status` become DB-level enums**
  instead of unchecked strings.
- **`StockMovements`** gives an append-only audit ledger for every quantity
  change (receipt, reservation, shipment, manual adjustment), so
  `quantity_available`/`quantity_reserved` are derived/verifiable instead of
  the only source of truth.
- **Pricing is modeled**: `Product.unit_price` as the current price, and
  `OrderItem.unit_price_at_order` to freeze the price actually charged so
  later price changes don't rewrite history.
- **Inbound stock is modeled** via `Supplier` → `PurchaseOrder` →
  `PurchaseOrderItem`, mirroring the existing `Order`/`OrderItem` shape for
  outbound stock — without it there's no way to represent how inventory
  ever gets replenished.
- **`updated_at` timestamps** added to `Inventory`, `Orders`, and `Products`
  so changes are traceable.
- **`reorder_point`** on `Product` gives a hook for low-stock alerts, a
  standard IMS feature that's currently absent entirely.
