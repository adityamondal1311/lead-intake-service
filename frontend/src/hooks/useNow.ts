import { useEffect, useState } from 'react'

/**
 * The current time, refreshed every `intervalMs`. Components showing relative times use it so
 * "5 minutes ago" keeps advancing while the page stays open instead of freezing at first render.
 */
export function useNow(intervalMs = 60_000): number {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now()), intervalMs)
    return () => window.clearInterval(id)
  }, [intervalMs])
  return now
}
