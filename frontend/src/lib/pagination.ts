export type PageItem = number | 'gap'

/** e.g. current 5 of 9 → [1, gap, 4, 5, 6, gap, 9]; small totals list every page. */
export function pageItems(current: number, total: number): PageItem[] {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1)
  const pages = new Set([1, total, current - 1, current, current + 1])
  const sorted = [...pages].filter((p) => p >= 1 && p <= total).sort((a, b) => a - b)
  const items: PageItem[] = []
  sorted.forEach((page, i) => {
    if (i > 0 && page - sorted[i - 1] > 1) items.push('gap')
    items.push(page)
  })
  return items
}
