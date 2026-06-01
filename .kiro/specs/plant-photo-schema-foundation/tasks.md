# Implementation Plan

- [ ] 1. 写真基盤の永続化構造を追加する
- [x] 1.1 写真基盤 migration の schema 検証を固定する
  - 写真記録が owner、植物、画像参照、撮影日、コメント、作成・更新日時を保持できることを schema inspection で確認する。
  - 植物本体に代表写真参照が追加され、旧来の単一画像項目が残っていないことを確認する。
  - downgrade 後に写真テーブルと代表写真参照が残らないことを確認する。
  - 完了時点で、migration test が失敗する形で期待 schema を明示している。
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 2.1, 3.3, 3.4, 3.5, 7.5_
  - _Boundary: Migration and verification_

- [x] 1.2 写真記録と代表写真参照の永続化構造を実装する
  - 写真記録をユーザー所有データとして保持し、植物個体に複数紐づけられる状態にする。
  - 新規植物は代表写真未設定を正規状態として保存できるようにする。
  - 旧来の植物本体画像項目には画像参照を保存しない状態にする。
  - 完了時点で、schema 検証が通り、写真未設定の植物と複数写真の保存先が存在する。
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 2.1, 2.3, 3.2, 3.3, 3.4, 3.5, 4.1, 6.6, 7.1, 7.2, 7.5_
  - _Boundary: PlantPhoto, Plant, Migration and verification_

- [ ] 2. Backend の代表写真 read contract を実装する
- [x] 2.1 植物一覧・詳細で代表写真URLを導出する
  - 代表写真が同じ owner と植物に属する場合だけ、植物一覧・詳細の代表画像URLとして返す。
  - 代表写真がない、不正、他 owner、他植物、または表示可能URLなしの場合は未設定として返す。
  - 写真未登録の植物一覧・詳細取得は失敗させない。
  - 完了時点で、Backend の read path は owner scope を保ったまま代表写真URLまたは null を返す。
  - _Depends: 1.2_
  - _Requirements: 2.2, 2.3, 2.4, 2.5, 4.2, 4.3, 4.4, 5.1, 5.2, 5.3, 5.4, 5.6, 7.1, 7.3, 7.4_
  - _Boundary: PlantRepository_

- [x] 2.2 植物作成と API schema を写真未設定前提へ移行する
  - 植物作成では画像URLを必須にも保存対象にもせず、代表写真未設定の植物を作成する。
  - レスポンスでは既存互換の代表画像URL field を維持し、owner 情報や内部写真参照を露出しない。
  - legacy な画像URL入力が送られても、植物本体画像や写真記録として保存しない。
  - 完了時点で、植物作成レスポンスは基本情報を維持しつつ代表画像URLを null として返す。
  - _Depends: 2.1_
  - _Requirements: 3.1, 3.2, 3.3, 4.5, 5.1, 5.2, 5.3, 5.5, 5.6, 7.1, 7.4, 7.5_
  - _Boundary: PlantService, Plant schemas_

- [x] 2.3 水やり関連の植物 summary を代表写真URLへ追従させる
  - 水やり関連表示で使う植物 summary が、旧来の植物本体画像ではなく代表写真URLを返すようにする。
  - 代表写真が未設定または表示不可の場合でも、水やり関連取得は失敗させない。
  - 完了時点で、植物一覧・詳細と水やり関連 summary の画像URL解釈が一致している。
  - _Depends: 2.1_
  - _Requirements: 2.2, 2.3, 5.3, 5.4, 5.5, 5.6, 7.4, 7.5_
  - _Boundary: PlantRepository, Watering summary_

- [ ] 3. Frontend の植物登録・表示を代表写真互換に合わせる
- [x] 3.1 植物登録の画像URL入力を取り除く
  - 植物登録の入力状態と作成 payload から画像URLを外す。
  - 登録フォームは画像URL入力欄を表示せず、植物名・家に来た日・水やり周期・メモで登録できる。
  - 完了時点で、Frontend の型検査上も植物作成入力に画像URLが含まれない。
  - _Depends: 2.2_
  - _Requirements: 3.1, 3.2, 3.3, 6.1, 6.2, 6.3, 7.1, 7.5_
  - _Boundary: Plants UI types/forms_

- [x] 3.2 一覧・詳細の代表画像表示を維持する
  - 植物一覧と詳細は代表画像URLがある場合に画像を表示し、ない場合は既存の代替表示を維持する。
  - 詳細画面では raw URL を植物本体の項目として表示しない。
  - 成長記録ギャラリー、写真並び替え、画像変換に関する UI は追加しない。
  - 完了時点で、既存の植物一覧・詳細体験は写真未登録でも表示でき、代表画像があれば補助情報として表示される。
  - _Depends: 2.2_
  - _Requirements: 2.2, 2.3, 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 6.4, 6.5, 7.4_
  - _Boundary: Plants UI types/forms_

- [ ] 4. 所有者分離と scope 境界の回帰テストを追加する
- [x] 4.1 植物 API の代表写真・所有者分離を検証する
  - 同じ植物に複数写真が紐づき、そのうち1枚だけが代表写真URLとして返ることを確認する。
  - 他 owner や他植物の写真が代表写真として扱われないことを確認する。
  - 写真未登録、代表写真なし、表示可能URLなしの植物が一覧・詳細で正常に取得できることを確認する。
  - 完了時点で、代表写真 read contract と owner separation の API test が通る。
  - _Depends: 2.2_
  - _Requirements: 1.1, 1.2, 2.1, 2.2, 2.3, 2.4, 2.5, 4.1, 4.2, 4.3, 4.4, 4.5, 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 7.1, 7.2, 7.3, 7.4_
  - _Boundary: Migration and verification, PlantRepository_

- [x] 4.2 写真 CRUD とストレージ scope が増えていないことを検証する
  - 画像アップロード、画像削除、外部ストレージ連携、写真CRUD、ギャラリー用 endpoint が追加されていないことを route surface で確認する。
  - owner 情報、内部写真参照、storage key がユーザー向けレスポンスに露出しないことを確認する。
  - 完了時点で、この spec が永続化構造と最小互換に限定されていることを test で検出できる。
  - _Depends: 2.2_
  - _Requirements: 4.5, 6.1, 6.2, 6.3, 6.4, 6.5_
  - _Boundary: Migration and verification, Plant schemas_

- [ ] 4.3 smoke verification に写真基盤の検証を組み込む
  - local SQLite と Turso の smoke path で、写真未設定の植物、複数写真、代表写真URL、他 owner 写真の混入なしを検証する。
  - ownerless な写真記録が通常 path で作られていないことを検証する。
  - 完了時点で、smoke script は写真基盤の代表的な owner scoped CRUD を検証して成功・失敗を判定できる。
  - _Depends: 2.2_
  - _Requirements: 1.1, 1.2, 2.1, 2.2, 2.3, 4.1, 4.2, 4.3, 4.4, 5.1, 5.2, 5.3, 5.6, 7.1, 7.2, 7.3, 7.4, 7.5_
  - _Boundary: Migration and verification_

- [ ] 5. 統合検証を完了する
- [ ] 5.1 Backend test suite と migration smoke を通す
  - Backend tests を実行し、migration、植物 API、認証境界、水やり関連 summary の回帰がないことを確認する。
  - local SQLite smoke を実行し、写真基盤を含む owner scoped CRUD が通ることを確認する。
  - 完了時点で、Backend の主要検証コマンドが成功し、写真基盤の失敗が残っていない。
  - _Depends: 4.3_
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_
  - _Boundary: Migration and verification_

- [ ] 5.2 Frontend build を通して型境界を確認する
  - Frontend build を実行し、画像URLを作成入力から外した型変更が全画面で整合していることを確認する。
  - 完了時点で、TypeScript build が成功し、植物登録・一覧・詳細の型エラーが残っていない。
  - _Depends: 3.2_
  - _Requirements: 3.1, 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 6.4, 7.4, 7.5_
  - _Boundary: Plants UI types/forms_
