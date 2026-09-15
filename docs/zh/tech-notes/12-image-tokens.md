# 图片的代价：视觉 token、尺寸与传输方式

> 语言：**中文** · 日本語（翻译中） · English（翻译中）
> 所属：[技术原理](README.md) · 更新：2026-09-16 · 实验代码：[labs/image-tokens](../../tech-notes/labs/image-tokens/)

StyleAI 是一个到处都在传图片的系统：

| 环节 | 传了几张图 |
| --- | --- |
| 衣橱打标 | 1 张（真值图） |
| 生图的每个阶段 | 模特参考 + 本阶段涉及单品的真值图 |
| 效果图检查 | 最终效果图 + 每件单品的真值图 |
| 对话过程 | 理想情况下 0 张 |

[《上下文与提示缓存》](07-context-and-prompt-caching.md)算过文字的账：十轮对话约 56 万输入 token。图片的单价要高得多——一张手机照片，可能抵得上几千字。

本文回答三个问题：一张图片到底算多少 token、应该在什么时候缩放到多大、多轮对话里的图片该怎么传。本文的规则来自 Claude 的官方文档，实验会用文档给出的对照表验证我们的实现是否正确。

## 模型怎么看一张图

模型不是按像素读图的，而是**按小方块（patch）读图**：图片被切成 28×28 像素的方块，每一块算一个视觉 token。

```text
tokens = ⌈宽 / 28⌉ × ⌈高 / 28⌉
```

以 1000×1000 的图为例：`⌈1000/28⌉ = 36`，所以是 36 × 36 = **1296 个 token**。

这个公式有两个直接推论：

1. **按面积计费，不是按文件大小。** 同样一张 1000×1000 的图，PNG 有 2 MB、JPEG 只有 200 KB，token 数完全一样。压缩文件大小只能减少传输时间，减不了费用。
2. **边长翻倍，代价变四倍。** 长边从 1024 缩到 512，token 数降到约四分之一。

## 分辨率档位与自动缩放

图片不会无限制地按原尺寸计费。每个模型有一个分辨率档位，超过上限的图片会在处理前被缩小：

| 档位 | 适用模型 | 长边上限 | 视觉 token 上限 |
| --- | --- | --- | --- |
| 高分辨率 | Claude 4.7 及之后的模型 | 2576 px | 4784 |
| 标准 | 其他模型 | 1568 px | 1568 |

缩放规则是：在保持宽高比的前提下，缩到同时满足两个上限的最大尺寸。所以一张 4K 照片在高分辨率档位上最多也就是 4784 个 token——**费用有上限，但这个上限并不低**。

注意，缩放发生在服务端。我们仍然应该在上传环节自己缩：

- 请求体更小，上传和传输更快；
- 缩放方式可控（我们知道自己缩成了多大，日志里也有记录）；
- 避免触发“一次请求超过 20 张图片时，每张图每边不得超过 2000 px”这类更严格的限制。

## 其他硬限制

| 项目 | 限制 |
| --- | --- |
| 支持格式 | JPEG、PNG、GIF、WebP；动图只使用第一帧 |
| 单张图片尺寸 | 最大 8000×8000 px |
| 单张图片大小 | 通过 Claude API 直接调用时，base64 编码后不超过 10 MB |
| 请求体大小 | 标准接口 32 MB |
| 每个请求的图片数 | 200k 上下文模型 100 张；其他模型 600 张 |
| 超过 20 张图片时 | 每张图每边不得超过 2000 px，否则整个请求被拒绝 |
| 图片与文字的顺序 | 图片放在文字之前效果更好 |
| 元数据 | 模型不读取图片的 EXIF 等元数据 |

最后一条对 StyleAI 有实际影响：拍摄方向记录在 EXIF 里，模型看不到。所以入库流程必须先按 EXIF 把图片转正，再交给模型，否则模型看到的是一张躺倒的衣服。

## 三种传图方式

| 方式 | 写法 | 适合 |
| --- | --- | --- |
| base64 内嵌 | `source: {type: "base64", media_type, data}` | 一次性的图片 |
| URL 引用 | `source: {type: "url", url}` | 公网可访问的图片 |
| 文件引用 | 先上传到 Files API，再用 `source: {type: "file", file_id}` | 会被反复使用的图片 |

这三者在 token 上没有区别——**视觉 token 只取决于尺寸**。区别在于请求体的大小。

这一点在多轮对话里很关键：对话历史每一轮都要完整重发（见[《上下文与提示缓存》](07-context-and-prompt-caching.md)）。如果图片是以 base64 内嵌的，**每一轮都会把整张图的字节重新传一遍**；换成 `file_id`，请求体里就只剩一个编号。

## 先验证规则实现得对不对

实验按上面的公式和缩放规则写了一份实现，并用官方文档里给出的对照表检查：

```text
[1] check the rule against the sizes listed in the documentation
  input         tier      docs size    ours          docs tok   ours  ok
  200x200       standard  200x200      200x200             64     64  yes
  1000x1000     standard  1000x1000    1000x1000         1296   1296  yes
  1092x1092     standard  1092x1092    1092x1092         1521   1521  yes
  1920x1080     standard  1456x819     1447x814          1560   1560  no ((1447, 814), 1560)
  1920x1080     high-res  1920x1080    1920x1080         2691   2691  yes
  2000x1500     standard  1269x952     1270x952          1564   1564  yes
  2000x1500     high-res  2000x1500    2000x1500         3888   3888  yes
  3840x2160     standard  1456x819     1447x814          1560   1560  no ((1447, 814), 1560)
  3840x2160     high-res  2576x1449    2576x1449         4784   4784  yes
```

**12 个用例的 token 数全部一致。** 两行标为 `no` 的，是缩放后的像素尺寸差了不到 1%（1447×814 对 1456×819）：这两个用例受 token 上限约束，实验用逐步收缩的方式逼近上限，官方实现的取整方式略有不同。由于计费按 token，结论不受影响。

## 常见照片值多少钱

```text
[2] photos StyleAI actually receives (high-resolution tier, claude-opus-5)
  image                           input       sent as       tokens  $/1000 imgs
  iPhone photo                    4032x3024   2193x1645       4661       23.30
  Android photo                   4000x3000   2193x1645       4661       23.30
  screenshot                      1290x2796   1188x2576       3956       19.78
  resized upload, long edge 2048  2048x1536   2048x1536       4070       20.35
  resized upload, long edge 1024  1024x768    1024x768        1036        5.18
  garment cutout in this lab      480x560     480x560          360        1.80
  rendered look 3:4 at 1K         768x1024    768x1024        1036        5.18
```

一张手机照片被缩到 2193×1645，用掉 4661 个视觉 token。作为对照，[《上下文与提示缓存》](07-context-and-prompt-caching.md)里估算的 StyleAI 全部稳定前缀（工具定义 + 系统提示词 + 技巧卡索引）约 9,000 token——**两张手机照片就相当于整份系统提示词。**

注意手机照片并没有被缩到长边 2576，而是 2193：先触发的是 4784 的 token 上限，不是长边上限。

## 一次效果图检查要花多少

检查请求要带上最终效果图和每件单品的真值图：

```text
[3] one render critique request: final image + truth images of each garment
  2 garments:   3774 visual tokens (final 1036 + truth 2738) = $0.0189 per request
  3 garments:   5143 visual tokens (final 1036 + truth 4107) = $0.0257 per request
  5 garments:   7881 visual tokens (final 1036 + truth 6845) = $0.0394 per request
```

一次检查约两到四美分，其中绝大部分是图片。这是[《系统架构》](../05-system-architecture.md)里“每个生图任务最多 8 次图像调用”这条预算之外，必须一并计入的成本。

## 上传时缩一下，能省多少

批量打标用的是便宜的模型，但数量大：

```text
[4] what pre-resizing saves for bulk tagging (claude-haiku-4-5)
  long edge   size          tokens  $/1000 imgs
  2048        1645x2193       4661        4.66
  1536        1536x2048       4070        4.07
  1024        1024x1365       1813        1.81
  768         768x1024        1036        1.04
  512         512x682          475        0.47
```

长边从 2048 缩到 1024，费用降到约 39%；再缩到 768，降到约 22%。

但不能一味缩小。图片太小会影响判断：材质（针织的纹路、牛仔的斜纹）、印花细节、缝线，这些正是打标要看的东西。**尺寸是准确率和成本之间的权衡，要用评测来定，而不是拍脑袋。** M1 的做法是：用同一批 200 件衣服，在 512、768、1024、1536 四个尺寸下各跑一遍打标，比较准确率曲线，选拐点。

## 多轮对话里的图片

```text
[5] resending images every turn vs referencing them
   1 turns, 3 images in history:    4107 visual tokens if resent each turn,   4107 if sent once
   5 turns, 3 images in history:   20535 visual tokens if resent each turn,   4107 if sent once
  10 turns, 3 images in history:   41070 visual tokens if resent each turn,   4107 if sent once
```

需要说明的是：这一栏比较的是**请求里携带的图片字节量**。视觉 token 本身也可以被提示缓存覆盖，命中时按缓存价计费；但每一轮把图片的 base64 重新塞进请求体，仍然会让请求变大、上传变慢。

StyleAI 的做法更直接：**对话历史里不放图片。** 模型在对话中需要的是衣服的标签和颜色数值（见[《衣服的颜色怎样变成数据》](02-garment-color-extraction.md)），不是图片本身。只有三个环节真正需要看图：打标、生图、效果图检查——它们都在任务队列里执行，不进入对话历史。

## StyleAI 的图片策略

| 环节 | 尺寸 | 传输方式 | 理由 |
| --- | --- | --- | --- |
| 上传保存 | 原图（长边上限 4096）+ 归一化图（长边 2048） | 对象存储 | 真值保留，算法升级后可以重算 |
| 衣橱打标 | 长边 1024（M1 校准） | 单次请求内嵌 | 一次性使用 |
| 生图参考 | 由生图模型的参考图规则决定 | provider 内部处理 | 各厂商规则不同，封装在 provider 里 |
| 效果图检查 | 效果图 1K + 各单品真值图 1024 | Files API `file_id` | 同一件衣服会被反复检查 |
| 对话历史 | 不放图片 | — | 避免每轮重发，也避免上下文膨胀 |

还有一条实现细节：**入库时按 EXIF 把图片转正并去除元数据**。模型不读 EXIF，转正必须由我们完成；去除元数据则是为了不把用户照片里的拍摄位置传给第三方。

## 隐私

Claude 的文档说明：通过 API 传入的图片是临时的，处理完成后即删除，不用于训练模型。即便如此，StyleAI 的隐私政策仍然要明确写出“用户上传的图片会发送给第三方模型服务进行处理”，并给出用户删除自己数据的入口。生图服务的条款要单独确认，不能假设与 Claude 一致。

## 小结

图片按面积计费：`⌈宽/28⌉ × ⌈高/28⌉`，超过档位上限时等比缩小。一张手机照片约 4,661 个视觉 token，抵得上 StyleAI 整份系统提示词的一半；长边缩到 1024，费用降到约 39%。

所以图片的成本控制有三件事：**上传时就缩到合适尺寸**（尺寸由评测确定）、**反复使用的图片用 file_id 引用**、**对话历史里用标签代替图片**。

读完本文，可以试着回答：用户衣橱里有 200 件衣服。如果对话时把候选单品的图片都给模型看，一次要多少视觉 token？换成只给标签和颜色数值，又是多少？

## 参考资料

- [Claude API：视觉能力（视觉 token、分辨率档位、限制）](https://platform.claude.com/docs/en/build-with-claude/vision)
- [Claude API：Files API](https://platform.claude.com/docs/en/build-with-claude/files)
- [Claude API：定价](https://platform.claude.com/docs/en/about-claude/pricing)
- [实验脚本：image_tokens_lab.py](../../tech-notes/labs/image-tokens/image_tokens_lab.py)
