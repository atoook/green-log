import type {
  PlantCreateInput,
  PlantFormState,
  PlantFormValidationResult,
  PlantUpdateInput,
} from '../types/plant'

export function validatePlantCreateForm(
  form: PlantFormState,
): PlantFormValidationResult<PlantCreateInput> {
  const normalized = normalizePlantForm(form)
  const error = validateRequiredPlantFields(normalized)
  if (error) {
    return { input: null, error }
  }

  return {
    input: {
      name: normalized.name,
      acquiredDate: normalized.acquiredDate,
      memo: normalized.memo,
      wateringCycleDays: normalized.wateringCycleDays,
    },
    error: null,
  }
}

export function validatePlantUpdateForm(
  form: PlantFormState,
): PlantFormValidationResult<PlantUpdateInput> {
  const normalized = normalizePlantForm(form)
  const error = validateRequiredPlantFields(normalized)
  if (error) {
    return { input: null, error }
  }

  return {
    input: {
      name: normalized.name,
      acquiredDate: normalized.acquiredDate,
      memo: normalized.memo,
      wateringCycleDays: normalized.wateringCycleDays,
    },
    error: null,
  }
}

interface NormalizedPlantForm {
  name: string
  acquiredDate: string | null
  memo: string | null
  wateringCycleDays: number
}

function normalizePlantForm(form: PlantFormState): NormalizedPlantForm {
  return {
    name: form.name.trim(),
    acquiredDate: form.acquiredDate || null,
    memo: form.memo.trim() || null,
    wateringCycleDays: Number(form.wateringCycleDays),
  }
}

function validateRequiredPlantFields(form: NormalizedPlantForm): string | null {
  if (!form.name) {
    return '植物名を入力してください'
  }
  if (form.acquiredDate !== null && !isValidDateOnly(form.acquiredDate)) {
    return '家に来た日を正しい日付で入力してください'
  }
  if (!Number.isFinite(form.wateringCycleDays) || !Number.isInteger(form.wateringCycleDays)) {
    return '水やり周期を日数で入力してください'
  }
  if (form.wateringCycleDays < 1) {
    return '水やり周期は1日以上で入力してください'
  }

  return null
}

function isValidDateOnly(value: string): boolean {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value)
  if (!match) {
    return false
  }

  const year = Number(match[1])
  const month = Number(match[2])
  const day = Number(match[3])
  const date = new Date(Date.UTC(year, month - 1, day))

  return (
    date.getUTCFullYear() === year &&
    date.getUTCMonth() === month - 1 &&
    date.getUTCDate() === day
  )
}
