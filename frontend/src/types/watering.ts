export type DueStatus = 'unrecorded' | 'due_today' | 'overdue'

export interface WateringPlantSummary {
  id: number
  name: string
  acquiredDate: string | null
  imageUrl: string | null
  wateringCycleDays: number
}

export interface PlantWateringState {
  plantId: number
  lastWateredAt: string | null
  nextWateringDate: string | null
  isDueToday: boolean
  hasWateredToday: boolean
  dueStatus: DueStatus | null
}

export interface WateringRecord {
  id: number
  plantId: number
  wateredAt: string
  createdAt: string
}

export interface UpcomingCareItem extends PlantWateringState {
  plant: WateringPlantSummary
}

export type UpcomingCareSectionKind = 'today' | 'tomorrow' | 'day_after_tomorrow' | 'future'

export interface UpcomingCareSection {
  date: string
  kind: UpcomingCareSectionKind
  items: UpcomingCareItem[]
}

export interface UpcomingCare {
  startDate: string
  days: number
  sections: UpcomingCareSection[]
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
