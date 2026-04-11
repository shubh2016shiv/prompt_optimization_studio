# APOST Backend — Automated Prompt Optimisation & Structuring Tool

The APOST backend is a production-grade FastAPI service designed to transform weak, underspecified instructions into highly reliable, structured prompts. It powers the APOST frontend interface by providing a suite of advanced, verifiable prompt-engineering tools.

Unlike standard "wrapper" APIs, the APOST backend is built on deterministic, mathematically sound implementations of cutting-edge research:

- **Deterministic TCRTE Scoring**: Evaluates prompts against a strict 5-dimension rubric (Task, Context, Role, Tone, Execution) using `gpt-4.1-nano` at `temperature=0` for perfect reproducibility.
- **Iterative Textual Backpropagation (TextGrad)**: Implements Stanford's true TextGrad forward-pass/loss/backward-pass optimization loop to harden prompts against known failure modes.
- **Medprompt kNN Few-Shot Retrieval**: Uses pre-computed Gemini embeddings and in-memory cosine similarity to dynamically retrieve the most relevant `<few_shot_examples>` based on the input task type. 
- **Adaptive Context Repetition Engine (CoRe)**: Programmatically estimates reasoning *hops* and bounds them (k=2 to 5) to actively counteract the transformer "Lost in the Middle" attention degradation.
- **Deterministic Framework Auto-Selection**: Evaluates complexity, task type, and TCRTE scores through a pure Python decision engine to scientifically route prompts to the optimal structural framework (e.g., XML Structured, Progressive, CoT Ensemble).

---

## Architecture & Code Layout

- **`app/api/route/`** â€” FastAPI HTTP endpoints mapping to the UI (`/gap-analysis`, `/optimize`, `/chat`).
- **`app/services/analysis/`** â€” The deterministic auto-select router and the CoRe reasoning hop-counter.
- **`app/services/optimization/`** â€” `textgrad` loop iteration, the `numpy`-backed kNN retriever, and the curated few-shot corpus.
- **`app/services/scoring/`** â€” Uncompromising `temperature=0` TCRTE scoring audits. 
- **`tests/`** â€” The comprehensive deterministic test suite mapped to every service component.

**Security:** The backend is completely stateless and does not store user API keys. Keys for LLM providers (Anthropic, OpenAI) are passed transiently on each client request. 

---

## Setup and Installation

This project strictly uses [uv](https://docs.astral.sh/uv/), the blazing-fast Python package and project manager, to guarantee sub-second, identical environment replication.

### 1. Requirements
- Python 3.11+
- `uv` installed (`curl -LsSf https://astral.sh/uv/install.sh | sh` or `pip install uv`)

### 2. Configure Environment Variables
Copy the default environment template:
```bash
cp .env.example .env
```
Ensure you provide a valid `GOOGLE_API_KEY` in `.env`. This allows the application to pre-compute the embeddings for the kNN few-shot corpus cleanly at startup. User optimization keys (OpenAI/Anthropic) remain client-supplied. 

---

## Running the Server

Because this is a decoupled frontend/backend repository, **where you run the command matters**.

### Option A: From inside the `backend/` directory (Recommended for Development)
Start the application using `uv` and `uvicorn`. The application bounds the ASGI loop and watches for changes directly. 

```bash
cd backend
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
> **Note:** If port `8000` is already in use by another service on Windows (`WinError 10013`), switch to an alternate port via `--port 8080`.

### Option B: From the Repository Root (Convenience Script)
If you are at the top-level repository root (one level above `backend/`), you can use the launcher script:

```bash
uv run python start_backend.py
```
*(This script internally handles changing into the `backend/` directory and loading the correct `.env` files).*

---

### Once Running:
- **Interactive API Docs (Swagger):** [http://127.0.0.1:8000/api/docs](http://127.0.0.1:8000/api/docs)
- **Health Check:** `curl -s http://127.0.0.1:8000/api/health`

---

## Testing & Verification

The suite includes 13 deterministic proofs verifying the algorithmic stability of the scoring, counting, routing, and selection components.

Run the test suite identically via `uv`:

```bash
# Export PYTHONPATH locally so pytest resolves all core modules
$env:PYTHONPATH="."  # On macOS/Linux: export PYTHONPATH="."
uv run pytest tests/ -v
```

---

## Integration Evaluation (No UI Required)

If you wish to test the end-to-end framework pipeline programmatically without booting the frontend, the `sample_usage/` folder exports sequential fixture tests:

```bash
# Ensure APOST_TEST_API_KEY is defined internally or in .env
uv run python sample_usage/run_all.py
```

## Configuration Guide

- **`app/docs/CONFIGURATION.md`** - centralized settings, default-value rationale, and safe tuning workflow for optimization runtime knobs.
