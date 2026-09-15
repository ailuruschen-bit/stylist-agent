# 技術選定

> 言語：[中文](../zh/02-tech-stack.md) · **日本語** · [English](../en/02-tech-stack.md)
> ステータス：ドラフト v0.1 · 更新：2026-09-15
> 中国語版が原本です。内容に差異がある場合は中国語版を優先します。
> 本書は StyleAI v2 の技術選定の結論と理由をまとめたものです。「要検証」の項目は、該当するマイルストーンでプロトタイプを使って確認してから確定します。

## 1. 選定の原則

1. **demo で検証済みのものを使う**：FastAPI、Next.js、ジョブキュー、SSE、Gemini による画像生成、ログインとクレジットは HackathonPJT で動作確認済みです。再利用してリスクを下げます。
2. **インフラは最小限に**：M0〜M6 の間は PostgreSQL とオブジェクトストレージだけに依存し、Redis、Kafka、Temporal などは導入しません。
3. **モデルは差し替え可能に**：LLM、画像生成モデル、ベクトルモデルはすべて内部インターフェース経由で接続し、比較評価や入れ替えをしやすくします。
4. **コンプライアンス優先**：サイトのボット対策や CAPTCHA は回避せず、著作権のある本文や画像は保存しません。
5. **Web のみ**：初回リリースは Web のみ。スマホはレスポンシブ対応でカバーし、ネイティブアプリはつくりません。

## 2. 全体像

| レイヤー | 採用 | 代替候補 | ステータス |
|---|---|---|---|
| フロントエンド | Next.js 16（App Router）+ React 19 + TypeScript | Remix、Vite + React | 確定 |
| UI | Tailwind CSS 4 + shadcn/ui | MUI、Chakra | 確定 |
| フロントの状態管理 | TanStack Query（サーバー状態）+ Zustand（ローカル UI 状態） | SWR、Redux | 確定 |
| 国際化 | next-intl（zh-CN / ja / en） | demo 独自の i18n を継続 | 確定 |
| バックエンド | Python 3.13 + FastAPI + Pydantic 2 | NestJS | 確定 |
| ORM とマイグレーション | SQLAlchemy 2（async）+ Alembic | SQLModel、Tortoise | 確定 |
| Agent の接続方式 | Anthropic Python SDK + 自前のツール呼び出しループ | Claude Agent SDK、Managed Agents、LangGraph | 確定 |
| メインモデル | Claude Opus 5 | Claude Fable 5.1 | 確定 |
| バックグラウンド用モデル | Claude Sonnet 5、Claude Haiku 4.5 | — | 確定 |
| 画像生成モデル | Gemini 3.1 Flash Image | Gemini 3 Pro Image、GPT Image、FLUX Kontext | 要検証（M3） |
| 切り抜き | BiRefNet（セルフホスト） | remove.bg、Photoroom API | 要検証（M1） |
| データベース | PostgreSQL 17 + pgvector | — | 確定 |
| ベクトルモデル | Voyage multimodal | Gemini Embedding、SigLIP（セルフホスト） | 要検証（M1） |
| ジョブキュー | Procrastinate（PostgreSQL ベース） | Celery + Redis、arq、Temporal | 確定 |
| リアルタイム配信 | SSE + PostgreSQL LISTEN/NOTIFY | WebSocket、Redis Pub/Sub | 確定 |
| オブジェクトストレージ | S3 互換（本番は Cloudflare R2）、ローカル開発はファイルシステム | AWS S3 | 確定 |
| デプロイ | Web：Vercel、API / Worker：東京リージョンのコンテナ、DB：東京リージョンのマネージド PostgreSQL | — | 要検証（M0） |
| 可観測性 | structlog + OpenTelemetry + Sentry + 自前の Agent トレース | Langfuse | 確定 |
| パッケージ管理 | pnpm 10（フロント）、uv（バックエンド） | npm、poetry | 確定 |

## 3. リポジトリ構成

```text
stylist-agent/
├── apps/
│   ├── web/                 # Next.js frontend
│   └── api/                 # FastAPI app, agent, tools, worker (same codebase, separate processes)
│       ├── app/
│       │   ├── api/         # HTTP routers (thin)
│       │   ├── services/    # business logic
│       │   ├── repositories/# database access
│       │   ├── agent/       # orchestrator loop, prompts, tool definitions
│       │   ├── providers/   # LLM / image / embedding / storage adapters
│       │   └── worker/      # background tasks (render pipeline, ingest, sweeps)
│       ├── migrations/      # Alembic
│       └── tests/
├── knowledge/               # human-curated technique cards (YAML), reviewed via PR
├── evals/                   # datasets and eval runners
├── infra/                   # docker compose, deployment configs
└── docs/                    # zh / ja / en documentation
```

フロントとバックエンドは同じリポジトリ（monorepo）に置きますが、それぞれの言語のツールチェーンを使い、Nx や Turborepo のような言語横断のビルドツールは入れません。API と Worker は同じコードを別プロセスで起動します。

## 4. フロントエンド

- **Next.js 16 + React 19**：demo で使用済み。Server Components はクローゼットやギャラリーのような読み取り中心の画面に向いています。
- **shadcn/ui**：コンポーネントのソースをリポジトリに置くため、StyleAI のビジュアルに合わせて自由に変更でき、ライブラリのテーマに縛られません。
- **API の型**：`openapi-typescript` で FastAPI の OpenAPI から TypeScript の型を生成し、手書きしません。
- **チャットのストリーミング表示**：フロントはバックエンドの SSE イベントを直接受け取ります（「開発規約」第 8 節）。Agent は Python 側にあるため、Node のバックエンドを前提とする Vercel AI SDK などは使いません。
- **テスト**：Vitest + Testing Library（コンポーネント）、Playwright（主要フローの E2E）。

## 5. バックエンド

- **Python 3.13 + FastAPI**：demo と同じで、AI 関連のエコシステムも最も充実しています。
- **レイヤー**：ルーター → サービス → リポジトリ。Agent のツールはサービス層だけを呼び、DB に直接アクセスしません。
- **ログイン**：demo のメール + パスワード、httpOnly Cookie のセッション方式を移植します。外部ログイン（Google、LINE）は今後の要件とします。
- **ツール**：依存関係は uv、lint とフォーマットは ruff、型チェックは mypy、テストは pytest。

## 6. Agent と LLM

### 6.1 モデルの役割分担

| 用途 | モデル | 理由 |
|---|---|---|
| 対話とオーケストレーション（Stylist Orchestrator） | `claude-opus-5` | 要望の理解、提案の組み立て、生成計画に最も高い判断力が必要 |
| 着用イメージのチェック（render_critique） | `claude-opus-5` | 正確な画像理解が必要。生成モデルとは別にして「自分で自分を採点する」状態を避ける |
| 雑誌学習、候補カードの作成 | `claude-sonnet-5` | 読む量が多く一定の判断力が必要。コストを抑えられる |
| クローゼットとカタログの一括タグ付け | `claude-haiku-4-5` | 量が多く出力の形が決まっているため速度重視。難しいサンプルは Sonnet 5 に回す |

モデル ID は設定ファイルにまとめ、業務コードにモデル名を直接書きません。

### 6.2 接続方式：Messages API + 自前のループ

| 方式 | 結論 | 理由 |
|---|---|---|
| Anthropic SDK + 自前のループ | **採用** | ツールは自前の DB と業務ロジックに依存する。各ステップのイベントを Web フロントに正確に配信したい。コスト上限、監査、評価のフックを入れやすい |
| Claude Agent SDK | 不採用 | ファイルシステムやコード向けの設計で、組み込みツールが今回の用途に合わない |
| Managed Agents | メインの対話では当面不採用。M5 でバックグラウンド処理への利用を評価 | 定期実行は「雑誌学習」「ブランド巡回」に向くが、メインの対話は自前の DB や SSE と密に連携する必要がある |
| LangChain / LangGraph | 不採用 | ベンダー横断の抽象化は不要。フレームワークが一層増えるとデバッグコストが上がる |

### 6.3 使用する主な API 機能

- **適応的思考**（`thinking: {type: "adaptive"}`）+ `effort` の段階設定：対話は `high`、単純なタグ付けは `low`。
- **ストリーミング**：対話リクエストはすべてストリーミングにし、思考の要約とツール呼び出しをリアルタイムでフロントに送ります。
- **プロンプトキャッシュ**：システムプロンプト、ツール定義、テクニックカードの索引を前方に置き、バイト単位で安定させます。
- **構造化出力**：タグ付け、提案、生成計画は JSON Schema で出力を制約し、ツール定義では `strict` を有効にします。
- **サーバーツール**：`web_search` / `web_fetch` を使い、`allowed_domains` でブランド公式サイトと承認済みメディアのドメインに限定します。
- **サーバー側の拒否フォールバック**：Claude Opus 5 の推奨設定に沿って fallbacks を有効にし、一部のリクエストがそのまま失敗するのを防ぎます。

## 7. 画像生成

- **第一候補は Gemini 3.1 Flash Image**：demo で接続済み。高速・低コストで、複数の参照画像入力と直前の画像の編集に対応しており、多段階生成に向いています。
- **M3 で比較評価**：Gemini 3 Pro Image、OpenAI GPT Image、FLUX Kontext。評価軸は服の再現度、モデルの同一性、変わった着こなしの完成度、1 枚あたりのコストと時間、商用利用の条件です。
- **Provider インターフェース**：`generate(refs, prompt)` と `edit(image, refs, prompt, mask?)` の 2 つを中心にし、Agent はインターフェースだけを扱い、具体的なモデルを意識しません。
- **モデルライブラリ**：モデルの参照画像セットは画像生成モデルで一度だけ生成し、人の選別と類似度チェックを経て登録。以降は読み取り専用のアセットとして使います。

## 8. クローゼット登録：切り抜きとタグ付け

1. **切り抜きに生成モデルを使わない**：demo は画像生成モデルで切り抜いていたため、服のディテールが知らないうちに変わる可能性がありました。v2 では BiRefNet などのセグメンテーションモデルで背景を除去し、登録画像が元のピクセルのままになるようにします。
2. **色はアルゴリズムで算出**：切り抜き後のピクセルをクラスタリングして hex と比率を求めます。LLM は色の名前付け（「杢グレー」など）だけを担当します。
3. **その他の属性は LLM の画像理解でタグ付け**：Haiku 4.5 + 構造化出力。信頼度の低い項目は Sonnet 5 で再確認します。
4. **ベクトル**：画像とタグのテキストからそれぞれベクトルをつくって pgvector に保存し、「似たアイテム探し」や提案の検索に使います。

## 9. データとストレージ

- **PostgreSQL 17 + pgvector**：業務データとアイテム・カードのベクトル検索を同じ DB に置き、トランザクションの整合性をシンプルに保ちます。
- **ジョブキュー Procrastinate**：PostgreSQL ベースの非同期タスクライブラリ。リトライ、定期実行、ロックに対応し、多段階生成、クローゼット登録、ブランド巡回、雑誌学習をカバーします。並行処理が大きく増えたら Temporal への移行を検討します。
- **リアルタイム配信**：Worker が `LISTEN/NOTIFY` でイベントを発行し、API プロセスが SSE に変換してブラウザへ送ります。API が複数インスタンスになっても Redis は不要です。
- **オブジェクトストレージ**：元画像、切り抜き、各段階の生成物。本番は Cloudflare R2（転送料金なし）、ローカル開発はファイルシステムのアダプタ（demo の storage 抽象を継続）。

## 10. ブランドデータの取得

最初の市場は日本のため、ブランドカタログは各ブランドの**日本公式サイト**のデータを使います（「情報ソース一覧」参照）。

取得方法の優先順位：

1. **公式またはアフィリエイト経由の商品データ**（商品フィード、アフィリエイト API）：最も安定しており、コンプライアンス面でも安全。M4 までに経路を調査します。
2. **公開されている商品ページ**：robots.txt と利用規約を守り、アクセス頻度を抑えて、`web_fetch` または自前の取得処理で構造化データを読み取ります。
3. **やらないこと**：CAPTCHA の回避、ブラウザフィンガープリントの偽装、ボット対策の突破。

既知のリスク：大手ブランドの公式サイトは強いボット対策や動的レンダリングが多いと見込まれ、ページ取得が不安定になる可能性があります。そのためアフィリエイト経路の調査は M0 から始めます。

## 11. デプロイ（要検証 · M0）

| コンポーネント | 有力案 | 補足 |
|---|---|---|
| Web | Vercel | Next.js をネイティブにサポート。東京のエッジあり |
| API / Worker | 東京リージョンのコンテナ基盤（Fly.io `nrt` または AWS ECS `ap-northeast-1`） | ユーザーが日本にいるため、ユーザーと DB の近くに置く |
| PostgreSQL | 東京リージョンのマネージドサービス（Supabase または AWS RDS）。pgvector 対応が必須 | M0 で価格と運用コストを比較して決定 |
| オブジェクトストレージ | Cloudflare R2 | S3 互換 |
| 切り抜きサービス | オンデマンド GPU インスタンスまたはサーバーレス GPU | M1 で呼び出し量を見て決定 |

## 12. 可観測性と評価

- **ログ**：structlog で JSON 出力し、全経路に `request_id` と `trace_id` を付けます。秘密情報とユーザーのプライバシー情報はログに書きません。
- **トレース**：OpenTelemetry で HTTP、DB、外部 API 呼び出しをカバーします。
- **Agent トレース**：各ターンの推論、ツールの入出力、トークン、コスト、処理時間を DB に保存し、社内のトレース画面で確認します（demo の生成ログページを拡張）。
- **エラー監視**：Sentry（Web と API）。
- **評価**：`evals/` にデータセットと評価スクリプトを置きます。プロンプトやツールを変更したら CI で小規模なスモーク評価を実行し、各マイルストーンの終わりにフル評価を行います。

## 13. 要検証事項

| 項目 | マイルストーン | 検証方法 |
|---|---|---|
| デプロイ基盤と DB のホスティング | M0 | 東京リージョンでの価格、レイテンシ、運用コストを比較 |
| ブランドのアフィリエイト経路 | M0 から | ブランドごとに日本向けの商品データ経路と規約を調査 |
| 切り抜きモデル | M1 | 50 着のサンプルでエッジ品質とディテールの保持を比較 |
| ベクトルモデル | M1 | 似たアイテム検索の top-5 ヒット率 |
| 画像生成モデル | M3 | 第 7 節の評価軸で評価セットをブラインド評価 |
| バックグラウンド Agent を Managed Agents に移すか | M5 | 運用コストと制御しやすさを比較 |
