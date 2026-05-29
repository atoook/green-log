# Requirements Document

## Project Description (Input)
Green Mate のプロダクト開発者は、今後追加される植物登録以外の水やり記録、成長写真、今日のお世話など、ユーザーごとのデータを扱う全機能で共通利用できる認証・認可基盤を必要としている。

現在の API は単一ユーザー MVP として動作しており、認証済みユーザーの判定、アプリケーション内部ユーザーの管理、所有者によるデータ分離が存在しない。既存の `plant-registration` spec でも、ログイン、複数ユーザー、user ownership は明示的に out of scope とされている。

Clerk は認証基盤としてのみ利用し、アプリケーション固有のユーザー管理は `users` table で行う。Backend は Clerk session token を検証して current user を取得し、初回ログインまたは初回保護 API アクセス時に application user を冪等作成する。アプリケーション内部では `users.id` を使い、すべてのユーザー所有ドメインテーブルは `users.id` を owner として参照する。クライアントから `userId` / `ownerId` を受け取らず、Plant API を最初の適用先として、未認証アクセス拒否とユーザー間データ分離を実現する。

## Requirements
<!-- Will be generated in /kiro-spec-requirements phase -->

