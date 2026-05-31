import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { test } from 'node:test'

const readSource = (path) => readFile(new URL(`../${path}`, import.meta.url), 'utf8')

const outOfScopeUi = /水やり履歴|今日のお世話|成長写真|共有/

test('usePlants clears stale list data on auth and forbidden failures only', async () => {
  const source = await readSource('src/composables/usePlants.ts')

  assert.match(source, /function\s+shouldClearPlantsOnError\s*\([^)]*ApiError/)
  assert.match(
    source,
    /return\s+error\.type\s*===\s*['"]auth['"]\s*\|\|\s*error\.type\s*===\s*['"]forbidden['"]/,
  )
  assert.match(
    source,
    /catch\s*\([^)]*caught[^)]*\)\s*\{[\s\S]*const\s+apiError\s*=\s*caught\s+as\s+ApiError[\s\S]*if\s*\(shouldClearPlantsOnError\(apiError\)\)\s*\{[\s\S]*plants\.value\s*=\s*\[\]/,
  )
  assert.match(
    source,
    /async\s+function\s+addPlant[\s\S]*catch\s*\([^)]*caught[^)]*\)\s*\{[\s\S]*const\s+apiError\s*=\s*caught\s+as\s+ApiError[\s\S]*if\s*\(shouldClearPlantsOnError\(apiError\)\)\s*\{[\s\S]*plants\.value\s*=\s*\[\][\s\S]*return\s+null/,
  )
  assert.doesNotMatch(source, /validation[\s\S]{0,120}plants\.value\s*=\s*\[\]/)
})

test('usePlantDetail clears loaded detail on load errors', async () => {
  const source = await readSource('src/composables/usePlantDetail.ts')

  assert.match(
    source,
    /catch\s*\([^)]*caught[^)]*\)\s*\{[\s\S]*plant\.value\s*=\s*null[\s\S]*error\.value\s*=\s*caught\s+as\s+ApiError/,
  )
})

test('PlantList has distinct safe error messages and own-plant empty state', async () => {
  const source = await readSource('src/components/plants/PlantList.vue')

  assert.match(source, /function\s+listErrorMessage\s*\([^)]*ApiError/)
  assert.match(source, /case\s+['"]auth['"][\s\S]*もう一度ログイン/)
  assert.match(source, /case\s+['"]forbidden['"][\s\S]*この植物一覧を表示できません/)
  assert.match(source, /case\s+['"]network['"][\s\S]*接続/)
  assert.match(source, /case\s+['"]server['"][\s\S]*読み込めません/)
  assert.match(source, /default:[\s\S]*植物一覧を表示できませんでした/)
  assert.match(source, /あなたの植物はまだ登録されていません/)
  assert.doesNotMatch(source, /error\.message/)
  assert.doesNotMatch(source, outOfScopeUi)
})

test('PlantList highlights days since arrival as companion time without backend fallback', async () => {
  const [source, helperSource] = await Promise.all([
    readSource('src/components/plants/PlantList.vue'),
    readSource('src/utils/arrival.ts'),
  ])
  const functionMatch = helperSource.match(/export\s+function\s+daysSinceArrivalLabel[\s\S]*?\n}/)

  assert.ok(functionMatch)

  const functionSource = functionMatch[0]
    .replace(/export\s+function/, 'function')
    .replace(/acquiredDate:\s*string\s*\|\s*null/, 'acquiredDate')
    .replace(/\):\s*string\s*\{/, ') {')
  const daysSinceArrivalLabel = new Function(`${functionSource}; return daysSinceArrivalLabel`)()

  assert.equal(daysSinceArrivalLabel('2026-05-19', new Date(2026, 4, 31, 23, 0)), 'いっしょに暮らして12日目')
  assert.equal(daysSinceArrivalLabel('2026-05-31', new Date(2026, 4, 31, 0, 0)), 'いっしょに暮らして0日目')
  assert.equal(daysSinceArrivalLabel(null, new Date(2026, 4, 31)), 'お迎え日は未記録')
  assert.match(source, /import\s+\{\s*daysSinceArrivalLabel\s*\}\s+from\s+['"]\.\.\/\.\.\/utils\/arrival['"]/)
  assert.match(helperSource, /function\s+daysSinceArrivalLabel\s*\([^)]*acquiredDate[^)]*string\s*\|\s*null[^)]*today\s*=\s*new Date/)
  assert.match(helperSource, /いっしょに暮らして\$\{daysSinceArrival\}日目/)
  assert.match(helperSource, /お迎え日は未記録/)
  assert.match(source, /inline-flex[\s\S]*bg-leaf-50[\s\S]*text-xs[\s\S]*font-semibold/)
  assert.match(helperSource, /const\s+millisecondsPerDay\s*=\s*24\s*\*\s*60\s*\*\s*60\s*\*\s*1000/)
  assert.match(helperSource, /Date\.UTC\([^)]*getFullYear\(\)[\s\S]*getMonth\(\)[\s\S]*getDate\(\)/)
  assert.match(helperSource, /Date\.UTC\([^)]*acquiredYear[\s\S]*acquiredMonth\s*-\s*1[\s\S]*acquiredDay/)
  assert.doesNotMatch(source, /daysSinceArrivalLabel\([^)]*createdAt/)
  assert.doesNotMatch(helperSource, /createdAt[\s\S]{0,120}いっしょに暮らして/)
})

test('PlantDetail keeps not-found behavior and safe auth/forbidden messages', async () => {
  const source = await readSource('src/components/plants/PlantDetail.vue')

  assert.match(source, /function\s+detailErrorMessage\s*\([^)]*ApiError/)
  assert.match(source, /case\s+['"]auth['"][\s\S]*もう一度ログイン/)
  assert.match(source, /case\s+['"]forbidden['"][\s\S]*この植物の記録を表示できません/)
  assert.match(source, /case\s+['"]not_found['"][\s\S]*植物が見つかりません/)
  assert.match(source, /default:[\s\S]*植物の記録を表示できませんでした/)
  assert.doesNotMatch(source, /error\.message/)
  assert.doesNotMatch(source, outOfScopeUi)
})

test('AuthGate and App keep protected route content unmounted while auth is not ready', async () => {
  const [gate, app] = await Promise.all([
    readSource('src/components/auth/AuthGate.vue'),
    readSource('src/App.vue'),
  ])

  assert.match(gate, /v-if=["']!isLoaded["']/)
  assert.match(gate, /v-else-if=["']!isSignedIn["']/)
  assert.match(gate, /<slot\s+v-else\s*\/>/)
  assert.match(app, /<AuthGate[\s\S]*<RouterView\s*\/>[\s\S]*<\/AuthGate>/)
})
