# Requirements Document

## Introduction
Plant Watering Care は、観葉植物初心者が植物ごとの水やり忘れを防ぎ、お世話の継続状況を振り返るための MVP 機能である。ユーザーは植物に水やりしたことを記録し、最新の水やり日時、次回水やり予定日、今日から近い未来までの水やり予定、直近の水やり実績を確認できる。既存の Plant Registration が保持する植物個体と水やり周期を前提に、Green Mate は「直近のお世話」と「習慣の見える化」へつながる状態を表示する。

## Boundary Context
- **In scope**: 水やり記録の作成、植物ごとの最新水やり日時の表示、次回水やり予定日の表示、今日から近い未来までの水やり予定表示、植物詳細での水やり状態と基本履歴の表示、ホーム画面での水やりヒートマップ表示、認証済みユーザーごとの非公開データ分離、空状態と失敗時の案内
- **Out of scope**: 通知送信、通知設定、通知権限要求、スキップ・延期、カレンダー表示、水やり以外のお世話種別、植物種ごとの推奨周期、過去の水やり記録の編集・削除、画像付き成長ログ、共有ユーザーによる共同お世話、植物別ヒートマップ切り替え、連続記録日数やランキングなどの習慣化指標
- **Adjacent expectations**: `plant-registration` が登録済み植物と水やり周期を提供する。本 spec は植物登録項目そのものを再設計しないが、植物一覧・詳細・ホーム画面に水やり状態を表示する導線は扱う。認証・認可基盤は保護された植物記録を自分のアカウント内に閉じる前提として扱う。既存の今日だけのお世話取得は、直近のお世話予定取得に置き換える。

## Requirements

### Requirement 1: 直近のお世話予定の表示
**Objective:** As a 観葉植物初心者, I want 今日から近い未来までの水やり予定を一か所で確認したい, so that 水やり忘れに気づき、明日以降のお世話も見通せる

#### Acceptance Criteria
1. When ユーザーが直近のお世話予定を開く, the Green Mate shall 今日の水やり予定を表示する
2. When ユーザーが今日を含む 3 日分の水やり予定を開く, the Green Mate shall 今日、明日、明後日の水やり予定を日ごとに分けて表示する
3. While 任意の日付の水やり予定に植物が 1 件以上ある, the Green Mate shall 各植物の名前、識別しやすい補助情報、最新水やり状態、次回水やり予定日を一覧で確認できるように表示する
4. While 任意の日付の水やり予定に植物が 0 件である, the Green Mate shall その日に必要な水やりがないことを表示する
5. While 登録済み植物に水やり記録がない, the Green Mate shall その植物の水やり状態が未記録であることを表示し、今日の初回記録の確認対象として扱う
6. While 次回水やり予定日が今日より前である, the Green Mate shall その植物が今日までに水やり確認が必要であることを今日の予定として表示する
7. The Green Mate shall 今日、明日、明後日の水やり予定を同じ日付基準で扱う

### Requirement 2: 水やり記録の作成
**Objective:** As a 観葉植物初心者, I want 水やりしたことをすぐ記録したい, so that 最新のお世話状態を忘れず残せる

#### Acceptance Criteria
1. When ユーザーが登録済み植物に対して水やりしたことを記録する, the Green Mate shall その植物の水やり記録を作成する
2. When 水やり記録が作成される, the Green Mate shall 記録が完了したことをユーザーに表示する
3. When 水やり記録が作成される, the Green Mate shall その植物の最新水やり日時を新しい記録に合わせて表示する
4. When 水やり記録が作成される, the Green Mate shall その植物の次回水やり予定日を新しい記録に合わせて表示する
5. If 水やり記録の作成に失敗する, then the Green Mate shall 記録が完了していないことを表示し、ユーザーが再試行できる状態を維持する
6. If ユーザーが存在しない植物または利用できない植物に対して水やりを記録しようとする, then the Green Mate shall 対象の植物を利用できないことを表示し、水やり記録を作成しない
7. If 同じ植物に対して同じ日付基準で水やり記録がすでに存在する, then the Green Mate shall 追加の水やり記録を作成しない
8. While 同じ植物の水やりが当日すでに記録済みである, the Green Mate shall 水やり記録ボタンを非活性にし、当日記録済みであることが分かるラベルを表示する

### Requirement 3: 最新水やり日時の表示
**Objective:** As a 観葉植物初心者, I want 植物ごとに最後に水をあげた日時を確認したい, so that 次に水をあげるべきか判断できる

#### Acceptance Criteria
1. When ユーザーが登録済み植物の詳細を開く, the Green Mate shall その植物の最新水やり日時を表示する
2. While 植物に複数の水やり記録がある, the Green Mate shall 最も新しい水やり記録を最新水やり日時として表示する
3. While 植物に水やり記録がない, the Green Mate shall 最新水やり日時が未記録であることを表示する
4. When ユーザーが直近のお世話予定または植物詳細で水やりを記録する, the Green Mate shall 表示中の最新水やり日時を記録後の状態に更新する

### Requirement 4: 次回水やり予定日の表示
**Objective:** As a 観葉植物初心者, I want 植物ごとの次回水やり予定日を知りたい, so that 先の見通しを持ってお世話できる

#### Acceptance Criteria
1. When 植物に最新水やり日時と水やり周期がある, the Green Mate shall 最新水やり日時と水やり周期から次回水やり予定日を表示する
2. While 植物に水やり記録がない, the Green Mate shall 次回水やり予定日を未確定として表示し、水やり記録を始められる導線を表示する
3. When 水やり記録が作成される, the Green Mate shall 次回水やり予定日を記録後の最新状態に合わせて更新する
4. The Green Mate shall 次回水やり予定日をユーザーが別途入力しなくても確認できる値として扱う
5. The Green Mate shall 水やり予定を日単位で表示し、直近のお世話予定と同じ日付基準で扱う

### Requirement 5: 水やり履歴の確認
**Objective:** As a 観葉植物初心者, I want 植物ごとの水やり履歴を見返したい, so that お世話の継続状況を振り返れる

#### Acceptance Criteria
1. When ユーザーが登録済み植物の詳細を開く, the Green Mate shall その植物の水やり履歴を確認できるように表示する
2. While 植物に水やり記録が 1 件以上ある, the Green Mate shall 各水やり記録の日付または日時を履歴として表示する
3. While 植物に水やり記録がない, the Green Mate shall 水やり履歴がまだないことを表示する
4. When 新しい水やり記録が作成される, the Green Mate shall その記録を対象植物の水やり履歴に含める
5. The Green Mate shall MVP の範囲では過去の水やり記録を編集または削除する操作を提供しない

### Requirement 6: 水やりヒートマップの表示
**Objective:** As a 観葉植物初心者, I want ホーム画面で最近の水やり実績を視覚的に確認したい, so that お世話の習慣が続いているかひと目で分かる

#### Acceptance Criteria
1. When ユーザーがホーム画面を開く, the Green Mate shall 認証済みユーザーの水やり実績を日単位のヒートマップとして表示する
2. The Green Mate shall ヒートマップの 1 つのマスを 1 日の水やり実績として表示する
3. The Green Mate shall 少なくとも直近 3 か月分の水やり実績をヒートマップで表示する
4. The Green Mate shall 全登録植物の水やり記録を日ごとに集計し、水やりした植物数をヒートマップに反映する
5. While ある日に水やりした植物が 0 件である, the Green Mate shall その日を実績がない状態として表示する
6. While ある日に水やりした植物が 1 件以上である, the Green Mate shall 水やりした植物数に応じて実績の強さが分かる段階的な色でその日を表示する
7. When ユーザーがヒートマップ上の日をタップまたはホバーする, the Green Mate shall その日の日付と水やりした植物名を確認できるように表示する
8. While ある日に水やりした植物が複数ある, the Green Mate shall その日の植物名をユーザーが判別できる形で表示する
9. The Green Mate shall ヒートマップ上の植物名を現在の登録名として表示する
10. While ユーザーが小さな画面で利用している, the Green Mate shall ヒートマップの各日、期間、実績の強さを判別できる表示を維持する
11. While 水やり記録がまだない, the Green Mate shall ヒートマップを空の実績として表示し、水やり記録を始められる状態を示す

### Requirement 7: ユーザー所有データの保護
**Objective:** As a Green Mate ユーザー, I want 自分の植物と水やり記録だけを見られるようにしたい, so that 私的な生活記録を安心して使える

#### Acceptance Criteria
1. When 認証済みユーザーが直近のお世話予定を開く, the Green Mate shall そのユーザーが所有する植物の水やり状態だけを表示する
2. When 認証済みユーザーが植物詳細の水やり状態または履歴を開く, the Green Mate shall そのユーザーが所有する植物の水やり情報だけを表示する
3. When 認証済みユーザーがホーム画面の水やりヒートマップを開く, the Green Mate shall そのユーザーが所有する水やり記録だけを集計して表示する
4. If 未ログインまたは認証状態を確認できないユーザーが水やり情報を開こうとする, then the Green Mate shall 保護された植物記録を表示せず、ログインまたは再認証へつながる状態を表示する
5. If ユーザーが自分の所有ではない植物の水やり情報を開こうとする, then the Green Mate shall 対象の存在を明かさず、利用できないことを表示する
6. The Green Mate shall 水やり情報の表示で内部ユーザー識別子、認証情報、所有者情報をユーザー向けに表示しない

### Requirement 8: 空状態と失敗時の案内
**Objective:** As a 観葉植物初心者, I want 記録がない時や失敗した時にも次の行動が分かる, so that 迷わずお世話を続けられる

#### Acceptance Criteria
1. While 登録済み植物が 0 件である, the Green Mate shall 直近のお世話予定で植物登録から始められることを表示する
2. When 直近のお世話予定の取得に失敗する, the Green Mate shall 直近のお世話予定を表示できないことと再試行できることを表示する
3. When 植物の水やり状態の取得に失敗する, the Green Mate shall 水やり状態を表示できないことと再試行または一覧へ戻る行動を表示する
4. When 水やり履歴の取得に失敗する, the Green Mate shall 履歴を表示できないことを表示し、植物の基本情報を確認できる状態をできるだけ維持する
5. When 水やりヒートマップの取得に失敗する, the Green Mate shall ヒートマップを表示できないことと再試行できることを表示する
6. While 水やり情報を読み込み中である, the Green Mate shall 読み込み中であることを表示し、未確定の状態を完了済みとして表示しない

### Requirement 9: MVP らしい体験と言葉づかい
**Objective:** As a 観葉植物初心者, I want 暮らしになじむ分かりやすい水やり体験を使いたい, so that 管理作業ではなく植物との生活記録として続けられる

#### Acceptance Criteria
1. The Green Mate shall 水やり機能のユーザー向け文言で「タスク」よりも「お世話」を優先する
2. The Green Mate shall 水やり機能のユーザー向け文言で「管理」よりも「記録」を優先する
3. The Green Mate shall 水やりの記録操作を初心者が迷わず実行できる主要操作として表示する
4. While ユーザーが小さな画面で利用している, the Green Mate shall 直近のお世話予定、最新水やり日時、次回水やり予定日、水やり記録操作、水やりヒートマップを読み取りやすく表示する

### Requirement 10: 将来機能との境界
**Objective:** As a プロダクト開発者, I want 水やり MVP の責務を明確にしたい, so that 通知や複数お世話種別を後から独立して追加できる

#### Acceptance Criteria
1. The Green Mate shall MVP の範囲では水やり通知を送信しない
2. The Green Mate shall MVP の範囲では通知時刻、通知頻度、通知先を設定する操作を提供しない
3. The Green Mate shall MVP の範囲では通知権限をユーザーに要求しない
4. The Green Mate shall MVP の範囲では水やりのスキップ、延期、繰り返しルールの詳細設定を提供しない
5. The Green Mate shall MVP の範囲では水やり以外のお世話種別を記録する操作を提供しない
6. The Green Mate shall MVP の範囲では植物種ごとの推奨水やり周期や育成レコメンドを提供しない
7. The Green Mate shall MVP の範囲では植物別ヒートマップ切り替え、連続記録日数、ランキング、週次または月次の習慣化サマリーを提供しない

### Requirement 11: お世話予定取得範囲の一貫性
**Objective:** As a プロダクト開発者, I want お世話予定の取得範囲を一貫して扱いたい, so that 当日の確認と近い未来の確認を同じ考え方で拡張できる

#### Acceptance Criteria
1. When お世話予定の取得範囲が指定されない, the Green Mate shall 今日の水やり予定だけを対象として扱う
2. When お世話予定の取得範囲として今日を含む 3 日分が指定される, the Green Mate shall 今日、明日、明後日の水やり予定を対象として扱う
3. While お世話予定の取得範囲が複数日にまたがる, the Green Mate shall 水やり予定を日付ごとに区別できる状態で表示できるようにする
4. The Green Mate shall 直近のお世話予定の取得を、今日だけのお世話取得の置き換えとして扱う
