import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { test } from 'node:test'
import ts from 'typescript'

async function readSource(path) {
  const sourceUrl = new URL(path, import.meta.url)
  return readFile(sourceUrl, 'utf8')
}

async function loadPlantsApiModule() {
  const source = await readSource('../src/api/plants.ts')
  const { outputText } = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.ES2022,
      target: ts.ScriptTarget.ES2022,
      verbatimModuleSyntax: true,
    },
    fileName: 'plants.ts',
  })

  return import(`data:text/javascript;charset=utf-8,${encodeURIComponent(outputText)}`)
}

function createRecordingAuthenticatedClient(resultByPath = new Map()) {
  const calls = []
  return {
    calls,
    client: {
      async request(path, init) {
        calls.push({ path, init })
        return resultByPath.get(path) ?? {}
      },
    },
  }
}

test('createPlantsApiClient delegates list requests to the authenticated client', async () => {
  const { createPlantsApiClient } = await loadPlantsApiModule()
  const plants = [
    {
      id: 1,
      name: 'ポトス',
      acquiredDate: null,
      memo: null,
      imageUrl: null,
      wateringCycleDays: 7,
      createdAt: '2026-01-01T00:00:00Z',
      updatedAt: '2026-01-01T00:00:00Z',
    },
  ]
  const { calls, client } = createRecordingAuthenticatedClient(new Map([['/plants', plants]]))

  const result = await createPlantsApiClient(client).listPlants()

  assert.deepEqual(result, plants)
  assert.deepEqual(calls, [{ path: '/plants', init: undefined }])
})

test('createPlantsApiClient posts plant create input without owner or user id fields', async () => {
  const { createPlantsApiClient } = await loadPlantsApiModule()
  const input = {
    name: 'ガジュマル',
    acquiredDate: '2026-05-01',
    memo: '窓辺',
    imageUrl: null,
    wateringCycleDays: 5,
  }
  const { calls, client } = createRecordingAuthenticatedClient(new Map([['/plants', { id: 2 }]]))

  await createPlantsApiClient(client).createPlant(input)

  assert.equal(calls.length, 1)
  assert.equal(calls[0].path, '/plants')
  assert.equal(calls[0].init.method, 'POST')
  assert.deepEqual(JSON.parse(calls[0].init.body), input)
  assert.equal('owner' in JSON.parse(calls[0].init.body), false)
  assert.equal('ownerUserId' in JSON.parse(calls[0].init.body), false)
  assert.equal('userId' in JSON.parse(calls[0].init.body), false)
  assert.equal('clerkUserId' in JSON.parse(calls[0].init.body), false)
})

test('createPlantsApiClient delegates detail requests to the authenticated client', async () => {
  const { createPlantsApiClient } = await loadPlantsApiModule()
  const { calls, client } = createRecordingAuthenticatedClient(new Map([['/plants/7', { id: 7 }]]))

  const result = await createPlantsApiClient(client).getPlant(7)

  assert.deepEqual(result, { id: 7 })
  assert.deepEqual(calls, [{ path: '/plants/7', init: undefined }])
})

test('plant api and composables do not use direct fetch and keep authenticated composition', async () => {
  const [plantsApiSource, usePlantsSource, usePlantDetailSource] = await Promise.all([
    readSource('../src/api/plants.ts'),
    readSource('../src/composables/usePlants.ts'),
    readSource('../src/composables/usePlantDetail.ts'),
  ])

  assert.doesNotMatch(plantsApiSource, /\bfetch\s*\(/)
  assert.doesNotMatch(usePlantsSource, /\bfetch\s*\(/)
  assert.doesNotMatch(usePlantDetailSource, /\bfetch\s*\(/)
  assert.match(usePlantsSource, /useAuthenticatedApi/)
  assert.match(usePlantsSource, /createPlantsApiClient/)
  assert.match(usePlantDetailSource, /useAuthenticatedApi/)
  assert.match(usePlantDetailSource, /createPlantsApiClient/)
})

test('plant request and response types do not expose owner or client user id fields', async () => {
  const source = await readSource('../src/types/plant.ts')
  const forbiddenFields = /\b(owner|ownerUserId|userId|clerkUserId)\b/

  assert.doesNotMatch(source, forbiddenFields)
  assert.match(source, /from '\.\/api'/)
})
