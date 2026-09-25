import EmptyState from '../components/EmptyState'
import ErrorState from '../components/ErrorState'
import LeadListSkeleton from '../components/LeadListSkeleton'
import LeadTable from '../components/LeadTable'
import { useLeads } from '../hooks/useLeads'
import { useNow } from '../hooks/useNow'
import { PAGE_SIZE } from '../lib/constants'

export default function LeadListPage() {
  const { data, error, isPending, isError, isFetching, refetch } = useLeads({
    page: 1,
    limit: PAGE_SIZE,
  })
  const now = useNow()
  const total = data?.pagination.total

  return (
    <section>
      <div className="flex items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Leads</h1>
          <p className="mt-1 text-sm text-zinc-600">Leads received from Meta Ads.</p>
        </div>
        {/* Announced to screen readers whenever the result count changes. */}
        <p aria-live="polite" className="text-sm text-zinc-500">
          {total !== undefined && `${total} ${total === 1 ? 'lead' : 'leads'}`}
        </p>
      </div>

      <div className="mt-6">
        {isPending ? (
          <LeadListSkeleton />
        ) : isError ? (
          <ErrorState error={error} onRetry={() => void refetch()} retrying={isFetching} />
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
          <LeadTable leads={data.data} now={now} />
        )}
      </div>
    </section>
  )
}
