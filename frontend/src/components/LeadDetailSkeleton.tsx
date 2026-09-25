/** Placeholder shaped like the lead detail page, so nothing jumps when data arrives. */
export default function LeadDetailSkeleton() {
  return (
    <div role="status" aria-label="Loading lead" className="animate-pulse">
      <div className="h-7 w-56 rounded bg-zinc-200" />
      <div className="mt-2 h-4 w-40 rounded bg-zinc-100" />
      <div className="mt-6 grid gap-6 lg:grid-cols-5">
        <div className="h-72 rounded-lg border border-zinc-200 bg-white lg:col-span-2" />
        <div className="h-72 rounded-lg border border-zinc-200 bg-white lg:col-span-3" />
      </div>
    </div>
  )
}
