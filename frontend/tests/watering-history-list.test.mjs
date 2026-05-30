import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { test } from 'node:test'

const readSource = (path) => readFile(new URL(`../${path}`, import.meta.url), 'utf8')

test('WateringHistoryList exposes presentational props and retry emit only', async () => {
  const source = await readSource('src/components/watering/WateringHistoryList.vue')

  assert.match(source, /import\s+type\s+\{\s*ApiError\s*\}\s+from\s+['"]\.\.\/\.\.\/types\/api['"]/)
  assert.match(source, /import\s+type\s+\{\s*WateringRecord\s*\}\s+from\s+['"]\.\.\/\.\.\/types\/watering['"]/)
  assert.match(source, /history:\s*WateringRecord\[\]/)
  assert.match(source, /isLoading:\s*boolean/)
  assert.match(source, /error:\s*ApiError\s*\|\s*null/)
  assert.match(source, /defineEmits<\{[\s\S]*retry:\s*\[\]/)
  assert.doesNotMatch(source, /fetch\(|createWateringApiClient|useAuthenticatedApi|Clerk|useRouter|useRoute|Authorization|Bearer|WateringActionButton|emit\(['"]record['"]/)
})

test('WateringHistoryList renders loading, error, and empty states with safe copy', async () => {
  const source = await readSource('src/components/watering/WateringHistoryList.vue')

  assert.match(source, /v-if=["']isLoading["']/)
  assert.match(source, /v-else-if=["']error["']/)
  assert.match(source, /v-else-if=["']history\.length\s*===\s*0["']/)
  assert.match(source, /水やり履歴/)
  assert.match(source, /履歴を読み込んでいます/)
  assert.match(source, /水やり履歴を表示できません/)
  assert.match(source, /水やり履歴はまだありません/)
  assert.match(source, /水やりを記録すると/)
  assert.match(source, /@click=["']emit\('retry'\)["']/)
  assert.match(source, /aria-live=["']polite["']/)
  assert.match(source, /function\s+historyErrorMessage\([^)]*ApiError\):\s*string/)
  assert.match(source, /case\s+['"]auth['"][\s\S]*ログイン/)
  assert.match(source, /case\s+['"]forbidden['"][\s\S]*利用できません/)
  assert.match(source, /case\s+['"]network['"][\s\S]*接続/)
  assert.match(source, /case\s+['"]server['"][\s\S]*読み込めません/)
  assert.doesNotMatch(source, /error\.message/)
})

test('WateringHistoryList preserves newest-first API order and emphasizes the first record', async () => {
  const source = await readSource('src/components/watering/WateringHistoryList.vue')

  assert.match(source, /v-for=["']\(record,\s*index\)\s+in\s+history["']/)
  assert.match(source, /:key=["']record\.id["']/)
  assert.match(source, /formatDateTime\(record\.wateredAt\)/)
  assert.match(source, /index\s*===\s*0/)
  assert.match(source, /最新の記録/)
  assert.match(source, /記録日時/)
  assert.match(source, /record\.id/)
  assert.doesNotMatch(source, /\.sort\(|\.reverse\(|toSorted\(|toReversed\(/)
  assert.doesNotMatch(source, /createdAt[\s\S]{0,160}<dd|formatDateTime\(record\.createdAt\)/)
})

test('WateringHistoryList stays within read-only MVP scope and readable mobile layout', async () => {
  const source = await readSource('src/components/watering/WateringHistoryList.vue')

  assert.match(source, /grid gap-4/)
  assert.match(source, /grid-cols-\[auto_minmax\(0,1fr\)\]/)
  assert.match(source, /min-w-0/)
  assert.match(source, /break-words/)
  assert.match(source, /rounded-md/)
  assert.doesNotMatch(source, /rounded-(xl|2xl|3xl)/)
  assert.doesNotMatch(source, /truncate/)
  assert.doesNotMatch(source, /編集|削除|メモ|CSV|エクスポート|カレンダー|通知|スキップ|延期|お世話種別|管理/)
  assert.doesNotMatch(source, /<input|<textarea|v-model|@click=["'][^"']*(edit|delete|remove|memo)/i)
})
