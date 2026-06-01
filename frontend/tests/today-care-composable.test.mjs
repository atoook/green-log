import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { test } from 'node:test'
import ts from 'typescript'

async function readSource(path) {
  const sourceUrl = new URL(path, import.meta.url)
  return readFile(sourceUrl, 'utf8')
}

async function loadUpcomingCareComposableModule() {
  const source = await readSource('../src/composables/useUpcomingCare.ts')
  const { outputText } = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.ES2022,
      target: ts.ScriptTarget.ES2022,
      verbatimModuleSyntax: true,
    },
    fileName: 'useUpcomingCare.ts',
  })

  const mountedCallbacks = []
  const factoryCalls = []
  globalThis.__upcomingCareVueMock = {
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
  globalThis.__upcomingCareWateringApiMock = {
    createWateringApiClient(apiClient) {
      factoryCalls.push(apiClient)
      return apiClient
    },
  }
  globalThis.__upcomingCareAuthApiMock = {
    useAuthenticatedApi() {
      return {
        async getUpcomingCare(days) {
          return createUpcomingCare([], days)
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
      'const { computed, onMounted, ref } = globalThis.__upcomingCareVueMock;',
    )
    .replace(
      /import\s+\{\s*createWateringApiClient\s*\}\s+from\s+['"]\.\.\/api\/watering['"];?/,
      'const { createWateringApiClient } = globalThis.__upcomingCareWateringApiMock;',
    )
    .replace(
      /import\s+\{\s*useAuthenticatedApi\s*\}\s+from\s+['"]\.\/useAuthenticatedApi['"];?/,
      'const { useAuthenticatedApi } = globalThis.__upcomingCareAuthApiMock;',
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

function createUpcomingCare(items = [], days = 3) {
  return {
    startDate: '2026-05-30',
    days,
    sections: [
      {
        date: '2026-05-30',
        kind: 'today',
        items,
      },
      {
        date: '2026-05-31',
        kind: 'tomorrow',
        items: [],
      },
      {
        date: '2026-06-01',
        kind: 'day_after_tomorrow',
        items: [],
      },
    ].slice(0, days),
  }
}

function createCareItem(plantId = 7) {
  return {
    plantId,
    lastWateredAt: null,
    nextWateringDate: null,
    isDueToday: true,
    hasWateredToday: false,
    dueStatus: 'unrecorded',
    plant: {
      id: plantId,
      name: 'ポトス',
      imageUrl: null,
      wateringCycleDays: 7,
    },
  }
}

test('useUpcomingCare loads upcoming care and exposes empty state separately from errors', async () => {
  const { module } = await loadUpcomingCareComposableModule()
  const calls = []
  const apiClient = {
    async getUpcomingCare(days) {
      calls.push(`getUpcomingCare:${days}`)
      return createUpcomingCare([])
    },
    async recordWatering() {
      throw createApiError('server')
    },
  }

  const state = module.useUpcomingCare({ wateringApiClient: apiClient, autoLoad: false })

  assert.equal(state.upcomingCare.value, null)
  assert.equal(state.sections.value.length, 0)
  assert.equal(state.items.value.length, 0)
  assert.equal(state.isEmpty.value, false)

  await state.loadUpcomingCare()

  assert.deepEqual(calls, ['getUpcomingCare:3'])
  assert.deepEqual(state.upcomingCare.value, createUpcomingCare([]))
  assert.deepEqual(state.sections.value, createUpcomingCare([]).sections)
  assert.deepEqual(state.items.value, [])
  assert.equal(state.isEmpty.value, true)
  assert.equal(state.error.value, null)
  assert.equal(state.isLoading.value, false)
})

test('useUpcomingCare clears protected data on auth and forbidden load failures only', async () => {
  for (const protectedErrorType of ['auth', 'forbidden']) {
    const { module } = await loadUpcomingCareComposableModule()
    const protectedCare = createUpcomingCare([createCareItem()])
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
      async getUpcomingCare() {
        return responses.shift()()
      },
      async recordWatering() {
        throw createApiError('server')
      },
    }
    const state = module.useUpcomingCare({ wateringApiClient: apiClient, autoLoad: false })

    await state.loadUpcomingCare()
    await state.loadUpcomingCare()

    assert.deepEqual(state.upcomingCare.value, protectedCare)
    assert.equal(state.error.value.type, 'network')

    await state.loadUpcomingCare()

    assert.equal(state.upcomingCare.value, null)
    assert.equal(state.error.value.type, protectedErrorType)
  }
})

test('useUpcomingCare records watering with per-plant recording state and refetches upcoming care', async () => {
  const { module } = await loadUpcomingCareComposableModule()
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
      hasWateredToday: true,
      dueStatus: null,
      history: [],
    },
  }
  const apiClient = {
    async getUpcomingCare(days) {
      calls.push(`getUpcomingCare:${days}`)
      return createUpcomingCare([])
    },
    async recordWatering(plantId) {
      calls.push(`recordWatering:${plantId}`)
      return recordPromise
    },
  }
  const state = module.useUpcomingCare({ wateringApiClient: apiClient, autoLoad: false })

  const resultPromise = state.recordWatering(7)

  assert.equal(state.isRecordingByPlantId.value[7], true)

  resolveRecord(createResult)
  const result = await resultPromise

  assert.deepEqual(result, createResult)
  assert.deepEqual(calls, ['recordWatering:7', 'getUpcomingCare:3'])
  assert.equal(state.isRecordingByPlantId.value[7], false)
  assert.equal(state.recordingError.value, null)
  assert.equal(state.successMessage.value, '水やりを記録しました。')
  assert.equal(state.isEmpty.value, true)
})

test('useUpcomingCare ignores duplicate watering submits for the same plant while pending', async () => {
  const { module } = await loadUpcomingCareComposableModule()
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
      hasWateredToday: true,
      dueStatus: null,
      history: [],
    },
  }
  const apiClient = {
    async getUpcomingCare(days) {
      calls.push(`getUpcomingCare:${days}`)
      return createUpcomingCare([])
    },
    async recordWatering(plantId) {
      calls.push(`recordWatering:${plantId}`)
      return recordPromise
    },
  }
  const state = module.useUpcomingCare({ wateringApiClient: apiClient, autoLoad: false })

  const firstResultPromise = state.recordWatering(7)
  const duplicateResult = await state.recordWatering(7)

  assert.equal(duplicateResult, null)
  assert.deepEqual(calls, ['recordWatering:7'])
  assert.equal(state.isRecordingByPlantId.value[7], true)

  resolveRecord(createResult)
  const firstResult = await firstResultPromise

  assert.deepEqual(firstResult, createResult)
  assert.deepEqual(calls, ['recordWatering:7', 'getUpcomingCare:3'])
  assert.equal(state.isRecordingByPlantId.value[7], false)
})

test('useUpcomingCare keeps record failures distinct from load failures and preserves retry data', async () => {
  const { module } = await loadUpcomingCareComposableModule()
  const protectedCare = createUpcomingCare([createCareItem()])
  const apiClient = {
    async getUpcomingCare() {
      return protectedCare
    },
    async recordWatering() {
      throw createApiError('network')
    },
  }
  const state = module.useUpcomingCare({ wateringApiClient: apiClient, autoLoad: false })

  await state.loadUpcomingCare()
  const result = await state.recordWatering(7)

  assert.equal(result, null)
  assert.deepEqual(state.upcomingCare.value, protectedCare)
  assert.equal(state.error.value, null)
  assert.equal(state.recordingError.value.type, 'network')
  assert.equal(state.successMessage.value, null)
  assert.equal(state.isRecordingByPlantId.value[7], false)
})

test('useUpcomingCare clears protected data on auth or forbidden record failures', async () => {
  const { module } = await loadUpcomingCareComposableModule()
  const protectedCare = createUpcomingCare([createCareItem()])
  const apiClient = {
    async getUpcomingCare() {
      return protectedCare
    },
    async recordWatering() {
      throw createApiError('forbidden')
    },
  }
  const state = module.useUpcomingCare({ wateringApiClient: apiClient, autoLoad: false })

  await state.loadUpcomingCare()
  await state.recordWatering(7)

  assert.equal(state.upcomingCare.value, null)
  assert.equal(state.recordingError.value.type, 'forbidden')
})

test('useUpcomingCare composes the authenticated watering client and stays within the frontend boundary', async () => {
  const [{ module, mountedCallbacks, factoryCalls }, source] = await Promise.all([
    loadUpcomingCareComposableModule(),
    readSource('../src/composables/useUpcomingCare.ts'),
  ])

  const state = module.useUpcomingCare()

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
