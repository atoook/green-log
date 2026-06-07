# Implementation Plan

- [x] 1. Warmup 用 runtime secret 設定を追加する
  - `WARMUP_KEY` を runtime 設定として読み取れるようにし、secret 値が通常の設定表示に露出しない状態にする。
  - `.env.example` に `WARMUP_KEY=` を追加し、実値を repository に残さず設定項目だけを確認できるようにする。
  - 完了時には backend 設定から warmup 固定キーを取得でき、未設定時は `None` または空として判定できる。
  - _Requirements: 1.1, 2.1, 2.2, 2.4, 4.5_
  - _Boundary: Runtime Settings_

- [x] 2. Warmup endpoint と運用成果物を実装する
- [x] 2.1 固定キーで保護された warmup endpoint を追加する
  - 正しい `X-Warmup-Key` が付いた request だけを warmup として受け付ける。
  - header 欠落、不一致、runtime secret 未設定の場合は成功扱いにせず、secret 値や検証詳細を応答に含めない。
  - 成功応答は呼び出し元が成功判定できる固定 JSON に留め、ユーザー所有データや認証情報を返さない。
  - 完了時には `GET /warmup` が DB、Clerk current user、domain service、repository に依存せず応答できる。
  - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 2.3, 2.4, 3.1, 3.2, 3.3_
  - _Boundary: Warmup Router_

- [x] 2.2 (P) cron-job.org の warmup 運用手順を追加する
  - cron-job.org を実行元にし、Cloudflare Workers Cron Trigger を使わないことを明記する。
  - timezone は `Asia/Tokyo`、実行時間は 2:00 から 5:00 を除外し、それ以外は 10 分ごとに実行する設定として記載する。
  - request header に `X-Warmup-Key` を設定し、固定キーと URL、スケジュール、timezone を最初に確認するトラブルシュート手順を記載する。
  - 完了時には運用者が Render の backend URL と `WARMUP_KEY` を使って cron-job.org のジョブを手動設定できる。
  - _Requirements: 3.4, 4.1, 4.2, 4.3, 4.4, 4.5, 5.1, 5.2, 5.3_
  - _Boundary: Operations Documentation_

- [x] 3. Backend 統合とテストを追加する
- [x] 3.1 Warmup router をアプリケーションへ組み込む
  - warmup endpoint を既存 backend application に登録し、公開 URL から呼び出せる API として有効にする。
  - CORS、frontend API client、認証済み domain API の挙動を変更しない。
  - 完了時には `GET /warmup` が application routing 上で到達可能になり、既存 domain endpoints の owner scope 境界は変更されない。
  - _Depends: 2.1_
  - _Requirements: 1.1, 1.2, 3.1, 3.2, 3.3_
  - _Boundary: Warmup Router, Application Wiring_

- [x] 3.2 Warmup API と runtime config のテストを追加する
  - 正しい header 付き request の成功、header 欠落、不一致、runtime secret 未設定の失敗を検証する。
  - warmup response に secret、ユーザー所有データ、認証情報が含まれないことを検証する。
  - auth dependency override や DB fixture に依存せず warmup endpoint を呼び出せることを検証する。
  - runtime config が `WARMUP_KEY` を secret として読み取り、`.env.example` に設定項目があることを検証する。
  - 完了時には warmup の成功・失敗・設定・非依存性が backend tests で再現可能になる。
  - _Depends: 3.1_
  - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 2.3, 2.4, 3.1, 3.2, 3.3, 4.5_
  - _Boundary: Backend Tests_

- [x] 4. Feature 全体の検証を完了する
  - backend test suite を実行し、warmup 追加後も既存 API と runtime config の回帰がないことを確認する。
  - 運用手順が cron-job.org、`Asia/Tokyo`、2:00-5:00 除外、10 分間隔、`X-Warmup-Key`、設定確認手順、非導入項目を満たすことを確認する。
  - 完了時には実装、テスト、運用手順が design の File Structure Plan と Requirements Traceability を満たしている。
  - _Depends: 2.2, 3.2_
  - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 2.3, 2.4, 3.1, 3.2, 3.3, 3.4, 4.1, 4.2, 4.3, 4.4, 4.5, 5.1, 5.2, 5.3_
  - _Boundary: Validation_
