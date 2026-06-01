# Research & Design Decisions

## Summary
- **Feature**: `plant-photo-schema-foundation`
- **Discovery Scope**: Extension
- **Key Findings**:
  - 既存 Backend は `Plant` と `WateringRecord` で、ユーザー所有 domain table に `owner_user_id` を持たせ、Repository で owner scoped lookup を行う pattern が確立している。
  - 既存 Frontend は `Plant.imageUrl` を一覧・詳細の表示補助に使っているため、レスポンス互換として `imageUrl` は代表写真URLとして残すのが最小変更になる。
  - `plants.cover_photo_id` と `plant_photos.plant_id` の双方向外部キーは SQLite/libSQL migration と downgrade を複雑にするため、DB FK は `plant_photos -> plants` に限定し、代表写真の同一 owner / plant 整合は repository/service と tests で検証する。

## Research Log

### 既存 Backend 境界
- **Context**: 写真記録を既存の植物・水やり domain にどう統合するか確認した。
- **Sources Consulted**: `backend/app/models/plant.py`, `backend/app/models/watering_record.py`, `backend/app/repositories/plant_repository.py`, `backend/app/repositories/watering_repository.py`, `backend/app/routers/plants.py`
- **Findings**:
  - `Plant` は `owner_user_id` を持ち、`PlantRepository.list/get_by_id` は owner id で絞り込む。
  - `WateringRecord` は `owner_user_id` と `plant_id` を持ち、Repository で植物所有確認を行う。
  - Service は domain validation、Router は HTTP error mapping を担当する。
- **Implications**:
  - `PlantPhoto` も `owner_user_id` と `plant_id` を持つ child table とし、Repository で owner/plant 整合を守る。
  - 新しい写真CRUD routerは作らず、植物一覧・詳細の read path だけを調整する。

### Migration と SQLite/libSQL 互換
- **Context**: `plants.cover_photo_id` と `plant_photos.plant_id` の参照関係が循環参照になりうる。
- **Sources Consulted**: `backend/alembic/versions/0002_create_users_and_plant_owners.py`, `backend/alembic/versions/0003_create_watering_records.py`, `backend/tests/test_watering_migration.py`
- **Findings**:
  - 既存 migration は SQLite 互換のため `batch_alter_table` を使用している。
  - Child table から `users` / `plants` への FK と owner-based composite indexes は既存 pattern と一致する。
  - `plants` 側に `plant_photos` への FK を追加すると、create/drop order と batch recreate の扱いが複雑になる。
- **Implications**:
  - `plant_photos.plant_id -> plants.id` と `plant_photos.owner_user_id -> users.id` は FK で保持する。
  - `plants.cover_photo_id` は nullable integer + index とし、同一 owner / plant の整合は query 条件と validation tests で固定する。

### Frontend/API 互換
- **Context**: 既存画面を壊さずに `plants.image_url` 依存を外す必要がある。
- **Sources Consulted**: `frontend/src/types/plant.ts`, `frontend/src/components/plants/PlantForm.vue`, `frontend/src/components/plants/PlantList.vue`, `frontend/src/components/plants/PlantDetail.vue`
- **Findings**:
  - `Plant.imageUrl` は一覧サムネイルと詳細ヘッダー画像に使われている。
  - 登録フォームは現在 `imageUrl` を入力・送信している。
  - 詳細画面には画像URLの値そのものを表示する項目がある。
- **Implications**:
  - Response の `imageUrl` は代表写真URLとして維持する。
  - Create input と登録フォームから `imageUrl` を外し、新規植物は代表写真未設定で作る。
  - 詳細画面の「画像 URL」行は今回の責務から外し、代表画像表示のみを維持する。

## Architecture Pattern Evaluation

| Option | Description | Strengths | Risks / Limitations | Notes |
|--------|-------------|-----------|---------------------|-------|
| Child table + response join | `plant_photos` を child table とし、植物 read path で代表写真URLを導出する | 既存 owner scoped repository pattern に合う。API互換を維持しやすい | list/detail query が join を持つ | 採用 |
| `plants.image_url` を残して後で移行 | 既存 column を維持し、将来写真機能で移行する | 変更量が少ない | 複数写真設計への依存廃止が進まない | 不採用 |
| 双方向DB FK | `plant_photos.plant_id` と `plants.cover_photo_id` の両方に FK を張る | DB上の参照整合が強い | SQLite/libSQL migration と downgrade が複雑。循環参照により実装リスクが上がる | 不採用 |

## Design Decisions

### Decision: 代表写真URLとして `imageUrl` レスポンスを維持する
- **Context**: 既存一覧・詳細は `imageUrl` を表示に使っている。
- **Alternatives Considered**:
  1. `imageUrl` を削除し `coverPhoto` object に置き換える
  2. `imageUrl` を代表写真URLとして再定義する
- **Selected Approach**: `PlantRead.image_url` は残し、`cover_photo_id` に紐づく写真の表示可能URLを返す。
- **Rationale**: 最小互換を維持しつつ、内部保存先を `plant_photos` に移せる。
- **Trade-offs**: 名前は旧来の単一画像項目を思わせるが、後続UI変更までの互換 field として扱える。
- **Follow-up**: 後続のギャラリー spec で `coverPhoto` / `photos` contract を検討する。

### Decision: `plants.cover_photo_id` にはDB FKを張らない
- **Context**: `plant_photos.plant_id` と `plants.cover_photo_id` は循環参照になりうる。
- **Alternatives Considered**:
  1. 双方向にDB FKを張る
  2. `cover_photo_id` は nullable integer とし、整合を owner scoped query と tests で守る
- **Selected Approach**: DB FK は `plant_photos -> plants/users` に限定し、`cover_photo_id` の妥当性は Repository/Service で検証する。
- **Rationale**: SQLite/libSQL 互換と migration/downgrade の単純さを優先する。
- **Trade-offs**: DB単独では orphan cover id を完全に防げないため、application validation と smoke/test coverage が重要になる。
- **Follow-up**: 後続の写真削除機能では、削除前に代表写真参照を解除する service rule を追加する。

### Decision: 写真CRUD APIは追加しない
- **Context**: 今回は画像アップロード・削除・外部ストレージが scope 外である。
- **Alternatives Considered**:
  1. 最小の写真作成APIを追加する
  2. 永続化 model/repository と植物 read path の互換調整に限定する
- **Selected Approach**: API surface は既存 `/plants` read/create の調整に留め、写真CRUD endpoint は追加しない。
- **Rationale**: アップロード処理なしで写真APIを公開すると、後続のストレージ責務と契約が先行して固まりすぎる。
- **Trade-offs**: 画面から写真追加はまだできないが、DB構造と read互換の検証は完了できる。
- **Follow-up**: 画像アップロード spec で写真作成・削除・代表写真更新 API を設計する。

## Risks & Mitigations
- `cover_photo_id` のDB FK未設定により不整合が入りうる — Repository/Service の owner/plant scoped join、migration smoke、unit tests で検出する。
- `imageUrl` の意味変更により実装者が植物本体画像として再利用する恐れがある — `PlantCreateInput` と登録フォームから `imageUrl` を外し、schema comment/designで代表写真URLと明記する。
- 既存 water/care summary が `Plant.image_url` を参照している — `WateringPlantSummaryRead.image_url` も代表写真URLとして扱うか、対象 query で導出する。

## References
- `.kiro/steering/product.md` — 写真を成長実感に使う product boundary
- `.kiro/steering/tech.md` — FastAPI/SQLModel/Alembic、SQLite/libSQL、owner scope 方針
- `.kiro/steering/auth.md` — internal owner id と protected API ルール
- `backend/alembic/versions/0003_create_watering_records.py` — owner scoped child table migration pattern
