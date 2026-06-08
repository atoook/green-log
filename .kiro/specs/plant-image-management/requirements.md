# Requirements Document

## Introduction
Plant Image Management は、Green Mate の植物詳細体験に画像アップロードと成長記録ギャラリーを統合するための仕様である。観葉植物初心者が、現在表示している植物に対して写真を追加し、その植物の成長を時系列で振り返り、一覧で見分けやすい代表画像を設定し、必要に応じて画像ごとの記録情報を整えられる状態を目指す。

既存の `plant-photo-schema-foundation` は、植物個体に複数の写真記録を紐づけ、代表写真を未設定にもできる基盤を扱う。本仕様では、その基盤を利用するユーザー操作と表示体験を定義し、画像を独立した管理対象ではなく植物との生活記録の一部として扱う。

## Boundary Context
- **In scope**: 植物詳細画面からの画像追加、現在表示している植物への画像紐づけ、植物ごとの時系列ギャラリー、画像ごとの撮影日やコメントなどのメタ情報表示、画像メタ情報の編集、現在枚数と上限の表示、上限なしユーザーの表示調整、代表画像設定、植物一覧での代表画像表示、画像削除、削除確認、代表画像削除時の未設定化、ユーザー所有データとしての画像分離
- **Out of scope**: 他植物への画像紐づけ変更、画像管理専用画面、プラン定義や課金、画像ファイルの差し替え、トリミング、サムネイル生成、画像変換、公開共有、タイムラプス表示そのもの、植物種マスタとの連携
- **Adjacent expectations**: 写真記録と代表写真の基盤は `plant-photo-schema-foundation` の前提を利用する。植物登録は画像なしで継続でき、植物基本情報の編集は画像ギャラリー操作と混在しない。画像メタ情報の編集は植物基本情報の編集と同じく閲覧状態と編集状態を分ける体験に合わせるが、植物そのものの基本情報更新は本仕様では扱わない。将来のタイムラプス表示や成長記録強化は、本仕様の時系列ギャラリーと写真記録を利用できるが、本仕様では提供しない

## Requirements

### Requirement 1: 植物詳細からの画像追加
**Objective:** As a 観葉植物初心者, I want 表示中の植物に写真を追加したい, so that 成長の様子を植物ごとの記録として残せる

#### Acceptance Criteria
1. When 認証済みユーザーが植物詳細画面で画像追加を開始する, the Green Mate shall 追加対象を現在表示している植物として扱う
2. When 認証済みユーザーが有効な画像を追加する, the Green Mate shall その画像を現在表示している植物の画像として記録する
3. When 画像追加が完了する, the Green Mate shall 追加した画像を対象植物のギャラリーに表示する
4. If ユーザーが他植物への紐づけ変更をしようとする, then the Green Mate shall その操作を提供しない
5. If 画像追加に失敗する, then the Green Mate shall 対象植物の既存画像と代表画像を失わず、失敗したことをユーザーに示す

### Requirement 2: 植物ごとの時系列ギャラリー
**Objective:** As a 観葉植物初心者, I want 植物ごとに写真を時系列で見返したい, so that 成長の変化を振り返れる

#### Acceptance Criteria
1. When ユーザーが植物詳細画面を表示する, the Green Mate shall その植物に紐づく画像だけをギャラリーに表示する
2. When 対象植物に複数の画像がある, the Green Mate shall 成長記録として振り返りやすい時系列で画像を表示する
3. While 対象植物に画像がない, the Green Mate shall 画像がまだない状態を示し、植物詳細の閲覧を継続できるようにする
4. If 表示対象の画像を読み込めない, then the Green Mate shall 植物詳細全体を失敗扱いにせず、対象画像が表示できない状態を示す
5. The Green Mate shall ギャラリーに他ユーザーまたは他植物の画像を表示しない

### Requirement 3: 画像枚数上限の表示と制御
**Objective:** As a 観葉植物初心者, I want 写真をあと何枚追加できるか分かるようにしたい, so that 追加できない理由で迷わずに済む

#### Acceptance Criteria
1. While ユーザーが一般ユーザーとして扱われる, the Green Mate shall 1植物あたり最大5枚まで画像を追加できるようにする
2. While ユーザーが一般ユーザーとして扱われる, the Green Mate shall 植物ごとの現在画像枚数と上限をユーザーに表示する
3. If 一般ユーザーが対象植物の上限に達した状態で画像を追加しようとする, then the Green Mate shall 画像を追加せず、上限に達していることをユーザーに示す
4. While ユーザーが上限なしユーザーとして扱われる, the Green Mate shall 対象植物への画像追加枚数を5枚に制限しない
5. While ユーザーが上限なしユーザーとして扱われる, the Green Mate shall 画像上限数をユーザーに表示しない
6. When 画像が追加または削除される, the Green Mate shall 対象植物の現在画像枚数表示を更新する

### Requirement 4: 代表画像の設定と一覧表示
**Objective:** As a 観葉植物初心者, I want 植物ごとに代表画像を選びたい, so that 一覧で植物を見分けやすくできる

#### Acceptance Criteria
1. When ユーザーが対象植物のギャラリー内画像を代表画像に設定する, the Green Mate shall その画像を対象植物の代表画像として扱う
2. If ユーザーが対象植物に紐づかない画像を代表画像に設定しようとする, then the Green Mate shall その画像を対象植物の代表画像として扱わない
3. While 対象植物に代表画像が設定されている, the Green Mate shall 植物一覧でその代表画像をサムネイルとして表示する
4. While 対象植物に代表画像が設定されていない, the Green Mate shall 植物一覧で代表画像未設定の状態を表示し、一覧表示を継続する
5. When 代表画像の設定が変更される, the Green Mate shall 植物詳細と植物一覧で同じ代表画像状態を反映する

### Requirement 5: 画像削除と代表画像削除時の扱い
**Objective:** As a 観葉植物初心者, I want 不要な写真を確認してから削除したい, so that 誤って成長記録を失うことを避けられる

#### Acceptance Criteria
1. When ユーザーが画像削除を開始する, the Green Mate shall 削除前に確認ダイアログを表示する
2. If ユーザーが削除確認をキャンセルする, then the Green Mate shall 対象画像を削除せず、ギャラリーの状態を維持する
3. When ユーザーが削除を確認する, the Green Mate shall 対象画像を対象植物のギャラリーから削除する
4. While 削除対象の画像が代表画像に設定されている, the Green Mate shall 削除確認時に代表画像も解除されることを明示する
5. When 代表画像に設定されている画像が削除される, the Green Mate shall 対象植物の代表画像を未設定に戻す
6. If 画像削除に失敗する, then the Green Mate shall 対象画像と代表画像状態を失わず、削除できなかったことをユーザーに示す

### Requirement 6: 画像メタ情報の編集
**Objective:** As a 観葉植物初心者, I want 追加済み画像の撮影日やコメントを後から直したい, so that 成長記録を実際の記録内容に合わせて整えられる

#### Acceptance Criteria
1. When ユーザーがギャラリー内の画像で編集モードへの切り替えを開始する, the Green Mate shall 対象画像の撮影日やコメントなど編集可能なメタ情報を更新できる状態にする
2. While 対象画像が編集モードである, the Green Mate shall 紐づく植物の変更操作を提供しない
3. While 対象画像が編集モードである, the Green Mate shall 画像ファイルの差し替え操作を提供しない
4. When ユーザーが有効なメタ情報変更を保存する, the Green Mate shall 対象画像のメタ情報を更新し、ギャラリー上の表示に反映する
5. If ユーザーがメタ情報編集をキャンセルする, then the Green Mate shall 対象画像の既存メタ情報を変更せず、閲覧状態に戻す
6. If メタ情報更新に失敗する, then the Green Mate shall 対象画像の既存メタ情報、紐づく植物、画像ファイル、代表画像状態を失わず、更新できなかったことをユーザーに示す
7. If ユーザーが対象植物に紐づかない画像のメタ情報を更新しようとする, then the Green Mate shall その画像のメタ情報を更新しない
8. When メタ情報更新により画像の時系列上の位置が変わる, the Green Mate shall 対象植物のギャラリーを更新後の時系列で表示する

### Requirement 7: ユーザー所有データとしての画像分離
**Objective:** As a 認証済みユーザー, I want 自分の植物画像だけを扱いたい, so that 他ユーザーの私的な植物記録と混ざらない

#### Acceptance Criteria
1. When 認証済みユーザーが植物画像を追加する, the Green Mate shall そのユーザーが所有する植物にだけ画像を追加できるようにする
2. While 認証済みユーザーが植物画像を閲覧する, the Green Mate shall そのユーザーが所有する植物画像だけを表示する
3. If 認証済みユーザーが他ユーザーの植物または画像を操作しようとする, then the Green Mate shall 対象の存在を漏らさず利用できない状態として扱う
4. If 未ログインまたはセッション切れのユーザーが植物画像を閲覧または操作しようとする, then the Green Mate shall 保護された植物画像を表示せず、ログインまたは再認証が必要な状態を示す
5. The Green Mate shall ユーザー向け表示に内部所有者識別子を露出しない

### Requirement 8: 隣接機能との境界と将来拡張
**Objective:** As a プロダクト開発者, I want 画像管理の責務を植物詳細体験に限定したい, so that 既存機能と将来拡張を分けて安全に進められる

#### Acceptance Criteria
1. The Green Mate shall この仕様の範囲では画像を他植物へ移動する操作を提供しない
2. The Green Mate shall この仕様の範囲では画像管理専用画面を提供しない
3. The Green Mate shall この仕様の範囲ではユーザー向けのプラン選択、課金、上限変更操作を提供しない
4. The Green Mate shall この仕様の範囲では画像ファイルの差し替え、トリミング、サムネイル生成、画像変換を提供しない
5. The Green Mate shall この仕様の範囲ではタイムラプス表示を提供しない
6. Where 将来の成長記録強化やタイムラプス表示が追加される, the Green Mate shall 本仕様で扱う植物ごとの時系列画像を利用できる状態にする

### Requirement 9: 変更後の検証可能性
**Objective:** As a プロダクト開発者, I want 画像管理の主要な振る舞いを検証できるようにしたい, so that 後続実装が要求を満たしているか確認できる

#### Acceptance Criteria
1. When 画像管理機能が提供される, the Green Mate shall 植物詳細から画像を追加できることを検証できる
2. When 画像管理機能が提供される, the Green Mate shall 植物ごとのギャラリーに対象植物の画像だけが表示されることを検証できる
3. When 画像管理機能が提供される, the Green Mate shall 一般ユーザーの画像上限と上限なしユーザーの挙動を検証できる
4. When 画像管理機能が提供される, the Green Mate shall 代表画像の設定、一覧表示、削除時の未設定化を検証できる
5. When 画像管理機能が提供される, the Green Mate shall 他ユーザー所有の植物画像を閲覧または操作できないことを検証できる
6. When 画像管理機能が提供される, the Green Mate shall 画像メタ情報の編集、キャンセル、失敗時の既存情報維持を検証できる
