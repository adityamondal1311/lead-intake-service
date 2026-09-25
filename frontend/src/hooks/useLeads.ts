import { keepPreviousData, useQuery } from '@tanstack/react-query'

import { getLeads } from '../api/leads'
import type { LeadListParams } from '../api/types'

export function useLeads(params: LeadListParams) {
  return useQuery({
    // Every parameter is part of the key, so each page/filter/search is cached separately.
    queryKey: ['leads', params],
    // TanStack passes an AbortSignal: when the key changes (e.g. the search term moves on), the
    // superseded request is cancelled, so an older response can never replace newer data.
    queryFn: ({ signal }) => getLeads(params, signal),
    // v5 replacement for v4's `keepPreviousData: true`: while the next page loads, keep showing
    // the current one instead of flashing back to a loading state.
    placeholderData: keepPreviousData,
  })
}
