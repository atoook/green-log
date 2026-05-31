# Research & Design Decisions: plant-watering-care

## Summary

- **Feature**: `plant-watering-care`
- **Discovery Scope**: Extension
- **Key Findings**:
  - 既存 `/care/today` は今日のみの flat list contract であり、明日・明後日の予定表示には response shape が不足している。
  - 既存 WateringService は Plant 一覧と `last_watered_at` summary から due state を作れるため、同じ計算を `days` 範囲へ一般化できる。
  - `/care/upcoming` を新設し、未指定 `days=1`、今回の UI では `days=3` とすることで、今日だけ取得と近い未来の取得を同じ contract に統合できる。

## Research Log

### 既存 `/care/today` contract

- **Context**: requirements が「今日のお世話」から「直近のお世話予定」へ拡張された。
- **Sources Consulted**: `backend/app/routers/care.py`, `backend/app/services/watering_service.py`, `backend/app/schemas/watering.py`, `frontend/src/api/watering.ts`, `frontend/src/composables/useTodayCare.ts`, `frontend/src/components/watering/TodayCareList.vue`
- **Findings**:
  - `GET /care/today` は `TodayCareRead { today, items }` を返す。
  - `WateringService.get_today_care` は `state.is_due_today` の plant だけを flat list にしている。
  - Frontend `TodayCareList` は 1 list 前提で、日付別 section を持たない。
- **Implications**:
  - 既存 endpoint を section 付きに変更するより、`/care/upcoming` へ置き換える方が意図が明確になる。
  - Frontend は `TodayCare` naming から `UpcomingCare` naming へ置換する。

### Upcoming range calculation

- **Context**: 今日、明日、明後日を同じ日付基準で扱う必要がある。
- **Sources Consulted**: `WateringService._build_state`, `APP_TIMEZONE`, existing service tests
- **Findings**:
  - 既存 service は `today_provider` を注入でき、Asia/Tokyo date を基準にできる。
  - 未記録 plant は `next_watering_date` がないため、未来 section ではなく今日 section の初回記録対象にする必要がある。
  - 期限超過 plant は `next_watering_date` が過去であっても今日の確認対象である。
- **Implications**:
  - `get_upcoming_care` は今日 section にだけ特別ルールを適用する。
  - 明日以降は `next_watering_date == section.date` の plant だけを含める。
  - `days` は過大範囲を避けるため 1..14 に制限する。

### Frontend integration

- **Context**: route とユーザー導線は既存 `/care/today` を使っている。
- **Sources Consulted**: `frontend/src/router/index.ts`, `frontend/src/pages/TodayCarePage.vue`, `frontend/src/components/watering/TodayCareList.vue`
- **Findings**:
  - URL route `/care/today` は既存 navigation として残せる。
  - data source は `/care/upcoming?days=3` へ置き換えられる。
  - section 表示は既存 item card と WateringActionButton を再利用できる。
- **Implications**:
  - API endpoint `/care/today` は削除するが、Frontend route path は互換のため維持してよい。
  - UI component と composable は upcoming naming へ rename する。

## Architecture Pattern Evaluation

| Option | Description | Strengths | Risks / Limitations | Notes |
|--------|-------------|-----------|---------------------|-------|
| New `/care/upcoming` endpoint | `days` で今日を含む日数を指定し、section response を返す | 今日のみと3日表示を同じ contract にできる | Frontend/backend の rename が必要 | 採用 |
| Extend `/care/today` | 既存 endpoint を section response に変更する | URL 変更が少ない | today という名前と複数日 response が矛盾する | 不採用 |
| Frontend-side future calculation | Plant list/detail API を組み合わせて UI が予定を計算する | Backend 変更が少ない | N+1 または情報不足、owner-scoped due logic の重複 | 不採用 |

## Design Decisions

### Decision: `/care/upcoming` を今日だけ取得の置き換えにする

- **Context**: ユーザーは今日だけでなく明日・明後日の水やり予定を見たい。
- **Alternatives Considered**:
  1. `/care/today` を section response に拡張する。
  2. `/care/upcoming` を追加し `/care/today` を削除する。
- **Selected Approach**: `/care/upcoming` を追加し、query なしは今日のみ、`days=3` は今日・明日・明後日とする。`/care/today` は削除する。
- **Rationale**: endpoint 名と behavior が一致し、今後の近未来表示にも自然に拡張できる。
- **Trade-offs**: 既存 tests と frontend client の rename が必要。
- **Follow-up**: 外部公開 API になった場合は deprecation window を設計する。現時点では pre-release として breaking change を許容する。

### Decision: response は sections 形式にする

- **Context**: 日ごとの空状態と表示分けが requirement に含まれる。
- **Alternatives Considered**:
  1. flat list に `scheduledDate` を付ける。
  2. date section の配列を返す。
- **Selected Approach**: `sections: [{ date, kind, items }]` を返す。
- **Rationale**: Frontend が今日・明日・明後日を直接描画でき、空 section も自然に表現できる。
- **Trade-offs**: API schema はやや大きくなる。
- **Follow-up**: `days > 3` を UI で使う場合、`kind: future` の見出し表示を検証する。

### Decision: 未来 section は `next_watering_date` 一致だけを含める

- **Context**: 未記録や期限超過は今日確認すべき状態であり、未来予定ではない。
- **Alternatives Considered**:
  1. 未記録 plant を全 section に出す。
  2. 未記録と期限超過は今日 section に限定する。
- **Selected Approach**: 今日 section は未記録、期限超過、今日予定。明日以降は `next_watering_date` が一致する plant のみ。
- **Rationale**: 今日すべき確認と未来の予定を混同しない。
- **Trade-offs**: 未記録 plant の未来予定は初回記録が作られるまで未確定のまま。
- **Follow-up**: 初回水やり前の推定予定を導入する場合は Plant Registration または Watering requirements を再検討する。

## Risks & Mitigations

- `/care/today` 参照が残る — backend route contract test、frontend type/build、`rg "/care/today|getTodayCare|TodayCare"` で検出する。
- `days` 範囲が広すぎて owner plant scan が重くなる — 1..14 に制限する。
- 今日/明日/明後日の date boundary がぶれる — 既存 `today_provider` と Asia/Tokyo date conversion を再利用する。
- 明日以降に期限超過 plant が混ざる — section ごとの inclusion rule を service tests で固定する。
- route path `/care/today` と画面内容の naming がずれる — URL は互換維持、画面 copy は「直近のお世話予定」へ更新する。

## References

- `.kiro/specs/plant-watering-care/requirements.md` — 直近のお世話予定と取得範囲要件。
- `.kiro/steering/product.md` — お世話・記録を優先する UX 方針。
- `.kiro/steering/tech.md` — Backend layered architecture、Frontend typed API/composable/component 境界。
- `backend/app/services/watering_service.py` — 既存 due state と date provider。
- `frontend/src/components/watering/TodayCareList.vue` — 既存 list UI の拡張点。
