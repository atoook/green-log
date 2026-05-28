# Brief: plant-registration

## Problem
観葉植物初心者は、自宅にある植物を個体ごとに把握しづらく、水やりや成長記録を始める前の基礎情報が整理されていない。植物種ではなく「自分が所有している鉢・個体」として登録できないと、後続の水やり記録、今日のお世話、写真ログがユーザーの日常に結びつかない。

## Current State
プロダクト方針は `docs/mvp.md` と `docs/architecture.md` に定義されている。MVP の最初の機能として Plant Registration が挙げられており、管理単位はユーザー所有の鉢・個体とされている。

実装面では、Frontend は Vue 3 + Vite の初期構成に近く、Backend は FastAPI のルートエンドポイントのみが存在する。植物登録、一覧、詳細、永続化、API クライアント、画面ルーティングはまだ実装されていない。

## Desired Outcome
ユーザーが所有している植物の鉢・個体を登録し、登録済み植物の一覧を見て、各植物の詳細を確認できる。Plant Registration の情報は後続機能である Watering Record、Today's Care TODO、Growth Photo Log の基礎データとして再利用できる。

## Approach
MVP 最初の縦切りとして、Plant エンティティ、REST API、SQLite/libSQL 永続化、Frontend の登録・一覧・詳細画面を一つの spec で扱う。Backend は FastAPI の Router / Service / Repository / Database レイヤーに沿って実装し、Frontend は API Client 経由で Backend を呼び出す。

この approach を採用する理由は、ユーザー価値である「自分の植物を登録して眺められる状態」を最短で提供しつつ、後続の水やり記録や写真ログが依存できる安定した Plant ID と基本属性を先に固められるため。

## Scope
- **In**: 植物の新規登録
- **In**: 植物一覧の表示
- **In**: 植物詳細の表示
- **In**: `name`, `acquiredDate`, `memo`, `imageUrl`, `wateringCycleDays` の入力・保存・表示
- **In**: 管理単位を植物種ではなくユーザー所有の鉢・個体として扱うデータモデル
- **In**: `GET /plants`, `POST /plants`, `GET /plants/{id}` の REST API
- **In**: SQLModel モデル、Pydantic スキーマ、Repository / Service / Router の最小構成
- **In**: Alembic による `plants` テーブル migration
- **In**: Mobile First のシンプルな登録、一覧、詳細 UI
- **Out**: 水やり実行記録
- **Out**: 最終水やり日時の保持
- **Out**: 次回水やり予定日の自動計算
- **Out**: 今日のお世話 TODO
- **Out**: カレンダー表示
- **Out**: 成長写真ログの複数写真管理
- **Out**: 画像アップロード機能
- **Out**: 認証、ログイン、マルチユーザー共有
- **Out**: 植物種マスタ、植物図鑑、育成ガイド

## Boundary Candidates
- Plant 基本情報の永続化と取得を担う Backend API 境界
- Plant 登録、一覧、詳細を担う Frontend 画面境界
- 後続機能が参照する Plant ID と基本属性のデータ契約
- `imageUrl` は URL 文字列として保存し、ファイルアップロードや画像変換とは分離する
- `wateringCycleDays` は登録時の基本設定として保存し、次回予定計算は Watering Record 側に委譲する

## Out of Boundary
- 水やり履歴、スキップ、完了操作
- 写真履歴、Before / After 比較、日付付き写真ログ
- 通知、お知らせ、PWA push
- 複数ユーザー、共有、権限管理
- 植物種ごとの推奨水やり周期や育成知識
- 外部ストレージ連携を含む画像アップロード

## Upstream / Downstream
- **Upstream**: `docs/mvp.md` の MVP 方針、Data Model Design、API Design Policy
- **Upstream**: `docs/architecture.md` の Frontend / Backend / Database 構成
- **Downstream**: Watering Record は Plant ID と `wateringCycleDays` に依存する
- **Downstream**: Today's Care TODO は Plant 一覧と水やり予定計算に依存する
- **Downstream**: Growth Photo Log は Plant 詳細と Plant ID に依存する
- **Downstream**: Calendar View は Plant と水やり・写真イベントに依存する

## Existing Spec Touchpoints
- **Extends**: なし
- **Adjacent**: Watering Record、Today's Care TODO、Growth Photo Log、Calendar View

## Constraints
技術スタックは Frontend: Vue 3, Vite, TypeScript, Tailwind CSS, PWA、Backend: FastAPI, Python, Pydantic, SQLModel、Database: Turso / SQLite / libSQL、Migration: Alembic とする。

UX は `docs/mvp.md` の方針に従い、業務ツール感や複雑な設定を避ける。用語は「管理」より「記録」、「タスク」より「お世話」を優先する。MVP 速度と継続利用しやすさを重視し、画像は `imageUrl` の保存に留める。
