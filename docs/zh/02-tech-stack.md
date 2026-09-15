# 技术选型

> 语言：**中文** · [日本語](../ja/02-tech-stack.md) · [English](../en/02-tech-stack.md)
> 状态：草案 v0.1 · 更新：2026-09-15
> 本文记录 StyleAI v2 的技术选型结论和理由。标注「待验证」的项，会在对应里程碑用原型确认后再定稿。

## 1. 选型原则

1. **沿用 demo 已验证的部分**：FastAPI、Next.js、任务队列、SSE、Gemini 生图、登录与额度，都已在 HackathonPJT 中跑通，直接复用可以降低风险。
2. **基础设施尽量少**：M0–M6 期间只依赖 PostgreSQL 和对象存储，不引入 Redis、Kafka、Temporal 等额外组件。
3. **模型可替换**：LLM、生图模型、向量模型都通过内部接口接入，方便评测对比和更换。
4. **合规优先**：不绕过网站反爬和验证码，不保存受版权保护的原文与图片。
5. **只做 Web**：首个版本只做 Web 端，移动端通过响应式布局兼顾，不做原生 App。

## 2. 总览

| 层 | 选型 | 备选 | 状态 |
|---|---|---|---|
| 前端框架 | Next.js 16（App Router）+ React 19 + TypeScript | Remix、Vite + React | 确定 |
| UI | Tailwind CSS 4 + shadcn/ui | MUI、Chakra | 确定 |
| 前端状态 | TanStack Query（服务端状态）+ Zustand（本地 UI 状态） | SWR、Redux | 确定 |
| 国际化 | next-intl（zh-CN / ja / en） | 沿用 demo 自研 i18n | 确定 |
| 后端框架 | Python 3.13 + FastAPI + Pydantic 2 | NestJS | 确定 |
| ORM 与迁移 | SQLAlchemy 2（async）+ Alembic | SQLModel、Tortoise | 确定 |
| Agent 接入 | Anthropic Python SDK + 自建工具调用循环 | Claude Agent SDK、Managed Agents、LangGraph | 确定 |
| 主模型 | Claude Opus 5 | Claude Fable 5.1 | 确定 |
| 后台模型 | Claude Sonnet 5、Claude Haiku 4.5 | — | 确定 |
| 生图模型 | Gemini 3.1 Flash Image | Gemini 3 Pro Image、GPT Image、FLUX Kontext | 待验证（M3） |
| 抠图 | BiRefNet（自部署） | remove.bg、Photoroom API | 待验证（M1） |
| 数据库 | PostgreSQL 17 + pgvector | — | 确定 |
| 向量模型 | Voyage multimodal | Gemini Embedding、SigLIP（自部署） | 待验证（M1） |
| 任务队列 | Procrastinate（基于 PostgreSQL） | Celery + Redis、arq、Temporal | 确定 |
| 实时推送 | SSE + PostgreSQL LISTEN/NOTIFY | WebSocket、Redis Pub/Sub | 确定 |
| 对象存储 | S3 兼容（生产 Cloudflare R2），本地开发用文件系统 | AWS S3 | 确定 |
| 部署 | Web：Vercel；API / Worker：东京区域容器；数据库：东京区域托管 PostgreSQL | — | 待验证（M0） |
| 可观测性 | structlog + OpenTelemetry + Sentry + 自建 Agent trace | Langfuse | 确定 |
| 包管理 | pnpm 10（前端）、uv（后端） | npm、poetry | 确定 |

## 3. 仓库结构

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

前后端放在同一个仓库（monorepo），但各自使用自己语言的工具链，不引入 Nx、Turborepo 等跨语言构建工具。API 与 Worker 共用一套代码，以不同进程启动。

## 4. 前端

- **Next.js 16 + React 19**：demo 已使用，Server Components 适合衣橱、画廊这类以读取为主的页面。
- **shadcn/ui**：组件源码放在仓库里，可以按 StyleAI 的视觉风格自由修改，不受组件库主题限制。
- **API 类型**：用 `openapi-typescript` 从 FastAPI 的 OpenAPI 文档生成 TypeScript 类型，不手写接口类型。
- **聊天流式展示**：前端直接消费后端的 SSE 事件（见《开发规范》第 8 节）。后端 Agent 在 Python 侧，所以不使用 Vercel AI SDK 这类假设 Node 后端的方案。
- **测试**：Vitest + Testing Library（组件）、Playwright（关键流程端到端）。

## 5. 后端

- **Python 3.13 + FastAPI**：与 demo 一致，AI 相关生态也最完整。
- **分层**：路由 → 服务 → 仓储。Agent 的工具只调用服务层，不直接访问数据库。
- **登录**：移植 demo 的邮箱 + 密码、httpOnly Cookie 会话方案；第三方登录（Google、LINE）列为后续需求。
- **工具链**：uv 管理依赖，ruff 负责 lint 与格式化，mypy 做类型检查，pytest 做测试。

## 6. Agent 与 LLM

### 6.1 模型分工

| 场景 | 模型 | 理由 |
|---|---|---|
| 对话与编排（Stylist Orchestrator） | `claude-opus-5` | 需要最强的判断力：理解需求、组合方案、规划生图 |
| 效果图自检（render_critique） | `claude-opus-5` | 视觉理解要准；和生图模型分开，避免“自己给自己打分” |
| 杂志学习、候选技巧卡 | `claude-sonnet-5` | 阅读量大、需要一定判断力，成本更低 |
| 衣橱与品牌目录批量打标 | `claude-haiku-4-5` | 量大、结构固定，速度快；疑难样本升级到 Sonnet 5 |

模型 ID 统一放在配置里，业务代码不直接写模型名。

### 6.2 接入方式：Messages API + 自建工具循环

| 方案 | 结论 | 原因 |
|---|---|---|
| Anthropic SDK + 自建循环 | **采用** | 工具都依赖我们自己的数据库和业务逻辑；需要把每一步事件精确推送到 Web 前端；方便加入成本上限、审计与评测钩子 |
| Claude Agent SDK | 不采用 | 它面向文件系统和代码类任务，自带的工具我们用不上 |
| Managed Agents | 暂不采用主链路；M5 评估用于后台任务 | 定时部署适合“杂志学习”“品牌巡检”这类后台 Agent，但主对话需要和我们的数据库、SSE 紧密结合 |
| LangChain / LangGraph | 不采用 | 我们不需要跨厂商抽象，多一层框架会增加调试成本 |

### 6.3 用到的关键 API 特性

- **自适应思考**（`thinking: {type: "adaptive"}`）+ `effort` 分级：对话用 `high`，简单打标用 `low`。
- **流式输出**：所有对话请求都走 streaming，把思考摘要和工具调用实时推给前端。
- **提示缓存**：系统提示词、工具定义、技巧卡索引放在前面，并保持字节级稳定。
- **结构化输出**：打标、方案、生图计划都用 JSON Schema 约束输出；工具定义开启 `strict`。
- **服务端工具**：`web_search` / `web_fetch`，用 `allowed_domains` 限定在品牌官网与已批准的媒体域名。
- **服务端拒答回退**：按 Claude Opus 5 的推荐配置开启 fallbacks，避免个别请求直接失败。

## 7. 生图

- **主选 Gemini 3.1 Flash Image**：demo 已接入，速度快、成本低，支持多张参考图输入和基于上一张图编辑，适合多阶段生图。
- **M3 评测对比**：Gemini 3 Pro Image、OpenAI GPT Image、FLUX Kontext。评测维度：服装还原度、模特身份一致性、非常规穿法完成度、单张成本与时延、商用许可条款。
- **Provider 接口**：`generate(refs, prompt)`、`edit(image, refs, prompt, mask?)` 两个核心方法，Agent 只面向接口，不感知具体模型。
- **模特库**：模特参考图组由生图模型一次性生成，经人工筛选与相似度检查后入库，之后作为只读资产使用。

## 8. 衣橱入库：抠图与打标

1. **抠图不用生成式模型**：demo 用生图模型抠图，可能悄悄改变服装细节。v2 用 BiRefNet 这类分割模型做背景移除，保证入库图片就是原图像素。
2. **颜色用算法算**：在抠图后的像素上做聚类，得到 hex 与占比；LLM 只负责给颜色命名（如「杢グレー / 麻灰」）。
3. **其余属性用 LLM 视觉打标**：Haiku 4.5 + 结构化输出，低置信度字段升级到 Sonnet 5 复核。
4. **向量**：图片与标签文本各生成一份向量，存入 pgvector，用于“找相似单品”和方案检索。

## 9. 数据与存储

- **PostgreSQL 17 + pgvector**：业务数据、单品和技巧卡向量检索都在同一个库里，事务一致性更简单。
- **任务队列 Procrastinate**：基于 PostgreSQL 的异步任务库，支持重试、定时任务和任务锁，覆盖多阶段生图、衣橱入库、品牌巡检、杂志学习。并发量明显增长后，再评估是否迁移到 Temporal。
- **实时推送**：Worker 通过 `LISTEN/NOTIFY` 发布事件，API 进程转成 SSE 推给浏览器；多个 API 实例时也不需要 Redis。
- **对象存储**：原图、抠图、各阶段生图产物。生产用 Cloudflare R2（无出网流量费），本地开发用文件系统适配器（沿用 demo 的 storage 抽象）。

## 10. 品牌数据获取

首发市场为日本，品牌目录取各品牌**日本官网**的数据（详见《内容来源清单》）。

获取方式按优先级：

1. **官方或联盟营销渠道的商品数据**（商品 feed、联盟 API）：最稳定，也最合规。M4 前完成渠道调研。
2. **公开商品页面**：遵守 robots.txt 与网站使用条款，控制访问频率，通过 `web_fetch` 或自建抓取读取结构化数据。
3. **明确不做**：绕过验证码、伪装浏览器指纹、破解反爬。

已知风险：部分大型品牌官网预计有较强的反爬措施和大量动态渲染，页面抓取可能不稳定。所以联盟渠道调研要提前到 M0 开始。

## 11. 部署（待验证 · M0）

| 组件 | 倾向方案 | 说明 |
|---|---|---|
| Web | Vercel | Next.js 原生支持，有东京边缘节点 |
| API / Worker | 东京区域容器平台（Fly.io `nrt` 或 AWS ECS `ap-northeast-1`） | 用户在日本，靠近用户和数据库 |
| PostgreSQL | 东京区域托管服务（Supabase 或 AWS RDS），需支持 pgvector | M0 比较价格与运维成本后决定 |
| 对象存储 | Cloudflare R2 | S3 兼容 |
| 抠图服务 | GPU 按需实例或 serverless GPU | M1 根据调用量决定 |

## 12. 可观测性与评测

- **日志**：structlog 输出 JSON，全链路带 `request_id` 与 `trace_id`；日志中不写密钥和用户隐私。
- **追踪**：OpenTelemetry 覆盖 HTTP、数据库、外部 API 调用。
- **Agent trace**：每轮推理、工具入参与出参、token、成本、耗时写入数据库，通过内部 trace 页面查看（由 demo 的生成日志页扩展而来）。
- **错误监控**：Sentry（Web 与 API）。
- **评测**：`evals/` 目录保存数据集与评测脚本。改动提示词或工具时，CI 跑小规模冒烟评测；每个里程碑结束时跑完整评测。

## 13. 待验证事项

| 事项 | 里程碑 | 验证方式 |
|---|---|---|
| 部署平台与数据库托管方案 | M0 | 比较东京区域价格、延迟与运维成本 |
| 品牌联盟营销渠道 | M0 起 | 逐个品牌调研日本地区的商品数据渠道与条款 |
| 抠图模型 | M1 | 50 件样本比较边缘质量与细节保留 |
| 向量模型 | M1 | 相似单品检索的 top-5 命中率 |
| 生图模型 | M3 | 按第 7 节的维度在评测集上盲评 |
| 后台 Agent 是否迁到 Managed Agents | M5 | 比较运维成本与可控性 |
