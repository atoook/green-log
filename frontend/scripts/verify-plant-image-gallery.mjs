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
      ],
      quota: { currentCount: 1, maxCount: null, unlimited: true },
      coverPhotoId: 'photo-1',
    },
    isLoading: false,
    isUploading: false,
    isSettingCover: false,
    isDeleting: false,
    error: null,
    actionError: null,
  })
  assert.match(listed, /1枚/)
  assert.doesNotMatch(listed, /\/ 5枚/)
  assert.match(listed, /代表/)
  assert.match(listed, /葉が増えた/)
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
  await composable.deletePhoto('photo-1')
  await composable.setCoverPhoto('new-photo')

  assert.deepEqual(calls, [
    ['upload', 1, 'photo.webp'],
    ['register', 1, 'plants/1/new-photo.webp', '新しい葉'],
    ['delete', 1, 'photo-1'],
    ['cover', 1, 'new-photo'],
  ])
  assert.equal(coverCallbackCount, 2)
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
  assert.doesNotMatch(plantPhotosSource, /ownerUserId|owner_user_id|storageKey|storage_key/)
}

async function verifyPageIntegration() {
  const source = await readFile(new URL('../src/pages/PlantDetailPage.vue', import.meta.url), 'utf8')
  assert.match(source, /PlantImageGallery/)
  assert.match(source, /usePlantPhotos/)
  assert.match(source, /onCoverImageChange: loadPlant/)
  assert.match(source, /@add="addPhoto"/)
  assert.match(source, /@set-cover="setCoverPhoto"/)
  assert.match(source, /@delete="deletePhoto"/)
}
