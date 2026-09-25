import '@testing-library/jest-dom/vitest'

import { cleanup } from '@testing-library/react'
import { afterAll, afterEach, beforeAll } from 'vitest'

import { resetDb } from './fakeApi'
import { server } from './server'

// A request no handler covers fails the test: nothing may silently depend on an undeclared call.
beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => {
  cleanup()
  server.resetHandlers() // drop per-test overrides
  resetDb()
})
afterAll(() => server.close())
