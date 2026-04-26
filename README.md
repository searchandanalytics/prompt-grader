# PromptGrade

> Score, compare, and build better prompts — powered by rule-based analysis and LLM-as-judge evaluation. Run fully local with Ollama, or bring your own API key.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Node 18+](https://img.shields.io/badge/node-18+-green.svg)](https://nodejs.org/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

---

## Features

### Grade — Score any prompt instantly

Paste a prompt and get a 0–100 score with a full breakdown across five dimensions. Three grading modes:

| Mode | How it works | Best for |
|---|---|---|
| **Hybrid** | Rule-based + LLM judge (30/70 weighted) | Most accurate, default |
| **Rule-based** | Deterministic heuristics, no LLM | Offline, free, fast |
| **LLM Judge** | Pure LLM evaluation against the rubric | Deep qualitative feedback |

Score interpretation:
- **Excellent** (90–100) — production-ready prompt
- **Needs Review** (<90) — specific feedback on what to improve

Each grading result includes per-dimension sub-scores, actionable feedback text, and the provider that generated the evaluation.

---

### Compare — A/B test two prompts side by side

Enter two prompt variants and run them through the same grader at once. See:

- Individual scores for Prompt A and Prompt B
- Per-dimension breakdown for both
- Automatic winner declaration (A / B / Tie)

Useful for iterating on prompt rewrites — you can objectively verify whether a change improved the score before shipping it.

---

### Batch — Grade many prompts at once

Upload a CSV or JSON file containing multiple prompts. Results stream back as they complete (no waiting for the full batch). Each row gets an individual score, breakdown, and feedback.

Output can be used to:
- Audit a prompt library for quality regressions
- Find the weakest prompts in a dataset
- Track prompt quality across releases

---

### Build — Prompt Builder Wizard

A 9-step guided wizard that turns plain English answers into a production-ready, auto-graded prompt. Based on the CO-STAR framework (Context, Objective, Style, Tone, Audience, Response format).

**Wizard steps:**

| Step | Field | Required |
|---|---|---|
| 1 | Task — what the AI should do | Yes |
| 2 | Context — background the AI needs | Optional |
| 3 | Objective — what success looks like | Yes |
| 4 | Style & Tone — formal/casual/technical + friendly/authoritative/etc. | Yes |
| 5 | Audience — who the output is for | Yes |
| 6 | Response format — paragraph/list/JSON/table/markdown/code | Yes |
| 7 | Examples — 1–3 examples of ideal output | Optional |
| 8 | Constraints — things to avoid or must-haves | Optional |
| 9 | Review & generate | — |

On the final step, the builder generates your prompt (via LLM if available, via template offline) and auto-grades it so you know the quality before you use it. Draft state is saved to localStorage so you can leave and come back.

---

### Scoring Rubric (5 dimensions)

Every grader evaluates prompts across the same five dimensions, each weighted equally by default:

| Dimension | What it measures |
|---|---|
| **Clarity** | Is the request clear and unambiguous? |
| **Specificity** | Are constraints, format, and scope defined? |
| **Structure** | Is the prompt well-organized and logically ordered? |
| **Task Alignment** | Does the prompt match the stated goal? |
| **Safety** | Is it free of harmful or manipulative patterns? |

Weights are configurable per request via the rubric API parameter.

---

### BYOK — Bring Your Own Key

PromptGrade never pays for your LLM calls. You connect your own provider in Settings:

1. Open **Settings** (gear icon, top right)
2. Select your provider (Anthropic, OpenAI, Google, Gemini, Groq, Ollama)
3. Paste your API key
4. Optionally tick **Remember on this device** (stored in browser localStorage only — never sent to any server)
5. Click **Test connection** — see latency and confirmation before saving

Provider priority (highest wins):

1. Key supplied in Settings for this session
2. Key saved in browser from a previous visit
3. Key in `backend/.env`
4. Ollama auto-detected locally
5. Rule-based only (no key, no model)

The header badge always shows the active provider and source (e.g. "Judge: Claude · via UI · this session").

**Supported providers:**

| Provider | Free tier | Notes |
|---|---|---|
| Ollama | Free (local) | Recommended for first-run. Pulls `llama3.1:8b` by default |
| Anthropic | No | Claude Sonnet 4.6 |
| OpenAI | No | GPT-4o-mini |
| Google Gemini | Yes | Gemini Flash |
| Groq | Yes | Llama 3.1 70b |
| Rule-based only | Free | Works offline, no model needed |

**Estimated cost for grading 100 prompts with LLM judge:**

| Provider | ~Cost |
|---|---|
| Ollama | Free |
| Anthropic Claude Sonnet 4.6 | ~$0.50 |
| OpenAI GPT-4o-mini | ~$0.10 |
| Google Gemini Flash | Free tier covers it |
| Groq Llama 3.1 | Free tier covers it |

---

### Live Provider Health

The backend health-checks the active provider on every status poll. If a provider goes down (e.g. Ollama stops running), the server automatically falls back to the next available provider and the UI shows a dismissible amber banner explaining what changed. The header badge updates within 30 seconds.

---

## Quick Start

### Option 1: Ollama — local, free, no account needed

```bash
# Install Ollama: https://ollama.com
ollama pull llama3.1:8b

git clone https://github.com/YOUR_USERNAME/promptgrade.git
cd promptgrade

# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — the header shows "Judge: Ollama (llama3.1:8b)".

### Option 2: API key (BYOK)

Copy `.env.example` to `backend/.env` and add one key:

```env
ANTHROPIC_API_KEY=sk-ant-...
# OR
OPENAI_API_KEY=sk-...
# OR
GOOGLE_API_KEY=...
# OR
GROQ_API_KEY=gsk_...
```

The app auto-detects which key is present and uses that provider.

### Option 3: No setup

Just run it. Rule-based mode works with zero configuration — no API key, no local model.

---

## API Reference

```bash
# Grade a single prompt
curl -X POST http://localhost:8000/api/v1/grade \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Write a poem about the sea", "grader": "hybrid"}'

# Compare two prompts
curl -X POST http://localhost:8000/api/v1/compare \
  -H "Content-Type: application/json" \
  -d '{
    "prompt_a": "Write a poem about the sea",
    "prompt_b": "Write a 14-line sonnet about the sea in iambic pentameter",
    "grader": "hybrid"
  }'

# Batch grade (results stream as NDJSON)
curl -X POST http://localhost:8000/api/v1/batch \
  -F "file=@prompts.csv" \
  -F "grader=hybrid"

# Build a prompt from a blueprint
curl -X POST http://localhost:8000/api/v1/build \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Write product descriptions",
    "objective": "Drive clicks for eco-conscious shoppers",
    "style": "casual",
    "tone": "friendly",
    "audience": "millennials",
    "response_format": "paragraph"
  }'

# Check active provider
curl http://localhost:8000/api/v1/status

# Re-detect provider (after installing Ollama without restart)
curl -X POST http://localhost:8000/api/v1/status/refresh
```

Full interactive docs at `http://localhost:8000/docs`.

---

## Architecture

```
┌─────────────────┐         ┌──────────────────────┐
│  React + Vite   │────────▶│  FastAPI             │
│  TypeScript     │  REST   │  Python 3.10+        │
│  TailwindCSS    │         └──────────┬───────────┘
└─────────────────┘                    │
                         ┌─────────────┼──────────────┐
                         ▼             ▼              ▼
                    ┌─────────┐  ┌──────────┐  ┌─────────┐
                    │  Rule-  │  │   LLM    │  │ Hybrid  │
                    │  based  │  │  Judge   │  │ grader  │
                    │ grader  │  │ (LiteLLM)│  │30% + 70%│
                    └─────────┘  └────┬─────┘  └─────────┘
                                      │
                ┌─────────┬───────────┼──────────┬─────────┐
                ▼         ▼           ▼          ▼         ▼
             Claude     GPT       Gemini       Groq     Ollama
```

---

## Roadmap

- [x] Rule-based grader
- [x] LLM-as-judge via LiteLLM (multi-provider)
- [x] Hybrid grader (rule-based + LLM weighted)
- [x] Ollama auto-detection and health monitoring
- [x] A/B comparison view
- [x] Batch grading with streaming results
- [x] BYOK Settings UI with test connection
- [x] Prompt Builder wizard (CO-STAR framework)
- [x] Live provider health check + fallback banner
- [ ] Custom rubric builder UI
- [ ] Multi-judge ensemble (Claude + GPT, vote/average)
- [ ] Docker Compose with bundled Ollama
- [ ] CLI tool (`promptgrade grade prompt.txt`)
- [ ] Plugin system for custom graders

---

## Contributing

Good areas to start:

- **New grader** — subclass `Grader` in `backend/app/graders/`
- **New provider** — LiteLLM handles most; custom adapters welcome
- **Domain rubrics** — code, marketing, customer support rubric presets
- **Docs and examples** — always useful

See [CONTRIBUTING.md](CONTRIBUTING.md) for the development workflow.

---

## License

[MIT](LICENSE)

---

*Inspired by [Promptfoo](https://github.com/promptfoo/promptfoo), [DeepEval](https://github.com/confident-ai/deepeval), and the broader prompt-engineering community. Built with [FastAPI](https://fastapi.tiangolo.com/), [LiteLLM](https://github.com/BerriAI/litellm), and [Vite](https://vitejs.dev/).*
