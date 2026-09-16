# stylist-agent

> [中文](README.md) · **日本語** · [English](README.en.md)

**StyleAI v2**（仮称）：あなたとクローゼットを共有する AI スタイリスト。

色と重ね着を理解し、アップロードされた服を一着ずつ読み取り、ブランド公式サイトでアイテムを探します。プロンプトも生成ステップも自分で決めて着用イメージをつくり、ファッション誌を読んで新しいテクニックを学び続けます。

## 現在の状況

**企画段階**：アプリケーションのコードはまだありません。企画書、技術選定、開発規約を固めている段階で、確定後に M0 の開発に入ります。

## ドキュメント

| ドキュメント | 中文 | 日本語 | English |
|---|---|---|---|
| 企画書 | [01-project-charter](docs/zh/01-project-charter.md) | [01-project-charter](docs/ja/01-project-charter.md) | [01-project-charter](docs/en/01-project-charter.md) |
| 技術選定 | [02-tech-stack](docs/zh/02-tech-stack.md) | [02-tech-stack](docs/ja/02-tech-stack.md) | [02-tech-stack](docs/en/02-tech-stack.md) |
| 開発規約 | [03-dev-guidelines](docs/zh/03-dev-guidelines.md) | [03-dev-guidelines](docs/ja/03-dev-guidelines.md) | [03-dev-guidelines](docs/en/03-dev-guidelines.md) |
| 情報ソース一覧 | [04-content-sources](docs/zh/04-content-sources.md) | [04-content-sources](docs/ja/04-content-sources.md) | [04-content-sources](docs/en/04-content-sources.md) |
| システムアーキテクチャ | [05-system-architecture](docs/zh/05-system-architecture.md) | [05-system-architecture](docs/ja/05-system-architecture.md) | [05-system-architecture](docs/en/05-system-architecture.md) |

中国語版が原本で、日本語版と英語版は順次更新します。企画書にはビジュアル版（三言語）の [docs/charter.html](docs/charter.html) もあります。ダウンロードしてブラウザで開いてください。

技術解説の記事と実験コード（セグメンテーションと画像生成モデル、色の抽出、PostgreSQL のジョブキュー、Agent の接続、モデル SDK とフレームワーク）は、学習用ブランチ [`tech-notes`](https://github.com/ailuruschen-bit/stylist-agent/tree/tech-notes/docs/zh/tech-notes) にあります。正式な開発内容には含みません。

## 主な決定事項

- プラットフォーム：Web
- 最初の市場：日本。ターゲットは 18〜30 歳の若者
- 第一弾ブランド：UNIQLO、ZARA、H&M、NIKE、adidas
- 技術スタック：Next.js + FastAPI + PostgreSQL（pgvector）。Agent は Claude Opus 5、画像生成は Gemini
- [HackathonPJT](https://github.com/ailuruschen-bit/HackathonPJT/tree/deploy/lite-budget) の demo をベースに新しく構築

## ライセンス

現時点ではオープンソースライセンスを付与していません。All rights reserved.
