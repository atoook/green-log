# Roadmap

## Overview
Green Mate の植物画像管理は、画像管理単体の機能ではなく、植物詳細体験の一部として扱う。植物は複数画像を持てるようにし、一覧では代表画像を表示し、詳細では成長記録として時系列に振り返れるギャラリーを提供する。

既存の `plant-photo-schema-foundation` は写真記録と代表写真の永続化基盤を扱う。今回の新規 spec は、その基盤を利用して植物詳細画面からのアップロード、植物単位ギャラリー、代表画像設定、削除確認、一覧での代表画像表示までをユーザー体験として定義する。

## Approach Decision
- **Chosen**: 植物詳細統合型の画像管理
- **Why**: 画像は植物個体の成長記録であり、アップロード対象を現在表示している植物に限定することで、初心者にも紐付け先が明確になる。代表画像もギャラリー内の画像から選ぶため、一覧表示と詳細体験の責務が自然につながる。
- **Rejected alternatives**: 画像管理専用画面は、植物との生活記録という体験から離れ、他植物への紐付け変更など不要な複雑さを生むため採用しない。植物登録時の単一画像アップロード中心の設計は、成長記録やタイムラプスへの拡張に弱いため採用しない。

## Scope
- **In**: 植物詳細画面からの画像アップロード、植物ごとの時系列ギャラリー、画像枚数と上限表示、代表画像設定、代表画像の一覧表示、画像削除と確認ダイアログ、代表画像削除時の未設定化、一般ユーザーの1植物5枚上限、特定ユーザーの上限なし扱い
- **Out**: 他植物への画像紐付け変更、画像管理専用画面、プラン定義や課金、画像編集、サムネイル生成、画像変換、共有、公開ギャラリー、タイムラプス表示そのもの

## Constraints
- Frontend は Vue 3 / Vite / TypeScript / Tailwind CSS の既存構成に従う。
- Backend は FastAPI / SQLModel / SQLAlchemy Session / Alembic の既存 layered architecture に従う。
- ユーザー所有データは Clerk User ID ではなく internal `users.id` で owner scope を適用する。
- 一般ユーザーの画像上限は定数として定義し、運用状況に応じて変更できるようにする。
- 特定ユーザーの上限なし判定は、当面プラン定義を作らず、ユーザーテーブル上の値を直接変更して対応する。
- 画像ファイル保存先や配信方式は、既存の写真記録の画像参照情報と整合する範囲で後続 design で具体化する。

## Boundary Strategy
- **Why this split**: 永続化構造の責務は既存の `plant-photo-schema-foundation` に残し、ユーザー操作・画面表示・画像枚数制限・削除確認などの体験は新規 `plant-image-management` に分ける。これにより schema 基盤の互換性検証と、植物詳細画面の実装を独立してレビューできる。
- **Shared seams to watch**: 写真記録の owner scope、代表写真参照の整合性、画像上限判定、代表画像削除時の未設定化、一覧・詳細 API の代表画像レスポンス互換。

## Existing Spec Updates
- [ ] plant-photo-schema-foundation -- 画像上限判定に必要なユーザー側フラグ、一般ユーザー5枚上限を参照できる前提、代表写真削除時に未設定へ戻せる整合性を既存基盤 spec の更新候補として確認する。Dependencies: none

## Direct Implementation Candidates
- [ ] 定数名の調整 -- 画像上限値の定数追加だけで済む場合は、新規 spec の実装タスク内で扱い、独立 spec にはしない。

## Specs (dependency order)
- [ ] plant-image-management -- 植物詳細画面に統合された画像アップロード、植物単位ギャラリー、代表画像設定、削除確認、一覧代表画像表示を提供する。Dependencies: plant-photo-schema-foundation
