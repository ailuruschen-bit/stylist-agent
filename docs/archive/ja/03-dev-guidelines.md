# 開発規約

> 言語：[中文](../zh/03-dev-guidelines.md) · **日本語** · [English](../en/03-dev-guidelines.md)
> ステータス：ドラフト v0.2 · 更新：2026-09-16
> 中国語版が原本です。内容に差異がある場合は中国語版を優先します。
> すべてのコントリビューター（AI コーディングアシスタントを含む）は本書に従ってください。規約自体の変更も PR で議論してからマージします。モジュール構成とデータの流れは[「システムアーキテクチャ」](05-system-architecture.md)を参照してください。

## 1. 言語ルール

| 場面 | 言語 |
|---|---|
| チーム内のコミュニケーション、Issue と PR の議論 | 中国語中心 |
| `docs/` のドキュメント | 中国語、日本語、英語の三言語。**中国語版が原本** |
| コードコメント、docstring | 英語 |
| 識別子（変数、関数、クラス、テーブル名、API フィールド、イベント名） | 英語 |
| コミットメッセージ、PR タイトル | 英語（Conventional Commits） |
| Agent のシステムプロンプト、ツールの説明、テクニックカード本文 | 英語（出力言語はユーザーに合わせる） |
| テクニックカードの用語 | `terms` フィールドに中日英の対訳 |
| UI の文言 | i18n で三言語。コンポーネントへのハードコードは禁止 |
| ユーザーに返すエラー | バックエンドはエラーコードと英語の message を返し、フロントがコードに応じて三言語の文言を表示 |
| ログ | 英語 |

**ドキュメントの同期ルール**：中国語のドキュメントを変更する PR では、日本語版と英語版も同時に更新します。翻訳が間に合わない場合は PR に明記し、該当する日本語・英語のドキュメント冒頭に「翻訳中」と記載し、`docs: sync translations` の Issue を作成して次の PR までに反映します。

## 2. ブランチとマージ

現在、長期に存在するブランチは 3 つです。

| ブランチ | 内容 | `main` へマージするか |
| --- | --- | --- |
| `main` | きれいな状態を保つ。企画段階ではリポジトリの説明のみ。正式開発の開始後にコードと確定版ドキュメントを置く | — |
| `draft` | 企画段階の検討用ドキュメント（企画書、技術選定、開発規約、情報ソース、システムアーキテクチャ。中日英） | 内容が固まってから整理してマージ |
| `tech-notes` | 学習用の技術解説記事と実験コード | マージしない |

- `main` は保護ブランチ。PR 経由でのみマージし、squash merge を使います。M0 開始時に GitHub で「CI 必須」「1 名以上の承認」「線形履歴」「強制プッシュ禁止」を有効にします。
- `draft` のドキュメントは検討中のため直接コミットしてよく、PR は必須ではありません。結論が安定したら正式版として整理し `main` へ入れます。
- `tech-notes` は長期の学習ブランチで、技術解説の記事と実験コードを置きます。正式な開発とは無関係で、**`main` にはマージしません**。正式ドキュメントの最新版を参照したいときは `main` から `tech-notes` へマージします。
- 機能ブランチ名：`<type>/<short-description>`。例：`feat/closet-upload`、`fix/sse-reconnect`。
  - type：`feat`、`fix`、`docs`、`refactor`、`test`、`chore`、`exp`（実験用。マージしなくてよい）。
  - 説明は小文字の英語とハイフンで、5 単語以内。
- 1 つの PR では 1 つのことだけ。変更は 400 行以内を目安にします（生成ファイル、ロックファイル、マイグレーションのスナップショットを除く）。大きな機能は依存順に複数の PR に分けます。
- マージ済みの機能ブランチは削除します。長く残っている `exp/` ブランチは毎月整理します。

## 3. コミット規約

[Conventional Commits](https://www.conventionalcommits.org/) に従います。

```text
<type>(<scope>): <summary in imperative mood>

<optional body: what and why, wrapped at 72 columns>

<optional footer: BREAKING CHANGE: ..., Refs: #123>
```

| 部分 | ルール |
| --- | --- |
| `type` | `feat`、`fix`、`docs`、`refactor`、`test`、`perf`、`chore`、`build`、`ci` |
| `scope` | `web`、`api`、`agent`、`render`、`closet`、`scout`、`learn`、`knowledge`、`evals`、`infra`、`docs`、`tech-notes` |
| summary | 英語の命令形、小文字始まり、句点なし、72 文字以内 |
| body | なぜ変更したか、何に影響するか。「何を変えたか」は diff が語る |
| footer | 互換性のない変更は `BREAKING CHANGE:`、Issue との関連は `Refs: #123` |

例：

```text
feat(closet): detect alternative wears during garment tagging

Tagging now returns wear options such as tied_waist and one_sleeve_off
based on category and closure type, so the agent can suggest them
without guessing.

Refs: #42
```

squash merge では PR タイトルが最終的なコミットの summary になるため、PR タイトルも本節のルールに従います。

## 4. Pull Request

### 4.1 PR の説明

リポジトリのテンプレート（`.github/pull_request_template.md`）を使い、最低限次を書きます。

1. 何をしたか、なぜしたか
2. どう確認したか（テスト、スクリーンショット、評価結果）
3. プロンプト、ツール、DB 構造、コスト、コンプライアンスへの影響
4. 三言語のドキュメントを同期したか

未完成の PR は Draft で作成します。

### 4.2 変更の種類ごとの確認事項

| 変更の種類 | 作成者が用意するもの | レビュアーが重点的に見る点 |
| --- | --- | --- |
| API | OpenAPI から生成した型の更新、旧フロントとの互換性の説明 | フィールド名、エラーコード、ページング、権限フィルタ |
| DB スキーマ | Alembic のマイグレーション、大きなテーブルでの所要時間とロックの説明 | 1 つ前のコードと互換か、インデックスは妥当か |
| プロンプト・ツール | 変更前後の評価結果、トレースの例 | ツール説明に「いつ使うか」が書かれているか、固定の生成プロンプトを入れていないか |
| 生成パイプライン | 10 件以上の提案の前後比較画像 | 服の再現、コストの変化 |
| UI | デスクトップとスマホのスクリーンショット、三言語の文言 | アクセシビリティ、ローディングとエラーの状態 |
| 外部データ取得 | robots と規約を確認した記録 | 保存してよいフィールドだけを保存しているか |
| 依存関係の更新 | 更新理由と変更点の要旨 | ライセンス、破壊的変更 |

### 4.3 完了の定義（Definition of Done）

- [ ] lint、型チェック、テストが通っている
- [ ] 新しいロジックにテストがある
- [ ] プロンプトやツールを変更した場合、評価結果を添付している
- [ ] DB 構造を変更した場合、Alembic のマイグレーションがある
- [ ] 新しい UI 文言が三言語で用意されている
- [ ] 関連ドキュメントを三言語で更新している（または第 1 節に従って明記し Issue を作成）
- [ ] 秘密情報、ユーザーデータ、ブランド画像、雑誌の本文をコミットしていない

### 4.4 レビューの約束

- レビュアーは 1 営業日以内に最初のコメントを返します。
- コメントは「必須」と「提案」に分け、提案は作成者が採否を決めます。
- 2 往復しても結論が出ない議論は同期のやり取りに切り替え、結論を PR に記録します。

## 5. コーディングの基本原則

- **コメントには「なぜ」を書く**。コードが語る「何をしているか」は繰り返しません。
- **使わないコードは残さない**：履歴は git に任せます。
- **設定は外に出す**：環境依存の値は環境変数から読み、`.env.example` に説明を書きます。
- **小さな関数と明確な名前**：`data`、`info`、`handle`、`manager` のような曖昧な名前は避けます。
- **失敗は明示する**：例外を握りつぶさず、処理できないエラーは十分な文脈を付けて上位へ。
- **TODO には Issue を紐づける**：`# TODO(#123): ...`。
- **外部呼び出しには必ずタイムアウト**：ネットワーク、モデル、DB のすべてに設定します。

### 5.1 命名

| 対象 | ルール | 例 |
| --- | --- | --- |
| Python のモジュール、関数、変数 | snake_case | `extract_palette`、`garment_id` |
| Python のクラス | PascalCase | `GarmentRepository` |
| 定数 | UPPER_SNAKE_CASE | `MAX_RENDER_IMAGE_CALLS` |
| DB テーブル | 複数形の snake_case | `render_stages` |
| DB カラム | snake_case、外部キーは `<entity>_id`、時刻は `<verb>_at` | `outfit_id`、`reviewed_at` |
| API パス | 小文字の複数形、ハイフン区切り | `/v1/garments`、`/v1/me/memories` |
| JSON フィールド | camelCase | `garmentId`、`createdAt` |
| イベント名 | `<resource>.<event>` | `render.stage`、`garment.ready` |
| Agent のツール | `verb_noun` の snake_case | `search_wardrobe` |
| 環境変数 | `STYLEAI_` 接頭辞 + UPPER_SNAKE_CASE。第三者 SDK 規定の変数はそのまま | `STYLEAI_DATABASE_URL`、`ANTHROPIC_API_KEY` |
| TypeScript のファイル | kebab-case | `outfit-card.tsx` |
| React コンポーネント | PascalCase | `OutfitCard` |
| i18n のキー | 画面ごとにまとめたドット区切り | `closet.upload.title` |

## 6. Python バックエンド

### 6.1 ツールとバージョン

- Python 3.13、依存関係は uv（`pyproject.toml` + `uv.lock`）。
- lint とフォーマットは ruff（行幅 100）、mypy は `app/` に strict。
- モジュール間の依存方向は import-linter で CI 検査。
- テストは pytest + pytest-asyncio。

### 6.2 レイヤー

```text
api (routers)  ->  services  ->  repositories  ->  database
agent/tools    ->  services
pipelines      ->  services / providers
worker/tasks   ->  pipelines / services
services       ->  providers
```

| 層 | 担当 | やらないこと |
| --- | --- | --- |
| `api` | パラメータ検証、認証、サービス呼び出し、レスポンス整形 | 業務ロジック、DB への直接アクセス |
| `services` | 業務ルール、トランザクション境界、複数リポジトリの組み合わせ | HTTP の詳細 |
| `repositories` | DB の読み書き。全クエリにユーザー条件を付与 | 業務判断、ORM Session を返すこと |
| `agent/tools` | モデルのツール要求をサービス呼び出しに変換し、結果をモデル向けに整形 | DB や外部 API への直接アクセス |
| `pipelines` | 複数ステップのバックグラウンド処理の編成 | ジョブのスケジュール定義 |
| `providers` | 外部サービスの呼び出し、リトライ、タイムアウト、計測 | 業務ルール |
| `worker` | Procrastinate のタスク、キュー、リトライ、ロックの宣言 | 業務ロジック |

**トランザクション境界はサービス層**。1 つのサービスメソッドが 1 つの作業単位に対応し、そこで開始・コミットします。リポジトリはセッションを受け取るだけで、自分でコミットしません。

### 6.3 具体例

ルーターはリクエストとレスポンスだけを扱います。

```python
@router.patch("/garments/{garment_id}", response_model=GarmentOut)
async def update_garment_tags(
    garment_id: UUID,
    body: GarmentTagsPatch,
    user: CurrentUser,
    service: GarmentServiceDep,
) -> GarmentOut:
    garment = await service.update_tags(user_id=user.id, garment_id=garment_id, patch=body)
    return GarmentOut.from_domain(garment)
```

サービス層がルールとトランザクションを持ちます。

```python
class GarmentService:
    async def update_tags(self, *, user_id: UUID, garment_id: UUID, patch: GarmentTagsPatch) -> Garment:
        """Apply user corrections and pin corrected fields against re-tagging."""
        async with self._uow() as uow:
            garment = await uow.garments.get_for_user(garment_id, user_id=user_id)
            if garment is None:
                raise AppError("GARMENT_NOT_FOUND", "Garment does not exist.")
            # Corrected fields are pinned so a later re-tagging run cannot overwrite them.
            garment.apply_user_corrections(patch.to_changes())
            await uow.garments.save(garment)
            await uow.events.add(user_id=user_id, type="garment.updated", payload={"garmentId": str(garment_id)})
            await uow.commit()
        return garment
```

インターフェースのモデルは camelCase のエイリアスを統一して使います。

```python
class ApiModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")


class GarmentTagsPatch(ApiModel):
    category: GarmentCategory | None = None
    formality: int | None = Field(default=None, ge=1, le=5)
    style_tags: list[str] | None = None
```

### 6.4 エラー処理

- 想定内の業務エラーは `AppError(code, message, detail)` を送出し、共通ハンドラがエラーレスポンス（第 8.3 節）に変換します。
- 想定外の例外はハンドラがスタックトレースを記録して Sentry に送り、レスポンスは `INTERNAL_ERROR` と `requestId` のみ返します。
- 外部サービスの例外は `providers` 層で `ProviderError`（`retryable` 付き）に変換し、上位がリトライか失敗かを判断します。
- 例外で通常フローを制御しません。「見つからない」はリポジトリで `None` を返し、エラーにするかはサービス層が決めます。

### 6.5 非同期とタイムアウト

- IO はすべて async。イベントループ内でブロッキング関数を呼ばず、必要な場合（画像処理など）は `asyncio.to_thread` か Worker に回します。
- 外部呼び出しにはタイムアウトを設定します：DB クエリは既定 10 秒、通常の HTTP は 30 秒、モデルのストリーミングは用途に応じて設定。
- 複数のツールやリクエストを並行実行するときは `asyncio.TaskGroup` を使い、1 つの失敗で他もキャンセルして、放置されたコルーチンを残しません。

### 6.6 ログ

structlog で構造化フィールドとして書き、文字列連結はしません。

```python
log.info("render_stage_completed", render_id=str(render_id), stage_no=stage.no, latency_ms=latency_ms, cost_usd=cost)
```

すべてのログに次のフィールドが自動で付きます。

| フィールド | 内容 |
| --- | --- |
| `request_id` | HTTP リクエストの識別子 |
| `trace_id` | API、Worker、外部呼び出しをまたぐ識別子 |
| `user_id` | 現在のユーザー（あれば） |
| `turn_id` / `render_id` / `job_id` | 処理対象（あれば） |

記録しないもの：秘密情報、Cookie、パスワード、ユーザーのアップロード画像の内容や署名付きリンク、モデル入力の全文（必要なら長さと要約のみ。全文はアクセス制御された Agent トレースへ）。

### 6.7 設定

- 設定は `app/settings.py` にまとめ、pydantic-settings で環境変数から読み、起動時に検証します。必須項目が欠けていれば起動を失敗させます。
- 業務コードは DI で設定オブジェクトを受け取り、`os.environ` を直接読みません。
- モデル ID、effort、予算上限などの AI 関連パラメータも設定に置き、環境ごとに調整できるようにします。

### 6.8 DB マイグレーション

- スキーマ変更はすべて Alembic で行い、機能の PR に含めます。
- `main` にマージ済みのマイグレーションは変更せず、必要なら新規に追加します。
- テーブル名は複数形の snake_case、主キーは UUID（カード番号を除く）、すべてのテーブルにタイムゾーン付きの `created_at`・`updated_at`。
- **マイグレーションは前方互換であること**：リリース時にマイグレーションが先に走り、旧コードがまだ動いています。カラムの削除や改名は 2 回のリリースに分けます。
- 大きなテーブルへのインデックス作成は `CREATE INDEX CONCURRENTLY` を使います。

## 7. TypeScript フロントエンド

### 7.1 ディレクトリ構成

```text
apps/web/src/
├── app/                  # routes (App Router)
│   └── [locale]/         # zh-CN / ja / en
├── components/
│   ├── ui/               # shadcn/ui based primitives
│   └── <feature>/        # closet, chat, outfit, render ...
├── features/             # hooks and state per feature (queries, mutations, SSE handling)
├── lib/
│   ├── api/              # generated OpenAPI types and fetch client
│   └── sse/              # event stream client with Last-Event-ID replay
├── messages/             # zh-CN.json, ja.json, en.json
└── styles/               # design tokens
```

### 7.2 コーディングのポイント

- `strict` を有効にし、`any` は禁止（必要なら `unknown` で受けて絞り込む）。
- 基本は Server Components。操作が必要な箇所だけ `"use client"`。
- サーバーデータは TanStack Query で取得し、Zustand に複製しません。SSE イベント到着時は該当クエリのキャッシュを更新するか無効化します。
- API の型は OpenAPI から生成（`pnpm gen:api`）し、**手書きしません**。外部入力は zod で検証します。
- スタイルは Tailwind とデザイントークン。色の値を直接書きません。
- データ表示は 4 つの状態を必ず扱います：読み込み中、空、エラー、正常。
- UI の文言はすべて `messages/` に置き、数値・日付・価格は next-intl の書式化関数を使います（価格は日本円）。

### 7.3 アクセシビリティ

- 操作要素はキーボードで扱え、フォーカスが見えること。
- 画像には `alt`。服の画像はタグから生成した説明（例：「グレーのフーディ」）を使います。
- コントラストは WCAG AA。色の情報は文字でも伝えます（色見本の横に色名を表示）。
- ストリーミング表示の領域は `aria-live="polite"` にし、読み上げが 1 文字ずつ中断されないようにします。

## 8. API 設計

### 8.1 基本ルール

- REST。パスは `/v1` 始まり、リソース名は複数形。
- リクエストとレスポンスの JSON は camelCase。
- ID は UUID 文字列、時刻は ISO 8601 の UTC（例：`2026-09-16T08:30:00Z`）。
- 金額は整数と通貨フィールドで表します（例：`{"amount": 5990, "currency": "JPY"}`）。
- 時間のかかるジョブを作る API は `202 Accepted` とジョブ／リソース ID を返します。

### 8.2 ページングと冪等性

- 一覧はカーソルページング：`?cursor=...&limit=20`（`limit` は最大 100）。レスポンスに `nextCursor`、次がなければ `null`。
- 作成系 API は `Idempotency-Key` ヘッダーに対応します。同じユーザー・同じキーの 24 時間以内の再送は最初の結果を返します。

### 8.3 エラー

```json
{ "error": { "code": "GARMENT_NOT_FOUND", "message": "Garment does not exist.", "detail": {}, "requestId": "..." } }
```

| HTTP | 用途 | コード例 |
| --- | --- | --- |
| 400 | 形式やパラメータが不正 | `VALIDATION_FAILED` |
| 401 | 未ログイン、セッション切れ | `UNAUTHENTICATED` |
| 403 | ログイン済みだが権限なし | `FORBIDDEN` |
| 404 | 存在しない、または本人のものでない | `GARMENT_NOT_FOUND`、`OUTFIT_NOT_FOUND` |
| 409 | 状態の競合 | `TURN_IN_PROGRESS`、`RENDER_ALREADY_RUNNING` |
| 413 | アップロードが大きすぎる | `UPLOAD_TOO_LARGE` |
| 422 | 形式は正しいが業務上処理できない | `IMAGE_NOT_A_GARMENT` |
| 429 | 頻度またはクレジットの上限 | `RATE_LIMITED`、`CREDITS_EXHAUSTED` |
| 503 | 依存サービスが一時的に利用不可 | `UPSTREAM_UNAVAILABLE` |

本人のものでないリソースは 403 ではなく 404 を返し、存在の有無を漏らしません。エラーコードは `app/errors.py` に集約し、フロントがコードに応じて三言語の文言を表示します。

### 8.4 SSE イベント

各イベントは `id`（= `seq`）、`event`、JSON の `data` を持ちます。再接続時はブラウザが `Last-Event-ID` を送り、サーバーがそれ以降を補完します。

| event | 意味 | data の主なフィールド |
|---|---|---|
| `message.delta` | 返答テキストの差分 | `turnId`、`text` |
| `thinking.summary` | 思考の要約 | `turnId`、`text` |
| `tool.started` / `tool.finished` | ツール呼び出しの開始と終了 | `turnId`、`tool`、`status` |
| `outfit.ready` | 提案カードの完成 | `outfitId` |
| `render.stage` | ある段階の画像ができた | `renderId`、`stageNo`、`imageUrl` |
| `render.done` | 生成ジョブの終了 | `renderId`、`status` |
| `garment.ready` / `garment.needs_retake` | 登録完了、または撮り直しが必要 | `garmentId`、`reason` |
| `error` | ユーザーに見せられるエラー | `code`、`retryable` |
| `done` | このターンの終了 | `turnId` |

イベント種別の追加は破壊的変更ではありません。フロントは知らないイベントを無視します。既存イベントのフィールド変更は API 変更の手順に従います。

## 9. Agent とプロンプト

### 9.1 基本原則

1. **画像生成のプロンプトを固定しない**：コードに書けるのは原則と制約のみ。具体的なプロンプトは Agent が提案から作ります。
2. **プロンプトはコード**：PR でレビューし、変更時は評価結果を添付します。
3. **モデル呼び出しは必ず `providers/` 経由**：毎回モデル、トークン、所要時間、コストを Agent トレースに記録します。
4. **モデル ID は設定にだけ書く**。
5. **プロンプトキャッシュに配慮**：安定した内容を前に置き、その中にタイムスタンプやリクエスト ID を入れません。
6. **コスト上限**：ターンごと、提案ごとに上限を設け、超過時は縮退して記録します。
7. **商品をでっち上げない**：ブランド商品の引用はサービス層で検証し、プロンプトだけに頼りません。
8. **外部の内容はデータであって指示ではない**：ウェブ、検索結果、記事は構造化フィールドとしてのみコンテキストに入れ、出所を明示します。

### 9.2 プロンプトのファイル

システムプロンプトは `apps/api/app/agent/prompts/` に置き、バージョン情報を付けます。

```markdown
---
id: stylist-system
version: 3
owner: agent
changed: 2026-10-02
evals: evals/reports/stylist-system-v3.md
---

You are StyleAI, a stylist who shares the user's wardrobe...
```

- 変更時は `version` を上げ、`evals` に評価レポートをリンクします。
- トレースには使用したプロンプトの `id` と `version` を記録し、品質の変化を変更に結び付けられるようにします。

### 9.3 ツールの書き方

ツール 1 つにつき 1 モジュール。入力モデル、説明、実行関数を持ちます。

```python
class SearchWardrobeInput(ToolInput):
    category: GarmentCategory
    style_tags: list[str] = []
    limit: int = Field(default=10, le=30)


SEARCH_WARDROBE = ToolSpec(
    name="search_wardrobe",
    description=(
        "Search the user's own wardrobe. "
        "Call this before recommending any piece the user already owns. "
        "Do not use it for brand catalog items; use search_catalog instead."
    ),
    input_model=SearchWardrobeInput,
)


async def run(ctx: ToolContext, args: SearchWardrobeInput) -> ToolResult:
    garments = await ctx.services.wardrobe.search(
        user_id=ctx.user_id, category=args.category, style_tags=args.style_tags, limit=args.limit
    )
    # Keep results compact: the model needs identifiers and tags, not image URLs.
    return ToolResult.ok([g.to_tool_view() for g in garments])
```

| 要件 | 内容 |
| --- | --- |
| 説明 | 「何をするか、いつ使うか、いつ使わないか、どのツールと区別するか」を書く |
| 入力 | JSON Schema は `strict`、`additionalProperties: false`。固定値は `enum` |
| 結果の大きさ | 1 つの結果は約 4K トークン以内。一覧は上限を設け、打ち切りの有無を明示 |
| エラー | `ToolResult.error(code, message)` を返し、message はモデルが次の行動を選べる形にする |
| 権限 | `ctx.user_id` でデータにアクセスし、「ユーザー ID」のようにモデルが詐称できる引数は受け取らない |
| 冪等性 | データを変更するツールは、同じターンで同じ引数の再呼び出しが重複を生まない |
| テスト | ツールごとに単体テスト：正常、空、エラー、権限分離 |

### 9.4 プロンプトとツール変更の評価フロー

1. ブランチでプロンプトやツールを変更する。
2. ローカルでスモーク評価（約 20 ケース）を実行し、明らかな劣化がないか確認する。
3. PR を作成し、CI がスモーク評価を実行して結果を PR に貼る。
4. 提案品質や生成に影響する変更は、マージ前にフル評価を実行し、レポートを `evals/reports/` に保存する。
5. 評価が下がる変更はマージしない。ただし PR でトレードオフを説明し、レビュアーが同意した場合を除く。

## 10. ナレッジのテクニックカード

- 人が整理したカードは `knowledge/cards/` に YAML で保存し、1 枚 1 ファイル（ファイル名は番号、例：`K-0412.yaml`）、PR で審査します。
- 学習パイプラインの候補カードは DB に保存し、承認後に YAML へ書き出して PR を出します。
- 番号は `K-0001` 形式。増やす一方で再利用せず、廃止したカードは `status` を `retired` にしてファイルは残します。
- CI で JSON Schema によりフィールドと値を検証します。

```yaml
id: K-0412
status: candidate          # candidate | approved | retired
title: Tonal layering
terms: { zh: 同色系深浅叠穿, ja: ワントーンの濃淡レイヤード, en: Tonal layering }
category: color            # color | layering | silhouette | texture
when_to_use: Few colors available; aiming for a polished look; fall/winter layering.
how: Pick three values of one hue and darken from base to outer layer; contrast knit, wool and leather textures.
avoid: Identical textures across all layers, which reads flat.
checks:                    # optional machine-checkable hints used by validate_outfit
  - same_hue_family: true
  - min_lightness_step: 15
tags: [color, layering]
season_scope: evergreen   # evergreen | FW26 | SS27 ...
expires_at: null
sources:
  - { outlet: "MEN'S NON-NO", title: "...", url: "...", accessed: 2026-09-01 }
confidence: 0.72
```

**審査の観点**：特定の商品ではなく複数のアイテムに一般化できるか、`when_to_use` と `avoid` が具体的か、原文の写しがないか（「情報ソース一覧」第 4 節）、既存カードと重複しないか、`checks` の数値が妥当か。

## 11. テスト

| レベル | ツール | 基準 |
|---|---|---|
| ユニット | pytest、Vitest | サービス層の行カバレッジ 80% 以上 |
| 結合 | pytest（Docker の実 PostgreSQL） | リポジトリ、主要 API、ジョブの登録と実行 |
| E2E | Playwright | アップロード登録、対話での提案、着用イメージ確認の 3 フロー |
| 評価 | `evals/` | プロンプトやツールの変更時（第 9.4 節） |

- **ユニットテストで実際のモデル API を呼ばない**。録画したレスポンスを `tests/fixtures/llm/` に置いて使います。録画スクリプトはリクエストから鍵とユーザー画像を除去します。
- 実 API が必要なテストは `@pytest.mark.live` を付け、既定では実行しません。
- テスト関数名は挙動を説明します：`test_update_tags_pins_corrected_fields`。
- テスト間で可変の状態を共有しません。結合テストは各ケースをトランザクション内で実行してロールバックします。
- テスト画像はチーム自身が撮影した服か、利用条件が明確な生成画像のみを使い、出所を `tests/fixtures/LICENSES.md` に記録します。
- 評価データセットにはバージョンを付け、変更時は理由も記録して、時期の違う評価が比較可能であるようにします。

## 12. セキュリティとコンプライアンス

本リポジトリは**公開リポジトリ**です。次のルールに例外はありません。

- **秘密情報は一切コミットしない**。`.env`（git 対象外）に置き、リポジトリには `.env.example` のみ。
- gitleaks をローカルの pre-commit と CI の二重で実行します。誤ってコミットした場合は、コミットを消すだけでなく直ちに無効化してローテーションします。
- ユーザーデータ、アップロード画像、ブランドの商品画像、雑誌の本文はコミットしません。
- 外部サイトへのアクセスは robots.txt と利用規約を守ります。CAPTCHA の回避やフィンガープリントの偽装は禁止です。
- アップロード画像は既定で非公開、本人のみアクセス可能。ユーザーは自分のデータを削除できます。
- 依存関係は Renovate または Dependabot が定期的に更新 PR を作成します。新規依存はライセンスとメンテナンス状況を確認します。
- 管理者 API は一般 API と別に認可し、操作は監査ログに記録します。

## 13. 開発環境

| ツール | バージョン |
|---|---|
| Node.js | 24 LTS（`.nvmrc`） |
| pnpm | 10 |
| Python | 3.13（`.python-version`） |
| uv | 最新の安定版 |
| Docker | ローカルの PostgreSQL と結合テスト用 |

- ローカルのフックは `pre-commit` で管理：ruff、prettier、gitleaks、コミットメッセージの検査、カードの Schema 検証。
- よく使うコマンドは M0 でリポジトリ直下のタスクスクリプト（`just dev`、`just test`、`just gen-api` など）にまとめ、`README` に記載します。
- ローカル開発では `infra/docker-compose.yml` で PostgreSQL を起動し、オブジェクトストレージはファイルシステムのアダプタを使います。

## 14. ドキュメント

| ディレクトリ | 内容 | ブランチ |
| --- | --- | --- |
| `docs/zh`、`docs/ja`、`docs/en` | 企画書、技術選定、開発規約、情報ソース、システムアーキテクチャ | `draft` |
| `docs/charter.html` | 企画書のビジュアル版 | `draft` |
| `docs/zh/tech-notes`、`docs/tech-notes/labs` | 技術解説の記事と実験コード | `tech-notes` |

- ドキュメントの決定が変わったら、その文書自体を更新し、冒頭のバージョンと日付を変更します。末尾に「変更履歴」を積み上げません。
- 技術選定の「要検証」項目が確定したら、結論と根拠（評価結果、比較データ）を「技術選定」に書き戻します。
- 技術解説の記事は「局所的完備」の原則に従います。1 篇で 1 つの問いに答え、それに必要な概念をすべて説明します。記事中の実験出力は実際に実行した結果でなければなりません。
