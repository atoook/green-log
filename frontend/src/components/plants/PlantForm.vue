<script setup lang="ts">
import { reactive, ref } from 'vue'
import type { PlantCreateInput, PlantFormState } from '../../types/plant'
import { validatePlantCreateForm } from '../../utils/plantFormValidation'

const props = defineProps<{
  isSubmitting: boolean
  serverError: string | null
}>()

const emit = defineEmits<{
  submit: [input: PlantCreateInput]
}>()

const form = reactive<PlantFormState>({
  name: '',
  acquiredDate: '',
  memo: '',
  wateringCycleDays: '7',
})

const fieldError = ref<string | null>(null)

function submitForm(): void {
  const result = validatePlantCreateForm(form)
  if (result.error || !result.input) {
    fieldError.value = result.error
    return
  }

  fieldError.value = null
  emit('submit', result.input)
}
</script>

<template>
  <form class="rounded-lg border border-leaf-100 bg-white p-4 shadow-sm" @submit.prevent="submitForm">
    <div class="mb-4">
      <p class="text-sm font-semibold text-leaf-700">植物を記録</p>
      <h1 class="mt-1 text-2xl font-semibold text-stone-950">新しい植物</h1>
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

    <p v-if="fieldError || props.serverError" class="mt-3 text-sm text-red-700">
      {{ fieldError || props.serverError }}
    </p>

    <button
      class="mt-4 w-full rounded-md bg-leaf-600 px-4 py-2 font-semibold text-white disabled:opacity-60"
      type="submit"
      :disabled="props.isSubmitting"
    >
      {{ props.isSubmitting ? '記録しています' : '植物を記録する' }}
    </button>
  </form>
</template>
