# 技術選定

> 言語：[中文](../zh/02-tech-stack.md) · **日本語** · [English](../en/02-tech-stack.md)
> ステータス：ドラフト v0.2 · 更新：2026-09-16
> 中国語版が原本です。内容に差異がある場合は中国語版を優先します。
> 本書は StyleAI v2 の技術選定の結論と理由をまとめます。「要検証」の項目は、該当するマイルストーンでプロトタイプを使って確認してから確定します。各技術の仕組みは `tech-notes` ブランチの[技術解説](https://github.com/ailuruschen-bit/stylist-agent/tree/tech-notes/docs/zh/tech-notes)（中国語）を、システムとしての組み合わせ方は[「システムアーキテクチャ」](05-system-architecture.md)を参照してください。
> 本書のモデル ID とライブラリのバージョンは 2026 年 9 月時点で確認したものです。

## 1. 選定の原則

1. **demo で検証済みのものを使う**：FastAPI、Next.js、ジョブ化された処理、SSE、Gemini の画像生成、ログインとクレジットは HackathonPJT で動作確認済みです。
2. **インフラは最小限に**：M0〜M6 の間は PostgreSQL とオブジェクトストレージだけに依存し、Redis、Kafka、Temporal などは導入しません。
3. **モデルは差し替え可能に**：LLM、画像生成、セグメンテーション、ベクトルモデルはすべて内部の provider インターフェース経由で接続します。
4. **API に近いほどよい**：モデルの機能更新は速いため、ベンダー公式 SDK を直接使い、中間に抽象フレームワークを挟みません。
5. **コンプライアンス優先**：サイトのボット対策や CAPTCHA は回避せず、著作権のある本文や画像は保存しません。
6. **Web のみ**：スマホはレスポンシブで対応し、ネイティブアプリはつくりません。

## 2. 全体像

| レイヤー | 採用 | 代替候補 | ステータス |
|---|---|---|---|
| フロントエンド | Next.js 16（App Router）+ React 19 + TypeScript | Remix、Vite + React | 確定 |
| UI | Tailwind CSS 4 + shadcn/ui | MUI、Chakra | 確定 |
| フロントのデータ | TanStack Query（サーバー状態）+ Zustand（ローカル UI 状態） | SWR、Redux | 確定 |
| 国際化 | next-intl（zh-CN / ja / en） | demo 独自の i18n を継続 | 確定 |
| バックエンド | Python 3.13 + FastAPI + Pydantic 2 | NestJS | 確定 |
| ORM とマイグレーション | SQLAlchemy 2（async）+ Alembic、ドライバは psycopg 3 | SQLModel | 確定 |
| Agent の接続 | Anthropic Python SDK + 自前のツール呼び出しループ | SDK の Tool Runner、LangGraph、Google ADK | 確定（Tool Runner は M0 で比較） |
| 対話・オーケストレーションのモデル | `claude-opus-5` | `claude-fable-5-1` | 確定 |
| バックグラウンド用モデル | `claude-sonnet-5`、`claude-haiku-4-5` | — | 確定 |
| 画像生成モデル | `gemini-3.1-flash-image`（Nano Banana 2） | `gemini-3-pro-image`（Nano Banana Pro）、GPT Image、FLUX.1 Kontext | 要検証（M3） |
| 画像生成 SDK | Google Gen AI SDK（`google-genai`） | — | 確定（Interactions API と generateContent は M0 で選定） |
| 切り抜き | BiRefNet（セルフホスト） | BiRefNet の他バリアント、商用の背景除去 API | 要検証（M1） |
| ベクトルモデル | `voyage-multimodal-3.5` | Gemini Embedding、SigLIP（セルフホスト） | 要検証（M1） |
| データベース | PostgreSQL 17 + pgvector | — | 確定 |
| ジョブキュー | Procrastinate 3.x（PostgreSQL ベース） | Celery + Redis、arq、Temporal | 確定 |
| リアルタイム配信 | SSE + イベントテーブル + PostgreSQL LISTEN/NOTIFY | WebSocket、Redis Pub/Sub | 確定 |
| オブジェクトストレージ | S3 互換：本番は Cloudflare R2、ローカルはファイルシステム | AWS S3 | 確定 |
| デプロイ | Web：Vercel、API / Worker：東京リージョンのコンテナ、DB：東京リージョンのマネージド PostgreSQL | — | 要検証（M0） |
| 可観測性 | structlog + OpenTelemetry + Sentry + 自前の Agent トレース | Langfuse | 確定 |
| パッケージ管理 | pnpm 10（フロント）、uv（バックエンド） | npm、poetry | 確定 |

## 3. リポジトリ構成

```text
stylist-agent/
├── apps/
│   ├── web/                 # Next.js frontend
│   └── api/                 # FastAPI app, agent, pipelines, worker (same codebase, separate processes)
│       ├── app/             # package layout: see "System architecture" section 4
│       ├── migrations/      # Alembic
│       └── tests/
├── services/
│   └── segmentation/        # BiRefNet inference service (GPU), deployed separately
├── knowledge/               # human-curated technique cards (YAML), reviewed via PR
├── evals/                   # datasets and eval runners
├── infra/                   # docker compose, deployment configs
└── docs/                    # zh / ja / en documentation
```

フロントとバックエンドは同じリポジトリに置き、それぞれの言語のツールチェーンを使います。Nx や Turborepo のような言語横断のビルドツールは入れません。API と Worker は同じコードを別プロセスで起動し、GPU と大きな重みが必要なセグメンテーションだけ別デプロイにします。

## 4. フロントエンド

| 選択 | 理由 | 注意点 |
| --- | --- | --- |
| Next.js 16 + React 19 | demo で使用済み。Server Components はクローゼットや提案一覧のような読み取り中心の画面に向く | 対話画面は操作が多いため、全体をクライアントコンポーネントとして実装 |
| Tailwind CSS 4 + shadcn/ui | コンポーネントのソースがリポジトリにあり、StyleAI のビジュアルに合わせて変更できる | デザイントークンを一箇所で定義し、コンポーネントに色の値を書かない |
| TanStack Query | サーバーデータのキャッシュ、再取得、楽観的更新 | SSE イベント到着時に該当クエリのキャッシュを更新 |
| Zustand | 入力欄やパネルの開閉などローカル状態 | サーバーデータは置かない |
| next-intl | 三言語の文言、日付と通貨の書式 | 価格は日本円で統一表示 |
| openapi-typescript | バックエンドの OpenAPI から型を生成し、契約を一致させる | 生成物はリポジトリにコミットし、CI で古くないか検査 |

**SSE クライアント**：ブラウザ標準の `EventSource` は GET のみでカスタムヘッダーを付けられません。StyleAI のイベント API は GET で Cookie 認証なので `EventSource` をそのまま使え、再接続時のみ `Last-Event-ID` が自動で付きます。

**テスト**：Vitest + Testing Library（コンポーネント）、Playwright（アップロード登録、対話での提案、着用イメージ確認の 3 フロー）。

## 5. バックエンド

| 選択 | 理由 |
| --- | --- |
| Python 3.13 + FastAPI | demo と同じ。AI 関連 SDK と画像処理のエコシステムが最も充実し、async と OpenAPI を標準で扱える |
| Pydantic 2 | リクエスト・レスポンス、ツール入力、構造化出力を同じモデル定義で扱える |
| SQLAlchemy 2 async + psycopg 3 | psycopg 3 は async と LISTEN/NOTIFY に対応し、Procrastinate のコネクタでもあるため、全体で同じドライバを使える |
| Alembic | スキーマ変更をバージョン管理できる |
| uv | 依存解決とインストールが速く、ロックファイルで再現できる |
| ruff + mypy | フォーマット、lint、型チェック |

**ログイン**：demo のメール + パスワードとセッション Cookie を移植します。外部ログイン（Google、LINE）は今後の要件です。

## 6. Agent と LLM

### 6.1 モデルの役割分担

| 用途 | モデル | effort | 理由 |
|---|---|---|---|
| 対話とオーケストレーション | `claude-opus-5` | high | 要望の理解、提案の組み立て、ツールの選択に最も高い判断力が必要 |
| 生成計画、着用イメージのチェック | `claude-opus-5` | high | 画像理解の精度が必要。生成モデルとは別にして自己採点を避ける |
| 雑誌学習、タグ付けの再確認 | `claude-sonnet-5` | medium | 読む量が多く判断も要るが、コストを抑えられる |
| クローゼットとカタログの一括タグ付け | `claude-haiku-4-5` | — | 件数が多く出力の形が決まっており、速度が効く |

モデル ID と effort は設定にまとめます。effort の初期値は M0 に評価セットで調整します。

### 6.2 接続方式

| 方式 | 結論 | 理由 |
|---|---|---|
| Anthropic SDK + 自前ループ | **採用** | ループ自体が短い。各コンテンツブロックを保存し SSE イベントに変換する必要がある。各周回で予算を確認する。サーバーツール併用時は `pause_turn` の処理が要る |
| Anthropic SDK の Tool Runner | M0 で比較 | 定型コードを減らせる。Python 版は現状 `pause_turn` を自動で継続しないため、イベントと予算の差し込み位置を満たせるか確認する |
| Claude Agent SDK | 不採用 | ファイルシステムやコード向けで、内蔵ツールが本プロダクトに合わない |
| Managed Agents | メイン対話では不採用。M5 にバックグラウンド用途を評価 | 定期実行はバックグラウンド Agent に向くが、メイン対話は DB と SSE に密結合 |
| LangGraph / Google ADK | 不採用 | メイン対話の流れが単純。長時間の中断・再開はジョブキューが担っている。抽象が増えると Claude の新機能の利用が遅れる |
| Spring AI | 対象外 | Java 向けフレームワークで、StyleAI のバックエンドは Python |

各方式の仕組みと違いは技術解説「Agent の接続とは何か」「モデル SDK と Agent フレームワーク」を参照してください。

### 6.3 使用する API 機能

| 機能 | 用途 |
| --- | --- |
| 適応的思考 + effort | 対話と計画で有効化。用途ごとに effort を設定 |
| ストリーミング | すべての対話リクエスト。StyleAI 独自の SSE イベントに変換 |
| プロンプトキャッシュ | ツール定義、システムプロンプト、カード索引を前方に置き安定させる |
| 構造化出力 | タグ付け結果、提案カード、生成計画、チェック結果 |
| `strict` ツール定義 | すべてのカスタムツール |
| サーバーツール `web_search` / `web_fetch` | ブランド検索（`allowed_domains` でブランド公式に限定）、雑誌学習（承認済みソースに限定） |
| サーバー側の圧縮 | 長い対話の古い履歴を自動要約 |
| サーバー側の拒否フォールバック | Claude Opus 5 の推奨設定に沿って有効化 |

## 7. 画像生成

### 7.1 モデル

Gemini の現行の画像モデル（いずれも正式版）：

| モデル ID | 名称 | 参照画像の上限 | 出力解像度 |
| --- | --- | --- | --- |
| `gemini-3.1-flash-image` | Nano Banana 2 | 物体 10 + 人物 4 + スタイル 3 | 1K、2K、4K |
| `gemini-3-pro-image` | Nano Banana Pro | 物体 6 + 人物 5 | 1K、2K、4K |
| `gemini-3.1-flash-lite-image` | Nano Banana 2 Lite | 物体 14 | 0.5K、1K |

第一候補は `gemini-3.1-flash-image`：参照画像の枠が「モデル参照 + 複数の服」という組み合わせをカバーでき、3:4 に対応し、速度とコストが多段階生成に向きます。出力画像にはすべて SynthID の不可視ウォーターマークが入ります。

M3 で `gemini-3-pro-image`、OpenAI GPT Image、FLUX.1 Kontext を評価セットでブラインド比較します。評価軸は、服の再現度（真値画像との比較）、モデルの同一性、変わった着こなしの完成度、多段階編集後の一貫性、1 枚あたりのコストと時間、商用利用条件です。

### 7.2 API の形式

Gemini API には現在 2 つの呼び出し方があります。Google が推奨する新しい Interactions API（サーバー側に対話が保存され、`previous_interaction_id` で継続）と、引き続き完全にサポートされる `generateContent` です。M0 でどちらかを選定します。確認すべき点：

- サーバー側に保存されることがユーザー画像のプライバシーに与える影響と、保存を無効にした場合の多段階編集の書き方；
- 「前段階の出力を入力にする」実装が、2 つの方式でコストと一貫性にどう影響するか。

### 7.3 Provider インターフェース

```python
class ImageProvider(Protocol):
    async def generate(self, refs: list[ImageRef], prompt: str, spec: OutputSpec) -> ImageResult: ...
    async def edit(self, image: ImageRef, refs: list[ImageRef], prompt: str, spec: OutputSpec) -> ImageResult: ...
```

`ImageResult` には画像、モデル、所要時間、課金用の使用量が入ります。生成パイプラインはこのインターフェースだけに依存します。

## 8. クローゼット登録：切り抜き、色、タグ付け

**切り抜きにはセグメンテーションを使い、生成モデルは使いません。** 生成モデルの出力ピクセルは描き直されたもので、質感や柄、文字が変わってしまいます。登録では、色の抽出・タグ付け・着用イメージのチェックの基準となる信頼できる真値画像が必要です。

| 候補 | 内容 | ライセンス |
| --- | --- | --- |
| BiRefNet（general / HR / matting / lite など） | 高解像度の二分セグメンテーション。輪郭が良く、alpha matte も出力できる | MIT |
| 商用の背景除去 API | GPU のデプロイが不要 | 各サービスの規約と料金 |

M1 で実写 50 着を使い、輪郭の質、ディテールの保持、所要時間を比較し、採用する重みのライセンスも確認します。

**色はアルゴリズムで計算**：服のピクセルのみを対象 → CIELAB 空間 → マスク付きぼかしの後に k-means → CIEDE2000 で同じ生地の濃淡を統合 → 比率でメインカラーを絞り込み → 元のピクセルからアクセントカラーを抽出 → 参照色表で命名。hex、CIELAB 値、比率を出力します。詳細は技術解説「服の色をデータにする」を参照してください。

**その他の属性はビジョンモデルでタグ付け**：Haiku 4.5 + 構造化出力。確信度の低い項目は Sonnet 5 で再確認します。

**ベクトル**：`voyage-multimodal-3.5` で服の画像とタグテキストのベクトルを作り、類似アイテム検索と提案検索に使います。M1 に類似アイテム検索の top-5 ヒット率で他候補と比較します。

## 9. データ、ジョブキュー、リアルタイム配信

**PostgreSQL 17 + pgvector**：業務データ、ジョブキュー、イベント、ベクトル検索を同じデータベースに置き、ジョブと業務データを同一トランザクションでコミットできるようにします。

**Procrastinate 3.x** の仕組みと StyleAI での使い方：

| 仕組み | Procrastinate の実装 | StyleAI での用途 |
| --- | --- | --- |
| ジョブの取得 | DB 関数内の `FOR UPDATE SKIP LOCKED` と、同一文での doing 更新 | 複数 Worker の並行処理 |
| 新着の通知 | 挿入時のトリガーで `pg_notify`。Worker が LISTEN し、既定 5 秒のポーリングで補完 | 登録と生成を早く開始する |
| Worker のハートビート | 既定 10 秒。30 秒以上途絶えたら失踪とみなす | 定期ジョブで停滞ジョブを回収し、未完了の段階から再開 |
| リトライ | `RetryStrategy`：固定、線形、指数の待機 | 外部 API の失敗時 |
| `lock` | 部分ユニークインデックス：同じ lock は同時に 1 件のみ doing | 同じ提案の生成ジョブを同時に 1 つに |
| `queueing_lock` | 部分ユニークインデックス：同じ値は同時に 1 件のみ todo | 登録ジョブの重複登録を防ぐ |
| 定期ジョブ | cron 式。DB のユニーク制約で重複登録を防止 | ブランド巡回、雑誌学習、停滞ジョブの回収 |

キューの分割：`ingest`、`render`、`scout`、`learn`、`maintenance`。`render` の Worker は別デプロイにし、時間のかかる生成が登録処理を圧迫しないようにします。

**リアルタイム配信**：イベントを `agent_events` に書いてから `NOTIFY`。API インスタンスが LISTEN して SSE で配信し、再接続時は `Last-Event-ID` からテーブルで補完します。

仕組みと実験は技術解説「PostgreSQL でジョブキューをつくる」を参照してください。

## 10. ブランドデータの取得

最初の市場は日本なので、ブランドカタログは各ブランドの日本公式サイトのデータを使います（「情報ソース一覧」参照）。優先順位：

1. **公式またはアフィリエイト経由の商品データ**：最も安定し、コンプライアンス面でも安全。M0 からブランドごとに調査します。
2. **公開されている商品ページ**：robots.txt と利用規約を守り、頻度を抑えて構造化データを読み取ります。
3. **やらないこと**：CAPTCHA の回避、フィンガープリントの偽装、ボット対策の突破。

既知のリスク：大手ブランドのサイトは強いボット対策と動的レンダリングが見込まれ、ページ取得が不安定になる可能性があります。アフィリエイト経路もなく、ページも安定して読めないブランドは、対抗手段を取るのではなく第一弾から入れ替えます。

## 11. デプロイ（要検証 · M0）

| コンポーネント | 有力案 | 補足 |
|---|---|---|
| Web | Vercel | Next.js をネイティブにサポート |
| API / Worker | 東京リージョンのコンテナ基盤（Fly.io `nrt` または AWS ECS `ap-northeast-1`） | ユーザーと DB に近い。SSE の長時間接続に対応が必要 |
| PostgreSQL | 東京リージョンのマネージドサービス（Supabase または AWS RDS）。pgvector 必須 | M0 で価格、接続数上限（LISTEN 用）、運用コストを比較 |
| オブジェクトストレージ | Cloudflare R2 | S3 互換、転送料金なし |
| セグメンテーション | オンデマンド GPU またはサーバーレス GPU | M1 に呼び出し量を見て決定 |

## 12. 可観測性と評価

- **ログ**：structlog の JSON 出力。全経路に `request_id` と `trace_id` を付け、秘密情報とプライバシー情報は記録しません。
- **トレース**：OpenTelemetry で HTTP、DB、外部 API をカバーし、`trace_id` はジョブ引数で Worker にも渡します。
- **Agent トレース**：「システムアーキテクチャ」第 12 節を参照。
- **エラー監視**：Sentry（Web と API）。
- **評価**：`evals/` にデータセットと評価スクリプトを置きます。プロンプトやツールの変更時は CI で小規模なスモーク評価、各マイルストーンの終わりにフル評価を実行します。評価セットは、服のタグ付けラベルセット、提案のブラインド評価セット、着用イメージの再現度評価セットです。

## 13. バージョン基準

| コンポーネント | バージョン |
| --- | --- |
| Node.js / pnpm | 24 LTS / 10 |
| Next.js / React / Tailwind CSS | 16 / 19 / 4 |
| Python / uv | 3.13 / 最新の安定版 |
| FastAPI / Pydantic / SQLAlchemy | 最新の安定版 / 2 / 2 |
| psycopg / Procrastinate | 3 / 3.x |
| PostgreSQL / pgvector | 17 / 最新の安定版 |
| anthropic / google-genai | 最新の安定版をロックファイルで固定 |

## 14. 要検証事項

| 項目 | マイルストーン | 検証方法 |
|---|---|---|
| 自前ループと Tool Runner | M0 | 同じシナリオを両方で実装し、コード量とイベント・予算の差し込み位置を比較 |
| Interactions API と generateContent | M0 | 多段階編集の書き方、プライバシー設定、コスト |
| デプロイ基盤と DB のホスティング | M0 | 東京リージョンでの価格、レイテンシ、接続数、運用コスト |
| 第三者モデルサービスのデータ規約 | M0 | ユーザー画像の学習利用の有無と保存期間を確認 |
| ブランドのアフィリエイト経路 | M0 から | ブランドごとに日本向けの商品データ経路と規約を調査 |
| 切り抜きモデル | M1 | 50 着で輪郭品質、ディテール保持、所要時間、ライセンスを比較 |
| ベクトルモデル | M1 | 類似アイテム検索の top-5 ヒット率 |
| 色抽出のしきい値 | M1 | 200 着のラベルセットでメインカラーとアクセントのしきい値を調整 |
| 画像生成モデル | M3 | 7.1 節の軸でブラインド評価 |
| バックグラウンド Agent を Managed Agents に移すか | M5 | 運用コストと制御しやすさを比較 |
