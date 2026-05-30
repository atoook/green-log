# Project Structure

## Organization Philosophy

Green Mate は monorepo 内で Frontend、Backend、Product documentation、Feature specs を分離する。実装は feature の縦切りを作りながらも、Frontend と Backend の内部では layer ごとの責務を保つ。

新しい feature は、まず `.kiro/specs/` に要求・設計・タスクを残し、実装では既存 layer に沿って必要な file を追加する。steering は directory catalog ではなく、配置判断の基準として使う。

## Directory Patterns

### Frontend Application
**Location**: `frontend/`  
**Purpose**: Vue 3 / Vite / TypeScript の user-facing UI。routing、page composition、typed API client、presentation component を置く。  
**Pattern**: `src/types` → `src/api` → `src/composables` → `src/components` → `src/pages` → `src/router` → `App.vue` の依存方向を基本にする。認証 provider は app bootstrap、保護表示は auth component、token 付与は authenticated API client に置く。

### Backend Application
**Location**: `backend/`  
**Purpose**: FastAPI REST API、domain use case、persistence、migration、database connection を置く。  
**Pattern**: `core/db` → `models/schemas` → `repositories` → `services` → `routers` → `main.py` の依存方向を基本にする。認証 provider 連携、current user 解決、webhook 検証は domain layer から分離した auth 境界に置く。

### Authentication Boundary
**Location**: `backend/app/auth/`, `frontend/src/components/auth/`, authenticated API client/composable
**Purpose**: Clerk session を Green Mate の current user に変換し、保護画面と保護 API の共通入口を提供する。
**Pattern**: Provider SDK と token/session 検証は auth 境界に閉じる。Plant などの domain feature は Clerk を直接知らず、internal owner id を受け取って owner-scoped operation を実行する。

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
- 認証 UI や protected content gate は `src/components/auth/` に置き、domain component に認証 provider の詳細を持ち込まない。
- Composable は `src/composables/use*.ts` とし、API 呼び出しと page-local state orchestration を担当する。
- API client は `src/api/<domain>.ts` に置き、request/response/error type は `src/types/` と連携する。ユーザー所有データの client は common authenticated client を経由する。
- Route 定義は `src/router/` に集約する。

## Backend Naming And Placement

- Router は `app/routers/` に置き、HTTP method/path、status code、error mapping を担当する。
- Service は `app/services/` に置き、use case と domain validation を担当する。
- Repository は `app/repositories/` に置き、SQLAlchemy `Session` を使う persistence boundary とする。
- SQLModel table model は `app/models/`、API schema は `app/schemas/` に分ける。
- 認証 session verification、`CurrentUser` dependency、auth/webhook error type は `app/auth/` に置く。
- Application user lifecycle は通常 layer に沿って model / repository / service に置き、domain service には active な internal owner id だけを渡す。
- 認証 provider webhook の HTTP entrypoint は router に置くが、署名検証と event parsing は auth 境界、application user 反映は service 境界に分ける。
- DB engine/session は `app/db/`、runtime settings は `app/core/` に置く。
- Alembic 設定と migration は `backend/alembic*` 配下に置く。
- Smoke verification や one-off validation は `app/scripts/` に置き、feature 実装の完了条件とつなげる。

## Import And Dependency Rules

- Backend は上位 layer から下位 layer へ依存する。Repository から Router へ依存しない。
- Service は FastAPI に依存しない。HTTP 例外は Router で domain outcome から変換する。
- Domain layer は Clerk SDK に依存しない。Clerk claims は auth dependency と user service で internal user に変換してから domain に渡す。
- ユーザー所有データの Repository は owner id を query 条件に含める。list/detail/update/delete のいずれも owner scope を外した lookup を通常 API path に置かない。
- Frontend component は API client を直接呼ばず、page/composable 経由にする。
- Frontend presentation component は Clerk token や Authorization header を扱わない。
- Shared mutable state は導入理由が明確になるまで global store に置かない。
- Generated cache、build output、local DB、secret-bearing `.env` は project knowledge として扱わない。

## Spec And Steering Boundary

steering は長期的な原則を記載する場所である。たとえば「植物は鉢・個体単位で扱う」「Backend は layered architecture を守る」「Turso/libSQL と SQLite の互換性を検証する」は steering に置く。

一方、特定 feature の field 一覧、route 単位の acceptance criteria、task checklist、検証ログは `.kiro/specs/<feature>/` に残す。新しい code が既存 pattern に従うだけなら steering 更新は不要である。

Authentication / Authorization は全ユーザー所有 feature の横断前提であるため、`auth.md` とこの structure 方針に従う。個別 feature の specs には、その domain table や API が owner scope をどこで適用するかだけを記載する。

## 更新履歴

- updated_at: 2026-05-30 - auth 境界、application user lifecycle、owner-scoped domain 配置ルールを反映。
