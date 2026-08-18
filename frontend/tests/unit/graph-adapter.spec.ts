import { parseNodeClipboard, sanitizeNodeClipboard, toFlowNode, toGraphNode } from '@/composables/useGraphAdapter'
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

  it('strips secrets and real-patient values from clipboard JSON', () => {
    const safe = sanitizeNodeClipboard(node)
    const parsed = JSON.stringify(safe)

    expect(parsed).not.toContain('should-strip')
    expect(parsed).not.toContain('real data')
    expect(safe.version).toBe(1)
  })

  it('returns validation issues without mutating on malformed paste', () => {
    const result = parseNodeClipboard('{"type":"rag"}')
    expect(result.node).toBeNull()
    expect(result.issues).toContain('缺少节点 id。')
  })
})
