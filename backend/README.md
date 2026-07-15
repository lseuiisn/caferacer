# WayPoint API

## Local run

1. Create a MySQL database named `drive_cafe` using `utf8mb4`.
2. Copy `.env.example` to `.env` and set secrets and provider keys.
3. Install dependencies with `pip install -e .`.
4. Run `alembic upgrade head`.
5. Run `uvicorn app.main:app --reload`.

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
