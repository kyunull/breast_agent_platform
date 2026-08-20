import { defineComponent, h } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const api = vi.hoisted(() => ({
  getDraft: vi.fn(),
  listVersions: vi.fn(),
  listModelProfiles: vi.fn(),
  listKnowledgeProfiles: vi.fn(),
}))

vi.mock('vue-router', () => ({ useRoute: () => ({ params: { id: 'workflow-1' } }) }))
vi.mock('@/api/workflows', () => ({ getDraft: api.getDraft, listVersions: api.listVersions }))
vi.mock('@/api/profiles', () => ({ listModelProfiles: api.listModelProfiles, listKnowledgeProfiles: api.listKnowledgeProfiles }))
vi.mock('@/components/DataPreparation.vue', () => ({
  default: defineComponent({
    name: 'DataPreparation',
    props: { extraction: { type: Object, required: true }, workflowId: { type: String, required: true } },
    emits: ['update', 'error'],
    setup: () => () => h('div', { class: 'data-preparation-stub' }),
  }),
}))

import WorkflowDataView from '@/views/WorkflowDataView.vue'
import WorkflowEditorView from '@/views/WorkflowEditorView.vue'
import { useWorkflowStore } from '@/stores/workflow'

const draft = {
  id: 'draft-1', workflow_id: 'workflow-1', version_number: 0, status: 'draft', name: '测试工作流', description: null,
  graph: { nodes: [], edges: [] }, extraction: { groups: [] }, metadata: {}, template_refs: [], definition_sha256: null,
}

const editorStubs = {
  NodePalette: true,
  WorkflowCanvas: true,
  NodeInspector: true,
  NodeSemanticForm: true,
}

describe('workflow workspace views', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    api.getDraft.mockResolvedValue(draft)
    api.listVersions.mockResolvedValue([])
    api.listModelProfiles.mockResolvedValue([])
    api.listKnowledgeProfiles.mockResolvedValue([])
    const store = useWorkflowStore()
    store.draft = structuredClone(draft)
  })

  it('does not render data preparation in the workflow editor', () => {
    const wrapper = mount(WorkflowEditorView, { global: { stubs: editorStubs } })

    expect(wrapper.find('.data-preparation-stub').exists()).toBe(false)
  })

  it('renders data preparation only in the data view and patches shared extraction', async () => {
    const store = useWorkflowStore()
    const patchLocal = vi.spyOn(store, 'patchLocal')
    const wrapper = mount(WorkflowDataView)
    const extraction = { groups: [{ id: 'pathology', label: '病理', fields: [], required: [] }] }

    expect(wrapper.findAll('.data-preparation-stub')).toHaveLength(1)
    wrapper.findComponent({ name: 'DataPreparation' }).vm.$emit('update', extraction)
    await wrapper.vm.$nextTick()

    expect(patchLocal).toHaveBeenCalledWith({ extraction })
  })

  it('shows a retry notice when a profile request is rejected', async () => {
    api.listKnowledgeProfiles.mockRejectedValueOnce(new Error('profile unavailable'))
    const wrapper = mount(WorkflowEditorView, { global: { stubs: editorStubs } })

    await new Promise((resolve) => setTimeout(resolve, 0))

    expect(wrapper.find('.notice--error').exists()).toBe(true)
  })
})
