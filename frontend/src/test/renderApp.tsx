import { QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter } from 'react-router'
import { RouterProvider } from 'react-router/dom'

import { createQueryClient } from '../lib/queryClient'
import { routes } from '../router'

/**
 * Renders the real app (real routes, real pages, real API client) at `url`, with a fresh query
 * client per test so no cached data leaks between tests. Retries keep the app's policy but with
 * no back-off delay. Returns Testing Library queries, a user-event instance and the router (for
 * asserting the URL and history).
 */
export function renderApp(url = '/') {
  const queryClient = createQueryClient({ retryDelay: 0 })
  const router = createMemoryRouter(routes, { initialEntries: [url] })
  const user = userEvent.setup()
  const view = render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
  return { ...view, user, router, queryClient }
}

/** The router's current search string, e.g. "?search=kumar". */
export function currentSearch(router: ReturnType<typeof createMemoryRouter>): string {
  return router.state.location.search
}
