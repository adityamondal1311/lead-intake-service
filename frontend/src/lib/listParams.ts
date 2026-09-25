import { isLeadStatus, type LeadStatus } from '../api/types'

/** The lead list's view state. The URL is its source of truth (shareable, back button works). */
export interface ListFilters {
  page: number
  status: LeadStatus | undefined
  search: string
}

export const MAX_SEARCH_LENGTH = 100 // same limit as the API

/**
 * URL → valid state. Anything hand-edited or stale is normalized instead of being sent to the API
 * (which would answer 422):
 *   status: missing or not a known status → all statuses
 *   page:   missing, non-numeric or < 1   → 1   (a page past the end is corrected once the
 *                                                  total is known; see LeadListPage)
 *   search: trimmed, capped at 100 chars; whitespace-only → no search
 */
export function parseListParams(params: URLSearchParams): ListFilters {
  const rawStatus = params.get('status')
  const rawPage = params.get('page') ?? ''
  const page = /^\d+$/.test(rawPage) ? Number(rawPage) : 1
  return {
    status: isLeadStatus(rawStatus) ? rawStatus : undefined,
    page: page >= 1 ? page : 1,
    search: (params.get('search') ?? '').trim().slice(0, MAX_SEARCH_LENGTH),
  }
}

/**
 * State → canonical URL params. Defaults are omitted (page 1, all statuses, no search), so each
 * view has exactly one URL and the unfiltered first page is simply "/".
 */
export function toSearchParams(filters: ListFilters): URLSearchParams {
  const params = new URLSearchParams()
  if (filters.search) params.set('search', filters.search)
  if (filters.status) params.set('status', filters.status)
  if (filters.page > 1) params.set('page', String(filters.page))
  return params
}

export function hasActiveFilters(filters: ListFilters): boolean {
  return Boolean(filters.search || filters.status)
}
