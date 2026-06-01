# Brief: plant-photo-schema-foundation

## Problem
観葉植物初心者が植物との暮らしを写真で振り返れるようにするには、1つの植物個体に複数枚の写真を紐づけられる永続化構造が必要である。

現在の植物記録は `plants.image_url` に単一の画像URLを直接持っており、一覧や詳細ヘッダーの代表画像には使えるが、将来の成長記録ギャラリー、日付付き写真、コメント付き写真には拡張しにくい。

## Current State
`plants` テーブルは植物個体の基本情報として `image_url` を持つ。Backend の `Plant` model、`PlantCreate` / `PlantRead` schema、Service、Frontend の `Plant` / `PlantCreateInput` 型も `imageUrl` を植物本体の属性として扱っている。

既存 spec `plant-registration` は画像URL入力と表示を扱うが、複数写真の成長ログや画像アップロードは out of scope としている。今回の変更は画像アップロード前段のDB・型・API互換の土台であり、正式リリース前のため既存 `image_url` データ保持や本番データ移行は考慮不要とする。

## Desired Outcome
植物個体は `plants.image_url` に依存せず、`plant_photos` に複数写真の参照情報とメタデータを持てる。代表画像は `plants.cover_photo_id` で nullable に参照でき、写真がない植物も登録・一覧・詳細表示できる。

既存の植物一覧・詳細取得APIは壊さず、Frontend が代表画像URLを従来どおり扱える最小互換を維持する。今後の画像アップロード、削除、外部ストレージ連携、成長記録ギャラリーUIは別タスクで追加できる。

## Approach
`plant_photos` を新設し、`owner_user_id` と `plant_id` を必須で持たせる。`plants` には nullable の `cover_photo_id` を追加し、代表写真が未設定の植物を自然に扱えるようにする。

Turso/libSQL と SQLite の互換性を優先し、マイグレーションでは循環参照の扱いを慎重にする。`plant_photos.plant_id -> plants.id` は明確な所有関係として外部キーを張る一方、`plants.cover_photo_id -> plant_photos.id` は循環FKになりうるため、実装時に SQLite/Turso の制約追加順序、batch alter、削除時挙動、検証クエリのいずれかで安全に扱う設計を採用する。

API レスポンスでは、当面 `imageUrl` を「代表写真URL」として返す互換フィールドに再定義する。内部的には `cover_photo_id` で紐づく `plant_photos.image_url` または将来の `storage_key` から導出し、request body から植物本体の `imageUrl` を受け取る設計は廃止する方向にする。

## Scope
- **In**: `plant_photos` テーブル追加
- **In**: `plants.cover_photo_id` nullable 追加
- **In**: `plants.image_url` 廃止前提のモデル・型定義整理
- **In**: 代表写真を返すための最小限の一覧・詳細APIレスポンス方針
- **In**: `owner_user_id` / `plant_id` による所有者チェックしやすい構造
- **In**: Turso/libSQL と SQLite で安全に通せる migration 方針
- **Out**: 画像アップロード処理
- **Out**: 画像ファイル保存・削除処理
- **Out**: 外部画像ストレージ連携
- **Out**: 写真CRUD APIの本格実装
- **Out**: 成長記録ギャラリーUI
- **Out**: 既存 `plants.image_url` データの本番移行・保持互換

## Boundary Candidates
- 植物基本情報: 植物個体の名前、迎えた日、メモ、水やり周期などを管理する
- 写真メタデータ: 植物に紐づく写真参照、撮影日、コメント、作成・更新日時を管理する
- 代表写真参照: 一覧・詳細ヘッダーで表示する1枚だけを植物本体から参照する
- API互換層: 既存画面が壊れないよう、代表写真URLを既存の `imageUrl` 相当として返す

## Out of Boundary
- ユーザーが画像ファイルを選択してアップロードする操作
- アップロード済みファイルの外部ストレージ保存
- 画像削除時のストレージオブジェクト削除
- 写真の並び替え、アルバム、ギャラリー表示
- サムネイル生成、画像変換、CDN最適化
- 公開共有、複数ユーザー共有、権限ロール

## Upstream / Downstream
- **Upstream**: `plant-registration` spec の植物個体登録・一覧・詳細、`auth-authorization-foundation` spec の internal user owner model、既存 Alembic migration、FastAPI/SQLModel/Pydantic schema、Vue typed API client
- **Downstream**: 画像アップロード機能、成長記録ギャラリー、写真削除機能、代表写真選択UI、将来のストレージ連携

## Existing Spec Touchpoints
- **Extends**: `plant-registration` の画像URL入力・一覧表示・詳細表示の扱いを、単一 `plants.image_url` から代表写真URLへ置き換える
- **Adjacent**: `plant-watering-care` は植物IDを参照するが写真管理の責務は持たない
- **Adjacent**: `auth-authorization-foundation` の owner scope 方針に従い、写真データも request body ではなく認証コンテキスト由来の owner で扱う

## Constraints
既存の Vue 3 + FastAPI + SQLModel + Alembic + Turso/libSQL 構成に合わせる。ローカル開発・test・CI の SQLite でも同じ migration と CRUD path を通せるようにする。

すべての写真データは認証済みユーザーの所有データとして扱い、`plant_photos.owner_user_id` を必須にする。API 実装時は `owner_user_id` と `plant_id` の両方で所有者チェックし、他ユーザーの植物や写真の存在を漏らさない。

`cover_photo_id` は nullable にし、写真未設定の植物、写真削除後の代表未設定状態、将来のアップロード前状態を許容する。

正式リリース前で既存 `plants.image_url` データは保持不要のため、データ移行の複雑さより新設構造への単純な移行を優先する。ただし既存画面・テストが期待する API レスポンス形は、必要最低限の互換調整を行う。
