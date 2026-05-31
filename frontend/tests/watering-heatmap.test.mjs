import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { test } from 'node:test'

const readSource = (path) => readFile(new URL(`../${path}`, import.meta.url), 'utf8')

test('WateringHeatmap exposes presentational props and selection/retry emits only', async () => {
  const source = await readSource('src/components/watering/WateringHeatmap.vue')

  assert.match(source, /import\s+type\s+\{\s*ApiError\s*\}\s+from\s+['"]\.\.\/\.\.\/types\/api['"]/)
  assert.match(source, /import\s+type\s+\{\s*WateringHeatmap,\s*WateringHeatmapDay,\s*WateringHeatmapLevel\s*\}\s+from\s+['"]\.\.\/\.\.\/types\/watering['"]/)
  assert.match(source, /heatmap:\s*WateringHeatmap\s*\|\s*null/)
  assert.match(source, /isLoading:\s*boolean/)
  assert.match(source, /error:\s*ApiError\s*\|\s*null/)
  assert.match(source, /selectedDate:\s*string\s*\|\s*null/)
  assert.match(source, /selectedDay:\s*WateringHeatmapDay\s*\|\s*null/)
  assert.match(source, /selectDate:\s*\[date:\s*string\]/)
  assert.match(source, /clearSelection:\s*\[\]/)
  assert.match(source, /retry:\s*\[\]/)
  assert.doesNotMatch(source, /fetch\(|createWateringApiClient|useAuthenticatedApi|Clerk|useRouter|useRoute|Authorization|Bearer/)
})

test('WateringHeatmap renders loading, error with retry, missing data, and all-zero empty states', async () => {
  const source = await readSource('src/components/watering/WateringHeatmap.vue')

  assert.match(source, /v-if=["']isLoading["']/)
  assert.match(source, /v-else-if=["']error["']/)
  assert.match(source, /v-else-if=["']!heatmap["']/)
  assert.match(source, /v-if=["']isEmptyHeatmap["']/)
  assert.match(source, /水やりヒートマップ/)
  assert.match(source, /実績を読み込んでいます/)
  assert.match(source, /ヒートマップを表示できません/)
  assert.match(source, /水やり記録はまだありません/)
  assert.match(source, /水やりを記録すると/)
  assert.match(source, /@click=["']emit\('retry'\)["']/)
  assert.match(source, /aria-live=["']polite["']/)
  assert.match(source, /function\s+heatmapErrorMessage\([^)]*ApiError\):\s*string/)
  assert.match(source, /case\s+['"]auth['"][\s\S]*ログイン/)
  assert.match(source, /case\s+['"]forbidden['"][\s\S]*表示できません/)
  assert.match(source, /case\s+['"]network['"][\s\S]*接続/)
  assert.match(source, /case\s+['"]server['"][\s\S]*読み込めません/)
  assert.doesNotMatch(source, /error\.message/)
})

test('WateringHeatmap maps one fixed cell per day to level 0-4 Tailwind colors', async () => {
  const source = await readSource('src/components/watering/WateringHeatmap.vue')

  assert.match(source, /v-for=["']day in heatmap\.days["']/)
  assert.match(source, /:key=["']day\.date["']/)
  assert.match(source, /type=["']button["']/)
  assert.match(source, /levelClasses\(day\.level\)/)
  assert.match(source, /case\s+0:[\s\S]*bg-stone-100/)
  assert.match(source, /case\s+1:[\s\S]*bg-leaf-50/)
  assert.match(source, /case\s+2:[\s\S]*bg-leaf-100/)
  assert.match(source, /case\s+3:[\s\S]*bg-leaf-600/)
  assert.match(source, /case\s+4:[\s\S]*bg-leaf-700/)
  assert.match(source, /h-4\s+w-4/)
  assert.match(source, /aria-label.*cellLabel\(day\)/)
  assert.match(source, /title.*cellLabel\(day\)/)
})

test('WateringHeatmap shows period, strength legend, date detail, and current plant names', async () => {
  const source = await readSource('src/components/watering/WateringHeatmap.vue')

  assert.match(source, /periodLabel/)
  assert.match(source, /formatDate\(props\.heatmap\.startDate\)/)
  assert.match(source, /formatDate\(props\.heatmap\.endDate\)/)
  assert.match(source, /実績なし/)
  assert.match(source, /多い/)
  assert.match(source, /detailDay/)
  assert.match(source, /formatDate\(detailDay\.date\)/)
  assert.match(source, /detailDay\.plants\.length\s*===\s*0/)
  assert.match(source, /この日の水やり記録はありません/)
  assert.match(source, /v-for=["']plant in detailDay\.plants["']/)
  assert.match(source, /:key=["']plant\.plantId["']/)
  assert.match(source, /plant\.name/)
  assert.match(source, /break-words/)
  assert.doesNotMatch(source, /plantCount[\s\S]{0,80}件だけ|回数|回/)
})

test('WateringHeatmap keeps mobile layout readable without scope creep controls', async () => {
  const source = await readSource('src/components/watering/WateringHeatmap.vue')

  assert.match(source, /overflow-x-auto/)
  assert.match(source, /grid-flow-col/)
  assert.match(source, /grid-rows-7/)
  assert.match(source, /min-w-max/)
  assert.match(source, /min-w-0/)
  assert.match(source, /break-words/)
  assert.match(source, /rounded-md/)
  assert.doesNotMatch(source, /rounded-(xl|2xl|3xl)/)
  assert.doesNotMatch(source, /タスク|管理|通知|スキップ|延期|カレンダー|お世話種別|ランキング|連続|streak|週次|月次|フィルタ|filter|RouterLink|Calendar|Notification|permission|skip|defer/i)
  assert.doesNotMatch(source, /<select|checkbox|radio|v-model|plantFilter|ranking|streak/)
})
