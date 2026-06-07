# Research & Design Decisions

## Summary
- **Feature**: `backend-warmup-endpoint`
- **Discovery Scope**: Extension
- **Key Findings**:
  - 既存 backend は FastAPI router を `app/main.py` で include し、runtime 設定は `app.core.config.Settings` に集約している。
  - warmup は業務データを扱わないため、service / repository / database session を追加しないほうが要件境界に合う。
  - cron-job.org はジョブ URL、HTTP method、リクエストヘッダー、timezone、実行履歴、通知設定を扱えるため、外部 warmup 実行元として要件に合う。

## Research Log

### 既存 backend への統合点
- **Context**: warmup endpoint を既存 FastAPI アプリへ追加するため、router と runtime config の配置を確認した。
- **Sources Consulted**:
  - `backend/app/main.py`
  - `backend/app/core/config.py`
  - `backend/app/routers/care.py`
  - `backend/tests/test_runtime_config.py`
  - `backend/tests/conftest.py`
- **Findings**:
  - router は `app/routers/` に置き、`main.py` で include する既存パターンがある。
  - secret 類は `pydantic.SecretStr` として `Settings` に保持し、テストでは secret 値が repr に出ないことを確認している。
  - `TestClient(app)` を使う API テストと、`Settings()` を直接生成する config テストが既にある。
- **Implications**:
  - `backend/app/routers/warmup.py` を新設し、`backend/app/main.py` に include する。
  - `WARMUP_KEY` は `Settings` の `SecretStr | None` とし、値取得用 property を提供する。
  - warmup router は `get_session`、domain repository、Clerk current user dependency に依存しない。

### cron-job.org の実行元としての適合性
- **Context**: cron-job.org を warmup 実行元にする要件が、必要な HTTP 設定を満たすか確認した。
- **Sources Consulted**:
  - https://docs.cron-job.org/rest-api.html
  - https://docs.cron-job.org/creating-cron-jobs.html
- **Findings**:
  - cron-job.org の REST API `DetailedJob` は `extendedData.headers` を持ち、ジョブごとの request headers を設定できる。
  - `JobSchedule` は `timezone`、`hours`、`minutes` を持ち、timezone は PHP supported timezones を参照する。
  - job execution history と notification settings があり、実行履歴や失敗通知は cron-job.org 側の責務として扱える。
  - cron-job.org の API key は account 操作用 secret であり、Green Mate の warmup endpoint に送る `X-Warmup-Key` とは別の secret として扱う必要がある。
- **Implications**:
  - 運用ドキュメントでは timezone を `Asia/Tokyo`、minutes を `0,10,20,30,40,50`、hours を `0,1,5-23` 相当として明記する。
  - `X-Warmup-Key` は cron-job.org の request header として設定し、URL query には含めない。
  - cron-job.org API の自動設定はこの spec の実装範囲外にする。

## Architecture Pattern Evaluation

| Option | Description | Strengths | Risks / Limitations | Notes |
|--------|-------------|-----------|---------------------|-------|
| Router-only endpoint | FastAPI router がヘッダー検証と応答を直接扱う | 最小構成、DB 非依存、要件に合う | 将来 warmup が複雑化した場合は分割が必要 | 採用 |
| Service layer 追加 | router から warmup service を呼ぶ | 既存 layered architecture に見える | 現時点では抽象化過多、業務処理と誤解されやすい | 不採用 |
| 既存 root endpoint 流用 | `/` を cron-job.org から叩く | 実装が少ない | 固定トークン保護と運用境界を満たしにくい | 不採用 |
| Cloudflare Workers Cron Trigger | Workers が backend を定期呼び出し | IaC 化しやすい | ユーザー方針に反する、warmup 専用 Workers 維持が必要 | 不採用 |

## Design Decisions

### Decision: warmup は router-only として実装する
- **Context**: 要件は軽量な受け付け可否と副作用なしの応答であり、業務 use case ではない。
- **Alternatives Considered**:
  1. Router-only endpoint
  2. Service layer 追加
  3. 既存 root endpoint 流用
- **Selected Approach**: `backend/app/routers/warmup.py` を追加し、`Settings` の固定キーと `X-Warmup-Key` を比較する。
- **Rationale**: 業務データ、DB、認証済みユーザー境界から明確に分離できる。
- **Trade-offs**: service 分割の再利用性はないが、現要件では再利用先がない。
- **Follow-up**: 将来 DB warmup や内部 health check を求める場合は別 spec として再設計する。

### Decision: secret 未設定時は fail closed にする
- **Context**: 公開 URL であるため、固定キーが未設定の状態で成功させると保護要件を満たせない。
- **Alternatives Considered**:
  1. 未設定時も開発環境だけ成功
  2. 未設定時は明示的に拒否
- **Selected Approach**: `WARMUP_KEY` が未設定または空の場合、warmup endpoint は成功応答を返さない。
- **Rationale**: 認証・認可 steering の fail closed 方針に沿う。
- **Trade-offs**: Render 環境変数の設定漏れは cron-job.org 側で失敗として見える。
- **Follow-up**: 運用ドキュメントで Render 側の環境変数確認をトラブルシュート手順に含める。

### Decision: cron-job.org 設定はドキュメントで固定し、自動作成はしない
- **Context**: 要件はシンプルな補助機能であり、専用監視基盤や複雑な運用機構を導入しない。
- **Alternatives Considered**:
  1. 手動設定手順をドキュメント化
  2. cron-job.org REST API を使う自動作成 script を追加
- **Selected Approach**: `docs/operations/backend-warmup.md` に URL、method、header、timezone、schedule、確認項目を記載する。
- **Rationale**: API key 管理やスクリプト保守を増やさず、cron-job.org console で履歴と通知を確認できる。
- **Trade-offs**: 初期設定は手動になる。
- **Follow-up**: 複数環境で同一設定を量産する必要が出た場合のみ、自動化を別途検討する。

## Risks & Mitigations
- `WARMUP_KEY` 未設定により cron-job.org が失敗する — 運用ドキュメントに Render 環境変数確認を明記する。
- 誤って業務データに触れる依存を追加する — router-only 設計とテストで DB session / auth dependency を不要にする。
- cron-job.org の schedule 設定ミスで 2:00 から 5:00 に実行される — `Asia/Tokyo`、minutes、hours の具体値を運用ドキュメントに明記する。

## References
- [cron-job.org REST API documentation](https://docs.cron-job.org/rest-api.html) — request headers、timezone、execution history、notification settings の確認。
- [cron-job.org Creating cron jobs documentation](https://docs.cron-job.org/creating-cron-jobs.html) — cron job request header values に変数を使えることの確認。
