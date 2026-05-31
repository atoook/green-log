<script setup lang="ts">
import { computed, onActivated, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import PlantForm from '../components/plants/PlantForm.vue'
import PlantList from '../components/plants/PlantList.vue'
import WateringHeatmap from '../components/watering/WateringHeatmap.vue'
import { usePlants } from '../composables/usePlants'
import { useWateringHeatmap } from '../composables/useWateringHeatmap'
import type { PlantCreateInput } from '../types/plant'

const router = useRouter()
const { plants, isLoadingList, isCreating, error, loadPlants, addPlant } = usePlants()
const {
  heatmap,
  isLoading: isLoadingHeatmap,
  error: heatmapError,
  selectedDate,
  selectedDay,
  loadHeatmap,
  retry: retryHeatmap,
  setSelectedDate,
  clearSelectedDate,
} = useWateringHeatmap({ autoLoad: false })

const serverError = computed(() => (error.value?.type === 'validation' ? error.value.message : null))

async function refreshHeatmap(): Promise<void> {
  await loadHeatmap()
}

onMounted(() => {
  void refreshHeatmap()
})

onActivated(() => {
  void refreshHeatmap()
})

async function submitPlant(input: PlantCreateInput): Promise<void> {
  const created = await addPlant(input)
  if (created) {
    await router.push({ name: 'plant-detail', params: { plantId: String(created.id) } })
  }
}

function selectPlant(plantId: number): void {
  void router.push({ name: 'plant-detail', params: { plantId: String(plantId) } })
}
</script>

<template>
  <main class="mx-auto grid max-w-5xl gap-4 p-4">
    <section class="grid gap-4 md:col-span-2">
      <WateringHeatmap
        :heatmap="heatmap"
        :is-loading="isLoadingHeatmap"
        :error="heatmapError"
        :selected-date="selectedDate"
        :selected-day="selectedDay"
        @select-date="setSelectedDate"
        @clear-selection="clearSelectedDate"
        @retry="retryHeatmap"
      />
    </section>

    <div class="grid gap-4 md:grid-cols-[360px_1fr]">
      <PlantForm :is-submitting="isCreating" :server-error="serverError" @submit="submitPlant" />
      <PlantList
        :plants="plants"
        :is-loading="isLoadingList"
        :error="error?.type === 'validation' ? null : error"
        @select="selectPlant"
        @retry="loadPlants"
      />
    </div>
  </main>
</template>
