/**
 * A stateful, in-memory fake of the backend API for tests, served through MSW.
 *
 * MSW intercepts `fetch` at the network boundary, so the app's real API client (URL building,
 * JSON, error envelope → ApiError, AbortSignal) runs in every test. The fake keeps state: a PATCH
 * changes what later GETs return, so flows like "update status, go back, see it in the list" are
 * tested rather than scripted. It follows the backend contract (README "API"): newest first,
 * case-insensitive search on name/email/phone, pagination, 404/422 envelopes, no-op PATCH.
 */
import { http, HttpResponse } from 'msw'

import type { Activity, LeadDetail, LeadStatus } from '../api/types'
import { LEAD_STATUSES } from '../api/types'

export const API = 'http://localhost:8000'

interface FakeState {
  leads: LeadDetail[]
  activities: Map<string, Activity[]>
  /** Every request the fake answered, for asserting how many were sent and with what. */
  requests: { method: string; path: string; params: URLSearchParams; body: unknown }[]
  nextId: number
}

export const db: FakeState = { leads: [], activities: new Map(), requests: [], nextId: 1 }

export function resetDb() {
  db.leads = []
  db.activities = new Map()
  db.requests = []
  db.nextId = 1
}

const id = (n: number) => `00000000-0000-4000-8000-${String(n).padStart(12, '0')}`
const BASE_TIME = Date.parse('2026-09-24T10:00:00Z')

/** Adds a lead (n-th added is n minutes newer) with a LEAD_CREATED activity; returns it. */
export function addLead(overrides: Partial<LeadDetail> = {}, activities?: Activity[]): LeadDetail {
  const n = db.nextId++
  const createdAt = new Date(BASE_TIME + n * 60_000).toISOString()
  const lead: LeadDetail = {
    id: id(n),
    externalId: `meta_lead_${n}`,
    fullName: `Lead ${n}`,
    email: `lead${n}@example.com`,
    phone: `+9190000${String(n).padStart(5, '0')}`,
    status: 'NEW',
    source: 'META_ADS',
    campaignId: 'cmp_1',
    formId: 'form_1',
    adId: 'ad_1',
    metaCreatedAt: createdAt,
    createdAt,
    updatedAt: createdAt,
    ...overrides,
  }
  db.leads.push(lead)
  db.activities.set(
    lead.id,
    activities ?? [
      {
        id: id(100_000 + n),
        type: 'LEAD_CREATED',
        actor: 'system:meta_webhook',
        details: { source: 'META_ADS', externalEventId: `evt_${n}` },
        createdAt,
      },
    ],
  )
  return lead
}

export function errorBody(code: string, message: string, requestId = 'req-test-1', details: unknown = null) {
  return { error: { code, message, details, requestId } }
}

export function errorResponse(status: number, code: string, message: string, requestId?: string) {
  return HttpResponse.json(errorBody(code, message, requestId), { status })
}

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

function summary(lead: LeadDetail) {
  const { id, fullName, email, phone, status, source, campaignId, createdAt } = lead
  return { id, fullName, email, phone, status, source, campaignId, createdAt }
}

function record(request: Request, body: unknown = null) {
  const url = new URL(request.url)
  db.requests.push({ method: request.method, path: url.pathname, params: url.searchParams, body })
}

export const handlers = [
  http.get(`${API}/leads`, ({ request }) => {
    record(request)
    const params = new URL(request.url).searchParams
    const page = Number(params.get('page') ?? 1)
    const limit = Number(params.get('limit') ?? 20)
    const status = params.get('status')
    const search = (params.get('search') ?? '').toLowerCase()
    if (!Number.isInteger(page) || page < 1 || (status && !LEAD_STATUSES.includes(status as LeadStatus))) {
      return errorResponse(422, 'VALIDATION_ERROR', 'Request validation failed')
    }
    const matching = db.leads
      .filter((lead) => !status || lead.status === status)
      .filter(
        (lead) =>
          !search ||
          [lead.fullName, lead.email, lead.phone].some((v) => v?.toLowerCase().includes(search)),
      )
      .sort((a, b) => b.createdAt.localeCompare(a.createdAt))
    const total = matching.length
    return HttpResponse.json({
      data: matching.slice((page - 1) * limit, page * limit).map(summary),
      pagination: { page, limit, total, totalPages: Math.ceil(total / limit) },
    })
  }),

  http.get(`${API}/leads/:id`, ({ request, params }) => {
    record(request)
    const leadId = String(params.id)
    if (!UUID.test(leadId)) return errorResponse(422, 'VALIDATION_ERROR', 'Request validation failed')
    const lead = db.leads.find((l) => l.id === leadId)
    if (!lead) return errorResponse(404, 'LEAD_NOT_FOUND', 'Lead not found')
    return HttpResponse.json({ lead, activities: db.activities.get(lead.id) ?? [] })
  }),

  http.patch(`${API}/leads/:id/status`, async ({ request, params }) => {
    const body = (await request.json()) as { status?: string }
    record(request, body)
    const lead = db.leads.find((l) => l.id === String(params.id))
    if (!lead) return errorResponse(404, 'LEAD_NOT_FOUND', 'Lead not found')
    const next = body.status as LeadStatus
    if (!LEAD_STATUSES.includes(next)) {
      return errorResponse(422, 'VALIDATION_ERROR', 'Request validation failed')
    }
    if (lead.status === next) return HttpResponse.json({ lead, activity: null })

    const activity: Activity = {
      id: id(200_000 + db.nextId++),
      type: 'STATUS_CHANGED',
      actor: 'user:dashboard',
      details: { from: lead.status, to: next },
      createdAt: new Date().toISOString(),
    }
    lead.status = next
    lead.updatedAt = activity.createdAt
    db.activities.set(lead.id, [activity, ...(db.activities.get(lead.id) ?? [])])
    return HttpResponse.json({ lead, activity })
  }),
]

/** Requests the fake answered, filtered by method and path. */
export function requestsTo(method: string, path: string) {
  return db.requests.filter((r) => r.method === method && r.path === path)
}
