import { screen, waitFor, within } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import { API, addLead, errorResponse, requestsTo } from '../test/fakeApi'
import { currentSearch, renderApp } from '../test/renderApp'
import { server } from '../test/server'

// jsdom does not apply CSS, so both the desktop table and the phone cards are in the DOM. Flow
// assertions look inside the table (what a desktop screen-reader user would use).
const table = async () => screen.findByRole('table')
const rowNames = async () =>
  within(await table())
    .getAllByRole('link')
    .map((link) => link.textContent)
const listRequests = () => requestsTo('GET', '/leads')

function addLeads(count: number) {
  for (let i = 0; i < count; i++) addLead()
}

describe('lead list: loading, content and empty states', () => {
  it('shows a skeleton, then the leads newest first with their status as text', async () => {
    addLead({ fullName: 'Older Lead', status: 'LOST' })
    addLead({ fullName: 'Newer Lead', status: 'CONTACTED' })

    renderApp('/')

    expect(screen.getByRole('status', { name: 'Loading leads' })).toBeInTheDocument()
    expect(await rowNames()).toEqual(['Newer Lead', 'Older Lead'])
    const newest = within(await table()).getAllByRole('row')[1]
    expect(newest).toHaveTextContent('Contacted')
    expect(screen.getByText('2 leads')).toBeInTheDocument()
  })

  it('says "No leads yet" when there are none at all', async () => {
    renderApp('/')

    expect(await screen.findByRole('heading', { name: 'No leads yet' })).toBeInTheDocument()
  })

  it('says "No leads match" for an empty filtered result, and Clear filters resets the view', async () => {
    addLead({ fullName: 'Rahul Sharma' })
    const { user, router } = renderApp('/?search=zzz&status=LOST')

    expect(await screen.findByRole('heading', { name: 'No leads match these filters' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Clear filters' }))

    expect(await rowNames()).toEqual(['Rahul Sharma'])
    expect(currentSearch(router)).toBe('')
    expect(screen.getByRole('searchbox')).toHaveValue('')
  })
})

describe('lead list: errors', () => {
  it('retries a 5xx, then shows the error with its request id; Try again recovers', async () => {
    addLead({ fullName: 'Rahul Sharma' })
    let failures = 0
    server.use(
      http.get(`${API}/leads`, () => {
        // Fail the first three attempts (initial + 2 automatic retries), then fall through to
        // the fake API.
        if (failures < 3) {
          failures++
          return errorResponse(500, 'INTERNAL_ERROR', 'Internal server error', 'req-err-1')
        }
      }),
    )
    const { user } = renderApp('/')

    expect(await screen.findByRole('alert')).toHaveTextContent('Something went wrong')
    expect(screen.getByText('req-err-1')).toBeInTheDocument()
    expect(failures).toBe(3) // the retry policy retried the 5xx twice

    await user.click(screen.getByRole('button', { name: 'Try again' }))
    expect(await rowNames()).toEqual(['Rahul Sharma'])
  })

  it('explains an unreachable server', async () => {
    server.use(http.get(`${API}/leads`, () => HttpResponse.error()))
    renderApp('/')

    expect(await screen.findByRole('alert')).toHaveTextContent("Can't reach the server")
  })
})

describe('lead list: search, filter and pagination (URL-driven)', () => {
  it('updates the input at once but sends one debounced request, then resets to page 1', async () => {
    addLeads(21) // two pages
    addLead({ fullName: 'Amit Kumar' })
    const { user, router } = renderApp('/?page=2')
    await table()

    const search = screen.getByRole('searchbox', { name: /search leads/i })
    await user.type(search, 'kumar')

    expect(search).toHaveValue('kumar') // no lag while typing
    await waitFor(async () => expect(await rowNames()).toEqual(['Amit Kumar']))
    const searches = listRequests().map((r) => r.params.get('search')).filter(Boolean)
    expect(searches).toEqual(['kumar']) // not "k", "ku", "kum", ...
    expect(currentSearch(router)).toBe('?search=kumar') // page reset to 1 (omitted)
  })

  it('filters by status and puts it in the URL', async () => {
    addLead({ fullName: 'Lost Lead', status: 'LOST' })
    addLead({ fullName: 'New Lead', status: 'NEW' })
    const { user, router } = renderApp('/')
    await table()

    await user.selectOptions(screen.getByRole('combobox', { name: 'Status' }), 'LOST')

    await waitFor(async () => expect(await rowNames()).toEqual(['Lost Lead']))
    expect(currentSearch(router)).toBe('?status=LOST')
    expect(listRequests().at(-1)?.params.get('status')).toBe('LOST')
  })

  it('paginates with real links: Back returns to the previous page, typing does not add history', async () => {
    addLeads(25)
    const { user, router } = renderApp('/')
    expect(await rowNames()).toHaveLength(20)

    await user.click(screen.getByRole('link', { name: 'Page 2' }))
    await waitFor(async () => expect(await rowNames()).toHaveLength(5))
    expect(currentSearch(router)).toBe('?page=2')

    // Typing replaces the history entry instead of pushing one per keystroke...
    await user.type(screen.getByRole('searchbox'), 'Lead 1')
    await waitFor(() => expect(currentSearch(router)).toBe('?search=Lead+1'))

    // ...so one Back skips all the keystrokes and lands on the first page.
    await router.navigate(-1)
    await waitFor(() => expect(currentSearch(router)).toBe(''))
    await waitFor(async () => expect(await rowNames()).toHaveLength(20))
  })

  it('keeps the current rows visible (dimmed, "Updating…") while the next page loads', async () => {
    addLeads(25)
    let release!: () => void
    const gate = new Promise<void>((resolve) => (release = resolve))
    server.use(
      http.get(`${API}/leads`, async ({ request }) => {
        if (new URL(request.url).searchParams.get('page') === '2') await gate
        // falls through to the fake API
      }),
    )
    const { user } = renderApp('/')
    const firstPage = await rowNames()

    await user.click(screen.getByRole('link', { name: 'Page 2' }))

    expect(await screen.findByText('Updating…')).toBeInTheDocument()
    expect(await rowNames()).toEqual(firstPage) // no flash to a blank or loading screen
    release()
    await waitFor(async () => expect(await rowNames()).toHaveLength(5))
    expect(screen.queryByText('Updating…')).not.toBeInTheDocument()
  })

  it('cleans up a hand-edited URL instead of sending it to the API', async () => {
    addLead()
    const { router } = renderApp('/?status=FOO&page=abc&junk=1')
    await table()

    await waitFor(() => expect(currentSearch(router)).toBe(''))
    for (const request of listRequests()) {
      expect(request.params.get('status')).toBeNull()
      expect(request.params.get('page')).toBe('1')
    }
  })

  it('corrects a page past the end to the last page', async () => {
    addLeads(25)
    const { router } = renderApp('/?page=99')

    await waitFor(() => expect(currentSearch(router)).toBe('?page=2'))
    await waitFor(async () => expect(await rowNames()).toHaveLength(5))
  })

  it('opening a lead and going "Back to leads" returns to the same filtered view', async () => {
    addLead({ fullName: 'Kavya Nair', status: 'QUALIFIED' })
    const { user, router } = renderApp('/?status=QUALIFIED')

    await user.click(within(await table()).getByRole('link', { name: 'Kavya Nair' }))
    await user.click(await screen.findByRole('link', { name: /back to leads/i }))

    await waitFor(() => expect(currentSearch(router)).toBe('?status=QUALIFIED'))
    expect(router.state.location.pathname).toBe('/')
  })
})
