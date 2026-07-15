# WayPoint API

## Local run

Local development uses a SQLite file by default, so MySQL does not need to be installed.

### macOS

```bash
cd "project-path/backend"
python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -e .

cp .env.example .env
```

Generate a JWT secret and set it in `.env`:

```bash
openssl rand -hex 32
```

```env
DATABASE_URL=sqlite:///./drive_cafe.db
JWT_SECRET_KEY=the-generated-value
```

Create the SQLite schema and start the API:

```bash
alembic upgrade head
uvicorn app.main:app --reload
```

`backend/drive_cafe.db` is a local-only database and is excluded from Git. Check
`http://localhost:8000/health` and `http://localhost:8000/docs` after startup.

On subsequent runs, only activate the virtual environment and start Uvicorn:

```bash
cd "project-path/backend"
source .venv/bin/activate
uvicorn app.main:app --reload
```

Windows virtual environments cannot be reused on macOS; always create `.venv` on the Mac.

### MySQL deployment

Production can continue to use MySQL by replacing only `DATABASE_URL` in `.env`:

```env
DATABASE_URL=mysql+pymysql://drive_cafe:password@localhost:3306/drive_cafe?charset=utf8mb4
```

Run `alembic upgrade head` before starting the deployment.

Run project scripts from the `backend` directory with module syntax so the current worktree is
used even when the shared virtual environment has another editable checkout registered:

```powershell
python -m scripts.seed_catalog --path data/catalog.json
python -m scripts.set_admin --email you@example.com
```

Interactive API documentation is available at `/docs` in development.

## Social login contract

The Flutter app sends the provider credential to `POST /api/v1/auth/social/login`: a Google
ID token for Google, or a Kakao access token for Kakao. The API validates that credential,
maps it to an internal user, and returns the platform's own access and refresh tokens.
Provider credentials are never stored in the database.

## TMAP

Set `TMAP_APP_KEY` only in `.env`. The `app.integrations.tmap.TmapClient` is used for
short-lived geocoding checks and route estimates. Do not persist TMAP-derived location data
beyond the provider's permitted retention period.
