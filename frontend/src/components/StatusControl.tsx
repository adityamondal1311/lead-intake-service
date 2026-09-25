import { ApiError } from '../api/client'
import { LEAD_STATUSES, isLeadStatus, type LeadStatus } from '../api/types'
import { useUpdateLeadStatus } from '../hooks/useUpdateLeadStatus'
import { STATUS_LABELS } from '../lib/constants'

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.isNetworkError) return "Couldn't reach the server."
    if (error.status >= 500) return 'The server hit an unexpected error.'
    return error.message
  }
  return 'An unexpected error occurred.'
}

/**
 * The status <select>. `status` is the server's value. While a change is being saved the select
 * shows the requested value, disabled, next to "Saving…": that displays the request, not a
 * result; the badge and timeline keep showing server data until the server confirms. On failure
 * the select returns to the server's value and the error is shown with its request id.
 */
export default function StatusControl({ leadId, status }: { leadId: string; status: LeadStatus }) {
  const mutation = useUpdateLeadStatus(leadId)
  const shown = mutation.isPending ? mutation.variables : status
  const requestId = mutation.error instanceof ApiError ? mutation.error.requestId : null

  return (
    <div>
      <div className="flex flex-wrap items-center gap-3">
        <label htmlFor="lead-status" className="text-sm font-semibold text-zinc-900">
          Status
        </label>
        <select
          id="lead-status"
          value={shown}
          // Disabled until the request settles: no second PATCH while one is in flight.
          disabled={mutation.isPending}
          aria-describedby="lead-status-feedback"
          onChange={(event) => {
            const next = event.target.value
            if (isLeadStatus(next) && next !== status) mutation.mutate(next)
          }}
          className="rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 disabled:cursor-wait disabled:bg-zinc-50 disabled:text-zinc-500"
        >
          {LEAD_STATUSES.map((value) => (
            <option key={value} value={value}>
              {STATUS_LABELS[value]}
            </option>
          ))}
        </select>
        {mutation.isPending && <span className="text-sm text-zinc-500">Saving…</span>}
      </div>

      {/* Polite live region: screen readers hear the outcome of the change. */}
      <div id="lead-status-feedback" aria-live="polite" className="mt-2 text-sm">
        {mutation.isSuccess && (
          <p className="text-green-700">
            {mutation.data.activity
              ? `Status updated to ${STATUS_LABELS[mutation.data.lead.status]}.`
              : `Status was already ${STATUS_LABELS[mutation.data.lead.status]}.`}
          </p>
        )}
        {mutation.isError && (
          <div role="alert" className="text-red-700">
            <p>Couldn't update the status. {errorMessage(mutation.error)}</p>
            {requestId && (
              <p className="mt-0.5 text-xs text-red-700/80">
                Request ID: <code className="font-mono select-all">{requestId}</code>
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
