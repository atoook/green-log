import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { test } from 'node:test'
import ts from 'typescript'

async function readSource(path) {
  const sourceUrl = new URL(path, import.meta.url)
  return readFile(sourceUrl, 'utf8')
}

async function loadTodayCareComposableModule() {
  const source = await readSource('../src/composables/useTodayCare.ts')
  const { outputText } = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.ES2022,
      target: ts.ScriptTarget.ES2022,
      verbatimModuleSyntax: true,
    },
    fileName: 'useTodayCare.ts',
  })

  const mountedCallbacks = []
  const factoryCalls = []
  globalThis.__todayCareVueMock = {
    computed(getter) {
      return {
        get value() {
          return getter()
        },
      }
    },
    onMounted(callback) {
      mountedCallbacks.push(callback)
    },
    ref(value) {
      return { value }
    },
  }
  globalThis.__todayCareWateringApiMock = {
    createWateringApiClient(apiClient) {
      factoryCalls.push(apiClient)
      return apiClient
    },
  }
  globalThis.__todayCareAuthApiMock = {
    useAuthenticatedApi() {
      return {
        async getTodayCare() {
          return { today: '2026-05-30', items: [] }
        },
        async recordWatering() {
          throw createApiError('server')
        },
      }
    },
  }

  const runnable = outputText
    .replace(
      /import\s+\{\s*computed,\s*onMounted,\s*ref\s*\}\s+from\s+['"]vue['"];?/,
      'const { computed, onMounted, ref } = globalThis.__todayCareVueMock;',
    )
    .replace(
      /import\s+\{\s*createWateringApiClient\s*\}\s+from\s+['"]\.\.\/api\/watering['"];?/,
      'const { createWateringApiClient } = globalThis.__todayCareWateringApiMock;',
    )
    .replace(
      /import\s+\{\s*useAuthenticatedApi\s*\}\s+from\s+['"]\.\/useAuthenticatedApi['"];?/,
      'const { useAuthenticatedApi } = globalThis.__todayCareAuthApiMock;',
    )

  assert.doesNotMatch(runnable, /^import\s/m)

  const module = await import(
    `data:text/javascript;charset=utf-8,${encodeURIComponent(`${runnable}\n// ${Date.now()}`)}`
  )

  return { module, mountedCallbacks, factoryCalls }
}

function createApiError(type) {
  return Object.assign(new Error(type), { type })
}

function createTodayCare(items = []) {
  return {
    today: '2026-05-30',
    items,
  }
}

function createCareItem(plantId = 7) {
  return {
    plantId,
    lastWateredAt: null,
    nextWateringDate: null,
    isDueToday: true,
    dueStatus: 'unrecorded',
    plant: {
      id: plantId,
      name: 'ポトス',
      imageUrl: null,
      wateringCycleDays: 7,
    },
  }
}

test('useTodayCare loads today care and exposes empty state separately from errors', async () => {
  const { module } = await loadTodayCareComposableModule()
  const calls = []
  const apiClient = {
    async getTodayCare() {
      calls.push('getTodayCare')
      return createTodayCare([])
    },
    async recordWatering() {
      throw createApiError('server')
    },
  }

  const state = module.useTodayCare({ wateringApiClient: apiClient, autoLoad: false })

  assert.equal(state.todayCare.value, null)
  assert.equal(state.items.value.length, 0)
  assert.equal(state.isEmpty.value, false)

  await state.loadTodayCare()

  assert.deepEqual(calls, ['getTodayCare'])
  assert.deepEqual(state.todayCare.value, createTodayCare([]))
  assert.deepEqual(state.items.value, [])
  assert.equal(state.isEmpty.value, true)
  assert.equal(state.error.value, null)
  assert.equal(state.isLoading.value, false)
})

test('useTodayCare clears protected data on auth and forbidden load failures only', async () => {
  for (const protectedErrorType of ['auth', 'forbidden']) {
    const { module } = await loadTodayCareComposableModule()
    const protectedCare = createTodayCare([createCareItem()])
    const responses = [
      () => protectedCare,
      () => {
        throw createApiError('network')
      },
      () => {
        throw createApiError(protectedErrorType)
      },
    ]
    const apiClient = {
      async getTodayCare() {
        return responses.shift()()
      },
      async recordWatering() {
        throw createApiError('server')
      },
    }
    const state = module.useTodayCare({ wateringApiClient: apiClient, autoLoad: false })

    await state.loadTodayCare()
    await state.loadTodayCare()

    assert.deepEqual(state.todayCare.value, protectedCare)
    assert.equal(state.error.value.type, 'network')

    await state.loadTodayCare()

    assert.equal(state.todayCare.value, null)
    assert.equal(state.error.value.type, protectedErrorType)
  }
})

test('useTodayCare records watering with per-plant recording state and refetches today care', async () => {
  const { module } = await loadTodayCareComposableModule()
  const calls = []
  let resolveRecord
  const recordPromise = new Promise((resolve) => {
    resolveRecord = resolve
  })
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
  const apiClient = {
    async getTodayCare() {
      calls.push('getTodayCare')
      return createTodayCare([])
    },
    async recordWatering(plantId) {
      calls.push(`recordWatering:${plantId}`)
      return recordPromise
    },
  }
  const state = module.useTodayCare({ wateringApiClient: apiClient, autoLoad: false })

  const resultPromise = state.recordWatering(7)

  assert.equal(state.isRecordingByPlantId.value[7], true)

  resolveRecord(createResult)
  const result = await resultPromise

  assert.deepEqual(result, createResult)
  assert.deepEqual(calls, ['recordWatering:7', 'getTodayCare'])
  assert.equal(state.isRecordingByPlantId.value[7], false)
  assert.equal(state.recordingError.value, null)
  assert.equal(state.successMessage.value, '水やりを記録しました。')
  assert.equal(state.isEmpty.value, true)
})

test('useTodayCare ignores duplicate watering submits for the same plant while pending', async () => {
  const { module } = await loadTodayCareComposableModule()
  const calls = []
  let resolveRecord
  const recordPromise = new Promise((resolve) => {
    resolveRecord = resolve
  })
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
  const apiClient = {
    async getTodayCare() {
      calls.push('getTodayCare')
      return createTodayCare([])
    },
    async recordWatering(plantId) {
      calls.push(`recordWatering:${plantId}`)
      return recordPromise
    },
  }
  const state = module.useTodayCare({ wateringApiClient: apiClient, autoLoad: false })

  const firstResultPromise = state.recordWatering(7)
  const duplicateResult = await state.recordWatering(7)

  assert.equal(duplicateResult, null)
  assert.deepEqual(calls, ['recordWatering:7'])
  assert.equal(state.isRecordingByPlantId.value[7], true)

  resolveRecord(createResult)
  const firstResult = await firstResultPromise

  assert.deepEqual(firstResult, createResult)
  assert.deepEqual(calls, ['recordWatering:7', 'getTodayCare'])
  assert.equal(state.isRecordingByPlantId.value[7], false)
})

test('useTodayCare keeps record failures distinct from load failures and preserves retry data', async () => {
  const { module } = await loadTodayCareComposableModule()
  const protectedCare = createTodayCare([createCareItem()])
  const apiClient = {
    async getTodayCare() {
      return protectedCare
    },
    async recordWatering() {
      throw createApiError('network')
    },
  }
  const state = module.useTodayCare({ wateringApiClient: apiClient, autoLoad: false })

  await state.loadTodayCare()
  const result = await state.recordWatering(7)

  assert.equal(result, null)
  assert.deepEqual(state.todayCare.value, protectedCare)
  assert.equal(state.error.value, null)
  assert.equal(state.recordingError.value.type, 'network')
  assert.equal(state.successMessage.value, null)
  assert.equal(state.isRecordingByPlantId.value[7], false)
})

test('useTodayCare clears protected data on auth or forbidden record failures', async () => {
  const { module } = await loadTodayCareComposableModule()
  const protectedCare = createTodayCare([createCareItem()])
  const apiClient = {
    async getTodayCare() {
      return protectedCare
    },
    async recordWatering() {
      throw createApiError('forbidden')
    },
  }
  const state = module.useTodayCare({ wateringApiClient: apiClient, autoLoad: false })

  await state.loadTodayCare()
  await state.recordWatering(7)

  assert.equal(state.todayCare.value, null)
  assert.equal(state.recordingError.value.type, 'forbidden')
})

test('useTodayCare composes the authenticated watering client and stays within the frontend boundary', async () => {
  const [{ module, mountedCallbacks, factoryCalls }, source] = await Promise.all([
    loadTodayCareComposableModule(),
    readSource('../src/composables/useTodayCare.ts'),
  ])

  const state = module.useTodayCare()

  assert.equal(factoryCalls.length, 1)
  assert.equal(mountedCallbacks.length, 1)
  assert.equal(state.isLoading.value, false)
  assert.doesNotMatch(source, /\bfetch\s*\(/)
  assert.doesNotMatch(source, /\buseAuth\s*\(/)
  assert.doesNotMatch(source, /Notification|permission|skip|defer|background/i)
  assert.match(source, /useAuthenticatedApi/)
  assert.match(source, /createWateringApiClient/)
  assert.doesNotMatch(source, /(?<![A-Za-z0-9_$])any(?![A-Za-z0-9_$])/)
})
