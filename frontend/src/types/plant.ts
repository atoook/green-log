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
  acquiredDate?: string | null
  memo?: string | null
  wateringCycleDays: number
}

export interface PlantUpdateInput {
  name?: string
  acquiredDate?: string | null
  memo?: string | null
  wateringCycleDays?: number
}

export interface PlantFormState {
  name: string
  acquiredDate: string
  memo: string
  wateringCycleDays: string
}

export interface PlantFormValidationResult<TInput> {
  input: TInput | null
  error: string | null
}

export type { ApiError, ApiErrorType } from './api'
