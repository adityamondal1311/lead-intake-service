import type { ReactNode } from 'react'

export default function EmptyState({
  title,
  description,
  action,
}: {
  title: string
  description: ReactNode
  action?: ReactNode
}) {
  return (
    <div className="rounded-lg border border-dashed border-zinc-300 bg-white px-6 py-12 text-center">
      <h2 className="text-sm font-semibold text-zinc-900">{title}</h2>
      <div className="mx-auto mt-1 max-w-md text-sm text-zinc-600">{description}</div>
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}
