import { nextTick } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const api = vi.hoisted(() => ({
  createRun: vi.fn(),
  getRun: vi.fn(),
  getTraces: vi.fn(),
  listModelProfiles: vi.fn(),
}))

vi.mock('vue-router', async () => {
  const { reactive } = await import('vue')
  const route = reactive({ params: { id: 'workflow-A' } })
  return { useRoute: () => route }
})
vi.mock('@/api/runs', () => ({
  cancelRun: vi.fn(),
  createRun: api.createRun,
  getEvidence: vi.fn(),
  getRun: api.getRun,
  getTraces: api.getTraces,
}))
vi.mock('@/api/profiles', () => ({ listModelProfiles: api.listModelProfiles }))

import WorkflowTestView from '@/views/WorkflowTestView.vue'
import { useRunStore } from '@/stores/run'
import { useWorkflowStore } from '@/stores/workflow'
import { useRoute } from 'vue-router'

const run = {
  id: 'run-1', workflow_id: 'workflow-A', workflow_version_id: 'version-1', model_profile_id: null,
  mode: 'sync' as const, status: 'succeeded' as const, input_sha256: 'hash', input_summary: {}, output: null,
  error: null, started_at: null, finished_at: null, created_at: '2026-08-20T00:00:00Z',
}

describe('WorkflowTestView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    ;(useRoute() as unknown as { params: { id: string } }).params.id = 'workflow-A'
    useWorkflowStore().draft = { graph: { nodes: [], edges: [] } } as never
    api.createRun.mockImplementation((payload: { workflow_id: string }) => Promise.resolve({ ...run, workflow_id: payload.workflow_id }))
    api.getRun.mockResolvedValue(run)
    api.getTraces.mockResolvedValue([])
    api.listModelProfiles.mockResolvedValue([])
  })

  it('uses the current workflow id after the route reuses the component instance', async () => {
    const wrapper = mount(WorkflowTestView, {
      global: {
        stubs: { JsonComparePane: true, TraceTimeline: true, EvidenceDrawer: true },
      },
    })
    await wrapper.vm.$nextTick()
    const route = useRoute() as unknown as { params: { id: string } }
    route.params.id = 'workflow-B'
    await nextTick()

    await (wrapper.vm as unknown as { run: () => Promise<void> }).run()

    expect(api.createRun).toHaveBeenCalledWith(expect.objectContaining({ workflow_id: 'workflow-B' }))
    expect(useRunStore().run?.workflow_id).toBe('workflow-B')
  })

  it('clears the previous run state when the workflow id changes', async () => {
    const wrapper = mount(WorkflowTestView, {
      global: {
        stubs: { JsonComparePane: true, TraceTimeline: true, EvidenceDrawer: true },
      },
    })
    const activeRun = { ...run, status: 'running' as const }
    api.createRun.mockResolvedValue(activeRun)
    api.getRun.mockResolvedValue(activeRun)
    await (wrapper.vm as unknown as { run: () => Promise<void> }).run()
    expect((wrapper.vm as unknown as { polling: { active: { value: boolean } } }).polling.active.value).toBe(true)
    const store = useRunStore()
    store.setTraces([{ id: 'trace-1', evidence_refs: [] } as never])

    const route = useRoute() as unknown as { params: { id: string } }
    route.params.id = 'workflow-B'
    await nextTick()

    expect(store.run).toBeNull()
    expect(store.traces).toEqual([])
    expect((wrapper.vm as unknown as { polling: { active: { value: boolean } } }).polling.active.value).toBe(false)
  })
})
