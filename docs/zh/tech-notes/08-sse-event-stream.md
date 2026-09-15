# 事件流：浏览器怎样实时看到 Agent 的每一步

> 语言：**中文** · 日本語（翻译中） · English（翻译中）
> 所属：[技术原理](README.md) · 更新：2026-09-16 · 实验代码：[labs/sse-stream](../../tech-notes/labs/sse-stream/)

用户发出一句“帮我搭一套周末出门的造型”，接下来会陆续发生这些事：

```text
0.3s   开始输出文字：“我先看看你衣橱里有哪些下装。”
0.8s   调用 search_wardrobe
1.5s   调用 retrieve_techniques
4s     方案卡片生成
6s     生图任务开始
40s    第一阶段效果图
70s    第二阶段效果图
95s    检查通过，最终图
```

如果等这一切结束再返回一个响应，用户要对着空白界面等一分半。我们需要的是：**服务器在过程中不断把新发生的事推给浏览器。**

本文说明 StyleAI 为什么用 SSE 而不是 WebSocket，SSE 在网络上到底长什么样，断线之后怎样不丢事件，以及多个服务实例时消息怎样找到正确的浏览器。

实验用标准库写了一个最小的 SSE 服务端与客户端，故意断开连接再重连，观察补发行为。实验代码见 [sse_lab.py](../../tech-notes/labs/sse-stream/sse_lab.py)，下文输出来自实际运行。

## 三种做法

| 做法 | 工作方式 | 代价 |
| --- | --- | --- |
| 轮询 | 浏览器每隔几秒问一次“有新内容吗” | 延迟与请求数成反比；多数请求是空的；文字流式输出做不了 |
| SSE（Server-Sent Events） | 浏览器发起一个普通的 HTTP GET，服务器保持连接不关闭，持续写入数据 | 只能服务器发给浏览器；文本协议 |
| WebSocket | 通过 HTTP 升级握手建立双向长连接 | 双向；需要独立的协议处理与网关配置；重连、心跳要自己实现 |

选择哪一种，取决于**数据往哪个方向流**。

StyleAI 的场景是明确的单向：用户的输入是一次普通的 `POST /messages` 请求，而需要持续推送的是 Agent 的输出。用户不需要在这条连接上频繁发消息给服务器。

SSE 因此更合适，而且它带来几个现成的好处：

- 它就是一个 HTTP 响应，`Content-Type: text/event-stream`，不需要额外的协议网关，Cookie 认证、日志、限流都和普通接口一致；
- 浏览器原生的 `EventSource` 会**自动重连**，并且自动带上上次收到的事件编号；
- 内容是纯文本，调试时用 `curl` 就能看到。

## 线上格式

SSE 的格式非常简单：一条事件由若干行字段组成，**空行表示一条事件结束**。

```text
id: 129
event: render.stage
data: {"renderId":"R-3391","stageNo":2,"imageUrl":"..."}

: keep-alive

id: 130
event: done
data: {"turnId":"T-77"}

```

| 字段 | 作用 |
| --- | --- |
| `id` | 事件编号。浏览器会记住最后一个，重连时通过 `Last-Event-ID` 请求头带回 |
| `event` | 事件名。前端按名称分发处理，不写则默认为 `message` |
| `data` | 数据。可以有多行，解析时按换行拼接；StyleAI 放一段 JSON |
| `retry` | 告诉浏览器重连前等待多少毫秒 |
| 以 `:` 开头的行 | 注释，解析器会忽略，用作心跳 |

这个格式决定了解析器的写法：按空行切分数据块，逐行读字段，遇到注释行跳过。实验里的 `SSEParser` 就是这样实现的，几十行代码。

## 断线之后会发生什么

实验的服务端按固定时间表产生 6 条事件，无论有没有客户端连着。客户端先正常连接，收到 2 条后故意断开：

```text
[1] connect from the beginning, then drop the connection after 2 events
  [ 0.00s] server client connected, Last-Event-ID=none
  [ 0.20s] server produced seq=1 message.delta
  [ 0.30s] client received seq=1 message.delta {"text":"我先看看你衣橱里有哪些下装。"}
  [ 0.60s] server produced seq=2 tool.started
  [ 0.60s] client received seq=2 tool.started {"tool":"search_wardrobe"}
  [ 0.60s] client disconnecting on purpose
```

在客户端离线的这段时间里，服务端继续产生了 seq=3 和 seq=4。现在客户端重新连接，但**不带任何编号**：

```text
[2] reconnect WITHOUT Last-Event-ID (client had seen up to seq=2)
  [ 1.51s] server client connected, Last-Event-ID=none
  [ 1.51s] server replaying 4 event(s): seq [1, 2, 3, 4]
  [ 1.51s] naive  received seq=1 message.delta ...
  [ 1.51s] naive  received seq=2 tool.started ...
  [ 1.51s] naive  received seq=3 tool.finished ...
  [ 1.51s] naive  received seq=4 render.stage ...
```

客户端没有说自己看到了哪里，服务端就只能二选一：**要么从头重发（客户端收到重复的 seq=1、2），要么只发之后的新事件（客户端永远缺了 seq=3、4）**。实验中的服务端选了前者，于是出现重复。两种选择都不对，因为信息不够。

带上编号，问题就不存在了：

```text
[3] reconnect WITH Last-Event-ID: 2
  [ 2.31s] server client connected, Last-Event-ID=2
  [ 2.31s] server replaying 4 event(s): seq [3, 4, 5, 6]
  [ 2.31s] client received seq=3 tool.finished ...
  [ 2.31s] client received seq=4 render.stage ...
  [ 2.31s] client received seq=5 render.stage ...
  [ 2.31s] client received seq=6 done {"turnId":"T-77"}
```

服务端从 seq=3 开始补发，不重复、不遗漏，客户端立刻追上了当前进度。浏览器原生的 `EventSource` 会自动记住最后一个 `id` 并在重连时带上这个请求头，所以**前端不需要为此写任何代码**，只要服务端给每条事件写 `id`，并能按编号补发。

输出最后还有一行：

```text
  [ 3.81s] client keep-alive comments ignored: 4
```

客户端一共收到了 4 条以 `:` 开头的心跳注释，解析器全部忽略，没有产生多余的事件。

## 服务端需要存什么

要能补发，服务端就必须**保存已经发出去的事件**，而不是产生后即扔。实验里用一个列表，StyleAI 用一张表：

```sql
CREATE TABLE agent_events (
    conversation_id uuid    NOT NULL,
    seq             bigint  NOT NULL,
    turn_id         uuid,
    type            text    NOT NULL,
    payload         jsonb   NOT NULL,
    created_at      timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (conversation_id, seq)
);
```

- **编号按会话递增**，不是全局递增，补发时按 `conversation_id` 加 `seq > $last` 查询即可。
- **先落库，再推送。** 事件与业务数据在同一个事务里提交：方案保存成功，`outfit.ready` 事件才存在。顺序反过来的话，用户可能看到一条指向不存在数据的事件。
- **保留时长**：事件用于补发和 trace，按会话保留一段时间后归档或删除。

这也解释了《系统架构》里的一个设计：生图 Worker 不直接把图片推给浏览器，而是写一条 `render.stage` 事件；推送由持有连接的 API 实例完成。

## 心跳、超时与代理

长连接会被各种中间环节悄悄切断：

| 环节 | 行为 | 对策 |
| --- | --- | --- |
| 反向代理、负载均衡 | 空闲超过一定时间关闭连接 | 定期发送 `: keep-alive` 注释行 |
| 缓冲式代理 | 攒够一批数据才转发，流式输出变成一次性到达 | 关闭该路径上的响应缓冲 |
| 手机切换网络、页面休眠 | 连接中断 | 依靠 `EventSource` 自动重连 + `Last-Event-ID` 补发 |
| 服务端部署更新 | 连接全部断开 | 同上；发布时事件已落库，补发即可 |

心跳还有一个作用：让服务端尽早发现客户端已经走了。写入失败时连接会报错，服务端就能释放资源。

## 多个服务实例时，事件怎样找到浏览器

生产环境有多个 API 实例，用户的 SSE 连接落在其中一个实例上，而产生事件的可能是另一个实例或 Worker 进程。

StyleAI 的做法是让数据库做这件事：

```text
Worker / 其他 API 实例
   │ 1. 写入 agent_events（事务提交）
   │ 2. NOTIFY conversation_<id>
   ▼
PostgreSQL
   │ 3. 通知送达所有 LISTEN 的连接
   ▼
持有该会话 SSE 连接的 API 实例
   │ 4. 读取 seq 大于已发送值的事件
   └─ 5. 写入 SSE 连接
```

通知只是“有新事件”的提醒，真正的数据来自表。即使通知丢失（例如实例正在重连数据库），事件也不会丢：下一次通知或兜底轮询会把它们一起带出来。这套机制的细节，见[《用 PostgreSQL 做任务队列》](03-postgresql-task-queue.md)中关于 `LISTEN/NOTIFY` 的部分。

## 前端的写法与两个限制

```javascript
const source = new EventSource(`/v1/conversations/${id}/events`, { withCredentials: true });

source.addEventListener("message.delta", (e) => appendText(JSON.parse(e.data)));
source.addEventListener("render.stage", (e) => updateRenderStage(JSON.parse(e.data)));
source.addEventListener("done", () => source.close());
```

浏览器原生的 `EventSource` 有两个限制：

1. **只能发 GET，不能自定义请求头。** 所以认证要用 Cookie（StyleAI 本来就用会话 Cookie），不能用 `Authorization` 头。
2. **同一域名下的并发连接数有限。** 每个会话一条连接、离开页面时关闭即可；如果将来需要同时订阅多个会话，改为一条连接多路复用。

需要自定义请求头或更复杂的控制时，可以改用 `fetch` 读取流式响应自己解析，代价是要自己实现重连与 `Last-Event-ID`。StyleAI 暂时不需要。

## 小结

SSE 就是一个不关闭的 HTTP 响应，格式简单到可以手写解析器。它适合 StyleAI 这种“服务器单向持续输出”的场景，还免费带来了浏览器端的自动重连。

真正需要我们设计的是**补发**：给每条事件编号、先落库再推送、按 `Last-Event-ID` 补发。实验说明了不带编号时服务端的两难——重复或遗漏，只能二选一。

读完本文，可以试着回答：用户在效果图生成到一半时刷新了页面，重新打开会话后应该看到什么？为了做到这一点，`GET /events` 之外还需要哪个接口？

## 参考资料

- [MDN：使用服务器发送事件](https://developer.mozilla.org/zh-CN/docs/Web/API/Server-sent_events/Using_server-sent_events)
- [MDN：EventSource](https://developer.mozilla.org/zh-CN/docs/Web/API/EventSource)
- [HTML 标准：Server-sent events（事件流格式与重连规则）](https://html.spec.whatwg.org/multipage/server-sent-events.html)
- [PostgreSQL 文档：NOTIFY](https://www.postgresql.org/docs/current/sql-notify.html)
