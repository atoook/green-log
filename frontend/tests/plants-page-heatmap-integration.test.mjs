import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { test } from 'node:test'

const readSource = (path) => readFile(new URL(`../${path}`, import.meta.url), 'utf8')

const outOfScopeHeatmapControls =
  /streak|ranking|rank|filter|summary|weekly|monthly|連続|ランキング|絞り込み|週次|月次/

function firstComponentTag(source, tagName) {
  const match = source.match(new RegExp(`<${tagName}[\\s\\S]*?\\/>`))
  assert.ok(match, `${tagName} tag must be present`)
  return match[0]
}

test('PlantsPage composes the watering heatmap without replacing plant form or list', async () => {
  const source = await readSource('src/pages/PlantsPage.vue')

  assert.match(
    source,
    /import\s+WateringHeatmap\s+from\s+['"]\.\.\/components\/watering\/WateringHeatmap\.vue['"]/,
  )
  assert.match(
    source,
    /import\s+\{\s*useWateringHeatmap\s*\}\s+from\s+['"]\.\.\/composables\/useWateringHeatmap['"]/,
  )
  assert.match(
    source,
    /const\s+\{[\s\S]*heatmap[\s\S]*isLoading:\s*isLoadingHeatmap[\s\S]*error:\s*heatmapError[\s\S]*selectedDate[\s\S]*selectedDay[\s\S]*loadHeatmap[\s\S]*retry:\s*retryHeatmap[\s\S]*setSelectedDate[\s\S]*clearSelectedDate[\s\S]*\}\s*=\s*useWateringHeatmap\(\{\s*autoLoad:\s*false\s*\}\)/,
  )
  assert.match(source, /onMounted\(\(\)\s*=>\s*\{[\s\S]*void\s+loadHeatmap\(\)[\s\S]*\}\)/)
  assert.match(
    source,
    /<WateringHeatmap[\s\S]*:heatmap=["']heatmap["'][\s\S]*:is-loading=["']isLoadingHeatmap["'][\s\S]*:error=["']heatmapError["'][\s\S]*:selected-date=["']selectedDate["'][\s\S]*:selected-day=["']selectedDay["'][\s\S]*@select-date=["']setSelectedDate["'][\s\S]*@clear-selection=["']clearSelectedDate["'][\s\S]*@retry=["']retryHeatmap["']/,
  )
  assert.match(
    source,
    /<PlantForm[\s\S]*:is-submitting=["']isCreating["'][\s\S]*:server-error=["']serverError["'][\s\S]*@submit=["']submitPlant["']/,
  )
  assert.match(
    source,
    /<PlantList[\s\S]*:plants=["']plants["'][\s\S]*:is-loading=["']isLoadingList["'][\s\S]*:error=["']error\?\.type\s*===\s*'validation'\s*\?\s*null\s*:\s*error["'][\s\S]*@select=["']selectPlant["'][\s\S]*@retry=["']loadPlants["']/,
  )
})

test('PlantsPage keeps heatmap loading and errors local to the heatmap section', async () => {
  const source = await readSource('src/pages/PlantsPage.vue')
  const plantFormTag = firstComponentTag(source, 'PlantForm')
  const plantListTag = firstComponentTag(source, 'PlantList')
  const heatmapTag = firstComponentTag(source, 'WateringHeatmap')

  assert.match(source, /const\s+serverError\s*=\s*computed\(/)
  assert.doesNotMatch(source, /serverError[\s\S]{0,120}heatmapError/)
  assert.doesNotMatch(plantFormTag, /heatmapError|isLoadingHeatmap/)
  assert.doesNotMatch(plantListTag, /heatmapError|isLoadingHeatmap/)
  assert.match(heatmapTag, /:error=["']heatmapError["']/)
  assert.match(heatmapTag, /:is-loading=["']isLoadingHeatmap["']/)
  assert.doesNotMatch(source, /const\s+\{[\s\S]*error:\s*error[\s\S]*\}\s*=\s*useWateringHeatmap\(\)/)
})

test('PlantsPage layout shows the recent heatmap alongside the existing home content on small screens', async () => {
  const source = await readSource('src/pages/PlantsPage.vue')

  assert.match(source, /<main\s+class=["']mx-auto grid max-w-5xl gap-4 p-4/)
  assert.match(source, /<section\s+class=["']grid gap-4 md:col-span-2["']/)
  assert.match(source, /<div\s+class=["']grid gap-4 md:grid-cols-\[360px_1fr\]["']/)
  assert.doesNotMatch(source, /hidden\s+md:block|md:hidden/)
  assert.doesNotMatch(source, outOfScopeHeatmapControls)
})
