# Requirements Document

## Introduction
Plant Registration は、観葉植物初心者が自分の暮らしの中にある植物を「植物種」ではなく「所有している鉢・個体」として記録するための MVP 最初の機能である。ユーザーは植物を登録し、登録済みの植物を一覧で確認し、各植物の詳細を見られる。一覧では、植物が家に来てからの日数も確認でき、育てている時間の積み重なりを感じられる。ここで作成される植物記録は、後続の水やり記録、今日のお世話、成長写真ログの基礎情報として利用される。

## Boundary Context
- **In scope**: 植物の新規登録、登録項目の入力・保存・表示、植物一覧、家に来てからの日数表示、植物詳細、登録前後の基本的な空状態と入力エラー表示
- **Out of scope**: 水やり完了・スキップ・履歴、次回水やり予定日の計算、今日のお世話、カレンダー表示、複数写真の成長ログ、画像アップロード、ログイン、複数ユーザー共有、植物種マスタ、植物図鑑、育成ガイド
- **Adjacent expectations**: 後続のお世話・写真・カレンダー機能が参照できるよう、各植物記録は個体を識別できる状態で保持されるが、本 spec はそれらの後続機能の操作や計算を提供しない

## Requirements

### Requirement 1: 植物個体の登録
**Objective:** As a 観葉植物初心者, I want 所有している鉢・個体を植物として登録したい, so that 水やりや成長記録の基礎になる情報を残せる

#### Acceptance Criteria
1. When ユーザーが植物登録を開始する, the Green Mate shall 植物名、家に来た日、メモ、画像 URL、水やり周期を入力できる登録手段を表示する
2. When ユーザーが有効な登録内容を送信する, the Green Mate shall 新しい植物記録を作成し、その植物を登録済みとして扱う
3. When 植物記録が作成される, the Green Mate shall その植物を他の植物と区別できる一意の記録として保持する
4. The Green Mate shall 植物記録の単位を植物種ではなくユーザーが所有する鉢・個体として扱う

### Requirement 2: 登録項目と入力検証
**Objective:** As a 観葉植物初心者, I want 必要な登録項目を分かりやすく入力したい, so that 後から植物を見返したときに自分の植物として認識できる

#### Acceptance Criteria
1. When ユーザーが植物名を入力する, the Green Mate shall 入力された植物名を植物記録の主要な表示名として保存する
2. If ユーザーが植物名を空のまま登録しようとする, then the Green Mate shall 登録を完了せず、植物名が必要であることを表示する
3. When ユーザーが家に来た日を入力する, the Green Mate shall その日付を植物記録に保存する
4. When ユーザーがメモを入力する, the Green Mate shall そのメモを植物記録に保存する
5. When ユーザーが画像 URL を入力する, the Green Mate shall その URL を植物記録に保存する
6. When ユーザーが水やり周期を入力する, the Green Mate shall その周期を日数として植物記録に保存する
7. If ユーザーが 1 日未満の水やり周期を入力して登録しようとする, then the Green Mate shall 登録を完了せず、水やり周期が 1 日以上であることを表示する
8. If ユーザーが数値ではない水やり周期を入力して登録しようとする, then the Green Mate shall 登録を完了せず、水やり周期を日数で入力する必要があることを表示する

### Requirement 3: 植物一覧の表示
**Objective:** As a 観葉植物初心者, I want 登録済みの植物と一緒に家に来てからの日数を一覧で見たい, so that 自分が育てている植物と過ごした時間をすぐ把握できる

#### Acceptance Criteria
1. When ユーザーが植物一覧を開く, the Green Mate shall 登録済みの植物を一覧として表示する
2. While 登録済みの植物が 1 件以上ある, the Green Mate shall 各植物の植物名を一覧で確認できるように表示する
3. While 登録済みの植物に家に来た日がある, the Green Mate shall 今日と家に来た日の差分日数を「家に来てからXX日」として一覧に表示する
4. While 登録済みの植物に家に来た日がない, the Green Mate shall 家に来た日が未記録であることを一覧に表示する
5. While 登録済みの植物に画像 URL がある, the Green Mate shall その画像を一覧上で植物を識別する補助情報として表示する
6. While 登録済みの植物に画像 URL がない, the Green Mate shall 画像がない状態でも植物名で植物を識別できる一覧表示を維持する
7. When ユーザーが一覧内の植物を選択する, the Green Mate shall 選択された植物の詳細を表示する

### Requirement 4: 植物詳細の表示
**Objective:** As a 観葉植物初心者, I want 登録した植物の詳細を見たい, so that その植物の基本情報を確認できる

#### Acceptance Criteria
1. When ユーザーが登録済み植物の詳細を開く, the Green Mate shall その植物の植物名、家に来た日、メモ、画像 URL、水やり周期を表示する
2. While 植物に画像 URL がある, the Green Mate shall その画像を詳細上で表示する
3. While 植物に任意項目の未入力がある, the Green Mate shall 未入力項目があっても詳細表示を継続する
4. If ユーザーが存在しない植物の詳細を開こうとする, then the Green Mate shall 対象の植物が見つからないことを表示する

### Requirement 5: 空状態と失敗時の案内
**Objective:** As a 観葉植物初心者, I want 登録前や失敗時にも次の行動が分かる, so that 迷わず植物記録を始められる

#### Acceptance Criteria
1. While 登録済みの植物が 0 件である, the Green Mate shall 植物を登録できることが分かる空状態を表示する
2. When 植物一覧の取得に失敗する, the Green Mate shall 一覧を表示できないことと再試行できることを表示する
3. When 植物詳細の取得に失敗する, the Green Mate shall 詳細を表示できないことと一覧に戻れることを表示する
4. When 植物登録に失敗する, the Green Mate shall 登録が完了していないことを表示し、ユーザーが入力内容を見直せる状態を維持する

### Requirement 6: 後続機能との境界
**Objective:** As a プロダクト開発者, I want Plant Registration の責務を植物基本情報に限定したい, so that 後続のお世話記録や写真記録を独立して追加できる

#### Acceptance Criteria
1. The Green Mate shall 植物記録に後続機能が参照できる植物の識別情報を持たせる
2. The Green Mate shall 水やり周期を植物の基本設定として保持する
3. The Green Mate shall Plant Registration の範囲では水やり完了、スキップ、履歴を記録しない
4. The Green Mate shall Plant Registration の範囲では次回水やり予定日を計算しない
5. The Green Mate shall Plant Registration の範囲では画像 URL を保存対象とし、画像ファイルのアップロード操作を提供しない
6. The Green Mate shall Plant Registration の範囲では植物種マスタや育成ガイドを提供しない

### Requirement 7: MVP らしい体験と言葉づかい
**Objective:** As a 観葉植物初心者, I want 暮らしになじむ分かりやすい画面で植物を記録したい, so that 管理作業ではなく植物との生活記録として続けられる

#### Acceptance Criteria
1. The Green Mate shall 植物登録、一覧、詳細で業務ツール的な表現よりも暮らしの記録に合う表現を優先する
2. The Green Mate shall ユーザー向け文言で「タスク」より「お世話」を優先する
3. The Green Mate shall ユーザー向け文言で「管理」より「記録」を優先する
4. While ユーザーが小さな画面で利用している, the Green Mate shall 植物登録、一覧、詳細の主要操作と主要情報を読み取りやすく表示する
