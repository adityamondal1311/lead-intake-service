import type { ErrorEnvelope } from './types'

// Read at build time (Vite inlines import.meta.env), so it must be set before `npm run build`.
const BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/+$/, '')

/**
 * Every failed API call becomes an ApiError, so components deal with one error shape.
 * `status` is 0 and `code` is NETWORK_ERROR when the server could not be reached at all.
 * `requestId` matches the server's X-Request-ID and its log lines for that request.
 */
export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly details: unknown
  readonly requestId: string | null

  constructor(
    status: number,
    code: string,
    message: string,
    details: unknown = null,
    requestId: string | null = null,
  ) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.details = details
    this.requestId = requestId
  }

  get isNetworkError(): boolean {
    return this.code === 'NETWORK_ERROR'
  }
}

type QueryValue = string | number | undefined | null

interface RequestOptions {
  method?: 'GET' | 'PATCH'
  query?: Record<string, QueryValue>
  body?: unknown
  signal?: AbortSignal
}

function buildUrl(path: string, query?: Record<string, QueryValue>): string {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(query ?? {})) {
    // Omit empty values rather than sending `status=` or `search=`.
    if (value !== undefined && value !== null && value !== '') params.set(key, String(value))
  }
  const qs = params.toString()
  return `${BASE_URL}${path}${qs ? `?${qs}` : ''}`
}

function isErrorEnvelope(body: unknown): body is ErrorEnvelope {
  return (
    typeof body === 'object' &&
    body !== null &&
    'error' in body &&
    typeof (body as ErrorEnvelope).error?.code === 'string'
  )
}

export async function apiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', query, body, signal } = options

  let response: Response
  try {
    response = await fetch(buildUrl(path, query), {
      method,
      signal,
      headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch (error) {
    // A cancelled request (e.g. superseded search) is not an error to show; let it propagate.
    if (signal?.aborted) throw error
    throw new ApiError(0, 'NETWORK_ERROR', 'Could not reach the server.')
  }

  if (response.ok) return (await response.json()) as T

  const parsed: unknown = await response.json().catch(() => null)
  if (isErrorEnvelope(parsed)) {
    const { code, message, details, requestId } = parsed.error
    throw new ApiError(response.status, code, message, details, requestId)
  }
  // Not our envelope (e.g. a proxy error page): keep the status and whatever id we have.
  throw new ApiError(
    response.status,
    'HTTP_ERROR',
    response.statusText || `Request failed with status ${response.status}`,
    null,
    response.headers.get('X-Request-ID'),
  )
}
