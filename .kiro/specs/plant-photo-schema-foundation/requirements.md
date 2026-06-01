# Requirements Document

## Project Description (Input)
観葉植物初心者が植物との暮らしを写真で振り返れるようにするには、1つの植物個体に複数枚の写真を紐づけられる永続化構造が必要である。

現在の植物記録は `plants.image_url` に単一の画像URLを直接持っており、一覧や詳細ヘッダーの代表画像には使えるが、将来の成長記録ギャラリー、日付付き写真、コメント付き写真には拡張しにくい。Backend の `Plant` model、`PlantCreate` / `PlantRead` schema、Service、Frontend の `Plant` / `PlantCreateInput` 型も `imageUrl` を植物本体の属性として扱っている。

この仕様では、`plants.image_url` に依存しない構造へ移行し、`plant_photos` に複数写真の参照情報とメタデータを保存できるようにする。代表画像は nullable な `plants.cover_photo_id` で管理し、既存の植物一覧・詳細取得APIは壊さず、当面 `imageUrl` を代表写真URLとして返す最小互換を維持する。

正式リリース前のため、既存 `plants.image_url` データの本番移行・保持互換は不要とする。画像アップロード、画像ファイル保存・削除、外部画像ストレージ連携、写真CRUD APIの本格実装、成長記録ギャラリーUIは今回の scope 外とする。

## Requirements
<!-- Will be generated in /kiro-spec-requirements phase -->

