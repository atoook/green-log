import { onMounted, ref, watch, type Ref } from 'vue'
import {
  createPlantPhotosApiClient,
  type PlantPhotosApiClient,
} from '../api/plantPhotos'
import type { ApiError } from '../types/api'
import type { PlantPhoto, PlantPhotoGallery } from '../types/plantPhoto'
import { useAuthenticatedApi } from './useAuthenticatedApi'

interface UsePlantPhotosOptions {
  plantPhotosApiClient?: PlantPhotosApiClient
  autoLoad?: boolean
  onCoverImageChange?: () => void | Promise<void>
}

interface AddPhotoInput {
  file: File
  takenDate?: string | null
  comment?: string | null
}

function shouldClearGalleryOnError(error: ApiError): boolean {
  return error.type === 'auth' || error.type === 'forbidden' || error.type === 'not_found'
}

export function usePlantPhotos(
  plantId: Ref<number | null>,
  options: UsePlantPhotosOptions = {},
) {
  const plantPhotosApiClient =
    options.plantPhotosApiClient ?? createPlantPhotosApiClient(useAuthenticatedApi())
  const gallery = ref<PlantPhotoGallery | null>(null)
  const isLoading = ref(false)
  const isUploading = ref(false)
  const isSettingCover = ref(false)
  const isDeleting = ref(false)
  const error = ref<ApiError | null>(null)
  const actionError = ref<ApiError | null>(null)

  async function loadPhotos(): Promise<void> {
    if (plantId.value === null) {
      gallery.value = null
      return
    }

    isLoading.value = true
    error.value = null
    try {
      gallery.value = await plantPhotosApiClient.listPlantPhotos(plantId.value)
    } catch (caught) {
      const apiError = caught as ApiError
      if (shouldClearGalleryOnError(apiError)) {
        gallery.value = null
      }
      error.value = apiError
    } finally {
      isLoading.value = false
    }
  }

  async function addPhoto(input: AddPhotoInput): Promise<PlantPhoto | null> {
    if (plantId.value === null || isUploading.value) {
      return null
    }

    isUploading.value = true
    actionError.value = null
    try {
      const upload = await plantPhotosApiClient.uploadPhoto({
        plantId: plantId.value,
        file: input.file,
      })
      const created = await plantPhotosApiClient.registerPlantPhoto(plantId.value, {
        objectKey: upload.objectKey,
        takenDate: input.takenDate ?? null,
        comment: input.comment ?? null,
      })
      await loadPhotos()
      return created
    } catch (caught) {
      actionError.value = caught as ApiError
      return null
    } finally {
      isUploading.value = false
    }
  }

  async function setCoverPhoto(photoId: string): Promise<void> {
    if (plantId.value === null || isSettingCover.value) {
      return
    }

    isSettingCover.value = true
    actionError.value = null
    try {
      gallery.value = await plantPhotosApiClient.setCoverPhoto(plantId.value, photoId)
      await options.onCoverImageChange?.()
    } catch (caught) {
      actionError.value = caught as ApiError
    } finally {
      isSettingCover.value = false
    }
  }

  async function deletePhoto(photoId: string): Promise<void> {
    if (plantId.value === null || isDeleting.value) {
      return
    }

    const deletedWasCover = gallery.value?.coverPhotoId === photoId
    isDeleting.value = true
    actionError.value = null
    try {
      await plantPhotosApiClient.deletePlantPhoto(plantId.value, photoId)
      await loadPhotos()
      if (deletedWasCover) {
        await options.onCoverImageChange?.()
      }
    } catch (caught) {
      actionError.value = caught as ApiError
    } finally {
      isDeleting.value = false
    }
  }

  if (options.autoLoad !== false) {
    onMounted(() => {
      void loadPhotos()
    })

    watch(plantId, () => {
      void loadPhotos()
    })
  }

  return {
    gallery,
    isLoading,
    isUploading,
    isSettingCover,
    isDeleting,
    error,
    actionError,
    loadPhotos,
    addPhoto,
    setCoverPhoto,
    deletePhoto,
  }
}
