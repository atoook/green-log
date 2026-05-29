# Gap Analysis: auth-authorization-foundation

## 実施日
2026-05-29T16:07:13Z

## 前提
- 対象 spec: `auth-authorization-foundation`
- `spec.json.language`: `ja`
- `requirements` は生成済みだが未承認である。gap analysis は設計判断と要件修正の材料として実施した。
- 既存コードは Plant Registration の縦切りが実装済みで、backend test は `8 passed, 2 warnings`。

## Current State Investigation

### 既存アーキテクチャ
- Frontend は `frontend/src/types -> api -> composables -> components -> pages -> router -> App.vue` の依存方向で構成されている。
- Backend は `core/db -> models/schemas -> repositories -> services -> routers -> main.py` の layered architecture を採用している。
- Backend Service は `HTTPException` を投げず、Router が domain error を HTTP response へ変換している。
- API JSON は camelCase、Python 内部は snake_case。
- DB は Turso/libSQL を主軸にし、SQLite local/test/CI と同じ migration / CRUD path を通す方針。

### 既存実装
- `backend/app/models/plant.py`
  - `Plant` table は `id`, `name`, `acquired_date`, `memo`, `image_url`, `watering_cycle_days`, timestamps を持つ。
  - 所有者列は存在しない。
- `backend/app/repositories/plant_repository.py`
  - `create`, `list`, `get_by_id` がある。
  - `list` は全件、`get_by_id` は ID のみで取得するため、現在は user isolation がない。
- `backend/app/services/plant_service.py`
  - Plant validation と create/list/get orchestration を担当する。
  - current user や owner context は引数にない。
- `backend/app/routers/plants.py`
  - `GET /plants`, `POST /plants`, `GET /plants/{plant_id}` を提供する。
  - 認証 dependency はない。
- `backend/app/core/config.py`
  - DB と CORS 設定のみ。
  - Clerk secret、issuer、authorized party、webhook secret などは未定義。
- `backend/alembic/versions/0001_create_plants.py`
  - `plants` table initial migration のみ。
  - `users` table や owner FK は未作成。
- `frontend/src/api/plants.ts`
  - typed fetch wrapper は存在する。
  - Authorization header injection と 401 handling はない。
- `frontend/src/router/index.ts`
  - `/`, `/plants`, `/plants/:plantId` のみ。
  - protected route guard はない。
- `frontend/src/main.ts` / `frontend/src/App.vue`
  - Clerk provider や sign-in/out UI はない。

### 既存テスト
- `backend/tests/test_plants_api.py`
  - Plant create/list/detail、validation、404、CORS、settings parsing を検証。
  - 認証・認可・ユーザー分離の fixture は未整備。
- Frontend は build script はあるが、frontend test framework は未導入。
- Smoke script `backend/app/scripts/verify_turso_crud.py` は Plant CRUD と type round-trip を検証するが、認証や owner scope は扱わない。

### 外部依存調査メモ
- Clerk Vue docs では `@clerk/vue` の `SignedIn`, `SignedOut`, `SignInButton`, `UserButton`, `SignOutButton`, `Protect`, `useAuth` などが提供される。
- Clerk docs では session token を Authorization header または `__session` cookie から取得して検証する backend pattern が示されている。
- Clerk Python SDK docs では `clerk_backend_api` と `authenticate_request` による request authentication が示されている。ただし FastAPI/Starlette の `Request` と SDK 例の `httpx.Request` の接続方法は設計フェーズで確認が必要。
- Clerk webhook docs では `user.created`, `user.updated`, `user.deleted` を DB 同期へ使い、webhook 署名検証を行う方針が示されている。

## Requirement-to-Asset Map

| Requirement | Existing assets | Gap |
| --- | --- | --- |
| 1. 認証体験 | `frontend/src/main.ts`, `App.vue`, `router/index.ts`, Plant pages | **Missing**: Clerk provider、登録/ログイン/ログアウト UI、認証状態確認、保護 route、未認証時 UI。**Constraint**: 既存 UI 文言は「暮らし」「記録」寄りに保つ。 |
| 2. 保護 API の認証必須化 | `backend/app/routers/plants.py`, `main.py`, `core/config.py` | **Missing**: token extraction/verification dependency、401 mapping、protected route convention、auth settings。**Constraint**: Service は HTTP 例外を知らない方針を維持する。 |
| 3. アプリケーションユーザー管理 | DB engine/session、Alembic、SQLModel patterns | **Missing**: `User` model、schema、repository/service、migration、unique constraint、status lifecycle。**Unknown**: user id 生成を Python 側 UUID text にするか DB 側にするか。 |
| 4. 所有者の決定 | Plant create flow, typed request schemas | **Missing**: CurrentUser context、create 時 owner 設定、client-supplied owner の拒否/無視方針。**Constraint**: API JSON は camelCase、Python は snake_case。 |
| 5. 所有者スコープの認可 | `PlantRepository.list/get_by_id`, `PlantService` | **Missing**: owner-scoped list/get/update/delete convention、404 vs 403 policy、future domain reusable helper。**Constraint**: Repository は HTTP を知らない。 |
| 6. Plant Registration への初回適用 | Plant model/schema/repo/service/router/frontend pages | **Missing**: `plants.owner_user_id`, migration, owner-scoped Plant CRUD, existing local DB migration strategy, A/B user tests。**Constraint**: Plant response contract へ owner を露出しない方が既存 UI への影響を抑えやすい。 |
| 7. 認証プロバイダー同期 | `main.py`, router pattern, settings pattern | **Missing**: webhook endpoint, signature verification, idempotent user sync, deleted/disabled handling, webhook tests. **Unknown**: Python dependency choice for Svix/webhook verification. |
| 8. 認証失敗時の安全性 | `frontend/src/api/plants.ts` error mapping, backend HTTP mapping | **Missing**: 401/403 typed errors、frontend auth error state、session-expired handling、secret-safe error messages。**Constraint**: user-facing copy should stay simple and non-technical. |

## Key Gaps And Constraints

### Backend gaps
- 認証 dependency が存在しない。
- `users` table と application user lifecycle が存在しない。
- Clerk ID と internal user ID を分離する model がない。
- Plant に owner FK がないため、現在の API は全ユーザー共有状態。
- Repository interface が owner context を要求しないため、後続 domain でも認可漏れが起きやすい。
- Webhook の raw body / signature verification / idempotent sync path がない。
- TestClient の dependency override は DB session のみで、current user override pattern が未定義。

### Frontend gaps
- `@clerk/vue` が未導入。
- Vite env に Clerk publishable key がない。
- App root に Clerk provider がない。
- Header に signed-in/out state と logout/user menu がない。
- Vue Router に protected route guard がない。
- API client に async token provider を渡す仕組みがない。
- `ApiErrorType` に `auth` / `forbidden` などの分類がない。

### Data and migration gaps
- `users` migration と `plants.owner_user_id` migration が必要。
- 既存 local/Turso data の owner backfill 方針が未決定。
- `owner_user_id NOT NULL` を既存 `plants` に追加する場合、既存行がある環境では段階 migration または開発データ reset が必要。
- SQLite/libSQL の FK enforcement と migration 差分を smoke で検証する必要がある。

### Dependency gaps
- Backend requirements に Clerk SDK、JWT verification library、webhook signature verification library がない。
- Frontend dependencies に `@clerk/vue` がない。
- 依存追加により network install が必要になる。実装フェーズでは承認済み prefix の `npm install` はあるが、Python dependency install は承認が必要になる可能性がある。

## Implementation Approach Options

### Option A: Extend Existing Components
既存 Plant router/service/repository と existing API client に直接 auth/owner を足す。

**変更対象候補**
- `backend/app/routers/plants.py`: `get_current_user` dependency を追加。
- `backend/app/services/plant_service.py`: create/list/get に user id 引数を追加。
- `backend/app/repositories/plant_repository.py`: owner-scoped query に変更。
- `frontend/src/api/plants.ts`: token 取得と Authorization header を追加。
- `frontend/src/router/index.ts`: route guard を追加。

**Pros**
- 初期変更が少なく、Plant 適用だけなら速い。
- 既存テストを拡張しやすい。

**Cons**
- 認証・認可が Plant 実装に密結合しやすい。
- 後続 domain が同じ model を再利用しにくくなる。
- Webhook/user lifecycle の責務を置く場所が曖昧になりやすい。

**Effort / Risk**
- Effort: M
- Risk: Medium
- 理由: 既存構造に沿えるが、共通基盤としては責務分離が弱い。

### Option B: Create New Components
認証・ユーザー・認可の専用 module を作り、Plant はその interface を利用する。

**新規作成候補**
- `backend/app/models/user.py`
- `backend/app/schemas/user.py`
- `backend/app/repositories/user_repository.py`
- `backend/app/services/user_service.py`
- `backend/app/auth/` または `backend/app/security/` 相当の current user dependency
- `backend/app/routers/webhooks.py`
- `frontend/src/auth/` または `frontend/src/composables/useAuthState.ts`
- `frontend/src/api/client.ts` 共通 request wrapper

**Pros**
- 認証・認可基盤としての責務が明確。
- 後続 domain が current user と owner scope pattern を再利用しやすい。
- Webhook と user lifecycle を Plant から分離できる。

**Cons**
- 初期ファイル数と設計対象が増える。
- 既存の小さい codebase にはやや重く見える可能性がある。
- interface 設計を誤ると過剰抽象になる。

**Effort / Risk**
- Effort: L
- Risk: Medium
- 理由: 複数 layer と外部 provider integration を跨ぐが、責務分離は要件に合う。

### Option C: Hybrid Approach
共通 auth/user module を新設し、Plant と frontend API client は既存構造を最小拡張する。

**組み合わせ**
- Backend は `users` と current user dependency を新設する。
- Plant repository/service/router は owner 引数を受ける形に拡張する。
- Frontend は Clerk provider と protected route を追加し、既存 `plants.ts` を共通 request wrapper へ寄せる。
- Webhook は第2段階または同 spec 内の後続 task として追加する。

**Pros**
- 共通基盤の責務を確保しつつ、既存 Plant 実装を活かせる。
- 要件の「今後の全機能で再利用可能」と「Plant への初回適用」の両方に合う。
- 実装を縦スライスで分割しやすい。

**Cons**
- auth module と Plant 変更の両方を調整する必要がある。
- API client 共通化の範囲を設計フェーズで決めないと中途半端になる。
- Webhook を後ろに回す場合、lazy creation との整合を明確にする必要がある。

**Effort / Risk**
- Effort: L
- Risk: Medium
- 理由: 外部 auth、DB migration、frontend/backend 両方の cross-cutting change があるが、既存 pattern を大きく崩さず進められる。

## Recommended Direction For Design Phase

### 推奨候補
Option C: Hybrid Approach を第一候補として設計するのが妥当。

### 理由
- 認証・認可基盤は Plant 固有ではないため、Backend に current user / user lifecycle / webhook の独立した境界が必要。
- 一方で、既存 codebase はまだ小さく、Plant への適用は既存 router/service/repository を owner-aware に拡張する方が自然。
- Frontend も既存 `api/plants.ts` を完全置換するより、共通 request helper を切り出して Plant client を載せ替える方が移行リスクが低い。

## Design Phase Research Needed

1. **Clerk Python integration**
   - `clerk_backend_api` の `authenticate_request` を FastAPI/Starlette `Request` とどう接続するか。
   - SDK を使うか、JWKS + JWT library で手動検証するか。
   - token 検証時の `authorized_parties`, issuer, audience の設定方針。

2. **Webhook signature verification**
   - Python で Clerk/Svix webhook 署名を検証する依存ライブラリと実装形。
   - raw body を FastAPI router で安全に扱う方法。

3. **Migration/backfill strategy**
   - 既存 `plants` 行をどう扱うか。
   - 開発 DB reset でよいか、temporary owner/backfill を migration に含めるか。
   - Turso/libSQL で FK と NOT NULL owner 追加が同じ手順で通るか。

4. **Testing strategy**
   - current user dependency を TestClient で override する方針。
   - token verification を unit/integration でどこまで mock し、どこから smoke/manual check にするか。
   - frontend の auth state を build-only で確認するか、追加 test framework を導入するか。

5. **Frontend auth UX**
   - Clerk prebuilt UI をそのまま使うか、Green Mate の文言・トーンに合わせて wrapping するか。
   - 未認証時の `/plants` 表示を redirect にするか、同一画面内の sign-in prompt にするか。

## Suggested Vertical Slices

1. **Backend user identity slice**
   - `users` table、User model/repository、current user dependency、認証なし/無効認証の拒否。

2. **Frontend auth shell slice**
   - Clerk provider、header sign-in/out、protected route、API token injection。

3. **Plant owner scope slice**
   - `plants.owner_user_id`、owner-scoped create/list/get、A/B user separation tests。

4. **Failure and error handling slice**
   - 401/403/404 の typed handling、session expired UX、secret-safe messages。

5. **Webhook sync slice**
   - user created/updated/deleted event の idempotent sync と verification。

6. **Smoke and contract validation slice**
   - SQLite/Turso smoke、OpenAPI contract、frontend build。

## Overall Effort And Risk

- Effort: L
- Risk: Medium

理由: 認証 provider、DB migration、frontend route/API、backend dependency、Plant owner migration が絡む cross-cutting change である。一方、既存 layer は整理されており、実装対象 domain は Plant だけから開始できるため、段階化すれば制御可能。

## Immediate Design Inputs

- `users.id` は steering の UUID text 方針に合わせる候補が強い。
- `plants.owner_user_id` は response schema へ露出しない方向が既存 UX と API 利用範囲に合う。
- 他ユーザー所有の detail/update/delete は 404 とし、一覧は current user 所有分のみ返す方針が要件と合う。
- Webhook は application user 作成の必須経路ではなく、profile/status 同期の補助経路として扱うと初回ログイン時の user 作成要件を満たしやすい。
- Requirements 未承認のため、設計前に「未認証時 UX」「既存 Plant data の扱い」「disabled/deleted user の user-facing response」を確認すると手戻りが減る。

---

## Design Discovery Update

### Summary
- **Feature**: `auth-authorization-foundation`
- **Discovery Scope**: Complex Integration
- **Key Findings**:
  - Clerk Vue SDK は `clerkPlugin` と `VITE_CLERK_PUBLISHABLE_KEY` を使い、`SignedIn`, `SignedOut`, `SignInButton`, `UserButton`, `useAuth` を提供するため、Green Mate 側は auth UI と token injection を wrapper 化すればよい。
  - Clerk Python SDK は backend request authentication を提供し、secret key と authorized parties を使う。FastAPI `Request` との接続は `ClerkSessionVerifier` adapter に閉じる設計にした。
  - Clerk webhook は `user.created`, `user.updated`, `user.deleted` を同期対象にし、Svix 署名検証後に idempotent upsert/status update へ渡す。

## Research Log

### Clerk Vue SDK integration
- **Context**: Requirement 1 と Frontend auth shell の設計。
- **Sources Consulted**: Clerk Vue quickstart and component reference via Context7.
- **Findings**:
  - Vue app は `clerkPlugin` に publishable key を渡して初期化する。
  - `SignedIn`, `SignedOut`, `SignInButton`, `UserButton`, `SignOutButton`, `useAuth` が利用できる。
  - publishable key は frontend env であり secret ではない。
- **Implications**:
  - `main.ts` が Clerk provider を所有する。
  - `AuthGate.vue` と `AuthHeaderControls.vue` を作り、Plant component へ Clerk 依存を漏らさない。

### Clerk Python request authentication
- **Context**: Requirement 2, 3, 4, 8 の Backend current user 設計。
- **Sources Consulted**: Clerk Python SDK docs via Context7.
- **Findings**:
  - Python SDK は `authenticate_request` と authorized parties option を提供する。
  - SDK examples は `httpx.Request` を使うため、FastAPI/Starlette `Request` との bridging を設計上の明示境界にする必要がある。
- **Implications**:
  - `ClerkSessionVerifier` が SDK integration adapter となる。
  - Router/Service/Repository は Clerk SDK を直接 import しない。

### Webhook verification and user sync
- **Context**: Requirement 7 の user synchronization。
- **Sources Consulted**: Clerk webhook syncing docs and Svix Python library docs via Context7.
- **Findings**:
  - Clerk は user lifecycle event を webhook で提供する。
  - webhook は署名検証後に処理する必要がある。
  - Svix は webhook signature verification の Python library を提供する。
- **Implications**:
  - `WebhookRouter` が raw body と headers を扱い、`ClerkWebhookService` は検証済み event だけを処理する。
  - webhook は lazy upsert の補助同期とし、初回 API access の user 作成要件を阻害しない。

### FastAPI integration points
- **Context**: Protected route dependency と raw body webhook endpoint。
- **Sources Consulted**: FastAPI dependency/security/raw body docs via Context7.
- **Findings**:
  - FastAPI dependency injection は auth dependency を route に注入する設計に合う。
  - raw body は `Request.body()` で取得でき、OpenAPI の request body は必要に応じて明示できる。
- **Implications**:
  - `get_current_user` は dependency として Router 層に置く。
  - webhook endpoint は Pydantic parse 前の raw payload を verification に渡す。

## Architecture Pattern Evaluation

| Option | Description | Strengths | Risks / Limitations | Notes |
|--------|-------------|-----------|---------------------|-------|
| Extend Existing Components | Plant router/service/repository と API client に auth を直接追加 | 初期変更が少ない | 共通基盤として再利用しづらい | Plant 固有に寄りすぎるため不採用 |
| Create New Components | auth/user/authorization を完全分離 | 境界が明確 | 小さい codebase には重い | 一部採用 |
| Hybrid Boundary | auth/user は新設し、Plant は owner-aware に拡張 | 要件と既存構造の均衡がよい | file 数と調整点は増える | 採用 |

## Design Decisions

### Decision: Hybrid auth boundary
- **Context**: 認証・認可は後続 domain が使うが、最初の適用先は Plant。
- **Alternatives Considered**:
  1. Plant に直接 Clerk 認証を組み込む。
  2. 完全な provider abstraction を作る。
  3. auth/user は新設し、Plant は owner id を受ける。
- **Selected Approach**: Option 3。
- **Rationale**: Clerk 依存を auth 境界に閉じ、Plant は internal owner id だけを見るため、将来 domain が再利用しやすい。
- **Trade-offs**: 初期 file 数は増えるが、責務分離と testability が上がる。
- **Follow-up**: tasks では auth/user と Plant owner scope を別境界に分ける。

### Decision: Lazy upsert plus webhook sync
- **Context**: 初回ログイン時に application user が作成され、webhook 遅延に依存しない必要がある。
- **Alternatives Considered**:
  1. webhook-first。
  2. API lazy upsert only。
  3. lazy upsert を主経路、webhook を profile/status 補助同期。
- **Selected Approach**: Option 3。
- **Rationale**: 初回 API access の確実性と user status 同期の両方を満たす。
- **Trade-offs**: 同じ user に対する write 経路が複数になるため unique constraint と idempotency が必須。
- **Follow-up**: user service tests で duplicate request と duplicate webhook を検証する。

### Decision: Owner field hidden from Plant API payloads
- **Context**: client-supplied owner を信頼しない要件と既存 Plant contract の互換性。
- **Alternatives Considered**:
  1. `ownerUserId` を response に出す。
  2. request だけでなく response でも owner を隠す。
- **Selected Approach**: request/response とも owner を隠す。
- **Rationale**: owner は authorization invariant であり user-facing Plant 情報ではない。
- **Trade-offs**: debugging には DB/test helper が必要。
- **Follow-up**: OpenAPI contract と frontend type に owner が漏れないことを確認する。

## Risks & Mitigations
- Clerk Python SDK と FastAPI Request の adapter 実装差分 — `ClerkSessionVerifier` に隔離し、unit test で失敗時の mapping を固定する。
- 既存 Plant data の owner backfill — migration は explicit backfill config がない場合に停止し、ownerless data を作らない。
- Webhook retry/duplicate — `users.clerk_user_id` unique constraint と idempotent upsert で吸収する。
- Frontend token injection 漏れ — common `AuthenticatedApiClient` を通らない API client を review で禁止する。

## References
- Clerk Vue quickstart and components — `clerkPlugin`, `VITE_CLERK_PUBLISHABLE_KEY`, `SignedIn`, `SignedOut`, `SignInButton`, `UserButton`, `useAuth`
- Clerk Python SDK request authentication — `authenticate_request`, secret key, authorized parties
- Clerk webhook syncing docs — `user.created`, `user.updated`, `user.deleted`, verified webhook processing
- FastAPI dependency and raw request body docs — route dependencies and webhook raw body handling
- Svix Python webhook library docs — webhook signature verification
