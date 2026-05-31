# Research & Design Decisions: plant-watering-care

## Summary

- **Feature**: `plant-watering-care`
- **Discovery Scope**: Extension
- **Key Findings**:
  - 既存の Watering domain slice は `WateringRecord`、`Plant.last_watered_at` summary、今日のお世話、植物詳細履歴まで実装済みであり、ヒートマップは同じ slice の read model として追加できる。
  - ホーム相当の root は `/plants` に redirect しているため、MVP の水やりヒートマップは `PlantsPage.vue` に追加するのが最小変更である。
  - 新しい chart library は不要。直近 3 か月程度の小さな日次グリッドは Vue component と Tailwind CSS で実装できる。

## Research Log

### 既存 Watering domain の拡張点

- **Context**: 要件 6 としてホーム画面の水やりヒートマップが追加された。
- **Sources Consulted**:
  - `.kiro/specs/plant-watering-care/requirements.md`
  - `backend/app/services/watering_service.py`
  - `backend/app/repositories/watering_repository.py`
  - `backend/app/schemas/watering.py`
  - `frontend/src/api/watering.ts`
  - `frontend/src/types/watering.ts`
  - `frontend/src/pages/PlantsPage.vue`
- **Findings**:
  - 既存 WateringService は `today_provider` と `now_provider` を注入でき、日付境界を test しやすい。
  - `watering_records.owner_user_id_watered_at` index があり、owner scoped の期間 query に利用できる。
  - `frontend/src/api/watering.ts` は Watering API の typed client として拡張しやすい。
  - `PlantsPage.vue` は root redirect 先であり、植物登録・一覧と同じホーム画面文脈にヒートマップを置ける。
- **Implications**:
  - 新規 backend router は不要で、`CareRouter` に `GET /care/watering-heatmap` を追加する。
  - Frontend は `useWateringHeatmap.ts` と `WateringHeatmap.vue` を追加し、`PlantsPage.vue` で compose する。

### ヒートマップ集計単位

- **Context**: 同じ植物を 1 日に複数回水やりする通常ケースは想定しない。詳細表示は回数より植物名が望ましい。
- **Sources Consulted**:
  - ユーザー確認: 同日同一植物の複数水やりは通常ない前提
  - `WateringRecord` model
  - `Plant` model
- **Findings**:
  - WateringRecord は record event を保持し、同じ plant の同日複数 record を DB 制約で禁止していない。
  - ヒートマップの価値は「何回押したか」より「どの植物をお世話したか」にある。
  - 現在の Plant 名を join して返せば、記録時点名を保存する追加 migration は不要である。
- **Implications**:
  - ヒートマップでは同一 UTC 日・同一 plant の複数 record を 1 植物として集計する。
  - 詳細表示は `date` と現在の `plant.name` list を返す。
  - 記録時点名の保持は将来要件が出るまで追加しない。

### UI 実装方式

- **Context**: GitHub Contribution Graph に似た日次ヒートマップを Vue で実装する。
- **Sources Consulted**:
  - `frontend/package.json`
  - `frontend/src/style.css`
  - 既存 Vue component / Tailwind CSS usage
- **Findings**:
  - 直近 3 か月程度のセル数は小さく、DOM grid で十分に扱える。
  - 新しい visualization library は、bundle size と styling 統合の観点で MVP には不要。
  - 小画面では横スクロールまたは compact grid によって日別セルの判別を維持できる。
- **Implications**:
  - `WateringHeatmap.vue` は外部 chart library なしで実装する。
  - `level` は backend で計算して API contract に含め、frontend は表示変換に集中する。
  - tap/hover の詳細表示は component-local state として持つ。

## Architecture Pattern Evaluation

| Option | Description | Strengths | Risks / Limitations | Notes |
|--------|-------------|-----------|---------------------|-------|
| Existing Watering Service extension | `WateringService` / `CareRouter` に heatmap read model を追加する | 既存 owner scope、date provider、typed client を再利用できる | Service が大きくなる | MVP では最小で境界が明確 |
| New Heatmap domain slice | Heatmap 専用 service/router/component を追加する | 責務名は明確 | WateringRecord の派生 read model だけにしては過剰 | 将来 streak/analytics が増えたら再検討 |
| Client-side aggregation | 履歴を frontend に渡して集計する | backend 変更が少ない | owner scoped 集計量が増え、detail と count の一貫性を UI が背負う | 不採用 |
| Stored daily aggregate | 日次集計 table を保存する | 長期間・大量データに強い | MVP には migration と整合性コストが過剰 | 不採用 |

## Design Decisions

### Decision: ヒートマップは Watering domain の read model とする

- **Context**: ヒートマップは WateringRecord の派生表示であり、水やり以外のお世話種別や習慣化 analytics は scope 外である。
- **Alternatives Considered**:
  1. WateringService に read model を追加する
  2. HeatmapService を新設する
  3. Frontend で履歴から集計する
- **Selected Approach**: `WateringService.get_watering_heatmap` と `GET /care/watering-heatmap` を追加する。
- **Rationale**: 既存 owner scope と date provider を再利用でき、今日のお世話と同じ protected care API 境界に収まる。
- **Trade-offs**: WateringService の責務は増えるが、派生 read model の範囲に留まるため許容する。
- **Follow-up**: streak、週次/月次 summary、植物別フィルタが入る場合は analytics 専用 slice へ分離を再検討する。

### Decision: API は `from` / `to` の範囲指定を受け付ける

- **Context**: MVP の表示値は直近 3 か月でよいが、日付範囲の調整が入る可能性は高い。
- **Alternatives Considered**:
  1. 固定 3 か月 window
  2. `days` query parameter
  3. `from` / `to` query parameter
- **Selected Approach**: `GET /care/watering-heatmap?from=YYYY-MM-DD&to=YYYY-MM-DD` を受け付ける。Frontend の MVP 初期値は直近 3 か月相当とする。
- **Rationale**: 日付範囲が明示的で、月境界や任意期間の調整に対応しやすい。API contract を先に安定させ、UI は MVP では固定の初期期間だけ使える。
- **Trade-offs**: Router/Service に date validation が必要になる。過大な期間指定を避けるため、MVP では 366 日を上限にする。
- **Follow-up**: UI 側で期間切り替えを提供する場合は、同じ API contract を利用する。

### Decision: 日次強度は水やりした distinct plant 数で決める

- **Context**: 同じ植物に同日複数回水やりすることは通常想定しない。詳細表示では回数より植物名が有用である。
- **Alternatives Considered**:
  1. WateringRecord 件数
  2. distinct plant 数
  3. 水やり済みかどうかの binary
- **Selected Approach**: distinct plant 数を `plantCount` とし、`0, 1, 2, 3, 4+` を `level 0-4` に変換する。
- **Rationale**: 1 日に何鉢お世話したかが視覚的に分かり、誤操作や同日重複 record の影響を抑えられる。
- **Trade-offs**: 同じ植物に複数回水やりした事実はヒートマップでは表現しない。
- **Follow-up**: 同日複数水やりを正式に扱う場合は、詳細表示に record count を追加する。

### Decision: ヒートマップの植物名は現在の登録名を表示する

- **Context**: 要件は現在名表示を採用した。記録時点名を保存する要件はない。
- **Alternatives Considered**:
  1. 現在の Plant 名を join して表示する
  2. WateringRecord に記録時点の plant name snapshot を保存する
- **Selected Approach**: 現在の Plant 登録名を表示する。
- **Rationale**: 既存 Plant data を再利用でき、追加 migration や過去名管理を避けられる。
- **Trade-offs**: 名前変更後は過去日の表示名も現在名になる。
- **Follow-up**: 記録時点名の厳密性が必要になった場合は WateringRecord snapshot の追加を別 spec で検討する。

## Risks & Mitigations

- 同日同一植物の重複 record がヒートマップを過大評価する — Service で date + plant_id の distinct 集計を行う。
- ヒートマップで多数の植物名が並ぶ — UI は判別可能な形を維持し、詳細な省略ルールは component 実装で固定する。
- UTC 日付とユーザーの生活日付がずれる — MVP は既存設計通り UTC date を使い、timezone profile 追加時に revalidation する。
- ヒートマップ取得失敗でホーム全体が壊れる — `WateringHeatmap` 部分に局所 error と retry を表示する。
- 将来 analytics が増えて WateringService が肥大化する — streak/週次/月次/植物別切り替えが入る時点で analytics boundary を再検討する。

## References

- `.kiro/steering/product.md` — 「植物との生活記録」、お世話・記録を優先する UX 方針。
- `.kiro/steering/tech.md` — Backend layered architecture、Frontend typed API/composable/component 境界。
- `.kiro/steering/auth.md` — owner scope、protected API、owner field 非公開。
- `.kiro/specs/plant-watering-care/requirements.md` — ヒートマップを含む最終要求。
