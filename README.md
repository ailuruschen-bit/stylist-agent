# stylist-agent · draft

**StyleAI v2**（工作名）：一位和你共用衣橱的 AI 穿搭博主。

它懂色彩与层次，读得懂你上传的每件衣服，会去品牌官网找单品，自己写提示词、自己决定怎么分阶段生成穿搭效果图，并通过阅读时尚杂志不断学到新技巧。

> **这是 `draft` 分支：立项摸索阶段的文档，还没有定稿，也还没有应用代码。**
> 干净的仓库说明在 [`main`](https://github.com/ailuruschen-bit/stylist-agent)，技术原理与实验在 [`tech-notes`](https://github.com/ailuruschen-bit/stylist-agent/tree/tech-notes/docs/zh/tech-notes)。

## 文档

摸索阶段只维护中文版，正式开发开始后再恢复中日英三语。

| 文档 | 说明 |
|---|---|
| [01 立项文档](docs/zh/01-project-charter.md) | 愿景、用户与场景、范围、核心能力、里程碑、风险、成功指标、待决策事项 |
| [02 技术选型](docs/zh/02-tech-stack.md) | 各层的选型结论、理由、备选方案与待验证事项 |
| [03 开发规范](docs/zh/03-dev-guidelines.md) | 分支与提交、代码规范、API 与事件约定、Agent 与提示词规范、测试与安全 |
| [04 内容来源清单](docs/zh/04-content-sources.md) | 品牌与杂志来源、数据字段映射、使用规则 |
| [05 系统架构](docs/zh/05-system-architecture.md) | 上下文、容器、模块、核心流程、数据模型、可观测性、失败处理 |

立项文档另有可视化版本 [docs/charter.html](docs/charter.html)，下载后用浏览器打开（内容为较早的快照）。

日文、英文旧稿归档在 [docs/archive/](docs/archive/)，已停止同步。

## 关键决策

- 平台：Web
- 首发市场：日本，受众为 18–30 岁年轻人
- 首批品牌：UNIQLO、ZARA、H&M、NIKE、adidas
- 技术栈：Next.js + FastAPI + PostgreSQL（pgvector）；Agent 使用 Claude Opus 5；生图使用 Gemini
- 基于 [HackathonPJT](https://github.com/ailuruschen-bit/HackathonPJT/tree/deploy/lite-budget) 的 demo 重新构建

## 许可

暂未授权任何开源许可证，保留所有权利。
