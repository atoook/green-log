<script setup lang="ts">
import { ref } from 'vue'
import UpcomingCareList from '../components/watering/UpcomingCareList.vue'
import { useUpcomingCare } from '../composables/useUpcomingCare'

const {
  sections,
  isLoading,
  error,
  recordingError,
  isRecordingByPlantId,
  successMessage,
  loadUpcomingCare,
  recordWatering,
} = useUpcomingCare()

const successfulPlantId = ref<number | null>(null)

async function recordUpcomingCare(plantId: number): Promise<void> {
  successfulPlantId.value = null
  const result = await recordWatering(plantId)
  successfulPlantId.value = result?.record.plantId ?? null
}

function retryUpcomingCare(): void {
  successfulPlantId.value = null
  void loadUpcomingCare()
}
</script>

<template>
  <main class="mx-auto grid max-w-5xl gap-4 p-4">
    <section class="grid gap-2">
      <p class="text-sm font-semibold text-leaf-700">暮らしの記録</p>
      <h1 class="text-2xl font-semibold text-stone-950">今日のお世話</h1>
      <p class="max-w-2xl text-sm leading-6 text-stone-600">
        今日から明後日までの水やり予定を確認し、水やりできたらその場で記録できます。
      </p>
    </section>

    <p
      v-if="successMessage"
      class="rounded-md border border-leaf-100 bg-white p-3 text-sm font-semibold text-leaf-700"
      aria-live="polite"
    >
      {{ successMessage }}
    </p>

    <UpcomingCareList
      :sections="sections"
      :is-loading="isLoading"
      :error="error"
      :recording-error="recordingError"
      :is-recording-by-plant-id="isRecordingByPlantId"
      :successful-plant-id="successfulPlantId"
      @record="recordUpcomingCare"
      @retry="retryUpcomingCare"
    />
  </main>
</template>
