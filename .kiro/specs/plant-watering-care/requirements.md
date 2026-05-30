# Requirements Document

## Project Description (Input)
観葉植物初心者は、植物ごとの水やり周期を登録できても、最後に水をあげた日や今日水やりが必要な植物をすぐ把握できない。結果として、水やり忘れや、短い間隔で何度も水をあげてしまう不安が残る。

現在の `plant-registration` は植物個体の登録、一覧、詳細、水やり周期の保存を扱っている。一方で、水やり完了・スキップ・履歴、次回水やり予定日の計算、今日のお世話は明示的に範囲外である。既存の Plant はユーザー所有データとして owner scope を持ち、`watering_cycle_days` を保持しているため、水やり記録も認証済みユーザーの private data として同じ owner 分離を守る必要がある。

この spec では、ユーザーが植物ごとに水やりしたことを記録でき、Green Mate が最新の水やり日時、次回水やり予定日、今日水やりが必要な植物を表示できる状態にする。MVP では `WateringRecord` を履歴の source of truth とし、`Plant.last_watered_at` は最新表示・Todo 判定用の集計キャッシュとして扱う。`next_watering_date` は保存せず、`last_watered_at` と `watering_cycle_days` から Service 層で動的に算出する。

## Requirements
<!-- Will be generated in /kiro-spec-requirements phase -->

