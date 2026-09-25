import { describe, expect, it } from 'vitest'

import { pageItems } from './pagination'

describe('pageItems', () => {
  it('lists every page when there are 7 or fewer', () => {
    expect(pageItems(1, 1)).toEqual([1])
    expect(pageItems(4, 7)).toEqual([1, 2, 3, 4, 5, 6, 7])
  })

  it('collapses the far side into a gap near the start', () => {
    expect(pageItems(1, 9)).toEqual([1, 2, 'gap', 9])
    expect(pageItems(2, 9)).toEqual([1, 2, 3, 'gap', 9])
  })

  it('shows neighbours with gaps on both sides in the middle', () => {
    expect(pageItems(5, 9)).toEqual([1, 'gap', 4, 5, 6, 'gap', 9])
  })

  it('collapses the near side into a gap at the end', () => {
    expect(pageItems(9, 9)).toEqual([1, 'gap', 8, 9])
  })

  it('does not insert a gap between adjacent pages', () => {
    expect(pageItems(3, 9)).toEqual([1, 2, 3, 4, 'gap', 9])
  })
})
