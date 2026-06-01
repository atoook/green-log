# Requirements Document

## Project Description (Input)
観葉植物初心者は、植物を登録した後に植物名、種類、メモ、水やり間隔、迎えた日などを直したくなる。現在は植物詳細で基本情報を見られるが、登録後に情報を更新する導線がないため、入力ミスの修正や暮らしに合わせた水やり間隔の調整ができない。

現在の `plant-registration` spec は植物の新規登録、一覧、詳細表示を扱っている。Frontend には `/plants/:plantId` の詳細画面、`PlantDetail`、`PlantForm`、`usePlantDetail`、`createPlantsApiClient` があり、Backend には `GET /plants`、`POST /plants`、`GET /plants/{plant_id}` がある。植物更新 API、更新用 schema、更新用 repository/service 処理、詳細画面からの編集状態はまだ存在しない。

この spec では、認証済みユーザーが自分の植物詳細画面から植物情報を編集し、保存後に詳細画面へ戻って更新内容をすぐ確認できる状態を目指す。更新中、成功、失敗、入力エラーの状態が分かり、植物名必須、水やり間隔の正数、日付の妥当性などは登録時の検証と揃える。本人の植物だけを更新でき、他ユーザーの植物は存在を漏らさず更新できないようにする。

詳細画面内で「編集」状態に切り替えるインライン編集を第一候補にする。既存の詳細画面を植物管理の中心にする目的に合い、保存成功後に同じ画面上で即時反映しやすい。登録フォームの入力検証と型をできるだけ再利用しつつ、更新用 API client、composable、Backend の `PATCH /plants/{id}` を追加する。

## Requirements
<!-- Will be generated in /kiro-spec-requirements phase -->
