# Implementation Gap Analysis: plant-image-management

作成日: 2026-06-06

## 前提
- `requirements.md` は生成済みだが、`approvals.requirements.approved` はまだ `false`。
- 本分析は設計前の情報整理であり、最終的な API 形状、保存方式、UI 分割は design phase で決定する。
- 外部依存の追加は現時点では確定していない。既存 stack は FastAPI / SQLModel / Alembic / Vue 3 / TypeScript / Tailwind CSS。

## Current State Investigation

### Backend
- 既存の植物 API は `GET /plants`, `POST /plants`, `GET /plants/{plant_id}`, `PATCH /plants/{plant_id}` のみ。
- `Plant` には `cover_photo_id` が存在し、`PlantPhoto` には `owner_user_id`, `plant_id`, `image_url`, `storage_key`, `taken_date`, `comment`, `created_at`, `updated_at` が存在する。
- `PlantRepository.list_with_cover_image()` と `get_by_id_with_cover_image()` は、同一 owner かつ同一 plant の `PlantPhoto.image_url` だけを代表画像 URL として返す。
- `PlantService` は一覧・詳細の `image_url` 互換を提供しているが、写真の作成、一覧、削除、代表画像設定は提供していない。
- `User` には上限なしユーザーを示す列がない。
- Alembic migration は `0004_create_plant_photos.py` まで存在し、写真基盤は DB 上にある。
- `backend/tests/test_backend_integration_contract.py` には「photo/upload/gallery/storage を公開しない」前段 spec 用の契約テストがあり、本 spec 実装時には意図的な更新が必要。
- `backend/app/scripts/verify_turso_crud.py` は写真 record と代表画像の smoke 検証を直接 DB 操作で行っている。写真 API 実装後は smoke の拡張候補になる。

### Frontend
- `Plant.imageUrl` は型に存在し、`PlantList.vue` と `PlantDetail.vue` は代表画像表示と空状態に対応済み。
- `src/api/plants.ts` は植物 CRUD の typed client のみ。写真 API client は未作成。
- `usePlantDetail.ts` は植物詳細取得と基本情報更新のみ。画像ギャラリー状態、追加、削除、代表画像設定は未実装。
- `PlantDetailPage.vue` は植物詳細、編集、水やり状態・履歴を composition している。画像ギャラリーを追加する integration point になる。
- API client 共通部 `createAuthenticatedApiClient()` は既定で `Content-Type: application/json` を付与する。実ファイル upload を `FormData` で行う場合は、ヘッダー制御または別 request helper の検討が必要。
- frontend tests は `node:test` による static/source-level contract が多く、API client が直接 `fetch` しないことや owner field 非公開を検証している。

### Existing Patterns
- Backend は Router / Service / Repository / Model / Schema の分離を守る。
- Service は domain validation を担当し、Router が HTTP status へ変換する。
- owner scope は `CurrentUser.id` を service/repository に渡し、他 owner の resource は 404 相当で存在を漏らさない。
- Frontend は page/composable/API client/type/component を分け、presentation component は Clerk token や fetch を直接扱わない。
- テストは backend pytest、frontend node:test、build/smoke verification で固定する。

## Requirement-to-Asset Map

| Requirement | Existing assets | Gap |
| --- | --- | --- |
| 1. 植物詳細からの画像追加 | `PlantPhoto` model, `plant_photos` table, owner-scoped plant lookup | **Missing**: 写真作成 API/service/repository/schema、upload request handling、追加後のギャラリー反映、失敗時 UI |
| 2. 植物ごとの時系列ギャラリー | `PlantPhoto.created_at`, `taken_date` indexes | **Missing**: 写真一覧 API、時系列 sort rule、frontend gallery type/composable/component、画像読み込み失敗 UI |
| 3. 画像枚数上限の表示と制御 | owner-scoped user/plant foundation | **Missing**: 上限定数、写真 count query、上限なし user flag、migration、API response の quota/status、上限エラー表現 |
| 4. 代表画像の設定と一覧表示 | `Plant.cover_photo_id`, cover URL join, `Plant.imageUrl`, `PlantList.vue` thumbnail | **Partial**: 一覧表示は既存。**Missing**: ギャラリー内からの代表設定 API/UI、同一 plant photo 検証、詳細と一覧の再同期 |
| 5. 画像削除と代表画像削除時の扱い | `PlantPhoto` table, nullable `cover_photo_id` | **Missing**: 写真削除 API/service/repository、代表画像削除時の解除処理、確認 dialog UI、削除失敗時 UI |
| 6. ユーザー所有データとしての画像分離 | auth dependency, owner-scoped plant pattern, `PlantPhoto.owner_user_id` | **Partial**: 基盤はある。**Missing**: 写真 API 全体での owner-scoped lookup と owner field 非公開 test |
| 7. 隣接機能との境界 | 前段 spec の out-of-scope tests | **Constraint**: 既存契約テストを本 spec の scope に合わせて更新し、storage/internal fields を露出しない境界は維持する必要 |
| 8. 変更後の検証可能性 | backend pytest, frontend node:test, smoke script | **Missing**: 写真 API/service/repository tests、frontend API/composable/component tests、owner separation tests、quota tests |

## Key Gaps And Constraints

### Missing Capabilities
- 写真操作専用の backend boundary。
  - 作成、一覧、削除、代表画像設定、枚数上限確認が必要。
  - `PlantRepository` に寄せるか `PlantPhotoRepository` を新設するかは design decision。
- 上限なしユーザー判定。
  - `users` table に boolean 相当の列追加が必要。
  - SQLite/libSQL の boolean round-trip 方針に合わせた migration/test が必要。
- upload/storage handling。
  - 現在は `image_url` / `storage_key` の格納先だけがある。
  - 画像ファイルをどこへ保存し、どう URL 化するかはまだ未決定。
- frontend gallery state。
  - 植物詳細画面内で、植物基本情報、水やり情報、画像ギャラリーの loading/error/success を分ける必要がある。
- representative image synchronization。
  - 代表画像設定後に `plant.imageUrl` と一覧側表示をどう更新するか設計が必要。

### Constraints
- owner id、storage key、cover photo id、内部 user id は user-facing response に露出しない方針。
- 他 owner の plant/photo は 404 相当で存在を漏らさない必要。
- 植物登録は画像なしで継続できる必要。
- 画像管理専用画面、他植物への移動、プラン UI、画像編集、サムネイル生成、タイムラプスは scope 外。
- 既存 `createAuthenticatedApiClient()` は JSON request を前提にしているため、multipart upload を採る場合は既存 client の拡張影響がある。

### Research Needed For Design Phase
- 画像ファイル保存方式。
  - ローカルファイル保存、外部 object storage、または一時的な URL 登録方式のうち、MVP と運用制約に合うものを比較する必要がある。
- FastAPI で multipart upload を採る場合の追加依存。
  - 現在 `python-multipart` は `backend/requirements.txt` にないため、`UploadFile` 利用時は依存追加と test/build 影響を確認する必要がある。
- ファイルサイズ、MIME type、拡張子、保存失敗時の rollback 方針。
  - requirements には「有効な画像」としかないため、design で validation policy を具体化する必要がある。
- 代表画像削除時の transaction boundary。
  - 写真削除と `cover_photo_id` 解除を同一 transaction で扱うか、storage 削除失敗との整合をどう取るか検討する必要がある。

## Implementation Approach Options

### Option A: 既存 Plant boundary を拡張する
`PlantRepository`, `PlantService`, `plants.py`, `plants.ts`, `usePlantDetail.ts` に写真操作を追加し、route も `/plants/{plant_id}/photos` など plant 配下に置く。

**Pros**
- 既存の owner-scoped plant lookup と代表画像互換をそのまま使いやすい。
- route が植物詳細体験に沿い、他植物への紐づけ変更を自然に排除できる。
- 初期実装のファイル数が少ない。

**Cons**
- `PlantService` と `PlantRepository` が植物基本情報、水やり連携、写真操作まで抱えて肥大化しやすい。
- 写真操作の test が plant CRUD test と混ざり、責務境界が見えにくくなる。
- upload/storage policy が入ると既存植物 CRUD の認知負荷が上がる。

**Fit**
- 小さな MVP なら可能。ただし今回の scope は追加・一覧・代表設定・削除・quota・upload まであるため、長期的には分離した方が扱いやすい。

### Option B: 写真専用 boundary を新設する
`PlantPhotoRepository`, `PlantPhotoService`, `PlantPhoto` schemas, `plant_photos` router/API client/composable/component を新設し、既存 plant boundary とは代表画像 URL 互換部分だけで連携する。

**Pros**
- 写真 CRUD、quota、代表画像設定、削除 transaction を独立して test しやすい。
- 既存植物基本情報や水やりの code path への影響を抑えられる。
- 将来の成長記録強化やタイムラプスに拡張しやすい。

**Cons**
- 新規ファイルと interface が増える。
- 代表画像設定では `plants.cover_photo_id` を更新するため、Plant との coordination が必要。
- 詳細画面の state orchestration は複数 composable を組み合わせる形になり、設計の一貫性が必要。

**Fit**
- requirements の幅と将来拡張を考えると最も自然。route は plant 配下に置きつつ、内部 service/repository は写真専用に分ける案が有力。

### Option C: Hybrid approach
backend は `PlantPhotoService/Repository` を新設し、代表画像 URL 互換は既存 `PlantService/Repository` を維持する。frontend は `PlantImageGallery` と `usePlantPhotos` を新設し、`PlantDetailPage.vue` に composition する。既存 `PlantDetail.vue` と `PlantList.vue` は代表画像表示の軽微な調整に留める。

**Pros**
- 既存の plant list/detail 互換を壊さず、写真操作の責務を分けられる。
- `PlantDetailPage.vue` の既存 pattern（水やり composable と表示 surface を分ける）に合う。
- test も API/client/composable/component 単位で追加しやすい。

**Cons**
- 代表画像設定後に `plant.imageUrl` を更新する coordination が必要。
- upload request helper と JSON API client の扱いを整理する必要がある。
- smoke verification や backend integration contract の更新範囲が複数にまたがる。

**Fit**
- 推奨候補。実装量は中程度だが、責務分離と既存互換のバランスがよい。

## Complexity And Risk

- **Effort**: M-L
  - DB migration、backend 写真操作、quota、upload/storage、frontend gallery、代表画像同期、複数 test 追加が必要。保存方式を URL 登録に限定できれば M、実ファイル upload と永続 storage まで含めると L。
- **Risk**: Medium
  - owner scope と代表画像整合性は既存 pattern で対応可能。一方、upload/storage 方式、multipart 依存、削除 transaction、quota user flag migration は設計判断が必要。

## Recommendations For Design Phase

### Preferred Direction
Hybrid approach を中心に design を作る。写真操作は専用 service/repository/API client/composable/component に分け、植物一覧・詳細の `imageUrl` 互換は既存 plant read path を活かす。

### Key Design Decisions
- 写真 API route を plant 配下に置くか、写真 resource として独立 route に置くか。
  - requirements 上は「現在表示中の植物に限定」なので、plant 配下 route が自然。
- upload 方式。
  - 実ファイル upload を scope-in するなら `FormData` / multipart と保存先を決める必要がある。
  - MVP として URL 登録や仮 storage を採る場合は、requirements の「画像追加」との整合を明示する必要がある。
- user quota field。
  - `users` に上限なし boolean を追加し、API response には露出せず、写真 quota response だけに user-facing な `limit` の有無を返す案が考えられる。
- representative image update。
  - 写真削除と `cover_photo_id` 解除、代表画像設定時の同一 plant/owner 検証を transactionally 扱う必要がある。
- frontend state split。
  - 植物 detail error、水やり error、画像 gallery error を混ぜない。
  - 画像追加/削除/代表設定の optimistic update 可否は design で決める。

### Test Additions To Plan
- Backend:
  - 写真一覧が owner/plant scoped で時系列になること。
  - 一般ユーザー5枚上限と上限なしユーザーの挙動。
  - 他 owner plant/photo 操作が 404 相当になること。
  - 代表画像設定が同一 owner/plant photo だけ許可されること。
  - 代表画像削除で `cover_photo_id` が null になること。
  - API response に owner/internal/storage fields が露出しないこと。
- Frontend:
  - 写真 API client が authenticated client を通ること。
  - `usePlantPhotos` が load/add/delete/set-cover の state と error を分離すること。
  - `PlantImageGallery` が画像なし、quota、上限なし、削除確認、代表画像削除 warning を表示すること。
  - `PlantDetailPage.vue` が既存 detail/watering と画像 error surface を混ぜないこと。
- Smoke / contract:
  - 前段の「photo CRUD を公開しない」contract を本 spec の route surface に合わせて更新すること。
  - SQLite/Turso smoke で写真 API または service path の owner separation と代表画像を検証すること。

---

# Design Input: 画像ストレージ方針

作成日: 2026-06-06

## 採用方針
- 画像ストレージは Amazon S3 を利用する。
- 初期実装では public read で運用する。
- 将来的に署名付き URL 方式へ移行できる構成にする。
- DB には公開 URL ではなく object key を保存する。
- 画像本体は DB に保存しない。

## 環境変数
```env
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=ap-northeast-1
S3_BUCKET_NAME=...
```

## S3 設定
- リージョンは `ap-northeast-1` を利用する。
- Object Ownership は `ACLs disabled / Bucket owner enforced` とする。
- 初期実装では public read を許可する。
- Bucket Policy で `s3:GetObject` を許可する。
- 専用 IAM ユーザーのアクセスキーを利用する。

## Object Key 方針
- DB には公開 URL ではなく object key のみを保存する。
- object key は推測されにくい構造にする。
- `photo_id` は UUID を利用する。
- `plant_photos.id` は今回対応の中で UUID に変更する。既存 `plant_photos` テーブルにはデータが入っていない前提のため、既存行の互換性や ID 移行は考慮しない。
- URL 生成方法と保存データを分離する。
- object key に user id は含めない。
- 例:

```text
plants/{plant_id}/{photo_id}.{ext}
```

## ストレージ抽象化方針
- アプリケーションは公開 URL ではなく object key を管理する。
- 表示用 URL は object key から動的に生成する。
- ストレージ固有の URL 形式を DB へ保存しない。
- 将来的な S3 から R2 などへのストレージ移行の影響を最小化する。
- 以下の移行を DB 変更なしで実施できる構成を目指す。
  - S3 public URL から署名付き URL
  - S3 から Cloudflare R2
  - S3/R2 から CDN 配信

## URL 生成方針
- 初期実装では object key から public URL を組み立てて利用する。
- URL 形式:

```text
https://{bucket}.s3.{region}.amazonaws.com/{object_key}
```

- 将来的には同じ object key を利用して署名付き URL を発行する方式へ移行可能にする。

## アップロード方針
- アップロードは FastAPI 経由で実施する。
- ブラウザから直接 S3 へはアップロードしない。
- ファイルサイズ、拡張子、認可チェックは API 側で行う。
- 一般ユーザーの枚数制限も API 側で検証する。

## API 設計方針
アップロード処理と画像メタ情報登録処理は分離する。

### アップロード API
```text
POST /photos/upload
```

役割:
- 画像ファイルを受け取る。
- S3 へアップロードする。
- object key を返却する。

### 画像登録 API
```text
POST /plants/{plant_id}/photos
```

役割:
- object key を植物に紐づける。
- 撮影日やコメントなどのメタ情報を保存する。
- 枚数制限を検証する。

## 削除方針
- DB レコード削除時は S3 object も削除する。
- DB と S3 の整合性を維持する。

## 将来拡張
- S3 public URL から署名付き URL への移行。
- CloudFront 配信。
- Cloudflare R2 への移行。
- ブラウザからの直接アップロード。
- 画像圧縮・サムネイル生成。

## 既存実装との具体的な差分
- 現在の `PlantPhoto` は `image_url` と `storage_key` を持つが、本方針では DB の canonical data を object key に寄せる。
- 現在の `PlantPhoto.id` は integer primary key だが、本方針では UUID primary key に変更する。既存データ移行は不要。
- 既存の一覧・詳細 API は `imageUrl` を返しているため、保存値としての object key と表示値としての URL を分ける変換層が必要。
- `PlantRepository.list_with_cover_image()` / `get_by_id_with_cover_image()` は現状 `PlantPhoto.image_url` を join して返している。design では `storage_key` から表示 URL を生成する責務の置き場所を決める必要がある。
- backend dependencies には S3 SDK と multipart upload に必要な依存がまだない。候補として AWS SDK と `python-multipart` の追加影響を design phase で確認する。
- frontend の authenticated API client は JSON 前提で `Content-Type: application/json` を付与する。`POST /photos/upload` は `FormData` を使う想定のため、upload 用 request path では Content-Type をブラウザに委ねられるようにする必要がある。

## 設計時に解決すべき論点
- `POST /photos/upload` が `plants/{plant_id}/{photo_id}.{ext}` 形式の object key を作るには、upload 時点で `plant_id` を受け取る必要がある。API path を `POST /plants/{plant_id}/photos/upload` に寄せるか、`POST /photos/upload` の request field に `plantId` を含めるか、または一時 object key を発行して登録時に確定 key へ移動するかを決める。
- アップロードと画像登録を分離すると、S3 upload 成功後に DB 登録が失敗した場合の orphan object が発生し得る。即時削除、期限付き cleanup、または upload API と登録 API の統合など、整合性方針を design で決める。
- DB レコード削除と S3 object 削除は単一 transaction にできない。S3 削除成功後に DB 削除するか、DB 削除後に S3 削除するか、失敗時の retry / compensating action を定義する必要がある。
- object key に user id を含めない方針では、owner 分離は DB と API 認可で担保する。public read 運用中は object key の推測困難性が重要になるため、UUID の採用と key 生成の一貫性を test で固定する必要がある。
- `plant_photos.id` を UUID にすることで object key と DB photo id を一致させやすくなる。一方で、`plants.cover_photo_id` も同じ UUID 型へ合わせる必要があるため、model、schema、migration、既存 repository test の更新範囲に含める。
- 初期 public read と将来の署名付き URL 移行を両立するため、frontend は URL の永続性を前提にせず、API response の表示用 URL を利用する形にする。
- `storage_key` を user-facing response に含めるかは慎重に扱う。現行方針では内部 field 非公開を維持し、frontend には表示用 URL と写真 ID、撮影日、コメント、代表画像状態だけを返す案が安全。
