# Django Learning Notes

Running notes from building the `products` app end-to-end. Concepts here
apply the same way to every future app (`warehouses`, `inventory`, etc.).

## Apps

A Django "app" is the unit that maps to what the old FastAPI backend called
a "module" — a self-contained slice of a domain with its own models, admin
registration, views, and migrations.

- `uv run python manage.py startapp <name>` scaffolds the folder
  (`models.py`, `admin.py`, `views.py`, `apps.py`, `migrations/`).
- Scaffolding the folder isn't enough — the app must be added to
  `INSTALLED_APPS` in `config/settings.py`, or Django never sees its models,
  admin registrations, or anything else in it.

## Models → migrations → database

- A model is a Python class in `models.py` subclassing `models.Model`. Each
  field becomes a column; the whole class becomes a table.
- Field types matter: `DecimalField` for money (never `FloatField`, binary
  float rounding), `PositiveIntegerField` for non-negative counts,
  `DateTimeField(auto_now_add=True)` (set once, on creation) vs.
  `auto_now=True` (updated every save).
- `unique=True` on a field enforces a DB-level unique constraint.
- Default table name is `<app_label>_<model_name>` lowercased (e.g.
  `products_product`). Override with `class Meta: db_table = "..."` if
  wanted — not necessary, just an app-prefix convention that avoids
  collisions across apps.
- `makemigrations` diffs your models against the last migration state and
  writes a new migration file (plain Python, declarative `operations` list)
  — it does NOT touch the database.
- `migrate` is the separate step that actually applies migrations to the
  database.

## Admin

- Registering a model in `admin.py` via `@admin.register(Model)` gets you a
  full CRUD UI at `/admin/` for free — no views/urls/templates needed.
- `list_display` controls which columns show in the list view;
  `search_fields` adds a search box.
- Requires a superuser (`manage.py createsuperuser`) to log in.
- Good for internal/staff use — not meant to be the app's real user-facing
  interface.

## URLs, views, templates (SSR)

Three pieces, wired together:

1. **`config/urls.py`** (project-level router) — `include()` hands off a URL
   prefix to an app's own URL file:
   ```python
   path("products/", include("products.urls")),
   ```
   Trailing slash matters — `"products"` vs `"products/"` changes what
   matches.

2. **`<app>/urls.py`** (app-level router, not scaffolded by `startapp` —
   create it yourself) — maps paths *relative to the prefix already
   consumed* to view functions:
   ```python
   path("", views.product_list, name="product-list")
   ```

3. **`<app>/views.py`** — a function taking `request`, returning a response.
   `render(request, template_name, context_dict)` is the shortcut for
   "look up this template, render it with this context, wrap in an
   HttpResponse."

### Template lookup and `APP_DIRS`

- `TEMPLATES[0]["APP_DIRS"] = True` means Django also searches every
  installed app's own `templates/` folder, in addition to
  `TEMPLATES[0]["DIRS"]` (project-wide templates, e.g. a shared
  `base.html`).
- All apps' `templates/` dirs get flattened into **one merged pool** — two
  apps both having `list.html` would collide, and Django would silently
  return whichever it finds first in `INSTALLED_APPS` order.
- Convention to avoid that: nest an app-name subfolder,
  `products/templates/products/list.html`, then reference it as
  `"products/list.html"` in `render()`. Skippable while there's only one
  app; worth revisiting once multiple apps have templates.
- Alternative layout: single root-level `templates/` dir with per-app
  subfolders (`templates/products/...`), wired via
  `TEMPLATES[0]["DIRS"] = [BASE_DIR / "templates"]`. Better home for shared
  chrome like `base.html`. Not yet decided for this project — tracked in
  `TODO.md`.
- Django does NOT inject any HTML boilerplate into templates — a template
  is rendered exactly as written, doctype/head/body included, nothing
  implicit.

## SSR CRUD pattern (HTML forms only support GET/POST)

Unlike a REST API, there's no native `PUT`/`PATCH`/`DELETE` from an HTML
form — so the same URL typically branches on `request.method`:

- List — `GET /products/`
- Detail — `GET /products/<id>/`
- Create — `GET /products/new/` renders an empty form, `POST` to the same
  URL processes the submission
- Update — `GET /products/<id>/edit/` renders a pre-filled form, `POST`
  saves it
- Delete — `POST /products/<id>/delete/` (never a plain GET link — GET
  requests shouldn't have side effects)

Django's generic class-based views (`ListView`, `DetailView`, `CreateView`,
`UpdateView`, `DeleteView`) implement this GET/POST-branching pattern with
far less boilerplate once the manual version is understood.

## SSR vs. CSR

Django templates render HTML server-side — good fit for internal/low-
interactivity tools (this project, for now). A customer-facing product with
rich interactivity would want a CSR/SPA frontend talking to a JSON API
(e.g. Django REST Framework) instead. Not mutually exclusive — the same
models can back both an SSR admin-style UI and a JSON API later.
