import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { test } from 'node:test'

const readSource = (path) => readFile(new URL(`../${path}`, import.meta.url), 'utf8')

test('TodayCareList exposes presentational props and emits without API or auth dependencies', async () => {
  const source = await readSource('src/components/watering/TodayCareList.vue')

  assert.match(source, /import\s+WateringActionButton\s+from\s+['"]\.\/WateringActionButton\.vue['"]/)
  assert.match(source, /import\s+type\s+\{\s*ApiError\s*\}\s+from\s+['"]\.\.\/\.\.\/types\/api['"]/)
  assert.match(source, /import\s+type\s+\{\s*UpcomingCareItem\s*\}\s+from\s+['"]\.\.\/\.\.\/types\/watering['"]/)
  assert.match(source, /items:\s*UpcomingCareItem\[\]/)
  assert.match(source, /isLoading:\s*boolean/)
  assert.match(source, /error:\s*ApiError\s*\|\s*null/)
  assert.match(source, /recordingError:\s*ApiError\s*\|\s*null/)
  assert.match(source, /isRecordingByPlantId:\s*Record<number,\s*boolean>/)
  assert.match(source, /successfulPlantId\?:\s*number\s*\|\s*null/)
  assert.match(source, /record:\s*\[plantId:\s*number\]/)
  assert.match(source, /retry:\s*\[\]/)
  assert.doesNotMatch(source, /fetch\(|createWateringApiClient|useAuthenticatedApi|Clerk|useRouter|useRoute|Authorization|Bearer/)
})

test('TodayCareList renders loading, error, empty, and recording failure states with safe copy', async () => {
  const source = await readSource('src/components/watering/TodayCareList.vue')

  assert.match(source, /v-if=["']isLoading["']/)
  assert.match(source, /v-else-if=["']error["']/)
  assert.match(source, /v-else-if=["']items\.length\s*===\s*0["']/)
  assert.match(source, /v-if=["']recordingError["']/)
  assert.match(source, /今日のお世話/)
  assert.match(source, /読み込んでいます/)
  assert.match(source, /今日必要な水やりはありません/)
  assert.match(source, /植物を登録/)
  assert.match(source, /記録できませんでした/)
  assert.match(source, /@click=["']emit\('retry'\)["']/)
  assert.match(source, /aria-live=["']polite["']/)
  assert.match(source, /function\s+careErrorMessage\([^)]*ApiError\):\s*string/)
  assert.match(source, /case\s+['"]auth['"][\s\S]*ログイン/)
  assert.match(source, /case\s+['"]forbidden['"][\s\S]*表示できません/)
  assert.match(source, /case\s+['"]network['"][\s\S]*接続/)
  assert.match(source, /case\s+['"]server['"][\s\S]*読み込めません/)
  assert.doesNotMatch(source, /error\.message/)
  assert.doesNotMatch(source, /タスク|管理|通知|スキップ|延期|カレンダー|お世話種別/)
})

test('TodayCareList displays due item details and delegates record events to WateringActionButton', async () => {
  const source = await readSource('src/components/watering/TodayCareList.vue')

  assert.match(source, /v-for=["']item in items["']/)
  assert.match(source, /:key=["']item\.plantId["']/)
  assert.match(source, /item\.plant\.name/)
  assert.match(source, /item\.plant\.wateringCycleDays/)
  assert.match(source, /lastWateredLabel\(item\)/)
  assert.match(source, /nextWateringLabel\(item\)/)
  assert.match(source, /dueStatusLabel\(item\)/)
  assert.match(source, /dueStatusClasses\(item\)/)
  assert.match(source, /未記録/)
  assert.match(source, /今日がお世話の日/)
  assert.match(source, /予定日を過ぎています/)
  assert.match(source, /未確定/)
  assert.match(source, /<WateringActionButton[\s\S]*:is-recording=["']Boolean\(isRecordingByPlantId\[item\.plantId\]\)["'][\s\S]*:has-error=["']Boolean\(recordingError\)["'][\s\S]*:was-successful=["']successfulPlantId === item\.plantId["'][\s\S]*@record=["']emit\('record', item\.plantId\)["']/)
})

test('TodayCareList keeps mobile layout readable without scope creep controls', async () => {
  const source = await readSource('src/components/watering/TodayCareList.vue')

  assert.match(source, /grid gap-3/)
  assert.match(source, /md:grid-cols-\[minmax\(0,1fr\)_auto\]/)
  assert.match(source, /min-w-0/)
  assert.match(source, /break-words/)
  assert.match(source, /w-full[\s\S]*md:w-auto/)
  assert.match(source, /rounded-md/)
  assert.doesNotMatch(source, /w-16\s+.*WateringActionButton|w-20|w-24|truncate/)
  assert.doesNotMatch(source, /RouterLink|calendar|Calendar|Notification|permission|skip|defer|history/i)
})
