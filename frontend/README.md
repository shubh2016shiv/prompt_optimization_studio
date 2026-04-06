# APOST Frontend — Automated Prompt Optimisation & Structuring Tool

The APOST frontend is a modern, high-performance React web application that provides the user interface for the APOST prompt engineering system. 

It powers the three core workflow stages:
1. **Gap Analysis**: A real-time audit of user prompts against the 5-dimension TCRTE rubric.
2. **Optimization**: Generating and comparing Conservative, Structured, and Advanced prompt variants across automatically selected frameworks (e.g., XML Structured, Progressive, CoT Ensemble).
3. **Chat Refinement**: An interactive, context-aware chat session to further refine generated prompts.

---

## Tech Stack & Architecture

This frontend is designed for speed, fluidity, and modularity:

- **Build Tool:** [Vite 6](https://vitejs.dev/) + SWC (Lightning fast HMR)
- **Framework:** [React 18](https://react.dev/) + TypeScript
- **State Management:** [Zustand 5](https://docs.pmnd.rs/zustand/getting-started/introduction) (Lightweight, un-opinionated state)
- **Styling:** [Tailwind CSS v4](https://tailwindcss.com/) (Utility-first styling)
- **Animations:** [Framer Motion 11](https://www.framer.com/motion/) (Smooth transitions and micro-interactions)
- **UI Primitives:** Customizable components built on [Radix UI](https://www.radix-ui.com/) (Accessible, unstyled components)
- **Icons:** [Lucide React](https://lucide.dev/)

---

## Setup & Installation

The project uses `npm` for dependency management. Make sure you have [Node.js](https://nodejs.org/) installed (v18 or higher recommended).

1. **Install dependencies:**
   ```bash
   cd frontend
   npm install
   ```

2. **Start the development server:**
   ```bash
   npm run dev
   ```

The application will start on **http://localhost:5173**.

---

## Connecting to the Backend

**Critical:** The frontend cannot function without the APOST Python backend running simultaneously.

The Vite development server is configured (`vite.config.ts`) to proxy all API requests (e.g., `/api/optimize`) directly to the backend. 

1. Before interacting with the UI, ensure your backend server is running in its own terminal window on **port 8000**:
   ```bash
   # In the backend/ directory
   uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```
2. The frontend proxy will seamlessly forward your requests. You do not need to configure any full URLs in the frontend code; everything uses relative `/api/...` paths.

Optional: if your backend runs on a different host/port, set `VITE_DEV_API_PROXY_TARGET` before starting Vite.
```bash
# Example (PowerShell)
$env:VITE_DEV_API_PROXY_TARGET = "http://127.0.0.1:8080"
npm run dev
```

---

## Available Scripts

- `npm run dev` — Starts the Vite development server with Hot Module Replacement (HMR).
- `npm run build` — Compiles TypeScript (`tsc -b`) and bundles the application for production deployment into the `dist/` directory.
- `npm run lint` — Runs ESLint to check for code quality and React hook rule violations.
- `npm run preview` — Boots a local static server to preview the production-ready build (`dist/`).
