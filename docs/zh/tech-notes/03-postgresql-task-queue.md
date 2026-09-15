# 用 PostgreSQL 做任务队列：行锁、SKIP LOCKED 与 LISTEN/NOTIFY

> 语言：**中文** · 日本語（翻译中） · English（翻译中）
> 所属：[技术原理](README.md) · 更新：2026-09-16 · 实验代码：[labs/postgres-queue](../../tech-notes/labs/postgres-queue/)

用户上传一件衣服，后台要抠图、算颜色、调用模型打标，前后十几秒；生成一张多阶段效果图，要四十秒到两分钟。这些工作都不能放在 HTTP 请求里同步做完：请求会超时，用户也不该一直等着。

常见的做法是引入任务队列：Web 服务只负责“登记一个任务”，然后立刻返回；另外的 Worker 进程从队列里领取任务，在后台慢慢执行。

说到任务队列，我们往往先想到 Redis、RabbitMQ、Kafka 这类独立组件。StyleAI 在《技术选型》里选择了 Procrastinate，一个**只依赖 PostgreSQL** 的任务队列库。PostgreSQL 是关系数据库，它怎么当队列用？

本文只使用我们熟悉的关系数据库功能：一张表、事务、行锁。我们一步步搭出一个能工作的队列，在真实的数据库上观察每一步会出什么问题、怎么解决，最后再回到 Procrastinate，看它在这套机制上补了哪些东西。

本文实验使用 PostgreSQL 14 和 Python 的 psycopg 3，每个“Worker”使用独立的数据库连接，和真实部署中独立的 Worker 进程一样。生产环境计划使用 PostgreSQL 17；本文用到的 `FOR UPDATE SKIP LOCKED` 和 `LISTEN/NOTIFY`，在 9.5 版本就已经具备。实验代码见 [queue_lab.py](../../tech-notes/labs/postgres-queue/queue_lab.py)，下文的输出都来自实际运行。

## 一个任务队列要保证什么

先把需求说清楚。对 StyleAI 来说，一个合格的任务队列至少要做到四件事：

| 要求 | 如果做不到 |
| --- | --- |
| 任务不丢 | 用户上传的衣服永远停在“处理中” |
| 同一个任务不被两个 Worker 同时领取 | 同一张效果图生成两次，成本翻倍 |
| Worker 崩溃后，任务还能被重新执行 | 进程重启一次，任务就卡死 |
| 新任务到来时，Worker 能尽快开始 | 用户上传后要等很久才开始处理 |

下面我们逐条满足这些要求。

## 一张表就是一个队列

先建一张 `jobs` 表。每一行是一个任务，`status` 记录它走到了哪一步：

```sql
CREATE TABLE jobs (
    id      bigserial PRIMARY KEY,
    task    text NOT NULL,
    status  text NOT NULL DEFAULT 'todo',   -- todo -> doing -> done
    worker  text
);
```

“登记任务”就是插入一行：

```sql
INSERT INTO jobs (task) VALUES ('render_look_1'), ('render_look_2'), ('ingest_garment_3');
```

因为数据写进了表，第一条要求“任务不丢”自然满足：只要事务提交成功，任务就持久保存在数据库里。

“领取任务”最直接的写法，是先查出一个待处理的任务，再把它标记为处理中：

```sql
SELECT id, task FROM jobs WHERE status = 'todo' ORDER BY id LIMIT 1;
UPDATE jobs SET status = 'doing', worker = 'worker-A' WHERE id = 1;
```

只有一个 Worker 时，这样写没有问题。但我们会同时运行多个 Worker，问题就出在两条语句之间的空隙里：

```text
时间 →
worker-A:  SELECT → 得到 id=1              UPDATE id=1
worker-B:        SELECT → 也得到 id=1             UPDATE id=1
```

A 查出 `id=1` 之后、改状态之前，B 也执行了同样的查询。此时 `id=1` 的状态仍是 `todo`，所以 B 也拿到了它。两个 Worker 会各自生成一遍 `render_look_1`。

第二条要求没有满足。我们需要一种办法：**一个 Worker 看中某个任务时，别的 Worker 不能再拿走它。**

## 用行锁防止重复领取

关系数据库本来就有这种机制：行锁。在 `SELECT` 末尾加上 `FOR UPDATE`，查询在返回行的同时，会给这些行加上锁：

```sql
SELECT id, task FROM jobs
WHERE status = 'todo'
ORDER BY id
LIMIT 1
FOR UPDATE;
```

行锁会一直持有到**当前事务结束**（提交或回滚）。在此期间，其他事务如果也想用 `FOR UPDATE` 锁同一行，就必须等待。

于是 Worker 的处理流程变成：开启事务 → `SELECT ... FOR UPDATE` 领取任务 → 改状态、执行任务 → 提交事务并释放锁。

我们让两个 Worker 按这个流程运行。worker-A 先领取任务，并在持有锁的状态下“工作” 2 秒；worker-B 晚 0.3 秒开始领取：

```text
[1] FOR UPDATE without SKIP LOCKED: B starts 0.3s after A
  worker-A: waited 0.00s, got job 1 (render_look_1)
  worker-B: waited 1.71s, got job 2 (render_look_2)
  jobs afterwards:
    id=1 task=render_look_1     status=done   worker=worker-A
    id=2 task=render_look_2     status=done   worker=worker-B
    id=3 task=ingest_garment_3  status=todo   worker=-
```

重复领取的问题解决了：A 做了 1 号任务，B 做了 2 号任务。

但请看 B 的等待时间：**1.71 秒**。它启动时，2 号和 3 号任务一直空闲着，它却停在那里，直到 A 的事务结束才拿到任务。

把 B 这 1.71 秒里发生的事展开：

```text
worker-B 执行 SELECT ... WHERE status = 'todo' ORDER BY id LIMIT 1 FOR UPDATE
   │
   ├─ 按 id 顺序，第一个满足条件的是 id=1
   ├─ 尝试给 id=1 加锁 → 已被 worker-A 锁住 → 等待
   │        …… 约 1.7 秒 ……
   ├─ worker-A 提交，锁释放；id=1 的最新状态是 done
   ├─ 重新检查条件：id=1 不再是 todo，跳过
   └─ 继续往下找：id=2 满足条件，加锁成功，返回
```

在 PostgreSQL 默认的“读已提交”隔离级别下，等到锁之后，数据库会用这一行**最新提交的版本**重新检查 `WHERE` 条件，所以 B 最终没有拿到已完成的 1 号任务，结果是正确的。

问题在于等待。所有 Worker 都按同样的顺序查找，都会先撞上同一个被锁的行。**Worker 越多，排队越长，多个 Worker 实际上变成了一个接一个地工作。**

## SKIP LOCKED：跳过别人正在处理的任务

我们真正想要的行为是：遇到已经被锁住的任务，不要等，直接看下一个。

PostgreSQL 为此提供了 `SKIP LOCKED`：

```sql
SELECT id, task FROM jobs
WHERE status = 'todo'
ORDER BY id
LIMIT 1
FOR UPDATE SKIP LOCKED;
```

加上它之后，查询遇到无法立即加锁的行会直接跳过，不再等待。其余条件不变，再运行一次：

```text
[2] FOR UPDATE SKIP LOCKED: B starts 0.3s after A
  worker-A: waited 0.00s, got job 1 (render_look_1)
  worker-B: waited 0.00s, got job 2 (render_look_2)
```

B 的等待时间从 1.71 秒变成了 0。它跳过了被 A 锁住的 1 号任务，立即拿到 2 号任务。

PostgreSQL 文档专门说明了这个选项的定位：跳过被锁的行，得到的是一个“不完整”的数据视图，所以它不适合一般的查询；但对多个消费者同时读取一张队列式的表，它正好能避免锁争用。

**`FOR UPDATE` 保证一个任务只被一个 Worker 领取，`SKIP LOCKED` 让多个 Worker 互不等待。** 两者结合，第二条要求才算真正满足。

## 锁要持有多久：Worker 崩溃之后

前两个实验里，Worker 从领取任务到完成任务，一直在同一个事务里，锁也一直持有。这种写法有一个很吸引人的性质，我们用实验看一下：worker-A 领取 1 号任务，把状态改为 `doing`，事务还没提交，进程就崩溃了。

```text
[3] worker dies while its transaction is open
  worker-A claimed job 1 and set status=doing, transaction still open
  another connection sees job 1 status=todo (uncommitted change is invisible)
  worker-A connection closed without COMMIT
  jobs afterwards:
    id=1 task=render_look_1     status=todo   worker=-
```

连接断开时，PostgreSQL 会回滚这个没有提交的事务。`doing` 状态随之撤销，锁也释放了，1 号任务回到 `todo`，其他 Worker 可以重新领取。**第三条要求“崩溃后能重新执行”，由事务自动满足。**

不过输出的第二行也暴露了这种写法的问题：在 A 的事务提交之前，其他连接看到的 1 号任务仍然是 `todo`。前端想显示“效果图生成中”，却读不到这个状态。

更严重的是持续时间。StyleAI 的一个生图任务要一两分钟，这意味着：

- 每个正在执行的任务都占着一个数据库连接和一个打开的事务；
- 长时间不结束的事务，会妨碍 PostgreSQL 清理旧版本的行数据（VACUUM），表和索引会逐渐膨胀；
- 任务执行期间调用外部 API 的时间，全部算在事务里。

所以实际的队列通常换一种做法：**用一个很短的事务完成领取，立即提交，再在事务之外执行任务。** 领取可以写成一条语句，查找、加锁、改状态一次完成：

```sql
WITH candidate AS (
    SELECT id FROM jobs
    WHERE status = 'todo'
    ORDER BY id
    LIMIT 1
    FOR UPDATE SKIP LOCKED
)
UPDATE jobs SET status = 'doing', worker = 'worker-A'
FROM candidate
WHERE jobs.id = candidate.id
RETURNING jobs.id, jobs.task;
```

这条语句提交后，`doing` 状态对所有人可见，锁也立刻释放。但刚才那个“崩溃自动回滚”的保护也没有了。同样让 worker-A 在领取后崩溃：

```text
[5] claim in one short transaction, then the worker dies
  worker-A claimed job 1 (render_look_1); the claim is already committed
  worker-A process dies: no more heartbeats, job never finishes
  jobs right after the crash:
    id=1 task=render_look_1     status=doing  worker=worker-A
```

1 号任务停在了 `doing`，没有任何机制会把它改回来。我们需要自己判断：这个 `doing` 是“正在认真执行”，还是“执行它的 Worker 已经不在了”。

常用的办法是**心跳**。每个 Worker 定期更新一张 `workers` 表中自己的 `last_heartbeat`。如果某个 Worker 超过一段时间没有心跳，它名下处于 `doing` 的任务就被视为**停滞任务**（stalled job），可以重新放回队列。

实验中，我们把 worker-A 的心跳时间改成 45 秒前，模拟它崩溃后过了一段时间，再用 30 秒作为判断阈值：

```sql
SELECT jobs.id, jobs.task, workers.name
FROM jobs JOIN workers ON workers.name = jobs.worker
WHERE jobs.status = 'doing'
  AND workers.last_heartbeat < now() - interval '30 seconds';
```

```text
  stalled jobs (worker heartbeat older than 30s): [(1, 'render_look_1', 'worker-A')]
  jobs after retrying stalled jobs:
    id=1 task=render_look_1     status=todo   worker=-
```

两种领取方式各有取舍：

| | 长事务：领取到完成都在一个事务里 | 短事务：领取后立即提交 |
| --- | --- | --- |
| 崩溃后恢复 | 自动回滚，任务回到 `todo` | 需要心跳和停滞检测 |
| `doing` 状态 | 其他连接看不到 | 所有人可见 |
| 连接与事务占用 | 整个任务期间都占用 | 只在领取的瞬间占用 |
| 适合 | 很短的任务 | 耗时任务，StyleAI 的大多数任务 |

还有一点要注意：重新执行意味着**同一个任务可能执行不止一次**。比如 Worker 其实已经生成了图片，只是在写回结果之前崩溃了。所以任务本身要设计成可以安全重复执行，例如生图结果按任务编号保存，重复执行时覆盖而不是新增。

## 任务和业务数据在同一个事务里

用数据库做队列，还有一个独立消息队列很难提供的好处。

用户上传衣服时，我们要做两件事：在 `garments` 表里插入这件衣服，再登记一个入库任务。如果队列在 Redis 里，这是两个系统的两次写入，中间可能失败：衣服记录写进了数据库，任务却没有发出去；或者任务发出去了，数据库事务却回滚了，Worker 去处理一件不存在的衣服。

队列就在同一个数据库里时，两次写入可以放进同一个事务。实验中，第一次上传在事务里写了衣服和任务，然后回滚；第二次正常提交：

```text
[6] enqueue a job in the same transaction as business data
  garments: [(2, 'navy shirt')]
  jobs:     [(5, 'ingest_garment_2', 'todo')]
```

回滚的那次，衣服和任务都没有留下；提交的那次，两者同时存在。**任务和它依赖的数据要么一起生效，要么一起消失。**

输出里的编号也值得看一眼：衣服的 `id` 是 2，任务的 `id` 是 5。回滚撤销了行数据，但序列（`bigserial` 背后的计数器）已经分配出去的值不会退回。编号出现空洞是正常现象，业务逻辑不能假设编号连续。

## LISTEN/NOTIFY：新任务到了，叫醒 Worker

现在还剩最后一条要求：新任务来了，Worker 要尽快开始。

最简单的办法是轮询：Worker 每隔几秒查一次表。间隔太长，任务要等；间隔太短，大量空查询白白消耗数据库。

PostgreSQL 提供了一个轻量的通知机制。一个连接执行 `LISTEN 频道名` 订阅频道，另一个连接执行 `NOTIFY 频道名, '内容'`（或调用函数 `pg_notify`）发出通知，所有正在监听的连接都会收到。

我们用实验观察它的三个关键行为：

1. 在任何连接开始监听**之前**，先发一条通知 `sent-before-listen`；
2. 监听开始后，在一个事务里插入任务并发通知，然后**回滚**；
3. 再在一个事务里插入任务并发通知，**等待 1 秒后提交**。

```text
[4] LISTEN/NOTIFY: rollback, commit, and a listener that is not connected yet
  pg_notify called at 0.01s, COMMIT at about 1.02s
  listener received 'from-committed-tx' at 1.02s
```

监听方只收到了一条通知。对照三个步骤：

| 步骤 | 结果 | 说明 |
| --- | --- | --- |
| 监听前发出的通知 | 没有收到 | 通知不会保存，发出时没人在听就丢失了 |
| 回滚事务里的通知 | 没有收到 | 通知随事务回滚一起撤销 |
| 提交事务里的通知 | 在 1.02 秒收到 | 调用发生在 0.01 秒，但**提交时**才送达 |

这和 PostgreSQL 文档的描述一致：事务内发出的通知在提交后才投递；通知不持久化；同一事务里频道和内容完全相同的通知只投递一次；默认内容上限是 8000 字节。

这些特性决定了 LISTEN/NOTIFY 在队列里的角色：**它只是一个“有新任务了”的提醒，任务本身仍以表里的数据为准。** 提醒可能丢失（比如 Worker 正在重连），所以 Worker 仍然保留一个较长间隔的轮询作为兜底。提交后才送达这一点正好符合需要：Worker 被叫醒时，任务行一定已经可以查到。

到这里，四条要求都有了对应的机制：

| 要求 | 机制 |
| --- | --- |
| 任务不丢 | 任务是表里的一行，随事务提交持久化 |
| 不被重复领取 | `FOR UPDATE SKIP LOCKED` |
| 崩溃后能重新执行 | 短事务领取 + 心跳 + 停滞任务检测 |
| 新任务尽快开始 | `LISTEN/NOTIFY` 提醒 + 轮询兜底 |

## 回到 Procrastinate：它补了哪些东西

Procrastinate 正是沿着这套思路实现的。对照它的数据库结构和 Worker 源码（本文参考 3.x 版本），可以找到前面每一个实验的对应物。

**任务表。** 任务存放在 `procrastinate_jobs` 表中，除了我们用过的状态字段，还有队列名 `queue_name`、任务名 `task_name`、参数 `args`、优先级 `priority`、计划执行时间 `scheduled_at`、已尝试次数 `attempts` 和领取它的 `worker_id`。状态有 `todo`、`doing`、`succeeded`、`failed`、`cancelled`、`aborting`、`aborted`。

**领取。** 领取任务的是一个数据库函数，核心就是我们写过的那条短事务语句：在候选任务上 `FOR UPDATE OF jobs SKIP LOCKED`，按优先级从高到低、编号从小到大挑一个，同一条语句把状态改为 `doing` 并记录 `worker_id`。

**提醒。** 表上有一个触发器，新任务插入时调用 `pg_notify`，同时发往“任意队列”频道和该队列自己的频道。Worker 默认开启 `listen_notify`，并以 5 秒为默认轮询间隔兜底：收到通知或到达轮询时间，二者先到哪个就去领取。

**心跳与停滞任务。** Worker 默认每 10 秒更新一次心跳，超过 30 秒没有心跳的 Worker 被视为失联。Procrastinate 提供查询停滞任务、将任务重新放回队列的接口，但不会自动重试，需要我们用一个定时任务调用它。这和实验 [5] 手动做的事情一致。

**重试。** 任务可以配置 `RetryStrategy`。失败后，任务被放回队列，并把 `scheduled_at` 推迟一段时间。等待秒数按下面的公式计算，其中 `attempts` 是已经尝试的次数：

```text
wait + linear_wait × attempts + exponential_wait ^ (attempts + 1)
```

**两种锁。** 这里的“锁”不是数据库行锁，而是任务上的一个字符串标签，用**部分唯一索引**（partial unique index）实现：

```sql
-- Only one job with a given lock may be running at a time.
CREATE UNIQUE INDEX ... ON procrastinate_jobs (lock) WHERE status = 'doing';
-- Only one job with a given queueing_lock may be waiting at a time.
CREATE UNIQUE INDEX ... ON procrastinate_jobs (queueing_lock) WHERE status = 'todo';
```

普通唯一索引要求整列不重复；加上 `WHERE` 之后，只在满足条件的行之间检查唯一性。于是，`lock` 相同的任务可以排队，但同一时刻只能有一个在执行；`queueing_lock` 相同的任务不能同时排队两个。StyleAI 可以用前者保证同一个方案不会被两个 Worker 同时生图，用后者防止用户连点按钮重复登记同一件衣服的入库任务。

**定时任务。** 用 cron 表达式声明周期任务，由 Worker 计算到期时间并登记任务。多个 Worker 同时运行时，数据库里“任务名 + 周期编号 + 计划时间”的唯一约束保证每个时间点只登记一次。StyleAI 的品牌巡检、停滞任务回收都会用它。

放到 StyleAI 的代码里，任务的声明方式大致如下。这段代码是设计示意，接口细节在 M0 按实际版本核对：

```python
import procrastinate

app = procrastinate.App(connector=procrastinate.PsycopgConnector())


@app.task(
    queue="render",
    retry=procrastinate.RetryStrategy(max_attempts=3, exponential_wait=4),
)
async def render_look(outfit_id: str, model_id: str) -> None:
    """Run the multi-stage render pipeline for one outfit."""
    await render_pipeline.run(outfit_id=outfit_id, model_id=model_id)


@app.periodic(cron="*/5 * * * *")
@app.task(queue="maintenance")
async def retry_stalled_jobs(timestamp: int) -> None:
    """Put jobs of workers that stopped sending heartbeats back into the queue."""
    ...


# Only one render per outfit may run at a time.
await render_look.configure(lock=f"outfit:{outfit_id}").defer_async(
    outfit_id=outfit_id, model_id=model_id
)
```

实验 [6] 演示的“任务与业务数据同一事务”，需要让 Procrastinate 登记任务时和 SQLAlchemy 使用同一个连接与事务。具体接法也放在 M0 验证。

## 什么时候该换成专门的消息队列

这套方案的代价同样来自“一切都在数据库里”：每次领取和完成都是一次数据库写入；已完成的任务行会不断累积，需要定期清理；每个 Worker 进程要保持一个监听连接。

对 StyleAI 首个版本的规模，这些都不是问题：任务量以“每个用户每天几十个”计，远低于 PostgreSQL 的承受能力。出现下面这些情况时，才需要重新评估：

- 任务量达到每秒上千，领取任务的写入开始和业务读写争抢数据库资源；
- 需要让多个独立服务订阅同一串事件，或者需要回放历史事件，这更接近 Kafka 这类日志型消息系统的场景；
- 流水线变得很长、需要跨天暂停和恢复，这时 Temporal 这类工作流引擎更合适。

## 小结

我们没有引入新的组件，只用表、事务和行锁，就得到了一个可靠的任务队列：`FOR UPDATE` 防止重复领取，`SKIP LOCKED` 让 Worker 互不等待，短事务加心跳处理崩溃，`LISTEN/NOTIFY` 负责及时提醒。任务与业务数据共用事务，是它相对独立消息队列最实在的优势。

读完本文，可以试着回答：如果一个生图任务在 Worker 崩溃前已经完成了三个阶段中的两个，重新执行时应该从头开始，还是从第三阶段继续？这需要在任务表之外记录什么？

## 参考资料

- [PostgreSQL 文档：SELECT 的锁定子句（FOR UPDATE、SKIP LOCKED）](https://www.postgresql.org/docs/current/sql-select.html#SQL-FOR-UPDATE-SHARE)
- [PostgreSQL 文档：显式锁定与行级锁](https://www.postgresql.org/docs/current/explicit-locking.html)
- [PostgreSQL 文档：事务隔离（读已提交下的重新检查）](https://www.postgresql.org/docs/current/transaction-iso.html)
- [PostgreSQL 文档：NOTIFY](https://www.postgresql.org/docs/current/sql-notify.html)
- [PostgreSQL 文档：LISTEN](https://www.postgresql.org/docs/current/sql-listen.html)
- [PostgreSQL 文档：部分索引](https://www.postgresql.org/docs/current/indexes-partial.html)
- [PostgreSQL 文档：VACUUM 与行版本清理](https://www.postgresql.org/docs/current/routine-vacuuming.html)
- [Procrastinate 文档](https://procrastinate.readthedocs.io/)
- [Procrastinate 源码：数据库结构 schema.sql](https://github.com/procrastinate-org/procrastinate/blob/main/procrastinate/sql/schema.sql)
- [Procrastinate 源码：Worker](https://github.com/procrastinate-org/procrastinate/blob/main/procrastinate/worker.py)
- [psycopg 3 文档：异步通知](https://www.psycopg.org/psycopg3/docs/advanced/async.html#asynchronous-notifications)
