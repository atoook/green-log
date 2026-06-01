<script setup lang="ts">
import { computed, ref, watch } from 'vue'

const props = withDefaults(
  defineProps<{
    isRecording: boolean
    disabled?: boolean
    hasError?: boolean
    alreadyRecordedToday?: boolean
    wasSuccessful?: boolean
  }>(),
  {
    disabled: false,
    hasError: false,
    alreadyRecordedToday: false,
    wasSuccessful: false,
  },
)

const emit = defineEmits<{
  record: []
}>()

const localPending = ref(false)
const isButtonDisabled = computed(
  () => props.disabled || props.alreadyRecordedToday || props.isRecording || localPending.value,
)

const buttonLabel = computed(() => {
  if (props.isRecording || localPending.value) {
    return '記録しています'
  }
  if (props.alreadyRecordedToday) {
    return '今日は記録済み'
  }
  if (props.wasSuccessful) {
    return '記録しました'
  }
  if (props.hasError) {
    return 'もう一度記録する'
  }
  return '水やりを記録する'
})

const statusMessage = computed(() => {
  if (props.isRecording || localPending.value) {
    return '水やりを記録しています'
  }
  if (props.wasSuccessful) {
    return '水やりを記録しました'
  }
  if (props.alreadyRecordedToday) {
    return '今日はすでに水やりを記録しています。'
  }
  if (props.hasError) {
    return '記録できませんでした。もう一度お試しください。'
  }
  if (props.disabled) {
    return '水やり記録は現在利用できません。'
  }
  return null
})

const buttonClasses = computed(() => [
  'inline-flex min-h-11 w-full items-center justify-center rounded-md px-4 py-2.5 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-60',
  props.wasSuccessful
    ? 'border border-leaf-600 bg-leaf-50 text-leaf-700'
    : props.hasError
      ? 'border border-red-200 bg-red-50 text-red-700'
      : 'bg-leaf-600 text-white hover:bg-leaf-700',
])

function handleClick(): void {
  if (isButtonDisabled.value) {
    return
  }

  localPending.value = true
  emit('record')
}

watch(() => props.isRecording, (isRecording) => {
  if (isRecording) {
    localPending.value = false
  }
})

watch(
  () => [props.wasSuccessful, props.hasError, props.disabled] as const,
  ([wasSuccessful, hasError, disabled], [previousWasSuccessful, previousHasError, previousDisabled]) => {
    if (!localPending.value) {
      return
    }

    const completed =
      (wasSuccessful && !previousWasSuccessful) ||
      (hasError && !previousHasError) ||
      (disabled && !previousDisabled)

    if (completed) {
      localPending.value = false
    }
  },
)
</script>

<template>
  <div class="grid gap-2">
    <button
      type="button"
      :class="buttonClasses"
      :disabled="isButtonDisabled"
      @click="handleClick"
    >
      {{ buttonLabel }}
    </button>
    <p v-if="statusMessage" class="text-sm text-stone-700" aria-live="polite">
      {{ statusMessage }}
    </p>
  </div>
</template>
