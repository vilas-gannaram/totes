1. Install uv (one-time, does what nvm+npm do together):
   curl -LsSf https://astral.sh/uv/install.sh | sh
   You already have it installed, so skip this.
2. Init the project (like npm init):
   uv init --app --no-readme --name totes .
   Creates pyproject.toml — that's your package.json.
3. Add Django as a dependency (like npm install django):
   uv add django psycopg2-binary python-dotenv
   uv add creates .venv/ automatically and writes to pyproject.toml + uv.lock (your package-lock.json). No separate "activate" step needed if you always run things through uv run.
4. Scaffold the Django project (like npx create-react-app .):
   uv run django-admin startproject totes .
   The trailing . puts it at repo root instead of nesting a subfolder. This creates manage.py (your primary CLI — like npm run <script>, every Django command goes through it) and an totes/ package with settings.py (your central config, à la next.config.js) and urls.py (your router).
5. Run the dev server (like npm run dev):
   uv run python manage.py runserver
6. Create an "app" — Django's unit of a feature module (not a whole project, more like a Rails "resource" or a src/features/products folder):
   uv run python manage.py startapp products
   Then add "products" to INSTALLED_APPS in settings.py — Django doesn't auto-discover apps the way file-bas
