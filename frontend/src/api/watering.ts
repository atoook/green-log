import type { AuthenticatedApiClient } from '../types/api'
import type {
  PlantWateringDetail,
  UpcomingCare,
  WateringHeatmap,
  WateringHeatmapRange,
  WateringRecordCreateResult,
} from '../types/watering'

export interface WateringApiClient {
  getUpcomingCare(days?: number): Promise<UpcomingCare>
  getPlantWatering(plantId: number): Promise<PlantWateringDetail>
  recordWatering(plantId: number): Promise<WateringRecordCreateResult>
  getWateringHeatmap(range: WateringHeatmapRange): Promise<WateringHeatmap>
}

export function createWateringApiClient(apiClient: AuthenticatedApiClient): WateringApiClient {
  return {
    getUpcomingCare(days?: number): Promise<UpcomingCare> {
      if (days === undefined) {
        return apiClient.request<UpcomingCare>('/care/upcoming')
      }

      const params = new URLSearchParams({ days: String(days) })
      return apiClient.request<UpcomingCare>(`/care/upcoming?${params.toString()}`)
    },

    getPlantWatering(plantId: number): Promise<PlantWateringDetail> {
      return apiClient.request<PlantWateringDetail>(`/plants/${plantId}/watering`)
    },

    recordWatering(plantId: number): Promise<WateringRecordCreateResult> {
      return apiClient.request<WateringRecordCreateResult>(`/plants/${plantId}/watering-records`, {
        method: 'POST',
        body: JSON.stringify({}),
      })
    },

    getWateringHeatmap(range: WateringHeatmapRange): Promise<WateringHeatmap> {
      const params = new URLSearchParams({
        from: range.from,
        to: range.to,
      })

      return apiClient.request<WateringHeatmap>(`/care/watering-heatmap?${params.toString()}`)
    },
  }
}
