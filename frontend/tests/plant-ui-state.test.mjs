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
  assert.match(source, /あなたの植物はまだ登録されていません/)
  assert.doesNotMatch(source, /error\.message/)
  assert.doesNotMatch(source, outOfScopeUi)
})

test('PlantDetail keeps not-found behavior and safe auth/forbidden messages', async () => {
  const source = await readSource('src/components/plants/PlantDetail.vue')

  assert.match(source, /function\s+detailErrorMessage\s*\([^)]*ApiError/)
  assert.match(source, /case\s+['"]auth['"][\s\S]*もう一度ログイン/)
  assert.match(source, /case\s+['"]forbidden['"][\s\S]*この植物の記録を表示できません/)
  assert.match(source, /case\s+['"]not_found['"][\s\S]*植物が見つかりません/)
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
