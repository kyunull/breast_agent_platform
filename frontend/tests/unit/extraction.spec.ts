import { serializeExtractionConfig, type ExtractionGroupForm } from '@/composables/useExtractionConfig'
import { visibleGovernedFields } from '@/composables/useGovernance'

describe('extraction config adapter', () => {
  it('serializes field rows into the backend extraction contract', () => {
    const groups: ExtractionGroupForm[] = [{
      id: 'pathology',
      label: '病理信息',
      fields: [{
        alias: 'her2_score',
        path: '$.pathology.her2.score',
        type: 'number',
        required: true,
        defaultValue: null,
        filterField: 'status',
        filterValue: 'final',
        sortBy: 'collected_at',
        order: 'asc',
        take: 'latest',
        timeFrom: '',
        timeTo: '',
      }],
    }]

    expect(serializeExtractionConfig(groups)).toEqual({
      groups: [{
        id: 'pathology',
        label: '病理信息',
        required: ['her2_score'],
        fields: [{
          alias: 'her2_score',
          path: '$.pathology.her2.score',
          type: 'number',
          required: true,
          default: null,
          array: { filter: { status: 'final' }, sort_by: 'collected_at', order: 'asc', take: 'latest' },
        }],
      }],
    })
  })
})

describe('governance field visibility', () => {
  it('keeps governed parameters out of medical forms', () => {
    expect(visibleGovernedFields('medical_user')).toEqual([])
    expect(visibleGovernedFields('admin_developer')).toContain('temperature')
  })
})
