import { Link } from 'react-router'

import type { LeadSummary } from '../api/types'
import RelativeTime from './RelativeTime'
import StatusBadge from './StatusBadge'

/** The phone layout of the lead list: same data as LeadTable, stacked into cards. */
export default function LeadCardList({
  leads,
  now,
  linkState,
}: {
  leads: LeadSummary[]
  now: number
  linkState: unknown
}) {
  return (
    <ul className="space-y-2">
      {leads.map((lead) => (
        <li key={lead.id}>
          <Link
            to={`/leads/${lead.id}`}
            state={linkState}
            className="block rounded-lg border border-zinc-200 bg-white p-4 hover:bg-zinc-50"
          >
            <div className="flex items-start justify-between gap-3">
              <span className="font-medium text-zinc-900">{lead.fullName}</span>
              <StatusBadge status={lead.status} />
            </div>
            <div className="mt-1 space-y-0.5 text-sm text-zinc-600">
              {lead.email && <div className="truncate">{lead.email}</div>}
              {lead.phone && <div>{lead.phone}</div>}
            </div>
            <div className="mt-2 flex items-center justify-between gap-3 text-xs text-zinc-500">
              <span className="truncate">{lead.campaignId ?? 'No campaign'}</span>
              <RelativeTime iso={lead.createdAt} now={now} />
            </div>
          </Link>
        </li>
      ))}
    </ul>
  )
}
