import { QueryClient } from '@tanstack/react-query'

import { ApiError } from '../api/client'

const MAX_RETRIES = 2

/**
 * Retry only failures that a retry can fix: the server being unreachable or a 5xx. A 4xx
 * (not found, validation error) will fail the same way every time, so retrying would only delay
 * the error message.
 */
export function shouldRetry(failureCount: number, error: unknown): boolean {
  if (failureCount >= MAX_RETRIES) return false
  if (error instanceof ApiError) return error.isNetworkError || error.status >= 500
  return false
}

/**
 * The app's query client. Tests build their own per test with the same retry policy but
 * `retryDelay: 0`, so retry behaviour is tested without waiting out the real back-off.
 */
export function createQueryClient(options: { retryDelay?: number } = {}): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        // Lead data changes when webhooks arrive, so treat it as fresh for a short while only.
        staleTime: 15_000,
        retry: shouldRetry,
        ...(options.retryDelay !== undefined && { retryDelay: options.retryDelay }),
      },
    },
  })
}

export const queryClient = createQueryClient()
