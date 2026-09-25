import { Link, useLocation, useParams } from 'react-router'

import ActivityTimeline from '../components/ActivityTimeline'
import ErrorState from '../components/ErrorState'
import LeadDetailSkeleton from '../components/LeadDetailSkeleton'
import LeadDetailsCard from '../components/LeadDetailsCard'
import RelativeTime from '../components/RelativeTime'
import StatusBadge from '../components/StatusBadge'
import { useDocumentTitle } from '../hooks/useDocumentTitle'
import { isLeadNotFound, useLead } from '../hooks/useLead'
import { useNow } from '../hooks/useNow'
import { sourceLabel } from '../lib/constants'

/**
 * Where "Back to leads" goes: the exact list view the user came from (search, status, page),
 * handed over by the list as router state. Opened directly (bookmark, shared link) → "/".
 * Pure navigation state: the API never sees it.
 */
function useBackToList(): string {
  const state: unknown = useLocation().state
  const listSearch =
    typeof state === 'object' && state !== null && 'listSearch' in state
      ? (state as { listSearch: unknown }).listSearch
      : undefined
  return typeof listSearch === 'string' && listSearch.startsWith('?') ? `/${listSearch}` : '/'
}

export default function LeadDetailPage() {
  const { leadId = '' } = useParams()
  const backTo = useBackToList()
  const { data, error, isPending, isError, isFetching, refetch } = useLead(leadId)
  const now = useNow()
  const notFound = isError && isLeadNotFound(error)

  useDocumentTitle(data?.lead.fullName ?? (notFound ? 'Lead not found' : undefined))

  const backLink = (
    <Link
      to={backTo}
      className="inline-flex items-center gap-1 rounded text-sm text-zinc-600 hover:text-zinc-900"
    >
      <span aria-hidden="true">←</span> Back to leads
    </Link>
  )

  if (isPending) {
    return (
      <>
        {backLink}
        <div className="mt-4">
          <LeadDetailSkeleton />
        </div>
      </>
    )
  }

  if (notFound) {
    return (
      <>
        {backLink}
        <section className="mx-auto max-w-md py-16 text-center">
          <h1 className="text-2xl font-semibold tracking-tight">Lead not found</h1>
          <p className="mt-2 text-sm text-zinc-600">
            There is no lead at this address. It may have been removed, or the link is incomplete.
          </p>
        </section>
      </>
    )
  }

  if (isError) {
    return (
      <>
        {backLink}
        <div className="mt-4">
          <ErrorState error={error} onRetry={() => void refetch()} retrying={isFetching} />
        </div>
      </>
    )
  }

  const { lead } = data

  return (
    <>
      {backLink}
      <header className="mt-4 flex flex-wrap items-center gap-x-3 gap-y-2">
        <h1 className="text-2xl font-semibold tracking-tight">{lead.fullName}</h1>
        <StatusBadge status={lead.status} />
      </header>
      <p className="mt-1 text-sm text-zinc-600">
        Created <RelativeTime iso={lead.createdAt} now={now} /> · via {sourceLabel(lead.source)}
      </p>

      {/* Desktop: details left, activity right. Phone: activity first (what changed matters
          most), details below. */}
      <div className="mt-6 grid gap-6 lg:grid-cols-5">
        <div className="lg:col-span-2">
          <LeadDetailsCard lead={lead} />
        </div>
        <section
          aria-labelledby="activity-heading"
          className="order-first rounded-lg border border-zinc-200 bg-white p-5 lg:order-none lg:col-span-3"
        >
          <h2 id="activity-heading" className="text-sm font-semibold text-zinc-900">
            Activity
          </h2>
          <div className="mt-4">
            <ActivityTimeline activities={data.activities} now={now} />
          </div>
        </section>
      </div>
    </>
  )
}
