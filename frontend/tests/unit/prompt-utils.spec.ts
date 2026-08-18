import { applyPromptCandidateToDraft } from '@/composables/usePromptOptimization'
import type { WorkflowGraph } from '@/types/graph'

describe('prompt draft application', () => {
  it('updates only the selected LLM draft node without mutating the source graph', () => {
    const graph: WorkflowGraph = { nodes: [{ id: 'llm-1', type: 'llm', name: '判断', position: { x: 0, y: 0 }, input_ports: [], output_ports: [], config: { prompt: '旧提示词' }, metadata: {} }], edges: [] }

    const next = applyPromptCandidateToDraft(graph, 'llm-1', '新提示词')

    expect(graph.nodes[0].config.prompt).toBe('旧提示词')
    expect(next.nodes[0].config.prompt).toBe('新提示词')
    expect(next.nodes[0].metadata.prompt_optimization).toBe(true)
  })
})
