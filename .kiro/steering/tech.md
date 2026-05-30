# Technology Stack

## Architecture

Green Mate は `frontend/` と `backend/` を分けた monorepo 構成で開発する。Frontend は Backend の REST API に依存し、Backend が Plant などの永続化データの authoritative source になる。

Backend は Router / Service / Repository / Database の layered architecture を基本にする。HTTP の責務、domain validation、persistence を分け、Repository は HTTP 例外を知らない。

Frontend は route/page/composable/component/API client/type を分離する。ページは composition、composable は画面単位の状態、component は presentation と入力イベントを主責務にする。

## Core Technologies

- **Frontend**: Vue 3, Vite, TypeScript, Tailwind CSS, Vue Router
- **Backend**: FastAPI, Pydantic, SQLModel, SQLAlchemy Session, Alembic
- **Database**: Turso/libSQL を主軸とし、test/CI/local smoke では SQLite も利用可能にする
- **Auth**: Clerk を外部認証 provider とし、Frontend は Clerk Vue SDK、Backend は Clerk session verification と Svix webhook verification を使う
- **API**: REST-based。FastAPI の OpenAPI 生成を contract 確認に活用する

## Frontend Standards

- Vue は `<script setup lang="ts">` を基本にする。
- URL を持つ複数画面は Vue Router で表現する。現在の基準 route は `/plants` と `/plants/:plantId`。
- API 通信は `src/api/` の typed client に集約し、component から直接 `fetch` しない。ユーザー所有データへの request は Clerk session token を付与する authenticated API client 経由にする。
- 画面状態はまず composable と page-local state で扱う。Pinia は、複数画面で共有する mutable state が明確になった段階で追加検討する。
- TypeScript では `any` を避け、API request/response/error は明示的な型で扱う。
- Styling は Tailwind CSS を基本に、mobile-first の spacing と readable text を優先する。
- 保護画面は route metadata と auth gate で囲み、認証状態の確認中や signed-out 状態ではユーザー所有データを描画しない。
- Presentation component は Clerk SDK や token 取得を直接扱わない。認証状態と API token injection は app bootstrap、auth component、composable、API client の境界に閉じる。

## Backend Standards

- Router は request/response mapping と HTTP error mapping を担当する。
- Service は use case と domain validation を担当し、FastAPI の `HTTPException` を投げない。
- Repository は SQLAlchemy `Session` を受け取り、create/list/get などの persistence operation を提供する。
- Pydantic/SQLModel schema は API JSON では camelCase を使い、Python 内部では snake_case を使う。
- Alembic migration は review 可能な形で作成し、SQLite と Turso/libSQL の互換性を意識する。
- Turso の URL は SQLAlchemy libSQL dialect で扱える形に正規化する。`libsql://...` と `sqlite+libsql://...` の差を接続層で吸収する。
- ユーザー所有データを扱う API は `CurrentUser` dependency を必須にする。認証失敗は 401、無効化・削除済みユーザーは 403、他ユーザー所有データの参照は存在を漏らさない 404 として扱う。
- Clerk User ID は認証元の識別子であり、domain data の所有者 ID として直接使わない。Backend は Clerk session を internal `users.id` に変換し、Service と Repository には internal owner id を渡す。
- owner は request body や query から受け取らず、必ず認証コンテキストから決定する。client から送られた user id / owner id は所有者判定に使わない。
- 認証・認可は fail closed にする。token、secret、raw claims、webhook signature などの検証情報を user-facing error や steering/spec に記載しない。
- Clerk webhook は署名検証済みイベントだけを application user 同期へ渡す。同期は冪等にし、削除済みユーザーを後着の update event で再有効化しない。

## Database And Type Policy

- Turso/libSQL を本番想定の主軸にする。
- ローカル開発・test・CI では SQLite を使えるようにし、同じ migration と CRUD path を通す。
- credential は `backend/.env` などの環境変数で扱い、steering や spec に secret 値を記載しない。
- UUID は text として保存・検証する。
- datetime は UTC ISO 文字列として API 表現と互換性検証を行う。DB driver 差分があるため、raw SQL の probe では Python `datetime` object を直接 bind しない。
- boolean は SQLite/libSQL の実態に合わせ、round-trip で truthy value として検証する。
- Application user は `users.id` を internal owner id として使い、provider 側 ID は unique mapping として保持する。
- すべてのユーザー所有 domain table は owner column を持ち、ownerless row を通常 path で作らない。API response/request schema に owner field を露出しない。

## Verification Commands

```bash
# Backend tests
cd backend
.venv/bin/pytest tests

# Local SQLite migration + owner-scoped CRUD smoke
cd backend
DATABASE_URL=sqlite:////private/tmp/green-log-smoke.db .venv/bin/python -m app.scripts.verify_turso_crud --mode local

# Turso migration + owner-scoped CRUD smoke
cd backend
.venv/bin/python -m app.scripts.verify_turso_crud --mode turso

# Frontend build
cd frontend
npm run build
```

## Long-Term Rule

Feature 固有の詳細な field、画面状態、API endpoint、受け入れ条件は specs に残す。steering には、新しい feature が同じ stack と境界で実装されるための長期方針だけを記載する。

Authentication / Authorization の恒久ルールは `auth.md` を source of truth とし、feature spec では対象 domain 固有の owner 適用点と検証観点だけを具体化する。

## 更新履歴

- updated_at: 2026-05-30 - Clerk、application user、owner scope、protected API の恒久ルールを反映。
