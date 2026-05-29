# Project Structure

## Organization Philosophy

Green Mate は monorepo 内で Frontend、Backend、Product documentation、Feature specs を分離する。実装は feature の縦切りを作りながらも、Frontend と Backend の内部では layer ごとの責務を保つ。

新しい feature は、まず `.kiro/specs/` に要求・設計・タスクを残し、実装では既存 layer に沿って必要な file を追加する。steering は directory catalog ではなく、配置判断の基準として使う。

## Directory Patterns

### Frontend Application
**Location**: `frontend/`  
**Purpose**: Vue 3 / Vite / TypeScript の user-facing UI。routing、page composition、typed API client、presentation component を置く。  
**Pattern**: `src/types` → `src/api` → `src/composables` → `src/components` → `src/pages` → `src/router` → `App.vue` の依存方向を基本にする。

### Backend Application
**Location**: `backend/`  
**Purpose**: FastAPI REST API、domain use case、persistence、migration、database connection を置く。  
**Pattern**: `core/db` → `models/schemas` → `repositories` → `services` → `routers` → `main.py` の依存方向を基本にする。

### Product Documentation
**Location**: `docs/`  
**Purpose**: MVP、architecture、product direction など、人間が読む高位の文脈を置く。  
**Pattern**: 実装タスクの細部ではなく、プロダクトや architecture の判断背景を残す。

### Feature Specifications
**Location**: `.kiro/specs/`  
**Purpose**: feature ごとの requirements、design、tasks、research を置く。  
**Pattern**: feature 固有の詳細、boundary、受け入れ条件、検証履歴はここに残す。長期的な共通方針だけ `.kiro/steering/` に昇格する。

## Frontend Naming And Placement

- Page component は `src/pages/*Page.vue` に置き、route と screen composition を担当する。
- Reusable or feature presentation component は `src/components/<domain>/` に置く。
- Composable は `src/composables/use*.ts` とし、API 呼び出しと page-local state orchestration を担当する。
- API client は `src/api/<domain>.ts` に置き、request/response/error type は `src/types/` と連携する。
- Route 定義は `src/router/` に集約する。

## Backend Naming And Placement

- Router は `app/routers/` に置き、HTTP method/path、status code、error mapping を担当する。
- Service は `app/services/` に置き、use case と domain validation を担当する。
- Repository は `app/repositories/` に置き、SQLAlchemy `Session` を使う persistence boundary とする。
- SQLModel table model は `app/models/`、API schema は `app/schemas/` に分ける。
- DB engine/session は `app/db/`、runtime settings は `app/core/` に置く。
- Alembic 設定と migration は `backend/alembic*` 配下に置く。
- Smoke verification や one-off validation は `app/scripts/` に置き、feature 実装の完了条件とつなげる。

## Import And Dependency Rules

- Backend は上位 layer から下位 layer へ依存する。Repository から Router へ依存しない。
- Service は FastAPI に依存しない。HTTP 例外は Router で domain outcome から変換する。
- Frontend component は API client を直接呼ばず、page/composable 経由にする。
- Shared mutable state は導入理由が明確になるまで global store に置かない。
- Generated cache、build output、local DB、secret-bearing `.env` は project knowledge として扱わない。

## Spec And Steering Boundary

steering は長期的な原則を記載する場所である。たとえば「植物は鉢・個体単位で扱う」「Backend は layered architecture を守る」「Turso/libSQL と SQLite の互換性を検証する」は steering に置く。

一方、特定 feature の field 一覧、route 単位の acceptance criteria、task checklist、検証ログは `.kiro/specs/<feature>/` に残す。新しい code が既存 pattern に従うだけなら steering 更新は不要である。

