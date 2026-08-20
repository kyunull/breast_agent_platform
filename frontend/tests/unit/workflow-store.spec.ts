import { setActivePinia, createPinia } from 'pinia'
import { useWorkflowStore } from '@/stores/workflow'
import * as workflowApi from '@/api/workflows'

vi.mock('@/api/workflows', () => ({
  getDraft: vi.fn(),
  listVersions: vi.fn(),
  listWorkflows: vi.fn(),
  createWorkflow: vi.fn(),
  patchDraft: vi.fn(),
  publishWorkflow: vi.fn(),
}))

const draft = {
  id: 'draft-1', workflow_id: 'workflow-1', version_number: 0, status: 'draft', name: 'Draft',
  description: null, graph: {}, extraction: {}, metadata: {}, template_refs: [], definition_sha256: null,
}

describe('workflow store draft context', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    vi.mocked(workflowApi.getDraft).mockResolvedValue(draft)
    vi.mocked(workflowApi.listVersions).mockResolvedValue([])
  })

  it('keeps a dirty draft and avoids API calls when ensuring the same workflow id', async () => {
    const store = useWorkflowStore()
    await store.loadDraft('workflow-1')
    store.patchLocal({ name: 'Changed' })
    await store.ensureDraft('workflow-1')
    expect(workflowApi.getDraft).toHaveBeenCalledTimes(1)
    expect(workflowApi.listVersions).toHaveBeenCalledTimes(1)
    expect(store.draft?.name).toBe('Changed')
    expect(store.dirty).toBe(true)
  })

  it('loads a different workflow id', async () => {
    const store = useWorkflowStore()
    await store.loadDraft('workflow-1')
    vi.mocked(workflowApi.getDraft).mockResolvedValue({ ...draft, workflow_id: 'workflow-2', id: 'draft-2', name: 'Other' })
    await store.ensureDraft('workflow-2')
    expect(workflowApi.getDraft).toHaveBeenCalledTimes(2)
    expect(workflowApi.listVersions).toHaveBeenCalledTimes(2)
    expect(store.draft?.workflow_id).toBe('workflow-2')
  })
})
