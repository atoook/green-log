import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { test } from 'node:test'
import ts from 'typescript'

async function readSource(path) {
  const sourceUrl = new URL(path, import.meta.url)
  return readFile(sourceUrl, 'utf8')
}

async function loadPlantWateringComposableModule() {
  const source = await readSource('../src/composables/usePlantWatering.ts')
  const { outputText } = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.ES2022,
      target: ts.ScriptTarget.ES2022,
      verbatimModuleSyntax: true,
    },
    fileName: 'usePlantWatering.ts',
  })

  const mountedCallbacks = []
  const watchedRefs = []
  const factoryCalls = []
  globalThis.__plantWateringVueMock = {
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
    watch(sourceRef, callback) {
      watchedRefs.push(sourceRef)
      return callback
    },
  }
  globalThis.__plantWateringApiErrorMock = {
    createApiError,
  }
  globalThis.__plantWateringWateringApiMock = {
    createWateringApiClient(apiClient) {
      factoryCalls.push(apiClient)
      return apiClient
    },
  }
  globalThis.__plantWateringAuthApiMock = {
    useAuthenticatedApi() {
      return {
        async getPlantWatering(plantId) {
          return createPlantWateringDetail({ plantId })
        },
        async recordWatering() {
          throw createApiError('server')
        },
      }
    },
  }

  const runnable = outputText
    .replace(
      /import\s+\{\s*computed,\s*onMounted,\s*ref,\s*watch\s*\}\s+from\s+['"]vue['"];?/,
      'const { computed, onMounted, ref, watch } = globalThis.__plantWateringVueMock;',
    )
    .replace(
      /import\s+\{\s*createApiError\s*\}\s+from\s+['"]\.\.\/api\/client['"];?/,
      'const { createApiError } = globalThis.__plantWateringApiErrorMock;',
    )
    .replace(
      /import\s+\{\s*createWateringApiClient\s*\}\s+from\s+['"]\.\.\/api\/watering['"];?/,
      'const { createWateringApiClient } = globalThis.__plantWateringWateringApiMock;',
    )
    .replace(
      /import\s+\{\s*useAuthenticatedApi\s*\}\s+from\s+['"]\.\/useAuthenticatedApi['"];?/,
      'const { useAuthenticatedApi } = globalThis.__plantWateringAuthApiMock;',
    )

  assert.doesNotMatch(runnable, /^import\s/m)

  const module = await import(
    `data:text/javascript;charset=utf-8,${encodeURIComponent(`${runnable}\n// ${Date.now()}`)}`
  )

  return { module, mountedCallbacks, watchedRefs, factoryCalls }
}

function createApiError(type, message = type) {
  return Object.assign(new Error(message), { type })
}

function createRecord(id, wateredAt) {
  return {
    id,
    plantId: 7,
    wateredAt,
    createdAt: wateredAt,
  }
}

function createPlantWateringDetail(overrides = {}) {
  return {
    plantId: 7,
    lastWateredAt: '2026-05-30T00:00:00Z',
    nextWateringDate: '2026-06-06',
    isDueToday: false,
    dueStatus: null,
    history: [
      createRecord(20, '2026-05-30T00:00:00Z'),
      createRecord(19, '2026-05-23T00:00:00Z'),
    ],
    ...overrides,
  }
}

test('usePlantWatering loads watering detail and exposes newest-first history separately', async () => {
  const { module } = await loadPlantWateringComposableModule()
  const plantIdParam = { value: '7' }
  const detail = createPlantWateringDetail()
  const calls = []
  const apiClient = {
    async getPlantWatering(plantId) {
      calls.push(`getPlantWatering:${plantId}`)
      return detail
    },
    async recordWatering() {
      throw createApiError('server')
    },
  }

  const state = module.usePlantWatering(plantIdParam, { wateringApiClient: apiClient, autoLoad: false })

  assert.equal(state.watering.value, null)
  assert.deepEqual(state.history.value, [])

  const loaded = await state.loadWatering()

  assert.deepEqual(loaded, detail)
  assert.deepEqual(calls, ['getPlantWatering:7'])
  assert.deepEqual(state.watering.value, detail)
  assert.deepEqual(state.history.value, detail.history)
  assert.equal(state.error.value, null)
  assert.equal(state.isLoading.value, false)
})

test('usePlantWatering validates plant id before requesting detail', async () => {
  const { module } = await loadPlantWateringComposableModule()
  const calls = []
  const apiClient = {
    async getPlantWatering(plantId) {
      calls.push(`getPlantWatering:${plantId}`)
      return createPlantWateringDetail({ plantId })
    },
    async recordWatering() {
      throw createApiError('server')
    },
  }

  const state = module.usePlantWatering({ value: ['not-a-number'] }, {
    wateringApiClient: apiClient,
    autoLoad: false,
  })
  const loaded = await state.loadWatering()

  assert.equal(loaded, null)
  assert.deepEqual(calls, [])
  assert.equal(state.watering.value, null)
  assert.equal(state.error.value.type, 'not_found')
  assert.equal(state.isLoading.value, false)
})

test('usePlantWatering clears protected and unavailable data but preserves retry data on transient load failures', async () => {
  for (const clearingErrorType of ['auth', 'forbidden', 'not_found']) {
    const { module } = await loadPlantWateringComposableModule()
    const previousDetail = createPlantWateringDetail()
    const responses = [
      () => previousDetail,
      () => {
        throw createApiError('network')
      },
      () => {
        throw createApiError(clearingErrorType)
      },
    ]
    const apiClient = {
      async getPlantWatering() {
        return responses.shift()()
      },
      async recordWatering() {
        throw createApiError('server')
      },
    }
    const state = module.usePlantWatering({ value: '7' }, { wateringApiClient: apiClient, autoLoad: false })

    await state.loadWatering()
    await state.loadWatering()

    assert.deepEqual(state.watering.value, previousDetail)
    assert.equal(state.error.value.type, 'network')

    await state.loadWatering()

    assert.equal(state.watering.value, null)
    assert.equal(state.error.value.type, clearingErrorType)
  }
})

test('usePlantWatering records watering once while pending and applies response state', async () => {
  const { module } = await loadPlantWateringComposableModule()
  const calls = []
  let resolveRecord
  const recordPromise = new Promise((resolve) => {
    resolveRecord = resolve
  })
  const initialDetail = createPlantWateringDetail({
    lastWateredAt: '2026-05-23T00:00:00Z',
    nextWateringDate: '2026-05-30',
    isDueToday: true,
    dueStatus: 'due_today',
    history: [createRecord(19, '2026-05-23T00:00:00Z')],
  })
  const updatedDetail = createPlantWateringDetail()
  const createResult = {
    record: updatedDetail.history[0],
    state: updatedDetail,
  }
  const apiClient = {
    async getPlantWatering() {
      return initialDetail
    },
    async recordWatering(plantId) {
      calls.push(`recordWatering:${plantId}`)
      return recordPromise
    },
  }
  const state = module.usePlantWatering({ value: '7' }, { wateringApiClient: apiClient, autoLoad: false })

  await state.loadWatering()

  const resultPromise = state.recordWatering()
  const duplicateResult = await state.recordWatering()

  assert.equal(duplicateResult, null)
  assert.deepEqual(calls, ['recordWatering:7'])
  assert.equal(state.isRecording.value, true)

  resolveRecord(createResult)
  const result = await resultPromise

  assert.deepEqual(result, createResult)
  assert.deepEqual(state.watering.value, updatedDetail)
  assert.deepEqual(state.history.value, updatedDetail.history)
  assert.equal(state.watering.value.lastWateredAt, '2026-05-30T00:00:00Z')
  assert.equal(state.watering.value.nextWateringDate, '2026-06-06')
  assert.equal(state.recordingError.value, null)
  assert.equal(state.successMessage.value, '水やりを記録しました。')
  assert.equal(state.isRecording.value, false)
})

test('usePlantWatering keeps record failures distinct from detail load failures', async () => {
  const { module } = await loadPlantWateringComposableModule()
  const loadedDetail = createPlantWateringDetail()
  const apiClient = {
    async getPlantWatering() {
      return loadedDetail
    },
    async recordWatering() {
      throw createApiError('network')
    },
  }
  const state = module.usePlantWatering({ value: '7' }, { wateringApiClient: apiClient, autoLoad: false })

  await state.loadWatering()
  const result = await state.recordWatering()

  assert.equal(result, null)
  assert.deepEqual(state.watering.value, loadedDetail)
  assert.equal(state.error.value, null)
  assert.equal(state.recordingError.value.type, 'network')
  assert.equal(state.successMessage.value, null)
  assert.equal(state.isRecording.value, false)
})

test('usePlantWatering clears protected data on unavailable record failures', async () => {
  for (const clearingErrorType of ['auth', 'forbidden', 'not_found']) {
    const { module } = await loadPlantWateringComposableModule()
    const loadedDetail = createPlantWateringDetail()
    const apiClient = {
      async getPlantWatering() {
        return loadedDetail
      },
      async recordWatering() {
        throw createApiError(clearingErrorType)
      },
    }
    const state = module.usePlantWatering({ value: '7' }, { wateringApiClient: apiClient, autoLoad: false })

    await state.loadWatering()
    await state.recordWatering()

    assert.equal(state.watering.value, null)
    assert.equal(state.history.value.length, 0)
    assert.equal(state.recordingError.value.type, clearingErrorType)
  }
})

test('usePlantWatering composes authenticated client and stays inside watering detail boundary', async () => {
  const [{ module, mountedCallbacks, watchedRefs, factoryCalls }, source] = await Promise.all([
    loadPlantWateringComposableModule(),
    readSource('../src/composables/usePlantWatering.ts'),
  ])

  const state = module.usePlantWatering({ value: '7' })

  assert.equal(factoryCalls.length, 1)
  assert.equal(mountedCallbacks.length, 1)
  assert.equal(watchedRefs.length, 1)
  assert.equal(state.isLoading.value, false)
  assert.doesNotMatch(source, /\bfetch\s*\(/)
  assert.doesNotMatch(source, /\buseAuth\s*\(/)
  assert.doesNotMatch(source, /createPlantsApiClient|usePlantDetail|plant\.value/)
  assert.doesNotMatch(source, /Notification|permission|skip|defer|background/i)
  assert.match(source, /useAuthenticatedApi/)
  assert.match(source, /createWateringApiClient/)
  assert.doesNotMatch(source, /(?<![A-Za-z0-9_$])any(?![A-Za-z0-9_$])/)
})
