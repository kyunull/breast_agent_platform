import ElementPlus from 'element-plus'
import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'

import NodeSemanticForm from '@/components/forms/NodeSemanticForm.vue'
import type { ExtractionGroup } from '@/types/api'
import type { GraphNode } from '@/types/graph'

function makeNode(type: GraphNode['type'], config: Record<string, unknown> = {}): GraphNode {
  return {
    id: `${type}-1`, type, name: '测试节点', position: { x: 0, y: 0 },
    input_ports: [{ id: 'input' }], output_ports: [{ id: 'output' }], config, metadata: {},
  }
}

const extractionGroups: ExtractionGroup[] = [
  {
    id: 'demographics', label: '基本资料', required: ['age'],
    fields: [
      { alias: 'age', path: '$.patient.age', type: 'integer', required: true, default: null },
      { alias: 'sex', path: '$.patient.sex', type: 'string', required: false, default: null },
    ],
  },
  {
    id: 'pathology', label: '病理资料', required: ['her2'],
    fields: [
      { alias: 'her2', path: '$.pathology.her2', type: 'string', required: true, default: null },
    ],
  },
]

function mountForm(node: GraphNode, groups: ExtractionGroup[] = []) {
  setActivePinia(createPinia())
  return mount(NodeSemanticForm, {
    props: {
      node,
      extractionGroups: groups,
      fieldOptions: [{ value: 'facts.age', label: 'age', source: '数据准备 · 事实资料', type: 'integer' }],
    },
    global: { plugins: [ElementPlus] },
  })
}

describe('NodeSemanticForm', () => {
  it('adds conditions to an AND/OR condition group', async () => {
    const wrapper = mountForm(makeNode('condition', { operator: 'eq', left: 'facts.age', right: 52 }))

    expect(wrapper.findAll('.condition-rule')).toHaveLength(1)
    expect(wrapper.find('.condition-logic').exists()).toBe(false)
    await wrapper.get('.condition-add').trigger('click')

    const updatedNode = wrapper.emitted('update')?.[0][0] as GraphNode
    expect(updatedNode).toMatchObject({
      config: { operator: 'and', operands: expect.arrayContaining([expect.any(Object), expect.any(Object)]) },
    })
    await wrapper.setProps({ node: updatedNode })

    expect(wrapper.find('.condition-logic').exists()).toBe(true)
    expect(wrapper.findAll('.condition-rule')).toHaveLength(2)
  })

  it('hides the empty comparison placeholder and uses labeled condition panels', () => {
    const wrapper = mountForm(makeNode('condition', {
      operator: 'and',
      operands: [
        { operator: 'empty', left: 'facts.age', right: null },
        { operator: 'not_empty', left: 'facts.stage', right: null },
      ],
    }))

    expect(wrapper.text()).not.toContain('无需比较值')
    expect(wrapper.findAll('.condition-rule__title').map((item) => item.text())).toEqual(['条件 01', '条件 02'])
    expect(wrapper.findAll('.condition-remove')).toHaveLength(2)
  })

  it.each(['input', 'python_rule', 'llm', 'output'] as const)('provides input and output field controls for %s nodes', (type) => {
    const wrapper = mountForm(makeNode(type))

    expect(wrapper.findAll('.field-contract')).toHaveLength(2)
    expect(wrapper.findAll('.field-add')).toHaveLength(2)
  })

  it('applies every saved extraction group to an input node by default', async () => {
    const wrapper = mountForm(makeNode('input'), extractionGroups)

    expect(wrapper.text()).toContain('全部资料分组')
    expect(wrapper.text()).toContain('2 个分组 · 3 个字段')
    await wrapper.get('.input-extraction__apply').trigger('click')

    const updates = wrapper.emitted('update') ?? []
    const updatedNode = updates[updates.length - 1][0] as GraphNode
    expect(updatedNode.config).toMatchObject({
      extraction_scope: 'all',
      extraction_group_ids: ['demographics', 'pathology'],
      input_fields: [
        { name: 'age', path: 'demographics.age', type: 'integer', required: true },
        { name: 'sex', path: 'demographics.sex', type: 'string', required: false },
        { name: 'her2', path: 'pathology.her2', type: 'string', required: true },
      ],
      output_fields: [
        { name: 'age', path: 'demographics.age', type: 'integer', required: true },
        { name: 'sex', path: 'demographics.sex', type: 'string', required: false },
        { name: 'her2', path: 'pathology.her2', type: 'string', required: true },
      ],
    })
  })

  it('shows an existing single-group input configuration as selected groups', () => {
    const wrapper = mountForm(makeNode('input', { group_id: 'pathology' }), extractionGroups)

    expect(wrapper.find('.input-extraction').attributes('data-scope')).toBe('selected')
    expect(wrapper.text()).toContain('1 个分组 · 1 个字段')
  })

  it('marks an applied input scheme as updated without replacing node fields', async () => {
    const wrapper = mountForm(makeNode('input'), extractionGroups)
    await wrapper.get('.input-extraction__apply').trigger('click')
    const updates = wrapper.emitted('update') ?? []
    const appliedNode = updates[updates.length - 1][0] as GraphNode
    await wrapper.setProps({
      node: appliedNode,
      extractionGroups: extractionGroups.map((group) => group.id === 'pathology'
        ? { ...group, fields: [...group.fields, { alias: 'er', path: '$.pathology.er', type: 'string' as const, required: false, default: null }] }
        : group),
    })

    expect(wrapper.text()).toContain('字段方案已更新')
    expect((wrapper.props('node') as GraphNode).config.output_fields).toHaveLength(3)
  })

  it('offers an exposed knowledge profile to RAG nodes', async () => {
    setActivePinia(createPinia())
    const wrapper = mount(NodeSemanticForm, {
      props: {
        node: makeNode('rag'),
        knowledgeProfiles: [{ id: 'kb-local', name: '本地乳腺癌指南知识库', description: null, exposed_to_medical: true, medical_options: {} }],
      },
      global: { plugins: [ElementPlus] },
    })

    const select = wrapper.findComponent({ name: 'ElSelect' })
    expect(wrapper.text()).toContain('知识库配置档案')
    expect(wrapper.findComponent({ name: 'ElOption' }).props('label')).toBe('本地乳腺癌指南知识库')
    await select.vm.$emit('update:modelValue', 'kb-local')
    const updatedNode = wrapper.emitted('update')?.[0][0] as GraphNode
    expect(updatedNode.config.knowledge_profile_ref).toBe('kb-local')
  })
})
