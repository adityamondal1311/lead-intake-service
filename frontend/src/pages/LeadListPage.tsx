import { useEffect, useState } from 'react'
import { useLocation, useSearchParams } from 'react-router'

import { LEAD_STATUSES, isLeadStatus } from '../api/types'
import EmptyState from '../components/EmptyState'
import ErrorState from '../components/ErrorState'
import LeadCardList from '../components/LeadCardList'
import LeadListSkeleton from '../components/LeadListSkeleton'
import LeadTable from '../components/LeadTable'
import Pagination from '../components/Pagination'
import { useDebouncedCallback } from '../hooks/useDebouncedCallback'
import { useDocumentTitle } from '../hooks/useDocumentTitle'
import { useLeads } from '../hooks/useLeads'
import { useNow } from '../hooks/useNow'
import { PAGE_SIZE, STATUS_LABELS } from '../lib/constants'
import {
  MAX_SEARCH_LENGTH,
  hasActiveFilters,
  parseListParams,
  toSearchParams,
  type ListFilters,
} from '../lib/listParams'

const SEARCH_DEBOUNCE_MS = 300

export default function LeadListPage() {
  const location = useLocation()
  const [searchParams, setSearchParams] = useSearchParams()
  const filters = parseListParams(searchParams)
  const canonical = toSearchParams(filters).toString()

  /**
   * Every change goes through the URL. `replace` for typing and filter changes (no history entry
   * per keystroke or dropdown pick); pagination uses plain links, which push history instead.
   * The functional form reads the *current* URL, so a debounced call never applies stale state.
   */
  const updateFilters = (patch: Partial<ListFilters>) =>
    setSearchParams((current) => toSearchParams({ ...parseListParams(current), ...patch }), {
      replace: true,
    })

  // Normalize hand-edited or stale URLs (status=FOO, page=abc, unknown params) in place.
  useEffect(() => {
    if (searchParams.toString() !== canonical) setSearchParams(canonical, { replace: true })
  }, [searchParams, canonical, setSearchParams])

  // The input updates instantly; only the URL (and so the request) waits for a pause in typing.
  const [searchInput, setSearchInput] = useState(filters.search)
  const [runSearch, cancelSearch] = useDebouncedCallback((value: string) => {
    updateFilters({ search: value.trim().slice(0, MAX_SEARCH_LENGTH), page: 1 })
  }, SEARCH_DEBOUNCE_MS)

  // When the URL's search changes from elsewhere (Back, "Clear filters"), mirror it into the
  // input: React's "adjust state when a prop changes" pattern, done during render, no effect.
  const [lastUrlSearch, setLastUrlSearch] = useState(filters.search)
  if (filters.search !== lastUrlSearch) {
    setLastUrlSearch(filters.search)
    if (filters.search !== searchInput.trim()) setSearchInput(filters.search)
  }

  const clearFilters = () => {
    cancelSearch() // a pending keystroke must not re-apply the old search afterwards
    setSearchInput('')
    updateFilters({ search: '', status: undefined, page: 1 })
  }

  const { data, error, isPending, isError, isFetching, isPlaceholderData, refetch } = useLeads({
    page: filters.page,
    limit: PAGE_SIZE,
    status: filters.status,
    search: filters.search || undefined,
  })
  const now = useNow()
  useDocumentTitle('Leads')

  // A page past the end (stale link, or filters shrank the result) → the last real page. Only
  // decided on real data for the current query, never on the previous page's placeholder.
  const totalPages = data?.pagination.totalPages
  useEffect(() => {
    if (isPlaceholderData || totalPages === undefined) return
    const lastPage = Math.max(totalPages, 1)
    if (filters.page > lastPage) {
      setSearchParams(toSearchParams({ ...filters, page: lastPage }), { replace: true })
    }
  }, [isPlaceholderData, totalPages, filters, setSearchParams])

  const total = data?.pagination.total
  const filtered = hasActiveFilters(filters)
  // Passed to the detail page so its back link can return to this exact view.
  const linkState = { listSearch: location.search }

  return (
    <section>
      <div className="flex items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Leads</h1>
          <p className="mt-1 text-sm text-zinc-600">Leads received from Meta Ads.</p>
        </div>
        {/* Announced to screen readers whenever the result count changes. */}
        <p aria-live="polite" className="text-sm text-zinc-500">
          {total !== undefined &&
            `${total} ${filtered ? 'matching ' : ''}${total === 1 ? 'lead' : 'leads'}`}
        </p>
      </div>

      <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-center">
        <label className="relative flex-1">
          <span className="sr-only">Search leads by name, email or phone</span>
          <input
            type="search"
            value={searchInput}
            maxLength={MAX_SEARCH_LENGTH}
            onChange={(event) => {
              setSearchInput(event.target.value)
              runSearch(event.target.value)
            }}
            placeholder="Search name, email or phone…"
            className="w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm placeholder:text-zinc-400 focus-visible:border-accent-600"
          />
        </label>
        <label className="flex items-center gap-2 text-sm text-zinc-600">
          Status
          <select
            value={filters.status ?? ''}
            onChange={(event) => {
              const value = event.target.value
              updateFilters({ status: isLeadStatus(value) ? value : undefined, page: 1 })
            }}
            className="rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900"
          >
            <option value="">All statuses</option>
            {LEAD_STATUSES.map((status) => (
              <option key={status} value={status}>
                {STATUS_LABELS[status]}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="mt-4">
        {isPending ? (
          <LeadListSkeleton />
        ) : isError ? (
          <ErrorState error={error} onRetry={() => void refetch()} retrying={isFetching} />
        ) : data.data.length === 0 && filtered ? (
          <EmptyState
            title="No leads match these filters"
            description="Try a different search term or status."
            action={
              <button
                type="button"
                onClick={clearFilters}
                className="rounded-md bg-accent-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-accent-700"
              >
                Clear filters
              </button>
            }
          />
        ) : data.data.length === 0 ? (
          <EmptyState
            title="No leads yet"
            description={
              <>
                Leads appear here as Meta webhooks arrive. Locally, send one with{' '}
                <code className="font-mono text-xs">scripts/send_test_webhook.py</code> or run{' '}
                <code className="font-mono text-xs">python -m scripts.seed</code>.
              </>
            }
          />
        ) : (
          // While the next page/filter loads, the current rows stay visible but dimmed.
          <div
            aria-busy={isPlaceholderData}
            className={isPlaceholderData ? 'opacity-60 transition-opacity' : 'transition-opacity'}
          >
            {isPlaceholderData && (
              <p className="mb-2 text-xs text-zinc-500" role="status">
                Updating…
              </p>
            )}
            <div className="hidden md:block">
              <LeadTable leads={data.data} now={now} linkState={linkState} />
            </div>
            <div className="md:hidden">
              <LeadCardList leads={data.data} now={now} linkState={linkState} />
            </div>
            <Pagination
              page={data.pagination.page}
              totalPages={data.pagination.totalPages}
              total={data.pagination.total}
              limit={data.pagination.limit}
            />
          </div>
        )}
      </div>
    </section>
  )
}
