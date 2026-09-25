import { describe, expect, it } from 'vitest'

import type { Activity } from '../api/types'
import { actorLabel, fieldLabel, formatChangeValue, parseActivity } from './activities'
import { formatDateTime } from './format'

const activity = (type: string, details: unknown): Activity => ({
  id: 'a1',
  type,
  actor: 'system:meta_webhook',
  details,
  createdAt: '2026-09-24T10:00:00Z',
})

describe('parseActivity: valid shapes are typed', () => {
  it('LEAD_CREATED', () => {
    const parsed = parseActivity(
      activity('LEAD_CREATED', { source: 'META_ADS', externalEventId: 'evt_1', webhookEventId: 'w1' }),
    )
    expect(parsed).toMatchObject({
      type: 'LEAD_CREATED',
      details: { source: 'META_ADS', externalEventId: 'evt_1', webhookEventId: 'w1' },
    })
  })

  it('LEAD_UPDATED, including a change to or from an empty value', () => {
    const changes = { phone: { from: '+911', to: '+912' }, email: { from: null, to: 'a@b.co' } }
    expect(parseActivity(activity('LEAD_UPDATED', { changes }))).toMatchObject({
      type: 'LEAD_UPDATED',
      details: { changes },
    })
  })

  it('STATUS_CHANGED', () => {
    expect(parseActivity(activity('STATUS_CHANGED', { from: 'NEW', to: 'LOST' }))).toMatchObject({
      type: 'STATUS_CHANGED',
      details: { from: 'NEW', to: 'LOST' },
    })
  })
})

describe('parseActivity: anything unexpected → null (rendered as a generic entry)', () => {
  it.each([
    ['unknown type', activity('LEAD_DELETED', {})],
    ['details not an object', activity('LEAD_CREATED', 'oops')],
    ['details null', activity('STATUS_CHANGED', null)],
    ['details an array', activity('STATUS_CHANGED', ['NEW'])],
    ['created without source', activity('LEAD_CREATED', {})],
    ['updated without changes', activity('LEAD_UPDATED', { externalEventId: 'evt' })],
    ['updated with a malformed change', activity('LEAD_UPDATED', { changes: { phone: '+912' } })],
    ['status with an unknown status', activity('STATUS_CHANGED', { from: 'NEW', to: 'WON' })],
    ['status missing "from"', activity('STATUS_CHANGED', { to: 'LOST' })],
  ])('%s', (_, input) => {
    expect(parseActivity(input)).toBeNull()
  })
})

describe('labels and values for people', () => {
  it('names known actors and falls back to the raw value', () => {
    expect(actorLabel('system:meta_webhook')).toBe('Meta webhook')
    expect(actorLabel('user:dashboard')).toBe('Dashboard')
    expect(actorLabel('user:42')).toBe('user:42')
  })

  it('labels fields and formats changed values', () => {
    expect(fieldLabel('campaignId')).toBe('Campaign')
    expect(fieldLabel('metaCreatedAt')).toBe('Submitted on Meta')
    expect(formatChangeValue('phone', null)).toBe('—')
    expect(formatChangeValue('metaCreatedAt', '2026-09-24T10:00:00Z')).toBe(
      formatDateTime('2026-09-24T10:00:00Z'),
    )
  })
})
