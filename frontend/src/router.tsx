import { createBrowserRouter, type RouteObject } from 'react-router'

import AppLayout from './components/AppLayout'
import LeadDetailPage from './pages/LeadDetailPage'
import LeadListPage from './pages/LeadListPage'
import NotFoundPage from './pages/NotFoundPage'
import RouteErrorPage from './pages/RouteErrorPage'

// Exported so tests render the real route table (in a memory router) rather than a copy.
export const routes: RouteObject[] = [
  {
    element: <AppLayout />,
    errorElement: <RouteErrorPage />,
    children: [
      { index: true, element: <LeadListPage /> },
      { path: 'leads/:leadId', element: <LeadDetailPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
]

export const router = createBrowserRouter(routes)
