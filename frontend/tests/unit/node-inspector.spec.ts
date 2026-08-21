import ElementPlus from 'element-plus'
import { mount } from '@vue/test-utils'

import NodeInspector from '@/components/NodeInspector.vue'
import type { GraphNode } from '@/types/graph'

const node: GraphNode = {
  id: 'condition-1',
  type: 'condition',
  name: 'HER2 判断',
  position: { x: 0, y: 0 },
  input_ports: [{ id: 'input' }],
  output_ports: [{ id: 'satisfied' }, { id: 'unsatisfied' }],
  config: {},
  metadata: {},
}

const mountInspector = () => mount(NodeInspector, {
  props: { node },
  attachTo: document.body,
  global: { plugins: [ElementPlus] },
})

describe('NodeInspector', () => {
  it('shows the selected node type and name instead of a generic title', () => {
    const wrapper = mountInspector()

    expect(wrapper.get('.node-inspector__heading').text()).toContain('条件 · HER2 判断')
    expect(wrapper.find('.node-inspector__name-input').exists()).toBe(false)
  })

  it('edits a node name only after clicking its text label', async () => {
    const wrapper = mountInspector()

    await wrapper.get('.node-inspector__name').trigger('click')
    const input = wrapper.get('.node-inspector__name-input input')
    await input.setValue('HER2 阳性判断')
    await input.trigger('keydown.enter')

    expect(wrapper.emitted('update')?.[0][0]).toMatchObject({ name: 'HER2 阳性判断' })
  })

  it('keeps structure tools collapsed until requested', async () => {
    const wrapper = mountInspector()

    expect(wrapper.find('.structure-tools__body').exists()).toBe(false)
    await wrapper.get('.structure-tools__toggle').trigger('click')
    expect(wrapper.get('.structure-tools__body').text()).toContain('复制节点 JSON')
  })
})
