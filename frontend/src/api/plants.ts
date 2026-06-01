import type { AuthenticatedApiClient } from '../types/api'
import type { Plant, PlantCreateInput, PlantUpdateInput } from '../types/plant'

export interface PlantsApiClient {
  listPlants(): Promise<Plant[]>
  createPlant(input: PlantCreateInput): Promise<Plant>
  getPlant(id: number): Promise<Plant>
  updatePlant(id: number, input: PlantUpdateInput): Promise<Plant>
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

    updatePlant(id: number, input: PlantUpdateInput): Promise<Plant> {
      return apiClient.request<Plant>(`/plants/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(input),
      })
    },
  }
}
