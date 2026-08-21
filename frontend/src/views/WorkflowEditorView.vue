<template>
  <section class="editor-page">
    <div v-if="errorMessage" class="notice notice--error"><CircleAlert :size="17" /><span>{{ errorMessage }}</span><button type="button" @click="loadProfiles">重试</button></div>
    <div class="editor-workspace">
      <NodePalette @add="addNode" />
      <WorkflowCanvas :graph="graph" :selected-node-id="selectedNodeId" @select="selectedNodeId = $event" @update="updateGraph" />
      <NodeInspector :node="selectedNode" @copy="copyNode" @delete="deleteNode" @paste="pasteNode" @update="updateNode">
        <template #default="{ node }"><NodeSemanticForm :node="node" :extraction-groups="extractionGroups" :model-profiles="modelProfiles" :knowledge-profiles="knowledgeProfiles" :field-options="fieldOptions" @update="updateNode" /></template>
      </NodeInspector>
    </div>

    <div class="editor-footnote"><Info :size="14" /><span>发布前后端会再次校验端点、分支和输出节点；前端提示只用于提前定位。</span></div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { CircleAlert, Info } from 'lucide-vue-next'

import { backfillConditionEdgeLabels, createGraphNode, toPersistedGraph } from '@/composables/useGraphAdapter'
import { useNodeClipboard } from '@/composables/useNodeClipboard'
import { buildFieldCatalog } from '@/composables/useWorkflowFields'
import { normalizeConditionConfig } from '@/composables/useConditionConfig'
import { getApiError } from '@/api/client'
import { listKnowledgeProfiles, listModelProfiles } from '@/api/profiles'
import { extractionConfigToForms, serializeExtractionConfig } from '@/composables/useExtractionConfig'
import { useWorkflowStore } from '@/stores/workflow'
import type { MedicalProfile } from '@/types/api'
import type { GraphNode, WorkflowGraph } from '@/types/graph'
import NodeInspector from '@/components/NodeInspector.vue'
import NodePalette from '@/components/NodePalette.vue'
import NodeSemanticForm from '@/components/forms/NodeSemanticForm.vue'
import WorkflowCanvas from '@/components/WorkflowCanvas.vue'

const store = useWorkflowStore()
const errorMessage = ref('')
const selectedNodeId = ref<string | null>(null)
const graph = ref<WorkflowGraph>({ nodes: [], edges: [] })
const clipboard = useNodeClipboard()
const modelProfiles = ref<MedicalProfile[]>([])
const knowledgeProfiles = ref<MedicalProfile[]>([])

const draft = computed(() => store.draft)
const selectedNode = computed(() => graph.value.nodes.find((node) => node.id === selectedNodeId.value) ?? null)
const extractionForms = computed(() => extractionConfigToForms(draft.value?.extraction))
const extractionGroups = computed(() => serializeExtractionConfig(extractionForms.value).groups)
const fieldOptions = computed(() => buildFieldCatalog(extractionForms.value, graph.value.nodes, selectedNodeId.value ?? undefined))

watch(() => store.draft?.graph, (value) => {
  graph.value = normalizeGraph(value)
}, { immediate: true })

onMounted(loadProfiles)

async function loadProfiles() {
  errorMessage.value = ''
  try {
    const [models, knowledge] = await Promise.allSettled([listModelProfiles(), listKnowledgeProfiles()])
    if (models.status === 'fulfilled') modelProfiles.value = models.value as MedicalProfile[]
    if (knowledge.status === 'fulfilled') knowledgeProfiles.value = knowledge.value as MedicalProfile[]
    const rejected = [models, knowledge].find((result) => result.status === 'rejected')
    if (rejected?.status === 'rejected') throw rejected.reason
  } catch (error) {
    errorMessage.value = getApiError(error).message
  }
}

function normalizeGraph(value: unknown): WorkflowGraph {
  if (!value || typeof value !== 'object') return { nodes: [], edges: [] }
  const candidate = value as Partial<WorkflowGraph>
  const nodes = Array.isArray(candidate.nodes) ? candidate.nodes.map((node) => {
    const raw = node as GraphNode
    const input_ports = Array.isArray(raw.input_ports) ? raw.input_ports.map((port) => typeof port === 'string' ? { id: port, label: port } : port) : []
    const output_ports = Array.isArray(raw.output_ports) ? raw.output_ports.map((port) => typeof port === 'string' ? { id: port, label: port } : port) : []
    if (raw.type !== 'condition') return { ...raw, input_ports, output_ports }
    const condition = normalizeConditionConfig(raw.config ?? {})
    return {
      ...raw,
      input_ports,
      output_ports: [
        { id: condition.truePort, label: condition.trueLabel },
        { id: condition.falsePort, label: condition.falseLabel },
      ],
    }
  }) as GraphNode[] : []
  return backfillConditionEdgeLabels({ nodes, edges: Array.isArray(candidate.edges) ? candidate.edges : [] })
}

function updateGraph(next: WorkflowGraph) {
  graph.value = next
  patchGraph()
}

function patchGraph() {
  store.patchLocal({ graph: toPersistedGraph(graph.value) as unknown as Record<string, unknown> })
}

function addNode(type: Parameters<typeof createGraphNode>[0]) {
  const node = createGraphNode(type, graph.value.nodes.length)
  graph.value = { ...graph.value, nodes: [...graph.value.nodes, node] }
  patchGraph()
  selectedNodeId.value = node.id
}

function updateNode(next: GraphNode) {
  const edges = next.type === 'condition'
    ? graph.value.edges.map((edge) => {
      if (edge.source !== next.id) return edge
      const config = normalizeConditionConfig(next.config)
      const sourcePort = edge.source_port ?? edge.source_handle
      const label = sourcePort === config.truePort ? config.trueLabel : sourcePort === config.falsePort ? config.falseLabel : undefined
      return label ? { ...edge, branch_label: label, label } : edge
    })
    : graph.value.edges
  graph.value = { ...graph.value, nodes: graph.value.nodes.map((node) => node.id === next.id ? next : node), edges }
  patchGraph()
}

function deleteNode() {
  if (!selectedNodeId.value) return
  graph.value = { nodes: graph.value.nodes.filter((node) => node.id !== selectedNodeId.value), edges: graph.value.edges.filter((edge) => edge.source !== selectedNodeId.value && edge.target !== selectedNodeId.value) }
  patchGraph()
  selectedNodeId.value = null
}

async function copyNode() {
  if (selectedNode.value) await clipboard.copy(selectedNode.value)
}

function pasteNode(next: GraphNode) {
  const imported = { ...next, id: `${next.id}-copy-${graph.value.nodes.length}`, position: { x: next.position.x + 60, y: next.position.y + 60 } }
  graph.value = { ...graph.value, nodes: [...graph.value.nodes, imported] }
  patchGraph()
  selectedNodeId.value = imported.id
}

</script>

<style scoped>
.editor-page { padding-top: 18px; }.notice { display: flex; gap: 10px; align-items: center; margin-bottom: 15px; padding: 12px 14px; color: var(--red-700); font-size: 13px; background: #fff0ef; border: 1px solid #e7bbb7; border-radius: var(--radius-sm); }.notice button { margin-left: auto; color: inherit; text-decoration: underline; cursor: pointer; background: none; border: 0; }.editor-workspace { display: grid; grid-template-columns: 160px minmax(660px, 1fr) 320px; min-height: 560px; overflow: hidden; background: var(--paper-100); border: 1px solid var(--line); box-shadow: var(--shadow-panel); }.editor-footnote { display: flex; gap: 8px; align-items: center; margin-top: 12px; color: var(--ink-650); font-size: 11px; }.editor-footnote svg { color: var(--teal-700); flex: 0 0 auto; }
@media (max-width: 1120px) {
  .editor-workspace { grid-template-columns: 150px minmax(580px, 1fr) 300px; overflow-x: auto; }
}
@media (max-width: 760px) {
  .editor-workspace { grid-template-columns: 145px 660px 300px; }
  .editor-footnote { align-items: flex-start; line-height: 1.5; }
}
</style>
