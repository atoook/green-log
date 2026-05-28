import type { ApiError, Plant, PlantCreateInput } from '../types/plant'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response

  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      headers: {
        'Content-Type': 'application/json',
        ...(init?.headers ?? {}),
      },
      ...init,
    })
  } catch {
    throw { type: 'network', message: '接続できませんでした' } as ApiError
  }

  if (response.ok) {
    return (await response.json()) as T
  }

  if (response.status === 404) {
    throw { type: 'not_found', message: '植物が見つかりません' } as ApiError
  }

  if (response.status === 422) {
    const body = (await response.json()) as { detail?: unknown }
    throw {
      type: 'validation',
      message: parseValidationMessage(body.detail),
      fieldErrors: {},
    } as ApiError
  }

  throw { type: 'server', message: '記録を読み込めませんでした' } as ApiError
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
