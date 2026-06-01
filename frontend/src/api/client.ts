import type {
  ApiError,
  ApiErrorType,
  AuthenticatedApiClient,
  SessionTokenProvider,
} from '../types/api'

interface AuthenticatedApiClientOptions {
  baseUrl?: string
  getToken: SessionTokenProvider
  fetch?: typeof fetch
}

const DEFAULT_API_BASE_URL = import.meta.env?.VITE_API_BASE_URL ?? 'http://localhost:8000'

const ERROR_MESSAGES: Record<ApiErrorType, string> = {
  auth: 'ログインの有効期限が切れました。もう一度ログインしてください。',
  forbidden: 'この操作を利用できません。',
  not_found: '対象の記録が見つかりません。',
  validation: '入力内容を確認してください。',
  network: '接続できませんでした。',
  server: '記録を読み込めませんでした。',
  conflict: 'すでに登録されています。',
}

export function createApiError(
  type: ApiErrorType,
  message = ERROR_MESSAGES[type],
  fieldErrors?: Record<string, string>,
): ApiError {
  const error = new Error(sanitizeMessage(type, message)) as ApiError
  error.name = 'ApiError'
  error.type = type
  error.fieldErrors = fieldErrors
  return error
}

function sanitizeMessage(type: ApiErrorType, message: string): string {
  if (/(authorization|bearer|clerk_secret|secret|token|verifier|sk_(test|live)_)/i.test(message)) {
    return ERROR_MESSAGES[type]
  }

  return message
}

export function createAuthenticatedApiClient(
  options: AuthenticatedApiClientOptions,
): AuthenticatedApiClient {
  const baseUrl = options.baseUrl ?? DEFAULT_API_BASE_URL
  const fetchImpl = options.fetch ?? fetch

  return {
    async request<TResponse>(path: string, init?: RequestInit): Promise<TResponse> {
      let token: string | null

      try {
        token = await options.getToken()
      } catch {
        throw createApiError('auth')
      }

      if (!token) {
        throw createApiError('auth')
      }

      let response: Response

      try {
        response = await fetchImpl(`${baseUrl}${path}`, {
          ...init,
          headers: createRequestHeaders(init?.headers, token),
        })
      } catch {
        throw createApiError('network')
      }

      if (response.ok) {
        return (await response.json()) as TResponse
      }

      throw createApiError(errorTypeForStatus(response.status))
    },
  }
}

function createRequestHeaders(headers: HeadersInit | undefined, token: string): Headers {
  const requestHeaders = new Headers(headers)

  if (!requestHeaders.has('Content-Type')) {
    requestHeaders.set('Content-Type', 'application/json')
  }

  requestHeaders.set('Authorization', `Bearer ${token}`)
  return requestHeaders
}

function errorTypeForStatus(status: number): ApiErrorType {
  if (status === 401) {
    return 'auth'
  }
  if (status === 403) {
    return 'forbidden'
  }
  if (status === 404) {
    return 'not_found'
  }
  if (status === 409) {
    return 'conflict'
  }
  if (status === 422) {
    return 'validation'
  }
  return 'server'
}
