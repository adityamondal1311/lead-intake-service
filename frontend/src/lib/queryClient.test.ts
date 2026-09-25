import { describe, expect, it } from 'vitest'

import { ApiError } from '../api/client'
import { shouldRetry } from './queryClient'

const status = (code: number) => new ApiError(code, 'X', 'x')
const network = new ApiError(0, 'NETWORK_ERROR', 'down')

describe('shouldRetry: retry only what a retry can fix', () => {
  it.each([
    ['network error', network],
    ['500', status(500)],
    ['503', status(503)],
  ])('retries a %s', (_, error) => {
    expect(shouldRetry(0, error)).toBe(true)
    expect(shouldRetry(1, error)).toBe(true)
  })

  it('stops after two retries', () => {
    expect(shouldRetry(2, status(500))).toBe(false)
  })

  it.each([400, 401, 404, 422])('never retries a %i (it fails the same way every time)', (code) => {
    expect(shouldRetry(0, status(code))).toBe(false)
  })

  it('does not retry unknown (non-API) errors', () => {
    expect(shouldRetry(0, new Error('bug'))).toBe(false)
  })
})
