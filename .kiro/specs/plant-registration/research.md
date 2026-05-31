# Research & Design Decisions

## Summary
- **Feature**: `plant-registration`
- **Discovery Scope**: Extension
- **Key Findings**:
  - 既存実装は Plant API、owner scope、Frontend の Plant 型、一覧 component をすでに持つ。
  - `acquiredDate` は Backend schema と Frontend type に存在するため、「いっしょに暮らしてXX日目」は API 追加なしで一覧表示に追加できる。
  - 経過日表示は Plant 基本情報の presentation concern であり、水やり予定計算や `/care` 系 API とは分離する。

## Research Log

### 既存 Plant contract
- **Context**: requirements に「いっしょに暮らしてXX日目」が追加されたため、既存 API と型で実現できるか確認した。
- **Sources Consulted**: `backend/app/schemas/plant.py`, `backend/app/models/plant.py`, `frontend/src/types/plant.ts`, `frontend/src/api/plants.ts`
- **Findings**:
  - `PlantCreate` と `PlantRead` は `acquired_date: date | None` を持ち、camelCase では `acquiredDate` として扱われる。
  - Frontend `Plant` type は `acquiredDate: string | null` を持つ。
  - `PlantsApiClient.listPlants()` は `Plant[]` を返すため、一覧 component に `acquiredDate` が届く。
- **Implications**:
  - Backend schema、model、API endpoint の追加変更は不要。
  - 表示改善は `PlantList.vue` と UI テストに閉じられる。

### 既存一覧 UI
- **Context**: 経過日表示の追加場所と表示方針を確認した。
- **Sources Consulted**: `frontend/src/components/plants/PlantList.vue`, `frontend/tests/plant-ui-state.test.mjs`
- **Findings**:
  - `PlantList` は現在、植物名、水やり周期、画像または fallback tile を表示している。
  - 一覧は `plants`, `isLoading`, `error` を props として受け取り、`select` と `retry` を emits で返す presentation component である。
  - 画像読み込み失敗は component-local `brokenImageIds` で扱われている。
- **Implications**:
  - 経過日表示は `PlantList` の派生ラベルとして追加する。
  - `acquiredDate` 未設定時は「お迎え日は未記録」と表示し、既存の一覧 item selection と画像 fallback を維持する。
  - 日付計算は現在日に依存するため、テストでは today を注入できる純粋関数として切り出す。

### Owner scope と境界
- **Context**: 旧 design は認証・所有者分離を境界外としていたが、現在の steering と実装では認証基盤が導入済みである。
- **Sources Consulted**: `.kiro/steering/product.md`, `.kiro/steering/tech.md`, `backend/app/routers/plants.py`, `backend/app/services/plant_service.py`, `backend/app/repositories/plant_repository.py`
- **Findings**:
  - Plant API は `CurrentUser` dependency を使い、Service/Repository へ internal owner id を渡す。
  - Repository は `owner_user_id` を `list` と `get_by_id` の条件に含めている。
  - owner id は request body/query から受け取らず、response にも露出しない。
- **Implications**:
  - Plant Registration は auth 基盤そのものを所有しないが、Plant data は owner-scoped API に依存する設計として記述する。
  - 経過日表示は `acquiredDate` のみから派生し、owner 情報や internal timestamp を表示しない。

## Architecture Pattern Evaluation

| Option | Description | Strengths | Risks / Limitations | Notes |
|--------|-------------|-----------|---------------------|-------|
| Frontend derived label | `PlantList` が `acquiredDate` から経過日を表示する | API 追加なし、既存 contract を活用、表示改善に閉じる | 現在日依存のテスト設計が必要 | 採用 |
| Backend computed field | Plant API が `daysSinceAcquired` を返す | UI は単純になる | 日付基準と表示文言が Backend contract に入り、表示改善に対して重い | 不採用 |
| Created date fallback | `acquiredDate` 未設定時に `createdAt` で代替表示する | 常に日数を出せる | 「家に来た日」と「記録を始めた日」の意味が混ざる | 不採用 |

## Design Decisions

### Decision: 経過日表示は Frontend の派生表示にする
- **Context**: `acquiredDate` は既に Plant response に含まれている。
- **Alternatives Considered**:
  1. Backend に computed field を追加する。
  2. Frontend で `acquiredDate` から表示用 label を作る。
- **Selected Approach**: `PlantList` が date-only 文字列から「いっしょに暮らしてXX日目」を派生表示する。
- **Rationale**: 既存 API contract を壊さず、小さな表示改善として実装できる。
- **Trade-offs**: Frontend test で today を固定する必要がある。
- **Follow-up**: 日付基準をアプリ全体で統一する必要が出た場合、共有 date utility への昇格を検討する。

### Decision: 未設定時は fallback 日付を使わず未記録表示にする
- **Context**: 要件は「植物の登録日、または迎えた日として保持している日付」が基準だが、既存のユーザー入力項目は `acquiredDate` である。
- **Alternatives Considered**:
  1. `createdAt` を fallback として使う。
  2. `acquiredDate` が null の場合は未記録として表示する。
- **Selected Approach**: `acquiredDate` が null の場合、「お迎え日は未記録」と表示する。
- **Rationale**: 「家に来た日」と「記録作成日」を混同せず、ユーザーに意味のある状態を示せる。
- **Trade-offs**: 未設定の植物では日数が出ない。
- **Follow-up**: Plant 編集機能が追加された時点で、未記録状態から家に来た日を追記する導線を検討する。

## Risks & Mitigations
- 日付 parse が timezone の影響で 1 日ずれる — `YYYY-MM-DD` を分解して calendar day 差分を計算する。
- 今日の日付依存でテストが不安定になる — 計算関数に today を注入できるようにする。
- 一覧 item の情報量が増えて mobile で詰まる — 既存の grid 幅を維持し、短い補助テキストとして配置する。
- `createdAt` fallback による意味の混同 — fallback は使わず未記録表示にする。

## References
- `.kiro/steering/product.md` — 植物との生活記録、private data、UX 用語方針。
- `.kiro/steering/tech.md` — Frontend/Backend の layer 分離、owner scope、typed API 方針。
- `backend/app/schemas/plant.py` — `acquiredDate` contract。
- `frontend/src/components/plants/PlantList.vue` — 一覧表示の拡張点。
