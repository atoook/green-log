export interface Plant {
  id: number
  name: string
  acquiredDate: string | null
  memo: string | null
  imageUrl: string | null
  wateringCycleDays: number
  createdAt: string
  updatedAt: string
}

export interface PlantCreateInput {
  name: string
  acquiredDate: string | null
  memo: string | null
  imageUrl: string | null
  wateringCycleDays: number
}

export interface PlantFormState {
  name: string
  acquiredDate: string
  memo: string
  imageUrl: string
  wateringCycleDays: string
}

export type ApiError =
  | { type: 'validation'; message: string; fieldErrors: Record<string, string> }
  | { type: 'not_found'; message: string }
  | { type: 'network'; message: string }
  | { type: 'server'; message: string }
