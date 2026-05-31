<script setup lang="ts">
import type { ApiError } from '../../types/api'
import type { UpcomingCareItem, UpcomingCareSection } from '../../types/watering'
import WateringActionButton from './WateringActionButton.vue'

withDefaults(
  defineProps<{
    sections: UpcomingCareSection[]
    isLoading: boolean
    error: ApiError | null
    recordingError: ApiError | null
    isRecordingByPlantId: Record<number, boolean>
    successfulPlantId?: number | null
  }>(),
  {
    successfulPlantId: null,
  },
)

const emit = defineEmits<{
  record: [plantId: number]
  retry: []
}>()

function careErrorMessage(error: ApiError): string {
  switch (error.type) {
    case 'auth':
      return 'ログインの有効期限が切れました。もう一度ログインしてください。'
    case 'forbidden':
      return '今日のお世話を表示できません。ログイン中のアカウントを確認してください。'
    case 'network':
      return '接続できませんでした。通信環境を確認してからもう一度お試しください。'
    case 'server':
      return '今日のお世話を読み込めませんでした。時間をおいてもう一度お試しください。'
    case 'not_found':
      return '今日のお世話が見つかりませんでした。'
    case 'validation':
      return '表示する内容を確認できませんでした。'
    default:
      return '今日のお世話を表示できませんでした。時間をおいてもう一度お試しください。'
  }
}

function recordingErrorMessage(error: ApiError): string {
  switch (error.type) {
    case 'auth':
      return '記録できませんでした。もう一度ログインしてからお試しください。'
    case 'forbidden':
      return '記録できませんでした。この植物を利用できるか確認してください。'
    case 'network':
      return '記録できませんでした。接続を確認してからもう一度お試しください。'
    case 'server':
      return '記録できませんでした。時間をおいてもう一度お試しください。'
    case 'not_found':
      return '記録できませんでした。対象の植物を利用できません。'
    case 'validation':
      return '記録できませんでした。操作をもう一度確認してください。'
    default:
      return '記録できませんでした。もう一度お試しください。'
  }
}

function dueStatusLabel(item: UpcomingCareItem): string {
  switch (item.dueStatus) {
    case 'unrecorded':
      return '未記録'
    case 'overdue':
      return '予定日を過ぎています'
    case 'due_today':
      return '今日がお世話の日'
    default:
      return '予定を確認'
  }
}

function dueStatusHelp(item: UpcomingCareItem): string {
  switch (item.dueStatus) {
    case 'unrecorded':
      return 'まだ水やり記録がありません。今日の水やりから始めましょう。'
    case 'overdue':
      return '次回予定日を過ぎています。土の乾き具合を見て、今日の水やりを確認しましょう。'
    case 'due_today':
      return '今日が次回予定日です。水やりできたら記録しましょう。'
    default:
      return '次回予定日が近づいています。水やりできたら記録しましょう。'
  }
}

function dueStatusClasses(item: UpcomingCareItem): string[] {
  const baseClasses = [
    'inline-flex',
    'w-fit',
    'rounded-md',
    'px-2.5',
    'py-1',
    'text-xs',
    'font-semibold',
  ]

  if (item.dueStatus === 'overdue') {
    return [...baseClasses, 'bg-red-50', 'text-red-700']
  }
  if (item.dueStatus === 'unrecorded') {
    return [...baseClasses, 'bg-amber-50', 'text-amber-800']
  }
  return [...baseClasses, 'bg-leaf-50', 'text-leaf-700']
}

function formatDate(value: string): string {
  const match = value.match(/^(?<year>\d{4})-(?<month>\d{2})-(?<day>\d{2})/)
  if (!match?.groups) {
    return value
  }

  return `${Number(match.groups.month)}月${Number(match.groups.day)}日`
}

function sectionTitle(section: UpcomingCareSection): string {
  switch (section.kind) {
    case 'today':
      return '今日のお世話'
    case 'tomorrow':
      return '明日のお世話'
    case 'day_after_tomorrow':
      return '明後日のお世話'
    default:
      return `${formatDate(section.date)}のお世話`
  }
}

function sectionEmptyMessage(section: UpcomingCareSection): string {
  if (section.kind === 'today') {
    return '今日必要な水やりはありません。'
  }

  return 'この日に必要な水やりはありません。'
}

function lastWateredLabel(item: UpcomingCareItem): string {
  if (!item.lastWateredAt) {
    return 'まだ水やり記録がありません'
  }

  return `${formatDate(item.lastWateredAt)}に記録`
}

function nextWateringLabel(item: UpcomingCareItem): string {
  if (!item.nextWateringDate) {
    return '未確定'
  }

  return formatDate(item.nextWateringDate)
}
</script>

<template>
  <section class="grid gap-4" aria-labelledby="upcoming-care-title">
    <div class="grid gap-1">
      <p class="text-sm font-semibold text-leaf-700">直近のお世話</p>
      <h2 id="upcoming-care-title" class="text-xl font-semibold text-stone-950">水やり予定</h2>
    </div>

    <p v-if="isLoading" class="rounded-md bg-white p-4 text-sm text-stone-600" aria-live="polite">
      読み込んでいます
    </p>

    <div v-else-if="error" class="rounded-md bg-red-50 p-4 text-sm text-red-800" aria-live="polite">
      <p>{{ careErrorMessage(error) }}</p>
      <button class="mt-3 font-semibold underline" type="button" @click="emit('retry')">もう一度</button>
    </div>

    <div v-else class="grid gap-3">
      <div v-if="recordingError" class="rounded-md bg-red-50 p-3 text-sm text-red-800" aria-live="polite">
        {{ recordingErrorMessage(recordingError) }}
      </div>

      <section
        v-for="section in sections"
        :key="section.date"
        class="grid gap-3 rounded-md border border-stone-200 bg-white p-4"
      >
        <div class="flex flex-wrap items-baseline justify-between gap-2">
          <h3 class="text-lg font-semibold text-stone-950">{{ sectionTitle(section) }}</h3>
          <p class="text-sm font-semibold text-stone-500">{{ formatDate(section.date) }}</p>
        </div>

        <div v-if="section.items.length === 0" class="rounded-md bg-leaf-50 p-4 text-sm text-stone-700">
          <p class="font-semibold text-stone-950">{{ sectionEmptyMessage(section) }}</p>
          <p class="mt-2">
            新しい植物を登録したら、ここで水やり予定を確認できます。植物を登録して暮らしの記録を増やしましょう。
          </p>
        </div>

        <ul v-else class="grid gap-3">
          <li
            v-for="item in section.items"
            :key="`${section.date}-${item.plantId}`"
            class="rounded-md border border-stone-200 bg-stone-50 p-4"
          >
            <article class="grid gap-3 md:grid-cols-[minmax(0,1fr)_auto] md:items-start">
              <div class="min-w-0 grid gap-3">
                <div class="flex flex-wrap items-start justify-between gap-2">
                  <div class="min-w-0">
                    <p class="text-sm font-semibold text-leaf-700">{{ sectionTitle(section) }}</p>
                    <h4 class="break-words text-lg font-semibold text-stone-950">{{ item.plant.name }}</h4>
                  </div>
                  <span :class="dueStatusClasses(item)">{{ dueStatusLabel(item) }}</span>
                </div>

                <dl class="grid gap-2 text-sm text-stone-700 sm:grid-cols-3">
                  <div class="min-w-0 rounded-md bg-white p-3">
                    <dt class="font-semibold text-stone-950">水やりの目安</dt>
                    <dd>{{ item.plant.wateringCycleDays }}日ごと</dd>
                  </div>
                  <div class="min-w-0 rounded-md bg-white p-3">
                    <dt class="font-semibold text-stone-950">最新の水やり</dt>
                    <dd>{{ lastWateredLabel(item) }}</dd>
                  </div>
                  <div class="min-w-0 rounded-md bg-white p-3">
                    <dt class="font-semibold text-stone-950">次回予定日</dt>
                    <dd>{{ nextWateringLabel(item) }}</dd>
                  </div>
                </dl>

                <p class="break-words text-sm text-stone-600">{{ dueStatusHelp(item) }}</p>
              </div>

              <div class="w-full md:w-auto md:min-w-44">
                <WateringActionButton
                  :is-recording="Boolean(isRecordingByPlantId[item.plantId])"
                  :has-error="Boolean(recordingError)"
                  :was-successful="successfulPlantId === item.plantId"
                  @record="emit('record', item.plantId)"
                />
              </div>
            </article>
          </li>
        </ul>
      </section>
    </div>
  </section>
</template>
