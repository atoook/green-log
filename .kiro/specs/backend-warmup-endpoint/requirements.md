# Requirements Document

## Introduction

Green Mate の利用者がアクセスする時間帯に Render 上のバックエンドがスリープしていると、初回アクセス時にコールドスタート待ちが発生する。これはサービスの主要機能の問題ではないが、利用開始時の体感速度を悪化させる運用上の課題である。

この仕様では、cron-job.org から公開 URL の warmup endpoint へ定期的にリクエストできるようにする。Green Mate API は固定ヘッダー `X-Warmup-Key` を検証し、正しい値の場合だけ warmup リクエストとして受け付ける。日本時間 `Asia/Tokyo` で 2:00 から 5:00 以外の時間帯に 10 分ごとに実行する運用設定を明文化する。

## Boundary Context

- **In scope**: warmup 専用 endpoint、固定ヘッダーによる受け付け可否、認証失敗時の拒否、業務データに触れない応答、cron-job.org の運用条件の明文化。
- **Out of scope**: Cloudflare Workers Cron Trigger、複雑なリトライ制御、複数サービスによる二重実行、フォールバック経路、専用監視基盤、データベース死活確認、通常業務処理、ユーザー向け画面。
- **Adjacent expectations**: ユーザー所有データの通常 API は既存の認証・認可境界に従う。この warmup endpoint は公開 URL だが、ユーザー所有データを返さず、固定ヘッダーの検証だけを運用上の受け付け条件にする。

## Requirements

### Requirement 1: Warmup リクエストの受け付け
**Objective:** As an 運用者, I want 外部 cron から backend の warmup を実行できる, so that 利用想定時間帯の初回アクセス時にコールドスタートが起きにくくなる

#### Acceptance Criteria
1. When cron-job.org が正しい `X-Warmup-Key` ヘッダーを付けて warmup endpoint へリクエストする, the Green Mate API shall warmup リクエストとして受け付ける
2. When warmup リクエストが受け付けられる, the Green Mate API shall 呼び出し元が成功として判定できる応答を返す
3. The Green Mate API shall warmup 応答でユーザー所有データ、植物記録、写真、水やり記録、認証情報を返さない

### Requirement 2: 固定トークンによる保護
**Objective:** As an 運用者, I want 公開 URL の warmup endpoint を固定トークンで保護できる, so that 第三者の任意リクエストを warmup として受け付けない

#### Acceptance Criteria
1. When warmup endpoint へのリクエストに `X-Warmup-Key` ヘッダーがない, the Green Mate API shall warmup リクエストとして受け付けない
2. When warmup endpoint へのリクエストに誤った `X-Warmup-Key` ヘッダーが付いている, the Green Mate API shall warmup リクエストとして受け付けない
3. If warmup 認証に失敗する, then the Green Mate API shall 業務処理を実行しない
4. If warmup 認証に失敗する, then the Green Mate API shall 期待されるトークン値や検証の内部情報を応答に含めない

### Requirement 3: 業務処理と永続化データからの分離
**Objective:** As an 開発者, I want warmup が通常の業務処理から分離されている, so that スリープ対策がサービス機能やユーザーデータに影響しない

#### Acceptance Criteria
1. When warmup endpoint が呼び出される, the Green Mate API shall 植物、写真、水やり、ユーザーなどの業務データを作成、更新、削除しない
2. When warmup endpoint が呼び出される, the Green Mate API shall データベースの死活確認を目的とした処理を行わない
3. When warmup endpoint が呼び出される, the Green Mate API shall ユーザー認証済み API と同じ所有者分離の対象データを読み出さない
4. The Green Mate API shall warmup endpoint をサービス主要機能の成功条件として扱わない

### Requirement 4: cron-job.org による実行スケジュール
**Objective:** As an 運用者, I want cron-job.org の設定条件を明確にできる, so that Cloudflare Workers を使わずに利用想定時間帯だけ warmup を実行できる

#### Acceptance Criteria
1. The operational documentation shall cron-job.org を warmup 実行元として指定する
2. The operational documentation shall cron-job.org 側のタイムゾーンを `Asia/Tokyo` に設定することを示す
3. The operational documentation shall 日本時間 2:00 から 5:00 の間は warmup を実行しないことを示す
4. The operational documentation shall 日本時間 2:00 から 5:00 以外の時間帯は 10 分ごとに warmup endpoint へリクエストすることを示す
5. The operational documentation shall cron-job.org のリクエストに `X-Warmup-Key` ヘッダーを設定することを示す

### Requirement 5: 補助的な運用機能としての扱い
**Objective:** As an 運用者, I want warmup 失敗時の扱いをシンプルに保てる, so that 補助的なスリープ対策に過剰な運用負荷をかけない

#### Acceptance Criteria
1. If warmup が一時的に失敗する, then the operational documentation shall 想定される利用者影響を初回アクセス時のコールドスタート発生可能性として説明する
2. If warmup に問題が発生する, then the operational documentation shall まず URL、ヘッダー、固定トークン、スケジュール、タイムゾーンの設定確認を行うことを示す
3. The operational documentation shall warmup のために複雑なリトライ制御、二重実行、フォールバック経路、専用監視基盤を導入しないことを示す
