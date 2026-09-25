import { QueryClient } from '@tanstack/react-query'

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Lead data changes when webhooks arrive, so treat it as fresh for a short while only.
      staleTime: 15_000,
    },
  },
})
