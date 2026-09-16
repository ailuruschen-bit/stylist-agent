# 技术选型

> 语言：中文（摸索阶段只维护中文版；日文、英文旧稿见 [docs/archive](../archive/)，正式开发开始时重新翻译）
> 状态：草案 v0.2 · 更新：2026-09-16
> 本文记录 StyleAI v2 的技术选型结论和理由。标注“待验证”的项，会在对应里程碑用原型确认后再定稿。各项技术的工作原理，见 `tech-notes` 分支的[技术原理](https://github.com/ailuruschen-bit/stylist-agent/tree/tech-notes/docs/zh/tech-notes)系列文章；系统如何组合这些技术，见[《系统架构》](05-system-architecture.md)。
> 文中的模型 ID 与库版本核对于 2026 年 9 月。

## 1. 选型原则

1. **沿用 demo 已验证的部分**：FastAPI、Next.js、任务化处理、SSE、Gemini 生图、登录与额度，都已在 HackathonPJT 中跑通。
2. **基础设施尽量少**：M0–M6 期间只依赖 PostgreSQL 和对象存储，不引入 Redis、Kafka、Temporal 等组件。
3. **模型可替换**：LLM、生图、分割、向量模型都通过内部 provider 接口接入，方便评测对比和更换。
4. **离 API 越近越好**：模型能力更新很快，优先直接使用厂商官方 SDK，不在中间增加抽象框架。
5. **合规优先**：不绕过网站反爬和验证码，不保存受版权保护的原文与图片。
6. **只做 Web**：手机通过响应式布局兼顾，不做原生 App。

## 2. 总览

| 层 | 选型 | 备选 | 状态 |
|---|---|---|---|
| 前端框架 | Next.js 16（App Router）+ React 19 + TypeScript | Remix、Vite + React | 确定 |
| UI | Tailwind CSS 4 + shadcn/ui | MUI、Chakra | 确定 |
| 前端数据 | TanStack Query（服务端状态）+ Zustand（本地 UI 状态） | SWR、Redux | 确定 |
| 国际化 | next-intl（zh-CN / ja / en） | 沿用 demo 自研 i18n | 确定 |
| 后端框架 | Python 3.13 + FastAPI + Pydantic 2 | NestJS | 确定 |
| ORM 与迁移 | SQLAlchemy 2（async）+ Alembic，驱动 psycopg 3 | SQLModel | 确定 |
| Agent 接入 | Anthropic Python SDK，手写工具调用循环 | SDK Tool Runner、LangGraph、Google ADK | 确定；Tool Runner 在 M0 对比 |
| 对话与编排模型 | `claude-opus-5` | `claude-fable-5-1` | 确定 |
| 后台模型 | `claude-sonnet-5`、`claude-haiku-4-5` | — | 确定 |
| 生图模型 | `gemini-3.1-flash-image`（Nano Banana 2） | `gemini-3-pro-image`（Nano Banana Pro）、GPT Image、FLUX.1 Kontext | 待验证（M3） |
| 生图 SDK | Google Gen AI SDK（`google-genai`） | — | 确定；Interactions API 与 generateContent 在 M0 选定 |
| 抠图 | BiRefNet（自部署） | BiRefNet 其他变体、商用背景移除 API | 待验证（M1） |
| 向量模型 | `voyage-multimodal-3.5` | Gemini Embedding、SigLIP（自部署） | 待验证（M1） |
| 数据库 | PostgreSQL 17 + pgvector | — | 确定 |
| 任务队列 | Procrastinate 3.x（基于 PostgreSQL） | Celery + Redis、arq、Temporal | 确定 |
| 实时推送 | SSE + 事件表 + PostgreSQL LISTEN/NOTIFY | WebSocket、Redis Pub/Sub | 确定 |
| 对象存储 | S3 兼容：生产 Cloudflare R2，本地文件系统 | AWS S3 | 确定 |
| 部署 | Web：Vercel；API / Worker：东京区域容器；数据库：东京区域托管 PostgreSQL | — | 待验证（M0） |
| 可观测性 | structlog + OpenTelemetry + Sentry + 自建 Agent trace | Langfuse | 确定 |
| 包管理 | pnpm 10（前端）、uv（后端） | npm、poetry | 确定 |

## 3. 仓库结构

```text
stylist-agent/
├── apps/
│   ├── web/                 # Next.js frontend
│   └── api/                 # FastAPI app, agent, pipelines, worker (same codebase, separate processes)
│       ├── app/             # see "System architecture" section 4 for the package layout
│       ├── migrations/      # Alembic
│       └── tests/
├── services/
│   └── segmentation/        # BiRefNet inference service (GPU), deployed separately
├── knowledge/               # human-curated technique cards (YAML), reviewed via PR
├── evals/                   # datasets and eval runners
├── infra/                   # docker compose, deployment configs
└── docs/                    # zh / ja / en documentation
```

前后端放在同一个仓库，各自使用自己语言的工具链，不引入 Nx、Turborepo 等跨语言构建工具。API 与 Worker 共用一套代码，以不同进程启动；分割服务依赖 GPU 和较大的模型权重，单独部署。

## 4. 前端

| 选择 | 理由 | 注意事项 |
| --- | --- | --- |
| Next.js 16 + React 19 | demo 已使用；Server Components 适合衣橱、方案列表这类读取为主的页面 | 对话页面是强交互页面，整体作为客户端组件实现 |
| Tailwind CSS 4 + shadcn/ui | 组件源码在仓库里，可按 StyleAI 视觉风格修改 | 设计令牌统一定义，组件中不写颜色值 |
| TanStack Query | 服务端数据的缓存、重新获取、乐观更新 | SSE 事件到达时更新对应查询的缓存 |
| Zustand | 对话输入框、面板展开等本地状态 | 不存放服务端数据 |
| next-intl | 三语文案、日期与货币格式 | 价格统一以日元显示 |
| openapi-typescript | 从后端 OpenAPI 生成类型，前后端契约一致 | 生成物提交到仓库，CI 检查是否过期 |

**SSE 客户端**：浏览器原生 `EventSource` 只支持 GET 且不能设置自定义请求头。StyleAI 的事件流接口是 GET，并通过 Cookie 认证，可以直接使用 `EventSource`；重连时浏览器会自动带上 `Last-Event-ID`。

**测试**：Vitest + Testing Library（组件），Playwright（上传入库、对话出方案、查看效果图三条主流程）。

## 5. 后端

| 选择 | 理由 |
| --- | --- |
| Python 3.13 + FastAPI | 与 demo 一致；AI 相关 SDK 与图像处理生态最完整；原生支持 async 和 OpenAPI |
| Pydantic 2 | 请求响应、工具入参、结构化输出共用同一套模型定义 |
| SQLAlchemy 2 async + psycopg 3 | psycopg 3 同时支持 async、LISTEN/NOTIFY，并且是 Procrastinate 的连接器，全栈使用同一个驱动 |
| Alembic | 数据库结构变更有版本、可回溯 |
| uv | 依赖解析与安装速度快，锁文件可复现 |
| ruff + mypy | 格式、lint、类型检查 |

**登录**：移植 demo 的邮箱密码与会话 Cookie 方案。第三方登录（Google、LINE）列为后续需求。

## 6. Agent 与 LLM

### 6.1 模型分工

| 场景 | 模型 | effort | 理由 |
|---|---|---|---|
| 对话与编排 | `claude-opus-5` | high | 理解需求、组合方案、决定工具调用，需要最强的判断力 |
| 生图规划、效果图检查 | `claude-opus-5` | high | 视觉理解要准；检查模型与生图模型不同，避免自己检查自己 |
| 杂志学习、打标复核 | `claude-sonnet-5` | medium | 阅读量大，需要一定判断力，成本更低 |
| 衣橱与品牌目录批量打标 | `claude-haiku-4-5` | — | 数量多、输出结构固定，速度快 |

模型 ID 和 effort 统一放在配置中。effort 的初始值在 M0 用评测集校准。

### 6.2 接入方式

| 方案 | 结论 | 原因 |
|---|---|---|
| Anthropic SDK + 手写循环 | **采用** | 循环本身很短；每个内容块都要落库并转换为 SSE 事件；需要在每一圈之间检查预算；同时使用服务端工具时需要处理 `pause_turn` |
| Anthropic SDK Tool Runner | M0 对比 | 能减少样板代码；Python 版本目前不会自动续上 `pause_turn`，需要确认能否满足事件与预算的插入点 |
| Claude Agent SDK | 不采用 | 面向文件系统和代码任务，内置工具与本产品无关 |
| Managed Agents | 主对话不采用；M5 评估用于后台学习与巡检 | 定时部署适合后台 Agent；主对话与数据库、SSE 紧密结合 |
| LangGraph / Google ADK | 不采用 | 主对话流程简单；需要暂停恢复的长流程已由任务队列承担；多一层抽象会延迟使用 Claude 新能力 |
| Spring AI | 不适用 | Java 框架，StyleAI 后端为 Python |

各方案的原理与差别，见技术原理《拆解 Agent 接入》《模型 SDK 与 Agent 框架》。

### 6.3 使用的 API 能力

| 能力 | 用途 |
| --- | --- |
| 自适应思考 + effort | 对话与规划启用；按场景设置 effort |
| 流式输出 | 所有对话请求；转换为 StyleAI 自己的 SSE 事件 |
| 提示缓存 | 工具定义、系统提示词、技巧卡索引放在前部并保持稳定 |
| 结构化输出 | 打标结果、方案卡片、生图计划、检查结果 |
| `strict` 工具定义 | 所有自定义工具 |
| 服务端工具 `web_search` / `web_fetch` | 品牌检索（`allowed_domains` 限定品牌官网）、杂志学习（限定已批准来源） |
| 服务端压缩 | 长对话自动总结较早的历史 |
| 服务端拒答回退 | 按 Claude Opus 5 的推荐配置开启 |

## 7. 生图

### 7.1 模型

Gemini 当前的图像模型（均为正式版）：

| 模型 ID | 名称 | 参考图上限 | 输出分辨率 |
| --- | --- | --- | --- |
| `gemini-3.1-flash-image` | Nano Banana 2 | 物体 10 + 人物 4 + 风格 3 | 1K、2K、4K |
| `gemini-3-pro-image` | Nano Banana Pro | 物体 6 + 人物 5 | 1K、2K、4K |
| `gemini-3.1-flash-lite-image` | Nano Banana 2 Lite | 物体 14 | 0.5K、1K |

主选 `gemini-3.1-flash-image`：参考图容量能覆盖“模特参考 + 多件服装”的组合，支持 3:4 画幅，速度与成本适合多阶段生成。所有输出图片带 SynthID 隐形水印。

M3 在评测集上盲评对比 `gemini-3-pro-image`、OpenAI GPT Image、FLUX.1 Kontext。评测维度：服装还原度（与真值图对比）、模特身份一致性、非常规穿法完成度、多轮编辑后的一致性、单张成本与耗时、商用许可条款。

### 7.2 API 形式

Gemini API 目前有两种调用方式：Google 推荐的新 Interactions API（交互默认保存在服务端，通过 `previous_interaction_id` 继续），以及仍被完整支持的 `generateContent`。M0 选定一种，需要确认的点：

- 服务端保存交互对用户图片隐私的影响，以及关闭保存后多轮编辑的写法；
- 多阶段生图中“以上一阶段输出为输入”的两种实现方式在成本与一致性上的差别。

### 7.3 Provider 接口

```python
class ImageProvider(Protocol):
    async def generate(self, refs: list[ImageRef], prompt: str, spec: OutputSpec) -> ImageResult: ...
    async def edit(self, image: ImageRef, refs: list[ImageRef], prompt: str, spec: OutputSpec) -> ImageResult: ...
```

`ImageResult` 包含图片、模型、耗时、计费用量。生图流水线只依赖这个接口。

## 8. 衣橱入库：抠图、颜色、打标

**抠图用分割模型，不用生成模型。** 生成模型的输出像素是重新画出来的，纹理、印花、文字会悄悄变化；分割模型只决定保留哪些原始像素。入库需要一张可信的真值图，作为颜色提取、打标和效果图检查的基准。

| 候选 | 说明 | 许可 |
| --- | --- | --- |
| BiRefNet（general / HR / matting / lite 等变体） | 高分辨率二分图像分割，边缘细节好，可输出 alpha matte | MIT |
| 商用背景移除 API | 无需部署 GPU | 按服务条款与计费 |

M1 用 50 件真实衣服照片比较边缘质量、细节保留、耗时，并确认所选权重的许可条款。

**颜色用算法计算**：只统计衣服像素 → CIELAB 空间 → 带遮罩模糊后 k-means 聚类 → 按 CIEDE2000 合并同一面料的深浅 → 按占比筛选主色 → 在原始像素中找点缀色 → 按参考色表命名。输出 hex、CIELAB 值与占比。具体算法与实验见技术原理《衣服的颜色怎样变成数据》。

**其余属性用视觉模型打标**：Haiku 4.5 + 结构化输出；低置信度字段由 Sonnet 5 复核。

**向量**：`voyage-multimodal-3.5` 为衣服图片与标签文本生成向量，用于相似单品检索与方案检索。M1 以相似单品检索的 top-5 命中率与其他候选比较。

## 9. 数据、任务队列与实时推送

**PostgreSQL 17 + pgvector**：业务数据、任务队列、事件、向量检索都在同一个数据库中，任务与业务数据可以在同一事务中提交。

**Procrastinate 3.x** 的工作方式与 StyleAI 中的用法：

| 机制 | Procrastinate 的实现 | StyleAI 的用法 |
| --- | --- | --- |
| 领取任务 | 数据库函数中 `FOR UPDATE SKIP LOCKED`，同一语句改为 doing | 多个 Worker 并行处理 |
| 新任务提醒 | 插入时触发 `pg_notify`；Worker 监听，默认每 5 秒轮询兜底 | 入库、生图尽快开始 |
| Worker 心跳 | 默认每 10 秒；超过 30 秒无心跳视为失联 | 定时任务回收停滞任务，从未完成阶段续跑 |
| 重试 | `RetryStrategy`：固定、线性、指数等待 | 外部 API 失败重试 |
| `lock` | 部分唯一索引：同一 lock 同时只有一个 doing | 同一方案同时只有一个生图任务 |
| `queueing_lock` | 部分唯一索引：同一值同时只有一个 todo | 防止重复登记入库任务 |
| 周期任务 | cron 表达式；数据库唯一约束防止重复登记 | 品牌巡检、杂志学习、停滞任务回收 |

队列划分：`ingest`、`render`、`scout`、`learn`、`maintenance`。`render` 队列的 Worker 单独部署，避免耗时的生图占满入库的处理能力。

**实时推送**：事件先写入 `agent_events` 表再 `NOTIFY`；API 实例监听后推送 SSE；浏览器重连时按 `Last-Event-ID` 从表中补发。

原理与实验见技术原理《用 PostgreSQL 做任务队列》。

## 10. 品牌数据获取

首发市场为日本，品牌目录使用各品牌日本官网的数据（见《内容来源清单》）。获取方式按优先级：

1. **官方或联盟营销渠道的商品数据**：最稳定、最合规。M0 开始逐个品牌调研。
2. **公开商品页面**：遵守 robots.txt 与使用条款，控制访问频率，解析页面中的结构化数据。
3. **明确不做**：绕过验证码、伪装浏览器指纹、破解反爬。

已知风险：大型品牌官网预计有较强的反爬措施与大量动态渲染，页面抓取可能不稳定。若某个品牌既没有联盟渠道、页面也无法稳定读取，就从首批品牌中替换，而不是采取对抗手段。

## 11. 部署（待验证 · M0）

| 组件 | 倾向方案 | 说明 |
|---|---|---|
| Web | Vercel | Next.js 原生支持 |
| API / Worker | 东京区域容器平台（Fly.io `nrt` 或 AWS ECS `ap-northeast-1`） | 靠近用户和数据库；SSE 需要支持长连接 |
| PostgreSQL | 东京区域托管服务（Supabase 或 AWS RDS），需支持 pgvector | M0 比较价格、连接数上限（LISTEN 连接）与运维成本 |
| 对象存储 | Cloudflare R2 | S3 兼容，无出网流量费 |
| 分割服务 | 按需 GPU 实例或 serverless GPU | M1 根据调用量决定 |

## 12. 可观测性与评测

- **日志**：structlog 输出 JSON，全链路带 `request_id` 与 `trace_id`，不记录密钥与用户隐私。
- **追踪**：OpenTelemetry 覆盖 HTTP、数据库、外部 API；`trace_id` 随任务参数传入 Worker。
- **Agent trace**：见《系统架构》第 12 节。
- **错误监控**：Sentry（Web 与 API）。
- **评测**：`evals/` 保存数据集与评测脚本。提示词或工具改动时，CI 跑小规模冒烟评测；每个里程碑结束时跑完整评测。评测集包括：衣服打标标注集、方案盲评集、效果图还原度评分集。

## 13. 版本基线

| 组件 | 版本 |
| --- | --- |
| Node.js / pnpm | 24 LTS / 10 |
| Next.js / React / Tailwind CSS | 16 / 19 / 4 |
| Python / uv | 3.13 / 最新稳定版 |
| FastAPI / Pydantic / SQLAlchemy | 最新稳定版 / 2 / 2 |
| psycopg / Procrastinate | 3 / 3.x |
| PostgreSQL / pgvector | 17 / 最新稳定版 |
| anthropic / google-genai | 最新稳定版，锁文件固定 |

## 14. 待验证事项

| 事项 | 里程碑 | 验证方式 |
|---|---|---|
| 手写循环与 Tool Runner | M0 | 同一场景各实现一次，比较代码量与事件、预算插入点 |
| Interactions API 与 generateContent | M0 | 多阶段编辑的写法、隐私设置、成本 |
| 部署平台与数据库托管 | M0 | 东京区域价格、延迟、连接数、运维成本 |
| 第三方模型服务的数据条款 | M0 | 确认用户图片是否用于训练、保存期限 |
| 品牌联盟营销渠道 | M0 起 | 逐个品牌调研日本地区的商品数据渠道与条款 |
| 抠图模型 | M1 | 50 件样本比较边缘质量、细节保留、耗时、许可 |
| 向量模型 | M1 | 相似单品检索 top-5 命中率 |
| 颜色提取阈值 | M1 | 200 件标注集校准主色、点缀色阈值 |
| 生图模型 | M3 | 按第 7.1 节维度盲评 |
| 后台 Agent 是否迁到 Managed Agents | M5 | 比较运维成本与可控性 |
