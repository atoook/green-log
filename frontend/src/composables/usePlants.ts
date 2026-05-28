import { onMounted, ref } from 'vue'
import { createPlant, listPlants } from '../api/plants'
import type { ApiError, Plant, PlantCreateInput } from '../types/plant'

export function usePlants() {
  const plants = ref<Plant[]>([])
  const isLoadingList = ref(false)
  const isCreating = ref(false)
  const error = ref<ApiError | null>(null)

  async function loadPlants(): Promise<void> {
    isLoadingList.value = true
    error.value = null
    try {
      plants.value = await listPlants()
    } catch (caught) {
      error.value = caught as ApiError
    } finally {
      isLoadingList.value = false
    }
  }

  async function addPlant(input: PlantCreateInput): Promise<Plant | null> {
    isCreating.value = true
    error.value = null
    try {
      const created = await createPlant(input)
      plants.value = [created, ...plants.value.filter((plant) => plant.id !== created.id)]
      return created
    } catch (caught) {
      error.value = caught as ApiError
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
