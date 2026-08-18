import { collectEvidenceRefs, formatRunError, isRunTerminal } from '@/composables/useRunUtils'

describe('run utilities', () => {
  it('recognizes all terminal run states', () => {
    expect(isRunTerminal('succeeded')).toBe(true)
    expect(isRunTerminal('failed')).toBe(true)
    expect(isRunTerminal('cancelled')).toBe(true)
    expect(isRunTerminal('running')).toBe(false)
  })

  it('collects unique evidence references from output and traces', () => {
    expect(collectEvidenceRefs({ evidence_refs: ['ev-1', 'ev-2'] }, [{ evidence_refs: ['ev-2', 'ev-3'] }])).toEqual(['ev-1', 'ev-2', 'ev-3'])
  })

  it('keeps backend error codes visible to clinicians', () => {
    expect(formatRunError({ code: 'citation_required', message: 'evidence missing' })).toBe('citation_required：evidence missing')
  })
})
