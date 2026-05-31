import { computed, onMounted, ref } from 'vue'
import { createWateringApiClient, type WateringApiClient } from '../api/watering'
import type { ApiError } from '../types/api'
import type { WateringHeatmap, WateringHeatmapDay, WateringHeatmapRange } from '../types/watering'
import { useAuthenticatedApi } from './useAuthenticatedApi'

const DEFAULT_HEATMAP_LOOKBACK_DAYS = 90

interface UseWateringHeatmapOptions {
  wateringApiClient?: WateringApiClient
  autoLoad?: boolean
  today?: Date
}

function shouldClearHeatmapOnError(error: ApiError): boolean {
  return error.type === 'auth' || error.type === 'forbidden'
}

function formatLocalDate(date: Date): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function shiftLocalDate(date: Date, days: number): Date {
  const shifted = new Date(date.getFullYear(), date.getMonth(), date.getDate())
  shifted.setDate(shifted.getDate() + days)
  return shifted
}

export function createDefaultWateringHeatmapRange(today: Date = new Date()): WateringHeatmapRange {
  return {
    from: formatLocalDate(shiftLocalDate(today, -DEFAULT_HEATMAP_LOOKBACK_DAYS)),
    to: formatLocalDate(today),
  }
}

export function useWateringHeatmap(options: UseWateringHeatmapOptions = {}) {
  const wateringApiClient = options.wateringApiClient ?? createWateringApiClient(useAuthenticatedApi())
  const heatmap = ref<WateringHeatmap | null>(null)
  const isLoading = ref(false)
  const error = ref<ApiError | null>(null)
  const selectedDate = ref<string | null>(null)
  const lastRequestedRange = ref<WateringHeatmapRange>(createDefaultWateringHeatmapRange(options.today))
  const days = computed<WateringHeatmapDay[]>(() => heatmap.value?.days ?? [])
  const isEmpty = computed(
    () => heatmap.value !== null && heatmap.value.days.every((day) => day.plantCount === 0),
  )
  const selectedDay = computed<WateringHeatmapDay | null>(() => {
    if (selectedDate.value === null) {
      return null
    }

    return days.value.find((day) => day.date === selectedDate.value) ?? null
  })

  async function loadHeatmap(range: WateringHeatmapRange = lastRequestedRange.value): Promise<WateringHeatmap | null> {
    lastRequestedRange.value = range
    isLoading.value = true
    error.value = null
    try {
      const loaded = await wateringApiClient.getWateringHeatmap(range)
      heatmap.value = loaded
      return loaded
    } catch (caught) {
      const apiError = caught as ApiError
      if (shouldClearHeatmapOnError(apiError)) {
        heatmap.value = null
        selectedDate.value = null
      }
      error.value = apiError
      return null
    } finally {
      isLoading.value = false
    }
  }

  function retry(): Promise<WateringHeatmap | null> {
    return loadHeatmap(lastRequestedRange.value)
  }

  function setSelectedDate(date: string | null): void {
    selectedDate.value = date
  }

  function clearSelectedDate(): void {
    selectedDate.value = null
  }

  if (options.autoLoad !== false) {
    onMounted(() => {
      void loadHeatmap()
    })
  }

  return {
    heatmap,
    days,
    isEmpty,
    isLoading,
    error,
    selectedDate,
    selectedDay,
    loadHeatmap,
    retry,
    setSelectedDate,
    clearSelectedDate,
  }
}
