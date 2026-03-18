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
- Tailwind CSS v4 + shadcn/ui
- Framer Motion (animations)
- Zustand (state management)

**Backend:**
- Python 3.12
- FastAPI + Uvicorn
- Pydantic v2
- HTTPX (async HTTP client)

**Deployment:**
- Docker (multi-stage build)
- Docker Compose

## Quick Start

### Option 1: Docker (Recommended)

```bash
# From repo root (this folder)
# 1) Create your env file
cp .env.example .env

# 2) Add at least one API key in .env (recommended: ANTHROPIC_API_KEY)

# 3) Build + run
docker compose up --build
```

Open:
- **App UI (served by FastAPI)**: `http://localhost:8000`
- **API docs**: `http://localhost:8000/api/docs`
- **Health**: `http://localhost:8000/api/health`

#### Windows PowerShell note

If `cp` isn’t available, use:

```powershell
Copy-Item .env.example .env
```

#### Windows (PowerShell) — Docker copy/paste

Run these from the repo root:

```powershell
# 1) Create env file
Copy-Item .env.example .env

# 2) Edit .env and set at least one API key (recommended: ANTHROPIC_API_KEY)
notepad .env

# 3) Build + run (Docker Desktop must be running)
docker compose up --build
```

### Option 2: Local Development (Frontend + Backend)

**Prerequisites:**
- Node.js 20+
- Python 3.12+
- npm (or pnpm)

You will run **two dev servers**:
- **Backend**: FastAPI on `http://localhost:8000`
- **Frontend**: Vite on `http://localhost:5173` (proxies `/api` → backend)

**Backend:**
```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create env file (recommended: keep backend env inside backend/)
cp .env.example .env

# Add at least one API key (recommended: ANTHROPIC_API_KEY)

# Run the backend
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend

# Install dependencies
npm install

# Run the development server
npm run dev
```

Open:
- **Frontend UI**: `http://localhost:5173`
- **Backend API docs**: `http://localhost:8000/api/docs`

#### Windows (PowerShell) — Local dev copy/paste

Open **two** PowerShell windows.

**Terminal A (Backend):**

```powershell
cd "d:\Generative AI Portfolio Projects\APOST\backend"

# Create + activate venv
py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1

# Install deps
python -m pip install --upgrade pip
pip install -r requirements.txt

# Create env file + set keys
Copy-Item .env.example .env
notepad .env

# Run API
python -m uvicorn app.main:app --reload --port 8000
```

**Terminal B (Frontend):**

```powershell
cd "d:\Generative AI Portfolio Projects\APOST\frontend"
npm install
npm run dev
```

Then open:
- **Frontend UI**: `http://localhost:5173`
- **Backend (API + docs)**: `http://localhost:8000/api/docs`

#### Troubleshooting (local)

- **CORS errors**: ensure `CORS_ORIGINS` includes `http://localhost:5173` (see `backend/.env.example`).
- **Backend not reachable from frontend**: Vite is configured to proxy `/api` to `http://localhost:8000` in `frontend/vite.config.ts`.

## Usage

1. **Enter Your Prompt** — Paste your raw prompt in the left panel
2. **Select Target Model** — Choose provider (Anthropic/OpenAI/Google) and model
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
├── .env.example
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

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Anthropic API key | - |
| `OPENAI_API_KEY` | OpenAI API key | - |
| `GOOGLE_API_KEY` | Google AI API key | - |
| `DEBUG` | Enable debug mode | `false` |
| `CORS_ORIGINS` | Allowed origins | `localhost` |
| `OPTIMIZER_MODEL` | Internal model for optimization | `claude-sonnet-4-20250514` |

## Docker Notes

- **Single-container runtime**: The `Dockerfile` builds the frontend and serves it from FastAPI as static files (`/`), with APIs under `/api/*`.
- **Development vs production**:
  - Local dev uses Vite (`:5173`) + FastAPI (`:8000`) separately.
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
- RAL-Writer restate technique for long-context optimization
- TextGrad iterative constraint hardening approach
