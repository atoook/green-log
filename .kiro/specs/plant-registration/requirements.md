# Requirements Document

## Project Description (Input)
観葉植物初心者は、自宅にある植物を個体ごとに把握しづらく、水やりや成長記録を始める前の基礎情報が整理されていない。植物種ではなく「自分が所有している鉢・個体」として登録できないと、後続の水やり記録、今日のお世話、写真ログがユーザーの日常に結びつかない。

現在、プロダクト方針は `docs/mvp.md` と `docs/architecture.md` に定義されている。MVP の最初の機能として Plant Registration が挙げられており、管理単位はユーザー所有の鉢・個体とされている。実装面では、Frontend は Vue 3 + Vite の初期構成に近く、Backend は FastAPI のルートエンドポイントのみが存在する。植物登録、一覧、詳細、永続化、API クライアント、画面ルーティングはまだ実装されていない。

ユーザーが所有している植物の鉢・個体を登録し、登録済み植物の一覧を見て、各植物の詳細を確認できる状態にする。Plant Registration の情報は後続機能である Watering Record、Today's Care TODO、Growth Photo Log の基礎データとして再利用できる。

対象スコープは、植物の新規登録、植物一覧の表示、植物詳細の表示、`name`, `acquiredDate`, `memo`, `imageUrl`, `wateringCycleDays` の入力・保存・表示、ユーザー所有の鉢・個体として扱うデータモデル、`GET /plants`, `POST /plants`, `GET /plants/{id}` の REST API、SQLModel モデル、Pydantic スキーマ、Repository / Service / Router の最小構成、Alembic による `plants` テーブル migration、Mobile First のシンプルな登録・一覧・詳細 UI とする。

水やり実行記録、最終水やり日時の保持、次回水やり予定日の自動計算、今日のお世話 TODO、カレンダー表示、成長写真ログの複数写真管理、画像アップロード機能、認証、ログイン、マルチユーザー共有、植物種マスタ、植物図鑑、育成ガイドは対象外とする。

技術スタックは Frontend: Vue 3, Vite, TypeScript, Tailwind CSS, PWA、Backend: FastAPI, Python, Pydantic, SQLModel、Database: Turso / SQLite / libSQL、Migration: Alembic とする。UX は `docs/mvp.md` の方針に従い、業務ツール感や複雑な設定を避ける。用語は「管理」より「記録」、「タスク」より「お世話」を優先する。MVP 速度と継続利用しやすさを重視し、画像は `imageUrl` の保存に留める。

## Requirements
<!-- Will be generated in /kiro-spec-requirements phase -->
