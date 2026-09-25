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
