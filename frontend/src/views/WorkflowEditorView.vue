<template>
  <section class="editor-page">
    <div class="editor-heading">
      <div>
        <p class="page-eyebrow">Workflow draft</p>
        <div class="title-row"><el-input v-if="draft" v-model="draft.name" class="title-input" @change="markNameDirty" /><h2 v-else>工作流编辑</h2><span v-if="draft" class="draft-badge">DRAFT v{{ draft.version_number }}</span></div>
        <p class="page-description">先定义资料入口，再把条件、证据和临床判断连成可追踪的路径。</p>
      </div>
      <div class="editor-actions">
        <RouterLink class="text-action" :to="`/workflows/${workflowId}/test`"><Play :size="15" />在线测试</RouterLink>
        <el-button :loading="store.saving" @click="save"><Save :size="15" />{{ store.saveLabel }}</el-button>
        <el-button type="primary" @click="publish"><Upload :size="15" />发布版本</el-button>
      </div>
    </div>

    <div v-if="errorMessage" class="notice notice--error"><CircleAlert :size="17" /><span>{{ errorMessage }}</span><button type="button" @click="load">重试</button></div>
    <div v-if="loading" class="loading-line">正在读取草稿...</div>
    <div v-else class="editor-workspace">
      <NodePalette @add="addNode" />
      <WorkflowCanvas :graph="graph" @select="selectedNodeId = $event" @update="updateGraph" />
      <NodeInspector :node="selectedNode" @copy="copyNode" @delete="deleteNode" @paste="pasteNode" @update="updateNode">
        <template #default="{ node }"><NodeSemanticForm :node="node" :extraction-groups="extractionGroups" :model-profiles="modelProfiles" :knowledge-profiles="knowledgeProfiles" @update="updateNode" /></template>
      </NodeInspector>
    </div>

    <DataPreparation :extraction="draft?.extraction" :workflow-id="workflowId" @error="errorMessage = $event" @update="updateExtraction" />

    <div class="editor-footnote"><Info :size="14" /><span>发布前后端会再次校验端点、分支和输出节点；前端提示只用于提前定位。</span></div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { CircleAlert, Info, Play, Save, Upload } from 'lucide-vue-next'

import { createGraphNode } from '@/composables/useGraphAdapter'
import { useNodeClipboard } from '@/composables/useNodeClipboard'
import { getApiError } from '@/api/client'
import { listKnowledgeProfiles, listModelProfiles } from '@/api/profiles'
import { extractionConfigToForms } from '@/composables/useExtractionConfig'
import { useWorkflowStore } from '@/stores/workflow'
import type { MedicalProfile } from '@/types/api'
import type { GraphNode, WorkflowGraph } from '@/types/graph'
import type { ExtractionConfig } from '@/types/api'
import DataPreparation from '@/components/DataPreparation.vue'
import NodeInspector from '@/components/NodeInspector.vue'
import NodePalette from '@/components/NodePalette.vue'
import NodeSemanticForm from '@/components/forms/NodeSemanticForm.vue'
import WorkflowCanvas from '@/components/WorkflowCanvas.vue'

const route = useRoute()
const store = useWorkflowStore()
const workflowId = String(route.params.id)
const loading = ref(true)
const errorMessage = ref('')
const selectedNodeId = ref<string | null>(null)
const graph = ref<WorkflowGraph>({ nodes: [], edges: [] })
const clipboard = useNodeClipboard()
const modelProfiles = ref<MedicalProfile[]>([])
const knowledgeProfiles = ref<MedicalProfile[]>([])

const draft = computed(() => store.draft)
const selectedNode = computed(() => graph.value.nodes.find((node) => node.id === selectedNodeId.value) ?? null)
const extractionGroups = computed(() => extractionConfigToForms(draft.value?.extraction).map((group) => ({ id: group.id, label: group.label, required: group.fields.filter((field) => field.required).map((field) => field.alias), fields: [] })))

onMounted(load)

async function load() {
  loading.value = true
  errorMessage.value = ''
  try {
    await store.loadDraft(workflowId)
    const [models, knowledge] = await Promise.allSettled([listModelProfiles(), listKnowledgeProfiles()])
    if (models.status === 'fulfilled') modelProfiles.value = models.value as MedicalProfile[]
    if (knowledge.status === 'fulfilled') knowledgeProfiles.value = knowledge.value as MedicalProfile[]
    graph.value = normalizeGraph(store.draft?.graph)
  } catch (error) {
    errorMessage.value = getApiError(error).message
  } finally {
    loading.value = false
  }
}

function normalizeGraph(value: unknown): WorkflowGraph {
  if (!value || typeof value !== 'object') return { nodes: [], edges: [] }
  const candidate = value as Partial<WorkflowGraph>
  return { nodes: Array.isArray(candidate.nodes) ? candidate.nodes as GraphNode[] : [], edges: Array.isArray(candidate.edges) ? candidate.edges : [] }
}

function updateGraph(next: WorkflowGraph) {
  graph.value = next
  store.patchLocal({ graph: next as unknown as Record<string, unknown> })
}

function addNode(type: Parameters<typeof createGraphNode>[0]) {
  const node = createGraphNode(type, graph.value.nodes.length)
  graph.value = { ...graph.value, nodes: [...graph.value.nodes, node] }
  store.patchLocal({ graph: graph.value as unknown as Record<string, unknown> })
  selectedNodeId.value = node.id
}

function updateNode(next: GraphNode) {
  graph.value = { ...graph.value, nodes: graph.value.nodes.map((node) => node.id === next.id ? next : node) }
  store.patchLocal({ graph: graph.value as unknown as Record<string, unknown> })
}

function updateExtraction(next: ExtractionConfig) {
  store.patchLocal({ extraction: next as unknown as Record<string, unknown> })
}

function deleteNode() {
  if (!selectedNodeId.value) return
  graph.value = { nodes: graph.value.nodes.filter((node) => node.id !== selectedNodeId.value), edges: graph.value.edges.filter((edge) => edge.source !== selectedNodeId.value && edge.target !== selectedNodeId.value) }
  store.patchLocal({ graph: graph.value as unknown as Record<string, unknown> })
  selectedNodeId.value = null
}

async function copyNode() {
  if (selectedNode.value) await clipboard.copy(selectedNode.value)
}

function pasteNode(next: GraphNode) {
  const imported = { ...next, id: `${next.id}-copy-${graph.value.nodes.length}`, position: { x: next.position.x + 60, y: next.position.y + 60 } }
  graph.value = { ...graph.value, nodes: [...graph.value.nodes, imported] }
  store.patchLocal({ graph: graph.value as unknown as Record<string, unknown> })
  selectedNodeId.value = imported.id
}

function markNameDirty() {
  if (draft.value) store.patchLocal({ name: draft.value.name })
}

async function save() {
  try { await store.saveDraft() } catch (error) { errorMessage.value = getApiError(error).message }
}

async function publish() {
  try { await store.publish() } catch (error) { errorMessage.value = getApiError(error).message }
}
</script>

<style scoped>
.editor-page { max-width: 1480px; margin: 0 auto; }.editor-heading { display: flex; gap: 18px; align-items: flex-end; justify-content: space-between; margin-bottom: 20px; }.page-eyebrow { margin: 0 0 6px; color: var(--teal-700); font-size: 11px; font-weight: 800; letter-spacing: .1em; text-transform: uppercase; }.title-row { display: flex; gap: 10px; align-items: center; }.title-row h2 { margin: 0; color: var(--ink-950); font-size: 27px; }.title-input { max-width: 430px; }.title-input :deep(.el-input__wrapper) { padding: 2px 10px; background: transparent; box-shadow: none; }.title-input :deep(input) { padding: 0; color: var(--ink-950); font-size: 27px; font-weight: 700; }.draft-badge { padding: 5px 8px; color: #7f4b08; font-size: 10px; font-weight: 800; background: #fff4da; border: 1px solid #e8c77e; border-radius: 999px; }.page-description { margin: 8px 0 0; color: var(--ink-650); font-size: 13px; }.editor-actions { display: flex; gap: 8px; align-items: center; }.editor-actions :deep(.el-button) { min-height: 36px; }.editor-actions :deep(.el-button--primary) { background: var(--teal-700); border-color: var(--teal-700); }.text-action { display: inline-flex; gap: 7px; align-items: center; padding: 0 7px; color: var(--teal-700); font-size: 13px; text-decoration: none; }.text-action:hover { color: var(--ink-950); }.notice { display: flex; gap: 10px; align-items: center; margin-bottom: 15px; padding: 12px 14px; color: var(--red-700); font-size: 13px; background: #fff0ef; border: 1px solid #e7bbb7; border-radius: var(--radius-sm); }.notice button { margin-left: auto; color: inherit; text-decoration: underline; cursor: pointer; background: none; border: 0; }.loading-line { padding: 26px 0; color: var(--ink-650); font-size: 13px; }.editor-workspace { display: grid; grid-template-columns: 160px minmax(660px, 1fr) 286px; min-height: 560px; overflow: hidden; background: var(--paper-100); border: 1px solid var(--line); box-shadow: var(--shadow-panel); }.editor-footnote { display: flex; gap: 8px; align-items: center; margin-top: 12px; color: var(--ink-650); font-size: 11px; }.editor-footnote svg { color: var(--teal-700); flex: 0 0 auto; }
@media (max-width: 1120px) { .editor-heading { display: block; }.editor-actions { margin-top: 15px; } .editor-workspace { grid-template-columns: 150px minmax(580px, 1fr) 260px; overflow-x: auto; } }
@media (max-width: 760px) { .editor-workspace { grid-template-columns: 145px 660px 250px; } .editor-footnote { align-items: flex-start; line-height: 1.5; } }
</style>
