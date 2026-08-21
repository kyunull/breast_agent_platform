import type { Edge, Node } from '@vue-flow/core'
import { toRaw } from 'vue'

import type { GraphEdge, GraphNode, GraphNodeType, GraphPort, WorkflowGraph } from '@/types/graph'

export interface FlowNodeData {
  graphNode: GraphNode
  label: string
  selected?: boolean
}

export interface NodeClipboardPayload {
  version: 1
  kind: 'breast-agent-workflow-node'
  node: GraphNode
}

interface PersistedGraphNode extends Omit<GraphNode, 'input_ports' | 'output_ports'> {
  input_ports: string[]
  output_ports: string[]
}

interface PersistedGraphEdge {
  id: string
  source: string
  target: string
  source_port: string
  target_port: string
  kind: 'normal' | 'branch' | 'reassessment'
  branch_label?: string
  loop_policy?: { max_iterations: number; exit_condition: string }
}

function cloneGraphValue<T>(value: T): T {
  const raw = toRaw(value)
  if (Array.isArray(raw)) return raw.map((item) => cloneGraphValue(item)) as T
  if (raw && typeof raw === 'object') {
    return Object.fromEntries(
      Object.entries(raw as Record<string, unknown>).map(([key, item]) => [key, cloneGraphValue(item)]),
    ) as T
  }
  return raw
}

export interface PersistedWorkflowGraph {
  nodes: PersistedGraphNode[]
  edges: PersistedGraphEdge[]
}

export function toFlowNode(node: GraphNode, selected = false): Node<FlowNodeData> {
  const rawNode = toRaw(node)
  return {
    id: rawNode.id,
    type: 'clinical-node',
    position: { x: rawNode.position.x, y: rawNode.position.y },
    data: { graphNode: cloneGraphValue(rawNode), label: rawNode.name, selected },
  }
}

export function toGraphNode(node: Node<FlowNodeData>): GraphNode {
  if (!node.data?.graphNode) throw new Error(`Vue Flow node ${node.id} is missing graph data`)
  const rawNode = toRaw(node)
  const rawData = toRaw(node.data)
  return {
    ...cloneGraphValue(rawData.graphNode),
    id: rawNode.id,
    position: { x: rawNode.position.x, y: rawNode.position.y },
  }
}

export function toFlowEdge(edge: GraphEdge): Edge {
  const sourcePort = edge.source_port ?? edge.source_handle ?? null
  const targetPort = edge.target_port ?? edge.target_handle ?? null
  const label = edge.branch_label ?? edge.label ?? undefined
  return {
    id: edge.id,
    source: edge.source,
    target: edge.target,
    sourceHandle: sourcePort,
    targetHandle: targetPort,
    label,
    data: { metadata: edge.metadata ?? {}, kind: edge.kind ?? (label ? 'branch' : 'normal'), loopPolicy: edge.loop_policy ?? undefined },
    type: 'smoothstep',
  }
}

export function toGraphEdge(edge: Edge): GraphEdge {
  const metadata = (edge.data?.metadata as Record<string, unknown> | undefined) ?? {}
  const kind = edge.data?.kind === 'reassessment' || edge.data?.kind === 'branch' ? edge.data.kind : (edge.label ? 'branch' : 'normal')
  const label = typeof edge.label === 'string' ? edge.label : null
  const loopPolicy = edge.data?.loopPolicy as GraphEdge['loop_policy'] | undefined
  return {
    id: edge.id,
    source: edge.source,
    target: edge.target,
    source_port: edge.sourceHandle ?? 'out',
    target_port: edge.targetHandle ?? 'in',
    kind,
    ...(label ? { branch_label: label } : {}),
    ...(loopPolicy ? { loop_policy: loopPolicy } : {}),
    metadata,
  }
}

export function toWorkflowGraph(nodes: Node<FlowNodeData>[], edges: Edge[]): WorkflowGraph {
  return { nodes: nodes.map(toGraphNode), edges: edges.map(toGraphEdge) }
}

export function backfillConditionEdgeLabels(graph: WorkflowGraph): WorkflowGraph {
  const nodes = new Map(graph.nodes.map((node) => [node.id, node]))
  return {
    ...graph,
    edges: graph.edges.map((edge) => {
      if (edge.branch_label || edge.label) return edge
      const node = nodes.get(edge.source)
      if (node?.type !== 'condition') return edge
      const sourcePort = edge.source_port ?? edge.source_handle
      const config = node.config
      const label = sourcePort === String(config.true_port ?? 'satisfied')
        ? String(config.true_label ?? '满足')
        : sourcePort === String(config.false_port ?? 'unsatisfied')
          ? String(config.false_label ?? '不满足')
          : (() => {
              const port = node.output_ports.find((item) => portId(item) === sourcePort)
              return typeof port === 'string' ? port : port?.label
            })()
      return label ? { ...edge, kind: 'branch', branch_label: label, label } : edge
    }),
  }
}

function portId(port: GraphPort | string): string {
  return typeof port === 'string' ? port : port.id
}

export function toPersistedGraph(graph: WorkflowGraph): PersistedWorkflowGraph {
  return {
    nodes: graph.nodes.map((node) => ({
      ...cloneGraphValue(node),
      input_ports: (node.input_ports ?? []).map(portId),
      output_ports: (node.output_ports ?? []).map(portId),
    })),
    edges: graph.edges.map((edge) => {
      const sourcePort = edge.source_port ?? edge.source_handle ?? 'out'
      const targetPort = edge.target_port ?? edge.target_handle ?? 'in'
      const label = edge.branch_label ?? edge.label
      return {
        id: edge.id,
        source: edge.source,
        target: edge.target,
        source_port: sourcePort,
        target_port: targetPort,
        kind: edge.kind ?? (label ? 'branch' : 'normal'),
        ...(label ? { branch_label: label } : {}),
        ...(edge.loop_policy ? { loop_policy: cloneGraphValue(edge.loop_policy) } : {}),
      }
    }),
  }
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
    node: sanitizeValue(cloneGraphValue(node)) as GraphNode,
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
    input_ports: type === 'input' ? [] : [{ id: 'in', label: '输入' }],
    output_ports: type === 'condition'
      ? [{ id: 'satisfied', label: '满足' }, { id: 'unsatisfied', label: '不满足' }]
      : type === 'output' ? [] : [{ id: 'out', label: '输出' }],
    config: type === 'condition'
      ? { operator: 'and', operands: [{ left: '', operator: 'not_empty', right: null }], true_port: 'satisfied', false_port: 'unsatisfied', true_label: '满足', false_label: '不满足', missing_strategy: 'false' }
      : {},
    metadata: {},
  }
}
