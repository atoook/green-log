# Requirements Document

## Introduction
Plant Photo Schema Foundation は、Green Mate が将来の成長写真ログや代表写真表示を自然に追加できるよう、植物個体と写真記録の関係を整理するための基盤仕様である。現在は植物本体に単一の画像URLを持つ前提だが、今後は1つの植物個体に複数枚の写真を紐づけ、一覧や詳細ヘッダーではその中から1枚を代表写真として扱える必要がある。

この仕様では、画像アップロードやギャラリーUIを作るのではなく、植物写真をユーザー所有データとして保持できる構造、代表写真を未設定にできる状態、既存の一覧・詳細表示が壊れない最小限のレスポンス互換を定義する。正式リリース前で既存画像データの保持は不要なため、旧来の植物本体画像項目から新しい写真記録へのデータ移行は扱わない。

## Boundary Context
- **In scope**: 植物個体に複数写真を紐づけられる永続化構造、代表写真の nullable な参照、写真記録の所有者分離、植物一覧・詳細取得における代表画像URLの最小互換、旧来の植物本体画像項目を廃止する前提整理
- **Out of scope**: 画像ファイルのアップロード、画像ファイルの保存・削除、外部画像ストレージ連携、写真CRUD APIの本格実装、成長記録ギャラリーUI、写真の並び替え、サムネイル生成、既存画像データの本番移行
- **Adjacent expectations**: 植物登録・一覧・詳細は引き続き植物個体を扱い、この仕様は写真記録を後続機能が参照できる基礎として整える。画像アップロード機能と成長記録ギャラリーは、この仕様で用意した写真記録と代表写真の前提を利用するが、本仕様では操作画面やファイル処理を提供しない

## Requirements

### Requirement 1: 植物写真記録の保持
**Objective:** As a プロダクト開発者, I want 1つの植物個体に複数の写真記録を紐づけられるようにしたい, so that 将来の成長記録ギャラリーや日付付き写真表示を追加できる

#### Acceptance Criteria
1. When 写真記録が植物個体に紐づけられる, the Green Mate shall その写真記録を対象の植物個体に属する記録として保持する
2. When 同じ植物個体に複数の写真記録が紐づけられる, the Green Mate shall それぞれの写真記録を独立した記録として区別できる状態で保持する
3. The Green Mate shall 写真記録に画像参照情報を保持できる
4. The Green Mate shall 写真記録に撮影日を任意項目として保持できる
5. The Green Mate shall 写真記録にコメントを任意項目として保持できる
6. The Green Mate shall 写真記録に作成日時と更新日時を保持できる

### Requirement 2: 代表写真の管理
**Objective:** As a 観葉植物初心者, I want 植物ごとに代表写真が1枚だけ表示されるようにしたい, so that 一覧や詳細ヘッダーで植物を見分けやすくできる

#### Acceptance Criteria
1. When 植物個体に代表写真が設定される, the Green Mate shall その植物個体の代表写真として1つの写真記録を参照できる
2. While 植物個体に代表写真が設定されている, the Green Mate shall 一覧と詳細でその代表写真を植物を識別する補助情報として扱う
3. While 植物個体に代表写真が設定されていない, the Green Mate shall 写真がない状態でも植物個体の登録、一覧表示、詳細表示を継続する
4. If 代表写真として参照する写真記録が対象の植物個体に属していない, then the Green Mate shall その写真記録を対象植物の代表写真として扱わない
5. If 代表写真として参照する写真記録が利用できない, then the Green Mate shall その植物個体を代表写真未設定として扱える

### Requirement 3: 植物本体画像項目への依存廃止
**Objective:** As a プロダクト開発者, I want 植物本体の単一画像項目に依存しない設計へ移行したい, so that 複数写真と代表写真の責務を分けられる

#### Acceptance Criteria
1. When 植物個体が新規登録される, the Green Mate shall 植物本体の単一画像項目を必須項目として要求しない
2. When 植物個体が新規登録される, the Green Mate shall 代表写真が未設定の植物個体として登録できる
3. The Green Mate shall 植物本体の単一画像項目を、写真記録の保存先として扱わない
4. The Green Mate shall 画像ファイルや画像参照情報を植物本体ではなく写真記録として扱える
5. While 正式リリース前の既存画像データがある場合, the Green Mate shall その画像データの保持や移行を完了条件にしない

### Requirement 4: ユーザー所有データとしての写真分離
**Objective:** As a 認証済みユーザー, I want 自分の植物写真だけが自分の植物に紐づくようにしたい, so that 他ユーザーの私的な植物記録と混ざらない

#### Acceptance Criteria
1. When 写真記録が作成される, the Green Mate shall 認証済みユーザーをその写真記録の所有者として扱う
2. When 写真記録が植物個体に紐づけられる, the Green Mate shall 写真記録の所有者と植物個体の所有者が一致する場合だけ紐づけを有効にする
3. While 認証済みユーザーが植物写真に関わる情報を取得する, the Green Mate shall そのユーザーが所有する写真記録だけを対象にする
4. If 認証済みユーザーが他ユーザーの植物または写真記録を参照しようとする, then the Green Mate shall 対象の存在を漏らさず利用不可として扱う
5. The Green Mate shall 写真記録の所有者識別子をユーザー向けレスポンスに露出しない

### Requirement 5: 既存一覧・詳細表示との互換
**Objective:** As a 観葉植物初心者, I want 写真構造が変わっても既存の植物一覧と詳細を使い続けたい, so that 画像アップロード前段の変更で現在の植物確認体験が壊れない

#### Acceptance Criteria
1. When ユーザーが植物一覧を取得する, the Green Mate shall 各植物個体について代表画像URLを既存画面が扱える形で返せる
2. When ユーザーが植物詳細を取得する, the Green Mate shall 対象植物の代表画像URLを既存画面が扱える形で返せる
3. While 植物個体に代表写真がない, the Green Mate shall 一覧と詳細の代表画像URLを未設定として返せる
4. While 代表写真に表示可能な画像参照情報がない, the Green Mate shall 一覧と詳細の代表画像URLを未設定として返せる
5. The Green Mate shall 既存の植物名、家に来た日、メモ、水やり周期、作成日時、更新日時の表示に必要な情報を引き続き返す
6. The Green Mate shall 植物一覧と植物詳細の取得において、写真が未登録であることを失敗として扱わない

### Requirement 6: 後続機能との境界
**Objective:** As a プロダクト開発者, I want 写真基盤の責務を永続化構造と最小互換に限定したい, so that 画像アップロードやギャラリー機能を独立して追加できる

#### Acceptance Criteria
1. The Green Mate shall この仕様の範囲では画像ファイルのアップロード操作を提供しない
2. The Green Mate shall この仕様の範囲では画像ファイルの保存先との連携を提供しない
3. The Green Mate shall この仕様の範囲では画像ファイルの削除処理を提供しない
4. The Green Mate shall この仕様の範囲では成長記録ギャラリーの画面表示を提供しない
5. The Green Mate shall この仕様の範囲では写真の並び替え、サムネイル生成、画像変換を提供しない
6. Where 後続の画像アップロード機能が追加される, the Green Mate shall この仕様で扱う写真記録に画像参照情報を紐づけられる前提を提供する

### Requirement 7: 変更後の検証可能性
**Objective:** As a プロダクト開発者, I want 写真基盤への移行が検証可能であることを確認したい, so that 後続実装が安全に依存できる

#### Acceptance Criteria
1. When 写真基盤の変更が適用される, the Green Mate shall 代表写真未設定の植物個体を正常に扱えることを検証できる
2. When 写真基盤の変更が適用される, the Green Mate shall 1つの植物個体に複数写真を紐づけられることを検証できる
3. When 写真基盤の変更が適用される, the Green Mate shall 他ユーザー所有の植物と写真が紐づかないことを検証できる
4. When 写真基盤の変更が適用される, the Green Mate shall 植物一覧と植物詳細が写真未登録でも取得できることを検証できる
5. When 写真基盤の変更が適用される, the Green Mate shall 旧来の植物本体画像項目に依存しないことを検証できる

