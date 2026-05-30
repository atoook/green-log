import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { test } from 'node:test'

const readSource = (path) => readFile(new URL(`../${path}`, import.meta.url), 'utf8')

test('WateringStatusPanel exposes presentational props and retry emit only', async () => {
  const source = await readSource('src/components/watering/WateringStatusPanel.vue')

  assert.match(source, /import\s+type\s+\{\s*ApiError\s*\}\s+from\s+['"]\.\.\/\.\.\/types\/api['"]/)
  assert.match(source, /import\s+type\s+\{\s*PlantWateringDetail\s*\}\s+from\s+['"]\.\.\/\.\.\/types\/watering['"]/)
  assert.match(source, /watering:\s*PlantWateringDetail\s*\|\s*null/)
  assert.match(source, /isLoading:\s*boolean/)
  assert.match(source, /error:\s*ApiError\s*\|\s*null/)
  assert.match(source, /wateringCycleDays\?:\s*number/)
  assert.match(source, /defineEmits<\{[\s\S]*retry:\s*\[\]/)
  assert.doesNotMatch(source, /fetch\(|createWateringApiClient|useAuthenticatedApi|Clerk|useRouter|useRoute|WateringActionButton|emit\(['"]record['"]/)
})

test('WateringStatusPanel renders loading, error, and missing-data states with safe copy', async () => {
  const source = await readSource('src/components/watering/WateringStatusPanel.vue')

  assert.match(source, /v-if=["']isLoading["']/)
  assert.match(source, /v-else-if=["']error["']/)
  assert.match(source, /v-else-if=["']!watering["']/)
  assert.match(source, /水やり状態を読み込んでいます/)
  assert.match(source, /水やり状態を表示できません/)
  assert.match(source, /まだ水やり状態を確認できません/)
  assert.match(source, /@click=["']emit\('retry'\)["']/)
  assert.match(source, /aria-live=["']polite["']/)
  assert.match(source, /function\s+statusErrorMessage\([^)]*ApiError\):\s*string/)
  assert.match(source, /case\s+['"]auth['"][\s\S]*ログイン/)
  assert.match(source, /case\s+['"]forbidden['"][\s\S]*利用できません/)
  assert.match(source, /case\s+['"]network['"][\s\S]*接続/)
  assert.match(source, /case\s+['"]server['"][\s\S]*読み込めません/)
  assert.doesNotMatch(source, /error\.message/)
})

test('WateringStatusPanel visually distinguishes unrecorded, due today, overdue, and not-due states', async () => {
  const source = await readSource('src/components/watering/WateringStatusPanel.vue')

  assert.match(source, /case\s+['"]unrecorded['"][\s\S]*未記録/)
  assert.match(source, /case\s+['"]due_today['"][\s\S]*今日水やりが必要/)
  assert.match(source, /case\s+['"]overdue['"][\s\S]*予定日を過ぎています/)
  assert.match(source, /return\s+[\s\S]*まだ水やりは不要/)
  assert.match(source, /bg-amber-50[\s\S]*text-amber-800/)
  assert.match(source, /bg-leaf-50[\s\S]*text-leaf-700/)
  assert.match(source, /bg-red-50[\s\S]*text-red-700/)
  assert.match(source, /bg-sky-50[\s\S]*text-sky-700/)
  assert.match(source, /statusTone\(watering\)/)
  assert.match(source, /statusLabel\(watering\)/)
  assert.match(source, /statusHelp\(watering\)/)
})

test('WateringStatusPanel shows latest and next watering values with frequency-derived copy', async () => {
  const source = await readSource('src/components/watering/WateringStatusPanel.vue')

  assert.match(source, /formatDateTime\(watering\.lastWateredAt\)/)
  assert.match(source, /formatDate\(watering\.nextWateringDate\)/)
  assert.match(source, /最新の水やり/)
  assert.match(source, /次回予定日/)
  assert.match(source, /未記録/)
  assert.match(source, /未確定/)
  assert.match(source, /登録した水やり頻度から算出/)
  assert.match(source, /wateringCycleDays[\s\S]*日ごとの水やり頻度から算出/)
  assert.match(source, /最初の水やりを記録すると/)
  assert.doesNotMatch(source, /次回予定日[\s\S]{0,160}<input|nextWateringDate[\s\S]{0,160}v-model/)
})

test('WateringStatusPanel keeps mobile layout readable without scope creep controls', async () => {
  const source = await readSource('src/components/watering/WateringStatusPanel.vue')

  assert.match(source, /grid gap-4/)
  assert.match(source, /sm:grid-cols-2/)
  assert.match(source, /min-w-0/)
  assert.match(source, /break-words/)
  assert.match(source, /rounded-md/)
  assert.doesNotMatch(source, /rounded-(xl|2xl|3xl)/)
  assert.doesNotMatch(source, /タスク|管理|通知|スキップ|延期|カレンダー|お世話種別|履歴|RouterLink|Calendar|Notification|permission|skip|defer/i)
})
