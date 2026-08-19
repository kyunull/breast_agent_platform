import { defineComponent, h, nextTick, reactive } from 'vue'
import { mount } from '@vue/test-utils'

import { toFlowNode } from '@/composables/useGraphAdapter'
import type { GraphNode, WorkflowGraph } from '@/types/graph'

vi.mock('@vue-flow/core', () => ({
  VueFlow: defineComponent({
    name: 'VueFlow',
    props: { nodes: { type: Array, default: () => [] }, edges: { type: Array, default: () => [] } },
    emits: ['update:nodes', 'update:edges', 'connect', 'node-click', 'node-drag-stop'],
    setup(props, { slots }) {
      return () => h('div', { class: 'vue-flow-stub' }, [
        ...(props.nodes as Array<{ id: string }>).map((node) => h('div', { class: 'flow-node-stub', 'data-node-id': node.id })),
        slots.default?.(),
      ])
    },
  }),
  Handle: defineComponent({ name: 'Handle', setup: () => () => h('span') }),
  Position: { Left: 'left', Right: 'right' },
}))

vi.mock('@vue-flow/background', () => ({
  Background: defineComponent({ name: 'Background', setup: () => () => h('span') }),
}))

vi.mock('@vue-flow/controls', () => ({
  Controls: defineComponent({ name: 'Controls', setup: () => () => h('span') }),
}))

import WorkflowCanvas from '@/components/WorkflowCanvas.vue'

const node: GraphNode = {
  id: 'input-1',
  type: 'input',
  name: '输入资料',
  position: { x: 0, y: 0 },
  input_ports: [{ id: 'input' }],
  output_ports: [{ id: 'output' }],
  config: {},
  metadata: {},
}

const graph: WorkflowGraph = { nodes: [node], edges: [] }

describe('WorkflowCanvas', () => {
  it('renders nodes when the parent graph adds one', async () => {
    const wrapper = mount(WorkflowCanvas, { props: { graph: reactive(graph) } })
    const nextNode = { ...node, id: 'output-1', type: 'output' as const, name: '方案输出' }

    await wrapper.setProps({ graph: { nodes: [node, nextNode], edges: [] } })

    expect(wrapper.findAll('.flow-node-stub')).toHaveLength(2)
  })

  it('does not emit a business graph update for Vue Flow internal node updates', async () => {
    const wrapper = mount(WorkflowCanvas, { props: { graph: reactive(graph) } })
    const vueFlow = wrapper.findComponent({ name: 'VueFlow' })
    const internalNode = { ...toFlowNode(node), dimensions: { width: 210, height: 104 }, handleBounds: {} }

    await nextTick()
    vueFlow.vm.$emit('update:nodes', [internalNode])
    await nextTick()

    expect(wrapper.emitted('update')).toBeUndefined()
  })

  it('emits a graph update when a canvas node position changes', async () => {
    const wrapper = mount(WorkflowCanvas, { props: { graph: reactive(graph) } })
    const vueFlow = wrapper.findComponent({ name: 'VueFlow' })
    const movedNode = { ...toFlowNode(node), position: { x: 180, y: 120 } }

    await nextTick()
    vueFlow.vm.$emit('update:nodes', [movedNode])
    await nextTick()

    expect(wrapper.emitted('update')?.[0][0]).toMatchObject({ nodes: [{ id: 'input-1', position: { x: 180, y: 120 } }] })
  })
})
