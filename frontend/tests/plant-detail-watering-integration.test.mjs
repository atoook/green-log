import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { test } from 'node:test'

const readSource = (path) => readFile(new URL(`../${path}`, import.meta.url), 'utf8')

const outOfScopeDetailUi =
  /通知|スキップ|延期|カレンダー|お世話種別|Notification|permission|skip|defer|calendar/i

test('PlantDetailPage composes plant basic detail with watering state, action, and history', async () => {
  const source = await readSource('src/pages/PlantDetailPage.vue')

  assert.match(
    source,
    /import\s+WateringActionButton\s+from\s+['"]\.\.\/components\/watering\/WateringActionButton\.vue['"]/,
  )
  assert.match(
    source,
    /import\s+WateringHistoryList\s+from\s+['"]\.\.\/components\/watering\/WateringHistoryList\.vue['"]/,
  )
  assert.match(
    source,
    /import\s+WateringStatusPanel\s+from\s+['"]\.\.\/components\/watering\/WateringStatusPanel\.vue['"]/,
  )
  assert.match(source, /import\s+\{\s*usePlantWatering\s*\}\s+from\s+['"]\.\.\/composables\/usePlantWatering['"]/)
  assert.match(
    source,
    /const\s+\{[\s\S]*watering[\s\S]*history[\s\S]*hasWateredToday[\s\S]*isLoading:\s*isWateringLoading[\s\S]*isRecording[\s\S]*error:\s*wateringError[\s\S]*recordingError[\s\S]*successMessage[\s\S]*loadWatering[\s\S]*recordWatering[\s\S]*\}\s*=\s*usePlantWatering\(plantId\)/,
  )
  assert.match(source, /const\s+hasRecordingError\s*=\s*computed\(\(\)\s*=>\s*recordingError\.value\s*!==\s*null\)/)
  assert.match(source, /const\s+wasWateringSuccessful\s*=\s*computed\(\(\)\s*=>\s*successMessage\.value\s*!==\s*null\)/)
  assert.match(source, /const\s+isWateringActionDisabled\s*=\s*computed\(\(\)\s*=>\s*!plant\.value\s*\|\|\s*hasWateredToday\.value\)/)
  assert.match(
    source,
    /async\s+function\s+recordPlantWatering\(\):\s*Promise<void>\s*\{[\s\S]*await\s+recordWatering\(\)/,
  )
  assert.match(
    source,
    /function\s+retryWatering\(\):\s*void\s*\{[\s\S]*void\s+loadWatering\(\)/,
  )
})

test('PlantDetailPage keeps plant and watering error surfaces separate', async () => {
  const source = await readSource('src/pages/PlantDetailPage.vue')
  const plantDetailTag = source.match(/<PlantDetail\b[^>]*\/>/)?.[0]

  assert.ok(plantDetailTag, 'PlantDetail tag must be present')
  assert.match(
    source,
    /<PlantDetail[\s\S]*:plant=["']plant["'][\s\S]*:is-loading=["']isLoading["'][\s\S]*:error=["']error["'][\s\S]*@back=["']backToList["'][\s\S]*@edit=["']startEditing["'][\s\S]*\/>/,
  )
  assert.match(source, /<section\s+v-if=["']plant["'][\s\S]*aria-labelledby=["']plant-watering-title["']/)
  assert.match(
    source,
    /<WateringStatusPanel[\s\S]*:watering=["']watering["'][\s\S]*:is-loading=["']isWateringLoading["'][\s\S]*:error=["']wateringError["'][\s\S]*:watering-cycle-days=["']plant\.wateringCycleDays["'][\s\S]*@retry=["']retryWatering["']/,
  )
  assert.match(
    source,
    /<WateringHistoryList[\s\S]*:history=["']history["'][\s\S]*:is-loading=["']isWateringLoading["'][\s\S]*:error=["']wateringError["'][\s\S]*@retry=["']retryWatering["']/,
  )
  assert.doesNotMatch(plantDetailTag, /wateringError/)
  assert.doesNotMatch(source, /error\s*\|\|\s*wateringError|wateringError\s*\|\|\s*error/)
})

test('PlantDetailPage wires record success feedback without direct API or out-of-scope UI', async () => {
  const source = await readSource('src/pages/PlantDetailPage.vue')

  assert.match(
    source,
    /<WateringActionButton[\s\S]*:is-recording=["']isRecording["'][\s\S]*:disabled=["']isWateringActionDisabled["'][\s\S]*:has-error=["']hasRecordingError["'][\s\S]*:already-recorded-today=["']hasWateredToday["'][\s\S]*:was-successful=["']wasWateringSuccessful["'][\s\S]*@record=["']recordPlantWatering["']/,
  )
  assert.match(source, /v-if=["']updateSuccessMessage \|\| successMessage["'][\s\S]*aria-live=["']polite["'][\s\S]*\{\{\s*updateSuccessMessage \|\| successMessage\s*\}\}/)
  assert.match(source, /水やりの記録/)
  assert.doesNotMatch(source, /fetch\(|createWateringApiClient|useAuthenticatedApi|Clerk|Authorization|Bearer/)
  assert.doesNotMatch(source, outOfScopeDetailUi)
})
