import { computed, onMounted, ref, watch, type Ref } from 'vue'
import { createApiError } from '../api/client'
import { createWateringApiClient, type WateringApiClient } from '../api/watering'
import type { ApiError } from '../types/api'
import type { PlantWateringDetail, WateringRecord, WateringRecordCreateResult } from '../types/watering'
import { useAuthenticatedApi } from './useAuthenticatedApi'

interface UsePlantWateringOptions {
  wateringApiClient?: WateringApiClient
  autoLoad?: boolean
}

function shouldClearWateringOnError(error: ApiError): boolean {
  return error.type === 'auth' || error.type === 'forbidden' || error.type === 'not_found'
}

export function usePlantWatering(
  plantIdParam: Ref<string | string[]>,
  options: UsePlantWateringOptions = {},
) {
  const wateringApiClient = options.wateringApiClient ?? createWateringApiClient(useAuthenticatedApi())
  const watering = ref<PlantWateringDetail | null>(null)
  const isLoading = ref(false)
  const isRecording = ref(false)
  const error = ref<ApiError | null>(null)
  const recordingError = ref<ApiError | null>(null)
  const successMessage = ref<string | null>(null)
  const history = computed<WateringRecord[]>(() => watering.value?.history ?? [])
  const hasWateredToday = computed(() => watering.value?.hasWateredToday ?? false)

  function parsePlantId(): number | null {
    const raw = Array.isArray(plantIdParam.value) ? plantIdParam.value[0] : plantIdParam.value
    const parsed = Number(raw)
    return Number.isInteger(parsed) && parsed > 0 ? parsed : null
  }

  function createNotFoundError(): ApiError {
    return createApiError('not_found', '水やり状態が見つかりません')
  }

  async function loadWatering(): Promise<PlantWateringDetail | null> {
    const plantId = parsePlantId()
    successMessage.value = null
    if (plantId === null) {
      watering.value = null
      error.value = createNotFoundError()
      return null
    }

    isLoading.value = true
    error.value = null
    try {
      const loaded = await wateringApiClient.getPlantWatering(plantId)
      watering.value = loaded
      return loaded
    } catch (caught) {
      const apiError = caught as ApiError
      if (shouldClearWateringOnError(apiError)) {
        watering.value = null
      }
      error.value = apiError
      return null
    } finally {
      isLoading.value = false
    }
  }

  async function recordWatering(): Promise<WateringRecordCreateResult | null> {
    if (isRecording.value || hasWateredToday.value) {
      return null
    }

    recordingError.value = null
    successMessage.value = null
    const plantId = parsePlantId()
    if (plantId === null) {
      watering.value = null
      recordingError.value = createNotFoundError()
      return null
    }

    isRecording.value = true

    try {
      const result = await wateringApiClient.recordWatering(plantId)
      watering.value = result.state
      error.value = null
      successMessage.value = '水やりを記録しました。'
      return result
    } catch (caught) {
      const apiError = caught as ApiError
      if (shouldClearWateringOnError(apiError)) {
        watering.value = null
      }
      recordingError.value = apiError
      return null
    } finally {
      isRecording.value = false
    }
  }

  if (options.autoLoad !== false) {
    onMounted(() => {
      void loadWatering()
    })

    watch(plantIdParam, () => {
      void loadWatering()
    })
  }

  return {
    watering,
    history,
    hasWateredToday,
    isLoading,
    isRecording,
    error,
    recordingError,
    successMessage,
    loadWatering,
    recordWatering,
  }
}
