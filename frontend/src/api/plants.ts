import type { AuthenticatedApiClient } from '../types/api'
import type { Plant, PlantCreateInput } from '../types/plant'

export interface PlantsApiClient {
  listPlants(): Promise<Plant[]>
  createPlant(input: PlantCreateInput): Promise<Plant>
  getPlant(id: number): Promise<Plant>
}

export function createPlantsApiClient(apiClient: AuthenticatedApiClient): PlantsApiClient {
  return {
    listPlants(): Promise<Plant[]> {
      return apiClient.request<Plant[]>('/plants')
    },

    createPlant(input: PlantCreateInput): Promise<Plant> {
      return apiClient.request<Plant>('/plants', {
        method: 'POST',
        body: JSON.stringify(input),
      })
    },

    getPlant(id: number): Promise<Plant> {
      return apiClient.request<Plant>(`/plants/${id}`)
    },
  }
}
