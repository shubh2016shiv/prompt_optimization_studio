# APOST — Feasibility Assessment: Python Tool + Intuitive UI + Docker

## Executive Summary

**Verdict: Highly feasible.** APOST can be reimplemented as a Python-backed tool with an intuitive web UI and packaged in Docker with moderate effort. The current React app is a single-file, API-calling frontend with no backend; porting the logic to Python and serving a clean UI is straightforward.

---

## 1. Current Project State

| Asset | Description |
|-------|-------------|
| **PromptOptimizer.jsx** | Single-file React app (~570 lines). Three-column layout: Left (prompt + model config), Middle (workflow: gap analysis → interview → optimisation → results), Right (AI chat). All LLM calls go directly from the browser to **Anthropic** only. |
| **APOST_v4_Documentation.md** | Full spec: TCRTE framework, 9 optimisation frameworks, provider-specific rules, four-phase state machine, prompt builders, and extension notes. |

**Core behaviours to preserve:**

- **Phase 1 — Gap analysis:** Build meta-prompt → call Claude → parse JSON (TCRTE scores, questions, complexity, recommended techniques).
- **Phase 2 — Interview:** Show coverage meter, complexity, techniques, auto-enrichments, question cards; collect answers.
- **Phase 3 — Optimisation:** Build optimizer meta-prompt (with optional gap answers) → call Claude → parse JSON (3 variants with system/user prompts, guards, TCRTE scores, prefill).
- **Phase 4 — Results:** Show three variant cards (tabs: System, User, Guards, Meta, Prefill); copy buttons; “Refine” opens chat with context.
- **Chat:** System prompt seeded with full session (raw prompt, gap data, answers, all variants); 28-message rolling window; quick-action chips.

---

## 2. Feasibility by Component

### 2.1 Python Backend — **Feasible**

| Concern | Assessment |
|---------|------------|
| **Prompt builders** | `buildGapAnalysisPrompt`, `buildOptimizerPrompt`, `buildChatSystem` are string templates with configuration. Direct port to Python (f-strings or templates). |
| **LLM calls** | Anthropic: `anthropic` SDK. OpenAI and Google: `openai`, `google-generativeai`. Documentation already describes provider-specific behaviour; multi-provider support is a matter of routing and prompt tweaks. |
| **JSON parsing** | Standard library; strip markdown code fences then `json.loads`. Same as current JS. |
| **State machine** | Four phases (`idle` → `analyzing` → `interview` → `optimizing` → `results`) with clear transitions. Easy to implement in Python (e.g. enum + handlers). |

**Suggested stack:** FastAPI (async, OpenAPI, easy to add API key handling and CORS) or Flask. Environment-based API keys for server-side calls so the UI never sees keys if you want a “production” mode.

### 2.2 Intuitive, User-Friendly UI — **Feasible**

Goal: easy to navigate, minimal learning curve.

| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| **Streamlit** | Fast to build, good for internal tools, native Python. | Less control over exact layout; three-column layout possible but not as crisp as custom HTML. | ✅ Good for an MVP or “single-page” style; can be made clear with sections and expanders. |
| **FastAPI + Jinja2 + HTMX / Alpine** | Server-rendered, no heavy JS; still responsive. | More front-end work for interactivity (e.g. tabs, copy, chat). | ✅ Good if you want a lightweight, accessible UI without a separate SPA. |
| **FastAPI + React/Vue SPA** | Pixel-perfect replica of current three-column design; best UX control. | Two codebases (API + frontend); build step. | ✅ Best for “professional workstation” feel and reuse of current UX patterns. |
| **Gradio** | Very quick for demos, good for ML. | Less suited to a multi-step workflow and rich layout. | ⚠️ Possible but not ideal for the full APOST workflow. |

**Recommendation:** Start with **Streamlit** for a first version (single codebase, quick iteration, good enough navigation with clear headings and steps). If you need the exact three-column “studio” feel and richer interactions, add a **FastAPI backend + simple React or Vue frontend** that consumes the API.

**UI/UX practices to apply:**

- **Left:** Stable config (prompt, variables, provider, model, API key). Clearly label “Step 1: Configure”.
- **Center:** Workflow steps with visible state (e.g. “Step 2: Analyse gaps” → “Step 3: Answer questions” → “Step 4: Optimise” → “Step 5: Results”). Use progress or stepper.
- **Right (or below on mobile):** Chat panel with quick actions and short hints (“Refine a variant”, “Add guards”).
- **Copy buttons** on every prompt block; **one primary action per step** (e.g. “Analyse Gaps” then “Optimise with Context”).
- Optional: short **tooltips** or “?” for TCRTE, CoRe, RAL-Writer, Prefill (link to doc or in-app glossary).

### 2.3 Docker Packaging — **Feasible**

- **Single service:** One Python app (e.g. Streamlit or FastAPI + static assets). No database required for core workflow.
- **Dockerfile:** Base image `python:3.11-slim` or `python:3.12-slim`; install deps from `requirements.txt`; expose port (e.g. 8501 for Streamlit, 8000 for FastAPI); `CMD` to run the app.
- **Secrets:** API keys via environment variables (e.g. `ANTHROPIC_API_KEY`) or a backend proxy so the container never bakes in keys.
- **Optional:** `docker-compose.yml` for local dev (e.g. mount source, env file). Later you can add Redis or DB for persistence if needed.

**Example (conceptual):**

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

---

## 3. Effort and Risks

| Area | Effort (rough) | Risk |
|------|----------------|------|
| Port prompt builders + state machine to Python | 1–2 days | Low |
| Integrate Anthropic (and optionally OpenAI/Google) | 0.5–1 day | Low |
| Streamlit UI replicating flow + coverage meter + variants + chat | 2–4 days | Low–medium |
| FastAPI + React UI (if chosen) | 4–7 days | Medium (two codebases) |
| Docker + env-based config | 0.5 day | Low |
| Testing (unit for prompts, integration for API) | 1–2 days | — |

**Risks:**

- **LLM output format:** Model may occasionally return non-JSON or wrapped in markdown. Mitigation: robust parsing (strip fences, try/except, optional retry with “output only JSON”).
- **API keys:** If UI calls providers directly (browser), keys stay client-side. For a Docker “tool”, you can either keep client-side keys or proxy all calls through the backend and inject server-side keys for better security.

---

## 4. Recommended Path

1. **Phase 1 — Core Python**
   - Create a Python package (e.g. `apost/`) with: prompt builders, config (providers, models, frameworks, task types), state machine, and a thin service layer that calls Anthropic (and optionally OpenAI/Google).
   - Add robust JSON extraction from LLM responses.
   - Unit-test prompt building and parsing.

2. **Phase 2 — Web UI**
   - Implement a **Streamlit** app: left sidebar for config, main area for workflow (idle → analyse → interview → optimise → results), and an expandable or second-column chat.
   - Keep the same user flow as the doc (Analyse Gaps First vs Skip → Optimise; answer questions; three variants with tabs; refine via chat).
   - Use `st.session_state` for phase, gap data, answers, result.

3. **Phase 3 — Docker**
   - Add `requirements.txt` and `Dockerfile`; run Streamlit (or FastAPI) in the container.
   - Document required env vars (e.g. `ANTHROPIC_API_KEY` for server-side, or note that user enters key in UI).
   - Optional: `docker-compose` for dev.

4. **Phase 4 (optional)**
   - Move to **FastAPI + React** if you need the exact three-column layout and maximum polish.
   - Add persistence (e.g. SQLite or Redis) for history.
   - Add more providers (OpenAI, Google) using the existing doc’s provider-specific sections.

---

## 5. Conclusion

Developing APOST as a **Python tool with an intuitive UI and Docker packaging is feasible** with no major technical blockers. The clearest path is:

- **Python** for all logic (prompts, state machine, API calls).
- **Streamlit** for a first, user-friendly UI that’s easy to navigate and good enough for most users.
- **Docker** for a single, portable image with env-based configuration.

If you want to proceed, the next step is to implement the Python core (prompt builders + Anthropic client + state machine), then add the Streamlit UI and Dockerfile in the same repo.
