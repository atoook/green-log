export type ApiErrorType =
  | 'validation'
  | 'not_found'
  | 'network'
  | 'server'
  | 'auth'
  | 'conflict'
  | 'forbidden'

export interface ApiError extends Error {
  type: ApiErrorType
  fieldErrors?: Record<string, string>
}

export interface AuthenticatedApiClient {
  request<TResponse>(path: string, init?: RequestInit): Promise<TResponse>
}

export type SessionTokenProvider = () => Promise<string | null>
