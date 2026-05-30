# Brief: plant-watering-care

## Problem
観葉植物初心者は、植物ごとの水やり周期を登録できても、最後に水をあげた日や今日水やりが必要な植物をすぐ把握できない。結果として、水やり忘れや、逆に短い間隔で何度も水をあげてしまう不安が残る。

## Current State
`plant-registration` は植物個体の登録、一覧、詳細、水やり周期の保存を扱っている。一方で、水やり完了・スキップ・履歴、次回水やり予定日の計算、今日のお世話は明示的に範囲外である。

既存の Plant はユーザー所有データとして owner scope を持ち、`watering_cycle_days` を保持している。認証済みユーザーの private data として、後続の水やり記録も同じ owner 分離を守る必要がある。

## Desired Outcome
ユーザーは植物ごとに水やりしたことを記録できる。Green Mate は最新の水やり日時、次回水やり予定日、今日水やりが必要な植物を表示し、ユーザーが水やり忘れを防げる状態にする。

MVP の最小ユーザーフローは次の通り。
- ユーザーが「今日のお世話」を開くと、今日水やりが必要な植物が一覧表示される。
- ユーザーが対象植物に水やりしたら、一覧または植物詳細から「水やりした」を記録できる。
- 記録後、その植物の最新水やり日時と次回水やり予定日が更新され、今日のお世話からは必要に応じて外れる。
- 植物詳細では、最新水やり日時、次回水やり予定日、水やり記録の基本的な履歴を確認できる。

## Approach
採用方針は「Watering Record を source of truth とし、Plant に latest summary を持たせ、次回予定日は動的計算する」。

`WateringRecord` は「いつ、どの植物に、水やりしたか」という履歴イベントを保持する。`Plant.last_watered_at` は最新記録を素早く表示・判定するための集計キャッシュとして扱い、ユーザーが直接編集する値にはしない。水やり記録作成時は、record 作成と Plant の `last_watered_at` 更新を同一 service operation で行い、必要なら WateringRecord から再構築できるようにする。

`next_watering_date` は MVP では保存しない。Service 層の計算関数が `last_watered_at` と `watering_cycle_days` から date として算出し、API response や Today's Todo 判定に利用する。これにより、水やり周期が変更された場合も保存済み予定日の再同期を避けられる。

検討した代替案:
- 履歴なしで Plant に `last_watered_at` だけ持つ: 実装は小さいが、履歴表示、後日の修正、通知や分析の拡張が弱い。
- `next_watering_date` まで保存する: Todo や通知検索は速くなるが、水やり周期変更・履歴修正時の不整合対策が MVP にしては重い。
- `PlantCareState` を別 table に切り出す: 責務分離は明確だが、既存 Plant が水やり周期を持つ現状では MVP の実装面積が増える。必要になれば将来移行できる。

## Scope
- **In**: 水やり記録の作成、植物ごとの最新水やり日時の保持、次回水やり予定日の動的計算、今日水やりが必要な植物の一覧、植物詳細での水やり状態表示、owner-scoped API と基本テスト
- **Out**: 通知送信、通知設定、スキップ・延期、カレンダー表示、複数種類のお世話、植物種ごとの推奨周期、画像付き成長ログ、過去記録の編集・削除、共有ユーザーの共同お世話

## Boundary Candidates
- Plant は植物個体の基本情報と水やり周期設定を持つ。`last_watered_at` を持つ場合も、これは WateringRecord 由来の summary であり履歴そのものではない。
- WateringRecord は水やり実績の履歴イベントを持つ。Plant の名前、画像、周期などの基本情報は重複保持しない。
- WateringService は水やり記録作成、最新水やり日時の更新、次回予定日の計算、今日のお世話判定を担当する。
- WateringRepository は owner scope を含む記録保存・取得を担当し、HTTP 例外や表示文言を知らない。
- Frontend は `src/api/`、`src/composables/`、`src/components/`、`src/pages/` の既存分離を守り、presentation component に認証 token の扱いを持ち込まない。

## Out of Boundary
- Plant Registration の登録項目そのものの再設計は行わない。ただし水やり状態を返す read model や detail 表示の拡張は touchpoint として扱う。
- `next_watering_date` を DB に保存しない。通知や大規模検索が必要になった時点で、indexed schedule state として別途設計する。
- 通知 channel、通知時刻、タイムゾーン設定、通知済み判定はこの spec では所有しない。
- 水やり以外のお世話種別、スキップ、延期、繰り返しルールの詳細化は別 spec に分ける。

## Upstream / Downstream
- **Upstream**: `plant-registration` の Plant 個体、`watering_cycle_days`、植物一覧・詳細、認証・認可基盤の CurrentUser と owner scope
- **Downstream**: 通知機能、今日のお世話の拡張、水やり履歴の編集・削除、成長記録との関連表示、カレンダー表示、将来の複数お世話種別

## Existing Spec Touchpoints
- **Extends**: `plant-registration` の Plant detail/list response または関連 read model に、最新水やり日時・次回水やり予定日・今日必要かどうかを表示する導線を追加する可能性がある
- **Adjacent**: `auth-authorization-foundation` の owner scope、protected API、owner field 非公開ルールを継承する

## Constraints
Markdown と spec 成果物は `spec.json.language` に合わせて日本語で記述する。Backend は FastAPI / SQLModel / Alembic の layered architecture に従い、Service は FastAPI の HTTP 例外に依存しない。Frontend は Vue 3 / TypeScript の typed API client と composable 境界を守る。

日時は API 表現では UTC ISO 文字列を基本にする。水やり予定は日単位の体験なので、MVP では `last_watered_at` の date と `watering_cycle_days` から `next_watering_date` を算出する。将来の通知ではユーザーのタイムゾーン、通知時刻、重複通知防止、周期変更時の再計算を別途設計する。

Today's Todo は MVP ではユーザーごとの植物数が少ない前提で、owner scope の植物と `last_watered_at` summary を使って service 層で判定する。将来、全ユーザー向け通知 scan や大量データで性能要件が出た場合は、`next_watering_date` を保存する schedule state と `(owner_user_id, next_watering_date)` index を追加する。
