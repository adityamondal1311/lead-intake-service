import { apiFetch } from './client'
import type { LeadListParams, LeadListResponse } from './types'

export function getLeads(params: LeadListParams, signal?: AbortSignal): Promise<LeadListResponse> {
  return apiFetch<LeadListResponse>('/leads', { query: { ...params }, signal })
}
