import ElementPlus from 'element-plus'
import { mount, shallowMount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import DataPreparation from '@/components/DataPreparation.vue'

describe('DataPreparation', () => {
  it('initializes an empty extraction with the default clinical field selection', async () => {
    const wrapper = shallowMount(DataPreparation, {
      props: { workflowId: 'workflow-1', extraction: { groups: [] } },
      global: { plugins: [ElementPlus], stubs: { ElTree: { template: '<div />', methods: { setCheckedKeys() {} } } } },
    })

    await wrapper.vm.$nextTick()
    const updates = wrapper.emitted('update') ?? []
    const latest = updates[updates.length - 1]?.[0] as { groups: Array<{ id: string; fields: Array<{ alias: string; path: string }> }> }
    const selectedPaths = latest.groups.flatMap((group) => group.fields.map((field) => field.path))

    expect(latest.groups.map((group) => group.id)).toEqual(expect.arrayContaining(['diagnosis', 'laboratories', 'examine_items', 'standard_pathology_reports']))
    expect(selectedPaths).toContain('$.patient_data.diagnosis[*].standard_name')
    expect(selectedPaths).not.toContain('$.patient_data.standard_patient.patient_name')
    expect(selectedPaths).not.toContain('$.patient_data.standard_inpatient_documentations[*].record_text')
    expect(wrapper.find('.selection-summary').text()).toMatch(/已选择 [1-9]\d* 个字段/)
  })

  it('does not replace an existing extraction with default selections', async () => {
    const extraction = {
      groups: [{
        id: 'custom',
        label: '自定义',
        fields: [{ alias: 'only_this', path: '$.custom.only_this', type: 'string', required: false, default: null }],
        required: [],
      }],
    }
    const wrapper = shallowMount(DataPreparation, {
      props: { workflowId: 'workflow-1', extraction },
      global: { plugins: [ElementPlus], stubs: { ElTree: { template: '<div />', methods: { setCheckedKeys() {} } } } },
    })

    await wrapper.vm.$nextTick()

    expect(wrapper.emitted('update')).toBeUndefined()
    expect(wrapper.find('.fields-column').text()).toContain('only_this')
    expect(wrapper.find('.fields-column').text()).not.toContain('病理诊断')
  })

  it('renders mapped Chinese names and inferred types for selected patient fields', async () => {
    const wrapper = shallowMount(DataPreparation, {
      props: {
        workflowId: 'workflow-1',
        extraction: {
          groups: [{
            id: 'pathology',
            label: '病理报告',
            fields: [{
              alias: 'pathology_diagnosis',
              path: '$.patient_data.standard_pathology_reports[*].pathology_diagnosis',
              type: 'array',
              required: true,
              default: null,
            }],
            required: ['pathology_diagnosis'],
          }],
        },
      },
      global: { plugins: [ElementPlus], stubs: { ElTree: { template: '<div />', methods: { setCheckedKeys() {} } } } },
    })

    await wrapper.vm.$nextTick()
    expect(wrapper.find('.data-preparation').text()).toContain('病理诊断')
    expect(wrapper.find('.data-preparation').text()).toContain('文本列表')
    expect(wrapper.find('.group-count').text()).toContain('1 个字段')
  })

  it('uploads a complete JSON document into the preview sample', async () => {
    const wrapper = shallowMount(DataPreparation, {
      props: { workflowId: 'workflow-1', extraction: { groups: [] } },
      global: { plugins: [ElementPlus], stubs: { ElTree: { template: '<div />', methods: { setCheckedKeys() {} } } } },
    })
    const file = new File(['{"patient_data":{"age":42}}'], 'BC-001.json', { type: 'application/json' })
    const input = wrapper.get('input[type="file"]')
    Object.defineProperty(input.element, 'files', { value: [file] })

    await input.trigger('change')
    await wrapper.vm.$nextTick()

    expect((wrapper.vm as unknown as { sampleText: string }).sampleText).toContain('"patient_data"')
    expect(wrapper.text()).toContain('BC-001.json')
  })

  it('keeps the current preview sample when an uploaded file is invalid', async () => {
    const wrapper = shallowMount(DataPreparation, {
      props: { workflowId: 'workflow-1', extraction: { groups: [] } },
      global: { plugins: [ElementPlus], stubs: { ElTree: { template: '<div />', methods: { setCheckedKeys() {} } } } },
    })
    ;(wrapper.vm as unknown as { sampleText: string }).sampleText = '{"existing":true}'
    const file = new File(['not json'], 'broken.json', { type: 'application/json' })
    const input = wrapper.get('input[type="file"]')
    Object.defineProperty(input.element, 'files', { value: [file] })

    await input.trigger('change')
    await wrapper.vm.$nextTick()

    expect((wrapper.vm as unknown as { sampleText: string }).sampleText).toBe('{"existing":true}')
    expect(wrapper.text()).toContain('文件内容不是有效 JSON。')
  })
})
