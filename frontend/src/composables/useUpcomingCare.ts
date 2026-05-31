import { computed, onMounted, ref } from 'vue'
import { createWateringApiClient, type WateringApiClient } from '../api/watering'
import type { ApiError } from '../types/api'
import type { UpcomingCare, UpcomingCareItem, WateringRecordCreateResult } from '../types/watering'
import { useAuthenticatedApi } from './useAuthenticatedApi'

const DEFAULT_UPCOMING_CARE_DAYS = 3

interface UseUpcomingCareOptions {
  wateringApiClient?: WateringApiClient
  autoLoad?: boolean
  days?: number
}

function shouldClearUpcomingCareOnError(error: ApiError): boolean {
  return error.type === 'auth' || error.type === 'forbidden'
}

export function useUpcomingCare(options: UseUpcomingCareOptions = {}) {
  const wateringApiClient = options.wateringApiClient ?? createWateringApiClient(useAuthenticatedApi())
  const days = options.days ?? DEFAULT_UPCOMING_CARE_DAYS
  const upcomingCare = ref<UpcomingCare | null>(null)
  const isLoading = ref(false)
  const isRecordingByPlantId = ref<Record<number, boolean>>({})
  const error = ref<ApiError | null>(null)
  const recordingError = ref<ApiError | null>(null)
  const successMessage = ref<string | null>(null)
  const sections = computed(() => upcomingCare.value?.sections ?? [])
  const items = computed<UpcomingCareItem[]>(() => sections.value.flatMap((section) => section.items))
  const isEmpty = computed(() => upcomingCare.value !== null && items.value.length === 0)

  async function loadUpcomingCare(): Promise<UpcomingCare | null> {
    isLoading.value = true
    error.value = null
    try {
      const loaded = await wateringApiClient.getUpcomingCare(days)
      upcomingCare.value = loaded
      return loaded
    } catch (caught) {
      const apiError = caught as ApiError
      if (shouldClearUpcomingCareOnError(apiError)) {
        upcomingCare.value = null
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
      await loadUpcomingCare()
      return result
    } catch (caught) {
      const apiError = caught as ApiError
      if (shouldClearUpcomingCareOnError(apiError)) {
        upcomingCare.value = null
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
      void loadUpcomingCare()
    })
  }

  return {
    upcomingCare,
    sections,
    items,
    isEmpty,
    isLoading,
    isRecordingByPlantId,
    error,
    recordingError,
    successMessage,
    loadUpcomingCare,
    recordWatering,
  }
}
