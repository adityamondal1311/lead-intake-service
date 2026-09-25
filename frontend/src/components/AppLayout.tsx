import { Link, Outlet } from 'react-router'

export default function AppLayout() {
  return (
    <div className="min-h-screen">
      {/* First focusable element: lets keyboard users jump past the header. */}
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:rounded-md focus:bg-white focus:px-3 focus:py-2 focus:text-sm focus:shadow"
      >
        Skip to content
      </a>
      <header className="border-b border-zinc-200 bg-white">
        <div className="mx-auto flex h-14 max-w-6xl items-center px-4 sm:px-6">
          <Link to="/" className="flex items-center gap-2 rounded text-sm font-semibold">
            <span aria-hidden="true" className="size-2.5 rounded-full bg-accent-600" />
            Lead Intake
          </Link>
        </div>
      </header>
      <main id="main" className="mx-auto max-w-6xl px-4 py-6 sm:px-6 sm:py-8">
        <Outlet />
      </main>
    </div>
  )
}
