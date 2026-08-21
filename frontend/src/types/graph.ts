export type GraphNodeType =
  | 'input'
  | 'condition'
  | 'python_rule'
  | 'rag'
  | 'llm'
  | 'parallel_agent'
  | 'output'
  | 'clinical_task'
  | 'subworkflow'
  | 'annotation'

export interface GraphPort {
  id: string
  label?: string
}

export interface GraphNode {
  id: string
  type: GraphNodeType
  name: string
  position: { x: number; y: number }
  input_ports: GraphPort[]
  output_ports: GraphPort[]
  config: Record<string, unknown>
  metadata: Record<string, unknown>
}

export interface GraphEdge {
  id: string
  source: string
  target: string
  source_port?: string | null
  target_port?: string | null
  source_handle?: string | null
  target_handle?: string | null
  kind?: 'normal' | 'branch' | 'reassessment'
  branch_label?: string | null
  loop_policy?: { max_iterations: number; exit_condition: string } | null
  label?: string | null
  metadata?: Record<string, unknown>
}

export interface WorkflowGraph {
  nodes: GraphNode[]
  edges: GraphEdge[]
}
