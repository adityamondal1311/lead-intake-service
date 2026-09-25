// Mirrors the backend's JSON contract (camelCase). Keep in sync with backend/app/schemas.

export const LEAD_STATUSES = ['NEW', 'CONTACTED', 'QUALIFIED', 'CONVERTED', 'LOST'] as const
export type LeadStatus = (typeof LEAD_STATUSES)[number]

export function isLeadStatus(value: unknown): value is LeadStatus {
  return typeof value === 'string' && (LEAD_STATUSES as readonly string[]).includes(value)
}

/** A row in GET /leads. Timestamps are ISO 8601 strings in UTC. */
export interface LeadSummary {
  id: string
  fullName: string
  email: string | null
  phone: string | null
  status: LeadStatus
  source: string
  campaignId: string | null
  createdAt: string
}

/** GET /leads/{id}: everything in the summary plus identifiers and Meta metadata. */
export interface LeadDetail extends LeadSummary {
  externalId: string
  formId: string | null
  adId: string | null
  metaCreatedAt: string | null
  updatedAt: string
}

/**
 * One audit trail entry as it arrives over the network. `details` is deliberately `unknown`
 * here: `parseActivity` (lib/activities.ts) checks its real shape and narrows it to TypedActivity.
 */
export interface Activity {
  id: string
  type: string
  actor: string
  details: unknown
  createdAt: string
}

// The documented details shape of each activity type (see backend activities.details).
export interface LeadCreatedDetails {
  source: string
  webhookEventId?: string
  externalEventId?: string
}

export interface FieldChange {
  from: string | null
  to: string | null
}

export interface LeadUpdatedDetails {
  /** Keyed by API field name (camelCase), e.g. { phone: { from, to } }. */
  changes: Record<string, FieldChange>
  webhookEventId?: string
  externalEventId?: string
}

export interface StatusChangedDetails {
  from: LeadStatus
  to: LeadStatus
}

interface ActivityBase {
  id: string
  actor: string
  createdAt: string
}

/** An activity whose details have been checked: `type` tells TypeScript which details it has. */
export type TypedActivity =
  | (ActivityBase & { type: 'LEAD_CREATED'; details: LeadCreatedDetails })
  | (ActivityBase & { type: 'LEAD_UPDATED'; details: LeadUpdatedDetails })
  | (ActivityBase & { type: 'STATUS_CHANGED'; details: StatusChangedDetails })

export interface LeadDetailResponse {
  lead: LeadDetail
  activities: Activity[] // newest first, as returned by the API
}

export interface Pagination {
  page: number
  limit: number
  total: number
  totalPages: number
}

export interface LeadListResponse {
  data: LeadSummary[]
  pagination: Pagination
}

export interface LeadListParams {
  page: number
  limit: number
  status?: LeadStatus
  search?: string
}

/** The body of every non-2xx response. */
export interface ErrorEnvelope {
  error: {
    code: string
    message: string
    details: unknown
    requestId: string | null
  }
}
