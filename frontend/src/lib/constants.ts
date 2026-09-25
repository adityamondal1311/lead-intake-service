import type { LeadStatus } from '../api/types'

export const STATUS_LABELS: Record<LeadStatus, string> = {
  NEW: 'New',
  CONTACTED: 'Contacted',
  QUALIFIED: 'Qualified',
  CONVERTED: 'Converted',
  LOST: 'Lost',
}

// Status colours are semantic and only used for status. The badge always shows the label too,
// so colour is never the only way to tell statuses apart.
export const STATUS_BADGE_CLASSES: Record<LeadStatus, string> = {
  NEW: 'bg-blue-50 text-blue-700 ring-blue-600/20',
  CONTACTED: 'bg-amber-50 text-amber-800 ring-amber-600/25',
  QUALIFIED: 'bg-violet-50 text-violet-700 ring-violet-600/20',
  CONVERTED: 'bg-green-50 text-green-700 ring-green-600/20',
  LOST: 'bg-zinc-100 text-zinc-600 ring-zinc-500/20',
}

export const STATUS_DOT_CLASSES: Record<LeadStatus, string> = {
  NEW: 'bg-blue-500',
  CONTACTED: 'bg-amber-500',
  QUALIFIED: 'bg-violet-500',
  CONVERTED: 'bg-green-500',
  LOST: 'bg-zinc-400',
}

const SOURCE_LABELS: Record<string, string> = { META_ADS: 'Meta Ads' }

export function sourceLabel(source: string): string {
  return SOURCE_LABELS[source] ?? source
}

export const PAGE_SIZE = 20
