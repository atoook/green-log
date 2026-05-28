<script setup lang="ts">
import { ref } from 'vue'
import type { ApiError, Plant } from '../../types/plant'

defineProps<{
  plants: Plant[]
  isLoading: boolean
  error: ApiError | null
}>()

const emit = defineEmits<{
  select: [plantId: number]
  retry: []
}>()

const brokenImageIds = ref<Set<number>>(new Set())

function markImageBroken(plantId: number): void {
  brokenImageIds.value = new Set([...brokenImageIds.value, plantId])
}
</script>

<template>
  <section class="rounded-lg border border-stone-200 bg-white p-4">
    <div class="mb-4 flex items-center justify-between gap-3">
      <div>
        <p class="text-sm font-semibold text-leaf-700">植物一覧</p>
        <h2 class="text-xl font-semibold text-stone-950">育てている植物</h2>
      </div>
      <button class="text-sm font-semibold text-leaf-700" type="button" @click="emit('retry')">再読み込み</button>
    </div>

    <p v-if="isLoading" class="text-sm text-stone-600">読み込んでいます</p>

    <div v-else-if="error" class="rounded-md bg-red-50 p-3 text-sm text-red-800">
      一覧を表示できませんでした。
      <button class="ml-2 font-semibold underline" type="button" @click="emit('retry')">もう一度</button>
    </div>

    <div v-else-if="plants.length === 0" class="rounded-md bg-leaf-50 p-5 text-sm text-stone-700">
      まだ植物の記録がありません。最初の鉢を記録してみましょう。
    </div>

    <ul v-else class="grid gap-3">
      <li v-for="plant in plants" :key="plant.id">
        <button
          class="grid w-full grid-cols-[64px_1fr] items-center gap-3 rounded-md border border-stone-200 p-2 text-left hover:border-leaf-600"
          type="button"
          @click="emit('select', plant.id)"
        >
          <img
            v-if="plant.imageUrl && !brokenImageIds.has(plant.id)"
            class="h-16 w-16 rounded-md object-cover"
            :src="plant.imageUrl"
            :alt="plant.name"
            @error="markImageBroken(plant.id)"
          />
          <span v-else class="flex h-16 w-16 items-center justify-center rounded-md bg-soil-100 text-sm text-soil-700">
            記録
          </span>
          <span>
            <span class="block font-semibold text-stone-950">{{ plant.name }}</span>
            <span class="block text-sm text-stone-600">{{ plant.wateringCycleDays }}日ごとにお世話</span>
          </span>
        </button>
      </li>
    </ul>
  </section>
</template>
