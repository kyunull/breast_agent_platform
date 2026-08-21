import { buildFieldCatalog } from '@/composables/useWorkflowFields'
import { BREAST_CANCER_INPUT_FIELDS, BREAST_CANCER_INPUT_SECTIONS, findBreastCancerInputField } from '@/data/breastCancerInputSchema'
import type { GraphEdge, GraphNode } from '@/types/graph'

const node = (id: string, config: Record<string, unknown>): GraphNode => ({
  id,
  type: 'python_rule',
  name: id,
  position: { x: 0, y: 0 },
  input_ports: [{ id: 'input' }],
  output_ports: [{ id: 'output' }],
  config,
  metadata: {},
})

describe('workflow field catalog', () => {
  it('exposes the reference patient schema with Chinese labels and sample-derived types', () => {
    expect(BREAST_CANCER_INPUT_SECTIONS).toHaveLength(12)
    expect(BREAST_CANCER_INPUT_FIELDS).toHaveLength(469)

    const pathology = findBreastCancerInputField('$.patient_data.standard_pathology_reports[0].pathology_diagnosis')
    expect(pathology).toEqual(expect.objectContaining({
      label: '病理诊断',
      path: '$.patient_data.standard_pathology_reports[*].pathology_diagnosis',
      type: 'array',
      itemType: 'string',
      typeLabel: '文本列表',
    }))

    const temperature = findBreastCancerInputField('$.patient_data.standard_physical_sign_records[*].body_temperature')
    expect(temperature).toEqual(expect.objectContaining({ type: 'array', itemType: 'number', typeLabel: '数值列表' }))
    expect(BREAST_CANCER_INPUT_FIELDS.every((field) => field.label && !field.label.includes('_') && !field.label.includes('字段'))).toBe(true)
  })

  it('marks only the diagnosis-relevant and initially de-identified fields as selected by default', () => {
    expect(findBreastCancerInputField('$.patient_data.diagnosis[*].standard_name')?.defaultSelected).toBe(true)
    expect(findBreastCancerInputField('$.patient_data.laboratories[*].standard_result')?.defaultSelected).toBe(true)
    expect(findBreastCancerInputField('$.patient_data.examine_items[*].original_description')?.defaultSelected).toBe(true)
    expect(findBreastCancerInputField('$.patient_data.standard_pathology_reports[*].pathology_diagnosis')?.defaultSelected).toBe(true)

    expect(findBreastCancerInputField('$.patient_data.standard_patient.patient_name')?.defaultSelected).toBe(false)
    expect(findBreastCancerInputField('$.patient_data.standard_patient.id_card_no')?.defaultSelected).toBe(false)
    expect(findBreastCancerInputField('$.patient_data.standard_inpatient_documentations[*].record_text')?.defaultSelected).toBe(false)
    expect(BREAST_CANCER_INPUT_SECTIONS.find((section) => section.id === 'recipe_medicines')?.fields.every((field) => !field.defaultSelected)).toBe(true)
  })

  it('merges extraction fields and other node outputs with source labels', () => {
    const catalog = buildFieldCatalog(
      [{
        id: 'facts',
        label: '事实资料',
        fields: [{ alias: 'age', path: '$.patient.age', type: 'integer', required: true }],
      }],
      [
        node('rule-1', { output_fields: [{ name: 'risk', path: 'risk', type: 'string' }] }),
        node('current', { output_fields: [{ name: 'own', path: 'own', type: 'string' }] }),
      ],
      'current',
    )

    expect(catalog).toEqual(expect.arrayContaining([
      expect.objectContaining({ value: 'facts.age', label: 'age', source: '数据准备 · 事实资料' }),
      expect.objectContaining({ value: 'rule-1.risk', label: 'risk', source: '节点 · rule-1' }),
    ]))
    expect(catalog.some((item) => item.value === 'current.own')).toBe(false)
  })

  it('only suggests outputs from transitive upstream nodes when graph edges are provided', () => {
    const nodes = [
      node('input-1', { output_fields: [{ name: 'age', path: 'age' }] }),
      node('rule-1', { output_fields: [{ name: 'risk', path: 'risk' }] }),
      node('current', { output_fields: [{ name: 'decision', path: 'decision' }] }),
      node('downstream', { output_fields: [{ name: 'report', path: 'report' }] }),
      node('detached', { output_fields: [{ name: 'note', path: 'note' }] }),
    ]
    const edges: GraphEdge[] = [
      { id: 'e1', source: 'input-1', target: 'rule-1' },
      { id: 'e2', source: 'rule-1', target: 'current' },
      { id: 'e3', source: 'current', target: 'downstream' },
    ]

    const catalog = buildFieldCatalog([], nodes, 'current', edges)

    expect(catalog.map((item) => item.value)).toEqual(['input-1.age', 'rule-1.risk'])
  })

  it('uses the mapped Chinese label and source path for patient fields in node selectors', () => {
    const catalog = buildFieldCatalog([{
      id: 'pathology',
      label: '病理报告',
      fields: [{ alias: 'pathology_diagnosis', path: '$.patient_data.standard_pathology_reports[*].pathology_diagnosis', type: 'array', required: false }],
    }])

    expect(catalog).toContainEqual(expect.objectContaining({
      value: 'pathology.pathology_diagnosis',
      label: '病理诊断',
      type: 'array',
      typeLabel: '文本列表',
      path: '$.patient_data.standard_pathology_reports[*].pathology_diagnosis',
    }))
  })

  it('deduplicates references and keeps legacy output aliases', () => {
    const catalog = buildFieldCatalog(
      [{ id: 'facts', label: '事实资料', fields: [{ alias: 'stage', path: '$.stage', type: 'string', required: false }] }],
      [node('rule-1', { output_alias: 'stage' })],
    )

    expect(catalog.filter((item) => item.value.endsWith('.stage'))).toHaveLength(2)
    expect(catalog.find((item) => item.value === 'rule-1.stage')?.source).toBe('节点 · rule-1')
  })
})
