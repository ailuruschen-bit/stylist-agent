# 开发规范

> 语言：**中文** · [日本語](../ja/03-dev-guidelines.md) · [English](../en/03-dev-guidelines.md)
> 状态：草案 v0.1 · 更新：2026-09-15
> 所有贡献者（包括 AI 编程助手）都应遵守本文。规范本身的修改，也要通过 PR 讨论后合入。

## 1. 语言约定

| 场景 | 语言 |
|---|---|
| 团队沟通、Issue 与 PR 讨论 | 中文为主 |
| `docs/` 下的文档 | 中文、日文、英文三语。**中文为源版本** |
| 代码注释、docstring | 英文 |
| 标识符（变量、函数、类、表名、API 字段） | 英文 |
| Commit message、PR 标题 | 英文（Conventional Commits） |
| Agent 系统提示词、工具描述 | 英文（输出语言跟随用户） |
| 知识库技巧卡 | 英文正文，术语附中日英对照 |
| UI 文案 | 通过 i18n 提供三语，禁止在组件中硬编码 |

**文档同步规则**：修改中文文档的 PR，须同时更新日文和英文版本。确实来不及翻译时，在 PR 中注明，并创建 `docs: sync translations` 的 Issue，在下一个 PR 前补齐。

## 2. 分支与合并

- `main` 为受保护分支，只能通过 PR 合入，使用 squash merge。
- 分支命名：`<type>/<short-description>`，例如 `feat/closet-upload`、`fix/sse-reconnect`。
  - 类型：`feat`、`fix`、`docs`、`refactor`、`test`、`chore`、`exp`（实验分支，可以不合入）。
- 一个 PR 只做一件事。建议变更不超过 400 行（不含生成文件、锁文件和迁移快照）。
- 合入条件：CI 全部通过，且至少一人 review。单人开发阶段允许自审，但必须对照 PR 模板逐项检查。

## 3. Commit 规范

使用 [Conventional Commits](https://www.conventionalcommits.org/)：

```text
<type>(<scope>): <summary in imperative mood>

<optional body: what and why>
```

- `type`：`feat`、`fix`、`docs`、`refactor`、`test`、`perf`、`chore`、`build`、`ci`
- `scope`：`web`、`api`、`agent`、`render`、`closet`、`scout`、`knowledge`、`evals`、`infra`、`docs`
- 示例：
  - `feat(closet): detect alternative wears during garment tagging`
  - `fix(render): retry stage when critique flags color mismatch`
  - `docs: add tech stack decision for task queue`

## 4. Pull Request

PR 描述使用仓库模板（`.github/pull_request_template.md`），至少说明：

1. 做了什么、为什么做
2. 如何验证（测试、截图、评测结果）
3. 是否影响提示词、工具、数据库结构、成本或合规
4. 三语文档是否已同步

**完成标准（Definition of Done）**

- [ ] 代码通过 lint、类型检查和测试
- [ ] 新增逻辑有对应测试
- [ ] 改动了提示词或工具时，附上评测结果
- [ ] 改动了数据库结构时，附上 Alembic 迁移
- [ ] 新增 UI 文案已提供三语
- [ ] 相关文档已更新（三语）
- [ ] 没有提交密钥、用户数据、品牌图片或杂志原文

## 5. 通用编码原则

- **注释解释“为什么”**，不重复代码已经表达的“做了什么”。
- **不留死代码**：不用的代码直接删除，历史交给 git。
- **配置外置**：环境相关的值通过环境变量读取，并在 `.env.example` 中列出。
- **小函数、明确命名**：命名本身应该说明用途，避免 `data`、`info`、`handle` 这类泛称。
- **失败要显式**：不要吞掉异常；无法处理的错误向上抛出，并带上足够的上下文。
- **TODO 必须关联 Issue**：写成 `# TODO(#123): ...`。

## 6. Python 后端

### 6.1 工具与版本

- Python 3.13，依赖由 uv 管理（`pyproject.toml` + `uv.lock`）。
- ruff 负责 lint 与格式化；mypy 对 `app/` 开启 strict 模式。
- pytest + pytest-asyncio 做测试。

### 6.2 分层

```text
api (routers)  ->  services  ->  repositories  ->  database
agent/tools    ->  services
worker/tasks   ->  services
```

- **路由层**只做参数校验、鉴权、调用服务、组装响应，不写业务逻辑。
- **服务层**承载业务逻辑，是唯一可以组合多个仓储的地方。
- **仓储层**只负责数据库读写，返回领域对象，不返回 ORM Session。
- **Agent 工具**调用服务层，不直接访问数据库，也不直接调用外部模型 API（通过 `providers/`）。

### 6.3 编码要点

- 所有函数签名都写类型标注；公共函数写英文 docstring。
- 接口边界（请求、响应、工具入参、LLM 结构化输出）一律使用 Pydantic 模型。
- JSON 字段对外使用 camelCase：Pydantic 模型统一配置 `alias_generator=to_camel`，Python 内部仍用 snake_case。
- IO 操作全部使用 async，不在事件循环中调用阻塞函数。
- 业务错误抛出 `AppError(code, message, detail)`，由统一的异常处理器转换为 HTTP 响应。
- 日志使用 structlog，写结构化字段，不拼接字符串；禁止记录密钥、Cookie、用户上传图片的内容。

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

### 6.4 数据库迁移

- 所有结构变更都通过 Alembic 迁移完成，迁移文件随功能 PR 一起提交。
- 已经合入 `main` 的迁移文件不再修改，需要调整时新建迁移。
- 表名使用复数 snake_case（如 `garments`、`knowledge_cards`）；主键统一为 UUID；所有表带 `created_at`、`updated_at`（带时区）。

## 7. TypeScript 前端

- 开启 `strict`，禁止 `any`（确有必要时用 `unknown` 并收窄类型）。
- 默认使用 Server Components，只在需要交互时加 `"use client"`。
- 服务端数据通过 TanStack Query 获取，不要把服务端数据复制到 Zustand。
- API 类型由 OpenAPI 生成（`pnpm gen:api`），**不手写接口类型**。外部输入用 zod 校验。
- 文件名使用 kebab-case（`outfit-card.tsx`），组件名使用 PascalCase（`OutfitCard`）。
- 样式使用 Tailwind 和设计令牌，不写行内颜色值。
- UI 文案全部放在 `messages/{zh-CN,ja,en}.json`，key 按页面分组，如 `closet.upload.title`。
- 可访问性：交互元素可以用键盘操作，图片提供 `alt`，颜色对比度满足 WCAG AA。
- ESLint（`eslint-config-next`）+ Prettier 统一格式。

## 8. API 设计

- REST 风格，路径以 `/v1` 开头，资源名用复数：`/v1/garments`、`/v1/outfits/{id}`。
- 请求与响应 JSON 使用 camelCase。
- 错误响应统一格式：

```json
{ "error": { "code": "GARMENT_NOT_FOUND", "message": "Garment does not exist.", "detail": {} } }
```

- 列表接口使用游标分页：`?cursor=...&limit=20`，响应带 `nextCursor`。
- 创建耗时任务的接口（上传入库、生图）支持 `Idempotency-Key` 请求头。
- **SSE 事件**：每条事件都有 `event` 和 JSON `data`，`data` 中带递增的 `seq`，便于断线重连后补发。

| event | 含义 |
|---|---|
| `message.delta` | Agent 回复文本的增量 |
| `thinking.summary` | 思考摘要 |
| `tool.started` / `tool.finished` | 工具调用开始与结束 |
| `render.stage` | 某个生图阶段产出图片 |
| `outfit.ready` | 方案卡片生成完成 |
| `error` | 可展示给用户的错误 |
| `done` | 本轮结束 |

## 9. Agent 与提示词

1. **不写死生图提示词**：代码里可以写原则和约束（例如“服装颜色以参考图为准”），具体的生图提示词必须由 Agent 根据方案生成。
2. **提示词是代码**：系统提示词放在 `apps/api/app/agent/prompts/*.md`，走 PR 审查；改动时附评测结果。
3. **工具设计**：
   - 一个工具只做一件事，名称使用 `verb_noun` 形式的 snake_case（如 `search_wardrobe`）。
   - 入参 JSON Schema 开启 `strict`，设置 `additionalProperties: false`。
   - 描述写清楚“什么时候用、什么时候不用”。
   - 返回结果精简、结构化，不把整页 HTML 或大段原始数据塞回模型。
   - 出错时返回 `is_error` 和可以据此采取行动的错误信息，不直接抛异常中断对话。
4. **模型调用统一走 `providers/`**：每次调用都记录模型、token、耗时、成本到 Agent trace。
5. **模型 ID 只出现在配置中**，业务代码不直接写模型名。
6. **提示缓存友好**：稳定内容（系统提示词、工具定义）放在前面，不在其中插入时间戳、请求 ID 等变化的值。
7. **成本上限**：每轮对话、每个方案都有 token 与生图次数上限，超出时降级（例如改为单阶段生图），并在 trace 中记录。
8. **不编造商品**：推荐品牌商品时，只能引用品牌目录中真实存在的条目。

## 10. 知识库技巧卡

- 人工整理的技巧卡以 YAML 文件保存在 `knowledge/cards/`，一张卡一个文件，通过 PR 审核。
- 学习管线产生的候选卡存在数据库中，审核通过后导出为 YAML 并提交 PR。
- 编号格式 `K-0001`，编号只增不复用。

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

- 技巧卡中不允许出现照抄的原文（规则见《内容来源清单》第 4 节）。

## 11. 测试

| 层级 | 工具 | 要求 |
|---|---|---|
| 单元测试 | pytest、Vitest | 服务层行覆盖率 ≥ 80% |
| 集成测试 | pytest（真实 PostgreSQL，Docker 启动） | 覆盖仓储与主要 API |
| 端到端 | Playwright | 覆盖上传入库、对话出方案、查看效果图三条主流程 |
| 评测 | `evals/` | 提示词或工具改动时运行，见《技术选型》第 12 节 |

- **单元测试不调用真实模型 API**。使用录制好的响应作为 fixture。
- 需要真实 API 的测试加 `@pytest.mark.live` 标记，默认不运行，需要显式开启。
- 测试图片只使用团队自己拍摄的服装，或许可条款明确允许使用的生成图片，并在 `fixtures/LICENSES.md` 中登记来源。

## 12. 安全与合规

本仓库是**公开仓库**，以下规则没有例外：

- **不提交任何密钥**。所有密钥放在 `.env`（已被忽略），仓库中只保留 `.env.example`。
- 启用 gitleaks：本地 pre-commit 钩子 + CI 双重检查。一旦误提交密钥，立即作废并轮换，而不是只删掉 commit。
- 不提交用户数据、用户上传的图片、品牌商品图片、杂志原文。
- 访问外部网站时遵守 robots.txt 与使用条款；禁止绕过验证码、伪装指纹等反爬对抗手段。
- 用户上传的图片默认私有，只有本人可以访问；支持用户删除自己的数据。

## 13. 开发环境

| 工具 | 版本 |
|---|---|
| Node.js | 24 LTS（`.nvmrc`） |
| pnpm | 10 |
| Python | 3.13（`.python-version`） |
| uv | 最新稳定版 |
| Docker | 用于本地 PostgreSQL 与集成测试 |

- 使用 `pre-commit` 管理本地钩子：ruff、prettier、gitleaks、提交信息格式检查。
- 本地启动方式会在 M0 完成后写入 `README`。
