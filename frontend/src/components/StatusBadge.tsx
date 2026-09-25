import type { LeadStatus } from '../api/types'
import { STATUS_BADGE_CLASSES, STATUS_DOT_CLASSES, STATUS_LABELS } from '../lib/constants'

export default function StatusBadge({ status }: { status: LeadStatus }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${STATUS_BADGE_CLASSES[status]}`}
    >
      <span aria-hidden="true" className={`size-1.5 rounded-full ${STATUS_DOT_CLASSES[status]}`} />
      {STATUS_LABELS[status]}
    </span>
  )
}
