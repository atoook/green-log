# Brief: plant-profile-editing

## Problem
観葉植物初心者は、植物を登録した後に植物名、種類、メモ、水やり間隔、迎えた日などを直したくなる。現在は植物詳細で基本情報を見られるが、登録後に情報を更新する導線がないため、入力ミスの修正や暮らしに合わせた水やり間隔の調整ができない。

## Current State
`plant-registration` spec は植物の新規登録、一覧、詳細表示を扱っている。Frontend には `/plants/:plantId` の詳細画面、`PlantDetail`、`PlantForm`、`usePlantDetail`、`createPlantsApiClient` があり、Backend には `GET /plants`、`POST /plants`、`GET /plants/{plant_id}` がある。植物更新 API、更新用 schema、更新用 repository/service 処理、詳細画面からの編集状態はまだ存在しない。

水やり機能は植物の `wateringCycleDays` と現在の植物名を参照するため、植物基本情報の更新結果は詳細画面、水やり状態、直近のお世話、ヒートマップなどの表示に反映される必要がある。ただし、水やり記録そのものの編集や削除は本 spec の責務ではない。

## Desired Outcome
認証済みユーザーは、自分の植物詳細画面から植物情報を編集し、保存後に詳細画面へ戻って更新内容をすぐ確認できる。更新中、成功、失敗、入力エラーの状態が分かり、植物名必須、水やり間隔の正数、日付の妥当性などは登録時の検証と揃う。本人の植物だけを更新でき、他ユーザーの植物は存在を漏らさず更新できない。

## Approach
詳細画面内で「編集」状態に切り替えるインライン編集を第一候補にする。既存の詳細画面を植物管理の中心にする目的に合い、保存成功後に同じ画面上で即時反映しやすい。登録フォームの入力検証と型をできるだけ再利用しつつ、更新用 API client、composable、Backend の `PATCH /plants/{id}` を追加する。

別画面の編集フォームへ遷移する案も考えられるが、MVP では画面数と遷移状態が増える割に価値が小さい。項目数が増える、写真編集など独立したワークフローが必要になる、または編集 UI が詳細画面を圧迫する段階で再検討する。

## Scope
- **In**: 植物詳細画面の編集導線、編集状態への切り替え、植物名・種類・メモ・水やり間隔・迎えた日または登録日相当の日付・既存登録フォーム由来の保持項目の更新、更新 API、本人所有植物だけを更新する認可、保存中・成功・失敗・入力エラー状態、更新後の詳細表示への即時反映、登録時バリデーションとの整合
- **Out**: 水やり記録の編集・削除、画像ファイルアップロード、複数写真の成長ログ編集、植物種マスタ、植物辞典、育成ガイド、共有ユーザーによる共同編集、通知設定、厳格な業務アプリ風の履歴整合制御

## Boundary Candidates
- 詳細画面の表示責務と編集フォーム状態の責務を分ける
- API client と composable に更新処理と保存状態を集約し、presentation component は入力とイベントに集中する
- Backend は Router / Service / Repository の既存 layered architecture に沿って、HTTP mapping、domain validation、owner scoped persistence を分ける
- 水やり予定・履歴は更新後の植物基本情報を参照する downstream とし、水やり記録の日付そのものは変更しない

## Out of Boundary
- 過去の水やり実績日より迎えた日を後にできない、といった強い業務制約は初期仕様では入れない
- 水やり記録の整合性チェックは、警告や補助表示の候補として検討しても、保存を妨げる必須制御にはしない
- 「種類」は既存 schema に項目がない場合、既存登録フォームが保持していない新規ドメイン項目として別途設計判断する。既存 DB にない列を追加する場合は migration と一覧・詳細表示への影響を明示する
- 画像 URL やカバー写真の扱いは、既存登録フォームや写真基盤 spec の実装状態に合わせる。画像アップロードは扱わない

## Upstream / Downstream
- **Upstream**: `plant-registration` の植物基本情報、登録時バリデーション、一覧・詳細表示、`auth-authorization-foundation` の CurrentUser と owner scope、`plant-photo-schema-foundation` のカバー画像参照
- **Downstream**: `plant-watering-care` の水やり周期、植物名、詳細画面の水やり状態表示、直近のお世話予定、ヒートマップ上の現在名表示、将来の成長写真ログや通知設定

## Existing Spec Touchpoints
- **Extends**: なし。新規 spec として植物基本情報の登録後更新を扱う
- **Adjacent**: `plant-registration` は新規登録と表示の基礎、`plant-watering-care` は更新後の水やり周期・植物名を参照する隣接領域、`auth-authorization-foundation` は本人所有データ更新の認可基盤

## Constraints
Frontend は Vue 3、Vite、TypeScript、Tailwind CSS、Vue Router の既存構成に従う。API 通信は `src/api/` の typed client と authenticated API client 経由にし、component から直接 `fetch` しない。Backend は FastAPI、Pydantic/SQLModel、Repository / Service / Router の層を守る。API JSON は camelCase、Python 内部は snake_case とする。ユーザー所有データは request body の owner 情報を信用せず、認証コンテキストから internal owner id を決定する。未ログインは 401、無効ユーザーは 403、他ユーザー所有植物の更新は存在を漏らさない 404 として扱う。
