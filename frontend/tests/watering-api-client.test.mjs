import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { test } from 'node:test'
import ts from 'typescript'

async function readSource(path) {
  const sourceUrl = new URL(path, import.meta.url)
  return readFile(sourceUrl, 'utf8')
}

async function loadWateringApiModule() {
  const source = await readSource('../src/api/watering.ts')
  const { outputText } = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.ES2022,
      target: ts.ScriptTarget.ES2022,
      verbatimModuleSyntax: true,
    },
    fileName: 'watering.ts',
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

test('createWateringApiClient delegates today care requests to the authenticated client', async () => {
  const { createWateringApiClient } = await loadWateringApiModule()
  const todayCare = {
    today: '2026-05-30',
    items: [],
  }
  const { calls, client } = createRecordingAuthenticatedClient(new Map([['/care/today', todayCare]]))

  const result = await createWateringApiClient(client).getTodayCare()

  assert.deepEqual(result, todayCare)
  assert.deepEqual(calls, [{ path: '/care/today', init: undefined }])
})

test('createWateringApiClient delegates plant watering detail requests by plant id', async () => {
  const { createWateringApiClient } = await loadWateringApiModule()
  const detail = {
    plantId: 7,
    lastWateredAt: null,
    nextWateringDate: null,
    isDueToday: true,
    dueStatus: 'unrecorded',
    history: [],
  }
  const { calls, client } = createRecordingAuthenticatedClient(
    new Map([['/plants/7/watering', detail]]),
  )

  const result = await createWateringApiClient(client).getPlantWatering(7)

  assert.deepEqual(result, detail)
  assert.deepEqual(calls, [{ path: '/plants/7/watering', init: undefined }])
})

test('createWateringApiClient posts an empty body for watering records without owner fields', async () => {
  const { createWateringApiClient } = await loadWateringApiModule()
  const createResult = {
    record: {
      id: 13,
      plantId: 7,
      wateredAt: '2026-05-30T00:00:00Z',
      createdAt: '2026-05-30T00:00:00Z',
    },
    state: {
      plantId: 7,
      lastWateredAt: '2026-05-30T00:00:00Z',
      nextWateringDate: '2026-06-06',
      isDueToday: false,
      dueStatus: null,
      history: [],
    },
  }
  const { calls, client } = createRecordingAuthenticatedClient(
    new Map([['/plants/7/watering-records', createResult]]),
  )

  const result = await createWateringApiClient(client).recordWatering(7)
  const body = JSON.parse(calls[0].init.body)

  assert.deepEqual(result, createResult)
  assert.equal(calls.length, 1)
  assert.equal(calls[0].path, '/plants/7/watering-records')
  assert.equal(calls[0].init.method, 'POST')
  assert.deepEqual(body, {})
  assert.equal('owner' in body, false)
  assert.equal('ownerUserId' in body, false)
  assert.equal('userId' in body, false)
  assert.equal('clerkUserId' in body, false)
})

test('createWateringApiClient delegates heatmap requests with an encoded date range', async () => {
  const { createWateringApiClient } = await loadWateringApiModule()
  const heatmap = {
    startDate: '2026-03-01',
    endDate: '2026-05-31',
    days: [
      {
        date: '2026-05-31',
        plantCount: 2,
        level: 2,
        plants: [
          { plantId: 7, name: 'Monstera' },
          { plantId: 9, name: 'Pothos' },
        ],
      },
    ],
  }
  const path = '/care/watering-heatmap?from=2026-03-01&to=2026-05-31'
  const { calls, client } = createRecordingAuthenticatedClient(new Map([[path, heatmap]]))

  const result = await createWateringApiClient(client).getWateringHeatmap({
    from: '2026-03-01',
    to: '2026-05-31',
  })

  assert.deepEqual(result, heatmap)
  assert.deepEqual(calls, [{ path, init: undefined }])
})

test('watering api and response types keep auth and owner data out of the client surface', async () => {
  const [wateringApiSource, wateringTypesSource] = await Promise.all([
    readSource('../src/api/watering.ts'),
    readSource('../src/types/watering.ts'),
  ])
  const forbiddenFields = /\b(owner|ownerUserId|userId|clerkUserId)\b/

  assert.doesNotMatch(wateringApiSource, /\bfetch\s*\(/)
  assert.doesNotMatch(wateringApiSource, forbiddenFields)
  assert.doesNotMatch(wateringTypesSource, forbiddenFields)
  assert.doesNotMatch(wateringTypesSource, /(?<![A-Za-z0-9_$])any(?![A-Za-z0-9_$])/)
})
