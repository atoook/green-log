import { onMounted, ref, watch, type Ref } from 'vue'
import { createApiError } from '../api/client'
import { createPlantsApiClient, type PlantsApiClient } from '../api/plants'
import type { ApiError, Plant, PlantUpdateInput } from '../types/plant'
import { useAuthenticatedApi } from './useAuthenticatedApi'

interface UsePlantDetailOptions {
  plantsApiClient?: PlantsApiClient
  autoLoad?: boolean
}

function shouldClearPlantOnError(error: ApiError): boolean {
  return error.type === 'auth' || error.type === 'forbidden' || error.type === 'not_found'
}

export function usePlantDetail(
  plantIdParam: Ref<string | string[]>,
  options: UsePlantDetailOptions = {},
) {
  const plantsApiClient = options.plantsApiClient ?? createPlantsApiClient(useAuthenticatedApi())
  const plant = ref<Plant | null>(null)
  const isLoading = ref(false)
  const isUpdating = ref(false)
  const error = ref<ApiError | null>(null)
  const updateError = ref<ApiError | null>(null)
  const successMessage = ref<string | null>(null)

  function parsePlantId(): number | null {
    const raw = Array.isArray(plantIdParam.value) ? plantIdParam.value[0] : plantIdParam.value
    const parsed = Number(raw)
    return Number.isInteger(parsed) && parsed > 0 ? parsed : null
  }

  async function loadPlant(): Promise<void> {
    const plantId = parsePlantId()
    successMessage.value = null
    if (plantId === null) {
      plant.value = null
      error.value = createApiError('not_found', '植物が見つかりません')
      return
    }

    isLoading.value = true
    error.value = null
    try {
      plant.value = await plantsApiClient.getPlant(plantId)
    } catch (caught) {
      plant.value = null
      error.value = caught as ApiError
    } finally {
      isLoading.value = false
    }
  }

  async function updatePlant(input: PlantUpdateInput): Promise<Plant | null> {
    if (isUpdating.value) {
      return null
    }

    updateError.value = null
    successMessage.value = null
    const plantId = parsePlantId()
    if (plantId === null) {
      updateError.value = createApiError('not_found', '植物が見つかりません')
      return null
    }

    isUpdating.value = true
    try {
      const updated = await plantsApiClient.updatePlant(plantId, input)
      plant.value = updated
      error.value = null
      successMessage.value = '植物情報を保存しました。'
      return updated
    } catch (caught) {
      const apiError = caught as ApiError
      if (shouldClearPlantOnError(apiError)) {
        plant.value = null
      }
      updateError.value = apiError
      return null
    } finally {
      isUpdating.value = false
    }
  }

  if (options.autoLoad !== false) {
    onMounted(() => {
      void loadPlant()
    })

    watch(plantIdParam, () => {
      void loadPlant()
    })
  }

  return {
    plant,
    isLoading,
    isUpdating,
    error,
    updateError,
    successMessage,
    loadPlant,
    updatePlant,
  }
}
