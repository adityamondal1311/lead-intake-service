import { setupServer } from 'msw/node'

import { handlers } from './fakeApi'

/** MSW in Node: intercepts fetch for the whole test run. Tests override with server.use(...). */
export const server = setupServer(...handlers)
