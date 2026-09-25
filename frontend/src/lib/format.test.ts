import { describe, expect, it } from 'vitest'

import { formatDateTime, formatRelative } from './format'

const NOW = Date.parse('2026-09-24T12:00:00Z')
const ago = (ms: number) => new Date(NOW - ms).toISOString()
const MIN = 60_000
const HOUR = 60 * MIN
const DAY = 24 * HOUR

describe('formatRelative (fixed clock)', () => {
  it.each([
    [10_000, 'just now'],
    [5 * MIN, '5 minutes ago'],
    [3 * HOUR, '3 hours ago'],
    [DAY, 'yesterday'],
    [3 * DAY, '3 days ago'],
  ])('%i ms ago → %s', (ms, text) => {
    expect(formatRelative(ago(ms), NOW)).toBe(text)
  })

  it('falls back to the absolute date after a week', () => {
    expect(formatRelative(ago(10 * DAY), NOW)).toBe(formatDateTime(ago(10 * DAY)))
  })

  it('moves forward as the clock does (it is a pure function of "now")', () => {
    const iso = ago(0)
    expect(formatRelative(iso, NOW)).toBe('just now')
    expect(formatRelative(iso, NOW + 2 * HOUR)).toBe('2 hours ago')
  })
})
