# Implementation Plan

- [x] 1. 基盤設定とデータ所有モデルを準備する
- [x] 1.1 Backend の認証関連 runtime 設定を追加する
  - Clerk session 検証と webhook 署名検証に必要な backend dependency を追加する。
  - Clerk secret、authorized parties、webhook secret、legacy owner backfill 設定を runtime settings と env example に追加する。
  - CORS と request header handling が `Authorization` を通せることを確認する。
  - secret 実値や verifier 内部情報を設定例やエラー表示に含めない状態になる。
  - _Requirements: 2.1, 2.2, 7.3, 8.4, 8.5_
  - _Boundary: Runtime Configuration_

- [x] 1.2 (P) Frontend の Clerk runtime 設定を追加する
  - `@clerk/vue` を frontend dependency として追加する。
  - publishable key の env 名を定義し、未設定時は保護データを描画しない起動失敗として扱う。
  - frontend に secret key を置かず、設定例にも secret 実値を含めない。
  - Clerk provider を組み込む前提が build で型検証できる状態になる。
  - _Requirements: 1.1, 1.2, 1.5, 8.5_
  - _Boundary: ClerkAppProvider_

- [x] 1.3 User table と Plant owner column の migration / owner scope 縦スライスを作成する
  - `users` table を UUID text primary key、unique `clerk_user_id`、status、profile fields、UTC timestamps で作成する。
  - `plants` に not null owner reference と owner lookup 用 index を追加する。
  - 既存 Plant row がある場合は明示 backfill 設定なしで ownerless migration が進まないようにする。
  - Alembic metadata が User model と Plant owner schema を検出できる状態になる。
  - Plant repository / service を owner id 必須の create/list/detail contract に変更し、NOT NULL owner migration と同じ縦スライスで full tests を保つ。
  - Local smoke が smoke application user を作成して owner-scoped Plant CRUD を通せる状態になる。
  - _Requirements: 3.3, 3.4, 3.5, 4.1, 4.2, 4.3, 5.1, 5.2, 5.3, 5.6, 6.1, 6.2, 6.3, 6.4, 6.6_
  - _Boundary: AuthMigration, PlantOwnerScope, Smoke Verification_

- [x] 1.4 Backend test data factory を所有者モデル前提へ拡張する
  - application user と owner-scoped Plant を作成できる test helper を用意する。
  - user A / user B の分離を test data factory だけで再現できる状態にする。
  - Plant API test が owner_user_id を持つ row を準備できる状態になる。
  - _Requirements: 3.1, 3.2, 3.5, 4.3, 5.6, 6.2_
  - _Boundary: Backend Test Infrastructure_
  - _Depends: 1.3_

- [x] 2. Backend の application user と current user を実装する
- [x] 2.1 UserRepository と UserService で application user lifecycle を扱う
  - `clerk_user_id` unique key による idempotent upsert を実装する。
  - 同じ Clerk user の初回アクセスと再アクセスで同一 application user を返す。
  - disabled / deleted status を保存し、active 以外を protected operation に使えない状態として表現する。
  - domain owner として Clerk User ID ではなく internal user id だけを返せる状態になる。
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 7.1, 7.2, 7.4, 7.5_
  - _Boundary: UserService, UserRepository_
  - _Depends: 1.3_

- [x] 2.2 (P) ClerkSessionVerifier を実装する
  - Bearer token の欠落、期限切れ、無効 token を fail closed の認証失敗に変換する。
  - Clerk SDK と FastAPI request の adapter 境界を verifier に閉じる。
  - valid token から Clerk user id と任意 profile 情報を抽出する。
  - verifier error が token、secret、raw claims を user-facing message に出さない状態になる。
  - _Requirements: 2.1, 2.2, 2.3, 4.4, 8.4, 8.5_
  - _Boundary: ClerkSessionVerifier_
  - _Depends: 1.1_

- [x] 2.3 CurrentUserDependency を protected API の共通入口にする
  - Clerk claims を application user の get-or-create に接続する。
  - active user の internal user id だけを `CurrentUser` として domain service に渡す。
  - 認証失敗は 401、disabled / deleted user は 403 に変換し、Service / Repository に HTTP 例外を漏らさない。
  - current user を決定できない request では domain data operation が実行されない状態になる。
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 3.1, 3.2, 3.6, 4.4, 4.5, 7.5, 8.1, 8.3, 8.4, 8.5_
  - _Boundary: CurrentUserDependency_
  - _Depends: 2.1, 2.2_

- [x] 2.4 CurrentUserDependency の test override fixture を追加する
  - protected router test で current user を user A / user B / disabled user に差し替えられる fixture を用意する。
  - dependency override が test ごとに cleanup され、別 test の current user に漏れない状態にする。
  - Plant API と webhook 後状態の test が共通 fixture で current user を再現できる状態になる。
  - _Requirements: 2.3, 3.6, 4.4, 4.5, 5.6, 8.3_
  - _Boundary: Backend Test Infrastructure, CurrentUserDependency_
  - _Depends: 2.3_

- [x] 2.5 Auth / user の unit test を追加する
  - first access、再アクセス、並行相当の重複 upsert で user が重複しないことを検証する。
  - invalid token と missing token が 401 相当、disabled / deleted user が 403 相当になることを検証する。
  - current user の `id` が internal user id であり Clerk User ID を owner として返さないことを検証する。
  - backend unit test で auth/user 境界の主要失敗パスが再現できる状態になる。
  - _Requirements: 2.1, 2.2, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 4.4, 4.5, 8.3, 8.4, 8.5_
  - _Boundary: Backend Auth Tests_
  - _Depends: 2.1, 2.2, 2.3_

- [x] 3. Frontend の認証 shell と typed API client を実装する
- [x] 3.1 (P) ClerkAppProvider、FrontendRouter、AuthGate、AuthHeaderControls を組み込む
  - app bootstrap に Clerk provider を追加し、route content を認証状態 gate の内側に配置する。
  - router に protected route metadata を付け、保護画面の表示判定が AuthGate に集約される状態にする。
  - signed-out 状態で登録・ログイン導線を表示し、signed-in 状態で保護画面を表示する。
  - auth loading 中と logout 後に Plant data を描画しない。
  - header からログイン、登録、ログアウト、user menu の導線が使える状態になる。
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 2.5, 8.1_
  - _Boundary: ClerkAppProvider, FrontendRouter, AuthGate, AuthHeaderControls_
  - _Depends: 1.2_

- [x] 3.2 (P) AuthenticatedApiClient と auth error 型を実装する
  - request ごとに Clerk session token を取得し、Bearer token として送信する。
  - token がない状態では保護操作を成功扱いせず、auth error として扱う。
  - 401、403、404、422、network/server error を typed error に分類する。
  - user-facing message に secret や verifier 内部情報が出ない状態になる。
  - _Requirements: 2.1, 2.2, 2.3, 8.1, 8.2, 8.3, 8.5_
  - _Boundary: AuthenticatedApiClient_
  - _Depends: 1.2_

- [x] 3.3 PlantsApiClient と Plant composable を token-aware client へ移行する
  - Plant list、create、detail request が common authenticated client 経由になる。
  - component から直接 fetch せず、既存の page/composable 分離を維持する。
  - request / response 型に owner field を追加せず、client 指定の user id を送らない。
  - Plant の既存登録項目と表示項目が変更されない状態になる。
  - _Requirements: 4.2, 5.1, 5.2, 6.1, 6.2, 6.3, 6.5, 6.6, 8.2_
  - _Boundary: PlantsApiClient, Plant Composables_
  - _Depends: 3.2_

- [x] 3.4 Frontend の保護画面エラー状態を認証失敗に対応させる
  - signed-out、auth loading、session expired、forbidden、not found、validation の表示状態を整理する。
  - auth error 発生時に新しい Plant data の取得・作成が成功した表示にならないようにする。
  - logout 後に直前ユーザーの Plant list / detail が画面に残らない状態になる。
  - 0 件状態は他ユーザーのデータではなく自分の植物未登録として表示される。
  - 水やり履歴、今日のお世話、成長写真ログ、共有機能の UI 導線をこの spec で追加しないことを確認する。
  - _Requirements: 1.4, 1.5, 1.6, 5.3, 6.4, 6.5, 6.7, 8.1, 8.2, 8.3, 8.5_
  - _Boundary: AuthGate, Plant UI State_
  - _Depends: 3.1, 3.3_

- [x] 4. Clerk webhook 同期を実装する
- [x] 4.1 (P) WebhookVerifier で Clerk event を署名検証する
  - raw body と Svix headers を使って webhook signature を検証する。
  - `user.created`、`user.updated`、`user.deleted` だけを typed event として受け付ける。
  - 検証できない event は UserService に到達せず、400 相当の失敗になる。
  - raw payload、signature secret、token が log や user-facing error に出ない状態になる。
  - _Requirements: 7.3, 8.4, 8.5_
  - _Boundary: WebhookVerifier_
  - _Depends: 1.1_

- [x] 4.2 ClerkWebhookService と webhook route で user state を同期する
  - verified `user.created` / `user.updated` を application user upsert に接続する。
  - verified `user.deleted` を deleted status へ反映し、以後の protected operation を許可しない状態にする。
  - duplicate delivery や API lazy upsert 済み user に対して重複 row を作らない。
  - `POST /webhooks/clerk` が検証済み event だけに `received` response を返す状態になる。
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 8.4, 8.5_
  - _Boundary: WebhookRouter, ClerkWebhookService_
  - _Depends: 2.1, 4.1_

- [x] 4.3 Webhook の integration test を追加する
  - invalid signature が user state を変更しないことを検証する。
  - duplicate create/update event が application user を重複作成しないことを検証する。
  - deleted event 後の user が protected data operation に使えないことを検証する。
  - webhook retry と lazy upsert の順序差が安全に処理される状態になる。
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 8.3, 8.4, 8.5_
  - _Boundary: Webhook Tests_
  - _Depends: 4.2_

- [x] 5. Plant API を owner scope に統合する
- [x] 5.1 Plant repository / service を owner-scoped contract へ変更する
  - Plant create は `CurrentUser.id` 由来の owner id を必須入力として保存する。
  - list は owner id で絞り込み、detail は plant id と owner id の組み合わせで取得する。
  - `PlantCreate` と `PlantRead` に owner field を露出せず、client 指定 user id を所有者判定に使わない。
  - update/delete を後続機能で追加する際も同じ owner lookup を使える service contract になる。
  - _Requirements: 3.4, 3.5, 4.1, 4.2, 4.3, 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7_
  - _Boundary: PlantOwnerScope_
  - _Depends: 1.3_

- [x] 5.2 Plant router を protected route として current user に接続する
  - Plant list、create、detail に current user dependency を適用する。
  - 未認証・無効 token は 401、disabled / deleted user は 403、他ユーザー Plant detail は 404 として扱う。
  - 公開 route から user-owned Plant data が返らないことを route policy として固定する。
  - 水やり履歴、今日のお世話、成長写真ログ、共有機能の endpoint をこの spec で追加しないことを確認する。
  - valid user の request だけが owner-scoped service に到達する状態になる。
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 4.4, 4.5, 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 6.1, 6.2, 6.3, 6.4, 6.7, 8.1, 8.3, 8.4_
  - _Boundary: PlantRouter, CurrentUserDependency Integration_
  - _Depends: 2.3, 5.1_

- [x] 5.3 Plant API の owner separation integration test を追加する
  - auth なしの Plant list/create/detail が 401 になり、Plant service を成功実行しないことを検証する。
  - user A と user B の create/list/detail が互いに分離されることを検証する。
  - 他ユーザー Plant detail は存在を返さず 404 になり、対象 row が変更されないことを検証する。
  - owner field が Plant API response に露出しないことを検証する。
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 4.1, 4.2, 4.4, 4.5, 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 8.1, 8.2, 8.3, 8.4_
  - _Boundary: Plant API Tests_
  - _Depends: 5.2_

- [x] 5.4 Local SQLite と Turso/libSQL の owner-scoped smoke を更新する
  - smoke user を作成し、その internal user id で Plant CRUD を実行する。
  - migration 後に ownerless Plant が作成されないことを local SQLite で検証する。
  - Turso/libSQL path でも user upsert と owner-scoped Plant create/list/detail が通ることを検証する。
  - smoke failure が実装完了判定を止められる状態になる。
  - _Requirements: 3.3, 4.1, 4.3, 5.1, 5.6, 6.1, 6.2, 8.4_
  - _Boundary: AuthMigration, Smoke Verification_
  - _Depends: 5.2_

## Implementation Notes

- 1.3: `plants.owner_user_id` の NOT NULL migration は Plant owner-scoped repository/service と local smoke owner 作成を同じ縦スライスで実装しないと既存 Plant CRUD が壊れるため、5.1 の実装と 5.4 の local smoke 更新を前倒しした。5.2 は real `CurrentUserDependency` の完成、5.4 は Turso/libSQL smoke 実行を引き続き所有する。

- [x] 6. Cross-boundary integration と最終検証を完了する
- [x] 6.1 Backend router composition と error contract を全体で検証する
  - webhook router と protected Plant router が main application に登録される。
  - auth/user/webhook/plant の error response が 401、403、404、422、400 の設計 contract に沿うことを確認する。
  - backend tests が auth、webhook、owner separation、disabled user、secret-safe error の回帰を含む状態になる。
  - `pytest` で backend の必須 test suite が通る状態になる。
  - _Requirements: 2.1, 2.2, 2.4, 2.5, 3.6, 5.3, 5.5, 7.3, 8.1, 8.2, 8.3, 8.4, 8.5_
  - _Boundary: Backend Integration Validation_
  - _Depends: 4.3, 5.3_

- [x] 6.2 Frontend build と保護 UI flow を検証する
  - signed-out では Plant list/detail が描画されず、登録・ログイン導線だけが表示されることを検証する。
  - signed-in 相当の状態では own empty state、Plant create、Plant detail navigation が既存 UI contract のまま動くことを検証する。
  - session expired / auth error が成功状態や stale data として残らないことを検証する。
  - TypeScript build が `any` なしの auth/API 型で通る状態になる。
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 6.1, 6.3, 6.5, 6.6, 8.1, 8.2, 8.3, 8.5_
  - _Boundary: Frontend Integration Validation_
  - _Depends: 3.4, 5.2_

- [x] 6.3 実装完了前の end-to-end owner model regression を固定する
  - backend と frontend の typed API contract が owner field 非公開のまま一致することを確認する。
  - 初回ログイン相当の request で application user が作成され、2 回目以降は再利用されることを API flow として検証する。
  - user A が user B の Plant を list/detail/update/delete pattern で扱えない owner-only model が将来 domain に再利用できることを確認する。
  - 水やり履歴、今日のお世話、成長写真ログ、共有機能がこの spec の実装差分に含まれないことを確認する。
  - backend test、migration smoke、frontend build の結果が揃って implementation gate を通せる状態になる。
  - _Requirements: 2.3, 3.1, 3.2, 3.3, 3.4, 3.5, 4.1, 4.2, 4.3, 4.4, 4.5, 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 6.1, 6.2, 6.3, 6.4, 6.6, 6.7, 7.5, 8.1, 8.2, 8.3, 8.4, 8.5_
  - _Boundary: End-to-End Auth Authorization Validation_
  - _Depends: 6.1, 6.2_
