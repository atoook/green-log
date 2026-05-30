# Gap Analysis: plant-watering-care

実施日時: 2026-05-30T08:01:05Z

## 前提

- `requirements.generated` は true だが、`requirements.approved` はまだ false。設計前の差分把握として分析を実施した。
- 外部依存の追加は現時点で不要に見えるため、Web 調査は行っていない。
- 既存の `plant-registration` は水やり記録、今日のお世話、次回水やり予定日を範囲外として明示している。

## Current State Investigation

### Backend

- 既存の植物 domain は `models -> schemas -> repositories -> services -> routers` の薄い縦切りで実装されている。
- `backend/app/models/plant.py`
  - `Plant` は `owner_user_id`、`name`、`acquired_date`、`memo`、`image_url`、`watering_cycle_days`、`created_at`、`updated_at` を持つ。
  - `last_watered_at` や水やり履歴に相当する field/table は存在しない。
  - owner 用 index は `(owner_user_id, id)` のみ。
- `backend/app/repositories/plant_repository.py`
  - `create/list/get_by_id` のみ。
  - list/detail は owner scoped lookup を行う。
  - create は repository 内で commit/refresh する設計。
- `backend/app/services/plant_service.py`
  - 植物作成、一覧、詳細のみ。
  - Service は FastAPI 例外を投げない。
- `backend/app/routers/plants.py`
  - `GET /plants`、`POST /plants`、`GET /plants/{plant_id}` のみ。
  - `CurrentUser` dependency を通して internal owner id を service に渡す。
- `backend/app/main.py`
  - 現在 include されている domain router は plants と webhooks のみ。
- Alembic
  - `0001_create_plants.py` が plants を作成。
  - `0002_create_users_and_plant_owners.py` が users と plants.owner_user_id を追加。
  - 水やり用 migration は存在しない。
- Smoke
  - `backend/app/scripts/verify_turso_crud.py` は user upsert と Plant CRUD、ownerless plants の確認のみ。
  - 水やり table や ownerless watering records の確認は未実装。

### Auth / Owner Scope

- `backend/app/auth/dependencies.py` が Clerk session を application user に変換し、active user の internal owner id を返す。
- `auth.md` はすべてのユーザー所有 domain table に owner column を持たせ、API response に owner field を出さないことを要求している。
- 他ユーザー所有 resource は owner scoped lookup により 404 相当にする方針が既にテストされている。

### Frontend

- `frontend/src/router/index.ts`
  - route は `/plants` と `/plants/:plantId` のみ。
  - 今日のお世話 route は存在しない。
- `frontend/src/api/client.ts`
  - Clerk token 付き authenticated API client が既にある。
  - HTTP status を `auth/forbidden/not_found/validation/network/server` に正規化する。
- `frontend/src/api/plants.ts`
  - Plant API client は list/create/get のみ。
  - 水やり記録、今日のお世話、履歴の client は存在しない。
- `frontend/src/types/plant.ts`
  - `Plant` は基本情報と `wateringCycleDays` のみ。
  - `lastWateredAt`、`nextWateringDate`、`isDueToday`、`wateringHistory` に相当する型は存在しない。
- `frontend/src/composables/usePlants.ts` と `usePlantDetail.ts`
  - API 呼び出しと画面状態は composable に集約されている。
  - auth/forbidden 時に植物一覧を clear する既存方針がある。
- `frontend/src/components/plants/PlantList.vue`
  - 植物名、画像、水やり周期を表示。
  - 今日のお世話、最新水やり状態、記録操作は未実装。
- `frontend/src/components/plants/PlantDetail.vue`
  - 植物基本情報だけを表示。
  - 水やり状態、次回予定、履歴、記録操作は未実装。
- `frontend/src/App.vue` と `AuthGate.vue`
  - protected route の入口は既にある。
  - header navigation は `/plants` のみ。

### Tests

- Backend tests は pytest ベースで、`SQLModel.metadata.create_all` の in-memory SQLite を使う。
- `backend/tests/test_plants_api.py`
  - Plant CRUD、owner separation、auth required、inactive user 403、CORS、route policy を検証。
  - 現在は `watering`、`today`、`care`、`growth`、`photo`、`share` を含む route が存在しないことを検証している。
- `backend/tests/test_e2e_owner_model_regression.py`
  - app-level owner model の regression を検証。
  - こちらも adjacent domain routes が存在しないことを検証している。
- `backend/tests/test_backend_integration_contract.py`
  - main app の protected plant router、auth error contract、other-owner 404、validation secret safety を検証。
- Frontend 側に test runner や component tests は見当たらない。
  - 現時点の frontend validation は `npm run build` が中心。

## Requirement-to-Asset Map

| Requirement | Existing Assets | Gap |
| --- | --- | --- |
| 1 今日のお世話の表示 | protected route、authenticated API client、Plant list | Missing: 今日のお世話 route/page/API、due 判定、未記録/期限超過表示 |
| 2 水やり記録の作成 | Plant detail/list、owner scoped backend pattern | Missing: 水やり記録 model/schema/repository/service/router、record 作成 UI、成功/失敗 state |
| 3 最新水やり日時の表示 | Plant detail page、PlantRead schema | Missing: latest watering summary、detail response または care response、UI 表示 |
| 4 次回水やり予定日の表示 | `watering_cycle_days` | Missing: latest watering と周期からの日単位算出、未確定表示、更新後反映 |
| 5 水やり履歴の確認 | Plant detail page | Missing: 履歴保存、履歴取得、履歴表示、空状態 |
| 6 ユーザー所有データの保護 | CurrentUser、owner scoped Plant pattern、auth tests | Missing: watering domain への owner column/lookup/response 非公開適用、other-owner tests |
| 7 空状態と失敗時の案内 | Plant list/detail の loading/error UI | Missing: care/today/history 固有の loading/error/empty UI |
| 8 MVP らしい体験と言葉づかい | 既存 UI は「記録」「お世話」寄り | Missing: watering UI 文言と mobile 表示確認 |
| 9 将来機能との境界 | Plant spec と tests で adjacent route 不在を固定 | Constraint: 新 feature 追加に合わせ既存の route policy tests を更新し、通知/skip/他 care 種別は追加しない |

## Key Gaps And Constraints

### Data / Persistence

- Missing: 水やり履歴を保存する永続化 asset。
- Missing: Plant の最新水やり日時 summary を持つ場合の migration。
- Missing: 水やり table に対する owner scope、foreign key、index。
- Constraint: SQLite と Turso/libSQL の互換性を保つ必要がある。
- Constraint: datetime は UTC ISO 文字列として API 表現と互換性を検証する方針。
- Research Needed: 「今日」の基準を server UTC date、client local date、将来の user timezone のどれに寄せるか。MVP は日単位要件だが、通知拡張では timezone が重要になる。

### Backend Domain Flow

- Missing: 水やり記録作成と最新水やり日時更新を一貫して扱う use case。
- Constraint: 既存 repository は `create` 内で commit するため、複数 entity 更新を 1 operation にまとめる場合は transaction 境界の設計が必要。
- Missing: 今日のお世話一覧を返す read model。
- Missing: detail 用に水やり状態と履歴を返す read model。
- Research Needed: Plant list/detail response を拡張するか、care/watering 専用 endpoint で read model を返すか。

### Frontend Flow

- Missing: 今日のお世話 page/route。
- Missing: 水やり API client と composable。
- Missing: record 作成後に今日のお世話一覧、植物詳細、履歴を再取得または局所更新する state flow。
- Constraint: presentation component は API token を扱わない既存方針。
- Constraint: header navigation と protected route meta の更新が必要。

### Tests / Verification

- Missing: watering API tests、owner separation tests、unauthenticated tests、other-owner 404 tests、route registration tests。
- Missing: migration tests for watering tables/columns/indexes。
- Missing: smoke verification for watering CRUD and ownerless watering rows。
- Constraint: 既存 tests は watering/care route 不在を明示的に期待しているため、新 feature の route を追加する際に意図的に更新が必要。
- Frontend は build verification が主。UI の振る舞いは型と build で最低限確認し、必要なら後続で component/e2e test 導入を検討する。

## Implementation Approach Options

### Option A: Plant 拡張中心

**概要**
- Plant に最新水やり日時を追加し、水やり記録の永続履歴は持たないか最小化する。
- 既存 Plant API/list/detail を拡張して、今日のお世話判定と次回予定日表示を実現する。

**主な変更候補**
- `backend/app/models/plant.py`
- `backend/app/schemas/plant.py`
- `backend/app/repositories/plant_repository.py`
- `backend/app/services/plant_service.py`
- `backend/app/routers/plants.py`
- `frontend/src/types/plant.ts`
- `frontend/src/api/plants.ts`
- `frontend/src/composables/usePlants.ts`
- `frontend/src/components/plants/*`

**Pros**
- 実装面積が最小。
- 既存の Plant CRUD と UI をそのまま活用しやすい。
- MVP の「最新状態」と「今日のお世話」だけなら速く到達できる。

**Cons**
- Requirement 5 の履歴確認を満たしにくい。
- 将来の履歴編集、分析、通知、カレンダー連携が弱い。
- Plant が基本情報と care event の責務を抱えやすい。

**評価**
- Effort: S から M。
- Risk: Medium。要件の履歴要件と discovery の履歴 source of truth 方針に合わない可能性が高い。

### Option B: Watering domain 新設中心

**概要**
- Watering 用の model/schema/repository/service/router/frontend slice を新設する。
- 最新水やり日時と次回予定日は履歴から都度算出し、Plant には summary を追加しない。

**主な変更候補**
- 新規 `backend/app/models/watering_record.py`
- 新規 `backend/app/schemas/watering.py`
- 新規 `backend/app/repositories/watering_repository.py`
- 新規 `backend/app/services/watering_service.py`
- 新規 `backend/app/routers/watering.py`
- 新規 Alembic migration
- 新規 `frontend/src/types/watering.ts`
- 新規 `frontend/src/api/watering.ts`
- 新規 `frontend/src/composables/useWatering*`
- 新規 `frontend/src/components/watering/*`
- 新規/更新 `frontend/src/pages/*`

**Pros**
- 責務分離が明確。
- 水やり履歴が source of truth になり、Requirement 5 と将来拡張に強い。
- Plant basic info の肥大化を避けやすい。

**Cons**
- 今日のお世話や一覧で毎回最新記録を探す必要があり、実装と query がやや複雑。
- 植物数が増えると集計 query/index 設計が必要になる。
- MVP の表示更新で複数 endpoint 間の整合を考える必要がある。

**評価**
- Effort: M。
- Risk: Medium。query 設計と日付基準の決定が必要だが、既存 layer pattern には合う。

### Option C: Hybrid - WateringRecord + Plant latest summary

**概要**
- 水やり履歴は専用 domain として保存し、Plant には最新水やり日時 summary を追加する。
- 水やり記録作成時に履歴作成と summary 更新を同じ use case として扱う。
- 次回水やり予定日は保存せず、最新水やり日時と水やり周期から read model で算出する。

**主な変更候補**
- Option B の新規 watering domain files
- `backend/app/models/plant.py` に `last_watered_at` 相当の nullable field
- `backend/app/repositories/plant_repository.py` に summary 更新用 method
- Plant read model または care read model の追加
- Alembic migration で watering records table と plants summary column を追加
- Frontend は watering 専用 API/composable/components と既存 Plant detail/list の一部表示拡張

**Pros**
- Requirement 3 と 5 を両立しやすい。
- 今日のお世話判定が単純になり、MVP 性能にも合う。
- 将来、履歴から summary を再構築できる設計にしやすい。
- Discovery brief の方針に最も近い。

**Cons**
- 履歴と summary の整合性が新しいリスクになる。
- transaction 境界や rollback 時の扱いを設計で明確にする必要がある。
- 既存 repository の commit-per-method と相性を確認する必要がある。

**評価**
- Effort: M。
- Risk: Medium。実装面積は増えるが、要件と将来拡張のバランスがよい。

## Compatibility Assessment

- Backend layering には新規 watering slice を足しやすい。
- 既存 auth dependency と owner scoped repository pattern は再利用できる。
- API response の camelCase 変換は既存 `alias_config` を再利用できる。
- Existing tests は route absence を固定している箇所があるため、feature 追加時に failure するのは想定内。設計/実装で route policy tests を新しい境界に更新する必要がある。
- Frontend は typed API client と composable 境界が明確なため、新規 watering client/composable を追加しやすい。
- ただし frontend test はないため、build と手動/ブラウザ確認に依存しやすい。

## Design Phase Recommendations

### Preferred Direction To Evaluate

- Option C を第一候補として詳細設計する価値が高い。
- 理由:
  - 履歴確認、最新状態、今日のお世話を同時に満たせる。
  - 既存 Plant が水やり周期を持つため、Plant summary との組み合わせで MVP の due 判定が単純になる。
  - `next_watering_date` を保存しない方針なら、周期変更時の保存済み予定日の不整合を避けられる。

### Design Decisions Needed

1. 水やり記録の作成時刻を server generated にするか、client から任意日時を受け取るか。
   - MVP 要件は「水やりしたことを記録」なので server generated が単純。
   - 過去記録の登録は要件外だが、将来拡張の余地は設計に残せる。
2. 今日のお世話 endpoint をどの単位で設けるか。
   - 例: `/care/today`、`/watering/today`、`/plants/due-watering`。
   - Product 文言は「お世話」寄りだが、domain は水やりだけなので route 境界は要検討。
3. Plant detail で水やり状態を返す方法。
   - Plant detail response を拡張するか、Plant detail page が watering detail endpoint を別取得するか。
4. 「今日」の日付基準。
   - MVP は UTC date か browser local date のどちらかを明確にする必要がある。
   - 将来通知では user timezone 設定が必要になる可能性が高い。
5. 履歴表示件数。
   - Requirement は基本履歴の表示のみで、全件/最新 N 件/pagination は未確定。
   - MVP は最新 N 件に絞る方が UI と性能面で扱いやすいが、要件または設計で明示が必要。
6. Transaction 境界。
   - Watering record 作成と Plant summary 更新を同一 commit にするか。
   - 既存 repository commit pattern を踏まえ、service が atomic operation を制御できる形にするか検討が必要。

### Tests To Plan

- Backend API
  - 今日のお世話一覧: due today、overdue、not due、未記録、0 件。
  - 水やり記録作成: success、missing plant、other-owner 404、unauthenticated 401、inactive 403。
  - detail/history: latest record selection、empty history、owner separation、owner fields hidden。
- Migration
  - watering records table/columns/indexes/foreign keys。
  - plants latest summary column を採用する場合も実運用前前提のため、legacy dual-read や backfill は不要。migration は nullable column 追加で扱う。
- App-level contract
  - new protected route registration。
  - secret-safe error contract。
  - other-owner existence hiding。
- Smoke
  - local SQLite と Turso path で user、plant、watering record、ownerless watering row check。
- Frontend
  - `npm run build`。
  - ブラウザ確認: 今日のお世話 empty/due、記録後の状態更新、detail 履歴、auth gate。

## Overall Effort And Risk

- Effort: M (3-7 days)
  - 新規 backend domain、migration、複数 API、frontend route/page/components、既存 tests 更新が必要。
- Risk: Medium
  - 既存 architecture とは整合するが、日付基準、履歴と summary の整合、route 境界、transaction 境界で設計判断が必要。

## Research Needed For Design Phase

- 日付基準: MVP の「今日」を UTC、server local、browser local のどれで扱うか。
- API shape: 今日のお世話、植物詳細水やり状態、履歴取得、記録作成の endpoint 境界。
- Summary strategy: Plant に latest summary を持つ場合の整合性回復方法。
- History scope: MVP の履歴表示件数と paging の有無。
- Verification scope: Turso smoke に watering CRUD をどこまで入れるか。

---

# Design Discovery & Synthesis: plant-watering-care

実施日時: 2026-05-30T08:08:23Z

## Summary

- **Feature**: `plant-watering-care`
- **Discovery Scope**: Extension
- **Key Findings**:
  - 既存 Plant/Auth/Frontend の縦切りに新しい watering slice を追加するのが最も整合する。
  - 外部依存は追加不要。既存の FastAPI / SQLModel / Alembic / Vue 3 / typed API client で実装できる。
  - 既存 route policy tests は watering/care/today route 不在を固定しているため、feature 実装時に新しい境界へ更新する必要がある。

## Research Log

### 既存統合点
- **Context**: Plant Watering Care は既存 Plant Registration の水やり周期と植物個体に依存する。
- **Sources Consulted**: `backend/app/models/plant.py`, `backend/app/repositories/plant_repository.py`, `backend/app/services/plant_service.py`, `backend/app/routers/plants.py`, `frontend/src/api/plants.ts`, `frontend/src/composables/usePlants.ts`, `frontend/src/composables/usePlantDetail.ts`, `frontend/src/router/index.ts`
- **Findings**:
  - Backend は Router / Service / Repository / Model / Schema の分離が明確。
  - Frontend は types -> api -> composables -> components -> pages -> router の依存方向を持つ。
  - Plant detail は植物基本情報だけを扱い、水やり状態を別 composable/component として追加できる。
- **Implications**:
  - Watering は新規 domain slice として追加し、既存 Plant API を大きく膨らませない。
  - Plant model には latest summary のみ追加し、履歴そのものは WateringRecord に分ける。

### 認証と owner scope
- **Context**: 水やり記録はユーザー所有の private data であり、他ユーザーの存在を漏らしてはならない。
- **Sources Consulted**: `.kiro/steering/auth.md`, `backend/app/auth/dependencies.py`, `backend/tests/test_plants_api.py`, `backend/tests/test_backend_integration_contract.py`
- **Findings**:
  - CurrentUser は internal application user id を返す。
  - Plant detail は owner scoped lookup により other-owner 404 を実現している。
  - API response は owner id や Clerk ID を返さない方針が既に固定されている。
- **Implications**:
  - WateringRecord も owner_user_id を持つ。
  - plant_id だけで record を作らず、必ず owner scoped Plant lookup を通してから作成する。

### 日付基準と future notification
- **Context**: 要件は日単位の今日のお世話を求めるが、ユーザー timezone 設定は scope 外。
- **Sources Consulted**: `.kiro/specs/plant-watering-care/requirements.md`, `.kiro/specs/plant-watering-care/brief.md`, `.kiro/steering/tech.md`
- **Findings**:
  - datetime の API 表現は UTC ISO 文字列が steering 方針。
  - 通知設定、通知時刻、通知権限は範囲外。
- **Implications**:
  - MVP の `today` 判定は backend UTC date を authoritative にする。
  - timezone-aware notification が入る場合は、date basis と schedule storage の再検討を revalidation trigger にする。

## Architecture Pattern Evaluation

| Option | Description | Strengths | Risks / Limitations | Notes |
|--------|-------------|-----------|---------------------|-------|
| Plant 拡張中心 | Plant に最新水やり日時を追加し、Plant API を中心に表示する | 実装が小さい | 履歴要件と将来拡張に弱い | 採用しない |
| Watering domain 新設 | 水やり履歴と計算をすべて Watering domain に置き、Plant に summary を持たない | 責務分離が強い | 今日のお世話判定と一覧が重くなりやすい | 単独採用しない |
| Hybrid | WateringRecord を履歴 source of truth、Plant に `last_watered_at` summary、予定日は計算 | 要件と MVP 性能のバランスがよい | summary 整合性と transaction 境界の設計が必要 | 採用 |

## Design Decisions

### Decision: Hybrid summary model
- **Context**: 最新水やり日時、履歴、今日のお世話を同時に満たす必要がある。
- **Alternatives Considered**:
  1. Plant に最新日時だけ保存する
  2. 履歴だけ保存して毎回集計する
  3. 履歴を保存し Plant に最新 summary を持つ
- **Selected Approach**: WateringRecord を source of truth とし、Plant の `last_watered_at` を派生 summary として更新する。
- **Rationale**: 履歴確認と今日のお世話の効率を両立でき、Discovery brief の方針とも一致する。
- **Trade-offs**: summary 整合性が新しいリスクになる。
- **Follow-up**: record 作成と summary 更新を同一 transaction で扱い、必要なら履歴から summary を再構築する検証 script を後続で検討する。

### Decision: Dedicated care and watering endpoints
- **Context**: Plant Registration の責務を植物基本情報に保ちたい。
- **Alternatives Considered**:
  1. `GET /plants` と `GET /plants/{plant_id}` を全面拡張する
  2. `/care/today` と `/plants/{plant_id}/watering` 系 endpoint を追加する
- **Selected Approach**: `/care/today` を今日のお世話 read model、`/plants/{plant_id}/watering` を植物別水やり状態、`/plants/{plant_id}/watering-records` を記録作成として定義する。
- **Rationale**: Product 文言の「今日のお世話」と domain 操作の「水やり記録」を分けられる。
- **Trade-offs**: frontend detail page は Plant と Watering の 2 つの API を扱う。
- **Follow-up**: 実装時は retry と partial failure 表示を composable で明確化する。

### Decision: No new dependencies
- **Context**: 日付計算と CRUD は既存 stack で実装できる。
- **Alternatives Considered**:
  1. date utility library を導入する
  2. Python/Vue 標準機能で扱う
- **Selected Approach**: 新しい dependency は追加しない。
- **Rationale**: MVP の日付計算は `date` と UTC ISO datetime で十分であり、依存追加のコストを避ける。
- **Trade-offs**: timezone-aware scheduling はこの設計では扱わない。
- **Follow-up**: 通知や timezone 設定が入る場合は改めて日付ライブラリや schedule state を評価する。

### Decision: MVP date basis is backend UTC date
- **Context**: 「今日」の基準が未設定のままでは API と UI がずれる。
- **Alternatives Considered**:
  1. browser local date を API に渡す
  2. backend UTC date を authoritative にする
  3. user timezone profile を追加する
- **Selected Approach**: MVP では backend UTC date を authoritative にする。
- **Rationale**: user timezone profile と通知設定は scope 外であり、backend が一貫した判定とテストを提供できる。
- **Trade-offs**: local midnight 付近ではユーザー感覚の「今日」とずれる可能性がある。
- **Follow-up**: timezone profile、通知時刻、通知送信が追加される場合は revalidation する。

## Risks & Mitigations

- Summary inconsistency — record 作成と Plant summary 更新を同一 service transaction に閉じる。
- Existing route policy tests failure — watering/care route を許可する regression test へ更新する。
- Date boundary mismatch — MVP は UTC date と明記し、timezone feature 追加時の revalidation trigger にする。
- Frontend partial failure — Plant basic information と watering state の失敗表示を分け、基本情報をできるだけ維持する。

## References

- `.kiro/steering/product.md` — お世話、記録、private data のプロダクト方針
- `.kiro/steering/tech.md` — stack、datetime、owner scope、verification command
- `.kiro/steering/structure.md` — backend/frontend の配置と dependency direction
- `.kiro/steering/auth.md` — owner scope、protected API、field 非公開ルール
- `.kiro/specs/plant-watering-care/research.md` — gap analysis
