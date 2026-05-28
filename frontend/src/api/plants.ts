import type { ApiError, Plant, PlantCreateInput } from '../types/plant'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export function createApiError(
  type: ApiError['type'],
  message: string,
  fieldErrors?: Record<string, string>,
): ApiError {
  const error = new Error(message) as ApiError
  error.name = 'PlantApiError'
  error.type = type
  error.fieldErrors = fieldErrors
  return error
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response

  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: {
        'Content-Type': 'application/json',
        ...(init?.headers ?? {}),
      },
    })
  } catch {
    throw createApiError('network', '接続できませんでした')
  }

  if (response.ok) {
    return (await response.json()) as T
  }

  if (response.status === 404) {
    throw createApiError('not_found', '植物が見つかりません')
  }

  if (response.status === 422) {
    const body = (await response.json()) as { detail?: unknown }
    throw createApiError('validation', parseValidationMessage(body.detail), {})
  }

  throw createApiError('server', '記録を読み込めませんでした')
}

function parseValidationMessage(detail: unknown): string {
  if (typeof detail === 'string') {
    return detail
  }
  return '入力内容を確認してください'
}

export function listPlants(): Promise<Plant[]> {
  return request<Plant[]>('/plants')
}

export function createPlant(input: PlantCreateInput): Promise<Plant> {
  return request<Plant>('/plants', {
    method: 'POST',
    body: JSON.stringify(input),
  })
}

export function getPlant(id: number): Promise<Plant> {
  return request<Plant>(`/plants/${id}`)
}
