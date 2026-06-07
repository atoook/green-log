# Backend Warmup

Render 上の backend が利用想定時間帯にスリープしにくい状態を保つため、cron-job.org から warmup endpoint を定期実行する。

この仕組みは補助的なスリープ対策であり、サービス主要機能ではない。warmup が一時的に失敗した場合の利用者影響は、初回アクセス時にコールドスタートが発生する可能性がある程度に留める。

## Render

backend service の環境変数に以下を設定する。

```text
WARMUP_KEY=<任意の秘密値>
```

- 実値は repository、spec、docs に記載しない。
- cron-job.org の request header に設定する値と一致させる。

## cron-job.org

cron-job.org に backend warmup 用の cron job を 1 件作成する。

| 項目 | 設定 |
|------|------|
| URL | `https://<backend-host>/warmup` |
| Method | `GET` |
| Timezone | `Asia/Tokyo` |
| Minutes | `0,10,20,30,40,50` |
| Hours | `0,1,5-23` |
| Header | `X-Warmup-Key: <WARMUP_KEY と同じ値>` |

日本時間 2:00 から 5:00 の間は実行しない。上記以外の時間帯は 10 分ごとに実行する。

## 確認手順

warmup が失敗している場合は、まず以下を確認する。

1. cron-job.org の URL が現在の backend 公開 URL を指している。
2. cron-job.org の request header に `X-Warmup-Key` が設定されている。
3. cron-job.org の `X-Warmup-Key` と Render の `WARMUP_KEY` が一致している。
4. cron-job.org の timezone が `Asia/Tokyo` になっている。
5. cron-job.org の schedule が 2:00 から 5:00 を除外し、それ以外を 10 分間隔にしている。
6. cron-job.org の execution history で HTTP status と直近の失敗時刻を確認する。

## 導入しないもの

この warmup では以下を導入しない。

- Cloudflare Workers Cron Trigger
- 複雑なリトライ制御
- 複数サービスによる二重実行
- フォールバック経路
- 専用監視基盤
- DB 死活確認
- 通常業務処理

失敗通知を使う場合も cron-job.org の通知設定に留め、Green Mate 側には warmup 専用の監視基盤を追加しない。
