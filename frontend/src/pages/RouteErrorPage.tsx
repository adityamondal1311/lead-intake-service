import { Link } from 'react-router'

/**
 * Shown if rendering a page throws. Without it, React Router shows its developer error screen;
 * with it, the user gets a way back and the error still reaches the browser console.
 */
export default function RouteErrorPage() {
  return (
    <section className="mx-auto max-w-md px-4 py-16 text-center">
      <h1 className="text-2xl font-semibold tracking-tight">Something went wrong</h1>
      <p className="mt-2 text-sm text-zinc-600">
        This page failed to load. Reloading usually helps; if it keeps happening, the details are
        in the browser console.
      </p>
      <Link
        to="/"
        reloadDocument
        className="mt-6 inline-block rounded-md bg-accent-600 px-4 py-2 text-sm font-medium text-white hover:bg-accent-700"
      >
        Back to leads
      </Link>
    </section>
  )
}
