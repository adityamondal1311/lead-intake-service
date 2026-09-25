import { Link } from 'react-router'

import type { LeadSummary } from '../api/types'
import RelativeTime from './RelativeTime'
import StatusBadge from './StatusBadge'

/** The desktop layout of the lead list (the page shows LeadCardList below the md breakpoint). */
export default function LeadTable({
  leads,
  now,
  linkState,
}: {
  leads: LeadSummary[]
  now: number
  linkState: unknown
}) {
  return (
    // overflow-x-auto: at in-between widths the table scrolls sideways rather than cutting columns.
    <div className="overflow-x-auto rounded-lg border border-zinc-200 bg-white">
      {/* table-fixed + set widths: columns keep their positions from page to page instead of
          resizing to each page's content. */}
      <table className="w-full min-w-[720px] table-fixed text-left text-sm">
        <caption className="sr-only">Leads, newest first</caption>
        <thead className="border-b border-zinc-200 bg-zinc-50 text-xs font-medium text-zinc-500">
          <tr>
            <th scope="col" className="w-[22%] px-4 py-2.5">Name</th>
            <th scope="col" className="w-[30%] px-4 py-2.5">Contact</th>
            <th scope="col" className="w-32 px-4 py-2.5">Status</th>
            <th scope="col" className="px-4 py-2.5">Campaign</th>
            <th scope="col" className="w-36 px-4 py-2.5 text-right">Created</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-100">
          {leads.map((lead) => (
            // The whole row is clickable (the link's ::after covers it), but the link itself is
            // the real, keyboard-focusable element; the row is not a div with onClick.
            <tr key={lead.id} className="relative hover:bg-zinc-50">
              <td className="truncate px-4 py-3 font-medium text-zinc-900">
                <Link
                  to={`/leads/${lead.id}`}
                  state={linkState}
                  className="rounded after:absolute after:inset-0 after:content-['']"
                >
                  {lead.fullName}
                </Link>
              </td>
              <td className="px-4 py-3 text-zinc-600">
                <div className="truncate">{lead.email ?? '—'}</div>
                <div className="text-xs text-zinc-500">{lead.phone ?? ''}</div>
              </td>
              <td className="px-4 py-3">
                <StatusBadge status={lead.status} />
              </td>
              <td className="truncate px-4 py-3 text-zinc-600">{lead.campaignId ?? '—'}</td>
              <td className="whitespace-nowrap px-4 py-3 text-right text-zinc-600">
                <RelativeTime iso={lead.createdAt} now={now} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
