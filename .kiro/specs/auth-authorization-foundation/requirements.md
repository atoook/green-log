# Requirements Document

## Introduction
Auth Authorization Foundation は、Green Mate が複数ユーザーの生活記録アプリとして安全に機能するための共通基盤である。ユーザーは登録、ログイン、ログアウト、セッション継続を通じて自分の植物記録へアクセスできる。Green Mate は認証済みユーザーをアプリケーション内部のユーザーとして扱い、すべてのユーザー所有データをそのユーザーに閉じて作成、参照、更新、削除できるようにする。

この spec は、今後追加される水やり記録、今日のお世話、成長写真ログなどが共通利用する認証・認可の振る舞いを定義する。Plant Registration は最初の適用先として扱い、植物データがユーザーごとに分離されることを確認する。

## Boundary Context
- **In scope**: ユーザー登録、ログイン、ログアウト、セッション状態、保護 API への未認証アクセス拒否、アプリケーションユーザーの作成と再利用、現在のユーザー取得、ユーザー所有データの所有者決定、所有者スコープの参照・更新・削除、Plant API への最初の適用、認証プロバイダーからのユーザー同期イベントへの対応
- **Out of scope**: Clerk 以外の認証プロバイダー選定、独自パスワード認証、MFA やパスワードリセットの独自実装、ロール・管理者権限・組織・共有機能、植物登録項目の変更、水やり履歴、今日のお世話、成長写真ログ、画像アップロード、退会後データ保持ポリシーの詳細化
- **Adjacent expectations**: Clerk は認証基盤としてのみ利用し、アプリケーション固有のユーザー管理と所有者判定は Green Mate 側で扱う。Plant Registration は植物個体の登録項目と表示体験を引き続き所有し、この spec はそのデータアクセスを認証済みユーザーに閉じる。後続のユーザー所有ドメイン機能は、この spec の所有者モデルを前提に要件と設計を作る。

## Requirements

### Requirement 1: 認証体験
**Objective:** As a Green Mate ユーザー, I want アカウント登録、ログイン、ログアウト、セッション継続を利用したい, so that 自分の生活記録へ安全にアクセスできる

#### Acceptance Criteria
1. When 未認証ユーザーがアカウント作成を開始する, the Green Mate shall 登録を完了できる認証手段を提供する
2. When 未認証ユーザーがログインを開始する, the Green Mate shall ログインを完了できる認証手段を提供する
3. When ユーザーが登録またはログインを完了する, the Green Mate shall そのユーザーを認証済みとして扱い、保護された画面や操作へ進める
4. When 認証済みユーザーがログアウトする, the Green Mate shall セッションを終了し、保護されたユーザーデータを表示しない状態に戻す
5. While 認証状態を確認中である, the Green Mate shall 保護されたユーザーデータを未確認のまま表示しない
6. If 登録またはログインが完了しない, then the Green Mate shall ユーザーを未認証のまま扱い、保護されたユーザーデータを利用可能にしない

### Requirement 2: 保護 API の認証必須化
**Objective:** As a プロダクト開発者, I want ユーザー所有データを扱う API を認証済みユーザーだけが利用できるようにしたい, so that すべてのデータ操作を特定のユーザーに結び付けられる

#### Acceptance Criteria
1. When 未認証リクエストが保護 API に送信される, the Green Mate API shall リクエストを認証エラーとして拒否する
2. If 期限切れまたは無効な認証情報で保護 API が呼び出される, then the Green Mate API shall リクエストを認証エラーとして拒否する
3. When 有効な認証情報で保護 API が呼び出される, the Green Mate API shall 認証済みユーザーの操作としてリクエストを処理する
4. The Green Mate API shall ユーザー所有データを作成、参照、更新、削除する API を保護 API として扱う
5. Where 公開 API が含まれる, the Green Mate API shall 認証なしでユーザー所有データを返さない

### Requirement 3: アプリケーションユーザー管理
**Objective:** As a プロダクト開発者, I want 認証基盤のユーザーと Green Mate 内部のユーザーを対応付けたい, so that ドメインデータはアプリケーション内部のユーザー識別子で一貫して所有できる

#### Acceptance Criteria
1. When 認証済みユーザーが初めて Green Mate を利用する, the Green Mate shall そのユーザーに対応するアプリケーションユーザーを作成する
2. When 同じ認証済みユーザーが再度 Green Mate を利用する, the Green Mate shall 既存のアプリケーションユーザーを再利用する
3. If 同じ認証済みユーザーに対する作成処理が複数回発生する, then the Green Mate shall アプリケーションユーザーを重複作成しない
4. The Green Mate shall Clerk のユーザー識別子を認証元の識別子として扱い、ドメインデータの所有者識別子として直接利用しない
5. The Green Mate shall アプリケーション内部のユーザー識別子をドメインデータの所有者として扱う
6. While アプリケーションユーザーが無効または削除済み状態である, the Green Mate shall そのユーザーによる保護データ操作を許可しない

### Requirement 4: 所有者の決定
**Objective:** As a プロダクト開発者, I want データ所有者を認証コンテキストから決定したい, so that クライアント指定値によるなりすましや誤った所有者設定を防げる

#### Acceptance Criteria
1. When 認証済みユーザーがユーザー所有データを作成する, the Green Mate shall そのデータの所有者を認証中のアプリケーションユーザーとして設定する
2. If ユーザー所有データの作成または更新リクエストにユーザー識別子が含まれる, then the Green Mate shall その値を所有者判定に使用しない
3. The Green Mate shall すべてのユーザー所有データに所有者を持たせる
4. The Green Mate shall 保護 API の処理中に現在のアプリケーションユーザーを一意に決定する
5. If 現在のアプリケーションユーザーを決定できない, then the Green Mate shall ユーザー所有データの作成、参照、更新、削除を実行しない

### Requirement 5: 所有者スコープの認可
**Objective:** As a Green Mate ユーザー, I want 自分のデータだけを見たり変更したりできるようにしたい, so that 他のユーザーに自分の生活記録を見られたり変更されたりしない

#### Acceptance Criteria
1. When 認証済みユーザーがユーザー所有データの一覧を開く, the Green Mate shall そのユーザーが所有するデータだけを表示または返却する
2. When 認証済みユーザーが自分のユーザー所有データを参照する, the Green Mate shall そのデータを表示または返却する
3. If 認証済みユーザーが他のユーザーのデータを参照しようとする, then the Green Mate shall そのデータを表示または返却しない
4. When 認証済みユーザーが自分のユーザー所有データを更新または削除する, the Green Mate shall 対象データに対してのみ変更を適用する
5. If 認証済みユーザーが他のユーザーのデータを更新または削除しようとする, then the Green Mate shall 対象データを変更しない
6. While 複数の認証済みユーザーが Green Mate を利用している, the Green Mate shall 各ユーザーの所有データを他のユーザーから分離して扱う

### Requirement 6: Plant Registration への初回適用
**Objective:** As a 観葉植物初心者, I want 登録した植物が自分だけの記録として扱われるようにしたい, so that 自分の植物一覧と詳細を安心して見返せる

#### Acceptance Criteria
1. When 認証済みユーザーが植物を登録する, the Green Mate shall その植物を認証中のユーザーが所有する植物として作成する
2. When 認証済みユーザーが植物一覧を開く, the Green Mate shall そのユーザーが所有する植物だけを一覧に表示する
3. When 認証済みユーザーが自分の植物詳細を開く, the Green Mate shall その植物の詳細を表示する
4. If 認証済みユーザーが他のユーザーの植物詳細を開こうとする, then the Green Mate shall その植物の詳細を表示しない
5. While 認証済みユーザーが所有する植物が 0 件である, the Green Mate shall 他のユーザーの植物ではなく、そのユーザー自身の植物が未登録である状態として扱う
6. The Green Mate shall Plant Registration で定義された植物登録項目、表示項目、植物個体の扱いを維持する
7. The Green Mate shall この spec の範囲では水やり履歴、今日のお世話、成長写真ログ、共有機能を提供しない

### Requirement 7: 認証プロバイダー同期
**Objective:** As a プロダクト開発者, I want 認証プロバイダー側のユーザー変更を Green Mate のユーザー状態に反映したい, so that ユーザー情報と利用可否を継続的に整合させられる

#### Acceptance Criteria
1. When 認証プロバイダーからユーザー作成または更新の同期イベントを受け取る, the Green Mate shall 対応するアプリケーションユーザー情報を作成または更新する
2. If 同じ同期イベントまたは同じユーザーに対する同期イベントを複数回受け取る, then the Green Mate shall アプリケーションユーザーを重複作成しない
3. If 検証できない同期イベントを受け取る, then the Green Mate shall そのイベントを拒否し、アプリケーションユーザー状態を変更しない
4. When 認証プロバイダーからユーザー削除または無効化の同期イベントを受け取る, the Green Mate shall 対応するアプリケーションユーザーが以後の保護データ操作を実行できない状態にする
5. While 同期イベントが未到達である, the Green Mate shall 認証済みアクセス時にアプリケーションユーザーを作成または再利用できる

### Requirement 8: 認証失敗時の安全性
**Objective:** As a Green Mate ユーザー, I want セッション切れや認証エラーのときにも自分のデータが安全に扱われるようにしたい, so that 誤って他人に見られたり不整合な状態で操作されたりしない

#### Acceptance Criteria
1. When 保護操作の途中でセッションが無効になる, the Green Mate shall 保護操作を完了せず、再認証が必要であることを示す
2. When 認証エラーが発生する, the Green Mate shall 保護されたユーザーデータを新しく取得または更新できたものとして扱わない
3. If 認証または現在のユーザー準備に一時的な失敗が発生する, then the Green Mate shall ユーザー所有データの操作を失敗させ、別ユーザーとして処理しない
4. If 認証情報、同期イベント、または所有者を検証できない, then the Green Mate shall ユーザー所有データへのアクセスを許可しない
5. The Green Mate shall ユーザー向けのエラー表示で secret 値や内部的な認証検証情報を公開しない
