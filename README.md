# APOST - Automated Prompt Optimisation and Structuring Tool

Prompt engineering studio with TCRTE gap analysis, guided optimisation, and chat-based refinement.

![Version](https://img.shields.io/badge/version-4.0.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## What You Get

- TCRTE coverage audit across Task, Context, Role, Tone, and Execution
- Guided gap interview to complete missing prompt context
- Three optimised variants (Conservative, Structured, Advanced)
- AI refinement chat with full session context
- Framework routing with CoRe, XML structuring, TextGrad-style hardening, and more

## Stack

Frontend:
- React 18 + TypeScript
- Vite
- Tailwind CSS v4
- Framer Motion
- Zustand

Backend:
- Python 3.12
- FastAPI + Uvicorn
- Pydantic v2
- HTTPX

Infra:
- Docker + Docker Compose
- `uv` for Python package and environment management

---

## Quick Start (Choose One)

If you want fastest onboarding, use Option 2 (Docker).
If you want hot reload while coding, use Option 1 (local backend then frontend).

### Option 1: Local Development (Backend first, then Frontend)

Prerequisites:
- Node.js 20+
- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/getting-started/installation/)

Install `uv` on Windows (once):

```powershell
winget install --id=astral-sh.uv -e
```

1. Backend setup

```powershell
cd "D:\Generative AI Portfolio Projects\APOST\backend"
uv venv --python 3.12 .venv
.\.venv\Scripts\Activate.ps1
uv pip install -r requirements.txt
Copy-Item .env.example .env
```

2. Backend start

```powershell
cd "D:\Generative AI Portfolio Projects\APOST\backend"
.\.venv\Scripts\Activate.ps1
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

3. Frontend setup and start (new terminal)

```powershell
cd "D:\Generative AI Portfolio Projects\APOST\frontend"
npm install
npm run dev -- --open
```

4. Open
- Frontend: `http://localhost:5173`
- Backend docs: `http://localhost:8000/api/docs`
- Backend health: `http://localhost:8000/api/health`

Note: if PowerShell script execution is restricted, either run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

or activate using cmd script:

```powershell
.\.venv\Scripts\activate.bat
```

---

### Option 2: Docker Full Stack (Recommended for frictionless run)

Prerequisite:
- Docker Desktop running

From repo root:

```powershell
cd "D:\Generative AI Portfolio Projects\APOST"
python .\run_apost_fullstack.py up
```

Useful commands:

```powershell
python .\run_apost_fullstack.py urls
python .\run_apost_fullstack.py status
python .\run_apost_fullstack.py logs
python .\run_apost_fullstack.py down
```

NPM wrappers:

```powershell
npm run fullstack:up
npm run fullstack:status
npm run fullstack:logs
npm run fullstack:down
```

Open:
- App UI: `http://127.0.0.1:8000`
- API docs: `http://127.0.0.1:8000/api/docs`
- Health: `http://127.0.0.1:8000/api/health/live`

---

## API Key Behavior (Important)

Default and recommended:
- Enter provider API key in the UI.
- Key is sent per request and not persisted by backend state.

Optional in `backend/.env`:
- `OPENAI_API_KEY` and/or `GOOGLE_API_KEY` can be set for provider-level startup checks or server-side flows.
- This is optional for normal UI-driven usage.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `uv pip install` fails with metadata/cache errors | `uv cache clean` then retry install |
| Port 8000 in use | `netstat -ano | findstr :8000` then `taskkill /PID <pid> /F` |
| Frontend shows backend offline | Start backend first, then frontend |
| CORS error from frontend dev server | Ensure `CORS_ORIGINS` in `backend/.env` includes `http://localhost:5173` |
| `uv` not found | Re-open terminal after `winget install --id=astral-sh.uv -e` |

---

## Project Structure

```text
APOST/
|-- backend/
|   |-- app/
|   |   |-- api/routes/
|   |   |-- models/
|   |   |-- services/
|   |   |-- config.py
|   |   `-- main.py
|   |-- .env.example
|   `-- requirements.txt
|-- frontend/
|   |-- src/
|   |-- package.json
|   `-- vite.config.ts
|-- docker-compose.yml
|-- Dockerfile
|-- run_apost_fullstack.py
|-- FULLSTACK_RUNBOOK.md
`-- README.md
```

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/health` | GET | Health check |
| `/api/gap-analysis` | POST | TCRTE coverage audit |
| `/api/optimize` | POST | Generate three prompt variants |
| `/api/chat` | POST | Chat refinement |

## License

MIT License. See [LICENSE](LICENSE).
