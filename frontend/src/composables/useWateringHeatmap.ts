import { computed, onMounted, ref } from 'vue'
import { createWateringApiClient, type WateringApiClient } from '../api/watering'
import type { ApiError } from '../types/api'
import type { WateringHeatmap, WateringHeatmapDay, WateringHeatmapRange } from '../types/watering'
import { useAuthenticatedApi } from './useAuthenticatedApi'

const DEFAULT_HEATMAP_LOOKBACK_DAYS = 90
const APP_TIME_ZONE = 'Asia/Tokyo'

interface UseWateringHeatmapOptions {
  wateringApiClient?: WateringApiClient
  autoLoad?: boolean
  today?: Date
}

function shouldClearHeatmapOnError(error: ApiError): boolean {
  return error.type === 'auth' || error.type === 'forbidden'
}

function getAppDateParts(date: Date): { year: number; month: number; day: number } {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: APP_TIME_ZONE,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).formatToParts(date)
  const values = Object.fromEntries(parts.map((part) => [part.type, part.value]))

  return {
    year: Number(values.year),
    month: Number(values.month),
    day: Number(values.day),
  }
}

function formatAppDate(date: Date): string {
  const { year, month, day } = getAppDateParts(date)
  return `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`
}

function shiftAppDate(date: Date, days: number): Date {
  const { year, month, day } = getAppDateParts(date)
  return new Date(Date.UTC(year, month - 1, day + days))
}

export function createDefaultWateringHeatmapRange(today: Date = new Date()): WateringHeatmapRange {
  return {
    from: formatAppDate(shiftAppDate(today, -DEFAULT_HEATMAP_LOOKBACK_DAYS)),
    to: formatAppDate(today),
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
