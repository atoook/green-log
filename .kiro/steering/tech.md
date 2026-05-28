# Technology Stack

## Architecture

Green Log は `frontend/` と `backend/` を分けた monorepo 構成で開発する。Frontend は Backend の REST API に依存し、Backend が Plant などの永続化データの authoritative source になる。

Backend は Router / Service / Repository / Database の layered architecture を基本にする。HTTP の責務、domain validation、persistence を分け、Repository は HTTP 例外を知らない。

Frontend は route/page/composable/component/API client/type を分離する。ページは composition、composable は画面単位の状態、component は presentation と入力イベントを主責務にする。

## Core Technologies

- **Frontend**: Vue 3, Vite, TypeScript, Tailwind CSS, Vue Router
- **Backend**: FastAPI, Pydantic, SQLModel, SQLAlchemy Session, Alembic
- **Database**: Turso/libSQL を主軸とし、test/CI/local smoke では SQLite も利用可能にする
- **API**: REST-based。FastAPI の OpenAPI 生成を contract 確認に活用する

## Frontend Standards

- Vue は `<script setup lang="ts">` を基本にする。
- URL を持つ複数画面は Vue Router で表現する。現在の基準 route は `/plants` と `/plants/:plantId`。
- API 通信は `src/api/` の typed client に集約し、component から直接 `fetch` しない。
- 画面状態はまず composable と page-local state で扱う。Pinia は、複数画面で共有する mutable state が明確になった段階で追加検討する。
- TypeScript では `any` を避け、API request/response/error は明示的な型で扱う。
- Styling は Tailwind CSS を基本に、mobile-first の spacing と readable text を優先する。

## Backend Standards

- Router は request/response mapping と HTTP error mapping を担当する。
- Service は use case と domain validation を担当し、FastAPI の `HTTPException` を投げない。
- Repository は SQLAlchemy `Session` を受け取り、create/list/get などの persistence operation を提供する。
- Pydantic/SQLModel schema は API JSON では camelCase を使い、Python 内部では snake_case を使う。
- Alembic migration は review 可能な形で作成し、SQLite と Turso/libSQL の互換性を意識する。
- Turso の URL は SQLAlchemy libSQL dialect で扱える形に正規化する。`libsql://...` と `sqlite+libsql://...` の差を接続層で吸収する。

## Database And Type Policy

- Turso/libSQL を本番想定の主軸にする。
- ローカル開発・test・CI では SQLite を使えるようにし、同じ migration と CRUD path を通す。
- credential は `backend/.env` などの環境変数で扱い、steering や spec に secret 値を記載しない。
- UUID は text として保存・検証する。
- datetime は UTC ISO 文字列として API 表現と互換性検証を行う。DB driver 差分があるため、raw SQL の probe では Python `datetime` object を直接 bind しない。
- boolean は SQLite/libSQL の実態に合わせ、round-trip で truthy value として検証する。

## Verification Commands

```bash
# Backend tests
cd backend
.venv/bin/pytest tests

# Local SQLite migration + CRUD smoke
cd backend
DATABASE_URL=sqlite:////private/tmp/green-log-smoke.db .venv/bin/python -m app.scripts.verify_turso_crud --mode local

# Turso migration + CRUD smoke
cd backend
.venv/bin/python -m app.scripts.verify_turso_crud --mode turso

# Frontend build
cd frontend
npm run build
```

## Long-Term Rule

Feature 固有の詳細な field、画面状態、API endpoint、受け入れ条件は specs に残す。steering には、新しい feature が同じ stack と境界で実装されるための長期方針だけを記載する。

