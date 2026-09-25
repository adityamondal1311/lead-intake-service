import { useQuery } from '@tanstack/react-query'

import { ApiError } from '../api/client'
import { getLead } from '../api/leads'

export const leadQueryKey = (id: string) => ['lead', id] as const

export function useLead(id: string) {
  // Retries follow the app-wide policy (network errors and 5xx only), so a 404, or the 422 a
  // malformed id produces, fails immediately instead of being retried.
  return useQuery({
    queryKey: leadQueryKey(id),
    queryFn: ({ signal }) => getLead(id, signal),
  })
}

/**
 * Both mean "there is no lead at this URL" to the user: 404 for an unknown id, 422 for one that
 * is not a UUID at all (a hand-edited URL). The distinction is an API detail.
 */
export function isLeadNotFound(error: unknown): boolean {
  return error instanceof ApiError && (error.status === 404 || error.status === 422)
}
