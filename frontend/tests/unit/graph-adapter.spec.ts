import { backfillConditionEdgeLabels, createGraphNode, parseNodeClipboard, sanitizeNodeClipboard, toFlowEdge, toFlowNode, toGraphEdge, toGraphNode, toPersistedGraph } from '@/composables/useGraphAdapter'
import type { Edge } from '@vue-flow/core'
import { reactive } from 'vue'
import type { GraphNode } from '@/types/graph'

const node: GraphNode = {
  id: 'rag-1',
  type: 'rag',
  name: '指南检索',
  position: { x: 120, y: 240 },
  input_ports: [{ id: 'query' }],
  output_ports: [{ id: 'context_text' }],
  config: { knowledge_profile_ref: 'profile-1', query_template: '{{病理}}', api_key: 'should-strip' },
  metadata: { owner: 'medical', simulated_input: { patient: 'real data' } },
}

describe('graph adapter', () => {
  it('round-trips backend node fields through a Vue Flow node', () => {
    expect(toGraphNode(toFlowNode(node))).toEqual(node)
  })

  it('keeps Vue Flow position updates isolated from the source graph', () => {
    const flowNode = toFlowNode(node)
    flowNode.position.x = 999

    expect(node.position.x).toBe(120)
  })

  it('converts graph nodes with nested Vue proxies for Vue Flow', () => {
    const reactiveNode = {
      ...node,
      config: reactive({ ...node.config }),
      input_ports: reactive([...node.input_ports]),
      output_ports: reactive([...node.output_ports]),
    } as GraphNode

    expect(() => toFlowNode(reactiveNode)).not.toThrow()
    expect(toFlowNode(reactiveNode).data?.graphNode).toEqual(node)
  })

  it('strips secrets and real-patient values from clipboard JSON', () => {
    const safe = sanitizeNodeClipboard(node)
    const parsed = JSON.stringify(safe)

    expect(parsed).not.toContain('should-strip')
    expect(parsed).not.toContain('real data')
    expect(safe.version).toBe(1)
  })

  it('copies graph nodes containing nested Vue proxies', () => {
    const reactiveNode = reactive({
      ...node,
      config: { ...node.config },
      metadata: { ...node.metadata },
    }) as GraphNode

    expect(() => sanitizeNodeClipboard(reactiveNode)).not.toThrow()
  })

  it('returns validation issues without mutating on malformed paste', () => {
    const result = parseNodeClipboard('{"type":"rag"}')
    expect(result.node).toBeNull()
    expect(result.issues).toContain('缺少节点 id。')
  })

  it('maps backend branch fields to Vue Flow and back without losing labels', () => {
    const edge = {
      id: 'edge-1',
      source: 'condition-1',
      target: 'next-1',
      source_port: 'satisfied',
      target_port: 'input',
      kind: 'branch' as const,
      branch_label: '满足条件',
    }

    const flowEdge = toFlowEdge(edge)
    expect(flowEdge.sourceHandle).toBe('satisfied')
    expect(flowEdge.label).toBe('满足条件')
    expect(toGraphEdge(flowEdge)).toMatchObject({
      source_port: 'satisfied',
      target_port: 'input',
      kind: 'branch',
      branch_label: '满足条件',
    })
  })

  it('persists graph ports as backend string ids while accepting legacy handles', () => {
    const graph = {
      nodes: [{ ...node, input_ports: [{ id: 'input', label: '输入' }], output_ports: [{ id: 'satisfied', label: '满足' }] }],
      edges: [{ id: 'edge-legacy', source: node.id, target: 'next', source_handle: 'output', target_handle: 'input', label: '旧标签' }],
    }

    expect(toPersistedGraph(graph)).toMatchObject({
      nodes: [{ input_ports: ['input'], output_ports: ['satisfied'] }],
      edges: [{ source_port: 'output', target_port: 'input', branch_label: '旧标签' }],
    })
  })

  it('preserves reassessment edge policy while normalizing edge fields', () => {
    const graph = {
      nodes: [node],
      edges: [{
        id: 'loop-1', source: node.id, target: node.id,
        source_port: 'context_text', target_port: 'query', kind: 'reassessment' as const,
        loop_policy: { max_iterations: 2, exit_condition: 'complete' },
      }],
    }

    expect(toPersistedGraph(graph)).toMatchObject({
      edges: [{ kind: 'reassessment', loop_policy: { max_iterations: 2, exit_condition: 'complete' } }],
    })
  })

  it('creates ordinary nodes with runtime-compatible in/out ports', () => {
    const input = createGraphNode('input', 0)
    const rule = createGraphNode('python_rule', 1)
    const output = createGraphNode('output', 2)

    expect(input.input_ports).toEqual([])
    expect(input.output_ports).toEqual([{ id: 'out', label: '输出' }])
    expect(rule.input_ports).toEqual([{ id: 'in', label: '输入' }])
    expect(rule.output_ports).toEqual([{ id: 'out', label: '输出' }])
    expect(output.input_ports).toEqual([{ id: 'in', label: '输入' }])
    expect(output.output_ports).toEqual([])
  })

  it('backfills labels on existing condition edges from their source ports', () => {
    const graph = {
      nodes: [{
        ...node,
        id: 'condition-1',
        type: 'condition' as const,
        output_ports: [{ id: 'satisfied', label: '满足' }, { id: 'unsatisfied', label: '不满足' }],
        config: { true_port: 'satisfied', false_port: 'unsatisfied', true_label: '通过', false_label: '退回' },
      }],
      edges: [
        { id: 'yes', source: 'condition-1', target: 'next-1', source_port: 'satisfied', target_port: 'in' },
        { id: 'no', source: 'condition-1', target: 'next-2', source_port: 'unsatisfied', target_port: 'in' },
      ],
    }

    expect(backfillConditionEdgeLabels(graph).edges).toMatchObject([
      { branch_label: '通过', label: '通过', kind: 'branch' },
      { branch_label: '退回', label: '退回', kind: 'branch' },
    ])
  })
})
