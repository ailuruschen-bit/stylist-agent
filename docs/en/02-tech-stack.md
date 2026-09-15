# Tech Stack

> Language: [中文](../zh/02-tech-stack.md) · [日本語](../ja/02-tech-stack.md) · **English**
> Status: Draft v0.1 · Updated: 2026-09-15
> The Chinese version is the source of truth. If versions differ, the Chinese version wins.
> This document records the technology choices for StyleAI v2 and the reasons behind them. Items marked “to validate” will be confirmed with a prototype in the listed milestone before they are final.

## 1. Principles

1. **Reuse what the demo proved.** FastAPI, Next.js, the job queue, SSE, Gemini image generation, login and credits all run in HackathonPJT. Reusing them lowers risk.
2. **Keep infrastructure minimal.** Through M0–M6 we depend only on PostgreSQL and object storage. No Redis, Kafka or Temporal.
3. **Keep models swappable.** LLMs, image models and embedding models all sit behind internal interfaces, so they are easy to compare and replace.
4. **Compliance first.** We never get around bot protection or CAPTCHAs, and we never store copyrighted text or images.
5. **Web only.** The first release is web only. Phones are covered with a responsive layout; there is no native app.

## 2. Overview

| Layer | Choice | Alternatives | Status |
|---|---|---|---|
| Frontend | Next.js 16 (App Router) + React 19 + TypeScript | Remix, Vite + React | Decided |
| UI | Tailwind CSS 4 + shadcn/ui | MUI, Chakra | Decided |
| Frontend state | TanStack Query (server state) + Zustand (local UI state) | SWR, Redux | Decided |
| i18n | next-intl (zh-CN / ja / en) | Keep the demo's custom i18n | Decided |
| Backend | Python 3.13 + FastAPI + Pydantic 2 | NestJS | Decided |
| ORM & migrations | SQLAlchemy 2 (async) + Alembic | SQLModel, Tortoise | Decided |
| Agent integration | Anthropic Python SDK + our own tool-use loop | Claude Agent SDK, Managed Agents, LangGraph | Decided |
| Main model | Claude Opus 5 | Claude Fable 5.1 | Decided |
| Background models | Claude Sonnet 5, Claude Haiku 4.5 | — | Decided |
| Image model | Gemini 3.1 Flash Image | Gemini 3 Pro Image, GPT Image, FLUX Kontext | To validate (M3) |
| Cutout | BiRefNet (self-hosted) | remove.bg, Photoroom API | To validate (M1) |
| Database | PostgreSQL 17 + pgvector | — | Decided |
| Embeddings | Voyage multimodal | Gemini Embedding, SigLIP (self-hosted) | To validate (M1) |
| Job queue | Procrastinate (PostgreSQL-based) | Celery + Redis, arq, Temporal | Decided |
| Realtime | SSE + PostgreSQL LISTEN/NOTIFY | WebSocket, Redis Pub/Sub | Decided |
| Object storage | S3-compatible (Cloudflare R2 in production), local filesystem in development | AWS S3 | Decided |
| Hosting | Web: Vercel; API / worker: containers in Tokyo; database: managed PostgreSQL in Tokyo | — | To validate (M0) |
| Observability | structlog + OpenTelemetry + Sentry + our own agent trace | Langfuse | Decided |
| Package managers | pnpm 10 (frontend), uv (backend) | npm, poetry | Decided |

## 3. Repository layout

```text
stylist-agent/
├── apps/
│   ├── web/                 # Next.js frontend
│   └── api/                 # FastAPI app, agent, tools, worker (same codebase, separate processes)
│       ├── app/
│       │   ├── api/         # HTTP routers (thin)
│       │   ├── services/    # business logic
│       │   ├── repositories/# database access
│       │   ├── agent/       # orchestrator loop, prompts, tool definitions
│       │   ├── providers/   # LLM / image / embedding / storage adapters
│       │   └── worker/      # background tasks (render pipeline, ingest, sweeps)
│       ├── migrations/      # Alembic
│       └── tests/
├── knowledge/               # human-curated technique cards (YAML), reviewed via PR
├── evals/                   # datasets and eval runners
├── infra/                   # docker compose, deployment configs
└── docs/                    # zh / ja / en documentation
```

Frontend and backend live in one repository (a monorepo), but each keeps its own language's toolchain. We don't add cross-language build tools like Nx or Turborepo. The API and the worker share one codebase and run as separate processes.

## 4. Frontend

- **Next.js 16 + React 19**: Already used in the demo. Server Components suit read-heavy pages like the wardrobe and the gallery.
- **shadcn/ui**: Component source lives in the repo, so it can be reshaped to StyleAI's visual identity without fighting a library theme.
- **API types**: Generated from FastAPI's OpenAPI document with `openapi-typescript`. We never hand-write API types.
- **Streaming chat**: The frontend consumes the backend's SSE events directly (see section 8 of the development guidelines). Because the agent runs in Python, we don't use tools like the Vercel AI SDK that assume a Node backend.
- **Testing**: Vitest + Testing Library for components, Playwright for end-to-end key flows.

## 5. Backend

- **Python 3.13 + FastAPI**: Same as the demo, with the richest AI ecosystem.
- **Layers**: Routers → services → repositories. Agent tools call services only and never touch the database directly.
- **Auth**: Port the demo's email + password sessions with httpOnly cookies. Third-party sign-in (Google, LINE) is a later requirement.
- **Tooling**: uv for dependencies, ruff for linting and formatting, mypy for type checking, pytest for tests.

## 6. Agent & LLMs

### 6.1 Model roles

| Use | Model | Why |
|---|---|---|
| Conversation & orchestration (Stylist Orchestrator) | `claude-opus-5` | Needs the strongest judgment: understanding requests, composing looks, planning renders |
| Render critique (render_critique) | `claude-opus-5` | Vision accuracy matters; keeping it separate from the image model avoids a model grading its own work |
| Magazine learning, candidate cards | `claude-sonnet-5` | Lots of reading with some judgment, at lower cost |
| Bulk tagging of wardrobe and catalog | `claude-haiku-4-5` | High volume with a fixed output shape; hard samples escalate to Sonnet 5 |

Model IDs live in configuration only. Business code never names a model directly.

### 6.2 Integration: Messages API + our own loop

| Option | Verdict | Reason |
|---|---|---|
| Anthropic SDK + our own loop | **Chosen** | Our tools depend on our own database and business logic; each step's events must stream precisely to the web frontend; easy to add cost caps, auditing and eval hooks |
| Claude Agent SDK | Not chosen | Built for filesystem and coding tasks; its built-in tools don't fit this product |
| Managed Agents | Not for the main flow; evaluate for background work in M5 | Scheduled deployments suit background agents like magazine learning and brand sweeps, but the main conversation is tightly coupled to our database and SSE |
| LangChain / LangGraph | Not chosen | We don't need a cross-vendor abstraction, and another framework layer makes debugging harder |

### 6.3 Key API features we rely on

- **Adaptive thinking** (`thinking: {type: "adaptive"}`) with `effort` levels: `high` for conversation, `low` for simple tagging.
- **Streaming**: Every conversation request streams, so reasoning summaries and tool calls reach the frontend in real time.
- **Prompt caching**: The system prompt, tool definitions and the technique card index come first and stay byte-for-byte stable.
- **Structured outputs**: Tagging, looks and render plans are constrained with JSON Schema; tool definitions use `strict`.
- **Server tools**: `web_search` / `web_fetch`, limited with `allowed_domains` to brand sites and approved media domains.
- **Server-side refusal fallbacks**: Enabled per the recommended Claude Opus 5 configuration, so an individual request doesn't simply fail.

## 7. Image generation

- **Primary: Gemini 3.1 Flash Image.** Already wired into the demo. It is fast and cheap, accepts multiple reference images and edits from a previous image, which fits multi-stage rendering.
- **Compared in M3**: Gemini 3 Pro Image, OpenAI GPT Image, FLUX Kontext. Criteria: garment fidelity, model identity consistency, how well unconventional wears come out, cost and latency per image, and commercial license terms.
- **Provider interface**: Two core methods, `generate(refs, prompt)` and `edit(image, refs, prompt, mask?)`. The agent only sees the interface, never a specific model.
- **Model roster**: Each model's reference set is generated once, then kept after human selection and resemblance screening. After that it is a read-only asset.

## 8. Wardrobe ingestion: cutout & tagging

1. **No generative model for cutouts.** The demo cut out garments with an image model, which can quietly change garment details. v2 removes backgrounds with a segmentation model such as BiRefNet, so the stored image keeps the original pixels.
2. **Colors are computed.** Clustering the cutout's pixels gives hex values and shares. The LLM only names the colors (for example “heather grey”).
3. **Other attributes come from LLM vision tagging.** Haiku 4.5 with structured outputs; low-confidence fields are re-checked by Sonnet 5.
4. **Embeddings.** One embedding for the image and one for the tag text, stored in pgvector for “find similar pieces” and look retrieval.

## 9. Data & storage

- **PostgreSQL 17 + pgvector**: App data and vector search for garments and cards live in one database, which keeps transactional consistency simple.
- **Procrastinate job queue**: An async task library on PostgreSQL with retries, periodic tasks and locking. It covers multi-stage rendering, wardrobe ingestion, brand sweeps and magazine learning. If concurrency grows a lot, we'll evaluate moving to Temporal.
- **Realtime**: The worker publishes events with `LISTEN/NOTIFY`, and the API process turns them into SSE for the browser. No Redis is needed even with several API instances.
- **Object storage**: Originals, cutouts and render stage outputs. Cloudflare R2 in production (no egress fees); a filesystem adapter in local development (continuing the demo's storage abstraction).

## 10. Brand data

Japan is the launch market, so the brand catalog uses data from each brand's **Japanese site** (see Content sources).

In order of preference:

1. **Product data from official or affiliate channels** (product feeds, affiliate APIs): The most stable and the safest for compliance. Research is done before M4.
2. **Public product pages**: Following robots.txt and terms of use at a low request rate, read with `web_fetch` or our own fetcher that extracts structured data.
3. **Never**: Getting around CAPTCHAs, spoofing browser fingerprints, or defeating bot protection.

Known risk: Major brand sites are expected to have strong bot protection and heavy client-side rendering, so page fetching may be unreliable. That is why affiliate channel research starts in M0.

## 11. Hosting (to validate · M0)

| Component | Leading option | Notes |
|---|---|---|
| Web | Vercel | Native Next.js support, with a Tokyo edge region |
| API / worker | Container platform in Tokyo (Fly.io `nrt` or AWS ECS `ap-northeast-1`) | Users are in Japan, so run close to them and to the database |
| PostgreSQL | Managed service in Tokyo (Supabase or AWS RDS), with pgvector | Decided in M0 after comparing price and operations cost |
| Object storage | Cloudflare R2 | S3-compatible |
| Cutout service | On-demand GPU instances or serverless GPU | Decided in M1 based on volume |

## 12. Observability & evaluation

- **Logs**: structlog JSON output with `request_id` and `trace_id` everywhere. No secrets or private user data in logs.
- **Tracing**: OpenTelemetry across HTTP, the database and external API calls.
- **Agent trace**: Each turn's reasoning, tool inputs and outputs, tokens, cost and latency are stored in the database and viewed on an internal trace page (extended from the demo's generation log page).
- **Error monitoring**: Sentry for web and API.
- **Evals**: Datasets and eval scripts live in `evals/`. When prompts or tools change, CI runs a small smoke eval. A full eval runs at the end of each milestone.

## 13. Open validations

| Item | Milestone | How |
|---|---|---|
| Hosting platform and database provider | M0 | Compare price, latency and operations cost in Tokyo |
| Brand affiliate channels | From M0 | Research product data channels and terms in Japan, brand by brand |
| Cutout model | M1 | Compare edge quality and detail retention on 50 samples |
| Embedding model | M1 | Top-5 hit rate for similar-garment search |
| Image model | M3 | Blind review on the eval set using the criteria in section 7 |
| Moving background agents to Managed Agents | M5 | Compare operations cost and control |
