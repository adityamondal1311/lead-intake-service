// Pure date formatting with the browser's Intl API (no date library). `now` is a parameter so
// callers can re-render relative times as time passes, and tests can fix the clock.

const absoluteFormat = new Intl.DateTimeFormat(undefined, {
  dateStyle: 'medium',
  timeStyle: 'short',
})
const relativeFormat = new Intl.RelativeTimeFormat(undefined, { numeric: 'auto' })

const MINUTE = 60_000
const HOUR = 60 * MINUTE
const DAY = 24 * HOUR

/** e.g. "24 Sep 2026, 3:30 pm" in the viewer's locale and time zone. */
export function formatDateTime(iso: string): string {
  return absoluteFormat.format(new Date(iso))
}

/** e.g. "just now", "5 minutes ago", "yesterday", "3 days ago"; older than a week → date. */
export function formatRelative(iso: string, now: number): string {
  const diff = new Date(iso).getTime() - now
  const abs = Math.abs(diff)
  if (abs < MINUTE) return 'just now'
  if (abs < HOUR) return relativeFormat.format(Math.round(diff / MINUTE), 'minute')
  if (abs < DAY) return relativeFormat.format(Math.round(diff / HOUR), 'hour')
  if (abs < 7 * DAY) return relativeFormat.format(Math.round(diff / DAY), 'day')
  return formatDateTime(iso)
}
