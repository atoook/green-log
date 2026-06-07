# Implementation Plan

- [x] 1. Foundation: S3 upload と UUID 写真基盤を実装可能にする
- [x] 1.1 Backend の S3 と multipart upload 実行前提を追加する
  - S3 接続に必要な環境変数を設定として読み込めるようにする。
  - AWS credential は secret として扱い、ログやエラーに実値が出ない状態にする。
  - multipart upload を受け付けるための依存関係が backend runtime と test runtime で解決できる。
  - `POST /photos/upload` の実装に必要な runtime prerequisite が揃っていることを設定テストで確認できる。
  - _Requirements: 1.1, 1.2, 6.4, 7.6_

- [x] 1.2 写真 ID と代表画像参照を UUID text に移行する
  - 既存写真データなしの前提で、写真 ID と代表画像参照を UUID text として扱う schema に変更する。
  - 写真には公開 URL ではなく object key を保存し、画像 URL 保存列に依存しない状態にする。
  - ユーザーごとの上限なし判定を保存できる列を追加する。
  - migration 後に `plant_photos.id`、`plants.cover_photo_id`、`users.photo_upload_unlimited` の schema が検証できる。
  - _Requirements: 3.1, 3.4, 4.1, 4.2, 7.6, 8.3, 8.4_

- [x] 1.3 写真の入力制約と API 表現を定義する
  - 画像種別、拡張子、サイズ、1植物あたりの一般ユーザー上限を共有制約として表現する。
  - 写真登録、写真表示、ギャラリー、枚数上限、代表画像設定の API 表現を camelCase で扱える。
  - gallery/list/detail の通常 response に owner id、storage key、内部 user id が含まれないことを型と schema で確認できる。
  - upload/register flow では一時的な object key を扱えるが、通常のギャラリー表示では表示用 URL だけを返す状態にする。
  - _Requirements: 1.2, 2.1, 3.2, 3.5, 4.3, 6.5, 7.3, 7.4_

- [x] 1.4 S3 object 操作と表示 URL 生成を分離する
  - object key から現在の S3 public URL を生成できる。
  - upload は ACL を指定せず S3 に object を保存し、delete は対象 object を削除できる。
  - S3 失敗時に credential、bucket 名、object key をユーザー向けエラーへ露出しない。
  - DB へ公開 URL を保存しなくても、代表画像やギャラリーの表示 URL を生成できることを storage 単位のテストで確認できる。
  - _Requirements: 1.2, 4.3, 5.3, 6.5, 7.6_

- [x] 2. Backend: owner-scoped な写真 lifecycle を提供する
- [x] 2.1 owner と plant に閉じた写真永続化操作を追加する
  - 対象植物の写真だけを時系列で取得できる。
  - 写真 count、作成、代表画像設定、削除、代表画像解除を owner と plant の条件付きで実行できる。
  - 他ユーザーまたは他植物の写真は通常 path から取得・設定・削除できない。
  - 代表画像削除時に対象植物の代表画像参照が未設定へ戻ることを repository test で確認できる。
  - _Requirements: 2.1, 2.2, 2.5, 4.1, 4.2, 5.3, 5.5, 6.2, 6.3, 8.2, 8.4, 8.5_
  - _Boundary: PlantPhotoRepository_

- [x] 2.2 (P) 画像 upload の検証と object key 発行を実装する
  - upload 時に `plantId`、認証済み owner、画像種別、拡張子、サイズ、枚数上限を検証する。
  - object key は `plants/{plant_id}/{photo_uuid}.{ext}` 形式で生成され、user id を含まない。
  - 一般ユーザーが上限到達後に upload しようとすると S3 保存前に拒否される。
  - valid upload では S3 object が作成され、object key が返ることを service test で確認できる。
  - _Requirements: 1.1, 1.2, 1.5, 3.1, 3.3, 3.4, 6.1, 6.3, 7.1, 7.6, 8.1, 8.3, 8.5_
  - _Boundary: PlantPhotoService, S3StorageClient_
  - _Depends: 1.1, 1.2, 1.3, 1.4_

- [x] 2.3 写真登録、一覧、代表画像、削除の domain flow を実装する
  - 登録 API 相当の処理でも owner と枚数上限を再検証し、upload 後の競合で上限を超えない。
  - 一覧は対象植物の写真、現在枚数、上限または上限なし状態、代表画像状態を返せる。
  - 代表画像設定は対象植物のギャラリー内画像だけを許可する。
  - 削除は S3 delete 成功後に DB から写真を削除し、代表画像だった場合は未設定へ戻す。
  - S3 delete 失敗時は DB record と代表画像状態が維持されることを service test で確認できる。
  - _Requirements: 1.2, 1.3, 1.5, 2.1, 2.2, 2.5, 3.2, 3.3, 3.5, 3.6, 4.1, 4.2, 4.5, 5.3, 5.5, 5.6, 6.1, 6.2, 6.3, 8.2, 8.3, 8.4, 8.5_
  - _Boundary: PlantPhotoService_

- [x] 2.4 写真操作の protected API surface を追加する
  - `POST /photos/upload` が multipart の `plantId` と `file` を受け取り、object key を返す。
  - 植物配下の写真一覧、写真登録、代表画像設定、写真削除 API が認証済み owner のみ利用できる。
  - validation、quota、not found、storage failure が既存の API error 方針に沿って HTTP status へ変換される。
  - OpenAPI 上で必要な photo route は公開され、owner/storage/internal field は response component に露出しない。
  - _Requirements: 1.1, 1.2, 1.5, 2.1, 3.3, 4.1, 5.3, 5.6, 6.1, 6.3, 6.4, 6.5, 7.1, 7.2, 7.3, 7.4, 8.1, 8.5_

- [x] 2.5 既存植物 read model の代表画像互換を object key ベースへ更新する
  - 植物一覧、植物詳細、水やり summary は DB の object key から生成した表示 URL を `imageUrl` として返す。
  - 代表画像未設定または表示 URL を生成できない場合は `imageUrl: null` として既存画面を継続できる。
  - 代表画像が他 owner または他 plant の写真を指す場合は表示 URL を返さない。
  - 既存の植物作成・更新・水やり取得が写真未登録でも失敗しないことを regression test で確認できる。
  - _Requirements: 4.3, 4.4, 4.5, 5.5, 6.2, 6.5, 7.6, 8.4, 8.5_

- [x] 3. Frontend: 植物詳細に画像ギャラリーを統合する
- [x] 3.1 写真 API client と multipart request helper を追加する
  - 写真 API の request/response 型を `any` なしで扱える。
  - upload request は `FormData` を使い、ブラウザが multipart boundary を設定できるよう `Content-Type` を手動設定しない。
  - 写真一覧、登録、代表画像設定、削除は authenticated client 経由で呼び出せる。
  - owner id、storage key、内部 user id を frontend の通常表示型に含めないことを静的テストで確認できる。
  - _Requirements: 1.1, 1.2, 2.1, 3.2, 4.1, 5.3, 6.4, 6.5, 7.1, 7.3, 8.1_
  - _Boundary: PlantPhotosApiClient_

- [x] 3.2 (P) 画像ギャラリーの状態管理を追加する
  - 植物 ID に基づいてギャラリー、枚数上限、代表画像状態を読み込める。
  - upload と登録、代表画像設定、削除をそれぞれ独立した loading/error/success state で扱える。
  - auth、forbidden、not found では gallery を clear し、validation/storage/server error では既存 gallery を維持する。
  - 代表画像変更または代表画像削除時に植物詳細の `imageUrl` を同期できる callback が呼ばれることを composable test で確認できる。
  - _Requirements: 1.3, 1.5, 2.1, 2.5, 3.2, 3.3, 3.5, 3.6, 4.1, 4.5, 5.3, 5.5, 5.6, 6.2, 6.3, 8.2, 8.3, 8.4, 8.5_
  - _Boundary: usePlantPhotos_
  - _Depends: 3.1_

- [x] 3.3 (P) 植物画像ギャラリー UI を追加する
  - 画像なし状態、時系列画像一覧、現在枚数と上限、上限なしユーザーの上限非表示を描画する。
  - 画像追加、代表画像設定、削除開始、削除キャンセル、削除確定の操作を presentation component から event として出せる。
  - 削除確認では代表画像を削除する場合に代表画像も解除されることを明示する。
  - 個別画像の読み込み失敗は tile fallback に留め、植物詳細全体を失敗表示にしないことを UI test で確認できる。
  - _Requirements: 1.1, 1.3, 2.1, 2.2, 2.3, 2.4, 3.2, 3.5, 4.1, 4.3, 4.4, 5.1, 5.2, 5.4, 7.2, 7.3, 7.4, 7.5, 8.2, 8.4_
  - _Boundary: PlantImageGallery_

- [x] 3.4 植物詳細画面へギャラリーを統合する
  - 植物詳細画面で plant detail、水やり、画像ギャラリーの error surface が混ざらず表示される。
  - 表示中の植物だけが画像追加対象になり、他植物への移動や専用画像管理画面への導線は出ない。
  - 代表画像設定後に詳細画像と一覧へ戻ったときのサムネイルが同じ状態になる。
  - 画像追加・削除後に現在枚数表示が更新されることを page-level test で確認できる。
  - _Requirements: 1.1, 1.3, 1.4, 2.3, 3.2, 3.6, 4.3, 4.4, 4.5, 5.6, 6.4, 7.1, 7.2, 8.1, 8.4_

- [x] 4. Integration validation と regression を完了する
- [x] 4.1 Backend API と owner separation の統合テストを追加する
  - upload、登録、一覧、代表画像設定、削除の happy path と failure path を API 経由で検証できる。
  - 他 owner の植物や写真に対する upload/register/list/cover/delete は存在を漏らさない。
  - 一般ユーザー5枚上限と上限なしユーザーの API 挙動を検証できる。
  - API response に owner id、storage key、internal auth field が出ないことを contract test で確認できる。
  - _Requirements: 1.1, 1.2, 1.5, 2.1, 2.5, 3.1, 3.3, 3.4, 4.1, 4.2, 5.3, 5.5, 5.6, 6.1, 6.2, 6.3, 6.4, 6.5, 8.1, 8.2, 8.3, 8.4, 8.5_

- [x] 4.2 Frontend の API、state、UI regression を追加する
  - API client が direct fetch ではなく authenticated client を使うことを検証できる。
  - upload では JSON Content-Type を付与しないことを検証できる。
  - ギャラリーの空状態、quota 表示、代表画像表示、削除確認、代表画像削除 warning、画像読み込み失敗 fallback を検証できる。
  - 植物詳細画面で画像ギャラリーが既存の編集・水やり UI と責務を分けて表示されることを検証できる。
  - _Requirements: 1.1, 1.3, 1.5, 2.1, 2.3, 2.4, 3.2, 3.5, 3.6, 4.1, 4.3, 4.4, 4.5, 5.1, 5.2, 5.4, 5.6, 6.4, 6.5, 7.1, 7.2, 7.3, 7.4, 7.5, 8.1, 8.2, 8.4_

- [x] 4.3 Migration、smoke、build の最終確認を更新する
  - SQLite migration test と downgrade test が UUID 写真 ID、object key、上限なしユーザー列を検証する。
  - local/Turso smoke が storage URL resolver、代表画像 URL、other-owner 非表示、写真未登録継続を検証する。
  - backend pytest と frontend build が通り、既存植物登録・編集・水やりの regression が発生していないことを確認できる。
  - S3 実 bucket がなくても通常 test suite は test double で実行でき、S3 adapter 単位の動作は分離して検証できる。
  - _Requirements: 2.5, 4.3, 4.4, 5.5, 6.2, 6.3, 6.5, 7.6, 8.1, 8.2, 8.3, 8.4, 8.5_
