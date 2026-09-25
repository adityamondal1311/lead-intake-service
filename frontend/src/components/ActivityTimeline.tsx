import type { ReactNode } from 'react'

import type { Activity, TypedActivity } from '../api/types'
import {
  actorLabel,
  fieldLabel,
  formatChangeValue,
  parseActivity,
} from '../lib/activities'
import { sourceLabel } from '../lib/constants'
import RelativeTime from './RelativeTime'
import StatusBadge from './StatusBadge'

type Tone = 'created' | 'updated' | 'status' | 'other'

const TONE_CLASSES: Record<Tone, string> = {
  created: 'bg-accent-100 text-accent-700',
  updated: 'bg-sky-100 text-sky-700',
  status: 'bg-amber-100 text-amber-800',
  other: 'bg-zinc-100 text-zinc-500',
}

// Small inline icons (no icon library). Decorative: the sentence next to each says what happened.
const ICONS: Record<Tone, ReactNode> = {
  created: <path d="M8 3v10M3 8h10" />,
  updated: <path d="M3 13h3l7-7-3-3-7 7v3z" />,
  status: <path d="M3 5h8l-2-2M13 11H5l2 2" />,
  other: <circle cx="8" cy="8" r="2" />,
}

function toneOf(activity: TypedActivity | null): Tone {
  if (!activity) return 'other'
  return activity.type === 'LEAD_CREATED'
    ? 'created'
    : activity.type === 'LEAD_UPDATED'
      ? 'updated'
      : 'status'
}

function EventId({ value }: { value?: string }) {
  if (!value) return null
  return (
    <code title={value} className="truncate font-mono text-zinc-400">
      {value}
    </code>
  )
}

/** The human-readable body of one entry. */
function Description({ activity }: { activity: TypedActivity | null }) {
  if (!activity) {
    return <p className="text-sm font-medium text-zinc-900">Activity recorded</p>
  }
  switch (activity.type) {
    case 'LEAD_CREATED':
      return (
        <p className="text-sm font-medium text-zinc-900">
          Lead created from {sourceLabel(activity.details.source)}
        </p>
      )
    case 'LEAD_UPDATED': {
      const changes = Object.entries(activity.details.changes)
      return (
        <>
          <p className="text-sm font-medium text-zinc-900">
            Lead updated: {changes.map(([field]) => fieldLabel(field).toLowerCase()).join(', ')}
          </p>
          <dl className="mt-1.5 space-y-1 text-sm">
            {changes.map(([field, change]) => (
              <div key={field} className="flex flex-wrap items-baseline gap-x-2">
                <dt className="text-zinc-500">{fieldLabel(field)}</dt>
                <dd className="min-w-0 break-words text-zinc-700">
                  <span className="text-zinc-500 line-through decoration-zinc-300">
                    {formatChangeValue(field, change.from)}
                  </span>
                  <span aria-hidden="true"> → </span>
                  <span className="sr-only"> changed to </span>
                  {formatChangeValue(field, change.to)}
                </dd>
              </div>
            ))}
          </dl>
        </>
      )
    }
    case 'STATUS_CHANGED':
      return (
        <div className="flex flex-wrap items-center gap-1.5 text-sm font-medium text-zinc-900">
          Status changed from <StatusBadge status={activity.details.from} /> to{' '}
          <StatusBadge status={activity.details.to} />
        </div>
      )
  }
}

/** The lead's audit trail, in the order the API returns it (newest first). */
export default function ActivityTimeline({
  activities,
  now,
}: {
  activities: Activity[]
  now: number
}) {
  if (activities.length === 0) {
    return <p className="text-sm text-zinc-500">No activity recorded yet.</p>
  }

  return (
    <ol aria-label="Activity" className="space-y-0">
      {activities.map((raw, index) => {
        const activity = parseActivity(raw)
        const tone = toneOf(activity)
        const isLast = index === activities.length - 1
        const eventId =
          activity && activity.type !== 'STATUS_CHANGED'
            ? activity.details.externalEventId
            : undefined
        return (
          <li key={raw.id} className="relative flex gap-3 pb-5 last:pb-0">
            {!isLast && (
              <span aria-hidden="true" className="absolute top-8 bottom-0 left-3.5 w-px bg-zinc-200" />
            )}
            <span
              aria-hidden="true"
              className={`relative flex size-7 shrink-0 items-center justify-center rounded-full ${TONE_CLASSES[tone]}`}
            >
              <svg
                viewBox="0 0 16 16"
                className="size-3.5"
                fill="none"
                stroke="currentColor"
                strokeWidth={1.75}
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                {ICONS[tone]}
              </svg>
            </span>
            <div className="min-w-0 flex-1 pt-1">
              <Description activity={activity} />
              <p className="mt-1 flex min-w-0 flex-wrap items-center gap-x-1.5 text-xs text-zinc-500">
                <span>by {actorLabel(raw.actor)}</span>
                <span aria-hidden="true">·</span>
                <RelativeTime iso={raw.createdAt} now={now} />
                {eventId && (
                  <>
                    <span aria-hidden="true">·</span>
                    <EventId value={eventId} />
                  </>
                )}
              </p>
            </div>
          </li>
        )
      })}
    </ol>
  )
}
