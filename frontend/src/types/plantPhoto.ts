export interface PlantPhoto {
  id: string
  plantId: number
  imageUrl: string
  takenDate: string | null
  comment: string | null
  isCover: boolean
  createdAt: string
}

export interface PlantPhotoQuota {
  currentCount: number
  maxCount: number | null
  unlimited: boolean
}

export interface PlantPhotoGallery {
  photos: PlantPhoto[]
  quota: PlantPhotoQuota
  coverPhotoId: string | null
}

export interface PlantPhotoCreateInput {
  objectKey: string
  takenDate?: string | null
  comment?: string | null
}

export interface PlantPhotoUpdateInput {
  takenDate?: string | null
  comment?: string | null
}

export interface PlantPhotoUploadResult {
  objectKey: string
}
