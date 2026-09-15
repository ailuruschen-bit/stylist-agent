# stylist-agent

> [中文](README.md) · [日本語](README.ja.md) · **English**

**StyleAI v2** (working name): an AI stylist who shares your wardrobe.

It understands color and layering, reads every garment you upload, and looks up pieces on brand websites. It writes its own image prompts, decides how to render each look in stages, and keeps learning new techniques by reading fashion magazines.

## Status

**Planning.** There is no application code yet. We are finalizing the charter, tech stack and development guidelines, and development starts with M0 once they are approved.

## Documentation

| Document | 中文 | 日本語 | English |
|---|---|---|---|
| Project charter | [01-project-charter](docs/zh/01-project-charter.md) | [01-project-charter](docs/ja/01-project-charter.md) | [01-project-charter](docs/en/01-project-charter.md) |
| Tech stack | [02-tech-stack](docs/zh/02-tech-stack.md) | [02-tech-stack](docs/ja/02-tech-stack.md) | [02-tech-stack](docs/en/02-tech-stack.md) |
| Development guidelines | [03-dev-guidelines](docs/zh/03-dev-guidelines.md) | [03-dev-guidelines](docs/ja/03-dev-guidelines.md) | [03-dev-guidelines](docs/en/03-dev-guidelines.md) |
| Content sources | [04-content-sources](docs/zh/04-content-sources.md) | [04-content-sources](docs/ja/04-content-sources.md) | [04-content-sources](docs/en/04-content-sources.md) |

A visual, trilingual version of the charter is at [docs/charter.html](docs/charter.html). Download it and open it in a browser.

## Key decisions

- Platform: web
- Launch market: Japan, for young adults aged 18–30
- Launch brands: UNIQLO, ZARA, H&M, NIKE, adidas
- Stack: Next.js + FastAPI + PostgreSQL (pgvector); Claude Opus 5 for the agent; Gemini for image generation
- Rebuilt from the [HackathonPJT](https://github.com/ailuruschen-bit/HackathonPJT/tree/deploy/lite-budget) demo

## License

No open-source license has been granted yet. All rights reserved.
