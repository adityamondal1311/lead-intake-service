import {
  isLeadStatus,
  type Activity,
  type FieldChange,
  type LeadUpdatedDetails,
  type TypedActivity,
} from '../api/types'
import { formatDateTime } from './format'

type Json = Record<string, unknown>

const isObject = (value: unknown): value is Json =>
  typeof value === 'object' && value !== null && !Array.isArray(value)

const optionalString = (value: unknown): string | undefined =>
  typeof value === 'string' ? value : undefined

const isChangeValue = (value: unknown): value is string | null =>
  typeof value === 'string' || value === null

function isFieldChange(value: unknown): value is FieldChange {
  return isObject(value) && isChangeValue(value.from) && isChangeValue(value.to)
}

/**
 * Checks an activity's actual shape and returns it typed, or null if it does not match what its
 * type promises (the timeline then shows a generic line instead of crashing). The API contract
 * says this never happens; the check is what makes that a guarantee on this side.
 */
export function parseActivity(activity: Activity): TypedActivity | null {
  const { id, actor, createdAt, details } = activity
  if (!isObject(details)) return null
  const base = { id, actor, createdAt }

  switch (activity.type) {
    case 'LEAD_CREATED':
      if (typeof details.source !== 'string') return null
      return {
        ...base,
        type: 'LEAD_CREATED',
        details: {
          source: details.source,
          webhookEventId: optionalString(details.webhookEventId),
          externalEventId: optionalString(details.externalEventId),
        },
      }
    case 'LEAD_UPDATED': {
      const { changes } = details
      if (!isObject(changes) || !Object.values(changes).every(isFieldChange)) return null
      return {
        ...base,
        type: 'LEAD_UPDATED',
        details: {
          changes: changes as LeadUpdatedDetails['changes'],
          webhookEventId: optionalString(details.webhookEventId),
          externalEventId: optionalString(details.externalEventId),
        },
      }
    }
    case 'STATUS_CHANGED':
      if (!isLeadStatus(details.from) || !isLeadStatus(details.to)) return null
      return { ...base, type: 'STATUS_CHANGED', details: { from: details.from, to: details.to } }
    default:
      return null
  }
}

const ACTOR_LABELS: Record<string, string> = {
  'system:meta_webhook': 'Meta webhook',
  'user:dashboard': 'Dashboard',
}

export function actorLabel(actor: string): string {
  return ACTOR_LABELS[actor] ?? actor
}

const FIELD_LABELS: Record<string, string> = {
  fullName: 'Name',
  email: 'Email',
  phone: 'Phone',
  campaignId: 'Campaign',
  formId: 'Form',
  adId: 'Ad',
  metaCreatedAt: 'Submitted on Meta',
}

export function fieldLabel(field: string): string {
  return FIELD_LABELS[field] ?? field
}

/** A changed value as a person reads it: dates formatted, empty shown as an em dash. */
export function formatChangeValue(field: string, value: string | null): string {
  if (value === null || value === '') return '—'
  return field === 'metaCreatedAt' ? formatDateTime(value) : value
}
