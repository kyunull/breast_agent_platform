import type { WorkflowGraph } from '@/types/graph'

export function applyPromptCandidateToDraft(graph: WorkflowGraph, nodeId: string, candidatePrompt: string): WorkflowGraph {
  return {
    nodes: graph.nodes.map((node) => node.id === nodeId ? { ...node, config: { ...node.config, prompt: candidatePrompt }, metadata: { ...node.metadata, prompt_optimization: true } } : { ...node, config: { ...node.config }, metadata: { ...node.metadata } }),
    edges: graph.edges.map((edge) => ({ ...edge, metadata: edge.metadata ? { ...edge.metadata } : edge.metadata })),
  }
}
