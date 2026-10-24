# Deploy: Supabase + Render + Vercel

## Order

1. **Supabase** — create project and database URL  
2. **Render** — deploy API, run migrations on start  
3. **Vercel** — deploy frontend with API proxy  
4. **Smoke test** — login and refresh (see below)

## 1. Supabase

1. Create a project at [supabase.com](https://supabase.com).
2. **Project Settings → Database → Connection string → Session pooler** (port **5432**).
3. Copy the URI (`postgresql://postgres.[ref]:[password]@...pooler.supabase.com:5432/postgres`).
4. Do **not** commit the password. Set it only on Render as `SUPABASE_DATABASE_URL`.

The backend accepts `postgres://` or `postgresql://` and enables SSL for Supabase hosts automatically.

## 2. Render (API)

**Option A — Blueprint:** New → Blueprint → connect repo → use [`render.yaml`](../render.yaml).

**Option B — Manual Web Service:**

| Setting | Value |
|---------|--------|
| Root / Docker context | `backend` |
| Dockerfile | `backend/Dockerfile` |
| Health check path | `/health` |

**Environment (required):**

| Variable | Notes |
|----------|--------|
| `SUPABASE_DATABASE_URL` | Session pooler URI from Supabase |
| `JWT_SECRET` | Long random string |
| `COOKIE_SECURE` | `true` |
| `CORS_ORIGINS` | Your Vercel URL, e.g. `https://skyreon.vercel.app` (add preview URLs if needed, comma-separated) |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | First admin login |
| `SUPER_ADMIN_EMAIL` / `SUPER_ADMIN_PASSWORD` | Optional super admin |

Start command is handled by [`backend/scripts/start-production.sh`](../backend/scripts/start-production.sh): `alembic upgrade head` then `uvicorn` on `$PORT`.

After deploy, open `https://<service>.onrender.com/health` → `{"status":"ok"}`.

## 3. Vercel (frontend)

1. Import repo; **Root Directory:** `frontend`.
2. **Environment variables:**

| Variable | Environment | Value |
|----------|-------------|--------|
| `NEXT_PUBLIC_API_URL` | Production | `https://<your-vercel-domain>` (same origin) |
| `API_PROXY_TARGET` | Production | `https://<your-render-service>.onrender.com` |
| `NEXT_PUBLIC_API_URL` | Preview (optional) | Preview URL |
| `API_PROXY_TARGET` | Preview | Same Render API URL |

3. Deploy. Browser calls `https://your-app.vercel.app/api/v1/...`; Vercel rewrites to Render ([`frontend/next.config.ts`](../frontend/next.config.ts)).

**Local dev:** do not set `API_PROXY_TARGET`; set `NEXT_PUBLIC_API_URL=http://localhost:8000`.

Update Render `CORS_ORIGINS` whenever you add a new Vercel preview domain you use for auth.

## 4. Smoke test

Replace URLs and credentials.

```bash
BASE=https://your-app.vercel.app
EMAIL=admin@skyreon.com
PASSWORD='your-admin-password'

# Health (Render direct)
curl -sf "https://your-api.onrender.com/health"

# Or use the script (same checks):
#   BASE=https://your-app.vercel.app API_DIRECT=https://your-api.onrender.com \
#   EMAIL=... PASSWORD=... ./scripts/smoke-production-auth.sh

BASE=https://your-app.vercel.app EMAIL=admin@skyreon.com PASSWORD='...' ./scripts/smoke-production-auth.sh
```

In the browser: open the Vercel URL → login → open Admin dashboard → confirm no 401/CORS errors in the network tab.

## Notes

- Render **free** tier sleeps; use **Starter** for scheduler jobs and steadier HRMS use.
- Supabase free tier has connection limits; one Render web service on the session pooler is usually enough.
- Postgres stays on Supabase only; do not add a Render Postgres service for this setup.
