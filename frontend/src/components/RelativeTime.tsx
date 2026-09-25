import { formatDateTime, formatRelative } from '../lib/format'

/** "5 minutes ago", with the exact date and time on hover and in the machine-readable attribute. */
export default function RelativeTime({ iso, now }: { iso: string; now: number }) {
  return (
    <time dateTime={iso} title={formatDateTime(iso)}>
      {formatRelative(iso, now)}
    </time>
  )
}
