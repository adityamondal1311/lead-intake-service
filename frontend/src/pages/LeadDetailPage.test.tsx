import { screen, waitFor, within } from '@testing-library/react'
import { http } from 'msw'
import { describe, expect, it } from 'vitest'

import type { Activity } from '../api/types'
import { API, addLead, db, errorResponse, requestsTo } from '../test/fakeApi'
import { renderApp } from '../test/renderApp'
import { server } from '../test/server'

const at = (minutes: number) => new Date(Date.parse('2026-09-24T10:00:00Z') + minutes * 60_000).toISOString()

const HISTORY: Activity[] = [
  {
    id: 'act-3',
    type: 'STATUS_CHANGED',
    actor: 'user:dashboard',
    details: { from: 'NEW', to: 'CONTACTED' },
    createdAt: at(30),
  },
  {
    id: 'act-2',
    type: 'LEAD_UPDATED',
    actor: 'system:meta_webhook',
    details: { changes: { phone: { from: '+911111', to: '+912222' } }, externalEventId: 'evt_2' },
    createdAt: at(20),
  },
  {
    id: 'act-1',
    type: 'LEAD_CREATED',
    actor: 'system:meta_webhook',
    details: { source: 'META_ADS', externalEventId: 'evt_1' },
    createdAt: at(10),
  },
]

const timelineEntries = () =>
  within(screen.getByRole('list', { name: 'Activity' })).getAllByRole('listitem')
/** The status badge beside the lead's name (server data, not the select). */
const headerBadge = () => screen.getByRole('heading', { level: 1 }).parentElement!
const statusSelect = () => screen.getByRole('combobox', { name: 'Status' })

describe('lead detail: content and timeline', () => {
  it('shows the lead, its contact links and a readable timeline, newest first', async () => {
    const lead = addLead(
      { fullName: 'Rohan Mehta', status: 'CONTACTED', email: 'rohan@example.com', externalId: 'meta_lead_7' },
      HISTORY,
    )
    renderApp(`/leads/${lead.id}`)

    expect(await screen.findByRole('heading', { level: 1, name: 'Rohan Mehta' })).toBeInTheDocument()
    expect(headerBadge()).toHaveTextContent('Contacted')
    expect(screen.getByRole('link', { name: 'rohan@example.com' })).toHaveAttribute(
      'href',
      'mailto:rohan@example.com',
    )
    expect(screen.getByText('meta_lead_7')).toBeInTheDocument()

    const [status, update, created] = timelineEntries()
    expect(status).toHaveTextContent('Status changed from New to Contacted')
    expect(status).toHaveTextContent('by Dashboard')
    expect(update).toHaveTextContent('Lead updated: phone')
    expect(update).toHaveTextContent(/\+911111.*changed to.*\+912222/)
    expect(update).toHaveTextContent('by Meta webhook')
    expect(update).toHaveTextContent('evt_2')
    expect(created).toHaveTextContent('Lead created from Meta Ads')
    expect(document.title).toBe('Rohan Mehta · Lead Intake')
  })

  it('renders an unexpected activity as a generic entry without breaking the rest', async () => {
    const malformed: Activity = {
      id: 'bad',
      type: 'STATUS_CHANGED',
      actor: 'user:dashboard',
      details: {},
      createdAt: at(40),
    }
    const lead = addLead({}, [malformed, ...HISTORY])
    renderApp(`/leads/${lead.id}`)

    await screen.findByRole('list', { name: 'Activity' })
    const entries = timelineEntries()
    expect(entries).toHaveLength(4)
    expect(entries[0]).toHaveTextContent('Activity recorded')
    expect(entries[1]).toHaveTextContent('Status changed from New to Contacted')
  })

  it.each([
    ['an unknown id (404)', '00000000-0000-4000-8000-999999999999'],
    ['a malformed id (422)', 'hello'],
  ])('shows "Lead not found" for %s, with exactly one request (no retry)', async (_, id) => {
    renderApp(`/leads/${id}`)

    expect(await screen.findByRole('heading', { name: 'Lead not found' })).toBeInTheDocument()
    expect(requestsTo('GET', `/leads/${id}`)).toHaveLength(1)
    expect(document.title).toBe('Lead not found · Lead Intake')
  })
})

describe('lead detail: status updates (server-authoritative)', () => {
  it('shows the request while saving, then the server-confirmed status and new activity', async () => {
    const lead = addLead({ status: 'NEW' })
    let release!: () => void
    const gate = new Promise<void>((resolve) => (release = resolve))
    server.use(
      http.patch(`${API}/leads/:id/status`, async () => {
        await gate // falls through to the fake API afterwards
      }),
    )
    const { user } = renderApp(`/leads/${lead.id}`)
    await screen.findByRole('list', { name: 'Activity' })

    await user.selectOptions(statusSelect(), 'CONTACTED')

    // While saving: the select shows the request, disabled; nothing claims the change happened.
    expect(statusSelect()).toBeDisabled()
    expect(statusSelect()).toHaveValue('CONTACTED')
    expect(screen.getByText('Saving…')).toBeInTheDocument()
    expect(headerBadge()).toHaveTextContent('New')
    expect(timelineEntries()).toHaveLength(1)

    release()

    await waitFor(() => expect(headerBadge()).toHaveTextContent('Contacted'))
    expect(statusSelect()).toBeEnabled()
    expect(timelineEntries()[0]).toHaveTextContent('Status changed from New to Contacted')
    expect(screen.getByText('Status updated to Contacted.')).toBeInTheDocument()
    const patches = requestsTo('PATCH', `/leads/${lead.id}/status`)
    expect(patches).toHaveLength(1)
    expect(patches[0].body).toEqual({ status: 'CONTACTED' })
  })

  it('applies the PATCH response immediately, before the background refetch returns', async () => {
    const lead = addLead({ status: 'NEW' })
    const { user } = renderApp(`/leads/${lead.id}`)
    await screen.findByRole('list', { name: 'Activity' })

    // From now on, hold every GET of this lead: only the PATCH response can update the page.
    let releaseRefetch!: () => void
    const refetchGate = new Promise<void>((resolve) => (releaseRefetch = resolve))
    server.use(
      http.get(`${API}/leads/:id`, async () => {
        await refetchGate
      }),
    )
    await user.selectOptions(statusSelect(), 'QUALIFIED')

    await waitFor(() => expect(headerBadge()).toHaveTextContent('Qualified'))
    expect(timelineEntries()[0]).toHaveTextContent('Status changed from New to Qualified')
    releaseRefetch()
  })

  it('on failure returns the select to the saved status and shows the error once', async () => {
    const lead = addLead({ status: 'NEW' })
    let patches = 0
    server.use(
      http.patch(`${API}/leads/:id/status`, () => {
        patches++
        return errorResponse(500, 'INTERNAL_ERROR', 'Internal server error', 'req-patch-1')
      }),
    )
    const { user } = renderApp(`/leads/${lead.id}`)
    await screen.findByRole('list', { name: 'Activity' })

    await user.selectOptions(statusSelect(), 'QUALIFIED')

    expect(await screen.findByRole('alert')).toHaveTextContent("Couldn't update the status")
    expect(screen.getByText('req-patch-1')).toBeInTheDocument()
    expect(statusSelect()).toHaveValue('NEW')
    expect(statusSelect()).toBeEnabled()
    expect(headerBadge()).toHaveTextContent('New')
    expect(patches).toBe(1) // status changes are not retried automatically
  })

  it('reports a no-op when someone else already set that status, and shows the server state', async () => {
    const lead = addLead({ status: 'NEW' })
    const { user } = renderApp(`/leads/${lead.id}`)
    await screen.findByRole('list', { name: 'Activity' })

    db.leads[0].status = 'CONTACTED' // another user changed it after this page loaded
    await user.selectOptions(statusSelect(), 'CONTACTED')

    expect(await screen.findByText('Status was already Contacted.')).toBeInTheDocument()
    expect(headerBadge()).toHaveTextContent('Contacted')
    expect(timelineEntries()).toHaveLength(1) // no activity invented for a no-op
  })

  it('reconciles in the background: changes made elsewhere appear after the update', async () => {
    const lead = addLead({ status: 'NEW' })
    const { user } = renderApp(`/leads/${lead.id}`)
    await screen.findByRole('list', { name: 'Activity' })

    // A webhook update lands on the server while the page is open (not yet on screen).
    db.activities.get(lead.id)!.unshift({
      id: 'webhook-update',
      type: 'LEAD_UPDATED',
      actor: 'system:meta_webhook',
      details: { changes: { phone: { from: '+911', to: '+912' } }, externalEventId: 'evt_9' },
      createdAt: new Date().toISOString(),
    })
    await user.selectOptions(statusSelect(), 'LOST')

    await waitFor(() =>
      expect(screen.getByRole('list', { name: 'Activity' })).toHaveTextContent('Lead updated: phone'),
    )
    expect(screen.getByRole('list', { name: 'Activity' })).toHaveTextContent(
      'Status changed from New to Lost',
    )
  })

  it('the list shows the new status after going back (its cache was refreshed)', async () => {
    addLead({ fullName: 'Varun Chopra', status: 'NEW' })
    const { user } = renderApp('/')
    const table = await screen.findByRole('table')
    expect(within(table).getAllByRole('row')[1]).toHaveTextContent('New')

    await user.click(within(table).getByRole('link', { name: 'Varun Chopra' }))
    await screen.findByRole('list', { name: 'Activity' })
    await user.selectOptions(statusSelect(), 'CONVERTED')
    await screen.findByText('Status updated to Converted.')
    await user.click(screen.getByRole('link', { name: /back to leads/i }))

    await waitFor(() =>
      expect(within(screen.getByRole('table')).getAllByRole('row')[1]).toHaveTextContent(
        'Converted',
      ),
    )
  })
})
