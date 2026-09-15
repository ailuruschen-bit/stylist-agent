# Project Charter

> Language: [中文](../zh/01-project-charter.md) · [日本語](../ja/01-project-charter.md) · **English**
> Status: Draft v0.3 · Updated: 2026-09-16 · Visual version: [charter.html](../charter.html) (open locally in a browser)
> The Chinese version is the source of truth. If versions differ, the Chinese version wins.

## 1. In one sentence

**StyleAI v2 is a stylist who shares your wardrobe.** It understands color and layering, reads every garment you upload, and looks up pieces on brand websites. It writes its own image prompts, decides how to render each look in stages, and keeps learning new techniques by reading fashion magazines.

## 2. Background

The hackathon demo ([HackathonPJT · deploy/lite-budget](https://github.com/ailuruschen-bit/HackathonPJT/tree/deploy/lite-budget)) proved the "upload a garment → avatar tries it on" pipeline, and exposed several problems:

| What the demo showed | What it means for v2 |
| --- | --- |
| A personal avatar needs a photo and body measurements: a high barrier and a privacy burden | v2 collects no body data and uses a built-in model roster |
| Try-on quality depended on long hand-written prompts, retuned for every pose and garment | In v2 the agent writes each prompt from the look itself |
| Generative cutout and try-on changed garment details, to the point where prompts had to say "never invent patterns" | v2 uses segmentation for ingestion and checks renders against the truth image |
| "Try-on" only answers "how does it look on"; it never answers "what should I wear it with" | v2 moves from try-on to styling advice |

## 3. Vision and positioning

v2 moves the focus from **try-on** to **styling**: telling people how to wear something and why it works, then proving it with a professional render.

It should feel like a stylist the user trusts: knowledgeable, honest, willing to talk it through, and familiar with every piece in their wardrobe.

### Product principles

1. **Start from what the user already owns.** Recommendations go in this order: pieces from the wardrobe → wardrobe plus a few new pieces → a whole new look. Shopping suggestions support the advice; they are not the point.
2. **Every suggestion comes with its reasoning.** Why the palette works, why the layers are arranged that way, which technique it draws on.
3. **Never judge or assume a body.** No body data is collected, no "slimming" or "hides your problem areas" language: only the relationships between garments and how to wear them.
4. **Honesty over flattery.** When a combination the user wants does not work, say why and offer a workable adjustment.
5. **Surprises need grounds.** Unconventional wears (tied at the waist, one sleeve off, jacket over the shoulders) are proposed from the garment's actual attributes, with the effect explained.

## 4. Users and scenarios

### 4.1 Personas

The launch market is Japan and the audience is 18–30. These three personas guide design and evaluation; they do not describe every user.

| Persona | Situation | Frustration | What they want from StyleAI |
| --- | --- | --- | --- |
| Shota, 20, student | Tokyo; mostly UNIQLO, GU and vintage; leans streetwear | Few clothes, always the same combinations; wants something fresh but doesn't know how | New looks from what's already there, plus the occasional affordable suggestion |
| Misaki, 26, office worker | Osaka; commutes on weekdays, goes out on weekends | No time to think in the morning; new purchases don't match the wardrobe | A look for today, fast; and a check before buying |
| Ren, 19, beginner | New to fashion, follows magazines and social media | Sees plenty of outfit photos but can't see the rules behind them | Not just the result: the reasoning, so there is something to learn |

### 4.2 Core scenarios

| # | Scenario | What the user says (example) | What the system produces |
| --- | --- | --- | --- |
| S1 | Deciding what to wear | "I'm going to Daikanyama tomorrow, casual but put-together" | One or two looks, mostly from the wardrobe, with renders |
| S2 | Building around one piece | "I always wear this grey hoodie with black pants. What else?" | Several looks around that piece, one with an unconventional wear |
| S3 | Deciding before buying | "How many outfits could I build with this ZARA jacket?" | Looks combining that product with the wardrobe, and why some pairings don't work |
| S4 | Filling a gap | "I want an outfit for an autumn date; tell me what's missing" | Wardrobe pieces plus a few brand items, with official links |
| S5 | Learning | "Why does tonal layering look expensive?" | An explanation grounded in the user's own wardrobe, with an example look |

## 5. Decisions made

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
| Branches | `main` holds product development only; learning material lives on `tech-notes` | 2026-09-16 |

## 6. Scope

**In scope**

- Long, multi-turn conversations to understand the occasion, mood and styles the user wants to try; UI and conversation in Chinese, Japanese and English
- Uploaded garment photos are cut out, analyzed, tagged and saved into a shared wardrobe; users can correct any tag
- Classic and new-season pieces from brands' Japanese sites, mixed with the user's own clothes
- Complete looks: pieces, layering, color logic, how to wear each piece, and the reasoning, citing technique cards
- Professional renders on built-in models, with multi-stage rendering and self-checks for complex looks
- Remembering preferences and dislikes the user states; users can view and delete them
- Techniques extracted from fashion magazines, added to the knowledge base after evals and human review

**Out of scope**

- Collecting or using body data
- Rendering the user themselves, or avatars built from their photos
- In-app checkout and payment (links out to brand sites only)
- Order import and e-commerce account connections
- Native mobile apps
- Prewritten prompt templates
- Social features (following, community sharing, comments)

## 7. Core capabilities

### 7.1 KNOW · Styling knowledge

**Value to the user**: looks are backed by structured expertise and come with reasons, not hunches.

- Knowledge is stored as "technique cards" covering color (color-wheel schemes, value and chroma steps, neutral ratios), layering (base / mid / outer / accent roles, alternating length, weight and fit), silhouette and proportion (H / A / V / X lines, loose over slim, waistline placement), and texture and pattern (material contrast, pattern scale, consistent formality).
- Knowledge base v1 is about 150 hand-curated cards, at least 25 in each of the four groups.
- Every look cites at least one card, and the citation can be expanded in the UI.

**Done when**: a stylist samples 30 looks and the cited cards match the look in at least 90% of them.

### 7.2 CLOSET · Wardrobe understanding

**Value to the user**: upload one photo and the garment is recorded accurately, with no forms to fill in.

- **Input**: flat-lay or hanging photos, JPEG / PNG / HEIC, up to 15 MB each.
- **Processing**: cutout → quality checks → color extraction → vision tagging → embeddings. When a check fails, the user is told exactly why (the garment isn't fully in frame, there are several garments, the photo is blurry).
- **Tag fields**: category and sub-category, primary and accent colors (hex, share, names in three languages), material, pattern, silhouette, length, formality (1–5), seasons, style tags, alternative wears.
- **Alternative wears** are derived from category and attributes: hoodies and shirts with sleeves can be tied at the waist, front-opening tops can be worn with one sleeve off or open as a layer, cardigans can be draped over the shoulders, long tees can be half-tucked.
- **Corrections**: users can edit any tag. Corrected fields are pinned against later re-tagging, and the corrections become evaluation data.

**Done when**: on a 200-garment labeled set, category, primary color, material and silhouette are at least 90% accurate, and ingestion completes in 20 seconds at P50.

### 7.3 SCOUT · Brand scouting

**Value to the user**: knowing what to buy so it works with what they own, with links that actually lead to a purchasable item.

- The five launch brands' Japanese sites are swept on a schedule; staples and new-season pieces are stored in the brand catalog.
- When catalog results are not enough during a conversation, the agent searches within brand domains and adds what it finds to the catalog.
- Recommendations may only cite catalog items that exist and are in stock; prices are shown in yen, with the official link and the fetch time.

**Done when**: at least 98% of recommended links load and are in stock at the time of recommendation.

### 7.4 COMPOSE · Outfit composition

**Value to the user**: a complete look they can wear as described.

- Looks combine the occasion and preferences from the conversation, user memory, the wardrobe, the brand catalog and the technique cards.
- A rules check confirms the palette and layering hold together before anything is saved or rendered.
- A conversation usually produces one reliable look, plus — where it fits — an "unexpected but it works" option with an explanation of why it works.

A look card contains:

| Part | Content |
| --- | --- |
| Title and occasion | For example "Daikanyama weekend · casual but sharp" |
| Pieces | Image, source (wardrobe / brand), layer role and wear style ("tied at the waist") for each piece |
| Color logic | The colors used and how they relate: "heather grey base, the navy chest logo echoing the indigo jeans" |
| Reasoning | Why it works, and the technique cards it cites |
| Alternatives | Pieces from the wardrobe that could swap in, or brand items to buy |
| Render | Stage progress while generating, then the final image |

**Done when**: stylist blind review scores expertise at 4.0 / 5 or above on average.

### 7.5 RENDER · Autonomous rendering

**Value to the user**: seeing what the look actually looks like on a model.

- The agent writes every prompt from the look. Simple looks render in one pass; complex ones (heavy layering, unconventional wears) are planned as several stages.
- Each stage appears on the look card as soon as it lands; the final image is checked for the right pieces, accurate color, whether the wear style was executed, and natural anatomy.
- Output spec: 3:4, full body in frame, soft studio light, seamless light backdrop.
- A failed render costs no credits and can be retried.

**Done when**: at least 80% of renders score 4 / 5 or above on garment fidelity; first image at P50 within 40s single-stage and 120s multi-stage.

### 7.6 LEARN · Self-improvement

**Value to the user**: advice that keeps up with the season and with what people are actually wearing.

- A background agent reads new articles from approved sources every week and drafts candidate technique cards.
- Candidates pass a copying check, deduplication, an eval regression and human review before joining the live knowledge base.
- Trend techniques carry an expiry date and lose weight automatically once the season passes.

**Done when**: eval scores hold after new cards are merged; review pass rates per source feed back into the source list.

## 8. Conversation experience

### 8.1 How the agent speaks

| Requirement | Detail |
| --- | --- |
| Language | Follows the user (Chinese, Japanese, English); Japanese uses a friendly です・ます register |
| Tone | Warm, expert, direct, like a stylist friend; no exclamation-mark or emoji clutter |
| Questions | When information is missing, ask first — one question at a time, the most important one |
| Explanations | A one-line explanation the first time a technical term appears |
| Boundaries | Never judge a body; never dismiss the user's taste, describe the effect of the combination instead |
| Uncertainty | Say so plainly, for example when a detail did not come out right in the render |

### 8.2 A sample exchange

> **User**: I'm going to Daikanyama tomorrow and want to wear my grey hoodie. No black pants this time.
>
> **StyleAI**: Got it. Let me see what's in your wardrobe that works with it. … You have indigo straight jeans and a white long-sleeve tee. The navy chest logo on the hoodie picks up the blue of the jeans nicely.
>
> Two options:
>
> **Option 1 · Safe**: white tee underneath, hoodie worn normally, indigo jeans cuffed once to show the ankle, white sneakers. It reads as "neutrals plus one blue" — clean and hard to get wrong.
>
> **Option 2 · Play with it**: tie the hoodie around your waist, wear just the white tee on top, and add your khaki work jacket. The hoodie at the waist creates a grey block that separates top from bottom, so the proportions read longer, and it has more of a street feel. It should be around 22°C tomorrow, so you can take off the jacket if it warms up, or put the hoodie on if it cools down.
>
> Renders are generating; the second one is multi-stage, so it will take a minute or two.

(This illustrates tone and structure, not literal output. The weather detail needs a weather integration, which is a later requirement.)

## 9. Model roster

- People who don't exist, generated with an image model licensed for commercial use. Each model has a reference set (front, side, three-quarter, in a plain white tee and light trousers) used as the identity reference on every render.
- Before launch, each model is screened for resemblance to real people and celebrities; the model card records the generating model, date, license terms and screening result.
- Four models at M0, twelve by M3. Men and women, across several style archetypes and a range of ethnicities.
- The agent picks a model to fit the look; the user can also choose one.

Proposed direction for the first four (open decision):

| Code | Presentation | Style archetype |
| --- | --- | --- |
| M-001 | Woman | Minimal / workwear |
| M-002 | Man | Street / sport |
| M-003 | Woman | Sweet-and-sharp / trend |
| M-004 | Man | City boy / casual |

## 10. Non-functional requirements

| Area | Requirement |
| --- | --- |
| Responsiveness | First text output within 3s at P50 after sending a message; wardrobe list loads within 1s at P95 |
| Availability | No formal SLA during the closed beta; external outages are surfaced clearly and saved data is never lost |
| Privacy | Uploads are private by default; users can delete garments, looks, memories and their account; the privacy policy states that images are processed by third-party model services |
| Internationalization | UI, conversation and tag names in Chinese, Japanese and English; prices in yen |
| Accessibility | Main flows work with a keyboard; contrast meets WCAG AA; images have alt text |
| Devices | Desktop and mobile browsers (latest two major versions of Chrome, Safari, Edge) |
| Cost | Token and render-count limits per turn and per look; the per-look cost target is set after M0 measurements |

## 11. Milestones

| Phase | Weeks | Deliverables | Done when |
|---|---|---|---|
| Preparation | — | Charter, tech stack, development guidelines, content sources and system architecture finalized | Docs reviewed and approved |
| M0 Foundation | W1–2 | Repo scaffold; agent loop skeleton; model roster v0 (4); eval set v0; research on hosting, data terms and brand data channels | One-sentence request → tool calls → one rendered look |
| M1 Wardrobe | W3–4 | Upload → cutout → tagging → saved; alternative-wear detection; tag corrections | ≥ 85% attribute accuracy on a 200-garment labeled set |
| M2 Styling brain | W5–7 | Knowledge base v1 (~150 cards); looks with reasoning; conversational persona; user memory | Stylist blind review ≥ 4 / 5 |
| M3 Render orchestration | W6–9 | Render planning, multi-stage, critique and repair; model roster v1 (12) | ≥ 80% of renders score ≥ 4 / 5 on fidelity |
| M4 Brand scouting | W9–11 | Catalogs from the five brands' Japanese sites; wardrobe + brand mixing | ≥ 98% of links valid |
| M5 Self-improvement | W11–13 | Magazine learning pipeline (P0 sources); candidate card evals and review UI | Eval scores hold after merging new cards |
| M6 Polish & beta | W13–15 | Cost and latency tuning; 30-person closed beta (users in Japan) | Save and return rates reach baseline |

## 12. Risks and compliance

| Risk | Level | Mitigation |
|---|---|---|
| Magazine copyright | High | Extract and rewrite abstract techniques only, record sources, store no text or images; copying checks; confirm subscription terms |
| Crawling brand sites and using product images | High | Prefer affiliate channels; respect robots.txt and terms; store metadata and links only; label renders as illustrations |
| Bot protection on major brand sites making data unreliable | High | Research affiliate channels from M0; replace brands we cannot access lawfully |
| Model likeness and rights to generated images | High | Commercially licensed image model; resemblance screening; record source and license |
| User images sent to third-party model services | High | Confirm each service's data terms in M0; state it in the privacy policy |
| Prompt injection from external web content | Medium | Only structured fields enter the context, never the system prompt; tool permissions limited to the current user |
| Garment fidelity loss | Medium | Segmentation keeps the original pixels; multi-stage edits checked against the truth image |
| Unconventional wears fail to render | Medium | Give each its own stage; build up render playbooks |
| Knowledge base drift or staleness | Medium | Candidate → eval → human review; trend cards expire |
| Hallucinated products | Medium | Service-layer check: only in-stock catalog items may be cited |
| Cost per look too high | Medium | Single-pass renders for simple looks; small models in the background; prompt caching; cost caps |

## 13. Success metrics (initial, recalibrated after M0)

| Metric | Definition | Target | How it is measured |
|---|---|---|---|
| Tagging accuracy | Category, primary color, material and silhouette matching the labels | ≥ 90% | 200-garment set, re-run each milestone |
| Garment fidelity | Share of renders rated ≥ 4 / 5 | ≥ 80% | 50 samples a week, scored by two reviewers independently |
| Styling expertise | Stylist blind review, 1–5 | ≥ 4.0 | 30 looks per milestone |
| Unexpected-wear uptake | Share of saved looks containing an unconventional wear | ≥ 15% | Product data |
| Brand link validity | Link loads and item is in stock when recommended | ≥ 98% | Sweep records |
| Time to first image | Single-stage P50 / multi-stage P50 | ≤ 40s / ≤ 120s | Render job records |
| Look save rate | Share of generated looks the user saves | Baseline at M6 | Product data |
| 7-day return rate | Share of users who start another conversation within 7 days | Baseline at M6 | Product data |
| Cost per look | LLM + image generation | Set after M0 | Cost recorded in traces |

## 14. Open decisions

1. **Product name**: StyleAI v2 is a working name; the repo is `stylist-agent`.
2. **Model roster**: whether the four directions in section 9 are right, and the ethnic range.
3. **Business model**: credits, brand affiliate commission, or subscription. This shapes brand partnerships and the credit design.
4. **Open-source license**: the repo is public but unlicensed (all rights reserved) until the business model is decided.

## 15. Related documents

- [Tech stack](02-tech-stack.md)
- [Development guidelines](03-dev-guidelines.md)
- [Content sources](04-content-sources.md)
- [System architecture](05-system-architecture.md)
- [Tech notes (`tech-notes` branch, Chinese)](https://github.com/ailuruschen-bit/stylist-agent/tree/tech-notes/docs/zh/tech-notes)
