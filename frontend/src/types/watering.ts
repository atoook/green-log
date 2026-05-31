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

export type WateringHeatmapLevel = 0 | 1 | 2 | 3 | 4

export interface WateringHeatmapRange {
  from: string
  to: string
}

export interface WateringHeatmapPlant {
  plantId: number
  name: string
}

export interface WateringHeatmapDay {
  date: string
  plantCount: number
  level: WateringHeatmapLevel
  plants: WateringHeatmapPlant[]
}

export interface WateringHeatmap {
  startDate: string
  endDate: string
  days: WateringHeatmapDay[]
}
