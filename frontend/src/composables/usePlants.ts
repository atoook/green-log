import { onMounted, ref } from 'vue'
import { createPlantsApiClient } from '../api/plants'
import type { ApiError, Plant, PlantCreateInput } from '../types/plant'
import { useAuthenticatedApi } from './useAuthenticatedApi'

function shouldClearPlantsOnError(error: ApiError): boolean {
  return error.type === 'auth' || error.type === 'forbidden'
}

export function usePlants() {
  const plantsApiClient = createPlantsApiClient(useAuthenticatedApi())
  const plants = ref<Plant[]>([])
  const isLoadingList = ref(false)
  const isCreating = ref(false)
  const error = ref<ApiError | null>(null)

  async function loadPlants(): Promise<void> {
    isLoadingList.value = true
    error.value = null
    try {
      plants.value = await plantsApiClient.listPlants()
    } catch (caught) {
      const apiError = caught as ApiError
      if (shouldClearPlantsOnError(apiError)) {
        plants.value = []
      }
      error.value = apiError
    } finally {
      isLoadingList.value = false
    }
  }

  async function addPlant(input: PlantCreateInput): Promise<Plant | null> {
    isCreating.value = true
    error.value = null
    try {
      const created = await plantsApiClient.createPlant(input)
      plants.value = [created, ...plants.value.filter((plant) => plant.id !== created.id)]
      return created
    } catch (caught) {
      const apiError = caught as ApiError
      if (shouldClearPlantsOnError(apiError)) {
        plants.value = []
      }
      error.value = apiError
      return null
    } finally {
      isCreating.value = false
    }
  }

  onMounted(() => {
    void loadPlants()
  })

  return {
    plants,
    isLoadingList,
    isCreating,
    error,
    loadPlants,
    addPlant,
  }
}
