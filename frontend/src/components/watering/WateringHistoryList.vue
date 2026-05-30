<script setup lang="ts">
import type { ApiError } from '../../types/api'
import type { WateringRecord } from '../../types/watering'

defineProps<{
  history: WateringRecord[]
  isLoading: boolean
  error: ApiError | null
}>()

const emit = defineEmits<{
  retry: []
}>()

function historyErrorMessage(error: ApiError): string {
  switch (error.type) {
    case 'auth':
      return 'ログインの有効期限が切れました。もう一度ログインしてください。'
    case 'forbidden':
      return 'この植物の水やり履歴は利用できません。ログイン中のアカウントを確認してください。'
    case 'network':
      return '接続できませんでした。通信環境を確認してからもう一度お試しください。'
    case 'server':
      return '水やり履歴を読み込めませんでした。時間をおいてもう一度お試しください。'
    case 'not_found':
      return '水やり履歴を表示できません。対象の植物を利用できません。'
    case 'validation':
      return '水やり履歴を確認できませんでした。'
    default:
      return '水やり履歴を表示できません。時間をおいてもう一度お試しください。'
  }
}

function formatDateTime(value: string): string {
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
</script>

<template>
  <section class="grid gap-4" aria-labelledby="watering-history-title">
    <div class="grid gap-1">
      <p class="text-sm font-semibold text-leaf-700">水やり履歴</p>
      <h2 id="watering-history-title" class="text-xl font-semibold text-stone-950">これまでの水やり</h2>
    </div>

    <p v-if="isLoading" class="rounded-md bg-white p-4 text-sm text-stone-600" aria-live="polite">
      履歴を読み込んでいます
    </p>

    <div v-else-if="error" class="rounded-md bg-red-50 p-4 text-sm text-red-800" aria-live="polite">
      <p>{{ historyErrorMessage(error) }}</p>
      <button class="mt-3 font-semibold underline" type="button" @click="emit('retry')">もう一度</button>
    </div>

    <div v-else-if="history.length === 0" class="rounded-md bg-stone-50 p-5 text-sm text-stone-700">
      <p class="font-semibold text-stone-950">水やり履歴はまだありません。</p>
      <p class="mt-2 break-words">
        水やりを記録すると、この植物のお世話を日時で振り返れます。
      </p>
    </div>

    <ul v-else class="grid gap-3">
      <li v-for="(record, index) in history" :key="record.id" class="rounded-md border border-stone-200 bg-white p-4">
        <article class="grid grid-cols-[auto_minmax(0,1fr)] gap-3">
          <div class="mt-1 h-2.5 w-2.5 rounded-full bg-leaf-500" aria-hidden="true"></div>
          <div class="min-w-0 grid gap-2">
            <div class="flex flex-wrap items-start justify-between gap-2">
              <p class="text-sm font-semibold text-stone-950">記録日時</p>
              <span
                v-if="index === 0"
                class="inline-flex w-fit rounded-md bg-leaf-50 px-2.5 py-1 text-xs font-semibold text-leaf-700"
              >
                最新の記録
              </span>
            </div>
            <p class="break-words text-sm text-stone-700">{{ formatDateTime(record.wateredAt) }}</p>
          </div>
        </article>
      </li>
    </ul>
  </section>
</template>
