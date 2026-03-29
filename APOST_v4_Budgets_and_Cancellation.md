# APOST v4 — Budgets & Cooperative Cancellation (Plan 5)

This document explains *the problem*, *the mechanism*, and *the reusable pattern* behind Plan 5.

It is written for engineers who want to:
- understand exactly how APOST enforces cost guardrails
- understand exactly how APOST cancels work safely across processes
- copy the same pattern into other long-running async systems

---

## 1) The Problem Plan 5 Solves

APOST can run an optimization pipeline that includes a dataset-driven evaluation phase.
That evaluation phase can fan out into many LLM calls.

### 1.1 A Concrete “How Did We Spend So Much?” Scenario

A user uploads an `evaluation_dataset` with 5,000 cases.
APOST generates 3 variants and evaluates all variants on all cases.

At minimum:

- 3 variants × 5,000 cases = 15,000 model executions

Depending on scoring mode, there may be additional judging calls.

If the system accepts this request without guardrails:
- cost can spike immediately
- workers can be occupied for a long time
- other users can be starved
- the only emergency stop becomes “kill the server”

Plan 5 adds two enterprise safety capabilities:

1. **Budgets (hard caps):** reject oversized requests before they start expensive work.
2. **Cancellation (safe abort):** allow users to stop an in-flight job without corrupting state or observability.

---

## 2) The Mental Model (Definitions)

### 2.1 Request vs Job

- **OptimizationRequest**: the user’s payload (prompt, framework, provider, optional `evaluation_dataset`).
- **Optimization job**: a durable record with a `job_id` stored in Redis that tracks lifecycle state over time.

### 2.2 Orchestrator vs Worker

- **Orchestrator**: the FastAPI process. It handles HTTP, persists job state, and stays responsive.
- **Worker**: a separate OS process (via `ProcessPoolExecutor`) that runs the heavy pipeline (LLM calls, parsing, evaluation loops).

### 2.3 Cooperative Cancellation (what it means)

Cooperative cancellation means:

- The cancel endpoint does *not* kill the worker process.
- The cancel endpoint records *intent* durably (`status = cancelled`).
- The worker checks for cancellation at safe points.
- If cancelled, the worker raises a dedicated exception and unwinds normally.

This matters because “hard kills” can:

- interrupt cleanup
- truncate logs/traces
- leave clients/sockets in uncertain states
- allow ambiguous or incorrect final job status

---

## 3) The Job State Machine (The Contract)

Plan 5 makes cancellation explicit as a first-class terminal state.

### 3.1 Status Values

- `queued`      — job record exists; execution not started
- `running`     — pipeline is executing
- `succeeded`   — final response persisted
- `failed`      — unrecoverable error persisted
- `cancelled`   — user requested stop; job must not continue

### 3.2 Allowed Transitions

```text
queued     -> running
queued     -> cancelled

running    -> succeeded
running    -> failed
running    -> cancelled

succeeded  -> terminal
failed     -> terminal
cancelled  -> terminal
```

### 3.3 “Cancellation Must Win”

The tricky part is preventing this race:

```text
User cancels (running -> cancelled)
Worker finishes right after and writes (running -> succeeded)
Final status becomes succeeded (wrong)
```

APOST prevents this by using guarded, atomic updates:

- job updates include an `expected_current_status` check
- the Redis update uses optimistic locking to prevent write stomping

If the job is already `cancelled`, the “running -> succeeded” update is rejected.

---

## 4) Architecture (Where Each Piece Lives)

### 4.1 Modules Involved

- Budget knob: `backend/app/config.py`
- Shared budget enforcement + cancellation checkpoints: `backend/app/services/optimization/optimization_pipeline.py`
- Cancel endpoint: `backend/app/api/routes/optimization_jobs.py`
- Durable orchestration + terminal transitions: `backend/app/services/optimization/optimization_job_service.py`
- Worker execution boundary (process pool) + cancellation checker closure: `backend/app/services/optimization/job_execution_backends.py`
- Deep-loop evaluation + per-case checkpoints: `backend/app/services/evaluation/task_level_evaluation.py`

### 4.2 End-to-End Flow (Async)

```text
Client
  |
  | POST /api/optimize/jobs
  v
FastAPI route
  |
  | validate request schema
  | budget gate (<= 100 cases)
  | persist job record (queued)
  | return { job_id }
  v
OptimizationJobService
  |
  | schedule orchestration task
  | update status: queued -> running
  v
ProcessPool worker process
  |
  | execute_optimization_request(..., cancellation_check)
  |   - pipeline checkpoints call cancellation_check()
  |   - deep evaluation loops call cancellation_check()
  v
Job service persists terminal state
  |
  | succeeded | failed | cancelled
  v
Client polls status, fetches result when succeeded
```

---

## 5) Budgets (Hard Cost Guardrails)

### 5.1 The Budget Knob

`backend/app/config.py`

- `max_task_evaluation_cases_per_request: int = 100`

This is a deliberately conservative default.

### 5.2 The Single Source of Truth

`backend/app/services/optimization/optimization_pipeline.py`

- `enforce_optimization_request_budget(optimization_request, request_id=...)`

What it does:

1. Reads `len(optimization_request.evaluation_dataset)`.
2. Compares against `settings.max_task_evaluation_cases_per_request`.
3. Logs one of:
   - `optimize.budget_check_passed`
   - `optimize.budget_check_rejected`
4. Raises `OptimizationRequestBudgetError` when over limit.

Why it lives in the shared pipeline:

- Both the sync route and the async job runner depend on the pipeline.
- Putting the rule here prevents “one endpoint forgot the limit” drift.

### 5.3 HTTP Semantics

Over-budget requests produce:

- `422 Unprocessable Entity`
- message includes provided count and max

In APOST:

- Sync optimize route maps this to `422`.
- Job creation maps this to `422` *before scheduling background work*.

The “before scheduling” property is important:

- no Redis job is created
- no worker is scheduled
- cost is controlled at the edge

---

## 6) Cancellation (The Mechanism)

Cancellation in APOST is intentionally split into three responsibilities.

### 6.1 Responsibility 1: Record Intent Durably

When a user calls:

- `POST /api/optimize/jobs/{job_id}/cancel`

the system:

- atomically updates the job record in Redis
- sets:
  - `status = cancelled`
  - `current_phase = cancelled`
  - `error_message = cancelled_by_user`

Key property:

- the endpoint is fast and safe
- it does not do heavy work

Idempotency rules:

- if the job is already `cancelled`, return current state
- if the job is `succeeded` or `failed`, return current state (no rewriting history)

### 6.2 Responsibility 2: Stop “Queued” Jobs Efficiently

If the job is still `queued` and a local orchestration task exists:

- the job service cancels the asyncio task immediately

This prevents starting a worker process at all.

### 6.3 Responsibility 3: Stop “Running” Jobs Cooperatively

A running job is executing inside a separate process.
The orchestrator cannot safely “reach in and stop a function”.

Instead, the worker cooperates:

- worker constructs a small async function `ensure_job_not_cancelled()`
- that function reads job state from Redis
- if `status == cancelled`, it raises `OptimizationJobCancelledError`

That function is passed down as `cancellation_check`.

The pipeline and evaluation loops call `await cancellation_check()` at safe points.

---

## 7) Where Cancellation Checkpoints Are Placed (Why It Works)

A cancellation system is only as good as its checkpoint placement.

APOST checks cancellation at two depths:

### 7.1 Pipeline Phase Checkpoints

`backend/app/services/optimization/optimization_pipeline.py` calls cancellation checkpoints:

- before framework resolution
- after framework resolution
- after cross-cutting inputs
- after variant generation
- before response finalization

These checkpoints ensure the pipeline can stop even if dataset evaluation is not the current phase.

### 7.2 Inner-Loop Checkpoints (The Most Important Ones)

`backend/app/services/evaluation/task_level_evaluation.py` calls cancellation checkpoints:

- before each variant evaluation
- before each dataset case
- before each pairwise tie-break comparison

Why this matters:

- If the user cancels at case 45, the worker stops before case 46.
- That can prevent dozens (or thousands) of remaining calls.

---

## 8) How Cancellation Is Finalized (And Not Misclassified)

The worker raises `OptimizationJobCancelledError`.

The job service catches it explicitly and persists the job as:

- `status = cancelled`
- `error_message = cancelled_by_user`

Why a dedicated exception matters:

- cancellation is not an operational failure
- cancellation should not page on-call
- cancellation should not pollute failure dashboards

---

## 9) Result Semantics (No Partial Results in v1)

For cancelled jobs:

- `/api/optimize/jobs/{job_id}/result` returns `409`
- message: `Optimization job was cancelled by user.`

This is a deliberate safety choice.

Partial results are not returned in v1 because partial results require:

- explicit schema fields like `is_partial` and `partial_reason`
- clear semantics for “some variants evaluated, some not”
- defensive consumer behavior

Without that, partial responses are easy to misinterpret as final truth.

---

## 10) Reusable Pattern (Apply This In Other Projects)

This exact approach generalizes to any long-running workflow:

- ETL pipelines
- media processing
- scoring pipelines
- evaluation harnesses
- large batch LLM operations

### 10.1 Minimal Blueprint

1) **Durable state** (DB/Redis) with explicit statuses.

2) **Budget gates** as a shared function.

3) **Cancel endpoint** that only flips durable intent.

4) **Worker cancellation check** that reads durable intent.

5) **Checkpoints** at:

- phase boundaries
- hot loops

6) **Guarded atomic updates** to prevent race overwrites.

### 10.2 Pseudocode You Can Copy

```text
# API cancel endpoint
update_atomic(job_id, status='cancelled', expected_status in {'queued','running'})
return current_status

# Worker cancellation check
record = store.get(job_id)
if record.status == 'cancelled':
    raise JobCancelledError()

# Checkpoints
before_phase(): cancellation_check()
per_item_loop(): cancellation_check()
```

### 10.3 Common Mistakes To Avoid

- budget enforced only on one endpoint
- cancellation implemented only by hard process kill
- no checkpoint inside inner loops
- allowing success to overwrite cancellation due to missing expected-status guards

---

## 11) Limitations (Honest Reality)

Cooperative cancellation cannot interrupt an in-flight model call immediately.

If a single LLM call takes 30 seconds:

- cancellation takes effect after the call returns (next checkpoint)

Typical production enhancements include:

- per-call timeouts
- job-level deadlines
- max concurrent jobs per tenant

---

## 12) What To Read In Code (APOST Reference Map)

- Budget config: `backend/app/config.py`
- Budget enforcement + checkpoint utility: `backend/app/services/optimization/optimization_pipeline.py`
- Cancel endpoint: `backend/app/api/routes/optimization_jobs.py`
- Cancel orchestration + terminal state: `backend/app/services/optimization/optimization_job_service.py`
- Worker-side Redis polling: `backend/app/services/optimization/job_execution_backends.py`
- Deep-loop checkpoints: `backend/app/services/evaluation/task_level_evaluation.py`

---

## 13) Final Takeaway

Plan 5 is production safety engineering.

- Budgets prevent accidental cost explosions.
- Cooperative cancellation prevents unsafe abort behavior.
- Durable state + guarded atomic updates prevent race-condition corruption.

This is one of the most reusable patterns for any long-running async workload.
