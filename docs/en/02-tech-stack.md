# Tech Stack

> Language: [中文](../zh/02-tech-stack.md) · [日本語](../ja/02-tech-stack.md) · **English**
> Status: Draft v0.2 · Updated: 2026-09-16
> The Chinese version is the source of truth. If versions differ, the Chinese version wins.
> This document records the technology choices for StyleAI v2 and the reasoning behind them. Items marked "to validate" are confirmed with a prototype in the listed milestone before they become final. For how each technique works, see the [tech notes](https://github.com/ailuruschen-bit/stylist-agent/tree/tech-notes/docs/zh/tech-notes) on the `tech-notes` branch (Chinese); for how the pieces fit together, see [System architecture](05-system-architecture.md).
> Model IDs and library versions were checked in September 2026.

## 1. Principles

1. **Reuse what the demo proved.** FastAPI, Next.js, job-based processing, SSE, Gemini image generation, login and credits all run in HackathonPJT.
2. **Keep infrastructure minimal.** Through M0–M6 we depend only on PostgreSQL and object storage: no Redis, Kafka or Temporal.
3. **Keep models swappable.** LLMs, image, segmentation and embedding models all sit behind internal provider interfaces.
4. **Stay close to the API.** Model capabilities move fast, so we use official vendor SDKs directly rather than adding an abstraction framework in between.
5. **Compliance first.** We never get around bot protection or CAPTCHAs, and we never store copyrighted text or images.
6. **Web only.** Phones are covered by responsive layout; there is no native app.

## 2. Overview

| Layer | Choice | Alternatives | Status |
|---|---|---|---|
| Frontend | Next.js 16 (App Router) + React 19 + TypeScript | Remix, Vite + React | Decided |
| UI | Tailwind CSS 4 + shadcn/ui | MUI, Chakra | Decided |
| Frontend data | TanStack Query (server state) + Zustand (local UI state) | SWR, Redux | Decided |
| i18n | next-intl (zh-CN / ja / en) | Keep the demo's custom i18n | Decided |
| Backend | Python 3.13 + FastAPI + Pydantic 2 | NestJS | Decided |
| ORM & migrations | SQLAlchemy 2 (async) + Alembic, driver psycopg 3 | SQLModel | Decided |
| Agent integration | Anthropic Python SDK with our own tool-use loop | SDK Tool Runner, LangGraph, Google ADK | Decided; Tool Runner compared in M0 |
| Conversation & orchestration model | `claude-opus-5` | `claude-fable-5-1` | Decided |
| Background models | `claude-sonnet-5`, `claude-haiku-4-5` | — | Decided |
| Image model | `gemini-3.1-flash-image` (Nano Banana 2) | `gemini-3-pro-image` (Nano Banana Pro), GPT Image, FLUX.1 Kontext | To validate (M3) |
| Image SDK | Google Gen AI SDK (`google-genai`) | — | Decided; Interactions API vs generateContent chosen in M0 |
| Cutout | BiRefNet (self-hosted) | Other BiRefNet variants, commercial background removal APIs | To validate (M1) |
| Embeddings | `voyage-multimodal-3.5` | Gemini Embedding, SigLIP (self-hosted) | To validate (M1) |
| Database | PostgreSQL 17 + pgvector | — | Decided |
| Job queue | Procrastinate 3.x (PostgreSQL-based) | Celery + Redis, arq, Temporal | Decided |
| Realtime | SSE + an events table + PostgreSQL LISTEN/NOTIFY | WebSocket, Redis Pub/Sub | Decided |
| Object storage | S3-compatible: Cloudflare R2 in production, filesystem locally | AWS S3 | Decided |
| Hosting | Web: Vercel; API / worker: containers in Tokyo; database: managed PostgreSQL in Tokyo | — | To validate (M0) |
| Observability | structlog + OpenTelemetry + Sentry + our own agent trace | Langfuse | Decided |
| Package managers | pnpm 10 (frontend), uv (backend) | npm, poetry | Decided |

## 3. Repository layout

```text
stylist-agent/
├── apps/
│   ├── web/                 # Next.js frontend
│   └── api/                 # FastAPI app, agent, pipelines, worker (same codebase, separate processes)
│       ├── app/             # package layout: see "System architecture" section 4
│       ├── migrations/      # Alembic
│       └── tests/
├── services/
│   └── segmentation/        # BiRefNet inference service (GPU), deployed separately
├── knowledge/               # human-curated technique cards (YAML), reviewed via PR
├── evals/                   # datasets and eval runners
├── infra/                   # docker compose, deployment configs
└── docs/                    # zh / ja / en documentation
```

Frontend and backend share one repository but keep their own language toolchains; no cross-language build tool (Nx, Turborepo) is introduced. The API and the worker run the same codebase as separate processes; segmentation is deployed separately because it needs a GPU and large weights.

## 4. Frontend

| Choice | Why | Watch out for |
| --- | --- | --- |
| Next.js 16 + React 19 | Already used in the demo; Server Components suit read-heavy pages like the wardrobe and look list | The chat page is interaction-heavy and is built as a client component |
| Tailwind CSS 4 + shadcn/ui | Component source lives in the repo and can be reshaped to StyleAI's visual identity | Design tokens are defined once; components never hardcode colors |
| TanStack Query | Caching, refetching and optimistic updates for server data | SSE events update the matching query cache |
| Zustand | Local state such as the composer and panel toggles | Never holds server data |
| next-intl | Trilingual copy, date and currency formatting | Prices always shown in yen |
| openapi-typescript | Types generated from the backend's OpenAPI keep the contract aligned | Generated files are committed; CI checks they are current |

**SSE client**: the browser's `EventSource` only issues GET requests and cannot set custom headers. StyleAI's event endpoint is a GET authenticated by cookie, so `EventSource` works directly, and the browser adds `Last-Event-ID` on reconnect.

**Testing**: Vitest + Testing Library for components, Playwright for the three main flows (upload and ingest, get a look from chat, view the render).

## 5. Backend

| Choice | Why |
| --- | --- |
| Python 3.13 + FastAPI | Same as the demo; the richest ecosystem for AI SDKs and image work, with native async and OpenAPI |
| Pydantic 2 | One set of models for requests, responses, tool inputs and structured outputs |
| SQLAlchemy 2 async + psycopg 3 | psycopg 3 supports async and LISTEN/NOTIFY and is Procrastinate's connector, so one driver covers everything |
| Alembic | Schema changes are versioned and reviewable |
| uv | Fast dependency resolution with a reproducible lockfile |
| ruff + mypy | Formatting, linting and type checking |

**Auth**: port the demo's email/password sessions with cookies. Third-party sign-in (Google, LINE) is a later requirement.

## 6. Agent and LLMs

### 6.1 Model roles

| Use | Model | effort | Why |
|---|---|---|---|
| Conversation and orchestration | `claude-opus-5` | high | Understanding the request, composing looks and planning renders need the strongest judgment |
| Render planning and critique | `claude-opus-5` | high | Vision accuracy matters, and keeping it separate from the image model avoids self-grading |
| Magazine learning, tagging re-checks | `claude-sonnet-5` | medium | Lots of reading with some judgment, at lower cost |
| Bulk tagging of wardrobe and catalog | `claude-haiku-4-5` | — | High volume with a fixed output shape; speed matters |

Model IDs and effort levels live in configuration. Initial effort values are calibrated against the eval set in M0.

### 6.2 Integration

| Option | Verdict | Reason |
|---|---|---|
| Anthropic SDK + our own loop | **Chosen** | The loop is short; every content block must be persisted and turned into an SSE event; budgets are checked between iterations; server tools require handling `pause_turn` |
| Anthropic SDK Tool Runner | Compared in M0 | Removes boilerplate, but the Python runner currently does not resume `pause_turn` automatically; we need to confirm the hook points for events and budgets |
| Claude Agent SDK | Not chosen | Built for filesystem and coding tasks; its built-in tools don't apply |
| Managed Agents | Not for the main conversation; evaluated for background work in M5 | Scheduled runs suit background agents, but the main conversation is tightly coupled to our database and SSE |
| LangGraph / Google ADK | Not chosen | The main flow is simple; long pause-and-resume work is already handled by the job queue; another abstraction delays access to new Claude features |
| Spring AI | Not applicable | A Java framework; the StyleAI backend is Python |

How each option works and how they differ is covered in the tech notes on the agent tool loop and on SDKs and agent frameworks.

### 6.3 API features we use

| Feature | Use |
| --- | --- |
| Adaptive thinking + effort | Enabled for conversation and planning, with effort set per use |
| Streaming | Every conversation request, converted into StyleAI's own SSE events |
| Prompt caching | Tool definitions, system prompt and card index kept first and byte-stable |
| Structured outputs | Tagging results, look cards, render plans, critique results |
| `strict` tool definitions | Every custom tool |
| Server tools `web_search` / `web_fetch` | Brand scouting (restricted to brand domains) and magazine learning (approved sources) |
| Server-side compaction | Summarizes earlier history in long conversations |
| Server-side refusal fallbacks | Enabled per the recommended Claude Opus 5 configuration |

## 7. Image generation

### 7.1 Models

Gemini's current image models (all generally available):

| Model ID | Name | Reference image limits | Output resolutions |
| --- | --- | --- | --- |
| `gemini-3.1-flash-image` | Nano Banana 2 | 10 object + 4 character + 3 style | 1K, 2K, 4K |
| `gemini-3-pro-image` | Nano Banana Pro | 6 object + 5 character | 1K, 2K, 4K |
| `gemini-3.1-flash-lite-image` | Nano Banana 2 Lite | 14 object | 0.5K, 1K |

`gemini-3.1-flash-image` is the primary choice: its reference-image budget covers "model reference plus several garments", it supports 3:4, and its speed and cost suit multi-stage rendering. Every generated image carries an invisible SynthID watermark.

In M3 we blind-compare `gemini-3-pro-image`, OpenAI GPT Image and FLUX.1 Kontext on the eval set. Criteria: garment fidelity against the truth image, model identity consistency, how well unconventional wears come out, consistency across several edits, cost and latency per image, and commercial license terms.

### 7.2 Which API shape

The Gemini API currently offers two: the newer Interactions API that Google recommends (interactions are stored server-side and continued with `previous_interaction_id`), and `generateContent`, which remains fully supported. M0 picks one, after checking:

- what server-side storage means for the privacy of user images, and how multi-stage editing is written with storage disabled;
- how the two shapes differ in cost and consistency when "the previous stage's output" is the input.

### 7.3 Provider interface

```python
class ImageProvider(Protocol):
    async def generate(self, refs: list[ImageRef], prompt: str, spec: OutputSpec) -> ImageResult: ...
    async def edit(self, image: ImageRef, refs: list[ImageRef], prompt: str, spec: OutputSpec) -> ImageResult: ...
```

`ImageResult` carries the image, the model, latency and billable usage. The render pipeline depends only on this interface.

## 8. Wardrobe ingestion: cutout, color, tagging

**Cutouts use a segmentation model, not a generative one.** A generative model's output pixels are redrawn, so texture, prints and text shift. Ingestion needs a truth image that color extraction, tagging and render critique can all rely on.

| Candidate | Notes | License |
| --- | --- | --- |
| BiRefNet (general / HR / matting / lite) | High-resolution dichotomous segmentation with good edges; can output an alpha matte | MIT |
| Commercial background removal APIs | No GPU to deploy | Per service terms and pricing |

M1 compares edge quality, detail retention and latency on 50 real garment photos, and confirms the license of the chosen weights.

**Colors are computed**: garment pixels only → CIELAB → masked blur then k-means → merge shades of the same fabric by CIEDE2000 → filter dominant colors by share → recover accents from the raw pixels → name against a reference table. The output is hex values, CIELAB values and shares. The algorithm and its experiments are in the color extraction tech note.

**Other attributes come from vision tagging**: Haiku 4.5 with structured outputs; low-confidence fields are re-checked by Sonnet 5.

**Embeddings**: `voyage-multimodal-3.5` embeds garment images and tag text for similar-item search and look retrieval. M1 compares it against the alternatives on top-5 hit rate for similar-item search.

## 9. Data, job queue and realtime delivery

**PostgreSQL 17 + pgvector**: business data, the job queue, events and vector search live in one database, so a job and the business data it depends on commit in the same transaction.

How **Procrastinate 3.x** works and how StyleAI uses it:

| Mechanism | How Procrastinate does it | How StyleAI uses it |
| --- | --- | --- |
| Claiming a job | A database function with `FOR UPDATE SKIP LOCKED` that flips the row to doing in the same statement | Several workers run in parallel |
| New-job notification | An insert trigger calls `pg_notify`; workers listen, with a 5-second poll as fallback | Ingestion and rendering start promptly |
| Worker heartbeats | Every 10 seconds by default; a worker silent for 30 seconds counts as lost | A scheduled job recovers stalled jobs and resumes from the first incomplete stage |
| Retries | `RetryStrategy`: fixed, linear or exponential waits | External API failures |
| `lock` | A partial unique index: only one job with a given lock can be doing | One render at a time per look |
| `queueing_lock` | A partial unique index: only one job with a given value can be todo | No duplicate ingestion jobs |
| Periodic jobs | Cron expressions, with a database unique constraint preventing duplicate enqueues | Brand sweeps, magazine learning, stalled-job recovery |

Queues: `ingest`, `render`, `scout`, `learn`, `maintenance`. The `render` queue runs on its own workers so slow renders cannot starve ingestion.

**Realtime delivery**: events are written to `agent_events` and then announced with `NOTIFY`; API instances listen and push SSE, replaying from the table by `Last-Event-ID` on reconnect.

The mechanics and experiments are in the PostgreSQL task queue tech note.

## 10. Brand data

Japan is the launch market, so the catalog uses each brand's Japanese site (see Content sources). In order of preference:

1. **Product data from official or affiliate channels**: the most stable and the safest for compliance; researched per brand from M0.
2. **Public product pages**: respecting robots.txt and terms, at a low request rate, reading the structured data on the page.
3. **Never**: getting around CAPTCHAs, spoofing fingerprints, or defeating bot protection.

Known risk: major brand sites are expected to have strong bot protection and heavy client-side rendering, so page fetching may be unreliable. A brand with neither an affiliate channel nor readable pages is replaced in the launch set rather than fought.

## 11. Hosting (to validate · M0)

| Component | Leading option | Notes |
|---|---|---|
| Web | Vercel | Native Next.js support |
| API / worker | Container platform in Tokyo (Fly.io `nrt` or AWS ECS `ap-northeast-1`) | Close to users and the database; must support long-lived SSE connections |
| PostgreSQL | Managed service in Tokyo (Supabase or AWS RDS) with pgvector | M0 compares price, connection limits (for LISTEN) and operations cost |
| Object storage | Cloudflare R2 | S3-compatible, no egress fees |
| Segmentation | On-demand GPU or serverless GPU | Decided in M1 based on volume |

## 12. Observability and evaluation

- **Logs**: structlog JSON with `request_id` and `trace_id` throughout; no secrets or private user data.
- **Tracing**: OpenTelemetry across HTTP, the database and external APIs; `trace_id` travels into workers through job arguments.
- **Agent trace**: see section 12 of System architecture.
- **Error monitoring**: Sentry for web and API.
- **Evals**: datasets and runners in `evals/`. Prompt or tool changes run a smoke eval in CI; each milestone ends with a full run. The eval sets are the tagging label set, the blind look-review set, and the render fidelity set.

## 13. Version baseline

| Component | Version |
| --- | --- |
| Node.js / pnpm | 24 LTS / 10 |
| Next.js / React / Tailwind CSS | 16 / 19 / 4 |
| Python / uv | 3.13 / latest stable |
| FastAPI / Pydantic / SQLAlchemy | latest stable / 2 / 2 |
| psycopg / Procrastinate | 3 / 3.x |
| PostgreSQL / pgvector | 17 / latest stable |
| anthropic / google-genai | Latest stable, pinned in the lockfile |

## 14. Open validations

| Item | Milestone | How |
|---|---|---|
| Hand-written loop vs Tool Runner | M0 | Implement the same scenario both ways; compare code volume and where events and budgets can hook in |
| Interactions API vs generateContent | M0 | Multi-stage editing, privacy settings, cost |
| Hosting platform and database provider | M0 | Price, latency, connection limits and operations cost in Tokyo |
| Third-party model service data terms | M0 | Whether user images are used for training, and retention periods |
| Brand affiliate channels | From M0 | Per brand: product data channels and terms in Japan |
| Cutout model | M1 | 50 samples: edge quality, detail retention, latency, license |
| Embedding model | M1 | Top-5 hit rate for similar-garment search |
| Color extraction thresholds | M1 | Calibrate dominant and accent thresholds on the 200-garment label set |
| Image model | M3 | Blind review on the criteria in section 7.1 |
| Moving background agents to Managed Agents | M5 | Operations cost versus control |
