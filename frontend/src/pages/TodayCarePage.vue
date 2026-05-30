<script setup lang="ts">
import { ref } from 'vue'
import TodayCareList from '../components/watering/TodayCareList.vue'
import { useTodayCare } from '../composables/useTodayCare'

const {
  items,
  isLoading,
  error,
  recordingError,
  isRecordingByPlantId,
  successMessage,
  loadTodayCare,
  recordWatering,
} = useTodayCare()

const successfulPlantId = ref<number | null>(null)

async function recordTodayCare(plantId: number): Promise<void> {
  successfulPlantId.value = null
  const result = await recordWatering(plantId)
  successfulPlantId.value = result?.record.plantId ?? null
}

function retryTodayCare(): void {
  successfulPlantId.value = null
  void loadTodayCare()
}
</script>

<template>
  <main class="mx-auto grid max-w-5xl gap-4 p-4">
    <section class="grid gap-2">
      <p class="text-sm font-semibold text-leaf-700">暮らしの記録</p>
      <h1 class="text-2xl font-semibold text-stone-950">今日のお世話</h1>
      <p class="max-w-2xl text-sm leading-6 text-stone-600">
        今日水やりが必要な植物を確認し、水やりできたらその場で記録できます。
      </p>
    </section>

    <p
      v-if="successMessage"
      class="rounded-md border border-leaf-100 bg-white p-3 text-sm font-semibold text-leaf-700"
      aria-live="polite"
    >
      {{ successMessage }}
    </p>

    <TodayCareList
      :items="items"
      :is-loading="isLoading"
      :error="error"
      :recording-error="recordingError"
      :is-recording-by-plant-id="isRecordingByPlantId"
      :successful-plant-id="successfulPlantId"
      @record="recordTodayCare"
      @retry="retryTodayCare"
    />
  </main>
</template>
