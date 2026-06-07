# Brief: backend-warmup-endpoint

## Problem
Green Mate の利用者がアクセスする時間帯に Render 上のバックエンドがスリープしていると、初回アクセス時にコールドスタート待ちが発生する。これはサービスの主要機能の問題ではないが、利用開始時の体感速度を悪化させる運用上の課題である。

## Current State
現在のバックエンドは FastAPI で構成され、植物記録や認証などの業務 API は router / service / repository の layered architecture に従っている。一方で、Render のスリープ対策として外部から定期的に安全に呼び出せる warmup 専用 endpoint はまだ用意されていない。

## Desired Outcome
cron-job.org から公開 URL の warmup endpoint へ定期的にリクエストできる。バックエンドは固定ヘッダー `X-Warmup-Key` を検証し、正しい値の場合だけ warmup リクエストとして受け付ける。日本時間 `Asia/Tokyo` で 2:00 から 5:00 以外の時間帯に 10 分ごとに実行する運用設定を明文化する。

## Approach
バックエンドに warmup 専用の軽量 endpoint を追加し、環境変数で設定した固定キーと `X-Warmup-Key` ヘッダーを比較する。endpoint は通常の業務処理、DB アクセス、ユーザー認証、外部 API 呼び出しを行わず、アプリケーションプロセスが応答可能であることだけを返す。スケジューリングは Cloudflare Workers Cron Trigger ではなく cron-job.org に寄せ、実行履歴や失敗通知は cron-job.org 側で扱う。

この方針は補助的な運用機能としてシンプルで、ホスティング先変更時も URL と cron-job.org 設定の更新で対応しやすい。

## Scope
- **In**: FastAPI の warmup 専用 endpoint、`X-Warmup-Key` ヘッダー検証、固定キーの環境変数設定、認証失敗時に処理しない応答、DB に触れない軽量レスポンス、cron-job.org の実行時間帯とヘッダー設定の運用メモ、最小限の endpoint テスト
- **Out**: Cloudflare Workers Cron Trigger、複雑なリトライ制御、複数サービスによる二重実行、フォールバック経路、専用監視基盤、DB 死活確認、通常業務処理、ユーザー向け画面、warmup のための大規模なテスト実装

## Boundary Candidates
- バックエンド HTTP 境界: warmup 専用 router が公開 URL とヘッダー検証を担当する。
- 設定境界: 固定キーは `backend/.env` などの環境変数で扱い、spec や steering に実値を記載しない。
- 運用境界: 実行スケジュール、タイムゾーン、失敗通知、実行履歴は cron-job.org 側の設定として扱う。

## Out of Boundary
- warmup endpoint は植物、写真、水やり、認証済みユーザーなどの domain data を読み書きしない。
- warmup endpoint は DB の死活監視や migration 検証を行わない。
- cron-job.org 以外のスケジューラーや二重化はこの spec では扱わない。
- warmup の一時失敗をサービス障害として扱うための専用監視や自動復旧は導入しない。

## Upstream / Downstream
- **Upstream**: 既存の FastAPI アプリケーション構成、`app.core.config.Settings` による環境変数管理、Render にデプロイされるバックエンド公開 URL。
- **Downstream**: cron-job.org のジョブ設定、Render 上の環境変数設定、将来ホスティング先を変更した場合の warmup URL 更新。

## Existing Spec Touchpoints
- **Extends**: なし
- **Adjacent**: `auth-authorization-foundation` は通常のユーザー認証・認可の責務を持つが、この endpoint は固定ヘッダーによる運用用トークン検証のみを扱い、ユーザー所有データの認可境界には入らない。

## Constraints
Backend は FastAPI / Pydantic Settings の既存構成に従う。secret 値は環境変数で管理し、repository、database session、Clerk 認証 dependency は使わない。cron-job.org 側のタイムゾーンは `Asia/Tokyo` とし、日本時間 2:00 から 5:00 は実行しない。それ以外の時間帯は 10 分ごとに warmup endpoint へリクエストする。
