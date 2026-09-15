# Development Guidelines

> Language: [中文](../zh/03-dev-guidelines.md) · [日本語](../ja/03-dev-guidelines.md) · **English**
> Status: Draft v0.1 · Updated: 2026-09-15
> The Chinese version is the source of truth. If versions differ, the Chinese version wins.
> Every contributor, including AI coding assistants, follows this document. Changes to the guidelines themselves also go through a PR discussion before merging.

## 1. Language policy

| Context | Language |
|---|---|
| Team communication, issue and PR discussion | Mainly Chinese |
| Documents under `docs/` | Chinese, Japanese and English. **Chinese is the source version** |
| Code comments, docstrings | English |
| Identifiers (variables, functions, classes, tables, API fields) | English |
| Commit messages, PR titles | English (Conventional Commits) |
| Agent system prompts, tool descriptions | English (output language follows the user) |
| Knowledge base technique cards | English body, with zh / ja / en terms |
| UI copy | All three languages via i18n; never hardcoded in components |

**Doc sync rule**: A PR that changes a Chinese document also updates the Japanese and English versions. If translation can't be finished in time, say so in the PR and open a `docs: sync translations` issue, to be resolved before the next PR.

## 2. Branches & merging

- `main` is protected. Changes land only through PRs, using squash merge.
- Branch names: `<type>/<short-description>`, e.g. `feat/closet-upload`, `fix/sse-reconnect`.
  - Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `exp` (experiments that may never merge).
- One PR does one thing. Aim for under 400 changed lines, excluding generated files, lockfiles and migration snapshots.
- Merge requirements: all CI checks pass and at least one review. While there is a single developer, self-review is allowed, but walk through every item in the PR template.

## 3. Commits

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```text
<type>(<scope>): <summary in imperative mood>

<optional body: what and why>
```

- `type`: `feat`, `fix`, `docs`, `refactor`, `test`, `perf`, `chore`, `build`, `ci`
- `scope`: `web`, `api`, `agent`, `render`, `closet`, `scout`, `knowledge`, `evals`, `infra`, `docs`
- Examples:
  - `feat(closet): detect alternative wears during garment tagging`
  - `fix(render): retry stage when critique flags color mismatch`
  - `docs: add tech stack decision for task queue`

## 4. Pull requests

Use the repo template (`.github/pull_request_template.md`). At minimum, cover:

1. What changed and why
2. How it was verified (tests, screenshots, eval results)
3. Whether it affects prompts, tools, database schema, cost or compliance
4. Whether the docs are synced in all three languages

**Definition of Done**

- [ ] Lint, type check and tests pass
- [ ] New logic has tests
- [ ] Eval results attached if prompts or tools changed
- [ ] Alembic migration included if the schema changed
- [ ] New UI copy provided in all three languages
- [ ] Related docs updated (all three languages)
- [ ] No secrets, user data, brand images or magazine text committed

## 5. General coding principles

- **Comments explain why.** Don't restate what the code already says.
- **No dead code.** Delete unused code; git keeps the history.
- **Configuration lives outside code.** Environment-specific values come from environment variables and are listed in `.env.example`.
- **Small functions, clear names.** A name should say what something is for. Avoid vague names like `data`, `info` or `handle`.
- **Fail loudly.** Don't swallow exceptions. Errors you can't handle are raised with enough context.
- **Every TODO links an issue**: `# TODO(#123): ...`.

## 6. Python backend

### 6.1 Tools & versions

- Python 3.13, dependencies managed with uv (`pyproject.toml` + `uv.lock`).
- ruff for linting and formatting; mypy in strict mode for `app/`.
- pytest + pytest-asyncio for tests.

### 6.2 Layers

```text
api (routers)  ->  services  ->  repositories  ->  database
agent/tools    ->  services
worker/tasks   ->  services
```

- **Routers** validate input, authenticate, call services and shape responses. No business logic.
- **Services** hold business logic and are the only place that combines several repositories.
- **Repositories** only read and write the database and return domain objects, never an ORM session.
- **Agent tools** call services. They never access the database directly or call external model APIs directly (they go through `providers/`).

### 6.3 Coding rules

- Every function signature has type hints; public functions have English docstrings.
- Every boundary (requests, responses, tool inputs, LLM structured outputs) uses Pydantic models.
- External JSON is camelCase: Pydantic models set `alias_generator=to_camel`, while Python code stays snake_case.
- All IO is async. Never call blocking functions inside the event loop.
- Business errors raise `AppError(code, message, detail)`, and a shared exception handler turns them into HTTP responses.
- Log with structlog using structured fields, not string concatenation. Never log secrets, cookies or the contents of user-uploaded images.

```python
async def tag_garment(garment_id: UUID, *, repo: GarmentRepository) -> GarmentTags:
    """Tag a garment from its cutout image and persist the result."""
    garment = await repo.get(garment_id)
    # Colors come from pixel clustering, not the LLM, so hex values stay exact.
    palette = extract_palette(garment.cutout_path)
    tags = await vision_tagger.tag(garment.cutout_path, palette=palette)
    await repo.save_tags(garment_id, tags)
    return tags
```

### 6.4 Database migrations

- Every schema change is an Alembic migration, committed in the same PR as the feature.
- Never edit a migration that has been merged into `main`; add a new one instead.
- Table names are plural snake_case (`garments`, `knowledge_cards`). Primary keys are UUIDs. Every table has timezone-aware `created_at` and `updated_at`.

## 7. TypeScript frontend

- `strict` is on and `any` is not allowed (use `unknown` and narrow it when truly needed).
- Server Components by default. Add `"use client"` only where interaction requires it.
- Fetch server data with TanStack Query. Don't copy server data into Zustand.
- API types are generated from OpenAPI (`pnpm gen:api`). **Never hand-write them.** Validate external input with zod.
- File names are kebab-case (`outfit-card.tsx`); components are PascalCase (`OutfitCard`).
- Style with Tailwind and design tokens. No inline color values.
- All UI copy lives in `messages/{zh-CN,ja,en}.json`, with keys grouped by page, e.g. `closet.upload.title`.
- Accessibility: interactive elements work with a keyboard, images have `alt` text, and color contrast meets WCAG AA.
- ESLint (`eslint-config-next`) + Prettier for consistent formatting.

## 8. API design

- REST, with paths under `/v1` and plural resource names: `/v1/garments`, `/v1/outfits/{id}`.
- Request and response JSON is camelCase.
- One error format everywhere:

```json
{ "error": { "code": "GARMENT_NOT_FOUND", "message": "Garment does not exist.", "detail": {} } }
```

- List endpoints use cursor pagination: `?cursor=...&limit=20`, with `nextCursor` in the response.
- Endpoints that start long-running jobs (upload ingestion, rendering) accept an `Idempotency-Key` header.
- **SSE events**: Each event has an `event` name and JSON `data`. `data` carries an increasing `seq` so missed events can be replayed after a reconnect.

| event | Meaning |
|---|---|
| `message.delta` | Incremental text of the agent's reply |
| `thinking.summary` | Reasoning summary |
| `tool.started` / `tool.finished` | A tool call starts / finishes |
| `render.stage` | A render stage produced an image |
| `outfit.ready` | A look card is ready |
| `error` | An error that can be shown to the user |
| `done` | The turn is finished |

## 9. Agent & prompts

1. **No hardcoded image prompts.** Code may state principles and constraints (e.g. “garment color follows the reference image”). The actual render prompts are written by the agent from the look.
2. **Prompts are code.** System prompts live in `apps/api/app/agent/prompts/*.md`, go through PR review, and changes come with eval results.
3. **Tool design**:
   - One tool, one job. Names are `verb_noun` snake_case (e.g. `search_wardrobe`).
   - Input JSON Schemas use `strict` with `additionalProperties: false`.
   - Descriptions say when to use the tool and when not to.
   - Results are compact and structured. Never send whole HTML pages or large raw payloads back to the model.
   - On failure, return `is_error` with a message the agent can act on, instead of throwing and ending the conversation.
4. **All model calls go through `providers/`.** Each call records the model, tokens, latency and cost in the agent trace.
5. **Model IDs appear only in configuration.** Business code never names a model.
6. **Cache-friendly prompts.** Stable content (system prompt, tool definitions) comes first, with no timestamps, request IDs or other changing values inside it.
7. **Cost caps.** Every turn and every look has token and render-count limits. When a limit is hit, degrade (e.g. switch to single-stage rendering) and record it in the trace.
8. **Never invent products.** Brand recommendations may only cite items that exist in the brand catalog.

## 10. Technique cards

- Human-curated technique cards are YAML files in `knowledge/cards/`, one card per file, reviewed via PR.
- Candidate cards from the learning pipeline live in the database. Once approved, they are exported to YAML and submitted as a PR.
- IDs use the `K-0001` format. Numbers only go up and are never reused.

```yaml
id: K-0412
status: candidate          # candidate | approved | retired
title: Tonal layering
terms: { zh: 同色系深浅叠穿, ja: ワントーンの濃淡レイヤード, en: Tonal layering }
when_to_use: Few colors available; aiming for a polished look; fall/winter layering.
how: Pick three values of one hue and darken from base to outer layer; contrast knit, wool and leather textures.
avoid: Identical textures across all layers, which reads flat.
tags: [color, layering]
season_scope: evergreen   # evergreen | FW26 | SS27 ...
expires_at: null
sources:
  - { outlet: "MEN'S NON-NO", title: "...", url: "...", accessed: 2026-09-01 }
confidence: 0.72
```

- Cards must not contain copied passages (see section 4 of Content sources).

## 11. Testing

| Level | Tools | Bar |
|---|---|---|
| Unit | pytest, Vitest | ≥ 80% line coverage in the service layer |
| Integration | pytest (real PostgreSQL via Docker) | Covers repositories and main APIs |
| End-to-end | Playwright | The three main flows: upload & ingest, get a look from chat, view the render |
| Evals | `evals/` | Run when prompts or tools change (see section 12 of Tech stack) |

- **Unit tests never call real model APIs.** Use recorded responses as fixtures.
- Tests that need real APIs are marked `@pytest.mark.live`. They don't run by default and must be enabled explicitly.
- Test images are only garments the team photographed, or generated images whose license clearly allows it, with the source recorded in `fixtures/LICENSES.md`.

## 12. Security & compliance

This is a **public repository**. These rules have no exceptions:

- **Never commit secrets.** Secrets go in `.env` (ignored); the repo only holds `.env.example`.
- gitleaks runs both as a local pre-commit hook and in CI. If a secret is ever committed, revoke and rotate it immediately. Deleting the commit is not enough.
- Never commit user data, user uploads, brand product images or magazine text.
- When accessing external sites, respect robots.txt and terms of use. Getting around CAPTCHAs, spoofing fingerprints or any other anti-bot evasion is prohibited.
- User uploads are private by default and visible only to their owner. Users can delete their own data.

## 13. Development environment

| Tool | Version |
|---|---|
| Node.js | 24 LTS (`.nvmrc`) |
| pnpm | 10 |
| Python | 3.13 (`.python-version`) |
| uv | Latest stable |
| Docker | For local PostgreSQL and integration tests |

- Local hooks are managed with `pre-commit`: ruff, prettier, gitleaks, and a commit message format check.
- Local setup instructions will be added to the `README` after M0.
