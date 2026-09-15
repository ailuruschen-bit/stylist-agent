# stylist-agent

> **中文** · [日本語](README.ja.md) · [English](README.en.md)

**StyleAI v2**（工作名）：一位和你共用衣橱的 AI 穿搭博主。

它懂色彩与层次，读得懂你上传的每件衣服，会去品牌官网找单品，自己写提示词、自己决定怎么分阶段生成穿搭效果图，并通过阅读时尚杂志不断学到新技巧。

## 当前状态

**规划阶段**：还没有应用代码。目前在完善立项、技术选型与开发规范文档，确认后进入 M0 开发。

## 文档

| 文档 | 中文 | 日本語 | English |
|---|---|---|---|
| 立项文档 | [01-project-charter](docs/zh/01-project-charter.md) | [01-project-charter](docs/ja/01-project-charter.md) | [01-project-charter](docs/en/01-project-charter.md) |
| 技术选型 | [02-tech-stack](docs/zh/02-tech-stack.md) | [02-tech-stack](docs/ja/02-tech-stack.md) | [02-tech-stack](docs/en/02-tech-stack.md) |
| 开发规范 | [03-dev-guidelines](docs/zh/03-dev-guidelines.md) | [03-dev-guidelines](docs/ja/03-dev-guidelines.md) | [03-dev-guidelines](docs/en/03-dev-guidelines.md) |
| 内容来源清单 | [04-content-sources](docs/zh/04-content-sources.md) | [04-content-sources](docs/ja/04-content-sources.md) | [04-content-sources](docs/en/04-content-sources.md) |
| 系统架构 | [05-system-architecture](docs/zh/05-system-architecture.md) | 翻译中 | 翻译中 |

中文为源版本，日文与英文版本随后同步。立项文档另有可视化的三语版本 [docs/charter.html](docs/charter.html)，下载后用浏览器打开。

技术原理文章与实验代码（分割与生成模型、颜色提取、PostgreSQL 任务队列、Agent 接入、模型 SDK 与框架）放在学习分支 [`tech-notes`](https://github.com/ailuruschen-bit/stylist-agent/tree/tech-notes/docs/zh/tech-notes)，不属于正式开发内容。

## 关键决策

- 平台：Web
- 首发市场：日本，受众为 18–30 岁年轻人
- 首批品牌：UNIQLO、ZARA、H&M、NIKE、adidas
- 技术栈：Next.js + FastAPI + PostgreSQL（pgvector）；Agent 使用 Claude Opus 5；生图使用 Gemini
- 基于 [HackathonPJT](https://github.com/ailuruschen-bit/HackathonPJT/tree/deploy/lite-budget) 的 demo 重新构建

## 许可

暂未授权任何开源许可证，保留所有权利。
