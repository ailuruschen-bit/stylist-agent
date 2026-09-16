# 开发规范

> 语言：中文（摸索阶段只维护中文版；日文、英文旧稿见 [docs/archive](../archive/)，正式开发开始时重新翻译）
> 状态：草案 v0.2 · 更新：2026-09-16
> 所有贡献者（包括 AI 编程助手）都应遵守本文。规范本身的修改，也要通过 PR 讨论后合入。模块划分与数据流见[《系统架构》](05-system-architecture.md)。

## 1. 语言约定

| 场景 | 语言 |
|---|---|
| 团队沟通、Issue 与 PR 讨论 | 中文为主 |
| `docs/` 下的文档 | **摸索阶段只写中文**；正式开发开始后恢复中日英三语，以中文为源版本 |
| 代码注释、docstring | 英文 |
| 标识符（变量、函数、类、表名、API 字段、事件名） | 英文 |
| Commit message、PR 标题 | 英文（Conventional Commits） |
| Agent 系统提示词、工具描述、技巧卡正文 | 英文（输出语言跟随用户） |
| 技巧卡术语 | `terms` 字段提供中日英对照 |
| UI 文案 | 通过 i18n 提供三语，禁止在组件中硬编码 |
| 返回给用户的错误信息 | 后端返回错误码与英文 message，前端按错误码显示三语文案 |
| 日志 | 英文 |

**摸索阶段的文档语言**：立项阶段文档改动频繁，逐条翻译不划算，因此 `draft` 分支上只写中文。此前翻译过的日文、英文稿件归档在 [`docs/archive/`](../archive/)，已停止同步，仅供查阅。

**正式开发开始后**：恢复中日英三语，中文为源版本。修改中文文档的 PR 须同时更新日文和英文版本；确实来不及翻译时，在 PR 中注明，在对应文档顶部标注“翻译中”，并创建 `docs: sync translations` 的 Issue，在下一个 PR 前补齐。

## 2. 分支与合并

当前有三条长期分支：

| 分支 | 内容 | 是否合回 `main` |
| --- | --- | --- |
| `main` | 保持干净。立项阶段只放仓库说明，正式开发开始后才放代码与定稿文档 | — |
| `draft` | 立项阶段的探索文档（立项、技术选型、开发规范、内容来源、系统架构，中日英三语） | 内容定稿后再整理合入 |
| `tech-notes` | 学习用的技术原理文章与实验代码 | 不合入 |

- `main` 为受保护分支，只能通过 PR 合入，使用 squash merge。M0 开始时在 GitHub 上开启：必须通过 CI、至少一人批准、保持线性历史、禁止强制推送。
- `draft` 上的文档仍在讨论中，可以直接提交，不要求 PR；结论稳定后再整理成正式文档合入 `main`。
- `tech-notes` 是长期存在的学习分支，存放技术原理文章和实验代码，与正式开发无关，**不合并回 `main`**。需要引用正式文档的最新内容时，从 `main` 合并到 `tech-notes`。
- 功能分支命名：`<type>/<short-description>`，例如 `feat/closet-upload`、`fix/sse-reconnect`。
  - 类型：`feat`、`fix`、`docs`、`refactor`、`test`、`chore`、`exp`（实验分支，可以不合入）。
  - 描述使用小写英文与连字符，不超过 5 个单词。
- 一个 PR 只做一件事。建议变更不超过 400 行（不含生成文件、锁文件和迁移快照）。更大的功能拆成多个 PR，按依赖顺序合入。
- 功能分支合入后删除。长期未合入的 `exp/` 分支每月清理一次。

## 3. Commit 规范

使用 [Conventional Commits](https://www.conventionalcommits.org/)：

```text
<type>(<scope>): <summary in imperative mood>

<optional body: what and why, wrapped at 72 columns>

<optional footer: BREAKING CHANGE: ..., Refs: #123>
```

| 部分 | 规则 |
| --- | --- |
| `type` | `feat`、`fix`、`docs`、`refactor`、`test`、`perf`、`chore`、`build`、`ci` |
| `scope` | `web`、`api`、`agent`、`render`、`closet`、`scout`、`learn`、`knowledge`、`evals`、`infra`、`docs`、`tech-notes` |
| summary | 英文祈使语气，首字母小写，不加句号，不超过 72 个字符 |
| body | 说明为什么改、有什么影响；“改了什么”由 diff 表达 |
| footer | 不兼容变更写 `BREAKING CHANGE:`；关联 Issue 写 `Refs: #123` |

示例：

```text
feat(closet): detect alternative wears during garment tagging

Tagging now returns wear options such as tied_waist and one_sleeve_off
based on category and closure type, so the agent can suggest them
without guessing.

Refs: #42
```

Squash merge 时，PR 标题即为最终的 commit summary，所以 PR 标题同样遵守本节规则。

## 4. Pull Request

### 4.1 PR 描述

使用仓库模板（`.github/pull_request_template.md`），至少说明：

1. 做了什么、为什么做
2. 如何验证（测试、截图、评测结果）
3. 是否影响提示词、工具、数据库结构、成本或合规
4. 三语文档是否已同步

尚未完成的 PR 以 Draft 形式创建。

### 4.2 按改动类型的检查项

| 改动类型 | 作者需要提供 | 审查者重点看 |
| --- | --- | --- |
| API 接口 | 更新 OpenAPI 生成的类型；说明是否兼容旧前端 | 字段命名、错误码、分页、权限过滤 |
| 数据库结构 | Alembic 迁移；说明迁移在大表上的耗时与锁 | 是否向前兼容上一版本代码；索引是否合理 |
| 提示词或工具 | 评测前后对比结果；trace 示例 | 工具描述是否写清“何时使用”；是否引入固定生图提示词 |
| 生图流水线 | 至少 10 个方案的前后对比图 | 服装还原、成本变化 |
| UI | 桌面与手机截图；三语文案 | 可访问性、加载与错误状态 |
| 外部数据获取 | 来源的 robots 与条款确认记录 | 是否只保存允许保存的字段 |
| 依赖升级 | 升级原因与变更日志要点 | 许可证、破坏性变更 |

### 4.3 完成标准（Definition of Done）

- [ ] 代码通过 lint、类型检查和测试
- [ ] 新增逻辑有对应测试
- [ ] 改动了提示词或工具时，附上评测结果
- [ ] 改动了数据库结构时，附上 Alembic 迁移
- [ ] 新增 UI 文案已提供三语
- [ ] 相关文档已更新（三语，或已按第 1 节标注并创建 Issue）
- [ ] 没有提交密钥、用户数据、品牌图片或杂志原文

### 4.4 审查约定

- 审查者在一个工作日内给出第一轮意见。
- 意见分为“必须修改”和“建议”，建议类意见由作者决定是否采纳。
- 讨论超过两轮仍无结论的，改为同步沟通，结论记录回 PR。

## 5. 通用编码原则

- **注释解释“为什么”**，不重复代码已经表达的“做了什么”。
- **不留死代码**：不用的代码直接删除，历史交给 git。
- **配置外置**：环境相关的值通过环境变量读取，并在 `.env.example` 中列出说明。
- **小函数、明确命名**：命名本身应该说明用途，避免 `data`、`info`、`handle`、`manager` 这类泛称。
- **失败要显式**：不要吞掉异常；无法处理的错误向上抛出，并带上足够的上下文。
- **TODO 必须关联 Issue**：写成 `# TODO(#123): ...`。
- **外部调用必有超时**：所有网络请求、模型调用、数据库查询都设置超时。

### 5.1 命名

| 对象 | 规则 | 示例 |
| --- | --- | --- |
| Python 模块、函数、变量 | snake_case | `extract_palette`、`garment_id` |
| Python 类 | PascalCase | `GarmentRepository` |
| 常量 | UPPER_SNAKE_CASE | `MAX_RENDER_IMAGE_CALLS` |
| 数据库表 | 复数 snake_case | `render_stages` |
| 数据库列 | snake_case；外键 `<entity>_id`；时间 `<verb>_at` | `outfit_id`、`reviewed_at` |
| API 路径 | 复数小写，连字符分隔 | `/v1/garments`、`/v1/me/memories` |
| JSON 字段 | camelCase | `garmentId`、`createdAt` |
| 事件名 | `<resource>.<event>` | `render.stage`、`garment.ready` |
| Agent 工具 | `verb_noun` snake_case | `search_wardrobe` |
| 环境变量 | `STYLEAI_` 前缀 + UPPER_SNAKE_CASE；第三方 SDK 约定的变量保持原名 | `STYLEAI_DATABASE_URL`、`ANTHROPIC_API_KEY` |
| TypeScript 文件 | kebab-case | `outfit-card.tsx` |
| React 组件 | PascalCase | `OutfitCard` |
| i18n key | 按页面分组的点分路径 | `closet.upload.title` |

## 6. Python 后端

### 6.1 工具与版本

- Python 3.13，依赖由 uv 管理（`pyproject.toml` + `uv.lock`）。
- ruff 负责 lint 与格式化（行宽 100）；mypy 对 `app/` 开启 strict 模式。
- 模块依赖方向用 import-linter 在 CI 中检查。
- pytest + pytest-asyncio 做测试。

### 6.2 分层

```text
api (routers)  ->  services  ->  repositories  ->  database
agent/tools    ->  services
pipelines      ->  services / providers
worker/tasks   ->  pipelines / services
services       ->  providers
```

| 层 | 负责 | 不做 |
| --- | --- | --- |
| `api` | 参数校验、鉴权、调用服务、组装响应 | 业务逻辑、直接访问数据库 |
| `services` | 业务规则、事务边界、组合多个仓储 | 处理 HTTP 细节 |
| `repositories` | 数据库读写，返回领域对象；所有查询带用户过滤条件 | 业务判断、返回 ORM Session |
| `agent/tools` | 把模型的工具请求转换为服务调用，把结果整理成给模型看的格式 | 直接访问数据库或外部 API |
| `pipelines` | 编排多步骤后台流程 | 定义任务调度参数 |
| `providers` | 调用外部服务：重试、超时、计量 | 业务规则 |
| `worker` | 声明 Procrastinate 任务、队列、重试、锁 | 业务逻辑 |

**事务边界在服务层。** 一个服务方法对应一个工作单元，由服务方法开启和提交事务；仓储方法接收会话参数，不自行提交。

### 6.3 一个完整的例子

路由只负责接收请求与返回响应：

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

服务层承载规则与事务：

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

接口模型统一使用 camelCase 别名：

```python
class ApiModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")


class GarmentTagsPatch(ApiModel):
    category: GarmentCategory | None = None
    formality: int | None = Field(default=None, ge=1, le=5)
    style_tags: list[str] | None = None
```

### 6.4 错误处理

- 可预期的业务错误抛出 `AppError(code, message, detail)`；统一的异常处理器把它转换为错误响应（格式见第 8.3 节）。
- 不可预期的异常由处理器记录完整堆栈并上报 Sentry，响应只返回 `INTERNAL_ERROR` 与 `requestId`。
- 调用外部服务的异常，在 `providers` 层转换为 `ProviderError`（带 `retryable` 标记），上层据此决定重试还是失败。
- 不要用异常控制正常流程；“没有找到”在仓储层返回 `None`，由服务层决定是否报错。

### 6.5 异步与超时

- IO 操作全部使用 async，不在事件循环中调用阻塞函数；必须调用阻塞库时（如图像处理），用 `asyncio.to_thread` 或放到 Worker 中执行。
- 每个外部调用设置超时：数据库查询默认 10 秒，普通 HTTP 30 秒，模型流式调用按场景配置。
- 并发执行多个工具或请求时使用 `asyncio.TaskGroup`，任何一个失败会取消其他任务，不留下悬空的协程。

### 6.6 日志

日志使用 structlog，写结构化字段，不拼接字符串：

```python
log.info("render_stage_completed", render_id=str(render_id), stage_no=stage.no, latency_ms=latency_ms, cost_usd=cost)
```

所有日志自动带上以下字段：

| 字段 | 说明 |
| --- | --- |
| `request_id` | HTTP 请求编号 |
| `trace_id` | 跨 API、Worker、外部调用的链路编号 |
| `user_id` | 当前用户（如有） |
| `turn_id` / `render_id` / `job_id` | 当前处理对象（如有） |

禁止记录：密钥、Cookie、密码、用户上传图片的内容或签名链接、完整的模型输入（需要时只记录长度与摘要，完整内容进入权限受控的 Agent trace）。

### 6.7 配置

- 配置集中在 `app/settings.py`，使用 pydantic-settings 从环境变量读取，启动时校验，缺失必需配置时直接启动失败。
- 业务代码通过依赖注入获取配置对象，不直接读取 `os.environ`。
- 模型 ID、effort、预算上限等 AI 相关参数也放在配置中，便于在不同环境中调整。

### 6.8 数据库迁移

- 所有结构变更都通过 Alembic 迁移完成，迁移文件随功能 PR 一起提交。
- 已经合入 `main` 的迁移文件不再修改，需要调整时新建迁移。
- 表名使用复数 snake_case；主键统一为 UUID（技巧卡编号除外）；所有表带 `created_at`、`updated_at`（带时区）。
- **迁移必须向前兼容**：发布时迁移先于新代码执行，旧代码仍在运行。删除或重命名列要分两次发布：先让代码不再使用，再删除。
- 在大表上创建索引使用 `CREATE INDEX CONCURRENTLY`。

## 7. TypeScript 前端

### 7.1 目录结构

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

### 7.2 编码要点

- 开启 `strict`，禁止 `any`（确有必要时用 `unknown` 并收窄类型）。
- 默认使用 Server Components，只在需要交互时加 `"use client"`。
- 服务端数据通过 TanStack Query 获取，不要把服务端数据复制到 Zustand。SSE 事件到达时，更新或失效对应的查询缓存。
- API 类型由 OpenAPI 生成（`pnpm gen:api`），**不手写接口类型**。外部输入用 zod 校验。
- 样式使用 Tailwind 与设计令牌，不写行内颜色值。
- 每个数据区域都要处理四种状态：加载中、空、错误、正常。
- UI 文案全部放在 `messages/` 中；数字、日期、价格使用 next-intl 的格式化函数，价格统一按日元显示。

### 7.3 可访问性

- 交互元素可以用键盘操作，焦点状态可见。
- 图片提供 `alt`；衣服图片的 `alt` 使用标签生成的描述，例如“灰色连帽卫衣”。
- 颜色对比度满足 WCAG AA；颜色信息同时用文字表达（例如色块旁显示颜色名称）。
- 流式输出区域设置 `aria-live="polite"`，避免屏幕阅读器被逐字打断。

## 8. API 设计

### 8.1 基本规则

- REST 风格，路径以 `/v1` 开头，资源名用复数。
- 请求与响应 JSON 使用 camelCase。
- 编号使用 UUID 字符串；时间使用 ISO 8601 格式的 UTC 时间，例如 `2026-09-16T08:30:00Z`。
- 金额以整数表示，并带币种字段，例如 `{"amount": 5990, "currency": "JPY"}`。
- 创建耗时任务的接口返回 `202 Accepted` 与任务或资源编号。

### 8.2 分页与幂等

- 列表接口使用游标分页：`?cursor=...&limit=20`，`limit` 最大 100，响应带 `nextCursor`，没有下一页时为 `null`。
- 创建类接口支持 `Idempotency-Key` 请求头：同一用户、同一 key 在 24 小时内重复请求，返回第一次的结果。

### 8.3 错误

错误响应统一格式：

```json
{ "error": { "code": "GARMENT_NOT_FOUND", "message": "Garment does not exist.", "detail": {}, "requestId": "..." } }
```

| HTTP 状态 | 使用场景 | 错误码示例 |
| --- | --- | --- |
| 400 | 请求格式或参数不合法 | `VALIDATION_FAILED` |
| 401 | 未登录或会话失效 | `UNAUTHENTICATED` |
| 403 | 已登录但无权访问 | `FORBIDDEN` |
| 404 | 资源不存在，或不属于当前用户 | `GARMENT_NOT_FOUND`、`OUTFIT_NOT_FOUND` |
| 409 | 状态冲突 | `TURN_IN_PROGRESS`、`RENDER_ALREADY_RUNNING` |
| 413 | 上传文件过大 | `UPLOAD_TOO_LARGE` |
| 422 | 格式正确但业务上无法处理 | `IMAGE_NOT_A_GARMENT` |
| 429 | 超过频率或额度限制 | `RATE_LIMITED`、`CREDITS_EXHAUSTED` |
| 503 | 依赖的服务暂时不可用 | `UPSTREAM_UNAVAILABLE` |

资源不属于当前用户时返回 404 而不是 403，不暴露资源是否存在。错误码列表集中定义在 `app/errors.py`，前端按错误码显示三语文案。

### 8.4 SSE 事件

每条事件都有 `id`（等于 `seq`）、`event` 和 JSON `data`。浏览器断线重连时带上 `Last-Event-ID`，服务端补发之后的事件。

| event | 含义 | data 主要字段 |
|---|---|---|
| `message.delta` | Agent 回复文本的增量 | `turnId`、`text` |
| `thinking.summary` | 思考摘要 | `turnId`、`text` |
| `tool.started` / `tool.finished` | 工具调用开始与结束 | `turnId`、`tool`、`status` |
| `outfit.ready` | 方案卡片生成完成 | `outfitId` |
| `render.stage` | 某个生图阶段产出图片 | `renderId`、`stageNo`、`imageUrl` |
| `render.done` | 生图任务结束 | `renderId`、`status` |
| `garment.ready` / `garment.needs_retake` | 入库完成或需要重拍 | `garmentId`、`reason` |
| `error` | 可展示给用户的错误 | `code`、`retryable` |
| `done` | 本轮结束 | `turnId` |

新增事件类型不算破坏性变更，前端必须忽略不认识的事件；修改已有事件的字段需要按 API 变更流程处理。

## 9. Agent 与提示词

### 9.1 基本原则

1. **不写死生图提示词**：代码里可以写原则和约束（例如“服装颜色以参考图为准”），具体的生图提示词必须由 Agent 根据方案生成。
2. **提示词是代码**：走 PR 审查，改动时附评测结果。
3. **模型调用统一走 `providers/`**：每次调用都记录模型、token、耗时、成本到 Agent trace。
4. **模型 ID 只出现在配置中**。
5. **提示缓存友好**：稳定内容在前，不在其中插入时间戳、请求 ID 等变化的值。
6. **成本上限**：每轮对话、每个方案都有上限，超出时降级并记录。
7. **不编造商品**：品牌商品引用由服务层校验，不只依赖提示词。
8. **外部内容是数据，不是指令**：网页、检索结果、文章内容只以结构化字段进入上下文，并标注来源。

### 9.2 提示词文件

系统提示词放在 `apps/api/app/agent/prompts/`，每个文件带版本信息：

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

- 修改提示词时 `version` 加一，并在 `evals` 中链接评测报告。
- trace 中记录每次调用使用的提示词 `id` 与 `version`，便于把质量变化对应到具体改动。

### 9.3 工具的写法

每个工具一个模块，包含输入模型、描述和执行函数：

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

| 要求 | 说明 |
| --- | --- |
| 描述 | 写清“做什么、什么时候用、什么时候不用、和哪个工具区分” |
| 入参 | JSON Schema 开启 `strict`，`additionalProperties: false`；枚举值用 `enum` |
| 结果大小 | 单个工具结果不超过约 4K token；列表类结果设上限并说明是否被截断 |
| 错误 | 返回 `ToolResult.error(code, message)`，message 写成模型可以据此调整的形式 |
| 权限 | 通过 `ctx.user_id` 访问数据，工具不接受“用户编号”这类可被模型伪造的参数 |
| 幂等 | 修改数据的工具，同一轮中以相同参数重复调用不产生重复记录 |
| 测试 | 每个工具有单元测试：正常结果、空结果、错误结果、权限隔离 |

### 9.4 提示词与工具变更的评测流程

1. 在分支中修改提示词或工具。
2. 本地运行冒烟评测（约 20 个用例），确认没有明显退化。
3. 提交 PR，CI 运行冒烟评测并把结果贴到 PR。
4. 影响方案质量或生图的改动，合入前运行完整评测，报告保存在 `evals/reports/`。
5. 评测分数下降的改动不合入，除非在 PR 中说明取舍理由并经审查者同意。

## 10. 知识库技巧卡

- 人工整理的技巧卡以 YAML 文件保存在 `knowledge/cards/`，一张卡一个文件，文件名为编号（`K-0412.yaml`），通过 PR 审核。
- 学习管线产生的候选卡存在数据库中，审核通过后导出为 YAML 并提交 PR。
- 编号格式 `K-0001`，编号只增不复用；废弃的卡片把 `status` 改为 `retired`，不删除文件。
- CI 用 JSON Schema 校验所有卡片的字段与取值。

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

**审核检查项**：技巧是否可以推广到多种单品，而不是某件具体商品；`when_to_use` 与 `avoid` 是否具体；没有照抄原文（规则见《内容来源清单》第 4 节）；与已有卡片不重复；`checks` 的数值是否合理。

## 11. 测试

| 层级 | 工具 | 要求 |
|---|---|---|
| 单元测试 | pytest、Vitest | 服务层行覆盖率 ≥ 80% |
| 集成测试 | pytest（Docker 中的真实 PostgreSQL） | 覆盖仓储、主要 API、任务的登记与执行 |
| 端到端 | Playwright | 上传入库、对话出方案、查看效果图三条主流程 |
| 评测 | `evals/` | 提示词或工具改动时运行，见第 9.4 节 |

- **单元测试不调用真实模型 API。** 使用录制好的响应作为 fixture，存放在 `tests/fixtures/llm/`；录制脚本会去除请求中的密钥与用户图片内容。
- 需要真实 API 的测试加 `@pytest.mark.live` 标记，默认不运行。
- 测试函数命名说明行为：`test_update_tags_pins_corrected_fields`。
- 测试之间不共享可变状态；集成测试每个用例在事务中执行并回滚。
- 测试图片只使用团队自己拍摄的服装，或许可条款明确允许使用的生成图片，并在 `tests/fixtures/LICENSES.md` 中登记来源。
- 评测数据集带版本号，修改数据集时同时记录修改原因，避免不同时间的评测分数不可比较。

## 12. 安全与合规

本仓库是**公开仓库**，以下规则没有例外：

- **不提交任何密钥**。所有密钥放在 `.env`（已被忽略），仓库中只保留 `.env.example`。
- 启用 gitleaks：本地 pre-commit 钩子 + CI 双重检查。一旦误提交密钥，立即作废并轮换，而不是只删掉 commit。
- 不提交用户数据、用户上传的图片、品牌商品图片、杂志原文。
- 访问外部网站时遵守 robots.txt 与使用条款；禁止绕过验证码、伪装指纹等反爬对抗手段。
- 用户上传的图片默认私有，只有本人可以访问；支持用户删除自己的数据。
- 依赖由 Renovate 或 Dependabot 定期发起升级 PR；新增依赖须确认许可证与维护状态。
- 管理员接口与普通接口分开鉴权，操作写入审计日志。

## 13. 开发环境

| 工具 | 版本 |
|---|---|
| Node.js | 24 LTS（`.nvmrc`） |
| pnpm | 10 |
| Python | 3.13（`.python-version`） |
| uv | 最新稳定版 |
| Docker | 用于本地 PostgreSQL 与集成测试 |

- 使用 `pre-commit` 管理本地钩子：ruff、prettier、gitleaks、提交信息格式检查、技巧卡 Schema 校验。
- 常用命令在 M0 统一整理到仓库根目录的任务脚本中（如 `just dev`、`just test`、`just gen-api`），并写入 `README`。
- 本地开发使用 `infra/docker-compose.yml` 启动 PostgreSQL；对象存储使用本地文件系统适配器。

## 14. 文档

| 目录 | 内容 | 分支 |
| --- | --- | --- |
| `docs/zh` | 立项、技术选型、开发规范、内容来源、系统架构（摸索阶段只有中文） | `draft` |
| `docs/archive` | 已停止同步的日文、英文旧稿 | `draft` |
| `docs/charter.html` | 立项文档的可视化版本（较早的快照） | `draft` |
| `docs/zh/tech-notes`、`docs/tech-notes/labs` | 技术原理文章与实验代码 | `tech-notes` |

- 文档中的决定发生变化时，更新文档本身并修改顶部的版本号与日期，不在文档末尾追加“变更记录”。
- 技术选型中“待验证”的项定稿时，把结论和依据（评测结果、对比数据）写回《技术选型》。
- 技术原理文章遵循“局部完备”原则：每篇围绕一个问题，解释回答它所需的全部概念；文中引用的实验输出必须来自实际运行。
