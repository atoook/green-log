import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { test } from 'node:test'
import ts from 'typescript'

async function readSource(path) {
  const sourceUrl = new URL(path, import.meta.url)
  return readFile(sourceUrl, 'utf8')
}

async function loadWateringHeatmapComposableModule() {
  const source = await readSource('../src/composables/useWateringHeatmap.ts')
  const { outputText } = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.ES2022,
      target: ts.ScriptTarget.ES2022,
      verbatimModuleSyntax: true,
    },
    fileName: 'useWateringHeatmap.ts',
  })

  const mountedCallbacks = []
  const factoryCalls = []
  globalThis.__wateringHeatmapVueMock = {
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
  globalThis.__wateringHeatmapWateringApiMock = {
    createWateringApiClient(apiClient) {
      factoryCalls.push(apiClient)
      return apiClient
    },
  }
  globalThis.__wateringHeatmapAuthApiMock = {
    useAuthenticatedApi() {
      return {
        async getWateringHeatmap(range) {
          return createHeatmap(range.from, range.to, [])
        },
      }
    },
  }

  const runnable = outputText
    .replace(
      /import\s+\{\s*computed,\s*onMounted,\s*ref\s*\}\s+from\s+['"]vue['"];?/,
      'const { computed, onMounted, ref } = globalThis.__wateringHeatmapVueMock;',
    )
    .replace(
      /import\s+\{\s*createWateringApiClient\s*\}\s+from\s+['"]\.\.\/api\/watering['"];?/,
      'const { createWateringApiClient } = globalThis.__wateringHeatmapWateringApiMock;',
    )
    .replace(
      /import\s+\{\s*useAuthenticatedApi\s*\}\s+from\s+['"]\.\/useAuthenticatedApi['"];?/,
      'const { useAuthenticatedApi } = globalThis.__wateringHeatmapAuthApiMock;',
    )

  assert.doesNotMatch(runnable, /^import\s/m)

  const module = await import(
    `data:text/javascript;charset=utf-8,${encodeURIComponent(`${runnable}\n// ${Date.now()}`)}`
  )

  return { module, mountedCallbacks, factoryCalls }
}

function createApiError(type, message = type) {
  return Object.assign(new Error(message), { type })
}

function createDay(date, overrides = {}) {
  return {
    date,
    plantCount: 0,
    level: 0,
    plants: [],
    ...overrides,
  }
}

function createHeatmap(startDate = '2026-03-02', endDate = '2026-05-31', days = []) {
  return {
    startDate,
    endDate,
    days,
  }
}

test('createDefaultWateringHeatmapRange builds the inclusive recent 90-day lookback range', async () => {
  const { module } = await loadWateringHeatmapComposableModule()

  const range = module.createDefaultWateringHeatmapRange(new Date(2026, 4, 31, 12))

  assert.deepEqual(range, {
    from: '2026-03-02',
    to: '2026-05-31',
  })
})

test('useWateringHeatmap loads the default range and exposes success state', async () => {
  const { module } = await loadWateringHeatmapComposableModule()
  const calls = []
  const day = createDay('2026-05-31', {
    plantCount: 2,
    level: 2,
    plants: [
      { plantId: 7, name: 'ポトス' },
      { plantId: 8, name: 'モンステラ' },
    ],
  })
  const heatmap = createHeatmap('2026-03-02', '2026-05-31', [day])
  const apiClient = {
    async getWateringHeatmap(range) {
      calls.push(range)
      return heatmap
    },
  }

  const state = module.useWateringHeatmap({
    wateringApiClient: apiClient,
    autoLoad: false,
    today: new Date(2026, 4, 31, 12),
  })

  assert.equal(state.heatmap.value, null)
  assert.deepEqual(state.days.value, [])
  assert.equal(state.isEmpty.value, false)

  const loaded = await state.loadHeatmap()

  assert.deepEqual(loaded, heatmap)
  assert.deepEqual(calls, [{ from: '2026-03-02', to: '2026-05-31' }])
  assert.deepEqual(state.heatmap.value, heatmap)
  assert.deepEqual(state.days.value, [day])
  assert.equal(state.isEmpty.value, false)
  assert.equal(state.error.value, null)
  assert.equal(state.isLoading.value, false)
})

test('useWateringHeatmap distinguishes successful empty heatmaps from initial and error states', async () => {
  const { module } = await loadWateringHeatmapComposableModule()
  const emptyHeatmap = createHeatmap('2026-03-02', '2026-05-31', [
    createDay('2026-05-30'),
    createDay('2026-05-31'),
  ])
  const apiClient = {
    async getWateringHeatmap() {
      return emptyHeatmap
    },
  }
  const state = module.useWateringHeatmap({ wateringApiClient: apiClient, autoLoad: false })

  assert.equal(state.isEmpty.value, false)

  await state.loadHeatmap()

  assert.equal(state.isEmpty.value, true)
  assert.equal(state.error.value, null)
  assert.equal(state.heatmap.value.days.length, 2)
})

test('useWateringHeatmap preserves retry data on transient load failures', async () => {
  const { module } = await loadWateringHeatmapComposableModule()
  const requestedRanges = []
  const previousHeatmap = createHeatmap('2026-03-02', '2026-05-31', [
    createDay('2026-05-31', {
      plantCount: 1,
      level: 1,
      plants: [{ plantId: 7, name: 'ポトス' }],
    }),
  ])
  const nextHeatmap = createHeatmap('2026-03-02', '2026-05-31', [
    createDay('2026-05-31', {
      plantCount: 2,
      level: 2,
      plants: [
        { plantId: 7, name: 'ポトス' },
        { plantId: 8, name: 'モンステラ' },
      ],
    }),
  ])
  const responses = [
    () => previousHeatmap,
    () => {
      throw createApiError('network')
    },
    () => nextHeatmap,
  ]
  const apiClient = {
    async getWateringHeatmap(range) {
      requestedRanges.push(range)
      return responses.shift()()
    },
  }
  const state = module.useWateringHeatmap({ wateringApiClient: apiClient, autoLoad: false })

  await state.loadHeatmap({ from: '2026-03-01', to: '2026-05-30' })
  const failed = await state.loadHeatmap({ from: '2026-03-02', to: '2026-05-31' })

  assert.equal(failed, null)
  assert.deepEqual(state.heatmap.value, previousHeatmap)
  assert.equal(state.error.value.type, 'network')

  const retried = await state.retry()

  assert.deepEqual(retried, nextHeatmap)
  assert.deepEqual(requestedRanges, [
    { from: '2026-03-01', to: '2026-05-30' },
    { from: '2026-03-02', to: '2026-05-31' },
    { from: '2026-03-02', to: '2026-05-31' },
  ])
  assert.deepEqual(state.heatmap.value, nextHeatmap)
  assert.equal(state.error.value, null)
})

test('useWateringHeatmap clears protected data on auth and forbidden load failures', async () => {
  for (const protectedErrorType of ['auth', 'forbidden']) {
    const { module } = await loadWateringHeatmapComposableModule()
    const protectedHeatmap = createHeatmap('2026-03-02', '2026-05-31', [
      createDay('2026-05-31', {
        plantCount: 1,
        level: 1,
        plants: [{ plantId: 7, name: 'ポトス' }],
      }),
    ])
    const responses = [
      () => protectedHeatmap,
      () => {
        throw createApiError(protectedErrorType)
      },
    ]
    const apiClient = {
      async getWateringHeatmap() {
        return responses.shift()()
      },
    }
    const state = module.useWateringHeatmap({ wateringApiClient: apiClient, autoLoad: false })

    await state.loadHeatmap()
    await state.loadHeatmap()

    assert.equal(state.heatmap.value, null)
    assert.deepEqual(state.days.value, [])
    assert.equal(state.isEmpty.value, false)
    assert.equal(state.error.value.type, protectedErrorType)
  }
})

test('useWateringHeatmap exposes selected date and selected day state for the heatmap UI', async () => {
  const { module } = await loadWateringHeatmapComposableModule()
  const selectedDay = createDay('2026-05-31', {
    plantCount: 1,
    level: 1,
    plants: [{ plantId: 7, name: 'ポトス' }],
  })
  const heatmap = createHeatmap('2026-03-02', '2026-05-31', [
    createDay('2026-05-30'),
    selectedDay,
  ])
  const apiClient = {
    async getWateringHeatmap() {
      return heatmap
    },
  }
  const state = module.useWateringHeatmap({ wateringApiClient: apiClient, autoLoad: false })

  await state.loadHeatmap()

  state.setSelectedDate('2026-05-31')
  assert.equal(state.selectedDate.value, '2026-05-31')
  assert.deepEqual(state.selectedDay.value, selectedDay)

  state.clearSelectedDate()
  assert.equal(state.selectedDate.value, null)
  assert.equal(state.selectedDay.value, null)
})

test('useWateringHeatmap composes the authenticated watering client and stays within the frontend boundary', async () => {
  const [{ module, mountedCallbacks, factoryCalls }, source] = await Promise.all([
    loadWateringHeatmapComposableModule(),
    readSource('../src/composables/useWateringHeatmap.ts'),
  ])

  const state = module.useWateringHeatmap()

  assert.equal(factoryCalls.length, 1)
  assert.equal(mountedCallbacks.length, 1)
  assert.equal(state.isLoading.value, false)
  assert.doesNotMatch(source, /\bfetch\s*\(/)
  assert.doesNotMatch(source, /\buseAuth\s*\(/)
  assert.doesNotMatch(source, /Notification|permission|skip|defer|background|ranking|streak/i)
  assert.match(source, /useAuthenticatedApi/)
  assert.match(source, /createWateringApiClient/)
  assert.doesNotMatch(source, /(?<![A-Za-z0-9_$])any(?![A-Za-z0-9_$])/)
})
