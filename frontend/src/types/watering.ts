export type DueStatus = 'unrecorded' | 'due_today' | 'overdue'

export interface WateringPlantSummary {
  id: number
  name: string
  imageUrl: string | null
  wateringCycleDays: number
}

export interface PlantWateringState {
  plantId: number
  lastWateredAt: string | null
  nextWateringDate: string | null
  isDueToday: boolean
  dueStatus: DueStatus | null
}

export interface WateringRecord {
  id: number
  plantId: number
  wateredAt: string
  createdAt: string
}

export interface TodayCareItem extends PlantWateringState {
  plant: WateringPlantSummary
}

export interface TodayCare {
  today: string
  items: TodayCareItem[]
}

export interface PlantWateringDetail extends PlantWateringState {
  history: WateringRecord[]
}

export interface WateringRecordCreateResult {
  record: WateringRecord
  state: PlantWateringDetail
}
