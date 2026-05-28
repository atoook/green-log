import { onMounted, ref, watch, type Ref } from 'vue'
import { getPlant } from '../api/plants'
import type { ApiError, Plant } from '../types/plant'

export function usePlantDetail(plantIdParam: Ref<string | string[]>) {
  const plant = ref<Plant | null>(null)
  const isLoading = ref(false)
  const error = ref<ApiError | null>(null)

  function parsePlantId(): number | null {
    const raw = Array.isArray(plantIdParam.value) ? plantIdParam.value[0] : plantIdParam.value
    const parsed = Number(raw)
    return Number.isInteger(parsed) && parsed > 0 ? parsed : null
  }

  async function loadPlant(): Promise<void> {
    const plantId = parsePlantId()
    if (plantId === null) {
      plant.value = null
      error.value = { type: 'not_found', message: '植物が見つかりません' }
      return
    }

    isLoading.value = true
    error.value = null
    try {
      plant.value = await getPlant(plantId)
    } catch (caught) {
      plant.value = null
      error.value = caught as ApiError
    } finally {
      isLoading.value = false
    }
  }

  onMounted(() => {
    void loadPlant()
  })

  watch(plantIdParam, () => {
    void loadPlant()
  })

  return {
    plant,
    isLoading,
    error,
    loadPlant,
  }
}
