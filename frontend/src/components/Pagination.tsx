import { Link, useLocation } from 'react-router'

import { parseListParams, toSearchParams } from '../lib/listParams'
import { pageItems } from '../lib/pagination'

// No display class here: page numbers are 'hidden sm:inline-flex', and a shared inline-flex
// would override that hidden (Tailwind emits inline-flex later), showing them on phones.
const base = 'h-8 min-w-8 items-center justify-center rounded-md px-2.5 text-sm'
const enabled = `${base} text-zinc-700 ring-1 ring-inset ring-zinc-200 bg-white hover:bg-zinc-50`
const disabled = `${base} text-zinc-300 ring-1 ring-inset ring-zinc-100 bg-white cursor-not-allowed`
const current = `${base} bg-accent-600 font-medium text-white`

export default function Pagination({
  page,
  totalPages,
  total,
  limit,
}: {
  page: number
  totalPages: number
  total: number
  limit: number
}) {
  const location = useLocation()
  const filters = parseListParams(new URLSearchParams(location.search))

  // Real links, not buttons: each page is a URL, so it gets a history entry (Back returns to
  // the previous page), can be opened in a new tab, and is keyboard-accessible by default.
  const hrefFor = (target: number) => {
    const qs = toSearchParams({ ...filters, page: target }).toString()
    return qs ? `?${qs}` : location.pathname
  }

  const first = total === 0 ? 0 : (page - 1) * limit + 1
  const last = Math.min(page * limit, total)

  return (
    <div className="mt-4 flex flex-col items-center justify-between gap-3 sm:flex-row">
      <p className="text-sm text-zinc-600">
        Showing <span className="font-medium text-zinc-900">{first}</span>–
        <span className="font-medium text-zinc-900">{last}</span> of{' '}
        <span className="font-medium text-zinc-900">{total}</span>
      </p>
      {totalPages > 1 && (
        <nav aria-label="Pagination" className="flex items-center gap-1">
          {page > 1 ? (
            <Link to={hrefFor(page - 1)} className={`${enabled} inline-flex`} rel="prev">
              ‹ Prev
            </Link>
          ) : (
            <span aria-disabled="true" className={`${disabled} inline-flex`}>
              ‹ Prev
            </span>
          )}
          {/* Page numbers from sm up; on a phone, Prev/Next plus "x of y" fits better. */}
          <span className="px-2 text-sm text-zinc-600 sm:hidden">
            {page} / {totalPages}
          </span>
          {pageItems(page, totalPages).map((item, i) =>
            item === 'gap' ? (
              <span key={`gap-${i}`} aria-hidden="true" className="hidden px-1 text-zinc-400 sm:inline">
                …
              </span>
            ) : item === page ? (
              <span key={item} aria-current="page" className={`${current} hidden sm:inline-flex`}>
                {item}
              </span>
            ) : (
              <Link
                key={item}
                to={hrefFor(item)}
                aria-label={`Page ${item}`}
                className={`${enabled} hidden sm:inline-flex`}
              >
                {item}
              </Link>
            ),
          )}
          {page < totalPages ? (
            <Link to={hrefFor(page + 1)} className={`${enabled} inline-flex`} rel="next">
              Next ›
            </Link>
          ) : (
            <span aria-disabled="true" className={`${disabled} inline-flex`}>
              Next ›
            </span>
          )}
        </nav>
      )}
    </div>
  )
}
