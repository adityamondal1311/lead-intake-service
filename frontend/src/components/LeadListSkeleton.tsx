/** Placeholder rows shaped like the lead table, so the layout does not jump when data arrives. */
export default function LeadListSkeleton({ rows = 8 }: { rows?: number }) {
  return (
    <div
      role="status"
      aria-label="Loading leads"
      className="overflow-hidden rounded-lg border border-zinc-200 bg-white"
    >
      {Array.from({ length: rows }, (_, i) => (
        <div
          key={i}
          className="flex animate-pulse items-center gap-4 border-b border-zinc-100 px-4 py-4 last:border-0"
        >
          <div className="h-3.5 w-1/4 rounded bg-zinc-200" />
          <div className="hidden h-3.5 w-1/4 rounded bg-zinc-100 sm:block" />
          <div className="h-5 w-20 rounded-full bg-zinc-100" />
          <div className="ml-auto h-3.5 w-16 rounded bg-zinc-100" />
        </div>
      ))}
    </div>
  )
}
