# stylist-agent · tech-notes

**这是学习分支。** 存放 StyleAI v2 相关技术的原理讲解与可运行实验，和正式开发无关，不会合并回 `main`。

- 立项阶段的文档在 [`draft`](https://github.com/ailuruschen-bit/stylist-agent/tree/draft/docs)
- 仓库说明在 [`main`](https://github.com/ailuruschen-bit/stylist-agent)

## 文章

每篇围绕一个问题，只解释回答它所需的概念；文中引用的输出都来自实验的实际运行。

| 文章 | 回答的问题 |
| --- | --- |
| [01 拆解“抠图”](docs/zh/tech-notes/01-generation-vs-segmentation.md) | 为什么衣橱入库不用生图模型抠图 |
| [02 衣服的颜色怎样变成数据](docs/zh/tech-notes/02-garment-color-extraction.md) | 主色、点缀色怎样从像素里算出来 |
| [03 用 PostgreSQL 做任务队列](docs/zh/tech-notes/03-postgresql-task-queue.md) | 关系数据库怎样当可靠的任务队列 |
| [04 拆解 Agent 接入](docs/zh/tech-notes/04-agent-tool-loop.md) | “Agent 调用工具”到底发生了什么 |
| [05 模型 SDK 与 Agent 框架](docs/zh/tech-notes/05-sdks-and-agent-frameworks.md) | Anthropic SDK、Google ADK、Spring AI、LangGraph 分别在哪一层 |
| [06 相似单品怎么找](docs/zh/tech-notes/06-vector-search.md) | “像不像”怎样变成可计算、可排序的量 |
| [07 上下文与提示缓存](docs/zh/tech-notes/07-context-and-prompt-caching.md) | 重发上下文的代价，缓存怎样避免重复付费 |
| [08 事件流](docs/zh/tech-notes/08-sse-event-stream.md) | 断线之后怎样不丢事件 |
| [09 结构化输出](docs/zh/tech-notes/09-structured-output.md) | 约束解码保证了什么，没保证什么 |
| [10 评测](docs/zh/tech-notes/10-evaluation.md) | 多少样本才足以支撑“这次更好”的结论 |
| [11 多阶段生图的一致性](docs/zh/tech-notes/11-multi-stage-consistency.md) | 一个阶段接一个阶段地编辑，误差会累积吗 |
| [12 图片的代价](docs/zh/tech-notes/12-image-tokens.md) | 一张照片值多少 token，应该缩到多大 |
| [13 外部内容是数据，不是指令](docs/zh/tech-notes/13-untrusted-content.md) | 读别人写的网页，风险在哪里，怎么限定后果 |

索引与阅读顺序见 [docs/zh/tech-notes/README.md](docs/zh/tech-notes/README.md)。

## 实验

实验代码在 [docs/tech-notes/labs](docs/tech-notes/labs)，不依赖应用代码，也不需要任何 API 密钥。运行方式见该目录的说明。

| 实验 | 对应文章 |
| --- | --- |
| [latent-roundtrip](docs/tech-notes/labs/latent-roundtrip) | 01、11 |
| [garment-palette](docs/tech-notes/labs/garment-palette) | 02 |
| [postgres-queue](docs/tech-notes/labs/postgres-queue) | 03 |
| [vector-search](docs/tech-notes/labs/vector-search) | 06 |
| [context-cost](docs/tech-notes/labs/context-cost) | 07 |
| [sse-stream](docs/tech-notes/labs/sse-stream) | 08 |
| [constrained-output](docs/tech-notes/labs/constrained-output) | 09 |
| [eval-stats](docs/tech-notes/labs/eval-stats) | 10 |
| [image-tokens](docs/tech-notes/labs/image-tokens) | 12 |
| [untrusted-content](docs/tech-notes/labs/untrusted-content) | 13 |

## 许可

暂未授权任何开源许可证，保留所有权利。
