<script setup lang="ts">
import { computed } from 'vue'
import type { ApiError } from '../../types/api'
import type { WateringHeatmap, WateringHeatmapDay, WateringHeatmapLevel } from '../../types/watering'

const props = defineProps<{
  heatmap: WateringHeatmap | null
  isLoading: boolean
  error: ApiError | null
  selectedDate: string | null
  selectedDay: WateringHeatmapDay | null
}>()

const emit = defineEmits<{
  selectDate: [date: string]
  clearSelection: []
  retry: []
}>()

const heatmapLevels: WateringHeatmapLevel[] = [0, 1, 2, 3, 4]

const isEmptyHeatmap = computed(() => {
  return props.heatmap !== null && props.heatmap.days.every((day) => day.plantCount === 0)
})

const detailDay = computed<WateringHeatmapDay | null>(() => {
  if (props.selectedDay) {
    return props.selectedDay
  }

  return props.heatmap?.days.find((day) => day.plantCount > 0) ?? props.heatmap?.days[0] ?? null
})

const periodLabel = computed(() => {
  if (!props.heatmap) {
    return ''
  }

  return `${formatDate(props.heatmap.startDate)} - ${formatDate(props.heatmap.endDate)}`
})

function heatmapErrorMessage(error: ApiError): string {
  switch (error.type) {
    case 'auth':
      return 'ログインの有効期限が切れました。もう一度ログインしてください。'
    case 'forbidden':
      return '水やりヒートマップを表示できません。ログイン中のアカウントを確認してください。'
    case 'network':
      return '接続できませんでした。通信環境を確認してからもう一度お試しください。'
    case 'server':
      return '水やりヒートマップを読み込めませんでした。時間をおいてもう一度お試しください。'
    case 'not_found':
      return '水やりヒートマップを表示できません。'
    case 'validation':
      return '表示する期間を確認できませんでした。'
    default:
      return '水やりヒートマップを表示できません。時間をおいてもう一度お試しください。'
  }
}

function formatDate(value: string): string {
  const match = value.match(/^(?<year>\d{4})-(?<month>\d{2})-(?<day>\d{2})/)
  if (!match?.groups) {
    return value
  }

  return `${Number(match.groups.month)}月${Number(match.groups.day)}日`
}

function fullDateLabel(value: string): string {
  const match = value.match(/^(?<year>\d{4})-(?<month>\d{2})-(?<day>\d{2})/)
  if (!match?.groups) {
    return value
  }

  return `${Number(match.groups.year)}年${Number(match.groups.month)}月${Number(match.groups.day)}日`
}

function levelClasses(level: WateringHeatmapLevel): string[] {
  const baseClasses = [
    'h-4 w-4',
    'rounded-sm',
    'border',
    'border-white',
    'transition',
    'focus:outline-none',
    'focus:ring-2',
    'focus:ring-leaf-600',
    'focus:ring-offset-1',
  ]

  switch (level) {
    case 0:
      return [...baseClasses, 'bg-stone-100', 'hover:bg-stone-200']
    case 1:
      return [...baseClasses, 'bg-leaf-50', 'hover:bg-leaf-100']
    case 2:
      return [...baseClasses, 'bg-leaf-100', 'hover:bg-leaf-600']
    case 3:
      return [...baseClasses, 'bg-leaf-600', 'hover:bg-leaf-700']
    case 4:
      return [...baseClasses, 'bg-leaf-700', 'hover:bg-leaf-600']
    default:
      return [...baseClasses, 'bg-stone-100']
  }
}

function cellLabel(day: WateringHeatmapDay): string {
  if (day.plants.length === 0) {
    return `${fullDateLabel(day.date)}: 水やり記録はありません`
  }

  const plantNames = day.plants.map((plant) => plant.name).join('、')
  return `${fullDateLabel(day.date)}: ${plantNames}`
}

function selectDay(day: WateringHeatmapDay): void {
  emit('selectDate', day.date)
}
</script>

<template>
  <section class="grid gap-4" aria-labelledby="watering-heatmap-title">
    <div class="grid gap-1">
      <p class="text-sm font-semibold text-leaf-700">最近のお世話</p>
      <h2 id="watering-heatmap-title" class="text-xl font-semibold text-stone-950">水やりヒートマップ</h2>
    </div>

    <p v-if="isLoading" class="rounded-md bg-white p-4 text-sm text-stone-600" aria-live="polite">
      実績を読み込んでいます
    </p>

    <div v-else-if="error" class="rounded-md bg-red-50 p-4 text-sm text-red-800" aria-live="polite">
      <p>{{ heatmapErrorMessage(error) }}</p>
      <button class="mt-3 font-semibold underline" type="button" @click="emit('retry')">もう一度</button>
    </div>

    <div v-else-if="!heatmap" class="rounded-md bg-stone-50 p-4 text-sm text-stone-700">
      まだ水やりヒートマップを確認できません。植物の記録を読み込んでから表示します。
    </div>

    <div v-else class="grid gap-4">
      <div class="flex flex-wrap items-start justify-between gap-3">
        <p class="break-words text-sm font-semibold text-stone-950">{{ periodLabel }}</p>
        <ol class="flex min-w-0 items-center gap-1 text-xs text-stone-600" aria-label="実績の強さ">
          <li class="mr-1 shrink-0">実績なし</li>
          <li v-for="level in heatmapLevels" :key="level" class="shrink-0">
            <span :class="levelClasses(level)" aria-hidden="true"></span>
          </li>
          <li class="ml-1 shrink-0">多い</li>
        </ol>
      </div>

      <div v-if="isEmptyHeatmap" class="rounded-md bg-leaf-50 p-4 text-sm text-stone-700">
        <p class="font-semibold text-stone-950">水やり記録はまだありません。</p>
        <p class="mt-2 break-words">
          水やりを記録すると、この場所に毎日の実績が色で残ります。
        </p>
      </div>

      <div class="overflow-x-auto pb-2">
        <div
          class="grid min-w-max grid-flow-col grid-rows-7 gap-1"
          role="grid"
          aria-label="日別の水やり実績"
          @mouseleave="emit('clearSelection')"
        >
          <button
            v-for="day in heatmap.days"
            :key="day.date"
            :class="levelClasses(day.level)"
            :aria-label="cellLabel(day)"
            :aria-pressed="selectedDate === day.date"
            :title="cellLabel(day)"
            type="button"
            role="gridcell"
            @click="selectDay(day)"
            @focus="selectDay(day)"
            @mouseenter="selectDay(day)"
          ></button>
        </div>
      </div>

      <article v-if="detailDay" class="min-w-0 rounded-md border border-stone-200 bg-white p-4">
        <div class="grid gap-3">
          <div class="min-w-0">
            <p class="text-sm font-semibold text-leaf-700">日別詳細</p>
            <h3 class="break-words text-lg font-semibold text-stone-950">
              {{ formatDate(detailDay.date) }}
            </h3>
          </div>

          <p v-if="detailDay.plants.length === 0" class="break-words text-sm text-stone-700">
            この日の水やり記録はありません。
          </p>

          <ul v-else class="grid gap-2 text-sm text-stone-700">
            <li
              v-for="plant in detailDay.plants"
              :key="plant.plantId"
              class="min-w-0 rounded-md bg-stone-50 px-3 py-2"
            >
              <span class="break-words font-semibold text-stone-950">{{ plant.name }}</span>
            </li>
          </ul>
        </div>
      </article>
    </div>
  </section>
</template>
