<script setup lang="ts">
import { computed, ref } from 'vue'
import type { ApiError } from '../../types/api'
import type { PlantPhoto, PlantPhotoGallery } from '../../types/plantPhoto'

const props = withDefaults(defineProps<{
  gallery: PlantPhotoGallery | null
  isLoading: boolean
  isUploading: boolean
  isSettingCover: boolean
  isDeleting: boolean
  isUpdatingMetadata?: boolean
  error: ApiError | null
  actionError: ApiError | null
}>(), {
  isUpdatingMetadata: false,
})

const emit = defineEmits<{
  add: [input: { file: File; takenDate: string | null; comment: string | null }]
  updateMetadata: [photoId: string, input: { takenDate: string | null; comment: string | null }]
  setCover: [photoId: string]
  delete: [photoId: string]
  retry: []
}>()

const selectedFile = ref<File | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const takenDate = ref('')
const comment = ref('')
const editingPhotoId = ref<string | null>(null)
const editingTakenDate = ref('')
const editingComment = ref('')
const failedImageIds = ref(new Set<string>())
const expandedCommentIds = ref(new Set<string>())
const collapsedCommentLength = 32

const photos = computed(() => props.gallery?.photos ?? [])
const quota = computed(() => props.gallery?.quota ?? null)
const isEditingPhoto = computed(() => editingPhotoId.value !== null)
const isAtLimit = computed(() => {
  if (!quota.value || quota.value.unlimited || quota.value.maxCount === null) {
    return false
  }
  return quota.value.currentCount >= quota.value.maxCount
})
const quotaLabel = computed(() => {
  if (!quota.value) {
    return ''
  }
  if (quota.value.unlimited) {
    return `${quota.value.currentCount}枚`
  }
  return `${quota.value.currentCount} / ${quota.value.maxCount}枚`
})

function onFileChange(event: Event): void {
  const input = event.target as HTMLInputElement
  selectedFile.value = input.files?.[0] ?? null
}

function submitPhoto(): void {
  if (!selectedFile.value || isAtLimit.value || props.isUploading) {
    return
  }

  emit('add', {
    file: selectedFile.value,
    takenDate: takenDate.value || null,
    comment: comment.value.trim() || null,
  })
  selectedFile.value = null
  if (fileInput.value) {
    fileInput.value.value = ''
  }
  takenDate.value = ''
  comment.value = ''
}

function confirmDelete(photo: PlantPhoto): void {
  const message = photo.isCover
    ? 'この画像を削除します。サムネイルも未設定に戻ります。'
    : 'この画像を削除します。'
  if (!window.confirm(message)) {
    return
  }
  emit('delete', photo.id)
}

function startEditing(photo: PlantPhoto): void {
  editingPhotoId.value = photo.id
  editingTakenDate.value = photo.takenDate ?? ''
  editingComment.value = photo.comment ?? ''
}

function cancelEditing(): void {
  editingPhotoId.value = null
  editingTakenDate.value = ''
  editingComment.value = ''
}

function submitMetadata(): void {
  if (!editingPhotoId.value || props.isUpdatingMetadata) {
    return
  }

  emit('updateMetadata', editingPhotoId.value, {
    takenDate: editingTakenDate.value || null,
    comment: editingComment.value.trim() || null,
  })
  cancelEditing()
}

function markImageFailed(photoId: string): void {
  failedImageIds.value = new Set(failedImageIds.value).add(photoId)
}

function shouldCollapseComment(value: string): boolean {
  return value.includes('\n') || value.length > collapsedCommentLength
}

function collapsedCommentPreview(value: string): string {
  const normalized = value.replace(/\s+/g, ' ').trim()
  if (normalized.length <= collapsedCommentLength) {
    return normalized
  }
  return `${normalized.slice(0, collapsedCommentLength)}...`
}

function isCommentExpanded(photoId: string): boolean {
  return expandedCommentIds.value.has(photoId)
}

function toggleComment(photoId: string): void {
  const next = new Set(expandedCommentIds.value)
  if (next.has(photoId)) {
    next.delete(photoId)
  } else {
    next.add(photoId)
  }
  expandedCommentIds.value = next
}
</script>

<template>
  <section class="grid max-w-full gap-4 rounded-lg border border-stone-200 bg-white p-4" aria-labelledby="plant-gallery-title">
    <div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
      <div class="min-w-0">
        <p class="text-sm font-semibold text-leaf-700">成長記録</p>
        <h2 id="plant-gallery-title" class="break-words text-2xl font-semibold text-stone-950">
          画像ギャラリー
        </h2>
      </div>
      <p v-if="quotaLabel" class="text-sm font-semibold text-stone-700">{{ quotaLabel }}</p>
    </div>

    <div class="grid min-w-0 gap-3 rounded-md bg-stone-50 p-3">
      <div v-if="error" class="rounded-md bg-red-50 p-3 text-sm text-red-800">
        <p>{{ error.message }}</p>
        <button class="mt-2 font-semibold text-red-900" type="button" @click="emit('retry')">
          再読み込み
        </button>
      </div>

      <p v-else-if="isLoading" class="text-sm text-stone-600">読み込んでいます</p>

      <div v-else-if="photos.length === 0" class="flex min-h-40 items-center justify-center rounded-md bg-white px-4 text-sm font-semibold text-leaf-700">
        画像はまだありません
      </div>

      <ol v-else class="grid items-start gap-3 sm:grid-cols-2">
        <li
          v-for="photo in photos"
          :key="photo.id"
          class="grid min-w-0 gap-3 rounded-md border border-stone-200 bg-white p-3"
        >
          <div class="relative">
            <img
              v-if="!failedImageIds.has(photo.id)"
              class="aspect-[4/3] w-full rounded-md object-cover"
              :src="photo.imageUrl"
              :alt="photo.comment || '植物画像'"
              @error="markImageFailed(photo.id)"
            />
            <div v-else class="flex aspect-[4/3] w-full items-center justify-center rounded-md bg-stone-100 text-sm text-stone-600">
              読み込めませんでした
            </div>
            <span
              v-if="photo.isCover"
              class="absolute left-2 top-2 rounded bg-leaf-700 px-2 py-1 text-xs font-semibold text-white"
            >
              サムネイル
            </span>
          </div>

          <form
            v-if="editingPhotoId === photo.id"
            class="grid gap-3 rounded-md bg-stone-50 p-3"
            @submit.prevent="submitMetadata"
          >
            <div class="grid gap-2">
              <label class="grid min-w-0 gap-1 text-sm font-semibold text-stone-800">
                撮影日
                <input
                  v-model="editingTakenDate"
                  class="box-border w-full min-w-0 max-w-full rounded-md border border-stone-300 px-3 py-2 text-sm font-normal"
                  type="date"
                  :disabled="isUpdatingMetadata"
                />
              </label>
              <label class="grid min-w-0 gap-1 text-sm font-semibold text-stone-800">
                コメント
                <input
                  v-model="editingComment"
                  class="w-full min-w-0 rounded-md border border-stone-300 px-3 py-2 text-sm font-normal"
                  type="text"
                  maxlength="120"
                  :disabled="isUpdatingMetadata"
                />
              </label>
            </div>
            <div class="grid w-full gap-2 pt-1">
              <button
                class="w-full rounded-md bg-leaf-700 px-3 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
                type="submit"
                :disabled="isUpdatingMetadata"
              >
                {{ isUpdatingMetadata ? '保存中' : '保存' }}
              </button>
              <button
                class="w-full rounded-md border border-stone-300 px-3 py-2 text-sm font-semibold text-stone-700 disabled:cursor-not-allowed disabled:opacity-50"
                type="button"
                :disabled="isUpdatingMetadata"
                @click="cancelEditing()"
              >
                キャンセル
              </button>
            </div>
          </form>

          <template v-else>
            <div class="grid gap-1 text-sm text-stone-700">
              <p>{{ photo.takenDate || photo.createdAt.slice(0, 10) }}</p>
              <div v-if="photo.comment" class="grid gap-1">
                <div
                  v-if="shouldCollapseComment(photo.comment) && !isCommentExpanded(photo.id)"
                  class="text-sm text-stone-700"
                >
                  <p class="break-words">
                    <span>{{ collapsedCommentPreview(photo.comment) }}</span>
                    <button
                      class="ml-1 inline text-xs font-semibold text-stone-500 underline underline-offset-2 hover:text-stone-700"
                      type="button"
                      aria-expanded="false"
                      @click="toggleComment(photo.id)"
                    >
                      もっと見る
                    </button>
                  </p>
                </div>
                <p v-else class="line-clamp-none whitespace-pre-wrap break-words">
                  <span>{{ photo.comment }}</span>
                  <button
                    v-if="shouldCollapseComment(photo.comment)"
                    class="ml-1 inline text-xs font-semibold text-stone-500 underline underline-offset-2 hover:text-stone-700"
                    type="button"
                    aria-expanded="true"
                    @click="toggleComment(photo.id)"
                  >
                    閉じる
                  </button>
                </p>
              </div>
            </div>

            <div v-if="!isEditingPhoto" class="flex flex-wrap gap-2">
              <button
                class="rounded-md border border-stone-300 px-3 py-2 text-sm font-semibold text-stone-700 disabled:cursor-not-allowed disabled:opacity-50"
                type="button"
                :disabled="isUpdatingMetadata"
                @click="startEditing(photo)"
              >
                編集
              </button>
              <button
                class="rounded-md border border-leaf-200 px-3 py-2 text-sm font-semibold text-leaf-700 disabled:cursor-not-allowed disabled:opacity-50"
                type="button"
                :disabled="photo.isCover || isSettingCover"
                @click="emit('setCover', photo.id)"
              >
                サムネイルにする
              </button>
              <button
                class="rounded-md border border-red-200 px-3 py-2 text-sm font-semibold text-red-700 disabled:cursor-not-allowed disabled:opacity-50"
                type="button"
                :disabled="isDeleting"
                @click="confirmDelete(photo)"
              >
                削除
              </button>
            </div>
          </template>
        </li>
      </ol>
    </div>

    <form class="grid min-w-0 gap-3 rounded-md border border-leaf-200 bg-leaf-50/60 p-4" @submit.prevent="submitPhoto">
      <div class="grid gap-2">
        <label class="grid min-w-0 gap-1 text-sm font-semibold text-stone-800">
          画像
          <input
            ref="fileInput"
            class="w-full min-w-0 rounded-md border border-stone-300 bg-white px-3 py-2 text-sm font-normal"
            type="file"
            accept="image/jpeg,image/png,image/webp"
            :disabled="isAtLimit || isUploading"
            @change="onFileChange"
          />
        </label>
      </div>

      <div class="grid gap-2 sm:grid-cols-2">
        <label class="grid min-w-0 gap-1 text-sm font-semibold text-stone-800">
          撮影日
          <input
            v-model="takenDate"
            class="box-border w-full min-w-0 max-w-full rounded-md border border-stone-300 bg-white px-3 py-2 text-sm font-normal"
            type="date"
            :disabled="isAtLimit || isUploading"
          />
        </label>
        <label class="grid min-w-0 gap-1 text-sm font-semibold text-stone-800">
          コメント
          <input
            v-model="comment"
            class="w-full min-w-0 rounded-md border border-stone-300 bg-white px-3 py-2 text-sm font-normal"
            type="text"
            maxlength="120"
            :disabled="isAtLimit || isUploading"
          />
        </label>
      </div>

      <p v-if="isAtLimit" class="text-sm font-semibold text-stone-700">画像枚数の上限に達しています。</p>
      <p v-if="actionError" class="rounded-md bg-red-50 p-3 text-sm text-red-800">{{ actionError.message }}</p>
      <button
        class="w-full rounded-md bg-leaf-700 px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
        type="submit"
        :disabled="!selectedFile || isAtLimit || isUploading"
      >
        {{ isUploading ? '追加中' : '追加' }}
      </button>
    </form>
  </section>
</template>
