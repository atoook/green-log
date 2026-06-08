import type { AuthenticatedApiClient } from '../types/api'
import type {
  PlantPhoto,
  PlantPhotoCreateInput,
  PlantPhotoGallery,
  PlantPhotoUpdateInput,
  PlantPhotoUploadResult,
} from '../types/plantPhoto'

export interface PlantPhotosApiClient {
  uploadPhoto(input: PlantPhotoUploadInput): Promise<PlantPhotoUploadResult>
  listPlantPhotos(plantId: number): Promise<PlantPhotoGallery>
  registerPlantPhoto(plantId: number, input: PlantPhotoCreateInput): Promise<PlantPhoto>
  updatePlantPhotoMetadata(
    plantId: number,
    photoId: string,
    input: PlantPhotoUpdateInput,
  ): Promise<PlantPhoto>
  setCoverPhoto(plantId: number, photoId: string): Promise<PlantPhotoGallery>
  deletePlantPhoto(plantId: number, photoId: string): Promise<PlantPhoto>
}

export interface PlantPhotoUploadInput {
  plantId: number
  file: File
}

export function createPlantPhotosApiClient(
  apiClient: AuthenticatedApiClient,
): PlantPhotosApiClient {
  return {
    uploadPhoto(input: PlantPhotoUploadInput): Promise<PlantPhotoUploadResult> {
      const formData = new FormData()
      formData.append('plantId', String(input.plantId))
      formData.append('file', input.file)

      return apiClient.request<PlantPhotoUploadResult>('/photos/upload', {
        method: 'POST',
        body: formData,
      })
    },

    listPlantPhotos(plantId: number): Promise<PlantPhotoGallery> {
      return apiClient.request<PlantPhotoGallery>(`/plants/${plantId}/photos`)
    },

    registerPlantPhoto(
      plantId: number,
      input: PlantPhotoCreateInput,
    ): Promise<PlantPhoto> {
      return apiClient.request<PlantPhoto>(`/plants/${plantId}/photos`, {
        method: 'POST',
        body: JSON.stringify(input),
      })
    },

    updatePlantPhotoMetadata(
      plantId: number,
      photoId: string,
      input: PlantPhotoUpdateInput,
    ): Promise<PlantPhoto> {
      return apiClient.request<PlantPhoto>(`/plants/${plantId}/photos/${photoId}`, {
        method: 'PATCH',
        body: JSON.stringify(input),
      })
    },

    setCoverPhoto(plantId: number, photoId: string): Promise<PlantPhotoGallery> {
      return apiClient.request<PlantPhotoGallery>(`/plants/${plantId}/cover-photo`, {
        method: 'PATCH',
        body: JSON.stringify({ photoId }),
      })
    },

    deletePlantPhoto(plantId: number, photoId: string): Promise<PlantPhoto> {
      return apiClient.request<PlantPhoto>(`/plants/${plantId}/photos/${photoId}`, {
        method: 'DELETE',
      })
    },
  }
}
