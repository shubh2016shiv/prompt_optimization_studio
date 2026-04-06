# APOST Full-Stack Runbook (Local, Professional Setup)

This repository already supports a clean full-stack runtime through Docker Compose:

- `redis` container for durable job/state storage
- `apost` container for backend API **and** production-built frontend UI

That means one host port (`8000`) serves the complete app:

- UI: `http://127.0.0.1:8000`
- API: `http://127.0.0.1:8000/api/*`

## Why this is the best local setup

This mirrors a common enterprise pattern for non-production environments:

- Single edge service (`apost`) for predictable routing and no frontend/backend port confusion
- Dedicated dependency container (`redis`) with health checks
- Explicit startup ordering (`apost` waits until Redis is healthy)
- Repeatable lifecycle commands (`up/down/status/logs`)

It is stable, easier to support, and removes local "works on my machine" drift.

## One-command operator flow

From project root:

```powershell
python .\run_apost_fullstack.py up
```

or directly:

```powershell
npm run fullstack:up
```

On macOS/Linux:

```bash
python ./run_apost_fullstack.py up
```

The script will:

1. Verify Docker is running.
2. Ensure `backend/.env` exists (creates it from `backend/.env.example` if missing).
3. Build and start `redis` + `apost`.
4. Wait for `http://127.0.0.1:8000/api/health/live`.
5. Print ready-to-use URLs.

## Daily operations

```powershell
# Start full stack (rebuild images)
python .\run_apost_fullstack.py up

# Tail service logs
python .\run_apost_fullstack.py logs

# Show running service status
python .\run_apost_fullstack.py status

# Stop and clean containers
python .\run_apost_fullstack.py down
```

Npm wrappers:

```powershell
npm run fullstack:up
npm run fullstack:status
npm run fullstack:logs
npm run fullstack:down
```

## Environment and secrets

- Runtime env is loaded from `backend/.env` via `docker-compose.yml`.
- Keep non-secret defaults in `backend/.env.example`.
- If you want optional provider-level health probes, add keys to `backend/.env`:
  - `OPENAI_API_KEY`
  - `GOOGLE_API_KEY`

Note: User API keys are still accepted per request in the UI and are not stored by default.

## Architecture snapshot

```text
Browser
  |
  v
localhost:8000  --->  apost container (FastAPI + static frontend)
                         |
                         v
                      redis container
```

## Troubleshooting

- `Docker is not available`: start Docker Desktop/Engine and retry.
- `backend/.env` missing: script auto-creates it; update values as needed.
- App not ready in time: rerun with larger timeout:
  - `python .\run_apost_fullstack.py up --health-timeout-seconds 240`
- See detailed logs:
  - `python .\run_apost_fullstack.py logs`

## Dev hot-reload alternative

For UI/backend code iteration with hot reload, run frontend and backend locally, but keep Redis in Docker:

```powershell
docker compose up -d redis
cd backend
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# In another terminal
cd frontend
npm run dev
```

Use this mode only when you need rapid code iteration. For integration validation, prefer the full-stack Compose flow.
