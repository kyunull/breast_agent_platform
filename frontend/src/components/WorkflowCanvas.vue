<template>
  <div class="flow-canvas">
    <VueFlow :nodes="nodes" :edges="edges" :delete-key-code="['Backspace', 'Delete']" class="clinical-flow" fit-view-on-init :default-viewport="{ x: 0, y: 0, zoom: 0.9 }" @connect="onConnect" @node-click="onNodeClick" @update:nodes="onNodesChange" @update:edges="onEdgesChange">
      <Background :gap="20" color="#cbd2cc" pattern-color="#cbd2cc" />
      <Controls :show-interactive="false" />
      <template #node-clinical-node="nodeProps"><WorkflowNode v-bind="nodeProps" /></template>
    </VueFlow>
    <div class="canvas-status"><span></span>{{ nodes.length }} 个节点 · {{ edges.length }} 条连线</div>
  </div>
</template>

<script setup lang="ts">
import { shallowRef, watch } from 'vue'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { VueFlow, type Connection, type Edge, type Node, type NodeMouseEvent } from '@vue-flow/core'

import { toFlowEdge, toFlowNode, toGraphEdge, toGraphNode, type FlowNodeData } from '@/composables/useGraphAdapter'
import type { WorkflowGraph } from '@/types/graph'
import WorkflowNode from './WorkflowNode.vue'

const props = defineProps<{ graph: WorkflowGraph; selectedNodeId?: string | null }>()
const emit = defineEmits<{ update: [graph: WorkflowGraph]; select: [nodeId: string] }>()
const nodes = shallowRef<Node<FlowNodeData>[]>([])
const edges = shallowRef<Edge[]>([])
let syncingFromParent = false

watch(() => props.graph, (graph) => {
  syncingFromParent = true
  nodes.value = graph.nodes.map((node) => toFlowNode(node, node.id === props.selectedNodeId))
  edges.value = graph.edges.map(toFlowEdge)
  queueMicrotask(() => { syncingFromParent = false })
}, { deep: true, immediate: true })

watch(() => props.selectedNodeId, (selectedNodeId) => {
  nodes.value = nodes.value.map((node): Node<FlowNodeData> => {
    const data = node.data as FlowNodeData | undefined
    if (!data) return node
    return { ...node, data: { ...data, selected: node.id === selectedNodeId } }
  })
})

function syncGraph() {
  if (syncingFromParent) return
  const graph: WorkflowGraph = {
    nodes: nodes.value.map((node) => toGraphNode(node)),
    edges: edges.value.map((edge) => toGraphEdge(edge)),
  }
  if (JSON.stringify(graph) === JSON.stringify(props.graph)) return
  emit('update', graph)
}

function onNodesChange(nextNodes: Node<FlowNodeData>[]) {
  nodes.value = nextNodes
  syncGraph()
}

function onEdgesChange(nextEdges: Edge[]) {
  edges.value = nextEdges
  syncGraph()
}

function onConnect(connection: Connection) {
  if (!connection.source || !connection.target) return
  const isDuplicate = edges.value.some((edge) => edge.source === connection.source && edge.target === connection.target && edge.sourceHandle === connection.sourceHandle)
  if (isDuplicate) return
  const sourceNode = nodes.value.find((node) => node.id === connection.source)
  const sourceGraphNode = sourceNode?.data?.graphNode
  const isBranch = sourceGraphNode?.type === 'condition'
  const label = isBranch ? conditionPortLabel(sourceGraphNode, connection.sourceHandle) : undefined
  edges.value = [...edges.value, {
    ...connection,
    id: `edge-${crypto.randomUUID()}`,
    type: 'smoothstep',
    ...(label ? { label, data: { kind: 'branch' } } : {}),
  }]
  syncGraph()
}

function conditionPortLabel(node: FlowNodeData['graphNode'] | undefined, handle: string | null | undefined) {
  if (!node || !handle) return undefined
  const config = node.config
  const port = node.output_ports.find((item) => (typeof item === 'string' ? item : item.id) === handle)
  const fallbackLabel = typeof port === 'string' ? port : port?.label
  if (handle === String(config.true_port ?? 'satisfied')) return String(config.true_label ?? fallbackLabel ?? '满足')
  if (handle === String(config.false_port ?? 'unsatisfied')) return String(config.false_label ?? fallbackLabel ?? '不满足')
  return typeof port === 'string' ? port : port?.label
}

function onNodeClick(event: NodeMouseEvent) {
  emit('select', event.node.id)
}
</script>

<style scoped>
.flow-canvas { position: relative; min-width: 0; min-height: 560px; overflow: hidden; background: #edf0ec; }
.clinical-flow { width: 100%; height: 560px; }
.canvas-status { position: absolute; right: 12px; bottom: 10px; display: flex; gap: 6px; align-items: center; padding: 5px 8px; color: var(--ink-650); font-size: 10px; background: rgb(248 247 243 / 90%); border: 1px solid var(--line); border-radius: var(--radius-sm); pointer-events: none; }
.canvas-status span { width: 6px; height: 6px; background: var(--teal-600); border-radius: 50%; }
:deep(.vue-flow__controls) { box-shadow: 0 2px 8px rgb(16 38 49 / 15%); }
:deep(.vue-flow__controls-button) { color: var(--ink-800); background: var(--paper-100); border-bottom-color: var(--line); }
:deep(.vue-flow__edge-path) { stroke: #627d7a; stroke-width: 2; }
:deep(.vue-flow__handle) { width: 10px; height: 10px; background: var(--teal-700); border: 2px solid #fffefa; box-shadow: 0 0 0 1px #53736e; }
:deep(.vue-flow__handle.connecting) { background: var(--teal-600); box-shadow: 0 0 0 3px rgb(39 137 123 / 20%); }
@media (max-width: 760px) { .canvas-status { right: 10px; bottom: 9px; } }
</style>
