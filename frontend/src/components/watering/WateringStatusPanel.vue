<script setup lang="ts">
import { computed } from 'vue'
import type { ApiError } from '../../types/api'
import type { PlantWateringDetail } from '../../types/watering'

const props = defineProps<{
  watering: PlantWateringDetail | null
  isLoading: boolean
  error: ApiError | null
  wateringCycleDays?: number
}>()

const emit = defineEmits<{
  retry: []
}>()

type StatusTone = 'unrecorded' | 'due' | 'overdue' | 'not-due'

const frequencyCopy = computed(() => {
  if (props.wateringCycleDays && props.wateringCycleDays > 0) {
    return `${props.wateringCycleDays}日ごとの水やり頻度から算出しています。`
  }

  return '登録した水やり頻度から算出しています。'
})

function statusErrorMessage(error: ApiError): string {
  switch (error.type) {
    case 'auth':
      return 'ログインの有効期限が切れました。もう一度ログインしてください。'
    case 'forbidden':
      return 'この植物の水やり状態は利用できません。ログイン中のアカウントを確認してください。'
    case 'network':
      return '接続できませんでした。通信環境を確認してからもう一度お試しください。'
    case 'server':
      return '水やり状態を読み込めませんでした。時間をおいてもう一度お試しください。'
    case 'not_found':
      return '植物の水やり状態を表示できません。対象の植物を利用できません。'
    case 'validation':
      return '水やり状態を確認できませんでした。'
    default:
      return '水やり状態を表示できません。時間をおいてもう一度お試しください。'
  }
}

function formatDate(value: string | null): string {
  if (!value) {
    return '未確定'
  }

  const match = value.match(/^(?<year>\d{4})-(?<month>\d{2})-(?<day>\d{2})/)
  if (!match?.groups) {
    return value
  }

  return `${Number(match.groups.year)}年${Number(match.groups.month)}月${Number(match.groups.day)}日`
}

function formatDateTime(value: string | null): string {
  if (!value) {
    return '未記録'
  }

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }

  return new Intl.DateTimeFormat('ja-JP', {
    year: 'numeric',
    month: 'numeric',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

function statusTone(watering: PlantWateringDetail): StatusTone {
  switch (watering.dueStatus) {
    case 'unrecorded':
      return 'unrecorded'
    case 'due_today':
      return 'due'
    case 'overdue':
      return 'overdue'
    default:
      return watering.isDueToday ? 'due' : 'not-due'
  }
}

function statusLabel(watering: PlantWateringDetail): string {
  switch (watering.dueStatus) {
    case 'unrecorded':
      return '未記録'
    case 'due_today':
      return '今日水やりが必要'
    case 'overdue':
      return '予定日を過ぎています'
    default:
      return watering.isDueToday ? '今日水やりが必要' : 'まだ水やりは不要'
  }
}

function statusHelp(watering: PlantWateringDetail): string {
  switch (watering.dueStatus) {
    case 'unrecorded':
      return `最初の水やりを記録すると、次回予定日が表示されます。${frequencyCopy.value}`
    case 'due_today':
      return `今日が次回予定日です。土の乾き具合を見ながらお世話しましょう。${frequencyCopy.value}`
    case 'overdue':
      return `次回予定日を過ぎています。植物の様子を見て、早めに水やりを確認しましょう。${frequencyCopy.value}`
    default:
      if (watering.isDueToday) {
        return `今日が次回予定日です。水やりできたら記録しましょう。${frequencyCopy.value}`
      }

      return `次回予定日まで見守れます。${frequencyCopy.value}`
  }
}

function statusCardClasses(watering: PlantWateringDetail): string[] {
  const baseClasses = ['rounded-md', 'border', 'p-4', 'grid', 'gap-4']
  const tone = statusTone(watering)

  if (tone === 'unrecorded') {
    return [...baseClasses, 'border-amber-200', 'bg-amber-50', 'text-amber-800']
  }
  if (tone === 'due') {
    return [...baseClasses, 'border-leaf-200', 'bg-leaf-50', 'text-leaf-700']
  }
  if (tone === 'overdue') {
    return [...baseClasses, 'border-red-200', 'bg-red-50', 'text-red-700']
  }

  return [...baseClasses, 'border-sky-200', 'bg-sky-50', 'text-sky-700']
}

function statusBadgeClasses(watering: PlantWateringDetail): string[] {
  const baseClasses = ['inline-flex', 'w-fit', 'rounded-md', 'px-2.5', 'py-1', 'text-xs', 'font-semibold']
  const tone = statusTone(watering)

  if (tone === 'unrecorded') {
    return [...baseClasses, 'bg-amber-100', 'text-amber-800']
  }
  if (tone === 'due') {
    return [...baseClasses, 'bg-leaf-100', 'text-leaf-700']
  }
  if (tone === 'overdue') {
    return [...baseClasses, 'bg-red-100', 'text-red-700']
  }

  return [...baseClasses, 'bg-sky-100', 'text-sky-700']
}
</script>

<template>
  <section class="grid gap-4" aria-labelledby="watering-status-title">
    <div class="grid gap-1">
      <p class="text-sm font-semibold text-leaf-700">水やり状態</p>
      <h2 id="watering-status-title" class="text-xl font-semibold text-stone-950">次の水やり目安</h2>
    </div>

    <p v-if="isLoading" class="rounded-md bg-white p-4 text-sm text-stone-600" aria-live="polite">
      水やり状態を読み込んでいます
    </p>

    <div v-else-if="error" class="rounded-md bg-red-50 p-4 text-sm text-red-800" aria-live="polite">
      <p>{{ statusErrorMessage(error) }}</p>
      <button class="mt-3 font-semibold underline" type="button" @click="emit('retry')">もう一度</button>
    </div>

    <div v-else-if="!watering" class="rounded-md bg-stone-50 p-4 text-sm text-stone-700">
      まだ水やり状態を確認できません。植物の記録を読み込んでから表示します。
    </div>

    <article v-else :class="statusCardClasses(watering)" :data-status="statusTone(watering)">
      <div class="flex flex-wrap items-start justify-between gap-2">
        <div class="min-w-0">
          <p class="text-sm font-semibold">水やりの目安</p>
          <h3 class="break-words text-lg font-semibold text-stone-950">{{ statusLabel(watering) }}</h3>
        </div>
        <span :class="statusBadgeClasses(watering)">{{ statusLabel(watering) }}</span>
      </div>

      <p class="break-words text-sm text-stone-700">{{ statusHelp(watering) }}</p>

      <dl class="grid gap-3 text-sm text-stone-700 sm:grid-cols-2">
        <div class="min-w-0 rounded-md bg-white/75 p-3">
          <dt class="font-semibold text-stone-950">最新の水やり</dt>
          <dd class="break-words">{{ formatDateTime(watering.lastWateredAt) }}</dd>
        </div>
        <div class="min-w-0 rounded-md bg-white/75 p-3">
          <dt class="font-semibold text-stone-950">次回予定日</dt>
          <dd class="break-words">{{ formatDate(watering.nextWateringDate) }}</dd>
          <dd class="mt-1 break-words text-xs text-stone-600">{{ frequencyCopy }}</dd>
        </div>
      </dl>
    </article>
  </section>
</template>
