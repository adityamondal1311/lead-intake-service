import { screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { addLead, requestsTo } from './fakeApi'
import { renderApp } from './renderApp'

describe('test harness', () => {
  it('renders the real app against the fake API', async () => {
    addLead({ fullName: 'Rahul Sharma' })

    renderApp('/')

    expect(await screen.findByRole('link', { name: 'Rahul Sharma' })).toBeInTheDocument()
    expect(requestsTo('GET', '/leads')).toHaveLength(1)
  })

  it('renders the 404 page for unknown routes', async () => {
    renderApp('/definitely/not/a/page')

    expect(await screen.findByRole('heading', { name: 'Page not found' })).toBeInTheDocument()
  })
})
