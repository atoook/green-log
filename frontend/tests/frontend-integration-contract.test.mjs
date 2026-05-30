import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { test } from 'node:test'

const readProjectFile = (path) => readFile(new URL(`../${path}`, import.meta.url), 'utf8')

test('frontend auth and api TypeScript contract explicitly rejects implicit any', async () => {
  const tsconfig = await readProjectFile('tsconfig.app.json')

  assert.match(tsconfig, /"noImplicitAny"\s*:\s*true/)
})

test('frontend auth and api source do not introduce explicit any', async () => {
  const sourcePaths = [
    'src/api/client.ts',
    'src/api/plants.ts',
    'src/composables/useAuthenticatedApi.ts',
    'src/composables/usePlants.ts',
    'src/composables/usePlantDetail.ts',
    'src/types/api.ts',
    'src/types/plant.ts',
  ]

  const explicitAnyPattern = /(?<![A-Za-z0-9_$])any(?![A-Za-z0-9_$])/

  for (const sourcePath of sourcePaths) {
    const source = await readProjectFile(sourcePath)
    assert.doesNotMatch(source, explicitAnyPattern, `${sourcePath} must not contain explicit any`)
  }
})

test('signed-in plant create keeps the existing detail navigation contract', async () => {
  const page = await readProjectFile('src/pages/PlantsPage.vue')

  assert.match(page, /const\s+created\s*=\s*await\s+addPlant\(input\)/)
  assert.match(
    page,
    /if\s*\(\s*created\s*\)\s*\{[\s\S]*router\.push\(\s*\{\s*name:\s*['"]plant-detail['"][\s\S]*plantId:\s*String\(created\.id\)/,
  )
  assert.match(
    page,
    /<PlantList[\s\S]*:plants="plants"[\s\S]*:error="error\?\.type\s*===\s*'validation'\s*\?\s*null\s*:\s*error"[\s\S]*@select="selectPlant"/,
  )
})
