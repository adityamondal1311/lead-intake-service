import { createBrowserRouter } from 'react-router'

import AppLayout from './components/AppLayout'
import LeadDetailPage from './pages/LeadDetailPage'
import LeadListPage from './pages/LeadListPage'
import NotFoundPage from './pages/NotFoundPage'
import RouteErrorPage from './pages/RouteErrorPage'

export const router = createBrowserRouter([
  {
    element: <AppLayout />,
    errorElement: <RouteErrorPage />,
    children: [
      { index: true, element: <LeadListPage /> },
      { path: 'leads/:leadId', element: <LeadDetailPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
])
