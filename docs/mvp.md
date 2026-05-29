# Green Mate - MVP 提案・技術設計

# Overview

## サービス名

Green Mate

---

## Concept

「植物との生活記録」をテーマにした、
初心者向けの観葉植物お世話・成長記録アプリ。

単なるタスク管理ではなく、

- 植物を枯らさない
- 成長を感じる
- 愛着を持って育てる

ことを目的とする。

---

# Vision

## Core Experience

ユーザーがアプリを開いた時に、

- 今日やるべきお世話が分かる
- 植物の成長を感じられる
- 植物との生活を振り返られる

状態を目指す。

---

# Product Positioning

## Not

植物辞典アプリ

---

## Yes

植物との生活を続けるための記録アプリ

---

# Target Users

## Main Target

観葉植物初心者

---

## User Problems

- 水やりタイミングが分からない
- 水やりを忘れる
- 育っている実感がない
- 植物管理が続かない

---

## Secondary Target

中級〜上級の植物好きユーザー

### Expected Usage

- 写真記録
- 成長記録
- 水やり履歴管理

---

# Core Concept

## Theme

植物との生活記録

---

## Keywords

- お世話
- 記録
- 成長
- 暮らし
- 愛着
- 継続

---

# MVP Scope

# 1. Plant Registration

植物（鉢）を登録する。

## Fields

| Field | Description |
|---|---|
| id | Plant ID |
| name | 植物名 |
| image | 植物写真 |
| acquiredDate | 家に来た日 |
| memo | メモ |
| wateringCycleDays | 水やり周期 |

---

# 2. Watering Record

水やり記録を管理する。

## Features

- 水やり実行記録
- 最終水やり日時保持
- 次回予定日の自動計算

---

## Schedule Logic

固定曜日ではなく、
「最後に水やりした日」を基準に次回予定を計算する。

---

## Example

\```text
周期: 7日
前回: 5/1
次回: 5/8

実際の水やり: 5/10
次回: 5/17
\```

---

# 3. Today's Care TODO

今日必要なお世話を表示する。

---

## Example UI

\```text
🌿 今日のお世話

💧 モンステラ
💧 パキラ
\```

---

## Actions

- 水やり完了
- スキップ

---

# 4. Calendar View

カレンダー上で予定・履歴を確認できる。

---

## Display Items

- 水やり予定
- 水やり履歴
- 写真記録

---

# 5. Growth Photo Log

植物の成長写真を記録する。

---

## Purpose

ユーザーが成長実感を得られるようにする。

---

## Features

- 写真追加
- 日付付き保存
- 過去比較

---

## Example UI

\```text
🌱 モンステラ
家に来て184日

[今日]
[30日前]
[90日前]
\```

---

# UX Direction

# Avoid

- 業務ツール感
- 管理画面感
- 複雑な設定
- 情報過多

---

# Aim For

- 暮らし感
- 愛着
- 成長を眺めたくなるUI
- 開きたくなるアプリ

---

# Tone & Wording

| Avoid | Prefer |
|---|---|
| タスク | お世話 |
| 管理 | 記録 |
| 実行 | 完了 |
| 通知 | お知らせ |

---

# Data Model Design

# Core Unit

管理単位は「植物種」ではなく、
ユーザーが所有している「鉢（個体）」とする。

---

## Example

\```text
❌ モンステラ（植物種）
⭕ リビングのモンステラ（所有個体）
\```

---

# Initial Technical Strategy

# Architecture Goal

- 小さく早くMVPを作る
- 運用コストを抑える
- 新技術（FastAPI）を学ぶ
- UI/UXに開発時間を使う

---

# Frontend

## Stack

- Vue 3
- Vite
- TypeScript
- Tailwind CSS
- PWA

---

## Why Vue

Vueは既存経験があり、
MVP開発速度を優先できるため。

新規学習コストを抑え、
FastAPI側の学習・設計に集中する。

---

## Frontend Policy

- Mobile First
- シンプルなUI
- 最低限の画面数
- API Client経由でBackendを呼ぶ

---

## Expected Structure

\```text
src/
├── api/
├── components/
├── composables/
├── pages/
├── stores/
├── types/
└── utils/
\```

---

# Backend

## Stack

- FastAPI
- Python
- Pydantic
- SQLModel

---

## Why FastAPI

- 軽量でMVP向き
- API設計を学びやすい
- OpenAPI/Swagger生成が強力
- Pythonバックエンド経験を得られる

---

## Backend Architecture

\```text
Router
  ↓
Service
  ↓
Repository
  ↓
Database
\```

---

## Expected Structure

\```text
app/
├── routers/
├── services/
├── repositories/
├── models/
├── schemas/
├── db/
├── core/
└── main.py
\```

---

# Database

## Stack

- Turso
- SQLite / libSQL

---

## Why Turso

- 運用コストを下げられる
- SQLiteベースで軽量
- 個人開発MVPと相性が良い
- 将来的なスケールも一定可能

---

# ORM

## Stack

- SQLModel

---

## Why SQLModel

- FastAPIとの相性が良い
- Pydanticベース
- 学習コストが比較的低い
- 型定義が綺麗

---

# Migration

## Stack

- Alembic

---

# Hosting

## Frontend

Candidate:

- Vercel
or
- Cloudflare Pages

---

## Backend

Candidate:

- Render
- Fly.io
- Railway

---

# API Design Policy

## Principles

- RESTベース
- OpenAPIを意識
- フロントから独立したAPI設計
- 将来的なReact/Next.js置き換え可能性を考慮

---

## Example Endpoints

\```text
GET    /plants
POST   /plants

GET    /plants/{id}

POST   /plants/{id}/watering

GET    /todos/today

POST   /plants/{id}/photos
\```

---

# Future Extensibility

# Possible Features

## Social

- 成長記録シェア
- Before / After画像
- 月次まとめ

---

## Smart Features

- AI植物診断
- 季節ごとの水やり調整
- 通知最適化

---

## Knowledge Features

- 植物図鑑
- 育成ガイド

---

# Explicitly Out of MVP Scope

以下はMVPでは実装しない。

- 肥料管理
- 湿度管理
- SNS機能
- AI診断
- 詳細通知設定
- グループ管理
- マルチユーザー共有
- 高度な分析機能

---

# Development Philosophy

## Prioritize

- MVP速度
- 継続利用しやすさ
- シンプルなUX
- 愛着が湧く体験

---

## Avoid

- 過度な設計
- 複雑化
- 初期からの高機能化
- 技術学習目的だけの過剰実装

---

# Final Direction

「植物管理ツール」ではなく、

「植物との生活を記録するアプリ」

として設計する。
