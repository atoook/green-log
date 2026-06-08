import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { createSSRApp, effectScope, ref } from 'vue'
import { renderToString } from '@vue/server-renderer'
import { createServer } from 'vite'

const server = await createServer({
  appType: 'custom',
  logLevel: 'silent',
  server: { middlewareMode: true, hmr: false },
})

try {
  const [galleryModule, composableModule] = await Promise.all([
    server.ssrLoadModule('/src/components/plants/PlantImageGallery.vue'),
    server.ssrLoadModule('/src/composables/usePlantPhotos.ts'),
  ])

  await verifyGalleryRender(galleryModule.default)
  await verifyGalleryDeleteFlow()
  await verifyComposable(composableModule.usePlantPhotos)
  await verifyApiClientSource()
  await verifyPageIntegration()
} finally {
  await server.close()
}

console.log('OK plant image gallery verification')

async function renderComponent(component, props) {
  return renderToString(createSSRApp(component, props))
}

async function verifyGalleryRender(PlantImageGallery) {
  const empty = await renderComponent(PlantImageGallery, {
    gallery: {
      photos: [],
      quota: { currentCount: 0, maxCount: 5, unlimited: false },
      coverPhotoId: null,
    },
    isLoading: false,
    isUploading: false,
    isSettingCover: false,
    isDeleting: false,
    isUpdatingMetadata: false,
    error: null,
    actionError: null,
  })
  assert.match(empty, /画像ギャラリー/)
  assert.match(empty, /0 \/ 5枚/)
  assert.match(empty, /画像はまだありません/)
  assert.doesNotMatch(empty, /storageKey|storage_key|ownerUserId|owner_user_id/)

  const listed = await renderComponent(PlantImageGallery, {
    gallery: {
      photos: [
        {
          id: 'photo-1',
          plantId: 1,
          imageUrl: 'https://cdn.example.invalid/plants/1/photo.webp',
          takenDate: '2026-06-01',
          comment: '葉が増えた',
          isCover: true,
          createdAt: '2026-06-01T09:30:00Z',
        },
        {
          id: 'photo-2',
          plantId: 1,
          imageUrl: 'https://cdn.example.invalid/plants/1/photo-2.webp',
          takenDate: '2026-06-02',
          comment: '新しい芽が出てきた。\n葉の色も濃くなってきたので、来週も同じ角度から撮影して比較したい。',
          isCover: false,
          createdAt: '2026-06-02T09:30:00Z',
        },
      ],
      quota: { currentCount: 2, maxCount: null, unlimited: true },
      coverPhotoId: 'photo-1',
    },
    isLoading: false,
    isUploading: false,
    isSettingCover: false,
    isDeleting: false,
    isUpdatingMetadata: false,
    error: null,
    actionError: null,
  })
  assert.match(listed, /2枚/)
  assert.doesNotMatch(listed, /\/ 5枚/)
  assert.match(listed, /サムネイル/)
  assert.match(listed, /編集/)
  assert.match(listed, /葉が増えた/)
  assert.match(listed, /新しい芽が出てきた。 葉の色も濃くなってきたので、来週も同じ角度/)
  assert.match(listed, /もっと見る/)
  assert.doesNotMatch(listed, /absolute bottom-0 right-0/)
  assert.doesNotMatch(listed, /bg-white pl-2/)
}

async function verifyGalleryDeleteFlow() {
  const source = await readFile(
    new URL('../src/components/plants/PlantImageGallery.vue', import.meta.url),
    'utf8',
  )
  assert.match(source, /window\.confirm\(message\)/)
  assert.match(source, /emit\('delete', photo\.id\)/)
  assert.match(source, /emit\('updateMetadata', editingPhotoId\.value/)
  assert.match(source, /startEditing\(photo\)/)
  assert.match(source, /cancelEditing\(\)/)
  assert.match(source, /const isEditingPhoto = computed\(\(\) => editingPhotoId\.value !== null\)/)
  assert.match(source, /<form[\s\S]*v-if="editingPhotoId === photo\.id"[\s\S]*<template v-else>/)
  assert.match(source, /class="grid items-start gap-3 sm:grid-cols-2"/)
  assert.match(source, /<div v-if="!isEditingPhoto" class="flex flex-wrap gap-2">/)
  assert.match(source, /class="grid max-w-full gap-4/)
  assert.match(source, /class="grid min-w-0 gap-3 rounded-md bg-stone-50 p-3"/)
  assert.match(source, /class="grid min-w-0 gap-3 rounded-md border border-stone-200 bg-white p-3"/)
  assert.match(source, /class="grid min-w-0 gap-3 rounded-md border border-leaf-200 bg-leaf-50\/60 p-4"/)
  assert.match(source, /class="w-full min-w-0 rounded-md border border-stone-300 bg-white px-3 py-2 text-sm font-normal"/)
  assert.match(source, /class="grid w-full gap-2 pt-1"/)
  assert.match(source, /class="w-full rounded-md bg-leaf-700/)
  assert.match(source, /class="w-full rounded-md border border-stone-300/)
  assert.match(source, /@change="onFileChange"[\s\S]*v-model="takenDate"[\s\S]*v-model="comment"[\s\S]*type="submit"[\s\S]*{{ isUploading \? '追加中' : '追加' }}/)
  assert.match(source, /const fileInput = ref<HTMLInputElement \| null>\(null\)/)
  assert.match(source, /fileInput\.value\.value = ''/)
  assert.match(source, /ref="fileInput"/)
  assert.match(source, /撮影日/)
  assert.match(source, /コメント/)
  assert.match(source, /サムネイルも未設定に戻ります/)
  assert.match(source, /閉じる/)
  assert.match(source, /class="ml-1 inline text-xs/)
  assert.doesNotMatch(source, /pendingDeletePhoto/)
  assert.doesNotMatch(source, /editingFile|replacementFile|type="file"[\s\S]*editingPhotoId/)
}

async function verifyComposable(usePlantPhotos) {
  const calls = []
  let coverCallbackCount = 0
  const plantId = ref(1)
  const gallery = {
    photos: [
      {
        id: 'photo-1',
        plantId: 1,
        imageUrl: 'https://cdn.example.invalid/plants/1/photo.webp',
        takenDate: null,
        comment: null,
        isCover: true,
        createdAt: '2026-06-01T09:30:00Z',
      },
    ],
    quota: { currentCount: 1, maxCount: 5, unlimited: false },
    coverPhotoId: 'photo-1',
  }
  const composable = effectScope().run(() =>
    usePlantPhotos(plantId, {
      autoLoad: false,
      onCoverImageChange: () => {
        coverCallbackCount += 1
      },
      plantPhotosApiClient: {
        uploadPhoto: async (input) => {
          calls.push(['upload', input.plantId, input.file.name])
          return { objectKey: 'plants/1/new-photo.webp' }
        },
        registerPlantPhoto: async (id, input) => {
          calls.push(['register', id, input.objectKey, input.comment])
          return {
            id: 'new-photo',
            plantId: id,
            imageUrl: 'https://cdn.example.invalid/plants/1/new-photo.webp',
            takenDate: input.takenDate ?? null,
            comment: input.comment ?? null,
            isCover: false,
            createdAt: '2026-06-01T09:30:00Z',
          }
        },
        updatePlantPhotoMetadata: async (id, photoId, input) => {
          calls.push(['update', id, photoId, input.takenDate, input.comment])
          return {
            ...gallery.photos[0],
            takenDate: input.takenDate ?? null,
            comment: input.comment ?? null,
          }
        },
        listPlantPhotos: async () => gallery,
        setCoverPhoto: async (id, photoId) => {
          calls.push(['cover', id, photoId])
          return { ...gallery, coverPhotoId: photoId }
        },
        deletePlantPhoto: async (id, photoId) => {
          calls.push(['delete', id, photoId])
          return gallery.photos[0]
        },
      },
    }),
  )

  composable.gallery.value = gallery
  await composable.addPhoto({
    file: new File(['image'], 'photo.webp', { type: 'image/webp' }),
    comment: '新しい葉',
  })
  await composable.updatePhotoMetadata('photo-1', {
    takenDate: '2026-06-03',
    comment: '撮影日を直した',
  })
  await composable.deletePhoto('photo-1')
  await composable.setCoverPhoto('new-photo')

  assert.deepEqual(calls, [
    ['upload', 1, 'photo.webp'],
    ['register', 1, 'plants/1/new-photo.webp', '新しい葉'],
    ['update', 1, 'photo-1', '2026-06-03', '撮影日を直した'],
    ['delete', 1, 'photo-1'],
    ['cover', 1, 'new-photo'],
  ])
  assert.equal(coverCallbackCount, 2)
  assert.equal(composable.isUpdatingMetadata.value, false)
  assert.equal(composable.actionError.value, null)
}

async function verifyApiClientSource() {
  const [apiClientSource, plantPhotosSource] = await Promise.all([
    readFile(new URL('../src/api/client.ts', import.meta.url), 'utf8'),
    readFile(new URL('../src/api/plantPhotos.ts', import.meta.url), 'utf8'),
  ])
  assert.match(apiClientSource, /body instanceof FormData/)
  assert.match(plantPhotosSource, /new FormData\(\)/)
  assert.match(plantPhotosSource, /\/photos\/upload/)
  assert.match(plantPhotosSource, /updatePlantPhotoMetadata/)
  assert.match(plantPhotosSource, /`\/plants\/\$\{plantId\}\/photos\/\$\{photoId\}`/)
  assert.match(plantPhotosSource, /method: 'PATCH'/)
  assert.doesNotMatch(plantPhotosSource, /method: 'PUT'/)
  assert.doesNotMatch(plantPhotosSource, /ownerUserId|owner_user_id|storageKey|storage_key/)
}

async function verifyPageIntegration() {
  const source = await readFile(new URL('../src/pages/PlantDetailPage.vue', import.meta.url), 'utf8')
  assert.match(source, /PlantImageGallery/)
  assert.match(source, /usePlantPhotos/)
  assert.match(source, /onCoverImageChange: loadPlant/)
  assert.match(source, /@add="addPhoto"/)
  assert.match(source, /:is-updating-metadata="isUpdatingMetadata"/)
  assert.match(source, /@update-metadata="updatePhotoMetadata"/)
  assert.match(source, /@set-cover="setCoverPhoto"/)
  assert.match(source, /@delete="deletePhoto"/)
}
