# APOST — Automated Prompt Optimisation & Structuring Tool

> A professional-grade prompt engineering studio with AI-powered gap analysis, TCRTE coverage auditing, and conversational refinement.

![Version](https://img.shields.io/badge/version-4.0.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## Features

- **TCRTE Coverage Audit** — Scores your prompt across Task, Context, Role, Tone, and Execution dimensions
- **Gap Interview** — Targeted questions to fill coverage gaps without prompt engineering knowledge
- **3 Optimised Variants** — Conservative, Structured, and Advanced variants with full guards
- **AI Refinement Chat** — Conversational prompt refinement with full session context
- **Framework Support** — KERNEL, XML Structured, Progressive Disclosure, CoT Ensemble, TextGrad, and more
- **Technique Application** — CoRe (Context Repetition), RAL-Writer, Claude Prefill, XML Bounding
- **Reasoning Model Aware** — Automatic CoT suppression for o-series and extended thinking models

## Tech Stack

**Frontend:**
- React 18 + TypeScript
- Vite (build tooling)
- Tailwind CSS v4
- Framer Motion (animations)
- Zustand (state management)

**Backend:**
- Python 3.12
- FastAPI + Uvicorn
- Pydantic v2
- HTTPX (async HTTP client)

**Package management:**
- [`uv`](https://docs.astral.sh/uv/) — fast Python package manager (replaces pip/venv)

**Deployment:**
- Docker (multi-stage build)
- Docker Compose

---

## Quick Start

> **Recommended for daily work:** Option 1 (local `uv`). The app shows a **green/red backend status badge** in the header so you always know if the API is reachable.

---

### Option 1: Local Development with `uv`

#### Prerequisites (install once on your machine)

- [Node.js 20+](https://nodejs.org/)
- [uv](https://docs.astral.sh/uv/getting-started/installation/) — Python package manager

```powershell
# Install uv (Windows)
winget install --id=astral-sh.uv -e
```

---

#### Backend — first-time setup

```powershell
cd "d:\Generative AI Portfolio Projects\APOST\backend"

# 1) Create an isolated virtual environment
uv venv --python 3.12 .venv

# 2) Activate it
.venv\Scripts\activate.bat

# 3) Install Python dependencies
uv pip install -r requirements.txt
```

> **If install fails with "Metadata field Name not found":**
> ```powershell
> uv cache clean
> uv pip install -r requirements.txt
> ```

#### Backend — env file (run once)

```powershell
# Still inside backend/
Copy-Item .env.example .env
notepad .env
```

Set at least one LLM API key. Example for OpenAI:

```env
OPENAI_API_KEY=sk-proj-...
```

#### Backend — start

```powershell
cd "d:\Generative AI Portfolio Projects\APOST\backend"
.venv\Scripts\activate.bat
uv run -- python -m uvicorn app.main:app --reload --port 8000
```

Verify it's running:
- **Health check**: `http://localhost:8000/api/health` → `{"status":"healthy"}`
- **API docs**: `http://localhost:8000/api/docs`

The app header will switch from **red → green** once the backend is reachable.

---

#### Frontend — first-time setup

```powershell
cd "d:\Generative AI Portfolio Projects\APOST\frontend"
npm install
```

#### Frontend — start

```powershell
cd "d:\Generative AI Portfolio Projects\APOST\frontend"
npm run dev -- --open
```

Frontend runs at `http://localhost:5173`. All `/api` calls are automatically proxied to `http://localhost:8000`.

---

### Option 2: Docker (containerised / production-like)

Requires [Docker Desktop](https://www.docker.com/products/docker-desktop/) to be running.

```powershell
# From repo root
python .\run_apost_fullstack.py up
```

You can also run via npm wrapper:

```powershell
npm run fullstack:up
```

Detailed operator documentation lives in `FULLSTACK_RUNBOOK.md`.

Note: In this Docker mode, Redis stays internal to the Compose network (no host `6379` binding), which avoids local Redis port conflicts.

Open:
- **App UI**: `http://localhost:8000`
- **API docs**: `http://localhost:8000/api/docs`
- **Health**: `http://localhost:8000/api/health`

---

### Troubleshooting

| Problem | Fix |
|---|---|
| `uv pip install` fails with "Metadata field Name not found" | `uv cache clean` then retry |
| Port 8000 already in use | `netstat -ano \| findstr :8000` → find PID → `taskkill /PID <pid> /F` |
| Frontend shows red "Backend offline" badge | Backend is not running — start it (see above) |
| CORS errors in browser console | Ensure `CORS_ORIGINS` in `backend/.env` includes `http://localhost:5173` |
| `uv: command not found` | `winget install --id=astral-sh.uv -e` |
| `python 3.12 not found` during `uv venv` | Run `py -0p` to see installed versions, use `--python 3.11` if needed |

---

## Usage

1. **Enter Your Prompt** — Paste your raw prompt in the left panel
2. **Select Target Model** — Choose provider (Anthropic / OpenAI / Google) and model
3. **Add API Key** — Enter your API key for the selected provider
4. **Analyse Gaps** — Click "🔍 Analyse Gaps First" for TCRTE coverage audit
5. **Answer Questions** — Fill in the gap interview questions (optional)
6. **Optimise** — Click "⬡ Optimise with Context" to generate 3 variants
7. **Refine in Chat** — Use the AI chat to iteratively improve your prompts

## Project Structure

```
APOST/
├── backend/
│   ├── app/
│   │   ├── api/routes/          # API endpoints
│   │   ├── models/              # Pydantic models
│   │   ├── services/            # Business logic
│   │   │   └── prompt_builders/ # Prompt construction
│   │   ├── config.py            # Settings management
│   │   └── main.py              # FastAPI application
│   ├── .env.example
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/          # Shared UI components
│   │   ├── features/            # Feature modules
│   │   │   ├── configuration/   # Left panel
│   │   │   ├── workflow/        # Middle panel
│   │   │   └── chat/            # Right panel
│   │   ├── hooks/               # Custom React hooks
│   │   ├── services/            # API client
│   │   ├── store/               # Zustand stores
│   │   ├── types/               # TypeScript types
│   │   └── constants/           # Static data
│   ├── package.json
│   └── vite.config.ts
├── Dockerfile
├── docker-compose.yml
├── run_apost_fullstack.py
├── FULLSTACK_RUNBOOK.md
└── README.md
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/gap-analysis` | POST | TCRTE coverage audit |
| `/api/optimize` | POST | Generate 3 prompt variants |
| `/api/chat` | POST | AI chat message |

## Environment Variables

API keys are **not** set in `.env`. Each user enters their own key directly in the UI - it is sent per-request and never stored on the server.

| Variable | Description | Default |
|----------|-------------|----------|
| `DEBUG` | Enable verbose debug output | `false` |
| `CORS_ORIGINS` | Comma-separated allowed origins | `http://localhost:5173,...` |
| `MAX_TOKENS_GAP_ANALYSIS` | Token budget for gap analysis | `1500` |
| `MAX_TOKENS_OPTIMIZATION` | Token budget for optimisation | `4096` |
| `MAX_TOKENS_CHAT` | Token budget per chat reply | `2048` |

## Docker Notes

- **Single-container runtime**: The `Dockerfile` builds the frontend and serves it from FastAPI as static files (`/`), with APIs under `/api/*`.
- **Development vs production**:
  - Local dev uses Vite (`:5173`) + FastAPI (`:8000`) separately with hot reload.
  - Docker runs a single production-like service on `:8000`.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

MIT License — see [LICENSE](LICENSE) for details.

## Acknowledgments

- TCRTE Framework inspired by Anthropic's prompt engineering guidelines
- CoRe (Context Repetition) technique from multi-hop reasoning research
- RAL-Writer restate technique for long-context optimisation
- TextGrad iterative constraint hardening approach
