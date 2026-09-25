import { Link } from 'react-router'

import { useDocumentTitle } from '../hooks/useDocumentTitle'

export default function NotFoundPage() {
  useDocumentTitle('Page not found')
  return (
    <section className="mx-auto max-w-md py-16 text-center">
      <p className="text-sm font-semibold text-accent-600">404</p>
      <h1 className="mt-2 text-2xl font-semibold tracking-tight">Page not found</h1>
      <p className="mt-2 text-sm text-zinc-600">
        The page you are looking for does not exist or has moved.
      </p>
      <Link
        to="/"
        className="mt-6 inline-block rounded-md bg-accent-600 px-4 py-2 text-sm font-medium text-white hover:bg-accent-700"
      >
        Back to leads
      </Link>
    </section>
  )
}
