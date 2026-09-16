# Development Guidelines

> Language: [中文](../zh/03-dev-guidelines.md) · [日本語](../ja/03-dev-guidelines.md) · **English**
> Status: Draft v0.2 · Updated: 2026-09-16
> The Chinese version is the source of truth. If versions differ, the Chinese version wins.
> Every contributor, including AI coding assistants, follows this document. Changes to the guidelines themselves also go through a PR. For module structure and data flow, see [System architecture](05-system-architecture.md).

## 1. Language policy

| Context | Language |
|---|---|
| Team communication, issue and PR discussion | Mainly Chinese |
| Documents under `docs/` | Chinese, Japanese and English. **Chinese is the source version** |
| Code comments, docstrings | English |
| Identifiers (variables, functions, classes, tables, API fields, event names) | English |
| Commit messages, PR titles | English (Conventional Commits) |
| Agent system prompts, tool descriptions, technique card bodies | English (output language follows the user) |
| Technique card terms | zh / ja / en in the `terms` field |
| UI copy | All three languages via i18n; never hardcoded in components |
| Errors returned to users | The backend returns a code and an English message; the frontend renders localized copy per code |
| Logs | English |

**Doc sync rule**: a PR that changes a Chinese document also updates the Japanese and English versions. If a translation cannot be finished in time, say so in the PR, mark the corresponding documents "in translation" at the top, and open a `docs: sync translations` issue to be resolved before the next PR.

## 2. Branches and merging

There are three long-lived branches:

| Branch | Content | Merged into `main`? |
| --- | --- | --- |
| `main` | Kept clean. During planning it holds only the repository description; code and finalized docs arrive when development starts | — |
| `draft` | Planning-stage working documents (charter, tech stack, development guidelines, content sources, system architecture, in three languages) | Once the content settles, cleaned up and merged |
| `tech-notes` | Tech notes and lab code, for learning | Never |

- `main` is protected: changes land only through PRs, squash-merged. When M0 starts, enable required CI, at least one approval, linear history and no force pushes on GitHub.
- Documents on `draft` are still under discussion: commit directly, no PR required. Once the conclusions hold, they are cleaned up and brought into `main` as finalized documents.
- `tech-notes` is a long-lived learning branch holding the tech notes and lab code. It is not part of product development and is **never merged into `main`**. To pick up the latest formal docs, merge `main` into `tech-notes`.
- Feature branches: `<type>/<short-description>`, e.g. `feat/closet-upload`, `fix/sse-reconnect`.
  - Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `exp` (experiments that may never merge).
  - Descriptions are lowercase English with hyphens, at most five words.
- One PR does one thing; aim for under 400 changed lines, excluding generated files, lockfiles and migration snapshots. Larger features are split into several PRs in dependency order.
- Merged feature branches are deleted; stale `exp/` branches are cleaned up monthly.

## 3. Commits

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```text
<type>(<scope>): <summary in imperative mood>

<optional body: what and why, wrapped at 72 columns>

<optional footer: BREAKING CHANGE: ..., Refs: #123>
```

| Part | Rule |
| --- | --- |
| `type` | `feat`, `fix`, `docs`, `refactor`, `test`, `perf`, `chore`, `build`, `ci` |
| `scope` | `web`, `api`, `agent`, `render`, `closet`, `scout`, `learn`, `knowledge`, `evals`, `infra`, `docs`, `tech-notes` |
| summary | English imperative, lowercase, no trailing period, at most 72 characters |
| body | Why the change and what it affects; the diff already says what changed |
| footer | `BREAKING CHANGE:` for incompatible changes; `Refs: #123` to link an issue |

Example:

```text
feat(closet): detect alternative wears during garment tagging

Tagging now returns wear options such as tied_waist and one_sleeve_off
based on category and closure type, so the agent can suggest them
without guessing.

Refs: #42
```

With squash merges the PR title becomes the commit summary, so PR titles follow the same rules.

## 4. Pull requests

### 4.1 Description

Use the repository template (`.github/pull_request_template.md`) and cover at least:

1. What changed and why
2. How it was verified (tests, screenshots, eval results)
3. Whether it affects prompts, tools, database schema, cost or compliance
4. Whether the docs are synced in all three languages

Unfinished work is opened as a draft.

### 4.2 Checks by type of change

| Change | The author provides | The reviewer focuses on |
| --- | --- | --- |
| API | Regenerated OpenAPI types; a note on compatibility with the deployed frontend | Field names, error codes, pagination, permission filters |
| Database schema | An Alembic migration; expected duration and locking on large tables | Forward compatibility with the previous code; index choices |
| Prompts or tools | Eval results before and after; a sample trace | Whether the tool description says when to use it; whether a fixed render prompt crept in |
| Render pipeline | Before/after images for at least 10 looks | Garment fidelity, cost impact |
| UI | Desktop and mobile screenshots; copy in three languages | Accessibility, loading and error states |
| External data fetching | A record of the robots and terms check | That only permitted fields are stored |
| Dependency upgrades | Why, plus the notable changelog entries | License, breaking changes |

### 4.3 Definition of Done

- [ ] Lint, type checks and tests pass
- [ ] New logic has tests
- [ ] Eval results attached if prompts or tools changed
- [ ] Alembic migration included if the schema changed
- [ ] New UI copy provided in all three languages
- [ ] Related docs updated in all three languages (or marked per section 1 with an issue opened)
- [ ] No secrets, user data, brand images or magazine text committed

### 4.4 Review conventions

- Reviewers give first feedback within one working day.
- Comments are either "must change" or "suggestion"; the author decides on suggestions.
- A discussion that runs past two rounds moves to a synchronous conversation, with the conclusion recorded back in the PR.

## 5. General coding principles

- **Comments explain why.** Don't restate what the code already says.
- **No dead code.** Git keeps the history.
- **Configuration lives outside code.** Environment-specific values come from environment variables, documented in `.env.example`.
- **Small functions, clear names.** Avoid vague names like `data`, `info`, `handle`, `manager`.
- **Fail loudly.** Don't swallow exceptions; raise with enough context when you can't handle it.
- **Every TODO links an issue**: `# TODO(#123): ...`.
- **Every external call has a timeout**: network requests, model calls and database queries alike.

### 5.1 Naming

| Thing | Rule | Example |
| --- | --- | --- |
| Python modules, functions, variables | snake_case | `extract_palette`, `garment_id` |
| Python classes | PascalCase | `GarmentRepository` |
| Constants | UPPER_SNAKE_CASE | `MAX_RENDER_IMAGE_CALLS` |
| Database tables | plural snake_case | `render_stages` |
| Database columns | snake_case; foreign keys `<entity>_id`; times `<verb>_at` | `outfit_id`, `reviewed_at` |
| API paths | lowercase plural, hyphenated | `/v1/garments`, `/v1/me/memories` |
| JSON fields | camelCase | `garmentId`, `createdAt` |
| Event names | `<resource>.<event>` | `render.stage`, `garment.ready` |
| Agent tools | `verb_noun` snake_case | `search_wardrobe` |
| Environment variables | `STYLEAI_` prefix + UPPER_SNAKE_CASE; third-party SDK variables keep their own names | `STYLEAI_DATABASE_URL`, `ANTHROPIC_API_KEY` |
| TypeScript files | kebab-case | `outfit-card.tsx` |
| React components | PascalCase | `OutfitCard` |
| i18n keys | Dotted path grouped by page | `closet.upload.title` |

## 6. Python backend

### 6.1 Tools and versions

- Python 3.13, dependencies managed with uv (`pyproject.toml` + `uv.lock`).
- ruff for linting and formatting (line width 100); mypy in strict mode for `app/`.
- Module dependency direction is enforced by import-linter in CI.
- pytest + pytest-asyncio for tests.

### 6.2 Layers

```text
api (routers)  ->  services  ->  repositories  ->  database
agent/tools    ->  services
pipelines      ->  services / providers
worker/tasks   ->  pipelines / services
services       ->  providers
```

| Layer | Responsible for | Never does |
| --- | --- | --- |
| `api` | Validation, authentication, calling services, shaping responses | Business logic, direct database access |
| `services` | Business rules, transaction boundaries, combining repositories | HTTP details |
| `repositories` | Database reads and writes, always filtered by user | Business decisions, returning an ORM session |
| `agent/tools` | Turning the model's tool requests into service calls and results into model-facing views | Direct database or external API access |
| `pipelines` | Orchestrating multi-step background work | Scheduling parameters |
| `providers` | External calls: retries, timeouts, usage accounting | Business rules |
| `worker` | Declaring Procrastinate tasks, queues, retries and locks | Business logic |

**Transaction boundaries live in the service layer.** One service method is one unit of work; it opens and commits the transaction. Repositories take a session and never commit on their own.

### 6.3 A worked example

The router only handles the request and the response:

```python
@router.patch("/garments/{garment_id}", response_model=GarmentOut)
async def update_garment_tags(
    garment_id: UUID,
    body: GarmentTagsPatch,
    user: CurrentUser,
    service: GarmentServiceDep,
) -> GarmentOut:
    garment = await service.update_tags(user_id=user.id, garment_id=garment_id, patch=body)
    return GarmentOut.from_domain(garment)
```

The service holds the rules and the transaction:

```python
class GarmentService:
    async def update_tags(self, *, user_id: UUID, garment_id: UUID, patch: GarmentTagsPatch) -> Garment:
        """Apply user corrections and pin corrected fields against re-tagging."""
        async with self._uow() as uow:
            garment = await uow.garments.get_for_user(garment_id, user_id=user_id)
            if garment is None:
                raise AppError("GARMENT_NOT_FOUND", "Garment does not exist.")
            # Corrected fields are pinned so a later re-tagging run cannot overwrite them.
            garment.apply_user_corrections(patch.to_changes())
            await uow.garments.save(garment)
            await uow.events.add(user_id=user_id, type="garment.updated", payload={"garmentId": str(garment_id)})
            await uow.commit()
        return garment
```

Boundary models use camelCase aliases consistently:

```python
class ApiModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")


class GarmentTagsPatch(ApiModel):
    category: GarmentCategory | None = None
    formality: int | None = Field(default=None, ge=1, le=5)
    style_tags: list[str] | None = None
```

### 6.4 Error handling

- Expected business errors raise `AppError(code, message, detail)`; a shared handler turns them into the error response in section 8.3.
- Unexpected exceptions are logged with a full stack trace and reported to Sentry; the response carries only `INTERNAL_ERROR` and a `requestId`.
- Exceptions from external services are converted in `providers` into `ProviderError` with a `retryable` flag, so callers can decide between retrying and failing.
- Don't use exceptions for normal flow: "not found" returns `None` from the repository, and the service decides whether that is an error.

### 6.5 Async and timeouts

- All IO is async; never call blocking functions on the event loop. Where a blocking library is unavoidable (image processing), use `asyncio.to_thread` or move the work to a worker.
- Every external call has a timeout: 10 seconds for database queries by default, 30 seconds for plain HTTP, configured per case for streaming model calls.
- Run concurrent tools or requests in an `asyncio.TaskGroup`, so one failure cancels the rest instead of leaving orphaned coroutines.

### 6.6 Logging

Log through structlog with structured fields, never string concatenation:

```python
log.info("render_stage_completed", render_id=str(render_id), stage_no=stage.no, latency_ms=latency_ms, cost_usd=cost)
```

Every log line carries:

| Field | Meaning |
| --- | --- |
| `request_id` | The HTTP request |
| `trace_id` | Spans API, worker and external calls |
| `user_id` | Current user, when there is one |
| `turn_id` / `render_id` / `job_id` | What is being processed, when applicable |

Never logged: secrets, cookies, passwords, the contents of user uploads or their signed URLs, or full model inputs (log length and a summary instead; the full content belongs in the access-controlled agent trace).

### 6.7 Configuration

- Configuration lives in `app/settings.py`, read from environment variables with pydantic-settings and validated at startup; a missing required value fails the boot.
- Business code receives the settings object by dependency injection and never reads `os.environ` directly.
- AI parameters (model IDs, effort, budget limits) live in configuration too, so they can differ per environment.

### 6.8 Database migrations

- Every schema change is an Alembic migration, committed with the feature.
- Migrations merged into `main` are never edited; add a new one instead.
- Tables are plural snake_case; primary keys are UUIDs (technique cards excepted); every table has timezone-aware `created_at` and `updated_at`.
- **Migrations must be forward compatible**: they run before the new code is deployed, while the old code is still serving. Dropping or renaming a column takes two releases.
- Create indexes on large tables with `CREATE INDEX CONCURRENTLY`.

## 7. TypeScript frontend

### 7.1 Directory layout

```text
apps/web/src/
├── app/                  # routes (App Router)
│   └── [locale]/         # zh-CN / ja / en
├── components/
│   ├── ui/               # shadcn/ui based primitives
│   └── <feature>/        # closet, chat, outfit, render ...
├── features/             # hooks and state per feature (queries, mutations, SSE handling)
├── lib/
│   ├── api/              # generated OpenAPI types and fetch client
│   └── sse/              # event stream client with Last-Event-ID replay
├── messages/             # zh-CN.json, ja.json, en.json
└── styles/               # design tokens
```

### 7.2 Coding rules

- `strict` is on and `any` is not allowed (use `unknown` and narrow it when truly needed).
- Server Components by default; add `"use client"` only where interaction requires it.
- Fetch server data with TanStack Query; never copy it into Zustand. When an SSE event arrives, update or invalidate the matching query cache.
- API types are generated from OpenAPI (`pnpm gen:api`) and **never hand-written**. Validate external input with zod.
- Style with Tailwind and design tokens; no inline color values.
- Every data area handles four states: loading, empty, error, ready.
- All UI copy lives in `messages/`; numbers, dates and prices go through next-intl formatters, with prices in yen.

### 7.3 Accessibility

- Interactive elements work with a keyboard and have a visible focus state.
- Images have `alt` text; garment images use a description generated from their tags, for example "grey hoodie".
- Contrast meets WCAG AA, and color information is also conveyed in text (a swatch is labeled with its color name).
- Streaming output areas use `aria-live="polite"` so screen readers are not interrupted word by word.

## 8. API design

### 8.1 Basics

- REST, with paths under `/v1` and plural resource names.
- Request and response JSON is camelCase.
- IDs are UUID strings; times are ISO 8601 in UTC, e.g. `2026-09-16T08:30:00Z`.
- Money is an integer plus a currency field, e.g. `{"amount": 5990, "currency": "JPY"}`.
- Endpoints that start long-running work return `202 Accepted` with a job or resource id.

### 8.2 Pagination and idempotency

- List endpoints use cursor pagination: `?cursor=...&limit=20` (max 100), with `nextCursor` in the response, `null` when there is no next page.
- Creation endpoints accept an `Idempotency-Key` header: the same user and key within 24 hours returns the first result.

### 8.3 Errors

```json
{ "error": { "code": "GARMENT_NOT_FOUND", "message": "Garment does not exist.", "detail": {}, "requestId": "..." } }
```

| HTTP | When | Example code |
| --- | --- | --- |
| 400 | Malformed request or parameters | `VALIDATION_FAILED` |
| 401 | Not signed in, or the session expired | `UNAUTHENTICATED` |
| 403 | Signed in but not allowed | `FORBIDDEN` |
| 404 | Does not exist, or does not belong to this user | `GARMENT_NOT_FOUND`, `OUTFIT_NOT_FOUND` |
| 409 | State conflict | `TURN_IN_PROGRESS`, `RENDER_ALREADY_RUNNING` |
| 413 | Upload too large | `UPLOAD_TOO_LARGE` |
| 422 | Well-formed but not processable | `IMAGE_NOT_A_GARMENT` |
| 429 | Rate or credit limit | `RATE_LIMITED`, `CREDITS_EXHAUSTED` |
| 503 | A dependency is temporarily unavailable | `UPSTREAM_UNAVAILABLE` |

A resource that belongs to someone else returns 404, not 403, so existence is not leaked. Error codes are defined in one place (`app/errors.py`), and the frontend renders localized copy per code.

### 8.4 SSE events

Every event has an `id` (equal to `seq`), an `event` name and JSON `data`. On reconnect the browser sends `Last-Event-ID` and the server replays what follows.

| event | Meaning | Main data fields |
|---|---|---|
| `message.delta` | Incremental reply text | `turnId`, `text` |
| `thinking.summary` | Reasoning summary | `turnId`, `text` |
| `tool.started` / `tool.finished` | A tool call starts / finishes | `turnId`, `tool`, `status` |
| `outfit.ready` | A look card is ready | `outfitId` |
| `render.stage` | A render stage produced an image | `renderId`, `stageNo`, `imageUrl` |
| `render.done` | A render job finished | `renderId`, `status` |
| `garment.ready` / `garment.needs_retake` | Ingestion finished, or the photo must be retaken | `garmentId`, `reason` |
| `error` | An error that can be shown to the user | `code`, `retryable` |
| `done` | The turn is finished | `turnId` |

Adding an event type is not a breaking change: the frontend must ignore events it does not know. Changing the fields of an existing event follows the API change process.

## 9. Agent and prompts

### 9.1 Principles

1. **No hardcoded render prompts.** Code may state principles and constraints; the actual prompts are written by the agent from the look.
2. **Prompts are code**: reviewed in PRs, with eval results attached when they change.
3. **All model calls go through `providers/`**, recording model, tokens, latency and cost in the agent trace.
4. **Model IDs appear only in configuration.**
5. **Keep prompts cache-friendly**: stable content first, with no timestamps or request IDs inside it.
6. **Cost caps** per turn and per look, with degradation and a trace entry when they are hit.
7. **Never invent products**: brand citations are verified in the service layer, not by the prompt.
8. **External content is data, not instructions**: web pages, search results and articles enter the context only as structured fields, with their source labeled.

### 9.2 Prompt files

System prompts live in `apps/api/app/agent/prompts/`, each carrying version information:

```markdown
---
id: stylist-system
version: 3
owner: agent
changed: 2026-10-02
evals: evals/reports/stylist-system-v3.md
---

You are StyleAI, a stylist who shares the user's wardrobe...
```

- Bump `version` on every change and link the eval report in `evals`.
- The trace records the prompt `id` and `version` used for each call, so quality changes can be traced to a specific edit.

### 9.3 Writing a tool

One module per tool, with an input model, a description and a run function:

```python
class SearchWardrobeInput(ToolInput):
    category: GarmentCategory
    style_tags: list[str] = []
    limit: int = Field(default=10, le=30)


SEARCH_WARDROBE = ToolSpec(
    name="search_wardrobe",
    description=(
        "Search the user's own wardrobe. "
        "Call this before recommending any piece the user already owns. "
        "Do not use it for brand catalog items; use search_catalog instead."
    ),
    input_model=SearchWardrobeInput,
)


async def run(ctx: ToolContext, args: SearchWardrobeInput) -> ToolResult:
    garments = await ctx.services.wardrobe.search(
        user_id=ctx.user_id, category=args.category, style_tags=args.style_tags, limit=args.limit
    )
    # Keep results compact: the model needs identifiers and tags, not image URLs.
    return ToolResult.ok([g.to_tool_view() for g in garments])
```

| Requirement | Detail |
| --- | --- |
| Description | Says what it does, when to use it, when not to, and how it differs from neighbouring tools |
| Input | JSON Schema with `strict` and `additionalProperties: false`; fixed sets use `enum` |
| Result size | At most ~4K tokens per result; list results are capped and say whether they were truncated |
| Errors | Return `ToolResult.error(code, message)` with a message the agent can act on |
| Permissions | Data is reached through `ctx.user_id`; tools never accept a "user id" argument the model could fabricate |
| Idempotency | Writing tools called twice with the same arguments in a turn create no duplicates |
| Tests | Each tool has unit tests: normal result, empty result, error, and user isolation |

### 9.4 Eval flow for prompt and tool changes

1. Change the prompt or tool on a branch.
2. Run the smoke eval locally (about 20 cases) and check for obvious regressions.
3. Open the PR; CI runs the smoke eval and posts the result.
4. For changes that affect look quality or rendering, run the full eval before merging and store the report in `evals/reports/`.
5. Changes that lower the score are not merged, unless the PR explains the tradeoff and the reviewer agrees.

## 10. Technique cards

- Human-curated cards are YAML files in `knowledge/cards/`, one per file named after its id (`K-0412.yaml`), reviewed in PRs.
- Candidate cards from the learning pipeline live in the database; once approved they are exported to YAML and submitted as a PR.
- IDs use the `K-0001` format, only ever increasing and never reused. Retired cards keep their file with `status: retired`.
- CI validates every card against a JSON Schema.

```yaml
id: K-0412
status: candidate          # candidate | approved | retired
title: Tonal layering
terms: { zh: 同色系深浅叠穿, ja: ワントーンの濃淡レイヤード, en: Tonal layering }
category: color            # color | layering | silhouette | texture
when_to_use: Few colors available; aiming for a polished look; fall/winter layering.
how: Pick three values of one hue and darken from base to outer layer; contrast knit, wool and leather textures.
avoid: Identical textures across all layers, which reads flat.
checks:                    # optional machine-checkable hints used by validate_outfit
  - same_hue_family: true
  - min_lightness_step: 15
tags: [color, layering]
season_scope: evergreen   # evergreen | FW26 | SS27 ...
expires_at: null
sources:
  - { outlet: "MEN'S NON-NO", title: "...", url: "...", accessed: 2026-09-01 }
confidence: 0.72
```

**Review checklist**: does the technique generalize beyond one product; are `when_to_use` and `avoid` specific; is anything copied from the source (see section 4 of Content sources); does it duplicate an existing card; are the `checks` values sensible.

## 11. Testing

| Level | Tools | Bar |
|---|---|---|
| Unit | pytest, Vitest | ≥ 80% line coverage in the service layer |
| Integration | pytest against a real PostgreSQL in Docker | Repositories, main APIs, job enqueue and execution |
| End-to-end | Playwright | Upload and ingest, get a look from chat, view the render |
| Evals | `evals/` | On prompt or tool changes (section 9.4) |

- **Unit tests never call real model APIs.** Recorded responses live in `tests/fixtures/llm/`; the recording script strips keys and user image data.
- Tests that need real APIs are marked `@pytest.mark.live` and do not run by default.
- Test names describe behavior: `test_update_tags_pins_corrected_fields`.
- Tests share no mutable state; integration tests run each case in a transaction and roll back.
- Test images are garments the team photographed, or generated images whose license clearly allows it, recorded in `tests/fixtures/LICENSES.md`.
- Eval datasets are versioned, and changes record why, so scores from different times stay comparable.

## 12. Security and compliance

This is a **public repository**, and these rules have no exceptions:

- **Never commit secrets.** They live in `.env` (git-ignored); the repo holds only `.env.example`.
- gitleaks runs as a local pre-commit hook and in CI. A leaked secret is revoked and rotated immediately, not just removed from the commit.
- Never commit user data, user uploads, brand product images or magazine text.
- Respect robots.txt and terms of use when fetching external sites. Getting around CAPTCHAs or spoofing fingerprints is prohibited.
- User uploads are private by default and reachable only by their owner; users can delete their own data.
- Dependencies are updated through Renovate or Dependabot PRs; new dependencies are checked for license and maintenance status.
- Admin endpoints are authorized separately from user endpoints, and their actions are written to an audit log.

## 13. Development environment

| Tool | Version |
|---|---|
| Node.js | 24 LTS (`.nvmrc`) |
| pnpm | 10 |
| Python | 3.13 (`.python-version`) |
| uv | Latest stable |
| Docker | Local PostgreSQL and integration tests |

- Local hooks are managed with `pre-commit`: ruff, prettier, gitleaks, commit message checks, and technique card schema validation.
- Common commands are collected into a task script at the repository root during M0 (`just dev`, `just test`, `just gen-api`) and documented in the `README`.
- Local development starts PostgreSQL with `infra/docker-compose.yml` and uses the filesystem storage adapter.

## 14. Documentation

| Directory | Content | Branch |
| --- | --- | --- |
| `docs/zh`, `docs/ja`, `docs/en` | Charter, tech stack, development guidelines, content sources, system architecture | `draft` |
| `docs/charter.html` | Visual version of the charter | `draft` |
| `docs/zh/tech-notes`, `docs/tech-notes/labs` | Tech notes and lab code | `tech-notes` |

- When a decision changes, update the document itself and its version and date at the top; do not append a changelog at the end.
- When an item marked "to validate" in the tech stack is settled, write the conclusion and the evidence (eval results, comparisons) back into that document.
- Tech notes follow the "locally complete" principle: one article answers one question and explains every concept that answer needs, and every experiment output quoted must come from an actual run.
