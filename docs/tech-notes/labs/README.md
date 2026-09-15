# Tech note labs

> [中文](#中文) · [日本語](#日本語) · [English](#english)

## 中文

这里是《技术原理》系列文章的实验代码。文章中的输出都来自这些脚本的实际运行。实验不依赖 StyleAI 的应用代码，也不需要任何 API 密钥。

| 实验 | 对应文章 | 依赖 |
| --- | --- | --- |
| [latent-roundtrip](latent-roundtrip/) | 01 生成模型与分割模型 | torch、diffusers、pillow、numpy、scikit-image；首次运行会从 Hugging Face 下载约 330 MB 的 VAE 权重 |
| [garment-palette](garment-palette/) | 02 衣服的颜色怎样变成数据 | numpy、pillow、scikit-image |
| [postgres-queue](postgres-queue/) | 03 用 PostgreSQL 做任务队列 | psycopg 3、一个可以随意读写的 PostgreSQL |
| [vector-search](vector-search/) | 06 相似单品怎么找 | numpy |
| [context-cost](context-cost/) | 07 上下文与提示缓存 | 无（纯计算） |
| [sse-stream](sse-stream/) | 08 事件流与断线补发 | 无（标准库，会在 127.0.0.1:8421 临时监听） |
| [constrained-output](constrained-output/) | 09 结构化输出 | numpy |
| [eval-stats](eval-stats/) | 10 评测方法 | numpy |

作者的运行环境：macOS（Apple Silicon）、Python 3.13、PostgreSQL 14。

## 日本語

「技術解説」シリーズの実験コードです。記事中の出力はすべて、これらのスクリプトを実際に実行した結果です。StyleAI のアプリケーションコードや API キーは必要ありません。依存関係と実行方法は下記の English セクションと共通です。

## English

Lab code for the tech notes series. Every output quoted in the articles comes from running these scripts. The labs don't depend on StyleAI application code and need no API keys.

### Python environment

```bash
python3 -m venv .venv
```

```bash
.venv/bin/pip install numpy pillow scikit-image "psycopg[binary]" torch diffusers safetensors
```

### garment-palette

```bash
cd garment-palette && ../.venv/bin/python extract_palette.py
```

Writes `out/hoodie_cutout.png` and `out/hoodie_on_white.png`, which the latent-roundtrip lab reuses.

### latent-roundtrip

Run garment-palette first.

```bash
cd latent-roundtrip && ../.venv/bin/python vae_roundtrip.py
```

### postgres-queue

The lab drops and recreates tables named `jobs`, `workers` and `garments`. Use a throwaway database. One way is a temporary local cluster on port 55432:

```bash
initdb -D /tmp/queue-lab-pg -U lab --auth=trust
```

```bash
pg_ctl -D /tmp/queue-lab-pg -o "-p 55432 -c listen_addresses=localhost" -l /tmp/queue-lab-pg.log start
```

```bash
cd postgres-queue && DATABASE_URL=postgresql://lab@localhost:55432/postgres ../.venv/bin/python queue_lab.py
```

Stop the cluster when done:

```bash
pg_ctl -D /tmp/queue-lab-pg stop
```
