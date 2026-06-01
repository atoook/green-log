<script setup lang="ts">
import type { ApiError, Plant } from '../../types/plant'

defineProps<{
  plant: Plant | null
  isLoading: boolean
  error: ApiError | null
}>()

const emit = defineEmits<{
  back: []
  edit: []
}>()

function detailErrorMessage(error: ApiError): string {
  switch (error.type) {
    case 'auth':
      return 'ログインの有効期限が切れました。もう一度ログインしてください。'
    case 'forbidden':
      return 'この植物の記録を表示できません。ログイン中のアカウントを確認してください。'
    case 'not_found':
      return '植物が見つかりません。'
    case 'validation':
      return '植物の指定を確認してください。'
    case 'network':
      return '接続できませんでした。通信環境を確認してからもう一度お試しください。'
    case 'server':
      return '植物の記録を読み込めませんでした。時間をおいてもう一度お試しください。'
    default:
      return '植物の記録を表示できませんでした。時間をおいてもう一度お試しください。'
  }
}
</script>

<template>
  <section class="rounded-lg border border-stone-200 bg-white p-4">
    <button class="mb-4 text-sm font-semibold text-leaf-700" type="button" @click="emit('back')">
      一覧へ戻る
    </button>

    <p v-if="isLoading" class="text-sm text-stone-600">読み込んでいます</p>

    <div v-else-if="error" class="rounded-md bg-red-50 p-4 text-sm text-red-800">
      {{ detailErrorMessage(error) }}
    </div>

    <article v-else-if="plant" class="grid gap-4">
      <img
        v-if="plant.imageUrl"
        class="aspect-[4/3] w-full rounded-md object-cover"
        :src="plant.imageUrl"
        :alt="plant.name"
      />
      <div v-else class="flex aspect-[4/3] w-full items-center justify-center rounded-md bg-leaf-50 text-leaf-700">
        植物の写真はまだありません
      </div>

      <div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div class="min-w-0">
          <p class="text-sm font-semibold text-leaf-700">植物の記録</p>
          <h1 class="mt-1 break-words text-3xl font-semibold text-stone-950">{{ plant.name }}</h1>
        </div>
        <button
          class="w-full rounded-md border border-leaf-200 px-4 py-2 text-sm font-semibold text-leaf-700 hover:bg-leaf-50 sm:w-auto"
          type="button"
          @click="emit('edit')"
        >
          編集
        </button>
      </div>

      <dl class="grid gap-3 text-sm">
        <div class="rounded-md bg-stone-50 p-3">
          <dt class="font-semibold text-stone-950">家に来た日</dt>
          <dd class="text-stone-700">{{ plant.acquiredDate || '未記録' }}</dd>
        </div>
        <div class="rounded-md bg-stone-50 p-3">
          <dt class="font-semibold text-stone-950">水やり周期</dt>
          <dd class="text-stone-700">{{ plant.wateringCycleDays }}日ごと</dd>
        </div>
        <div class="rounded-md bg-stone-50 p-3">
          <dt class="font-semibold text-stone-950">メモ</dt>
          <dd class="whitespace-pre-wrap text-stone-700">{{ plant.memo || '未記録' }}</dd>
        </div>
      </dl>
    </article>
  </section>
</template>
