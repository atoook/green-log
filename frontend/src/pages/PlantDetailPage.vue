<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import PlantDetail from '../components/plants/PlantDetail.vue'
import WateringActionButton from '../components/watering/WateringActionButton.vue'
import WateringHistoryList from '../components/watering/WateringHistoryList.vue'
import WateringStatusPanel from '../components/watering/WateringStatusPanel.vue'
import { usePlantDetail } from '../composables/usePlantDetail'
import { usePlantWatering } from '../composables/usePlantWatering'

const route = useRoute()
const router = useRouter()
const plantId = computed(() => route.params.plantId)
const { plant, isLoading, error } = usePlantDetail(plantId)
const {
  watering,
  history,
  isLoading: isWateringLoading,
  isRecording,
  error: wateringError,
  recordingError,
  successMessage,
  loadWatering,
  recordWatering,
} = usePlantWatering(plantId)

const hasRecordingError = computed(() => recordingError.value !== null)
const wasWateringSuccessful = computed(() => successMessage.value !== null)
const isWateringActionDisabled = computed(() => !plant.value)

function backToList(): void {
  void router.push({ name: 'plants' })
}

async function recordPlantWatering(): Promise<void> {
  await recordWatering()
}

function retryWatering(): void {
  void loadWatering()
}
</script>

<template>
  <main class="mx-auto grid max-w-3xl gap-4 p-4">
    <PlantDetail :plant="plant" :is-loading="isLoading" :error="error" @back="backToList" />

    <section
      v-if="plant"
      class="grid gap-4 rounded-lg border border-stone-200 bg-white p-4"
      aria-labelledby="plant-watering-title"
    >
      <div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div class="min-w-0">
          <p class="text-sm font-semibold text-leaf-700">水やりの記録</p>
          <h2 id="plant-watering-title" class="break-words text-2xl font-semibold text-stone-950">
            {{ plant.name }}のお世話
          </h2>
        </div>

        <div class="w-full sm:w-auto sm:min-w-48">
          <WateringActionButton
            :is-recording="isRecording"
            :disabled="isWateringActionDisabled"
            :has-error="hasRecordingError"
            :was-successful="wasWateringSuccessful"
            @record="recordPlantWatering"
          />
        </div>
      </div>

      <p
        v-if="successMessage"
        class="rounded-md border border-leaf-100 bg-leaf-50 p-3 text-sm font-semibold text-leaf-700"
        aria-live="polite"
      >
        {{ successMessage }}
      </p>

      <WateringStatusPanel
        :watering="watering"
        :is-loading="isWateringLoading"
        :error="wateringError"
        :watering-cycle-days="plant.wateringCycleDays"
        @retry="retryWatering"
      />

      <WateringHistoryList
        :history="history"
        :is-loading="isWateringLoading"
        :error="wateringError"
        @retry="retryWatering"
      />
    </section>
  </main>
</template>
