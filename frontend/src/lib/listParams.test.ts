import { describe, expect, it } from 'vitest'

import { hasActiveFilters, parseListParams, toSearchParams } from './listParams'

const parse = (query: string) => parseListParams(new URLSearchParams(query))

describe('parseListParams: URL → valid list state', () => {
  it('defaults to page 1, all statuses, no search', () => {
    expect(parse('')).toEqual({ page: 1, status: undefined, search: '' })
  })

  it.each([
    ['status=LOST', 'LOST'],
    ['status=FOO', undefined],
    ['status=lost', undefined], // exact values only
    ['status=', undefined],
  ])('status: %s → %s', (query, status) => {
    expect(parse(query).status).toBe(status)
  })

  it.each([
    ['page=3', 3],
    ['page=abc', 1],
    ['page=0', 1],
    ['page=-2', 1],
    ['page=2.5', 1],
    ['page=', 1],
  ])('page: %s → %s', (query, page) => {
    expect(parse(query).page).toBe(page)
  })

  it('trims search, treats whitespace-only as no search, and caps it at 100 characters', () => {
    expect(parse('search=%20%20kumar%20').search).toBe('kumar')
    expect(parse('search=%20%20%20').search).toBe('')
    expect(parse(`search=${'x'.repeat(150)}`).search).toHaveLength(100)
  })
})

describe('toSearchParams: state → canonical URL', () => {
  it('omits every default, so the unfiltered first page is just "/"', () => {
    expect(toSearchParams({ page: 1, status: undefined, search: '' }).toString()).toBe('')
  })

  it('includes only non-default values', () => {
    expect(toSearchParams({ page: 2, status: 'LOST', search: 'kumar' }).toString()).toBe(
      'search=kumar&status=LOST&page=2',
    )
  })

  it('round-trips: normalizing a messy URL gives the canonical one', () => {
    const messy = parse('status=FOO&page=abc&search=%20kumar%20&junk=1')
    expect(toSearchParams(messy).toString()).toBe('search=kumar')
  })
})

describe('hasActiveFilters', () => {
  it('is true for a search or a status, not for the page alone', () => {
    expect(hasActiveFilters({ page: 3, status: undefined, search: '' })).toBe(false)
    expect(hasActiveFilters({ page: 1, status: 'NEW', search: '' })).toBe(true)
    expect(hasActiveFilters({ page: 1, status: undefined, search: 'a' })).toBe(true)
  })
})
