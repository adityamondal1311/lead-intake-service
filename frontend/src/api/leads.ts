import { apiFetch } from './client'
import type { LeadDetailResponse, LeadListParams, LeadListResponse } from './types'

export function getLeads(params: LeadListParams, signal?: AbortSignal): Promise<LeadListResponse> {
  return apiFetch<LeadListResponse>('/leads', { query: { ...params }, signal })
}

export function getLead(id: string, signal?: AbortSignal): Promise<LeadDetailResponse> {
  return apiFetch<LeadDetailResponse>(`/leads/${encodeURIComponent(id)}`, { signal })
}
