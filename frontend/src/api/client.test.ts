import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import { API, errorBody, requestsTo } from '../test/fakeApi'
import { server } from '../test/server'
import { ApiError, apiFetch } from './client'

async function failure(promise: Promise<unknown>): Promise<unknown> {
  try {
    await promise
  } catch (error) {
    return error
  }
  throw new Error('expected the request to fail')
}

describe('apiFetch', () => {
  it('turns the error envelope into an ApiError with the request id', async () => {
    server.use(
      http.get(`${API}/boom`, () =>
        HttpResponse.json(errorBody('LEAD_NOT_FOUND', 'Lead not found', 'req-42'), { status: 404 }),
      ),
    )

    const error = await failure(apiFetch('/boom'))

    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({
      status: 404,
      code: 'LEAD_NOT_FOUND',
      message: 'Lead not found',
      requestId: 'req-42',
    })
  })

  it('reports an unreachable server as NETWORK_ERROR', async () => {
    server.use(http.get(`${API}/down`, () => HttpResponse.error()))

    const error = await failure(apiFetch('/down'))

    expect(error).toMatchObject({ status: 0, code: 'NETWORK_ERROR', isNetworkError: true })
  })

  it('keeps the status and X-Request-ID when the error is not our envelope (e.g. a proxy page)', async () => {
    server.use(
      http.get(`${API}/proxy`, () =>
        new HttpResponse('<h1>Bad gateway</h1>', {
          status: 502,
          statusText: 'Bad Gateway',
          headers: { 'Content-Type': 'text/html', 'X-Request-ID': 'req-proxy' },
        }),
      ),
    )

    const error = await failure(apiFetch('/proxy'))

    expect(error).toMatchObject({
      status: 502,
      code: 'HTTP_ERROR',
      message: 'Bad Gateway',
      requestId: 'req-proxy',
    })
  })

  it('leaves empty query values out of the URL', async () => {
    await apiFetch('/leads', { query: { page: 1, limit: 20, status: undefined, search: '' } })

    const [request] = requestsTo('GET', '/leads')
    expect(request.params.toString()).toBe('page=1&limit=20')
  })

  it('lets a cancelled request reject as an abort, not as an ApiError to show', async () => {
    const controller = new AbortController()
    controller.abort()

    const error = await failure(apiFetch('/leads', { signal: controller.signal }))

    expect(error).not.toBeInstanceOf(ApiError)
    expect((error as Error).name).toBe('AbortError')
  })
})
