# Project Charter

> Language: [中文](../zh/01-project-charter.md) · [日本語](../ja/01-project-charter.md) · **English**
> Status: Draft v0.2 · Updated: 2026-09-15 · Visual version: [charter.html](../charter.html) (open locally in a browser)
> The Chinese version is the source of truth. If versions differ, the Chinese version wins.

## 1. In one sentence

**StyleAI v2 is a stylist who shares your wardrobe.** It understands color and layering, reads every garment you upload, and looks up pieces on brand websites. It writes its own image prompts, decides how to render each look in stages, and keeps learning new techniques by reading fashion magazines.

## 2. Vision & positioning

The hackathon demo ([HackathonPJT · deploy/lite-budget](https://github.com/ailuruschen-bit/HackathonPJT/tree/deploy/lite-budget)) proved the “upload a garment → virtual try-on” pipeline. v2 moves the focus from **try-on** to **styling**: telling people how to wear something and why it works, then showing it on a professional model.

- **Expert**: Structured knowledge of color, layering, silhouette and proportion, and texture contrast. Every look comes with its reasoning.
- **Playful**: Beyond safe picks, it suggests street-style moves like a hoodie tied at the waist, one sleeve off, or a jacket draped over the shoulders.
- **Autonomous**: The agent decides the prompts, the render steps and the brand searches. No prewritten templates.
- **Always learning**: It keeps reading fashion content and adds new techniques to its knowledge base.

## 3. Decisions made

| Topic | Decision | Date |
|---|---|---|
| Platform | Web only (responsive, so it also works in mobile browsers) | 2026-09-15 |
| Launch market | Japan | 2026-09-15 |
| Audience | Young adults aged 18–30 | 2026-09-15 |
| Launch brands | UNIQLO, ZARA, H&M, NIKE, adidas (Japanese sites) | 2026-09-15 |
| Magazine sources | First-batch proposal in [Content sources](04-content-sources.md) | 2026-09-15 |
| Body data | Not collected, not used | 2026-09-15 |
| Repository | Public GitHub repo `stylist-agent`, no open-source license for now | 2026-09-15 |
| Language policy | Team communication mainly in Chinese; docs in Chinese, Japanese and English; code comments in English | 2026-09-15 |

## 4. Scope

**In scope**

- Long, multi-turn conversations to understand the occasion, mood and styles the user wants to try
- Uploaded garments are analyzed, tagged and saved into a shared wardrobe
- Classic and new-season pieces from brands' Japanese sites, mixed with the user's own clothes
- Complete looks: pieces, layering, color logic, how to wear each piece, and why it works
- Professional renders on built-in models, with multi-stage rendering for complex looks
- Techniques extracted from fashion magazines and added to the knowledge base after review

**Out of scope**

- Collecting or using body data
- Rendering the user themselves, or avatars built from their photos
- In-app checkout and payment (links out to brand sites only)
- Order import and e-commerce account connections
- Native mobile apps
- Prewritten prompt templates

## 5. From demo to v2

| Demo component | Role in v2 | Decision |
|---|---|---|
| Job queue & worker | Same idea, reimplemented with Procrastinate; adds render pipeline and ingestion jobs | Upgrade |
| SSE progress updates | Becomes the agent event stream | Upgrade |
| NanoBanana adapter + self-check | Split into `render_stage` and `render_critique` tools; the agent writes the prompts | Upgrade |
| Generative cutout | Replaced by a segmentation model so garment details don't change | Replace |
| Generation log debug page | Extended into a full agent trace | Upgrade |
| Login, credits, admin, trilingual i18n | Carried over | Keep |
| Avatars, pose library, body measurements, order import, hardcoded prompts | No longer needed | Remove |

## 6. Core capabilities

| Code | Capability | Key points |
|---|---|---|
| KNOW | Styling knowledge | Color, layering, silhouette and proportion, texture and pattern; stored as searchable, citable “technique cards” |
| CLOSET | Wardrobe understanding | Cutout, tagging (color hex + share, material, silhouette, formality, etc.), and alternative wears (tied at the waist, one sleeve off, etc.) |
| SCOUT | Brand scouting | Finds staples and new-season pieces on brands' Japanese sites and caches them in a catalog; looks may only cite real catalog items |
| COMPOSE | Outfit composition | Combines the conversation, wardrobe, catalog and technique cards; rules check before rendering; a reliable look plus an unexpected one that works |
| RENDER | Autonomous rendering | The agent writes each prompt; complex looks are planned in stages with edits and self-checks |
| LEARN | Self-improvement | A background agent reads magazines and writes candidate cards; merged after evals and human review |

## 7. Multi-stage rendering

1. **Plan**: Judge complexity and write a structured render plan (stages, reference images, details that must stay faithful, what to check).
2. **Base look**: Model reference + base layer and bottoms. Color, print and cut accuracy come first.
3. **Layering**: Edit the previous result to add outer layers.
4. **Unconventional wears & details**: Waist tie, one sleeve off, half-tuck, rolled sleeves, accessories, one local edit at a time.
5. **Critique & repair** (loop): Check against the plan; on a failure, re-run the relevant stage or patch locally, up to a retry cap.

Simple looks render in one pass and then get critiqued.

## 8. Model roster

- People who don't exist, generated with an image model licensed for commercial use. Each model has a reference set that keeps them consistent across renders.
- Before launch, each model is screened for resemblance to real people and celebrities, and the generating model, date and license terms are recorded.
- Men and women across several style archetypes and ethnicities. The agent picks one to fit the look, and users can choose one themselves.
- One output spec: soft studio light, seamless backdrop, full body in frame, 3:4.

## 9. Milestones

| Phase | Weeks | Deliverables | Done when |
|---|---|---|---|
| M0 Foundation | W1–2 | Repo scaffold; agent loop skeleton; model roster v0 (4 models); eval set v0; research on hosting and brand data channels | One-sentence request → tool calls → one rendered look |
| M1 Wardrobe | W3–4 | Upload → cutout → tagging → saved; alternative-wear detection | ≥ 85% attribute accuracy on a 200-garment labeled set |
| M2 Styling brain | W5–7 | Knowledge base v1 (~150 cards); looks with reasoning; conversational persona | Stylist blind review scores expertise ≥ 4 / 5 |
| M3 Render orchestration | W6–9 | Render planning, multi-stage, critique and repair; model roster v1 (12 models) | ≥ 80% of renders score ≥ 4 / 5 on garment fidelity |
| M4 Brand scouting | W9–11 | Catalogs from the 5 brands' Japanese sites; wardrobe + brand mixing | ≥ 98% of recommended links valid |
| M5 Self-improvement | W11–13 | Magazine learning pipeline (P0 sources); candidate card evals and review | Eval scores hold after new cards are merged |
| M6 Polish & beta | W13–15 | Cost and latency tuning; 30-person closed beta (users in Japan) | Save and return rates reach baseline |

Before development: finalize this charter, the tech stack, the development guidelines and the content sources, then start M0 once they are approved.

## 10. Risks & compliance

| Risk | Level | Mitigation |
|---|---|---|
| Magazine copyright | High | Extract and rewrite abstract techniques only, record the source, store no text or images; check subscription service terms |
| Crawling brand sites and using product images | High | Prefer affiliate channels; respect robots.txt and terms; store metadata and links only; label renders as illustrations |
| Unstable data due to bot protection on major brand sites | High | Research affiliate channels starting in M0; no attempts to get around bot protection |
| Model likeness and rights to generated images | High | Commercially licensed image model; resemblance screening; record source and license |
| Garment fidelity loss | Medium | Segmentation keeps the original pixels; multi-stage edits + vision critique |
| Unconventional wears fail to render | Medium | Give each its own stage; build up render playbook cards |
| Knowledge base drifts or goes stale | Medium | Candidate → eval → human review; trend cards expire |
| Hallucinated products | Medium | Cite catalog items only; links re-checked on a schedule |
| Cost per look too high | Medium | Single-pass renders for simple looks; small models for background work; prompt caching; a cost cap per look |

## 11. Success metrics (initial, recalibrated after M0)

| Metric | Definition | Target |
|---|---|---|
| Tagging accuracy | Category, color, material, silhouette on the labeled set | ≥ 90% |
| Garment fidelity | Share of renders rated ≥ 4 / 5 by reviewers | ≥ 80% |
| Styling expertise | Stylist blind review, 1–5 | ≥ 4.0 |
| Unexpected-wear uptake | Share of saved looks that include an unconventional wear | ≥ 15% |
| Brand link validity | Link loads and item is in stock when recommended | ≥ 98% |
| Time to first image | Single-stage P50 / multi-stage P50 | ≤ 40s / ≤ 120s |
| Cost per look | LLM + image generation | Set after M0 |

## 12. Open decisions

1. **Product name**: StyleAI v2 is a working name; the repo is `stylist-agent`.
2. **Model roster**: Gender balance, style archetypes, ethnic range, and personas for the first four models.
3. **Business model**: Credits, brand affiliate commission, or subscription. This shapes how we partner with brands.
4. **Open-source license**: The repo is public but unlicensed (all rights reserved) until the business model is decided.

## 13. Related documents

- [Tech stack](02-tech-stack.md)
- [Development guidelines](03-dev-guidelines.md)
- [Content sources](04-content-sources.md)
