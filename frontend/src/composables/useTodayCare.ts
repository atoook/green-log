import { computed, onMounted, ref } from 'vue'
import { createWateringApiClient, type WateringApiClient } from '../api/watering'
import type { ApiError } from '../types/api'
import type { TodayCare, TodayCareItem, WateringRecordCreateResult } from '../types/watering'
import { useAuthenticatedApi } from './useAuthenticatedApi'

interface UseTodayCareOptions {
  wateringApiClient?: WateringApiClient
  autoLoad?: boolean
}

function shouldClearTodayCareOnError(error: ApiError): boolean {
  return error.type === 'auth' || error.type === 'forbidden'
}

export function useTodayCare(options: UseTodayCareOptions = {}) {
  const wateringApiClient = options.wateringApiClient ?? createWateringApiClient(useAuthenticatedApi())
  const todayCare = ref<TodayCare | null>(null)
  const isLoading = ref(false)
  const isRecordingByPlantId = ref<Record<number, boolean>>({})
  const error = ref<ApiError | null>(null)
  const recordingError = ref<ApiError | null>(null)
  const successMessage = ref<string | null>(null)
  const items = computed<TodayCareItem[]>(() => todayCare.value?.items ?? [])
  const isEmpty = computed(() => todayCare.value !== null && todayCare.value.items.length === 0)

  async function loadTodayCare(): Promise<TodayCare | null> {
    isLoading.value = true
    error.value = null
    try {
      const loaded = await wateringApiClient.getTodayCare()
      todayCare.value = loaded
      return loaded
    } catch (caught) {
      const apiError = caught as ApiError
      if (shouldClearTodayCareOnError(apiError)) {
        todayCare.value = null
      }
      error.value = apiError
      return null
    } finally {
      isLoading.value = false
    }
  }

  async function recordWatering(plantId: number): Promise<WateringRecordCreateResult | null> {
    if (isRecordingByPlantId.value[plantId]) {
      return null
    }

    isRecordingByPlantId.value = {
      ...isRecordingByPlantId.value,
      [plantId]: true,
    }
    recordingError.value = null
    successMessage.value = null

    try {
      const result = await wateringApiClient.recordWatering(plantId)
      successMessage.value = '水やりを記録しました。'
      await loadTodayCare()
      return result
    } catch (caught) {
      const apiError = caught as ApiError
      if (shouldClearTodayCareOnError(apiError)) {
        todayCare.value = null
      }
      recordingError.value = apiError
      return null
    } finally {
      isRecordingByPlantId.value = {
        ...isRecordingByPlantId.value,
        [plantId]: false,
      }
    }
  }

  if (options.autoLoad !== false) {
    onMounted(() => {
      void loadTodayCare()
    })
  }

  return {
    todayCare,
    items,
    isEmpty,
    isLoading,
    isRecordingByPlantId,
    error,
    recordingError,
    successMessage,
    loadTodayCare,
    recordWatering,
  }
}
