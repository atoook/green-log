<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import type { ApiError, Plant, PlantFormState, PlantUpdateInput } from '../../types/plant'
import { validatePlantUpdateForm } from '../../utils/plantFormValidation'

const props = defineProps<{
  plant: Plant
  isSaving: boolean
  serverError: ApiError | null
}>()

const emit = defineEmits<{
  submit: [input: PlantUpdateInput]
  cancel: []
}>()

const form = reactive<PlantFormState>({
  name: '',
  acquiredDate: '',
  memo: '',
  wateringCycleDays: '7',
})
const fieldError = ref<string | null>(null)

watch(
  () => props.plant,
  (plant) => {
    form.name = plant.name
    form.acquiredDate = plant.acquiredDate ?? ''
    form.memo = plant.memo ?? ''
    form.wateringCycleDays = String(plant.wateringCycleDays)
    fieldError.value = null
  },
  { immediate: true },
)

function submitForm(): void {
  const result = validatePlantUpdateForm(form)
  if (result.error || !result.input) {
    fieldError.value = result.error
    return
  }

  fieldError.value = null
  emit('submit', result.input)
}

function serverErrorMessage(error: ApiError): string {
  switch (error.type) {
    case 'auth':
      return 'ログインの有効期限が切れました。もう一度ログインしてください。'
    case 'forbidden':
      return 'この植物の記録を保存できません。ログイン中のアカウントを確認してください。'
    case 'not_found':
      return '植物が見つかりません。'
    case 'validation':
      return '入力内容を確認してください。'
    case 'network':
      return '接続できませんでした。通信環境を確認してからもう一度お試しください。'
    case 'server':
      return '植物の記録を保存できませんでした。時間をおいてもう一度お試しください。'
    default:
      return '植物の記録を保存できませんでした。時間をおいてもう一度お試しください。'
  }
}
</script>

<template>
  <form class="grid gap-4 rounded-lg border border-stone-200 bg-white p-4" @submit.prevent="submitForm">
    <div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
      <div class="min-w-0">
        <p class="text-sm font-semibold text-leaf-700">植物の記録</p>
        <h1 class="mt-1 break-words text-2xl font-semibold text-stone-950">植物情報を編集</h1>
      </div>
      <button
        class="w-full rounded-md border border-stone-200 px-4 py-2 text-sm font-semibold text-stone-700 hover:bg-stone-50 disabled:opacity-60 sm:w-auto"
        type="button"
        :disabled="isSaving"
        @click="emit('cancel')"
      >
        取り消し
      </button>
    </div>

    <div class="grid gap-3">
      <label class="grid gap-1 text-sm text-stone-700">
        植物名
        <input v-model="form.name" class="rounded-md border border-stone-200 px-3 py-2" type="text" />
      </label>
      <label class="grid gap-1 text-sm text-stone-700">
        家に来た日
        <input v-model="form.acquiredDate" class="rounded-md border border-stone-200 px-3 py-2" type="date" />
      </label>
      <label class="grid gap-1 text-sm text-stone-700">
        水やり周期
        <input v-model="form.wateringCycleDays" class="rounded-md border border-stone-200 px-3 py-2" inputmode="numeric" />
      </label>
      <label class="grid gap-1 text-sm text-stone-700">
        メモ
        <textarea v-model="form.memo" class="min-h-24 rounded-md border border-stone-200 px-3 py-2" />
      </label>
    </div>

    <p v-if="fieldError || serverError" class="text-sm text-red-700" aria-live="polite">
      {{ fieldError || (serverError ? serverErrorMessage(serverError) : '') }}
    </p>

    <button
      class="w-full rounded-md bg-leaf-600 px-4 py-2 font-semibold text-white disabled:opacity-60"
      type="submit"
      :disabled="isSaving"
    >
      {{ isSaving ? '保存しています' : '保存する' }}
    </button>
  </form>
</template>
