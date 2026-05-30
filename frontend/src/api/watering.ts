import type { AuthenticatedApiClient } from '../types/api'
import type {
  PlantWateringDetail,
  TodayCare,
  WateringRecordCreateResult,
} from '../types/watering'

export interface WateringApiClient {
  getTodayCare(): Promise<TodayCare>
  getPlantWatering(plantId: number): Promise<PlantWateringDetail>
  recordWatering(plantId: number): Promise<WateringRecordCreateResult>
}

export function createWateringApiClient(apiClient: AuthenticatedApiClient): WateringApiClient {
  return {
    getTodayCare(): Promise<TodayCare> {
      return apiClient.request<TodayCare>('/care/today')
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
  }
}
