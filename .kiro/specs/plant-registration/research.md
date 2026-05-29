# Research & Design Decisions

## Summary
- **Feature**: `plant-registration`
- **Discovery Scope**: Simple Addition
- **Key Findings**:
  - 現状コードは backend が FastAPI の root route のみ、frontend が Vite 初期画面のみで、既存の植物ドメイン実装はない。
  - `docs/mvp.md` と `docs/architecture.md` は Router / Service / Repository / Database、REST、OpenAPI-first、Mobile First を明示しているため、その方針に沿った最小の縦切りにする。
  - SQLModel と FastAPI の公式ドキュメントは、table model と create/read schema の分離、Session dependency、`response_model`、404 の `HTTPException` を推奨パターンとして示している。
  - Turso 公式ドキュメントは SQLAlchemy 用に `sqlalchemy-libsql` と `sqlite+libsql` dialect URL を示しているが、package は experimental/beta 扱いのため、Plant Registration 実装時点で migration + CRUD を Turso 接続で早期検証する必要がある。

## Research Log

### 既存コード構成
- **Context**: Plant Registration を既存構成へ追加するため、現状の拡張点を確認した。
- **Sources Consulted**: `backend/app/main.py`, `backend/requirements.txt`, `frontend/src/App.vue`, `frontend/src/components/HelloWorld.vue`, `frontend/src/style.css`, `frontend/package.json`, `docs/mvp.md`, `docs/architecture.md`
- **Findings**:
  - Backend は `FastAPI(title="Green Mate API")` と root route のみ。
  - Frontend は Vite 初期 UI で、routing、API client、domain type、store は未作成。
  - backend dependencies には FastAPI、Pydantic、SQLModel、SQLAlchemy、Alembic、python-dotenv、uvicorn が含まれる。
  - frontend dependencies は Vue のみで、Vue Router や Pinia は未導入。
- **Implications**:
  - 新しい domain file 群を作っても既存実装との競合は小さい。
  - MVP でも複数画面構成になるため、Vue Router を初期導入する。
  - Plant Registration 時点では複数画面で共有する mutable state が明確ではないため、Pinia は導入しない。
  - Tailwind CSS は project stack に含まれるが未導入のため、実装タスクで setup が必要。

### FastAPI と SQLModel の CRUD パターン
- **Context**: Plant 基本情報を保存・取得する API contract と persistence pattern を決める必要がある。
- **Sources Consulted**: Context7 `/fastapi/fastapi`, Context7 `/websites/sqlmodel_tiangolo`
- **Findings**:
  - FastAPI は Pydantic model による request body validation と response model による response serialization/documentation を提供する。
  - SQLModel の FastAPI examples は table model と create/public schema を分け、Session dependency で session を注入する。
  - 作成時は model validation 後に `session.add`, `session.commit`, `session.refresh` で永続化後の row を返すパターンが示されている。
  - 詳細取得で対象が存在しない場合は `HTTPException(status_code=404)` を返すパターンが示されている。
- **Implications**:
  - Plant は `Plant` table model、`PlantCreate` request schema、`PlantRead` response schema に分離する。
  - Router は response model を明示し、OpenAPI 上の contract を安定させる。
  - Repository は SQLModel session を受け取り、Service は validation と domain policy を集約する。

### Turso/libSQL と SQLAlchemy 接続
- **Context**: レビューで、単純な local SQLite 接続だけではなく Turso/libSQL dialect を利用した接続構成と migration 動作を早期検証対象に含める必要が示された。
- **Sources Consulted**: Turso SQLAlchemy docs, Turso libSQL docs, PyPI `sqlalchemy-libsql`, Alembic autogenerate docs
- **Findings**:
  - Turso の SQLAlchemy docs は `pip install sqlalchemy-libsql` と、`sqlite+libsql` dialect を使った remote、embedded replica、memory、local の engine examples を示している。
  - Remote Turso 接続では `TURSO_DATABASE_URL` と `TURSO_AUTH_TOKEN` を環境変数に置き、`connect_args` に auth token を渡す。
  - libSQL は SQLite fork で、Turso docs は SQLite 互換性を説明している。ただし Turso Database と libSQL の成熟度・エンジン差分は分けて扱われている。
  - PyPI 上の `sqlalchemy-libsql` 0.2.0 は SQLAlchemy dialect for libSQL で、experimental かつ beta classifier が付いている。
  - Alembic autogenerate は target metadata と現在の database schema を比較するが、CHECK constraint など一部の差分検出は dialect により制限されるため、migration file は手動 review が必要。
- **Implications**:
  - `backend/app/db/engine.py` は local SQLite と Turso/libSQL を database URL で切り替える設計にする。
  - `backend/requirements.txt` には `sqlalchemy-libsql` を追加する。
  - Alembic は同じ `DATABASE_URL` 解決関数を使い、local SQLite と Turso の両方に upgrade を実行できることを検証する。
  - Plant Registration の実装完了条件に、Turso 接続で initial migration、POST/GET CRUD smoke test、型 round trip の確認を含める。

### Vue 3 と Vue Router の最小画面構成
- **Context**: 登録、一覧、詳細をユーザーが試せる複数画面構成にするが、MVP 初期で global state を過剰に増やさない。
- **Sources Consulted**: Context7 `/vuejs/vue`, Context7 `/websites/router_vuejs`, `frontend/package.json`
- **Findings**:
  - Vue 3 Composition API は `reactive` と `computed` で local state と derived state を扱える。
  - `<script setup>` は現行構成と相性がよく、TypeScript の型定義を component 内外で利用できる。
  - typed props/emits を使えば presentation component の contract を保てる。
  - Vue Router 4 は Vue 3 の公式 router で、`createRouter`, `createWebHistory`, route records, `router-view` による SPA routing を提供する。
  - Vue Router は route params を string 系として扱うため、`plantId` は page boundary で number に変換・検証する必要がある。
- **Implications**:
  - `/plants` と `/plants/:plantId` を初期 route として定義する。
  - `PlantsPage` と `PlantDetailPage` を page boundary とし、`usePlants` は list/create、`usePlantDetail` は detail fetch を担当する。
  - `PlantForm`, `PlantList`, `PlantDetail` は typed props/emits を持つ presentation component とする。
  - Pinia は初期 MVP では導入せず、複数画面で共有する状態が明確になった段階で再検討する。

## Architecture Pattern Evaluation

| Option | Description | Strengths | Risks / Limitations | Notes |
|--------|-------------|-----------|---------------------|-------|
| Layered CRUD | Router / Service / Repository / Database と API client / composable / components に分ける | docs の architecture と一致し、後続機能が Plant contract を参照しやすい | 小規模にはややファイル数が増える | 採用 |
| Direct endpoint CRUD | Router から直接 DB を操作する | 最短で実装できる | 後続の水やりや写真機能で domain policy が散らばる | 不採用 |
| Vue Router with local composables | Vue Router で page を分け、状態は page/local composable で保持する | 複数画面 URL を初期から扱え、Pinia なしで過剰な共有状態を避けられる | list state と detail state の再取得が発生しうる | 採用 |
| Full frontend routing and global store | Router と store を初期から導入する | 画面数が増えた後に拡張しやすい | Plant Registration 時点では共有状態が未確定 | Pinia は不採用 |

## Design Decisions

### Decision: Plant 基本情報の単一 aggregate
- **Context**: 登録単位は植物種ではなく、ユーザーが所有する鉢・個体である。
- **Alternatives Considered**:
  1. 植物種 master と所有個体を分離する。
  2. 所有個体だけを Plant として扱う。
- **Selected Approach**: 所有個体を `Plant` aggregate とし、`name`, `acquiredDate`, `memo`, `imageUrl`, `wateringCycleDays` を直接保持する。
- **Rationale**: MVP の user value に直結し、植物図鑑や育成ガイドを境界外に保てる。
- **Trade-offs**: 種別情報の再利用は後回しになるが、登録体験が単純になる。
- **Follow-up**: 後続で植物種 master を追加する場合は Plant contract の再検証が必要。

### Decision: 画像は URL 文字列として扱う
- **Context**: 要件は `imageUrl` の保存・表示であり、画像アップロードは対象外。
- **Alternatives Considered**:
  1. ファイルアップロードと storage を同時に導入する。
  2. `imageUrl` の文字列保存に限定する。
- **Selected Approach**: API と UI は `imageUrl` を任意の文字列 URL として受け取り、表示時に画像読み込み失敗の fallback を出す。
- **Rationale**: MVP の範囲を守り、storage や認証の導入を避けられる。
- **Trade-offs**: ユーザーが直接画像をアップロードする体験は提供しない。
- **Follow-up**: Growth Photo Log または upload spec で storage contract を定義する。

### Decision: Frontend は Vue Router と local composable で構成する
- **Context**: MVP でも複数画面構成になるため routing は初期から必要だが、Plant Registration 時点では Pinia を必要とする共有状態は未確定である。
- **Alternatives Considered**:
  1. Vue Router と Pinia を同時に追加する。
  2. Vue Router を追加し、状態は page/local composable で管理する。
  3. App 内 view state だけで画面を切り替える。
- **Selected Approach**: Vue Router を `src/router/index.ts` に導入し、`/plants` と `/plants/:plantId` を route として定義する。API client を `src/api/plants.ts` に置き、`usePlants` が list/create、`usePlantDetail` が detail fetch を管理する。
- **Rationale**: MVP の複数画面構成に必要な URL と navigation を初期から確保しつつ、Pinia 導入による global state の先回りを避けられる。
- **Trade-offs**: 一覧から詳細へ移動した際に detail は route param を基準に再取得する。状態共有最適化は後続に回す。
- **Follow-up**: Today's Care、Calendar、Growth Photo Log などで Plant list や user session を複数画面が共有する必要が明確になった時点で Pinia 導入を再検討する。

### Decision: Database 接続は local SQLite と Turso/libSQL を同じ contract で扱う
- **Context**: Production target は Turso/libSQL であり、local SQLite のみで実装を進めると migration と型保存の互換性リスクが後段で露見する。
- **Alternatives Considered**:
  1. Local SQLite だけで Plant Registration を実装し、Turso は deploy 前に検証する。
  2. Plant Registration の時点で `sqlalchemy-libsql` を導入し、local SQLite と Turso の両方で migration + CRUD を検証する。
- **Selected Approach**: `DATABASE_URL` により `sqlite:///...` と `sqlite+libsql://...` を切り替える。Turso remote は `TURSO_DATABASE_URL` と `TURSO_AUTH_TOKEN` を使い、Alembic と runtime が同じ engine factory を通る。
- **Rationale**: 最初の table と CRUD が最小である段階なら、dialect、migration、型保存の問題を低コストで切り分けられる。
- **Trade-offs**: 初期実装に環境変数と external database smoke test が増える。`sqlalchemy-libsql` は experimental なので、問題が出た場合は dialect 起因か model/migration 起因かを切り分ける必要がある。
- **Follow-up**: Turso で Alembic migration が不安定な場合、manual SQL migration または Turso CLI migration workflow を別 spec/decision として検討する。

### Decision: SQLite 互換を優先した型保存方針
- **Context**: Plant Registration では integer ID、date、datetime が必要で、後続機能では UUID と boolean が必要になる可能性が高い。local SQLite と Turso/libSQL 間で round trip の差分を避けたい。
- **Alternatives Considered**:
  1. Python/SQLAlchemy の抽象型に全面的に任せる。
  2. SQLite 互換の物理表現を明示し、application boundary で型変換する。
- **Selected Approach**: UUID は canonical string、datetime は UTC ISO 8601 string または SQLAlchemy DateTime の round trip を検証してから固定、boolean は INTEGER 0/1 相当として扱える SQLAlchemy Boolean を使い、Turso 上の保存値を確認する。
- **Rationale**: SQLite 系 DB は型 affinity の影響を受けるため、早期に保存表現を固定すると後続 domain の migration risk が下がる。
- **Trade-offs**: Plant Registration で直接使わない UUID/boolean も smoke table または validation script で検証対象に含める。
- **Follow-up**: 検証結果を `research.md` に追記し、必要なら `tech.md` steering に型保存方針を昇格する。

## Risks & Mitigations
- Tailwind CSS が未導入 — 実装タスクで package と config を追加し、既存 CSS を置き換える。
- Vue Router が未導入 — 実装タスクで `vue-router` を追加し、`createWebHistory` と explicit route records で初期 routing を構成する。
- Pinia の先行導入による過剰設計 — Plant Registration では導入せず、共有状態の境界が明確になった段階で再評価する。
- Alembic 設定ファイルが未作成 — migration task で `alembic.ini`, `env.py`, initial revision をまとめて作成する。
- SQLite と Turso/libSQL の接続差分 — `sqlalchemy-libsql` を導入し、local SQLite と Turso/libSQL の両方で migration + CRUD smoke test を実施する。
- Alembic と Turso の相性 — initial migration は autogenerate だけに依存せず手動 review し、Turso remote database へ `upgrade head` を実行して確認する。
- UUID / datetime / boolean の保存差分 — Plant migration と併せて round trip 検証 script を作り、local SQLite と Turso の結果を比較する。
- 画像 URL の外部読み込み失敗 — UI component 側で placeholder fallback を持つ。

## References
- [FastAPI documentation via Context7 `/fastapi/fastapi`](https://fastapi.tiangolo.com/) — response model、request validation、HTTPException の設計確認
- [SQLModel documentation via Context7 `/websites/sqlmodel_tiangolo`](https://sqlmodel.tiangolo.com/) — table model、schema 分離、Session dependency、CRUD pattern の確認
- [Vue documentation via Context7 `/vuejs/vue`](https://vuejs.org/) — Composition API、`<script setup>`、typed component contract の確認
- [Vue Router documentation via Context7 `/websites/router_vuejs`](https://router.vuejs.org/) — `createRouter`, `createWebHistory`, `router-view`, route params の確認
- [Turso SQLAlchemy docs](https://docs.turso.tech/sdk/python/orm/sqlalchemy) — `sqlalchemy-libsql`, `sqlite+libsql`, Turso credential, engine configuration の確認
- [Turso libSQL docs](https://docs.turso.tech/libsql) — SQLite compatibility と libSQL/Turso Database の位置付け確認
- [sqlalchemy-libsql PyPI](https://pypi.org/project/sqlalchemy-libsql/) — package status, version, platform, license の確認
- [Alembic autogenerate docs](https://alembic.sqlalchemy.org/en/latest/autogenerate.html) — metadata comparison と autogenerate limitation の確認
- `docs/mvp.md` — product scope、UX language、Plant Registration field
- `docs/architecture.md` — monorepo structure、backend layer structure、REST policy
