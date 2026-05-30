# Authentication And Authorization

## Purpose

Authentication / Authorization は Green Mate の全ユーザー所有データに適用する共通基盤である。後続 feature は、Clerk で認証されたユーザーを Green Mate 内部の application user に対応付け、internal owner id によってデータを分離する前提で設計する。

この file は provider 固有の実装手順ではなく、ユーザー所有 domain を追加するときに守る恒久ルールを記載する。

## Identity Model

- Clerk は外部認証 provider として扱い、Green Mate の domain owner にはしない。
- Clerk User ID は `users.clerk_user_id` の unique mapping として保持する。domain table は Clerk User ID ではなく、internal `users.id` を owner id として参照する。
- 初回の保護 API アクセスでは application user を lazy upsert し、以後は同じ Clerk user に対して同じ internal user を再利用する。
- Application user の状態は `active`、`disabled`、`deleted` を区別する。`active` 以外の user は保護データ操作に使わない。
- 削除済み user を webhook の後着 update で再有効化しない。再有効化や退会後データ保持は、別 spec で明示されるまで追加しない。

## Protected API Rules

- ユーザー所有データを扱う API は必ず `CurrentUser` を解決してから domain service を呼ぶ。
- 認証情報が欠落、不正、期限切れ、検証不能な場合は fail closed で 401 にする。
- Application user が `disabled` または `deleted` の場合は 403 にし、domain operation を実行しない。
- 他ユーザー所有データの detail / update / delete は対象の存在を漏らさない。通常は owner-scoped lookup の結果として 404 を返す。
- 公開 API を追加する場合も、認証なしでユーザー所有データを返してはならない。

## Owner Scope Rules

- owner id は request body、query、route parameter から採用しない。必ず認証済み `CurrentUser.id` から決定する。
- create は `CurrentUser.id` を owner として保存する。client から送られた user id / owner id は無視し、API schema にも露出しない。
- list は owner id で絞り込む。detail、update、delete は resource id と owner id の両方で lookup する。
- すべてのユーザー所有 domain table は owner column を持ち、ownerless row を通常 path で作らない。
- API response は owner id、Clerk User ID、内部認証情報を返さない。必要な user-facing 表示だけを別途設計する。

## Frontend Auth Rules

- Clerk provider は app bootstrap に置き、保護 route は router metadata と auth gate で囲む。
- 認証状態を確認中の間は、ユーザー所有データを描画しない。
- signed-out、logout 後、session expired、auth error の状態では、直前ユーザーのデータを成功状態として残さない。
- API token injection は authenticated API client / composable に集約する。presentation component は Clerk SDK、Bearer token、Authorization header を扱わない。
- User-facing auth error は再ログインや利用不可を示す文言に留め、secret、token、raw claims、verifier 内部情報を表示しない。

## Webhook Sync Rules

- Clerk webhook は raw body と Svix headers で署名検証してから処理する。
- 受け付ける provider event は application user lifecycle に必要なものだけに限定する。
- Webhook processing は冪等にし、重複 delivery や lazy upsert との順序差で user row を重複作成しない。
- Webhook verification に失敗した event は application user state を変更しない。
- Webhook secret、signature、raw payload の機密情報を log、error response、steering、spec に記載しない。

## Verification Expectations

- Auth / user 境界は、missing token、invalid token、inactive user、lazy upsert、duplicate upsert を test で固定する。
- User-owned domain API は、unauthenticated access、user A / user B separation、other-owner detail 404、owner field 非公開を test で固定する。
- Migration と smoke verification は、application user 作成、owner-scoped CRUD、ownerless row が通常 path で作られないことを確認する。
- Frontend build は、auth gate、typed API error、token-aware API client の型境界を通す。

## 更新履歴

- updated_at: 2026-05-30 - 認証・認可基盤の実装完了に合わせ、恒久的な identity / owner scope / protected API ルールを追加。
