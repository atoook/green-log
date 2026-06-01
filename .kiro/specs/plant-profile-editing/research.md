# Research & Design Decisions

## Summary
- **Feature**: `plant-profile-editing`
- **Discovery Scope**: Extension
- **Key Findings**:
  - 既存の植物基本情報は `Plant` model、`PlantCreate` / `PlantRead` schema、`GET/POST /plants`、詳細画面の `usePlantDetail` と `PlantDetail` に集約されている。
  - 更新 API はまだ存在せず、owner-scoped lookup は `PlantRepository.get_by_id(owner_user_id, plant_id)` と auth steering のルールに沿って追加できる。
  - 今回は DB への項目追加を行わないため、編集対象は既存テーブルにある `name`, `acquired_date`, `memo`, `watering_cycle_days` に限定する。

## Research Log

### 既存植物 CRUD と詳細画面
- **Context**: 詳細画面から植物情報を編集するため、既存の表示・取得・登録パターンを確認した。
- **Sources Consulted**: `backend/app/models/plant.py`, `backend/app/schemas/plant.py`, `backend/app/repositories/plant_repository.py`, `backend/app/services/plant_service.py`, `backend/app/routers/plants.py`, `frontend/src/api/plants.ts`, `frontend/src/composables/usePlantDetail.ts`, `frontend/src/components/plants/PlantDetail.vue`, `frontend/src/pages/PlantDetailPage.vue`
- **Findings**:
  - Plant の永続属性は `name`, `acquired_date`, `memo`, `watering_cycle_days`, `last_watered_at`, `cover_photo_id`, timestamps が中心である。
  - `imageUrl` は `plant_photos` の cover photo から read response に合成され、create input の legacy `imageUrl` は保存されない。
  - 詳細画面は `PlantDetailPage` が composition を担当し、`PlantDetail` は表示と戻るイベントを担当する。
  - `usePlantDetail` は get の読み込み状態のみを持ち、更新状態はまだない。
- **Implications**:
  - 画像 URL 更新はこの spec では扱わず、cover photo 表示は既存 join を維持する。
  - 更新成功後は `usePlantDetail` の `plant` ref を更新 response で置き換えると、詳細と水やり見出しへ即時反映できる。

### 認証と owner scope
- **Context**: 本人の植物だけ更新できるようにするため、認証・認可の既存ルールとテストを確認した。
- **Sources Consulted**: `.kiro/steering/auth.md`, `.kiro/steering/tech.md`, `backend/tests/test_plants_api.py`, `backend/tests/test_e2e_owner_model_regression.py`
- **Findings**:
  - protected API は `CurrentUser` を必須にし、domain service には internal owner id を渡す。
  - detail / update / delete は resource id と owner id の両方で lookup し、他 owner は 404 とするルールである。
  - 既存 regression test は `PATCH /plants/{id}` が未存在で 405 であることを現在の前提としている。
- **Implications**:
  - 本 spec 実装時は regression test を「他 owner の PATCH は 404、対象 row は変更されない」に更新する。
  - request body に owner 系 field が含まれても schema で採用せず、response にも owner field を出さない。

### 水やり機能との接点
- **Context**: 水やり周期や植物名の更新が水やり表示にどう影響するか確認した。
- **Sources Consulted**: `backend/app/services/watering_service.py`, `backend/app/repositories/watering_repository.py`, `frontend/src/pages/PlantDetailPage.vue`, `frontend/src/components/watering/WateringStatusPanel.vue`, `backend/app/scripts/verify_turso_crud.py`
- **Findings**:
  - 水やり予定は Plant の `watering_cycle_days` と `last_watered_at` から計算される。
  - ヒートマップ上の植物名は現在の Plant name を参照する既存 smoke verification がある。
  - 水やり記録の日時は watering record 側に保持され、植物の `acquired_date` 更新とは独立している。
- **Implications**:
  - 植物基本情報更新は watering record を変更しない。
  - 更新後の詳細画面では `wateringCycleDays` prop が変わるため、必要に応じて水やり状態を再読込して次回目安を最新化する。

### データモデル差分
- **Context**: 今回の編集対象が既存テーブルだけで完結するか確認した。
- **Sources Consulted**: `backend/app/models/plant.py`, `backend/alembic/versions/*.py`, `frontend/src/types/plant.ts`
- **Findings**:
  - 既存 Plant model には `name`, `acquired_date`, `memo`, `watering_cycle_days` があり、今回の編集対象はこれらで完結する。
  - 現行 model に存在しない新規属性は今回の更新対象ではない。
- **Implications**:
  - 新規 migration は不要である。
  - 既存テーブルにない項目は requirements/design/tasks の対象から外し、別 spec の候補に留める。

## Architecture Pattern Evaluation

| Option | Description | Strengths | Risks / Limitations | Notes |
|--------|-------------|-----------|---------------------|-------|
| インライン編集 | 詳細画面内で表示と編集フォームを切り替える | 詳細画面を中心にでき、保存後の即時反映が単純 | 詳細画面が混みやすい | 採用。MVP の項目数では適切 |
| 編集専用 route | `/plants/:id/edit` のような別画面へ遷移する | 入力項目が増えても整理しやすい | route、遷移、戻り状態が増える | 今回は不採用。将来の複雑化で再検討 |
| 登録フォーム共通化 | `PlantForm` を create/edit 両対応にする | 検証と UI を共有しやすい | 登録画面の scope まで広がりやすい | 検証 utility は共有し、編集 UI は専用 component とする |

## Design Decisions

### Decision: 詳細画面内編集を採用する
- **Context**: 要件は詳細画面を植物管理の中心にすること、保存後に詳細へ戻ることを求めている。
- **Alternatives Considered**:
  1. インライン編集
  2. 編集専用 route
- **Selected Approach**: `PlantDetailPage` に編集状態を持たせ、`PlantDetail` の編集イベントで `PlantEditForm` を表示する。
- **Rationale**: 既存 route を増やさず、更新 response で `plant` state を置き換えれば詳細と水やり見出しへ即時反映できる。
- **Trade-offs**: 画面内の責務が増えるため、form と validation を presentation / utility に分けて page の肥大化を抑える。
- **Follow-up**: 項目追加や写真編集が増えた場合は編集専用 route を再評価する。

### Decision: 既存テーブルにない項目は対象外にする
- **Context**: ユーザー確認により、今回は DB への項目追加を行わないことが明確になった。
- **Alternatives Considered**:
  1. 新規植物属性を追加する
  2. 既存 Plant table の項目だけを編集対象にする
- **Selected Approach**: `name`, `acquired_date`, `memo`, `watering_cycle_days` の更新に限定する。
- **Rationale**: 今回の目的である登録後の修正と水やり周期・メモ調整を満たし、DB migration と contract 拡張のリスクを避けられる。
- **Trade-offs**: 既存項目以外の編集は提供しない。必要になった時点で別 spec として扱う。
- **Follow-up**: 追加属性が必要になったら、DB 項目追加を含む新規 spec で再検討する。

### Decision: 更新は full replacement に近い `PATCH` として扱う
- **Context**: UI は編集フォーム全体を保存し、要件は既存基本情報の更新を求めている。
- **Alternatives Considered**:
  1. `PUT` で全項目置換
  2. `PATCH` で送信項目だけ更新
  3. `PATCH` だが編集フォームは全 editable field を送る
- **Selected Approach**: `PATCH /plants/{plant_id}` に `PlantUpdate` を送り、null は任意項目のクリアとして扱う。実装ではフォームから editable field をすべて送る。
- **Rationale**: 将来の部分更新にも拡張しやすく、現在の UI では保存内容が明確である。
- **Trade-offs**: 未送信と null の意味を schema で区別する必要がある。
- **Follow-up**: タスク化時に Pydantic unset handling と TypeScript request 型を明示する。

### Decision: 水やり実績との日付整合は保存拒否にしない
- **Context**: 要件 7 は柔軟性を優先し、既存水やり記録を壊さないことを求めている。
- **Alternatives Considered**:
  1. 実績日より後の acquired date を拒否する
  2. 警告のみ表示する
  3. 何も表示せず保存する
- **Selected Approach**: 初期実装では保存拒否しない。警告を出す場合も補助情報に留める。
- **Rationale**: 家に来た日を後から思い出して直す生活記録アプリでは、厳格な業務制約より柔軟性が重要である。
- **Trade-offs**: 時系列上不自然な表示が起こり得るが、実績データは保持される。
- **Follow-up**: ユーザー混乱が見えた場合に補助文言を追加する。

## Risks & Mitigations
- 更新後の水やり目安が古い state のまま残る — `PlantDetailPage` で更新成功後に plant state を差し替え、必要に応じて `loadWatering` を再実行する。
- owner scope の漏れで他ユーザー植物を更新できる — repository update は `owner_user_id` と `plant_id` の両方で lookup し、other owner regression test を追加する。
- 登録フォームと編集フォームの検証が乖離する — 検証 utility を共有し、create/edit の field 差分は props ではなく component 責務として明示する。
- 新規属性を誤って実装範囲に含める — file structure と data model に migration 不要、既存 Plant fields のみと明記する。

## References
- `.kiro/steering/product.md` — 植物は鉢・個体単位、暮らしの記録として扱う方針
- `.kiro/steering/tech.md` — Frontend / Backend layer、API、型、owner scope の実装方針
- `.kiro/steering/structure.md` — file placement と dependency direction
- `.kiro/steering/auth.md` — protected API と owner scope の恒久ルール
