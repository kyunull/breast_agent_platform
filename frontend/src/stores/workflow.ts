import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import * as workflowApi from '@/api/workflows'
import { getApiError } from '@/api/client'
import type { DraftResponse, PublishedVersion, WorkflowSummary } from '@/types/api'

export const useWorkflowStore = defineStore('workflow', () => {
  const items = ref<WorkflowSummary[]>([])
  const draft = ref<DraftResponse | null>(null)
  const versions = ref<PublishedVersion[]>([])
  const selectedNodeId = ref<string | null>(null)
  const dirty = ref(false)
  const saving = ref(false)
  const error = ref<{ code: string; message: string } | null>(null)
  const saveLabel = computed(() => (saving.value ? '保存中' : dirty.value ? '未保存修改' : '已保存'))

  async function loadWorkflows() {
    error.value = null
    try {
      items.value = await workflowApi.listWorkflows()
    } catch (err) {
      error.value = getApiError(err)
    }
  }

  async function create(name: string, description?: string) {
    const created = await workflowApi.createWorkflow({ name, description })
    items.value = [created, ...items.value]
    return created
  }

  async function loadDraft(workflowId: string) {
    error.value = null
    draft.value = await workflowApi.getDraft(workflowId)
    versions.value = await workflowApi.listVersions(workflowId)
    dirty.value = false
  }

  function patchLocal(patch: Partial<DraftResponse>) {
    if (!draft.value) return
    draft.value = { ...draft.value, ...patch }
    dirty.value = true
  }

  async function saveDraft() {
    if (!draft.value || !dirty.value) return draft.value
    saving.value = true
    try {
      draft.value = await workflowApi.patchDraft(draft.value.workflow_id, {
        name: draft.value.name,
        description: draft.value.description,
        graph: draft.value.graph,
        extraction: draft.value.extraction,
        metadata: draft.value.metadata,
        template_refs: draft.value.template_refs,
      })
      dirty.value = false
      return draft.value
    } finally {
      saving.value = false
    }
  }

  async function publish() {
    if (!draft.value) return null
    await saveDraft()
    const published = await workflowApi.publishWorkflow(draft.value.workflow_id)
    versions.value = [published, ...versions.value]
    return published
  }

  return { items, draft, versions, selectedNodeId, dirty, saving, error, saveLabel, loadWorkflows, create, loadDraft, patchLocal, saveDraft, publish }
})
