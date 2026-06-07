# Requirements Document

## Project Description (Input)
Green Mate の利用者がアクセスする時間帯に Render 上のバックエンドがスリープしていると、初回アクセス時にコールドスタート待ちが発生する。これはサービスの主要機能の問題ではないが、利用開始時の体感速度を悪化させる運用上の課題である。

現在のバックエンドは FastAPI で構成され、植物記録や認証などの業務 API は router / service / repository の layered architecture に従っている。一方で、Render のスリープ対策として外部から定期的に安全に呼び出せる warmup 専用 endpoint はまだ用意されていない。

cron-job.org から公開 URL の warmup endpoint へ定期的にリクエストできるようにする。バックエンドは固定ヘッダー `X-Warmup-Key` を検証し、正しい値の場合だけ warmup リクエストとして受け付ける。日本時間 `Asia/Tokyo` で 2:00 から 5:00 以外の時間帯に 10 分ごとに実行する運用設定を明文化する。

## Requirements
<!-- Will be generated in /kiro-spec-requirements phase -->
