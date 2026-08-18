import type { Edge, Node } from '@vue-flow/core'

import type { GraphEdge, GraphNode, GraphNodeType, WorkflowGraph } from '@/types/graph'

export interface FlowNodeData {
  graphNode: GraphNode
  label: string
}

export interface NodeClipboardPayload {
  version: 1
  kind: 'breast-agent-workflow-node'
  node: GraphNode
}

export function toFlowNode(node: GraphNode): Node<FlowNodeData> {
  return {
    id: node.id,
    type: 'clinical-node',
    position: node.position,
    data: { graphNode: structuredClone(node), label: node.name },
  }
}

export function toGraphNode(node: Node<FlowNodeData>): GraphNode {
  if (!node.data?.graphNode) throw new Error(`Vue Flow node ${node.id} is missing graph data`)
  return {
    ...structuredClone(node.data.graphNode),
    id: node.id,
    position: { x: node.position.x, y: node.position.y },
  }
}

export function toFlowEdge(edge: GraphEdge): Edge {
  return {
    id: edge.id,
    source: edge.source,
    target: edge.target,
    sourceHandle: edge.source_handle ?? null,
    targetHandle: edge.target_handle ?? null,
    label: edge.label ?? undefined,
    data: { metadata: edge.metadata ?? {} },
    type: 'smoothstep',
  }
}

export function toGraphEdge(edge: Edge): GraphEdge {
  return {
    id: edge.id,
    source: edge.source,
    target: edge.target,
    source_handle: edge.sourceHandle,
    target_handle: edge.targetHandle,
    label: typeof edge.label === 'string' ? edge.label : null,
    metadata: (edge.data?.metadata as Record<string, unknown> | undefined) ?? {},
  }
}

export function toWorkflowGraph(nodes: Node<FlowNodeData>[], edges: Edge[]): WorkflowGraph {
  return { nodes: nodes.map(toGraphNode), edges: edges.map(toGraphEdge) }
}

const sensitiveKey = /(?:api[_-]?key|secret|token|authorization|password|credential|patient(?:[_-]?(?:id|name|data))?|mrn|medical[_-]?record|身份证|患者)/i
const sampleKey = /(?:simulated?_?input|sample_?json|raw_?input|payload|example_?patient)/i

function sanitizeValue(value: unknown, key = ''): unknown {
  if (sensitiveKey.test(key)) return undefined
  if (sampleKey.test(key)) return { note: '请在粘贴后填入模拟样例，不包含真实患者资料。' }
  if (Array.isArray(value)) return value.map((item) => sanitizeValue(item)).filter((item) => item !== undefined)
  if (value && typeof value === 'object') {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>)
        .map(([entryKey, entryValue]) => [entryKey, sanitizeValue(entryValue, entryKey)] as const)
        .filter(([, entryValue]) => entryValue !== undefined),
    )
  }
  return value
}

export function sanitizeNodeClipboard(node: GraphNode): NodeClipboardPayload {
  return {
    version: 1,
    kind: 'breast-agent-workflow-node',
    node: sanitizeValue(structuredClone(node)) as GraphNode,
  }
}

export function stringifyNodeClipboard(node: GraphNode): string {
  return JSON.stringify(sanitizeNodeClipboard(node), null, 2)
}

export function parseNodeClipboard(text: string): { node: GraphNode | null; issues: string[] } {
  let raw: unknown
  try {
    raw = JSON.parse(text)
  } catch {
    return { node: null, issues: ['粘贴内容不是有效 JSON。'] }
  }
  const candidate = (raw as NodeClipboardPayload)?.node ?? raw
  if (!candidate || typeof candidate !== 'object') return { node: null, issues: ['粘贴内容不是节点对象。'] }
  const node = candidate as Partial<GraphNode>
  const issues: string[] = []
  if (!node.id || typeof node.id !== 'string') issues.push('缺少节点 id。')
  if (!node.type || typeof node.type !== 'string') issues.push('缺少节点类型。')
  if (!node.name || typeof node.name !== 'string') issues.push('缺少节点名称。')
  if (!node.position || typeof node.position.x !== 'number' || typeof node.position.y !== 'number') issues.push('节点坐标无效。')
  if (!node.config || typeof node.config !== 'object') issues.push('节点配置无效。')
  if (issues.length) return { node: null, issues }
  return { node: structuredClone(node as GraphNode), issues: [] }
}

export function createGraphNode(type: GraphNodeType, index: number): GraphNode {
  const labels: Record<GraphNodeType, string> = {
    input: '输入资料',
    condition: '临床条件',
    python_rule: '规则处理',
    rag: '指南检索',
    llm: '临床判断',
    parallel_agent: '并行 Agent',
    output: '方案输出',
    clinical_task: '资料补全任务',
    subworkflow: 'MDT 子工作流',
    annotation: '医学说明',
  }
  return {
    id: `${type}-${crypto.randomUUID()}`,
    type,
    name: labels[type],
    position: { x: 180 + (index % 3) * 300, y: 120 + Math.floor(index / 3) * 180 },
    input_ports: [{ id: 'input', label: '输入' }],
    output_ports: [{ id: 'output', label: '输出' }],
    config: {},
    metadata: {},
  }
}
