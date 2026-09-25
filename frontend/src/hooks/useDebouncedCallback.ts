import { useCallback, useEffect, useRef } from 'react'

/**
 * Returns [run, cancel]: `run(value)` calls `callback(value)` after `delayMs` without another
 * call. Debouncing the *action* (not a state value watched by an effect) means a pending search
 * can be cancelled outright, e.g. when the user clears the filters mid-typing.
 */
export function useDebouncedCallback<T>(
  callback: (value: T) => void,
  delayMs: number,
): [(value: T) => void, () => void] {
  const timer = useRef<number | undefined>(undefined)
  const latestCallback = useRef(callback)

  useEffect(() => {
    latestCallback.current = callback
  })

  const cancel = useCallback(() => window.clearTimeout(timer.current), [])

  const run = useCallback(
    (value: T) => {
      window.clearTimeout(timer.current)
      timer.current = window.setTimeout(() => latestCallback.current(value), delayMs)
    },
    [delayMs],
  )

  useEffect(() => cancel, [cancel]) // no stray navigation after the page unmounts

  return [run, cancel]
}
