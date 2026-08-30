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
- Decided for this project: **both**, not either/or. A root-level
  `templates/` dir (wired via
  `TEMPLATES[0]["DIRS"] = [BASE_DIR / "templates"]`) holds shared chrome
  (`base.html`), while each app keeps its own `templates/<app>/` dir for
  its own views. `{% extends "base.html" %}` resolves via `DIRS` (checked
  before `APP_DIRS`), same as Nunjucks `extends`/EJS `include` in JS
  frameworks — Django just ships this natively.
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

## Foreign keys and DB-level constraints (from `inventory`)

- `models.ForeignKey("products.Product", on_delete=models.CASCADE)` — the
  `"app_label.Model"` string form avoids a circular import when the target
  app isn't imported directly; `on_delete` is required and decides what
  happens to this row when the referenced row is deleted (`CASCADE` deletes
  it too).
- `class Meta: constraints = [...]` is where real DB-level constraints live,
  as opposed to field kwargs that only validate at the Django/form layer:
  - `models.UniqueConstraint(fields=[...], name=...)` — multi-column
    uniqueness (`unique_together` on a single field isn't enough for
    "unique per product+warehouse").
  - `models.CheckConstraint(condition=models.Q(...), name=...)` — an actual
    SQL `CHECK`. Note: `PositiveIntegerField` only stops negative values
    from Django's own validation (forms/`full_clean()`) — it is **not** a
    DB-level check constraint by itself. Direct SQL or a
    `.update()`/bulk write can still slip a negative value in without
    `CheckConstraint`.
- `models.TextChoices` gives an enum-like field
  (`models.CharField(choices=MovementType.choices)`) without hand-writing a
  tuple-of-tuples — still just a `CharField` with an app-level constraint,
  not a real Postgres `ENUM` type (that's still an open TODO item for
  `Order.status`/`PurchaseOrder.status`).
- `related_name="movements"` on a FK controls the reverse accessor name
  (`inventory_obj.movements.all()`); without it Django defaults to
  `<lowercased-model-name>_set`.

## Static files and the daisyUI/Tailwind build

- `django.contrib.staticfiles`'s `AppDirectoriesFinder` only auto-discovers
  each app's own `static/` dir — a project-root `static/` dir needs
  `STATICFILES_DIRS = [BASE_DIR / "static"]` in `settings.py`, same
  reasoning as `TEMPLATES[0]["DIRS"]` for the shared `templates/` dir.
- Tailwind's CDN ("Play") build doesn't support plugins at all (confirmed
  when trying to add `@tailwindcss/typography`) — the real install uses a
  standalone `tailwindcss` binary + daisyUI's `.mjs` bundle, no Node.js
  needed, compiling a real `output.css` served via `{% static %}`.
- Gotcha: Tailwind v4's automatic content/class detection uses the
  **working directory the build command runs from** to find the project
  root, not just the input CSS file's location. Running the compiler from
  inside `static/css/` (as the one-time installer script does, since it
  `cd`s there first) means it never scans `templates/`, `products/`, etc.,
  so daisyUI/Tailwind classes silently don't get generated. The `Makefile`
  targets (`css-build`/`css-watch`) run from the repo root specifically to
  avoid this — always rebuild via `make`, not by cd-ing into `static/css/`.
- The downloaded `tailwindcss` binary and generated `daisyui.mjs` /
  `daisyui-theme.mjs` / `output.css` are gitignored build artifacts (like
  `.venv/`) — `input.css` (the actual source config) is the only tracked
  file in `static/css/`, regenerated via `make css-install` + `css-build`.
- Fonts (Geist/Geist Mono) are self-hosted `.woff2` files under
  `static/fonts/`, wired in via `@font-face` + a Tailwind `@theme` block
  overriding `--font-sans`/`--font-mono` in `input.css` — same
  no-CDN-dependency reasoning as the Tailwind/daisyUI switch.
