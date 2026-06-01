# Requirements Document

## Introduction
Plant Profile Editing は、観葉植物初心者が登録後の植物基本情報を詳細画面から見直し、暮らしの変化や入力ミスに合わせて直せるようにする機能である。ユーザーは植物詳細を植物との生活記録の中心として使い、植物名、種類、家に来た日、メモ、水やり周期などをあとから調整できる。更新された情報は、その植物の詳細表示や水やり目安など、現在の植物情報を参照する表示へ自然に反映される。

## Boundary Context
- **In scope**: 植物詳細画面からの編集導線、植物基本情報の編集、保存中・成功・失敗・入力エラー状態、登録時に近い入力検証、認証済みユーザー本人の植物だけを更新できる保護、更新後の詳細表示と関連表示への反映
- **Out of scope**: 水やり記録の編集・削除、画像ファイルアップロード、複数写真の成長ログ編集、植物種マスタ、植物辞典、育成ガイド、共有ユーザーによる共同編集、通知設定、厳格な業務記録としての履歴整合制御
- **Adjacent expectations**: `plant-registration` が登録済み植物と基本表示を提供し、`plant-watering-care` は更新後の植物名と水やり周期を参照する。本 spec は植物基本情報の登録後更新を扱うが、水やり実績そのものの変更や植物種ごとの推奨値提供は扱わない。

## Requirements

### Requirement 1: 詳細画面からの編集開始
**Objective:** As a 観葉植物初心者, I want 植物詳細画面からその植物の情報を直したい, so that 登録後の入力ミスや変化にすぐ対応できる

#### Acceptance Criteria
1. When ユーザーが登録済み植物の詳細を開く, the Green Mate shall その植物の基本情報を編集できる導線を表示する
2. When ユーザーが編集導線を選択する, the Green Mate shall 対象植物の現在の基本情報を確認しながら編集できる状態を表示する
3. While 編集状態である, the Green Mate shall 編集対象の植物が分かるように現在の植物名または識別情報を表示する
4. When ユーザーが編集を取り消す, the Green Mate shall 未保存の変更を保存せず、詳細表示に戻る
5. While 植物詳細の取得に失敗している, the Green Mate shall 編集導線を完了可能な操作として表示しない

### Requirement 2: 編集対象の植物基本情報
**Objective:** As a 観葉植物初心者, I want 登録済み植物の基本情報をあとから調整したい, so that 自分の植物として分かりやすい記録を保てる

#### Acceptance Criteria
1. When ユーザーが植物情報を編集する, the Green Mate shall 植物名、種類、家に来た日または登録日として扱う日付、メモ、水やり周期を編集対象として扱う
2. Where 既存の登録フォームで保持している追加の植物基本情報がある, the Green Mate shall その項目を更新対象として扱う
3. When ユーザーが任意項目を空にして保存する, the Green Mate shall その項目を未入力として扱い、植物詳細の表示を継続する
4. The Green Mate shall 植物記録の単位を植物種ではなくユーザーが所有する鉢・個体として扱う
5. The Green Mate shall 種類の入力を植物種マスタや育成ガイドの選択に依存させない

### Requirement 3: 入力検証
**Objective:** As a 観葉植物初心者, I want 分かりやすい入力エラーで修正したい, so that 誤った内容を保存せずに植物情報を整えられる

#### Acceptance Criteria
1. If ユーザーが植物名を空のまま保存しようとする, then the Green Mate shall 更新を完了せず、植物名が必要であることを表示する
2. If ユーザーが 1 日未満の水やり周期を保存しようとする, then the Green Mate shall 更新を完了せず、水やり周期が 1 日以上であることを表示する
3. If ユーザーが数値ではない水やり周期を保存しようとする, then the Green Mate shall 更新を完了せず、水やり周期を日数で入力する必要があることを表示する
4. If ユーザーが不正な日付を保存しようとする, then the Green Mate shall 更新を完了せず、日付を見直す必要があることを表示する
5. When 入力エラーが表示される, the Green Mate shall ユーザーが入力内容を見直せる状態を維持する
6. The Green Mate shall 植物登録時と同じ意味の入力項目では登録時と整合する検証結果を返す

### Requirement 4: 保存状態と失敗時の案内
**Objective:** As a 観葉植物初心者, I want 保存中や失敗時の状態を理解したい, so that 同じ操作を重複せず落ち着いてやり直せる

#### Acceptance Criteria
1. When ユーザーが有効な編集内容を保存する, the Green Mate shall 対象植物の基本情報を更新する
2. While 保存処理が進行中である, the Green Mate shall 保存中であることを表示し、同じ保存操作の重複実行を防ぐ
3. When 植物情報の保存が成功する, the Green Mate shall 保存が完了したことをユーザーに表示する
4. If 植物情報の保存に失敗する, then the Green Mate shall 更新が完了していないことを表示し、ユーザーが再試行または入力見直しをできる状態を維持する
5. If 保存中に認証状態が利用できなくなった, then the Green Mate shall 保護された植物情報を保存済みとして扱わず、ログインまたは再認証へつながる状態を表示する

### Requirement 5: 更新後の詳細表示への反映
**Objective:** As a 観葉植物初心者, I want 保存後すぐに更新後の情報を確認したい, so that 修正できたことを迷わず確かめられる

#### Acceptance Criteria
1. When 植物情報の保存が成功する, the Green Mate shall 更新後の植物詳細を表示する
2. When 植物名が更新される, the Green Mate shall 詳細画面上の植物名を更新後の名前として表示する
3. When 家に来た日または登録日として扱う日付が更新される, the Green Mate shall その日付に基づく表示を更新後の内容として表示する
4. When メモが更新される, the Green Mate shall 詳細画面上のメモを更新後の内容として表示する
5. When 水やり周期が更新される, the Green Mate shall 水やり周期を参照する表示を更新後の周期に基づいて表示する
6. While 任意項目が未入力である, the Green Mate shall 未入力項目があっても更新後の詳細表示を継続する

### Requirement 6: ユーザー所有データの保護
**Objective:** As a Green Mate ユーザー, I want 自分の植物だけを編集できるようにしたい, so that 私的な生活記録を安心して使える

#### Acceptance Criteria
1. When 認証済みユーザーが植物情報を更新する, the Green Mate shall そのユーザーが所有する植物だけを更新対象として扱う
2. If 未ログインまたは認証状態を確認できないユーザーが植物情報を編集しようとする, then the Green Mate shall 保護された植物情報を表示または更新せず、ログインまたは再認証へつながる状態を表示する
3. If ユーザーが自分の所有ではない植物を編集しようとする, then the Green Mate shall 対象の存在を明かさず、利用できないことを表示する
4. The Green Mate shall 植物情報の編集画面または保存結果で内部ユーザー識別子、認証情報、所有者情報をユーザー向けに表示しない
5. The Green Mate shall ユーザーから送られた所有者情報を植物の所有者判定として扱わない

### Requirement 7: 水やり記録との関係
**Objective:** As a 観葉植物初心者, I want 植物情報を柔軟に直したい, so that 水やり実績を壊さずに基本情報だけ調整できる

#### Acceptance Criteria
1. When ユーザーが水やり周期を更新する, the Green Mate shall 既存の水やり記録を変更せず、以後の水やり目安に更新後の周期を反映する
2. When ユーザーが植物名を更新する, the Green Mate shall 水やり履歴や実績表示で参照される植物名を現在の登録名として表示できるようにする
3. When ユーザーが家に来た日または登録日として扱う日付を更新する, the Green Mate shall 既存の水やり記録の日付を変更しない
4. If 更新後の日付が既存の水やり記録日と時系列上ずれる, then the Green Mate shall その理由だけで保存を必ず拒否することはしない
5. Where 日付の整合性に関する案内を表示する場合, the Green Mate shall 保存を妨げる制約ではなくユーザーが判断できる補助情報として表示する

### Requirement 8: MVP らしい体験と言葉づかい
**Objective:** As a 観葉植物初心者, I want 暮らしになじむ分かりやすい編集体験を使いたい, so that 管理作業ではなく植物との生活記録として続けられる

#### Acceptance Criteria
1. The Green Mate shall 植物情報の編集で業務ツール的な表現よりも暮らしの記録に合う表現を優先する
2. The Green Mate shall ユーザー向け文言で「タスク」より「お世話」を優先する
3. The Green Mate shall ユーザー向け文言で「管理」より「記録」を優先する
4. While ユーザーが小さな画面で利用している, the Green Mate shall 植物情報の編集、保存、取り消し、エラー確認の主要操作を読み取りやすく表示する
5. The Green Mate shall 植物詳細画面を植物の基本情報とお世話状態を見直す中心画面として扱う
