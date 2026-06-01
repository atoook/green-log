import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { createSSRApp, effectScope, ref } from 'vue'
import { renderToString } from '@vue/server-renderer'
import { createServer } from 'vite'

const server = await createServer({
  appType: 'custom',
  logLevel: 'silent',
  server: { middlewareMode: true, hmr: false },
})

try {
  const [
    plantDetailModule,
    plantEditFormModule,
    plantValidationModule,
    plantDetailComposableModule,
  ] = await Promise.all([
    server.ssrLoadModule('/src/components/plants/PlantDetail.vue'),
    server.ssrLoadModule('/src/components/plants/PlantEditForm.vue'),
    server.ssrLoadModule('/src/utils/plantFormValidation.ts'),
    server.ssrLoadModule('/src/composables/usePlantDetail.ts'),
  ])

  const samplePlant = {
    id: 42,
    name: '窓辺のポトス',
    acquiredDate: '2026-05-28',
    memo: '明るい窓辺',
    imageUrl: null,
    wateringCycleDays: 7,
    createdAt: '2026-05-28T00:00:00Z',
    updatedAt: '2026-05-28T00:00:00Z',
  }

  await verifyDetailEditEntry(plantDetailModule.default, samplePlant)
  await verifyEditFormStates(plantEditFormModule.default, samplePlant)
  verifyValidation(plantValidationModule)
  await verifyDetailComposable(plantDetailComposableModule.usePlantDetail, samplePlant)
  await verifyPageIntegration()
} finally {
  await server.close()
}

console.log('OK plant edit flow verification')

async function renderComponent(component, props) {
  return renderToString(createSSRApp(component, props))
}

async function verifyDetailEditEntry(PlantDetail, samplePlant) {
  const loaded = await renderComponent(PlantDetail, {
    plant: samplePlant,
    isLoading: false,
    error: null,
  })
  assert.match(loaded, /編集/)
  assert.match(loaded, /窓辺のポトス/)

  const loading = await renderComponent(PlantDetail, {
    plant: null,
    isLoading: true,
    error: null,
  })
  assert.doesNotMatch(loading, /編集/)

  const error = await renderComponent(PlantDetail, {
    plant: null,
    isLoading: false,
    error: apiError('not_found'),
  })
  assert.doesNotMatch(error, /編集/)
}

async function verifyEditFormStates(PlantEditForm, samplePlant) {
  const idle = await renderComponent(PlantEditForm, {
    plant: samplePlant,
    isSaving: false,
    serverError: null,
  })
  for (const expectedText of [
    '植物情報を編集',
    '植物名',
    '家に来た日',
    '水やり周期',
    'メモ',
    '取り消し',
    '保存する',
  ]) {
    assert.match(idle, new RegExp(expectedText))
  }
  for (const outOfScopeText of ['種類', 'species', 'ownerUserId', 'owner_user_id']) {
    assert.doesNotMatch(idle, new RegExp(outOfScopeText))
  }

  const saving = await renderComponent(PlantEditForm, {
    plant: samplePlant,
    isSaving: true,
    serverError: null,
  })
  assert.match(saving, /保存しています/)
  assert.match(saving, /disabled/)

  const failed = await renderComponent(PlantEditForm, {
    plant: samplePlant,
    isSaving: false,
    serverError: apiError('network'),
  })
  assert.match(failed, /接続できませんでした/)
}

function verifyValidation(module) {
  const valid = module.validatePlantUpdateForm({
    name: '  棚のポトス  ',
    acquiredDate: '2026-06-01',
    memo: '  ',
    wateringCycleDays: '10',
  })
  assert.deepEqual(valid, {
    input: {
      name: '棚のポトス',
      acquiredDate: '2026-06-01',
      memo: null,
      wateringCycleDays: 10,
    },
    error: null,
  })

  assert.match(
    module.validatePlantUpdateForm({
      name: '',
      acquiredDate: '',
      memo: '',
      wateringCycleDays: '7',
    }).error,
    /植物名/,
  )
  assert.match(
    module.validatePlantUpdateForm({
      name: 'ポトス',
      acquiredDate: '2026-02-31',
      memo: '',
      wateringCycleDays: '7',
    }).error,
    /日付/,
  )
  assert.match(
    module.validatePlantUpdateForm({
      name: 'ポトス',
      acquiredDate: '',
      memo: '',
      wateringCycleDays: '0',
    }).error,
    /水やり周期/,
  )
  assert.match(
    module.validatePlantUpdateForm({
      name: 'ポトス',
      acquiredDate: '',
      memo: '',
      wateringCycleDays: '99999999',
    }).error,
    /99日以内/,
  )
}

async function verifyDetailComposable(usePlantDetail, samplePlant) {
  const updatedPlant = {
    ...samplePlant,
    name: '更新後のポトス',
    memo: null,
    wateringCycleDays: 10,
    updatedAt: '2026-06-01T00:00:00Z',
  }
  const plantId = ref('42')
  const successful = effectScope().run(() =>
    usePlantDetail(plantId, {
      autoLoad: false,
      plantsApiClient: {
        listPlants: async () => [],
        createPlant: async () => samplePlant,
        getPlant: async () => samplePlant,
        updatePlant: async () => updatedPlant,
      },
    }),
  )
  successful.plant.value = samplePlant
  const result = await successful.updatePlant({
    name: updatedPlant.name,
    memo: null,
    wateringCycleDays: 10,
  })
  assert.equal(result.name, updatedPlant.name)
  assert.equal(successful.plant.value.name, updatedPlant.name)
  assert.equal(successful.successMessage.value, '植物情報を保存しました。')
  assert.equal(successful.updateError.value, null)

  const failed = effectScope().run(() =>
    usePlantDetail(plantId, {
      autoLoad: false,
      plantsApiClient: {
        listPlants: async () => [],
        createPlant: async () => samplePlant,
        getPlant: async () => samplePlant,
        updatePlant: async () => {
          throw apiError('validation')
        },
      },
    }),
  )
  failed.plant.value = samplePlant
  const failedResult = await failed.updatePlant({ name: '' })
  assert.equal(failedResult, null)
  assert.equal(failed.plant.value.name, samplePlant.name)
  assert.equal(failed.updateError.value.type, 'validation')
}

async function verifyPageIntegration() {
  const source = await readFile(new URL('../src/pages/PlantDetailPage.vue', import.meta.url), 'utf8')
  assert.match(source, /v-if="plant && isEditing"/)
  assert.match(source, /@edit="startEditing"/)
  assert.match(source, /@submit="savePlant"/)
  assert.match(source, /@cancel="cancelEditing"/)
  assert.match(source, /const updated = await updatePlant\(input\)/)
  assert.match(source, /isEditing\.value = false/)
  assert.match(source, /await loadWatering\(\)/)
  assert.doesNotMatch(source, /recordWatering\(input/)
}

function apiError(type) {
  return Object.assign(new Error(type), { name: 'ApiError', type })
}
