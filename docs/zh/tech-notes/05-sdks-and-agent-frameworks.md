# 模型 SDK 与 Agent 框架：Anthropic SDK、Google Gen AI SDK / ADK、Spring AI、LangGraph

> 语言：**中文** · 日本語（翻译中） · English（翻译中）
> 所属：[技术原理](README.md) · 更新：2026-09-16 · 前置阅读：[04 拆解 Agent 接入](04-agent-tool-loop.md)

讨论技术选型时，这些名字经常被放在一起比较：Anthropic SDK、Google Gen AI SDK、Google ADK、Spring AI、LangChain、LangGraph。它们都和“调用大模型、构建 Agent”有关，但并不是同一类东西。把 Spring AI 和 Anthropic SDK 放在同一张对比表里，就像把 Spring Data 和 JDBC 驱动放在一起比较：两者都能读写数据库，却处在不同的层级。

上一篇文章把 Agent 拆成了“模型 + 工具 + 循环”，并且手写了这个循环。本文就以这个循环为参照物，看每个 SDK 或框架替我们做了其中的哪一部分，又额外带来了什么。

我们从一个不用任何 SDK 的 HTTP 请求开始，逐层往上：厂商 SDK、Spring AI 这样的应用框架、LangGraph 和 ADK 这样的编排框架。最后回到 StyleAI，说明为什么主对话直接使用 Anthropic SDK。

本文的代码用于说明各个库的结构和写法，没有连接真实 API 运行；各库的版本信息核对于 2026 年 9 月。

## 先画出层级

先给出本文的整体模型，后面逐层展开：

```text
┌─────────────────────────────────────────────────────────────────┐
│ 编排 / Agent 框架   LangGraph、Google ADK                          │
│ 多步流程的结构、状态、持久化、暂停与恢复                            │
├─────────────────────────────────────────────────────────────────┤
│ 应用框架            Spring AI、LangChain                           │
│ 统一多家模型的接口，融入所在的技术生态                               │
├─────────────────────────────────────────────────────────────────┤
│ 厂商 SDK            anthropic、google-genai                        │
│ 把 HTTP API 包装成编程语言里的类型和函数                            │
├─────────────────────────────────────────────────────────────────┤
│ 模型服务 API        Claude Messages API、Gemini API                │
│ HTTPS + JSON                                                       │
└─────────────────────────────────────────────────────────────────┘
```

越往上，库替我们做的事情越多，我们写的代码离真正的 HTTP 请求也越远。**上层几乎都建立在下层之上**：Spring AI 2.0 调用 Claude 时使用 Anthropic 官方的 Java SDK，LangGraph 通过 LangChain 的模型接口调用各家模型，最终发出的都是同样的 HTTP 请求。

对 Java 开发者，可以借用一组熟悉的对应关系来记：

| AI 领域 | Java 数据访问领域 |
| --- | --- |
| 模型服务 API | 数据库的网络协议 |
| 厂商 SDK | JDBC 驱动 |
| Spring AI | Spring Data / JdbcTemplate |
| LangGraph、ADK | 更接近工作流引擎，负责跨多步的流程与状态 |

这个类比只用来定位层级。下面我们逐层看它们具体做了什么。

## 起点：不用 SDK 的一次请求

Messages API 就是一个 HTTPS 接口。用 Python 的 httpx 直接调用：

```python
import os

import httpx

response = httpx.post(
    "https://api.anthropic.com/v1/messages",
    headers={
        "x-api-key": os.environ["ANTHROPIC_API_KEY"],
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    },
    json={
        "model": "claude-opus-5",
        "max_tokens": 16000,
        "messages": [{"role": "user", "content": "灰色卫衣配什么裤子？"}],
    },
    timeout=600,
)
data = response.json()
print(data["content"][0]["text"])
```

这段代码能工作，但所有细节都要我们自己处理：

- 响应是字典，`data["content"][0]["text"]` 写错了键名，运行时才会发现；
- 遇到 429（限流）或 5xx（服务端错误），要自己判断是否重试、隔多久重试；
- 流式输出时，要自己解析 SSE 的每一行事件，再拼回内容块；
- 工具调用的循环，要自己完整实现。

## 厂商 SDK：把 HTTP 变成函数调用

### Anthropic SDK

同样的请求，用 Anthropic 的 Python SDK：

```python
from anthropic import Anthropic

client = Anthropic()  # reads ANTHROPIC_API_KEY from the environment

message = client.messages.create(
    model="claude-opus-5",
    max_tokens=16000,
    messages=[{"role": "user", "content": "灰色卫衣配什么裤子？"}],
)
for block in message.content:
    if block.type == "text":
        print(block.text)
```

SDK 做的事情可以列得很具体：

| 替我们处理的事 | 表现 |
| --- | --- |
| 请求与响应的类型 | 响应是带类型的对象，编辑器能补全，类型检查能发现错误 |
| 认证与请求头 | 从环境变量读取密钥，自动加上版本头 |
| 重试与超时 | 对限流、服务端错误和网络错误默认重试 2 次；有默认超时 |
| 流式输出 | `client.messages.stream(...)` 把 SSE 事件解析成对象，并能直接拿到最终完整消息 |
| 错误分类 | 限流、认证失败、参数错误分别是不同的异常类型 |
| 工具循环（可选） | Tool Runner 按上一篇的循环执行工具并回传结果 |

**但 SDK 没有改变 API 的任何语义。** 消息仍然由我们保存，工具调用仍然是 `tool_use` 和 `tool_result` 两种内容块，`stop_reason` 仍然需要判断。SDK 是 API 在编程语言里的一层薄封装，API 文档里的每个概念，都能在 SDK 里找到一一对应的类型。

Anthropic 为 Python、TypeScript、Java、Go、Ruby、C#、PHP 提供官方 SDK。新的 API 能力（比如新的服务端工具）通常最先出现在这一层。

### Google Gen AI SDK

Google 为 Gemini API 提供的官方 SDK 叫 Google Gen AI SDK，Python 包名是 `google-genai`。结构和 Anthropic SDK 类似：创建一个客户端，调用生成内容的方法。

它和 Anthropic SDK 有两处值得注意的差别。

**第一，默认自动执行工具。** 把一个普通的 Python 函数直接放进 `tools`，SDK 会读取函数签名和文档字符串生成工具声明；模型请求调用时，SDK 自己执行这个函数、回传结果、继续请求，默认最多连续执行 10 次：

```python
from google import genai
from google.genai import types

client = genai.Client()  # reads the Gemini API key from the environment


def search_wardrobe(category: str) -> list[dict]:
    """Search the user's wardrobe by category."""
    return wardrobe_service.search(category=category)


response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="What bottoms go with my grey hoodie?",
    config=types.GenerateContentConfig(tools=[search_wardrobe]),
)
print(response.text)
```

上一篇里我们手写的循环，在这里被默认隐藏了。需要自己控制时，可以通过 `AutomaticFunctionCallingConfig(disable=True)` 关闭，改为手动处理模型返回的函数调用。

**第二，Google 提供了有状态的 Interactions API。** 除了传统的 `generateContent`（Google 现在称其为旧版，但仍完整支持），Gemini API 新增了 Interactions API：每次交互在服务端保存，下一次请求只需带上 `previous_interaction_id`，不必重新发送完整历史。这和 Messages API“历史由应用保存、每次完整发送”的方式不同。Gemini 图像生成文档中的示例，也已经改用 Interactions API 编写。

StyleAI 生图使用 Gemini 图像模型，所以后端会同时使用两家的 SDK：对话与编排用 Anthropic SDK，生图 provider 内部用 Google Gen AI SDK。两者都封装在各自的 provider 接口后面，业务代码不直接依赖任何一家。

## Spring AI：Spring 生态里的统一抽象

### 它处在哪一层

Spring AI 是 Spring 官方的项目，面向 Java。它不是某一家模型厂商的 SDK，而是在各家模型之上提供一套统一的编程接口。2026 年 6 月发布的 Spring AI 2.0 面向 Spring Boot 4.0 / 4.1 和 Spring Framework 7.0，核心支持 OpenAI、Anthropic、Amazon Bedrock、Google GenAI、Mistral AI、DeepSeek、Ollama 等模型服务；其中 OpenAI 和 Anthropic 的集成改为基于厂商的官方 SDK 实现。

所以“Spring AI 算什么”的答案是：**它是应用框架层，站在厂商 SDK 之上**。就像我们用 Spring Data 时不必关心底层是哪个 JDBC 驱动，用 Spring AI 写的代码，可以通过配置切换底层模型。

### ChatClient 与 Advisor 链

Spring AI 的主要入口是 `ChatClient`。一次调用大致这样写：

```java
class WardrobeTools {

    @Tool(description = "Search the user's wardrobe by category")
    List<Garment> searchWardrobe(String category) {
        return wardrobeService.search(category);
    }
}

String answer = chatClient.prompt()
        .user("What bottoms go with my grey hoodie?")
        .tools(new WardrobeTools())
        .call()
        .content();
```

`@Tool` 注解的作用，和 Anthropic Python SDK 的 `@beta_tool` 装饰器类似：从方法签名生成工具说明。

更能体现 Spring 风格的是 **Advisor 链**。每次请求在发给模型之前、响应返回之后，都会依次经过一串 Advisor。它们像 Servlet 的 Filter 或 Spring 的拦截器，可以在请求里补充对话记忆、检索到的文档，也可以记录日志、校验结构化输出。

2.0 版本把工具调用的循环也做成了一个 Advisor，叫 `ToolCallingAdvisor`，`ChatClient` 默认自动注册它。它的工作方式，正好对应上一篇的循环：

```text
ChatClient.call()
   │
   ▼
Advisor 链（按 order 排序）
   ├─ 对话记忆 Advisor …………… 在循环外：只看到最终结果
   ├─ ToolCallingAdvisor
   │     ├─ 调用模型
   │     ├─ 响应里有工具调用？
   │     │     是 → ToolCallingManager 执行工具 → 追加结果 → 重新进入下游链路
   │     │     否 → 返回
   ├─ 日志 Advisor ……………………… 放在循环内：能看到每一圈的请求与响应
   ▼
ChatModel（Anthropic、OpenAI、Google GenAI……）
```

Advisor 放在 `ToolCallingAdvisor` 之前还是之后，决定了它只看到最终结果，还是能看到循环里的每一圈。在 1.x 版本中，这个循环藏在各个模型实现的内部，外部无法插入逻辑；2.0 把它提到了公开的 Advisor 链上。

Spring AI 还提供向量数据库的统一接口、MCP（Model Context Protocol）的客户端与服务端注解等能力，用法同样遵循 Spring 的配置和依赖注入方式。

**对 Java 团队来说，Spring AI 的价值在于“一致性”**：模型调用和其他 Spring 组件一样，可以注入、配置、测试、观测。代价是多了一层抽象：某家模型刚发布的新参数，要等 Spring AI 适配后才能通过统一接口使用。

StyleAI 的后端是 Python，所以不会使用 Spring AI；这里介绍它，是为了在层级图里找准它的位置。

## LangGraph：把流程画成一张有状态的图

### 从循环到图

回头看上一篇的循环：“调用模型”和“执行工具”两个步骤来回交替，由“有没有工具调用”决定下一步去哪里。如果把步骤画成节点、把跳转画成边，这个循环就是一张很小的图：

```text
START ──► model ──有工具调用──► tools
            ▲                    │
            └────────────────────┘
            │
            └──没有工具调用──► END
```

LangGraph 是 LangChain 团队开发的编排框架，有 Python 和 JavaScript 版本。它做的事情，就是让我们**用图来描述多步流程**，并由框架负责按图执行、保存状态。

### 三个核心概念：状态、节点、边

**状态（State）**：图里所有节点共享的一份数据，结构由我们定义。节点之间不直接传参，而是读写这份状态。

**节点（Node）**：一个普通函数，接收当前状态，返回**要更新的部分**，而不是完整的新状态。

**边（Edge）**：决定节点执行完之后去哪里。普通边总是去同一个节点；条件边调用一个函数，根据状态决定去向。`START` 和 `END` 是两个特殊节点，表示入口和结束。

节点只返回“要更新的部分”，那这部分怎样合并进状态？由每个状态字段的**归约函数**（reducer）决定。默认的归约函数直接用新值覆盖旧值；对话消息这类字段，则需要把新消息追加到列表末尾。

用 LangGraph 把上一篇的循环写出来：

```python
from langchain_anthropic import ChatAnthropic
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

tools = [search_wardrobe, retrieve_techniques]
model = ChatAnthropic(model="claude-opus-5").bind_tools(tools)


def call_model(state: MessagesState) -> dict:
    # Return only the update; the messages reducer appends it to the history.
    return {"messages": [model.invoke(state["messages"])]}


builder = StateGraph(MessagesState)
builder.add_node("model", call_model)
builder.add_node("tools", ToolNode(tools))
builder.add_edge(START, "model")
builder.add_conditional_edges("model", tools_condition)  # to "tools" or END
builder.add_edge("tools", "model")

graph = builder.compile(checkpointer=InMemorySaver())
```

对照上一篇的伪代码：

| 手写循环 | LangGraph |
| --- | --- |
| `messages` 列表 | `MessagesState` 中的 `messages` 字段，归约函数负责追加 |
| 调用 Messages API | `model` 节点 |
| 执行工具、拼 `tool_result` | `ToolNode` |
| `if stop_reason != "tool_use": break` | 条件边 `tools_condition` |
| `while` 循环 | `tools` 到 `model` 的边 |

`ChatAnthropic` 来自 LangChain：它把 Anthropic SDK 包装成 LangChain 统一的模型接口，`bind_tools` 把工具说明加进请求。LangChain 1.x 提供的 `create_agent`，内部正是构造了这样一张“模型节点 + 工具节点 + 条件边”的图。

### 图是怎样执行的：超步

LangGraph 的执行模型借鉴了 Google 的 Pregel 图计算系统，按**超步**（super-step）推进：

1. 一个超步里，所有被激活的节点执行，可以并行；
2. 这些节点返回的更新，在超步结束时通过归约函数合并进状态；
3. 根据边，确定下一个超步要激活哪些节点；
4. 没有节点被激活时，执行结束。

以“用户问一句，模型调用一次工具后回答”为例：

| 超步 | 执行的节点 | 状态中的 messages 变化 | 下一步 |
| --- | --- | --- | --- |
| 1 | `model` | 追加一条带工具调用的 AI 消息 | 条件边：有工具调用 → `tools` |
| 2 | `tools` | 追加工具结果消息 | 普通边 → `model` |
| 3 | `model` | 追加最终回答 | 条件边：没有工具调用 → `END` |

如果一个节点通过边同时指向两个节点，这两个节点会在下一个超步里并行执行，它们对同一字段的更新由归约函数合并。这也是归约函数必须明确定义的原因。

### 检查点：暂停与恢复

编译时传入的 `checkpointer`，会在每个超步结束后保存一份状态快照，按对话线程（thread）区分。这带来了手写循环不容易得到的能力：

- **中断等待人工确认**：节点里调用 `interrupt()`，图的执行暂停，状态保存下来；之后用 `Command(resume=...)` 带着人的答复恢复执行。
- **进程重启后继续**：状态存在 PostgreSQL 等持久化的检查点里，换一个进程也能从断点继续。
- **回看历史状态**：每个超步的快照都保存着，可以查看或从某个历史点重新执行。

`InMemorySaver` 只把快照存在内存里，用于开发；生产环境会换成数据库实现。

**LangGraph 的核心价值在于“状态化的流程”**：当流程有多个分支、需要并行、可能暂停几小时等人确认、中途进程可能重启时，它把这些复杂度收进了框架。

## Google ADK：以 Agent 为单位组织应用

Google 的 Agent Development Kit（ADK）是另一种编排框架，有 Python、Go、Java、TypeScript 版本。它为 Gemini 做了优化，但设计上不限定模型。

和 LangGraph 从“图”出发不同，ADK 从“Agent”出发。最小的 ADK 程序就是声明一个 Agent：

```python
from google.adk import Agent

root_agent = Agent(
    name="stylist",
    model="gemini-2.5-flash",
    instruction="You are a friendly stylist. Use the tools to look up the user's wardrobe.",
    tools=[search_wardrobe],
)
```

一个 Agent 就是“指令 + 模型 + 工具”，工具循环由 ADK 的运行时负责。围绕 Agent，ADK 2.x 提供了一整套运行环境：

| 概念 | 作用 |
| --- | --- |
| Agent | 指令、模型、工具的组合，可以把任务委派给其他 Agent |
| Workflow | 用图的方式编排多个 Agent，支持路由、循环、重试 |
| Runner | 执行 Agent，产生事件流 |
| Session / State | 保存对话与状态 |
| Event | 模型输出、工具调用、状态变更都以事件形式记录 |
| 工具确认 | 执行某个工具前要求人工确认 |

此外还有开发用的 Web 界面、评测工具，以及把 Agent 发布为 MCP 服务等能力。

**ADK 更像一个“Agent 应用框架 + 运行时”**：它不只提供编排结构，还规定了 Agent 怎样组织、会话怎样保存、事件怎样观察。选择 ADK，意味着接受它对应用结构的这套约定。

## 放在一起比较

| | Anthropic SDK | Google Gen AI SDK | Spring AI | LangGraph | Google ADK |
| --- | --- | --- | --- | --- | --- |
| 层级 | 厂商 SDK | 厂商 SDK | 应用框架 | 编排框架 | 编排框架 + 运行时 |
| 主要语言 | Python、TS、Java、Go 等 | Python、JS、Go、Java | Java | Python、JS | Python、Go、Java、TS |
| 模型 | Claude | Gemini | 多家 | 多家（经 LangChain 模型接口） | Gemini 优先，支持其他模型 |
| 工具循环 | 自己写，或用 Tool Runner | 默认自动执行 | `ToolCallingAdvisor` | 图中的节点与边 | Runner |
| 对话状态 | 应用保存 | 应用保存，或由 Interactions API 在服务端保存 | 应用保存，可用记忆 Advisor | 检查点 | Session |
| 暂停与恢复 | 自己实现 | 自己实现 | 自己实现 | 检查点 + 中断 | 工具确认、可恢复执行 |
| 新 API 能力的可用速度 | 最快 | 最快 | 等框架适配 | 等 LangChain 模型接口适配 | Gemini 能力快，其他模型等适配 |

用一句话区分它们：**厂商 SDK 让我们调用一家模型；Spring AI 让 Java 应用统一调用多家模型；LangGraph 和 ADK 让我们组织一个多步、有状态、可能要暂停的流程。**

## StyleAI 为什么直接使用 Anthropic SDK

回到 StyleAI 的主对话。结合前面几节，选择的理由可以对应到具体的层级：

1. **主对话的流程很短。** 它就是上一篇的那个循环，加上成本检查和 SSE 推送。用图来描述两个节点、一条条件边，框架带来的结构收益有限。
2. **需要长时间暂停、重启后恢复的部分，已经交给了任务队列。** 效果图生成是 StyleAI 里唯一耗时很长的流程，它运行在 Procrastinate 的 Worker 中（见[《用 PostgreSQL 做任务队列》](03-postgresql-task-queue.md)），状态保存在我们自己的表里。这正是 LangGraph 检查点最擅长的场景，但在 StyleAI 的架构里已经有了承担者。
3. **要尽早用上 Claude 的专有能力。** 自适应思考、服务端网页检索、提示缓存、结构化输出、服务端拒答回退，都首先在官方 SDK 中可用。多一层抽象，就要等一次适配。
4. **SSE 事件要和 API 的内容块精确对应。** 直接处理 SDK 的流式事件，映射关系最清楚，排查问题时也只需要看一层。

以下情况出现时，会重新评估 LangGraph 或 ADK：对话变成多个 Agent 分工协作；某些操作需要用户确认后才能继续，而且确认可能隔很久；或者后台学习流程变成有很多分支的长流程。后台 Agent 是否迁到 Anthropic 的 Managed Agents，按《技术选型》的计划在 M5 评估。

## 小结

这些名字之所以容易混在一起，是因为它们解决的都是“怎样用好大模型”，但解决的是不同层级的问题。厂商 SDK 是 HTTP API 的类型化封装，概念与 API 一一对应；Spring AI 在 SDK 之上统一多家模型，并融入 Spring 的编程方式；LangGraph 用状态、节点、边描述流程，靠检查点实现暂停与恢复；ADK 以 Agent 为单位，提供从编排到会话、事件的一整套运行时。

判断该用哪一层，可以回到上一篇的那个循环问自己：**我需要别人替我跑这个循环吗？我的流程是一个循环，还是一张需要保存状态的图？**

读完本文，可以试着回答：如果 StyleAI 增加一个功能，生成方案后要等用户在手机上确认“要不要花额度生成 4K 效果图”，用户可能半小时后才回复，你会把这个等待放在对话循环、任务队列，还是换成 LangGraph 的中断？

## 参考资料

- [Claude API：Messages API 与客户端 SDK](https://platform.claude.com/docs/en/api/overview)
- [Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python)
- [Google Gen AI Python SDK 文档](https://googleapis.github.io/python-genai/)
- [Gemini API：Interactions API](https://ai.google.dev/gemini-api/docs/interactions)
- [Spring AI 2.0.0 GA 发布说明](https://spring.io/blog/2026/06/12/spring-ai-2-0-0-GA-available-now/)
- [Spring AI 2.0：可组合的工具调用架构](https://spring.io/blog/2026/06/15/spring-ai-composable-tool-calling/)
- [Spring AI 参考文档：Chat Client API](https://docs.spring.io/spring-ai/reference/api/chatclient.html)
- [Spring AI 参考文档：Tool Calling](https://docs.spring.io/spring-ai/reference/api/tools.html)
- [LangGraph 文档：Graph API（状态、节点、边、超步）](https://docs.langchain.com/oss/python/langgraph/graph-api)
- [LangChain 文档：Agents 与 create_agent](https://docs.langchain.com/oss/python/langchain/agents)
- [Pregel：大规模图处理系统（SIGMOD 2010）](https://dl.acm.org/doi/10.1145/1807167.1807184)
- [Google ADK（Python）](https://github.com/google/adk-python)
