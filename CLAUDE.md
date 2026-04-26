# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**PromptGrade** is an open-source prompt grading platform that evaluates prompts using a hybrid approach:
- **Rule-based grading**: Fast, deterministic checks (length, structure, clarity heuristics, keyword presence)
- **LLM-as-judge grading**: Uses Claude/GPT to evaluate prompts against rubrics
- **A/B comparison**: Compare two prompts side-by-side across all metrics
- **Batch processing**: Upload CSV/JSON to grade many prompts at once

The goal is to help prompt engineers, AI teams, and researchers systematically improve their prompts with reproducible scores.

## Tech Stack

- **Backend**: Python 3.10+, FastAPI, Pydantic v2, LiteLLM (multi-provider LLM client)
- **Frontend**: React 18 + Vite + TypeScript, TailwindCSS, shadcn/ui, Recharts
- **Storage**: SQLite for local dev (via SQLAlchemy), Postgres-ready
- **Testing**: pytest (backend), Vitest + React Testing Library (frontend)
- **Linting**: ruff + mypy (Python), eslint + prettier (TS)
- **CI**: GitHub Actions

### LLM Provider Strategy (BYOK — Bring Your Own Key)

This is an OSS project, so **the maintainer never pays for users' LLM calls**. Every user supplies their own API key (or runs a local model). The app must work in all of these modes:

1. **Ollama (local, free)** — default for first-run experience. No API key needed. Recommend `llama3.1:8b` or `mistral` as default judge model.
2. **Anthropic Claude** — user provides `ANTHROPIC_API_KEY`.
3. **OpenAI GPT** — user provides `OPENAI_API_KEY`.
4. **Google Gemini** — user provides `GOOGLE_API_KEY` (has a free tier).
5. **Groq** — user provides `GROQ_API_KEY` (has a free tier, very fast).
6. **Rule-based only** — no LLM at all, fully free, works offline.

We use **LiteLLM** as the unified client so all providers go through one interface. The user picks a provider in the UI or via `JUDGE_PROVIDER` env var. If no provider is configured, the app falls back to rule-based mode and shows a banner explaining how to enable LLM grading.

## Repository Structure

```
promptgrade/
├── backend/
│   ├── app/
│   │   ├── api/         # FastAPI routers (grade, batch, compare endpoints)
│   │   ├── core/        # Config, settings, logging
│   │   ├── graders/     # Grader implementations (rule_based.py, llm_judge.py, hybrid.py)
│   │   ├── models/      # Pydantic schemas + SQLAlchemy models
│   │   └── main.py      # FastAPI app entrypoint
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── components/  # Reusable UI components
│   │   ├── pages/       # Route-level pages (Dashboard, Compare, Batch)
│   │   ├── lib/         # API client, utils
│   │   └── styles/
├── examples/            # Example prompts + rubrics (JSON/CSV)
├── .github/workflows/   # CI pipelines
├── CLAUDE.md            # This file
├── README.md
└── LICENSE              # MIT
```

## Core Concepts

### Grader Interface
All graders implement a common `Grader` base class with an `async grade(prompt: str, rubric: Rubric) -> GradeResult` method. Each new grader should:
1. Subclass `Grader` in `backend/app/graders/`
2. Return a `GradeResult` with `score` (0-100), `breakdown` (dict of sub-scores), and `feedback` (str)
3. Be registered in `graders/__init__.py` so it can be selected by name from the API

### Rubric
A `Rubric` is a structured spec that defines what "good" means for a prompt. It includes weighted criteria (clarity, specificity, structure, task_alignment, safety). Default rubrics live in `examples/rubrics/`.

### Hybrid Scoring
The hybrid grader runs rule-based checks first (cheap), then sends the prompt to an LLM judge with the rule-based results as context. Final score is a weighted combination (default 30% rules, 70% LLM — configurable via env).

## Development Commands

### Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Run dev server (with hot reload)
uvicorn app.main:app --reload --port 8000

# Run tests
pytest                      # All tests
pytest tests/test_graders/  # Specific dir
pytest -k "test_rule"       # Match by name
pytest --cov=app            # With coverage

# Lint + typecheck
ruff check . && ruff format .
mypy app/
```

### Frontend
```bash
cd frontend
npm install

# Dev server
npm run dev                 # Runs on http://localhost:5173

# Build for production
npm run build

# Test + lint
npm run test
npm run lint
```

### Full stack (both at once)
From repo root:
```bash
docker compose up           # If docker-compose.yml exists
# OR run backend + frontend in two terminals
```

## Environment Variables

All API keys are **optional**. The app picks whichever provider has a key configured. If none, it falls back to rule-based grading only.

`backend/.env`:
```
# Pick ONE of these (or none, for rule-based only mode)
ANTHROPIC_API_KEY=sk-ant-...      # Optional
OPENAI_API_KEY=sk-...             # Optional
GOOGLE_API_KEY=...                # Optional (free tier available)
GROQ_API_KEY=gsk_...              # Optional (free tier available)

# Or use Ollama for fully local, free LLM grading
OLLAMA_BASE_URL=http://localhost:11434   # Default if Ollama is detected

# Which provider/model to use as judge (auto-detected if not set)
JUDGE_PROVIDER=anthropic|openai|google|groq|ollama
JUDGE_MODEL=claude-sonnet-4-6     # Provider-specific model name

# App config
DATABASE_URL=sqlite:///./promptgrade.db
LOG_LEVEL=INFO
```

Frontend uses `frontend/.env`:
```
VITE_API_BASE_URL=http://localhost:8000
```

Never commit `.env` files. Use `.env.example` as a template. The `.env.example` file should clearly tell users that **all keys are optional** and that Ollama is the recommended free default.

## Coding Conventions

### Python
- Use **type hints everywhere**. mypy is run in CI in strict mode.
- Use **Pydantic v2** for all data models that cross API boundaries.
- All API endpoints are **async**. Use `httpx.AsyncClient` for outbound calls, never `requests`.
- Imports: stdlib → third-party → local, separated by blank lines (ruff handles this).
- Docstrings: Google style for public functions/classes.
- Errors: raise `HTTPException` from FastAPI handlers; raise custom exceptions from domain code (defined in `core/exceptions.py`).

### TypeScript / React
- Functional components only, no class components.
- Use `interface` for component props, `type` for unions/utility types.
- API responses are typed via shared types in `frontend/src/lib/types.ts` — keep these in sync with backend Pydantic models.
- Tailwind for styling. shadcn/ui for primitives. No inline styles unless dynamic.
- File naming: `PascalCase.tsx` for components, `camelCase.ts` for utilities.

### Commits & PRs
- Conventional commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`
- Every PR must pass CI (tests + lint + typecheck) before merge.
- Add tests for new graders or API endpoints.

## Testing Strategy

- **Unit tests**: each grader has its own test file with at least: known-good prompt, known-bad prompt, edge cases (empty, very long, malformed).
- **API tests**: use FastAPI's `TestClient`, mock LLM calls with `pytest-mock` to avoid spending API credits in CI.
- **LLM judge tests**: keep a small set of "golden" prompt/score pairs in `tests/fixtures/golden.json` to detect regressions in judge prompts.
- **Frontend**: component tests for non-trivial UI (compare view, batch upload). Integration test for the full grading flow against a mocked backend.

## Important Notes for Claude Code

1. **When adding a new grader**: create the file in `backend/app/graders/`, register it in `__init__.py`, add a corresponding entry in the `GraderType` enum in `models/schemas.py`, and write tests. Update the README's grader table.

2. **When changing API schemas**: update both the Pydantic model AND the matching TypeScript type in `frontend/src/lib/types.ts`. Mismatch causes silent runtime errors.

3. **LLM calls cost users money (not the maintainer)**: this is BYOK — every user pays for their own API usage. Never ship default keys, never proxy through a maintainer-owned key. In tests, always mock LLM calls with `pytest-mock`. Real LLM calls are gated behind a `pytest -m llm` marker that's skipped in CI by default. Document expected costs in the README (e.g., "grading 100 prompts with Claude Sonnet ≈ $0.50").

4. **First-run experience (Ollama auto-detect)**: when the backend starts, it runs a `detect_provider()` routine in this exact order:
   1. If `JUDGE_PROVIDER` env var is set explicitly → use that (user override wins).
   2. Else, check for paid API keys in `.env` (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GROQ_API_KEY`, `GOOGLE_API_KEY`) → use the first one found.
   3. Else, ping `OLLAMA_BASE_URL` (default `http://localhost:11434/api/tags`) with a 1-second timeout. If it responds, list available models and pick a sensible default (`llama3.1:8b` if present, else first available model).
   4. Else, fall back to rule-based-only mode.
   
   The selected mode is logged at startup and exposed via `GET /api/v1/status` so the frontend can display it. The frontend shows a small badge in the header: "Judge: Ollama (llama3.1:8b)" / "Judge: Claude Sonnet 4.6" / "Rule-based only".
   
   If the user falls into mode 4 (rule-based only), show a non-blocking banner in the UI with two CTAs: "Install Ollama (free, local)" linking to ollama.com, and "Add an API key" linking to docs. Never block grading — rule-based works fine on its own.

5. **Provider detection must be cached**: don't ping Ollama on every request. Detect once at startup, cache the result in `app.state.judge_config`. Add a `POST /api/v1/status/refresh` endpoint so users can re-detect after installing Ollama without restarting the server.

6. **Don't commit secrets**: the pre-commit hook scans for API keys. If you see `detect-secrets` complaining, you have a leaked key — rotate it before pushing.

7. **Performance**: batch grading should stream results as they complete, not block until all are done. Use FastAPI's `StreamingResponse` with NDJSON.

8. **Keep dependencies minimal**: every new dep needs justification. Prefer stdlib, then well-maintained libs, then niche ones.

9. **OSS hygiene**: any user-facing change needs a CHANGELOG.md entry and possibly a docs update. Be friendly to first-time contributors — clear error messages, helpful issue templates.

## Feature Specifications

This section contains detailed specs for major features and bug fixes. When implementing, treat each as a self-contained unit of work. Reference the spec by name (e.g., "Implement Feature 1") and follow it precisely. Each spec ends with **Acceptance Criteria** — verify against this checklist before considering the work done.

---

### Bug Fix #1: Tab Consistency (Grader Controls Across Grade / Compare / Batch)

**Problem:**
The Grade tab has a clean control bar at the bottom: `[Hybrid] [Rule-based] [LLM Judge]` grader-type buttons + a model dropdown (`phi3:latest`) + the `Grade Prompt` action button. The Compare and Batch tabs are missing or have a different layout for these same controls. This is a UX consistency bug — users have to relearn the interface on every tab.

**Goal:**
All three primary tabs (Grade, Compare, Batch) must expose the same grader-type and model controls in the same visual position, with **independent state per tab** (each tab remembers its own selection, switching tabs does NOT propagate the change).

**Design (extract the existing control bar into a reusable component):**

1. Create `frontend/src/components/GraderControlBar.tsx`:
   - Props: `graderType`, `onGraderTypeChange`, `model`, `onModelChange`, `availableModels`, `actionLabel`, `onAction`, `actionDisabled`.
   - Renders the three grader-type buttons (Hybrid / Rule-based / LLM Judge) on the left.
   - Renders the model dropdown next to them — but **only when** `graderType === "hybrid" || graderType === "llm_judge"`. For Rule-based, the dropdown is hidden because it's irrelevant (no LLM is called).
   - Renders the primary action button on the right (`Grade Prompt` / `Compare Prompts` / `Run Batch`). Label is configurable via `actionLabel` prop.
   - Visually identical across tabs: same spacing, same button styles, same disabled states.

2. State ownership — **per-tab independent state**:
   - Each tab page (`GradePage`, `ComparePage`, `BatchPage`) owns its own `useState` for `graderType` and `model`.
   - Switching tabs does NOT carry state across. User explicitly stated: each tab keeps its own selection.
   - Initial default for every tab: `graderType="hybrid"`, `model=` first available model from the provider's model list.

3. Layout per tab:
   - **Grade tab**: textarea on top, `<GraderControlBar />` at the bottom of the card. (No change — this is the reference design.)
   - **Compare tab**: two textareas side-by-side ("Prompt A" / "Prompt B"), then `<GraderControlBar />` at the bottom spanning the full width. Action button label: `Compare Prompts`.
   - **Batch tab**: file upload zone (CSV/JSON drop area) on top, then `<GraderControlBar />` at the bottom. Action button label: `Run Batch`. Action button disabled until a file is selected.

4. Available models list:
   - Comes from `GET /api/v1/status` which returns `{provider, current_model, available_models[]}`.
   - The list is fetched once when the app loads, stored in a context (`ProviderContext`).
   - Each tab reads from this context but maintains its own *selected* model.

**Why repeated controls (and not a global header selector):**
The user has explicitly chosen per-tab independent state. A global selector would imply a shared setting and contradict that choice. Repeated in-tab controls make the active selection unambiguous and discoverable on every screen.

**Acceptance criteria:**
- [ ] `<GraderControlBar />` exists as a reusable component.
- [ ] All three tabs render the same control bar at the bottom of their main content area.
- [ ] Visual styling (button shape, color, spacing, dropdown style) is pixel-identical across tabs.
- [ ] Selecting "Hybrid" in Grade tab does NOT change the selection in Compare or Batch.
- [ ] Model dropdown is hidden when "Rule-based" is selected (in all three tabs).
- [ ] Each tab's action button shows the correct label and disabled state.
- [ ] Available models list is fetched once and shared via context, but per-tab selection is independent.

---

### Feature 1: BYOK Provider Selection (UI + .env fallback)

**Goal:** Let users pick an LLM provider and supply their API key from the UI, with `.env` as a fallback. Responses must be parsed safely with no JSON errors surfacing to the user.

**User stories:**
- As a user, I open Settings and see a dropdown of providers (Anthropic, OpenAI, Google, Groq, Ollama, Rule-based).
- I paste my API key into a password-masked input.
- I tick "Remember this key on this device" if I want it persisted; otherwise it lives only in memory for this session.
- I click "Test connection" — the app makes a minimal call (1-token completion) and shows ✓ success or a friendly error.
- The header badge updates to show the active provider.
- If I don't configure anything in the UI, the app falls back to whatever is in `backend/.env`.
- If `.env` is also empty, it auto-detects Ollama. If Ollama isn't running, rule-based mode activates.

**Resolution priority (highest wins):**
1. UI-supplied key for current session (in-memory)
2. UI-supplied key persisted in browser (if "remember" was ticked)
3. `backend/.env` API keys
4. Ollama auto-detection
5. Rule-based fallback

**Storage rules:**
- "Remember" ticked → store in browser `localStorage` under key `promptgrade.providerConfig`. Key is stored as-is (browser-local, never leaves the device). Add a clear warning tooltip: "Stored in your browser only. Anyone with access to this device can read it."
- "Remember" unticked → keep in React state only; gone on refresh.
- Backend never persists user-supplied keys to disk. They live in `request.headers["X-Provider-Key"]` and `X-Provider-Name` per request, used once, then discarded.
- The `/api/v1/status` response must include the key source (`ui_session`, `ui_persisted`, `env`, `ollama_auto`, `rule_based`) so the UI can display it transparently.

**Technical approach:**
- Backend: add a dependency `get_provider_config(request)` that reads headers first, falls back to env config. Return a typed `ProviderConfig` (Pydantic).
- All grader endpoints accept these optional headers. No URL params (keys must never appear in logs).
- LiteLLM call is wrapped in `try/except` catching `litellm.exceptions.*`, network errors, and `json.JSONDecodeError`. On failure, return a structured `GradeError` response (HTTP 200 with `status: "error"`), never raw 500 with stack trace.
- Frontend: `<ProviderSelector />` component in Settings. Use shadcn `Select`, `Input type="password"`, `Switch` for remember.
- Add a `useProviderConfig()` hook that reads/writes localStorage and exposes `{config, setConfig, testConnection}`.

**No-JSON-error guarantee:**
The LLM judge must always return parseable output. Implementation:
1. The judge prompt explicitly says: "Return ONLY a valid JSON object matching this schema: {...}. No prose, no markdown fences."
2. Parse with `json.loads()` inside a `try/except`. On `JSONDecodeError`, run a regex extraction (`re.search(r"\{.*\}", text, re.DOTALL)`) and retry parse.
3. If still fails, validate with Pydantic `model_validate_json()` which has clearer errors.
4. If all attempts fail, return a fallback `GradeResult` with `score=null`, `feedback="Judge response could not be parsed. Showing rule-based score only."` — and silently degrade to rule-based for that grade. Log the raw output for debugging.
5. The user **never sees** "JSONDecodeError" or any Python exception. Errors are friendly, actionable, and translated to the UI as toast notifications.

**Acceptance criteria:**
- [ ] Settings page renders with provider dropdown, key input, remember checkbox, test button.
- [ ] Test button shows ✓/✗ with clear message within 5s.
- [ ] Header badge updates immediately after successful test.
- [ ] Clearing the UI config and refreshing falls back to `.env` if present.
- [ ] Malformed LLM responses never produce a 5xx or visible JSON error.
- [ ] Keys are never logged, never sent in URL params, never appear in browser history.

---

### Feature 2: Prompt Builder Wizard (plain English → optimized prompt)

**Goal:** Help users who don't know prompt engineering build a high-quality prompt by answering simple questions in a step-by-step wizard.

**Framework used:** CO-STAR + Examples + Constraints (industry best practice, popularized by Singapore GovTech and aligned with Anthropic/OpenAI prompting guides).

**Wizard steps (one screen per step):**

| Step | Field | What we ask | Required | Example placeholder |
|------|-------|-------------|----------|---------------------|
| 1 | **Task** | "What do you want the AI to do?" (free text, 1 sentence) | Yes | "Write product descriptions for an e-commerce site" |
| 2 | **Context** | "What background should the AI know?" | Optional | "We sell sustainable bamboo home goods to eco-conscious millennials" |
| 3 | **Objective** | "What's the goal? What does success look like?" | Yes | "Drive clicks and convey eco-friendliness in under 50 words" |
| 4 | **Style & Tone** | Two dropdowns: Style (formal/casual/technical/creative) + Tone (friendly/authoritative/playful/empathetic/neutral) | Yes | — |
| 5 | **Audience** | "Who is the output for?" | Yes | "Online shoppers aged 25-40, mobile users" |
| 6 | **Response format** | Dropdown (paragraph/bulleted list/JSON/table/markdown/code) + optional length | Yes | — |
| 7 | **Examples** | "Paste 1-3 examples of ideal output (optional but boosts quality 30%+)" | Optional | — |
| 8 | **Constraints** | "Anything to avoid? Any must-haves?" | Optional | "No superlatives like 'best ever'. Always mention free shipping." |
| 9 | **Review & generate** | Show all answers, let user edit, then click "Build my prompt" | — | — |

**Technical approach:**
- Backend endpoint: `POST /api/v1/build` accepts a `PromptBlueprint` (Pydantic model with all 8 fields, most optional) and returns `{prompt: str, explanation: str, generated_by: "llm" | "template"}`.
- Internally, this calls the LLM judge with a meta-prompt: "You are an expert prompt engineer. Given this blueprint, write a production-ready prompt following the CO-STAR framework. Output ONLY the final prompt, no preamble." Same JSON-safety rules as Feature 1.
- If no LLM is available (rule-based mode), the endpoint **assembles a template-based prompt** using string formatting. Not as good as LLM-generated, but works offline.
- Auto-grade the generated prompt immediately and show the score on the final screen (ties into Feature 3).

**Frontend:**
- `<PromptBuilder />` component using shadcn `Tabs` or a custom stepper.
- Progress indicator at top (1 of 9, 2 of 9, ...).
- "Back" / "Next" / "Skip" (for optional steps) buttons.
- "Save draft" button that persists wizard state to localStorage so users can come back.
- On final screen: copy button, "Grade this prompt" button (jumps to Grade view with prompt pre-filled), "Edit" (back to step 1).

**Acceptance criteria:**
- [ ] Wizard navigation works forward/back without losing data.
- [ ] Required fields show validation errors before allowing Next.
- [ ] Optional fields show "Skip" option.
- [ ] Generated prompt appears on screen 9 with auto-graded badge (Feature 3).
- [ ] "Save draft" preserves state across refresh.
- [ ] Works in rule-based mode using template fallback (no LLM needed).

---

### Feature 3: Excellence Badge (score-based status)

**Goal:** Show a simple visual signal — Excellent or Needs Review — instead of overwhelming users with raw numbers. Power users can still see the full breakdown via a toggle.

**Rules:**
- Score `>= 90` → display badge: `✨ Excellent` (green/emerald, `bg-emerald-100 text-emerald-800`)
- Score `< 90` → display badge: `⚠️ Needs Review` (amber, `bg-amber-100 text-amber-800`)
- Score `null` (judge failed, rule-based unavailable) → `❓ Unknown` (gray, `bg-gray-100 text-gray-600`)

**Where to show the badge:**
- Top-right of `<GradeResultCard />` (Grade tab)
- Top-right of each row in `<BatchResultsTable />` (Batch tab)
- Top-right of each side in `<ComparisonView />` (Compare tab)
- Final step of `<PromptBuilder />` (Feature 2)

**Implementation:**
- Single reusable `<ScoreBadge score={number | null} />` component in `frontend/src/components/ScoreBadge.tsx`.
- Pure UI, no business logic. Threshold (90) defined as `EXCELLENT_THRESHOLD` in `frontend/src/lib/constants.ts` so it's easy to change later.
- Raw score is **still computed and stored** in the backend (we don't lose data), but only the badge is shown by default. Add a small "Show details" toggle on the result card that expands to reveal the numeric score and per-dimension breakdown for power users.

**Acceptance criteria:**
- [ ] Badge renders in all 4 locations listed above.
- [ ] Color and icon change based on score threshold.
- [ ] Null/error states render the gray "Unknown" badge gracefully.
- [ ] "Show details" toggle reveals full breakdown without page reload.
- [ ] Threshold is a single source of truth (one constant).

---

### Feature 4: Prompt Builder UI Integration

**Goal:** Add the Builder (Feature 2) into the existing UI in a discoverable, non-intrusive way that fits the existing tab structure (Grade / Compare / Batch).

**Recommended approach (UX best practice):**

1. **Primary entry: a fourth top-nav tab.**
   The header navigation should add a `Build` tab alongside `Grade`, `Compare`, `Batch`. The Build tab is the dedicated home for the wizard. This keeps it discoverable and gives it the room a 9-step wizard needs.

2. **Secondary entry: contextual CTA on Grade tab.**
   On the Grade tab, next to the existing `Grade Prompt` button (in the `<GraderControlBar />`), add a small secondary text link: `✨ Build with AI`. Clicking it routes to the Build tab. This catches users who land on Grade not knowing what to type.

3. **Empty state on Grade tab.**
   When the prompt textarea is empty, show a subtle hint below it: "Don't know where to start? Try the Prompt Builder →" (link to Build tab).

4. **Cross-tab handoff.**
   - Build → Grade: when wizard finishes, "Grade this prompt" button navigates to Grade tab with the generated prompt pre-filled (use URL state or React Router state).
   - Grade → Build: optional "Improve with Builder" button on a low-scoring grade result — pre-fills the wizard with the existing prompt as the starting Task.

**Why a tab and not a modal:** modals are good for short forms. A 9-step wizard with optional fields and draft-save needs persistent space, scrolling, and a URL it can be linked to. A dedicated tab serves this better.

**Why not a side drawer:** drawers compete with main content for screen space and feel "temporary" — users hesitate to invest time in something dismissable.

**Routing:**
- `/grade` (existing)
- `/compare` (existing)
- `/batch` (existing)
- `/build` (new) — wizard
- `/build/:draftId` (optional, future) — saved drafts

**Acceptance criteria:**
- [ ] Four tabs visible in header: Grade, Compare, Batch, Build.
- [ ] Active tab highlighted clearly (matches existing Grade-tab highlight style).
- [ ] Secondary "✨ Build with AI" link visible in Grade tab's control bar.
- [ ] Empty-state hint on Grade tab links to Build tab.
- [ ] Build → Grade handoff pre-fills the prompt.
- [ ] Browser back/forward works correctly across tabs.
- [ ] Mobile-responsive: tabs collapse to a hamburger or scrollable bar on narrow screens.

---

## Current Roadmap

- [x] Core grader interface + rule-based grader
- [x] LLM-as-judge grader via LiteLLM (multi-provider)
- [x] Ollama auto-detection on startup
- [x] Hybrid grader (rules + LLM weighted)
- [x] REST API (single, batch, compare, status)
- [x] React dashboard with comparison view + provider badge
- [ ] **Bug Fix #1**: Tab consistency (GraderControlBar across Grade/Compare/Batch)
- [ ] **Feature 1**: BYOK provider selection UI with .env fallback
- [ ] **Feature 2**: Prompt builder wizard (CO-STAR framework)
- [ ] **Feature 3**: Excellence badge (Excellent / Needs Review)
- [ ] **Feature 4**: Builder integrated as 4th top-nav tab + contextual CTAs
- [ ] Custom rubric builder UI
- [ ] Multi-judge ensemble (Claude + GPT, vote/average)
- [ ] Self-hosted via Docker Compose (with Ollama service bundled)
- [ ] CLI tool (`promptgrade grade prompt.txt`)
- [ ] Plugin system for custom graders
