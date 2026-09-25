import { useMutation, useQueryClient } from '@tanstack/react-query'

import { updateLeadStatus } from '../api/leads'
import type { LeadDetailResponse, LeadStatus } from '../api/types'
import { leadQueryKey } from './useLead'

/**
 * Changes a lead's status. Server-authoritative, not optimistic: a status change is an audited
 * domain operation (the backend updates the lead and records STATUS_CHANGED in one transaction),
 * so nothing on screen claims the change happened until the server says it did.
 *
 * On success the PATCH response is written straight into the lead's cache (new status + the new
 * activity on top of the timeline), so the user sees it immediately without another request.
 * Then, success or failure, the lead and the lead list are refetched in the background to
 * reconcile with anything else that changed meanwhile (a webhook update, another user).
 *
 * Mutations are not retried (TanStack's default for mutations): a failed status change is
 * reported, and the user decides whether to try again.
 */
export function useUpdateLeadStatus(leadId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (status: LeadStatus) => updateLeadStatus(leadId, status),
    onSuccess: ({ lead, activity }) => {
      queryClient.setQueryData<LeadDetailResponse>(leadQueryKey(leadId), (current) => {
        if (!current) return current
        const alreadyShown = activity && current.activities.some((a) => a.id === activity.id)
        return {
          lead,
          activities: activity && !alreadyShown ? [activity, ...current.activities] : current.activities,
        }
      })
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: leadQueryKey(leadId) })
      // Prefix match: every cached list page/filter, so the list shows the new status on return.
      void queryClient.invalidateQueries({ queryKey: ['leads'] })
    },
  })
}
