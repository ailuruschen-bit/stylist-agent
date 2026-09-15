# 開発規約

> 言語：[中文](../zh/03-dev-guidelines.md) · **日本語** · [English](../en/03-dev-guidelines.md)
> ステータス：ドラフト v0.1 · 更新：2026-09-15
> 中国語版が原本です。内容に差異がある場合は中国語版を優先します。
> すべてのコントリビューター（AI コーディングアシスタントを含む）は本書に従ってください。規約自体の変更も PR で議論してからマージします。

## 1. 言語ルール

| 場面 | 言語 |
|---|---|
| チーム内のコミュニケーション、Issue と PR の議論 | 中国語中心 |
| `docs/` のドキュメント | 中国語、日本語、英語の三言語。**中国語版が原本** |
| コードコメント、docstring | 英語 |
| 識別子（変数、関数、クラス、テーブル名、API フィールド） | 英語 |
| コミットメッセージ、PR タイトル | 英語（Conventional Commits） |
| Agent のシステムプロンプト、ツールの説明 | 英語（出力言語はユーザーに合わせる） |
| ナレッジのテクニックカード | 本文は英語、用語に中日英の対訳を付ける |
| UI の文言 | i18n で三言語を用意。コンポーネントへのハードコードは禁止 |

**ドキュメントの同期ルール**：中国語のドキュメントを変更する PR では、日本語版と英語版も同時に更新します。翻訳が間に合わない場合は PR にその旨を書き、`docs: sync translations` の Issue を作成して、次の PR までに反映します。

## 2. ブランチとマージ

- `main` は保護ブランチ。PR 経由でのみマージし、squash merge を使います。
- ブランチ名：`<type>/<short-description>`。例：`feat/closet-upload`、`fix/sse-reconnect`。
  - type：`feat`、`fix`、`docs`、`refactor`、`test`、`chore`、`exp`（実験用。マージしなくてもよい）。
- 1 つの PR では 1 つのことだけを行います。変更は 400 行以内を目安にします（生成ファイル、ロックファイル、マイグレーションのスナップショットを除く）。
- マージ条件：CI がすべて成功し、1 名以上のレビューがあること。一人で開発している段階ではセルフレビューも可としますが、PR テンプレートの項目を必ず確認します。

## 3. コミット規約

[Conventional Commits](https://www.conventionalcommits.org/) に従います。

```text
<type>(<scope>): <summary in imperative mood>

<optional body: what and why>
```

- `type`：`feat`、`fix`、`docs`、`refactor`、`test`、`perf`、`chore`、`build`、`ci`
- `scope`：`web`、`api`、`agent`、`render`、`closet`、`scout`、`knowledge`、`evals`、`infra`、`docs`
- 例：
  - `feat(closet): detect alternative wears during garment tagging`
  - `fix(render): retry stage when critique flags color mismatch`
  - `docs: add tech stack decision for task queue`

## 4. Pull Request

PR の説明はリポジトリのテンプレート（`.github/pull_request_template.md`）を使い、最低限次の内容を書きます。

1. 何をしたか、なぜしたか
2. どう確認したか（テスト、スクリーンショット、評価結果）
3. プロンプト、ツール、DB 構造、コスト、コンプライアンスへの影響の有無
4. 三言語のドキュメントを同期したか

**完了の定義（Definition of Done）**

- [ ] lint、型チェック、テストが通っている
- [ ] 新しいロジックにテストがある
- [ ] プロンプトやツールを変更した場合、評価結果を添付している
- [ ] DB 構造を変更した場合、Alembic のマイグレーションがある
- [ ] 新しい UI 文言が三言語で用意されている
- [ ] 関連ドキュメントを三言語で更新している
- [ ] 秘密情報、ユーザーデータ、ブランド画像、雑誌の本文をコミットしていない

## 5. コーディングの基本原則

- **コメントには「なぜ」を書く**。コードを読めばわかる「何をしているか」は繰り返しません。
- **使わないコードは残さない**：不要なコードは削除し、履歴は git に任せます。
- **設定は外に出す**：環境によって変わる値は環境変数から読み、`.env.example` に記載します。
- **小さな関数と明確な名前**：名前だけで用途がわかるようにし、`data`、`info`、`handle` のような曖昧な名前は避けます。
- **失敗は明示する**：例外を握りつぶさず、処理できないエラーは十分な文脈を付けて上位に投げます。
- **TODO には Issue を紐づける**：`# TODO(#123): ...` の形式で書きます。

## 6. Python バックエンド

### 6.1 ツールとバージョン

- Python 3.13。依存関係は uv で管理（`pyproject.toml` + `uv.lock`）。
- lint とフォーマットは ruff。mypy は `app/` に strict モードを適用。
- テストは pytest + pytest-asyncio。

### 6.2 レイヤー

```text
api (routers)  ->  services  ->  repositories  ->  database
agent/tools    ->  services
worker/tasks   ->  services
```

- **ルーター層**：パラメータ検証、認証、サービス呼び出し、レスポンスの組み立てだけを行い、業務ロジックは書きません。
- **サービス層**：業務ロジックを持ち、複数のリポジトリを組み合わせてよいのはこの層だけです。
- **リポジトリ層**：DB の読み書きだけを担当し、ドメインオブジェクトを返します。ORM の Session は返しません。
- **Agent のツール**：サービス層を呼び出します。DB に直接アクセスせず、外部モデルの API も直接呼びません（`providers/` を経由）。

### 6.3 コーディングのポイント

- すべての関数シグネチャに型ヒントを書き、公開関数には英語の docstring を付けます。
- インターフェースの境界（リクエスト、レスポンス、ツールの入力、LLM の構造化出力）はすべて Pydantic モデルにします。
- 外部に出す JSON は camelCase：Pydantic モデルに `alias_generator=to_camel` を設定し、Python 内部は snake_case のままにします。
- IO はすべて async にし、イベントループ内でブロッキング関数を呼びません。
- 業務エラーは `AppError(code, message, detail)` を投げ、共通の例外ハンドラで HTTP レスポンスに変換します。
- ログは structlog で構造化フィールドとして書き、文字列連結はしません。秘密情報、Cookie、ユーザーがアップロードした画像の内容は記録しません。

```python
async def tag_garment(garment_id: UUID, *, repo: GarmentRepository) -> GarmentTags:
    """Tag a garment from its cutout image and persist the result."""
    garment = await repo.get(garment_id)
    # Colors come from pixel clustering, not the LLM, so hex values stay exact.
    palette = extract_palette(garment.cutout_path)
    tags = await vision_tagger.tag(garment.cutout_path, palette=palette)
    await repo.save_tags(garment_id, tags)
    return tags
```

### 6.4 DB マイグレーション

- 構造の変更はすべて Alembic のマイグレーションで行い、機能の PR に含めてコミットします。
- `main` にマージ済みのマイグレーションは変更しません。修正が必要なら新しいマイグレーションを作ります。
- テーブル名は複数形の snake_case（`garments`、`knowledge_cards` など）。主キーは UUID に統一し、すべてのテーブルにタイムゾーン付きの `created_at`、`updated_at` を持たせます。

## 7. TypeScript フロントエンド

- `strict` を有効にし、`any` は禁止（どうしても必要なら `unknown` を使って型を絞り込む）。
- 基本は Server Components。操作が必要な場合だけ `"use client"` を付けます。
- サーバーのデータは TanStack Query で取得し、Zustand にコピーしません。
- API の型は OpenAPI から生成し（`pnpm gen:api`）、**手書きしません**。外部からの入力は zod で検証します。
- ファイル名は kebab-case（`outfit-card.tsx`）、コンポーネント名は PascalCase（`OutfitCard`）。
- スタイルは Tailwind とデザイントークンを使い、色の値を直接書きません。
- UI の文言はすべて `messages/{zh-CN,ja,en}.json` に置き、キーは画面ごとにまとめます（例：`closet.upload.title`）。
- アクセシビリティ：操作可能な要素はキーボードで使えること、画像には `alt` を付けること、色のコントラストは WCAG AA を満たすこと。
- ESLint（`eslint-config-next`）+ Prettier でフォーマットを統一します。

## 8. API 設計

- REST スタイル。パスは `/v1` から始め、リソース名は複数形：`/v1/garments`、`/v1/outfits/{id}`。
- リクエストとレスポンスの JSON は camelCase。
- エラーレスポンスの形式を統一します。

```json
{ "error": { "code": "GARMENT_NOT_FOUND", "message": "Garment does not exist.", "detail": {} } }
```

- 一覧 API はカーソルページネーション：`?cursor=...&limit=20`。レスポンスに `nextCursor` を含めます。
- 時間のかかるジョブを作る API（アップロード登録、画像生成）は `Idempotency-Key` ヘッダーに対応します。
- **SSE イベント**：各イベントは `event` と JSON の `data` を持ち、`data` には連番の `seq` を入れて、再接続後に取りこぼしを再送できるようにします。

| event | 意味 |
|---|---|
| `message.delta` | Agent の返答テキストの差分 |
| `thinking.summary` | 思考の要約 |
| `tool.started` / `tool.finished` | ツール呼び出しの開始と終了 |
| `render.stage` | 生成の各段階で画像ができた |
| `outfit.ready` | 提案カードができた |
| `error` | ユーザーに表示できるエラー |
| `done` | このターンの終了 |

## 9. Agent とプロンプト

1. **画像生成のプロンプトを固定しない**：コードに書いてよいのは原則と制約（例：「服の色は参照画像に合わせる」）だけです。具体的な生成プロンプトは Agent が提案内容から作ります。
2. **プロンプトはコードとして扱う**：システムプロンプトは `apps/api/app/agent/prompts/*.md` に置いて PR でレビューし、変更時は評価結果を添付します。
3. **ツール設計**：
   - 1 つのツールは 1 つの役割だけを持ち、名前は `verb_noun` 形式の snake_case（例：`search_wardrobe`）。
   - 入力の JSON Schema は `strict` を有効にし、`additionalProperties: false` を設定します。
   - 説明には「いつ使うか、いつ使わないか」を明記します。
   - 返す結果は簡潔で構造化されたものにし、ページ全体の HTML や大量の生データをモデルに戻しません。
   - エラー時は `is_error` と、次の行動を判断できるエラーメッセージを返し、例外で対話を止めません。
4. **モデル呼び出しは必ず `providers/` を通す**：呼び出しごとにモデル、トークン、処理時間、コストを Agent トレースに記録します。
5. **モデル ID は設定にだけ書く**。業務コードにモデル名を直接書きません。
6. **プロンプトキャッシュを意識する**：安定した内容（システムプロンプト、ツール定義）を前に置き、タイムスタンプやリクエスト ID など変化する値を挟みません。
7. **コスト上限**：対話の各ターン、各提案にトークン数と画像生成回数の上限を設け、超えたら縮退（例：一段階生成に切り替え）してトレースに記録します。
8. **商品をでっち上げない**：ブランド商品を提案するときは、ブランドカタログに実在するアイテムだけを引用します。

## 10. ナレッジのテクニックカード

- 人が整理したテクニックカードは `knowledge/cards/` に YAML ファイルとして 1 枚 1 ファイルで保存し、PR でレビューします。
- 学習パイプラインが作った候補カードは DB に保存し、審査を通過したら YAML に書き出して PR を出します。
- ID の形式は `K-0001`。番号は増やす一方で、再利用しません。

```yaml
id: K-0412
status: candidate          # candidate | approved | retired
title: Tonal layering
terms: { zh: 同色系深浅叠穿, ja: ワントーンの濃淡レイヤード, en: Tonal layering }
when_to_use: Few colors available; aiming for a polished look; fall/winter layering.
how: Pick three values of one hue and darken from base to outer layer; contrast knit, wool and leather textures.
avoid: Identical textures across all layers, which reads flat.
tags: [color, layering]
season_scope: evergreen   # evergreen | FW26 | SS27 ...
expires_at: null
sources:
  - { outlet: "MEN'S NON-NO", title: "...", url: "...", accessed: 2026-09-01 }
confidence: 0.72
```

- テクニックカードに原文をそのまま写した文章を入れてはいけません（ルールは「情報ソース一覧」第 4 節）。

## 11. テスト

| レベル | ツール | 基準 |
|---|---|---|
| ユニットテスト | pytest、Vitest | サービス層の行カバレッジ 80% 以上 |
| 結合テスト | pytest（Docker で起動した実際の PostgreSQL） | リポジトリと主要な API をカバー |
| E2E | Playwright | アップロード登録、対話での提案、着用イメージの確認という 3 つの主要フロー |
| 評価 | `evals/` | プロンプトやツールの変更時に実行（「技術選定」第 12 節） |

- **ユニットテストでは実際のモデル API を呼びません**。録画したレスポンスを fixture として使います。
- 実際の API が必要なテストには `@pytest.mark.live` を付け、デフォルトでは実行せず、明示的に有効化したときだけ実行します。
- テスト画像は、チームが自分で撮影した服か、利用条件で使用が明確に認められた生成画像だけを使い、出所を `fixtures/LICENSES.md` に記録します。

## 12. セキュリティとコンプライアンス

このリポジトリは**公開リポジトリ**です。次のルールに例外はありません。

- **秘密情報は一切コミットしない**。秘密情報は `.env`（git の対象外）に置き、リポジトリには `.env.example` だけを置きます。
- gitleaks を使い、ローカルの pre-commit フックと CI の二重でチェックします。誤ってコミットした場合は、コミットを消すだけでなく、すぐにその鍵を無効化してローテーションします。
- ユーザーデータ、ユーザーがアップロードした画像、ブランドの商品画像、雑誌の本文はコミットしません。
- 外部サイトへのアクセスは robots.txt と利用規約を守ります。CAPTCHA の回避やフィンガープリントの偽装など、ボット対策への対抗は禁止です。
- ユーザーがアップロードした画像はデフォルトで非公開とし、本人だけがアクセスできます。ユーザーが自分のデータを削除できるようにします。

## 13. 開発環境

| ツール | バージョン |
|---|---|
| Node.js | 24 LTS（`.nvmrc`） |
| pnpm | 10 |
| Python | 3.13（`.python-version`） |
| uv | 最新の安定版 |
| Docker | ローカルの PostgreSQL と結合テスト用 |

- ローカルのフックは `pre-commit` で管理します：ruff、prettier、gitleaks、コミットメッセージの形式チェック。
- ローカルでの起動手順は M0 完了後に `README` に追記します。
