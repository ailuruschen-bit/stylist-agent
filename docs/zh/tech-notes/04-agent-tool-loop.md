# 拆解 Agent 接入：模型怎样调用我们的代码

> 语言：**中文** · 日本語（翻译中） · English（翻译中）
> 所属：[技术原理](README.md) · 更新：2026-09-16

用户在 StyleAI 里说：“用我那件灰色卫衣，帮我搭一套周末去代官山逛街的造型。”

要回答这句话，Agent 至少得知道衣橱里有哪些下装和外套，查几张相关的技巧卡，最后还要让生图流水线出一张效果图。可是模型运行在 Anthropic 的服务器上，它连不上我们的数据库，也调用不了我们的 Python 函数。

那么，“Agent 调用工具”到底是怎么发生的？我们平时说的“Agent 接入”，接入的又是什么？

本文从一次最普通的 API 请求开始，一步步加上工具说明、工具调用、结果回传，把这条链路拆成我们能亲手写出来的一个循环。最后回到 StyleAI，看一轮真实对话会在这个循环里走几圈，以及生图这种耗时一两分钟的操作为什么不能直接放进循环里等结果。

本文的 JSON 示例按 Claude Messages API 的格式整理，为了便于阅读，省略了 `id`、`usage` 等与本文结论无关的字段。

## 从一次无状态的请求开始

调用 Claude，本质上是向 Messages API 发一个 HTTP 请求。请求里写明用哪个模型、最多生成多少 token，以及到目前为止的对话：

```json
{
  "model": "claude-opus-5",
  "max_tokens": 16000,
  "messages": [
    { "role": "user", "content": "灰色卫衣配什么裤子好看？" }
  ]
}
```

响应里是模型这一次生成的内容：

```json
{
  "role": "assistant",
  "stop_reason": "end_turn",
  "content": [
    { "type": "text", "text": "灰色卫衣很百搭。想要休闲一点，可以配深色直筒牛仔裤……" }
  ]
}
```

这里有两个细节，后面会反复用到。

第一，`content` 是一个**数组**，里面每一项叫作一个内容块（content block），用 `type` 区分种类。现在只有一个 `text` 块，后面会出现其他种类。

第二，`stop_reason` 说明模型**为什么停下**。`end_turn` 表示它认为这一轮已经说完了。

如果用户接着问“那鞋子呢？”，我们发出的第二个请求必须把前面的对话一起带上：

```json
{
  "model": "claude-opus-5",
  "max_tokens": 16000,
  "messages": [
    { "role": "user", "content": "灰色卫衣配什么裤子好看？" },
    { "role": "assistant", "content": [{ "type": "text", "text": "灰色卫衣很百搭……" }] },
    { "role": "user", "content": "那鞋子呢？" }
  ]
}
```

**Messages API 是无状态的：模型每次只能看到这一次请求里的内容。** 服务器不会替我们记住上一轮说了什么，“对话历史”由我们的应用保存，每次请求时完整发送。

这一点决定了后面的一切：模型能知道什么、能做什么，都取决于我们在请求里放了什么。

## 给模型一份工具说明书

现在的模型只会根据训练中学到的知识回答，它不知道这位用户的衣橱里到底有什么。我们希望它在需要的时候，能“查一下衣橱”。

做法是在请求里加上 `tools`，把我们愿意提供的能力逐个描述出来。以查询衣橱为例：

```json
{
  "name": "search_wardrobe",
  "description": "Search the user's wardrobe. Call this before recommending pieces the user already owns. Do not use it for brand catalog items.",
  "input_schema": {
    "type": "object",
    "properties": {
      "category": { "type": "string", "enum": ["tops", "bottoms", "outerwear", "shoes", "accessories"] },
      "style_tags": { "type": "array", "items": { "type": "string" } },
      "limit": { "type": "integer" }
    },
    "required": ["category"],
    "additionalProperties": false
  }
}
```

一份工具定义只有三部分：

| 字段 | 作用 |
| --- | --- |
| `name` | 工具名，模型用它来指明要调用哪一个 |
| `description` | 用自然语言说明这个工具做什么、**什么时候该用、什么时候不该用** |
| `input_schema` | 用 JSON Schema 描述参数的结构 |

注意，我们交给模型的只是这份**说明书**，而不是函数本身。`search_wardrobe` 背后真正查数据库的 Python 代码，始终留在我们的服务器上。

模型读到说明书后，就知道自己“可以请求查衣橱，并且要按这个格式给出参数”。`description` 写得越清楚，模型越能在该用的时候用、不该用的时候不用。这也是《开发规范》要求工具描述写清“何时使用”的原因。

## 模型“调用”工具时，实际发生了什么

带上工具定义，再发一次请求：

```json
{
  "model": "claude-opus-5",
  "max_tokens": 16000,
  "tools": [ { "name": "search_wardrobe", "...": "..." } ],
  "messages": [
    { "role": "user", "content": "用我那件灰色卫衣，帮我搭一套周末逛街的造型。" }
  ]
}
```

这次的响应变了：

```json
{
  "role": "assistant",
  "stop_reason": "tool_use",
  "content": [
    { "type": "text", "text": "我先看看你衣橱里有哪些能和灰卫衣搭的下装。" },
    {
      "type": "tool_use",
      "id": "toolu_01A",
      "name": "search_wardrobe",
      "input": { "category": "bottoms", "style_tags": ["casual", "street"], "limit": 10 }
    }
  ]
}
```

`content` 里多了一个 `tool_use` 块，`stop_reason` 也从 `end_turn` 变成了 `tool_use`。

把这个块读清楚，就能回答本文开头的问题：**模型并没有执行任何东西。它只是生成了一段结构化的文字，意思是“请帮我用这些参数调用 `search_wardrobe`”，然后停了下来。**

| 字段 | 含义 |
| --- | --- |
| `id` | 这次调用请求的编号，回传结果时要对上 |
| `name` | 想调用哪个工具 |
| `input` | 按 `input_schema` 生成的参数 |

`stop_reason: "tool_use"` 则是在告诉我们：模型的话还没说完，它在等工具的结果。

从模型的角度看，“调用工具”和“写一句回答”是同一件事：都是在生成内容。区别只在于，工具调用这部分内容有固定的结构，我们的程序能读懂并据此行动。

## 我们执行，再把结果交回去

模型停在了半路，接下来轮到我们的应用：

1. 从 `content` 中找到 `tool_use` 块。
2. 按 `name` 找到对应的 Python 函数，用 `input` 作为参数执行它。
3. 把执行结果作为 `tool_result` 块，放进一条新的 `user` 消息，再次发起请求。

第三步发出的 `messages` 是这样的：

```json
[
  { "role": "user", "content": "用我那件灰色卫衣，帮我搭一套周末逛街的造型。" },
  {
    "role": "assistant",
    "content": [
      { "type": "text", "text": "我先看看你衣橱里有哪些能和灰卫衣搭的下装。" },
      { "type": "tool_use", "id": "toolu_01A", "name": "search_wardrobe", "input": { "category": "bottoms", "...": "..." } }
    ]
  },
  {
    "role": "user",
    "content": [
      {
        "type": "tool_result",
        "tool_use_id": "toolu_01A",
        "content": "[{\"id\":\"G-000088\",\"name\":\"black wide chinos\"},{\"id\":\"G-000102\",\"name\":\"indigo straight jeans\"}]"
      }
    ]
  }
]
```

这里有三处需要对齐：

- 上一轮模型返回的 `content` **原样**放回 `assistant` 消息，包括其中的 `tool_use` 块。
- `tool_result` 放在 `user` 消息里。对模型来说，工具结果是“外部世界”提供的信息，和用户输入属于同一侧。
- `tool_use_id` 必须等于对应 `tool_use` 的 `id`，模型靠它把结果和请求对上。

模型拿到结果后继续生成。它可能直接给出搭配建议（`stop_reason` 变回 `end_turn`），也可能发现还需要查外套，于是再请求一次工具。

## 把它写成一个循环

“请求 → 模型要工具 → 执行 → 回传 → 再请求”这件事，会一直重复到模型不再请求工具为止。用伪代码写出来：

```text
messages = [用户的话]

loop:
    response = 调用 Messages API(model, tools, messages)
    messages.append(assistant: response.content)      // 原样保存模型输出

    if response.stop_reason != "tool_use":
        break                                          // 模型说完了

    results = []
    for block in response.content where block.type == "tool_use":
        output = 执行我们的函数(block.name, block.input)
        results.append(tool_result(tool_use_id = block.id, content = output))

    messages.append(user: results)                     // 结果交回模型

最终回答 = response.content 中的 text 块
```

这就是 Agent 最核心的结构。在本文的范围内，我们可以这样定义：**Agent = 模型 + 一组工具 + 让两者来回交替的循环。** 模型负责决定下一步做什么，工具负责真正去做，循环负责把两边接起来。

所谓“Agent 接入”，就是在我们的应用里实现这三件事：写好工具说明，执行模型请求的工具，维护消息历史并驱动循环。

## 一次回复里可以请求多个工具

模型可以在同一次响应里放多个 `tool_use` 块。比如它想同时查下装和相关技巧卡：

```json
"content": [
  { "type": "tool_use", "id": "toolu_01A", "name": "search_wardrobe", "input": { "category": "bottoms" } },
  { "type": "tool_use", "id": "toolu_01B", "name": "retrieve_techniques", "input": { "query": "street casual with grey hoodie" } }
]
```

这两个调用互不依赖，我们可以并发执行。回传时，**把所有 `tool_result` 放进同一条 `user` 消息**，每个结果用各自的 `tool_use_id` 对应：

```json
{
  "role": "user",
  "content": [
    { "type": "tool_result", "tool_use_id": "toolu_01A", "content": "..." },
    { "type": "tool_result", "tool_use_id": "toolu_01B", "content": "..." }
  ]
}
```

如果工具执行失败，不要吞掉这个结果，也不要让整个请求报错退出。返回一个带 `"is_error": true` 的 `tool_result`，并写清楚发生了什么：

```json
{ "type": "tool_result", "tool_use_id": "toolu_01A", "is_error": true, "content": "Category 'pants' is not valid. Use one of: tops, bottoms, outerwear, shoes, accessories." }
```

模型读到错误后，通常会修正参数重试，或者换一种做法。**错误信息也是给模型看的输入**，所以要写成它能据此采取行动的样子。

## 让参数一定符合格式

模型按 `input_schema` 生成参数，但“按照”不等于“保证”。如果在工具定义里加上 `"strict": true`，API 会约束生成过程，保证 `input` 一定能通过这份 JSON Schema 的校验。

同样的思路也用在模型的最终回答上。StyleAI 需要一张结构化的方案卡片（单品列表、层次角色、配色逻辑、理由），而不是一段自由文本。这时可以用结构化输出（`output_config.format`）指定回答的 JSON Schema。

两者的分工是：

| 机制 | 约束的对象 | StyleAI 中的用途 |
| --- | --- | --- |
| `strict: true` | 工具调用的参数 | 所有工具入参 |
| `output_config.format` | 模型的回答内容 | 打标结果、方案卡片、生图计划 |

## 服务端工具：由 Anthropic 执行的工具

前面的工具都由我们执行，称为**客户端工具**。还有一类工具由 Anthropic 在服务器上执行，比如网页搜索 `web_search` 和网页读取 `web_fetch`，称为**服务端工具**。

声明方式不同，服务端工具不需要我们写 `input_schema`，只声明类型：

```json
{ "type": "web_search_20260209", "name": "web_search", "allowed_domains": ["www.uniqlo.com", "www.zara.com"] }
```

执行方式也不同。模型决定搜索时，Anthropic 的服务器直接执行搜索，把结果放回模型的上下文，模型继续生成。我们收到的响应里，会同时出现调用和结果两个块：

```text
content:
  text                    "我去优衣库日本官网看看当季的宽松长裤。"
  server_tool_use         { name: "web_search", input: { query: "..." } }
  web_search_tool_result  [ 搜索结果列表 ]
  text                    "找到两款……"
```

**我们的循环不需要为服务端工具做任何事**，它们在一次 API 请求内部就完成了。唯一要处理的是 `stop_reason: "pause_turn"`：服务端工具在一次请求里连续执行太多轮时，API 会暂停并返回。这时把收到的 `content` 原样追加为 `assistant` 消息，再发一次请求，服务器就会从暂停处继续。

所以循环的判断条件要稍微扩展：

```text
if stop_reason == "tool_use":   执行客户端工具，回传结果，继续
if stop_reason == "pause_turn": 原样追加 assistant 内容，继续
否则:                           结束
```

## 思考内容也要原样放回

StyleAI 的主对话开启了自适应思考（adaptive thinking）。开启后，模型可能在 `text` 和 `tool_use` 之前先生成 `thinking` 块，里面是推理过程的摘要，或者为空（取决于显示设置）。

对循环来说，只需要记住一条：**`thinking` 块和其他块一样，要随 `assistant` 消息原样放回。** 模型在工具调用之间保持连贯的推理，依赖这些块。前面伪代码里“原样保存模型输出”这一步，已经覆盖了这个要求。

## 流式输出：边生成边推给浏览器

一轮回答可能要生成几百到几千个 token。如果等整条响应生成完再返回，用户会盯着空白界面等十几秒。

开启流式输出后，API 通过 SSE（Server-Sent Events）把响应拆成一连串事件推送过来：

```text
message_start
content_block_start   { index: 0, type: "text" }
content_block_delta   { text_delta: "我先看看" }
content_block_delta   { text_delta: "你衣橱里……" }
content_block_stop
content_block_start   { index: 1, type: "tool_use", name: "search_wardrobe" }
content_block_delta   { input_json_delta: "{\"category\":" }
content_block_delta   { input_json_delta: " \"bottoms\"}" }
content_block_stop
message_delta         { stop_reason: "tool_use" }
message_stop
```

事件的顺序和前面的 `content` 数组一一对应：每个内容块有开始、若干增量、结束。工具参数也是一段段到达的，要等 `content_block_stop` 之后才能解析完整的 JSON。

StyleAI 的后端夹在中间：一边接收 Anthropic 的事件，一边转换成我们自己的事件推给浏览器。两套事件的对应关系是：

| Anthropic 事件 | StyleAI 推给浏览器的事件 |
| --- | --- |
| `text` 块的 `text_delta` | `message.delta` |
| `thinking` 块的摘要 | `thinking.summary` |
| `tool_use` 块结束 | `tool.started` |
| 我们执行完工具 | `tool.finished` |
| `message_stop` 且 `stop_reason` 为 `end_turn` | `done` |

我们不直接把 Anthropic 的事件转发给浏览器。前端只依赖我们定义的事件格式，将来即使更换模型厂商，前端也不需要改。

## 回到 StyleAI：一轮对话走几圈

现在把开头那句话放进循环，看一轮对话的完整过程。下面是一种典型的走法，模型在每一步的具体选择会随对话内容变化：

| 圈数 | 模型输出 | 我们的应用做什么 | 浏览器看到 |
| --- | --- | --- | --- |
| 1 | 文字 + `search_wardrobe`（下装）+ `retrieve_techniques`（街头休闲） | 并发执行两个工具，回传结果 | 一句开场白，两个“正在查询”提示 |
| 2 | `search_wardrobe`（外套） | 执行，回传 | “正在查询外套” |
| 3 | `validate_outfit`（候选方案） | 用配色与层次规则检查，返回通过或问题清单 | “正在检查搭配” |
| 4 | `render_look`（方案 + 模特） | **创建生图任务，立即返回任务编号** | “效果图生成中” |
| 5 | 方案卡片（结构化输出），`end_turn` | 保存方案，结束本轮 | 方案卡片 |

第 4 圈值得单独说明。

## 生图为什么不在循环里等

一张多阶段效果图要 40 秒到两分钟。如果 `render_look` 同步执行，循环就要卡在这里等生图完成，而这段时间里：

- API 请求之间的间隔被拉长，Web 请求可能超时；
- 用户看不到任何中间进展；
- 服务进程重启时，正在等待的对话会直接丢失。

所以 `render_look` 只做一件事：把生图计划写进任务队列，马上返回：

```json
{ "type": "tool_result", "tool_use_id": "toolu_04", "content": "{\"renderJobId\":\"R-3391\",\"status\":\"queued\"}" }
```

模型拿到任务编号，就可以先把方案卡片交给用户，本轮对话结束。生图流水线在后台 Worker 中独立运行，每完成一个阶段，就通过 SSE 推送一次 `render.stage` 事件，前端把图片填进方案卡片。

生图流水线内部同样会调用 Claude，比如用 `render_critique` 检查效果图。但那是一段由我们代码控制步骤的**固定流程**：规划、逐阶段生成、检查、修复。它和对话循环不同，不需要模型决定“下一步调用哪个工具”。任务队列本身的工作原理，见[《用 PostgreSQL 做任务队列》](03-postgresql-task-queue.md)。

**对话循环负责决策，耗时的执行交给任务队列。** 这条边界决定了 StyleAI 的系统架构。

## 自己写循环，还是用 SDK 的 Tool Runner

Anthropic 的 Python SDK 提供了一个 Tool Runner。我们用装饰器把普通函数声明成工具，它会自动生成 `input_schema`，并替我们跑前面那个循环：

```python
from anthropic import Anthropic, beta_tool

client = Anthropic()


@beta_tool
def search_wardrobe(category: str, limit: int = 10) -> str:
    """Search the user's wardrobe by category.

    Args:
        category: One of tops, bottoms, outerwear, shoes, accessories.
        limit: Maximum number of garments to return.
    """
    return json.dumps(wardrobe_service.search(category=category, limit=limit))


runner = client.beta.messages.tool_runner(
    model="claude-opus-5",
    max_tokens=16000,
    tools=[search_wardrobe],
    messages=[{"role": "user", "content": "..."}],
)
for message in runner:  # one assistant message per loop iteration
    print(message.content)
```

它和我们手写的循环做的是同一件事，只是把“执行工具、拼接 `tool_result`、判断是否结束”藏进了 SDK。

StyleAI 在 M0 先手写循环，原因来自前面几节：

1. **每一步都要落库、推送 SSE。** 手写循环里，每个内容块、每次工具执行都有明确的位置写 trace、发事件。
2. **我们会同时使用服务端工具。** Python SDK 的 Tool Runner 在当前版本中不会自动处理 `pause_turn`，品牌检索时需要自己续上暂停的轮次。
3. **成本上限和降级**需要在每一圈之间检查 token 与生图次数。

手写循环的核心逻辑不到一百行。M0 会用两种写法各实现一次同一个场景，对比代码量和可控性后在《技术选型》中定稿。

## 小结

回到开头的问题：模型从来没有“调用”我们的代码。它读取工具说明，输出一段结构化的调用请求，然后停下；我们的应用执行请求、交回结果，再让模型继续。**Agent 接入的全部工作，就是把这个往返过程稳定地跑起来。**

在此基础上，StyleAI 又加了三条约定：前端只看我们自己的事件格式；工具调用的参数和最终回答都用 Schema 约束；耗时操作交给任务队列，不在对话循环里等待。

读完本文，可以试着回答：如果用户在效果图还没生成完时又发了一句“换成白色鞋子”，消息历史里会有哪些内容？新的一轮循环会从哪里开始？

## 参考资料

- [Claude API：工具使用概览](https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview)
- [Claude API：实现工具调用](https://platform.claude.com/docs/en/agents-and-tools/tool-use/implement-tool-use)
- [Claude API：处理 stop_reason（含 pause_turn）](https://platform.claude.com/docs/en/build-with-claude/handling-stop-reasons)
- [Claude API：程序化工具调用](https://platform.claude.com/docs/en/agents-and-tools/tool-use/programmatic-tool-calling)
- [Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python)
- [MDN：Server-Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)
