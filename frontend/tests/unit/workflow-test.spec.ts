import { nextTick } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import ElementPlus from 'element-plus'
import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const api = vi.hoisted(() => ({
  cancelRun: vi.fn(),
  createRun: vi.fn(),
  getEvidence: vi.fn(),
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
  cancelRun: api.cancelRun,
  createRun: api.createRun,
  getEvidence: api.getEvidence,
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
    api.cancelRun.mockResolvedValue(undefined)
    api.getEvidence.mockResolvedValue({ run_id: run.id, evidence_id: 'ev-1', title: 'A evidence', content: 'A' })
    api.getRun.mockResolvedValue(run)
    api.getTraces.mockResolvedValue([])
    api.listModelProfiles.mockResolvedValue([])
  })

  it('uses the current workflow id after the route reuses the component instance', async () => {
    const wrapper = mount(WorkflowTestView, {
      global: {
        plugins: [ElementPlus],
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
        plugins: [ElementPlus],
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

  it('ignores an in-flight polling result from the previous workflow', async () => {
    const wrapper = mount(WorkflowTestView, {
      global: {
        plugins: [ElementPlus],
        stubs: { JsonComparePane: true, TraceTimeline: true, EvidenceDrawer: true },
      },
    })
    const activeRun = { ...run, status: 'running' as const }
    let resolveRun!: (value: typeof activeRun) => void
    api.createRun.mockResolvedValue(activeRun)
    api.getRun.mockImplementation(() => new Promise((resolve) => { resolveRun = resolve }))

    const runPromise = (wrapper.vm as unknown as { run: () => Promise<void> }).run()
    await nextTick()
    expect((wrapper.vm as unknown as { polling: { active: { value: boolean } } }).polling.active.value).toBe(true)

    const route = useRoute() as unknown as { params: { id: string } }
    route.params.id = 'workflow-B'
    await nextTick()
    resolveRun(activeRun)
    await runPromise
    await nextTick()

    expect(useRunStore().run).toBeNull()
    expect(useRunStore().traces).toEqual([])
  })

  it('keeps the new workflow polling after a previous workflow request rejects', async () => {
    const wrapper = mount(WorkflowTestView, {
      global: {
        plugins: [ElementPlus],
        stubs: { JsonComparePane: true, TraceTimeline: true, EvidenceDrawer: true },
      },
    })
    const activeA = { ...run, id: 'run-A', workflow_id: 'workflow-A', status: 'running' as const }
    const activeB = { ...run, id: 'run-B', workflow_id: 'workflow-B', status: 'running' as const }
    let rejectA!: (reason?: unknown) => void
    let resolveB!: (value: typeof activeB) => void
    api.createRun.mockImplementation((payload: { workflow_id: string }) => Promise.resolve(payload.workflow_id === 'workflow-A' ? activeA : activeB))
    api.getRun
      .mockImplementationOnce(() => new Promise((_resolve, reject) => { rejectA = reject }))
      .mockImplementationOnce(() => new Promise((resolve) => { resolveB = resolve }))

    void (wrapper.vm as unknown as { run: () => Promise<void> }).run()
    await nextTick()
    const route = useRoute() as unknown as { params: { id: string } }
    route.params.id = 'workflow-B'
    await nextTick()
    void (wrapper.vm as unknown as { run: () => Promise<void> }).run()
    await nextTick()
    rejectA(new Error('A failed'))
    await nextTick()

    const vm = wrapper.vm as unknown as { polling: { active: { value: boolean }; error: { value: unknown } } }
    expect(vm.polling.active.value).toBe(true)
    expect(vm.polling.error.value).toBeNull()

    resolveB(activeB)
    await nextTick()
    expect(useRunStore().run?.workflow_id).toBe('workflow-B')
  })

  it('does not write a cancelled run after switching workflows', async () => {
    const wrapper = mount(WorkflowTestView, {
      global: {
        plugins: [ElementPlus],
        stubs: { JsonComparePane: true, TraceTimeline: true, EvidenceDrawer: true },
      },
    })
    const runA = { ...run, id: 'run-A', workflow_id: 'workflow-A', status: 'succeeded' as const }
    let resolveCancel!: () => void
    let resolveCancelledRun!: (value: typeof runA) => void
    api.createRun.mockResolvedValue(runA)
    api.cancelRun.mockImplementation(() => new Promise<void>((resolve) => { resolveCancel = resolve }))
    api.getRun.mockImplementation(() => new Promise((resolve) => { resolveCancelledRun = resolve }))

    await (wrapper.vm as unknown as { run: () => Promise<void> }).run()
    const cancelPromise = (wrapper.vm as unknown as { cancel: () => Promise<void> }).cancel()
    const route = useRoute() as unknown as { params: { id: string } }
    route.params.id = 'workflow-B'
    await nextTick()
    resolveCancel()
    await nextTick()
    resolveCancelledRun(runA)
    await cancelPromise

    expect(useRunStore().run).toBeNull()
  })

  it('does not open evidence from a previous workflow after switching', async () => {
    const wrapper = mount(WorkflowTestView, {
      global: {
        plugins: [ElementPlus],
        stubs: { JsonComparePane: true, TraceTimeline: true, EvidenceDrawer: true },
      },
    })
    const runA = { ...run, id: 'run-A', workflow_id: 'workflow-A', status: 'succeeded' as const }
    let resolveEvidence!: (value: { run_id: string; evidence_id: string; title: string; content: string }) => void
    api.createRun.mockResolvedValue(runA)
    api.getEvidence.mockImplementation(() => new Promise((resolve) => { resolveEvidence = resolve }))

    await (wrapper.vm as unknown as { run: () => Promise<void> }).run()
    const openPromise = (wrapper.vm as unknown as { openEvidence: (id: string) => Promise<void> }).openEvidence('ev-1')
    const route = useRoute() as unknown as { params: { id: string } }
    route.params.id = 'workflow-B'
    await nextTick()
    resolveEvidence({ run_id: 'run-A', evidence_id: 'ev-1', title: 'A evidence', content: 'A' })
    await openPromise

    expect(useRunStore().evidence).toBeNull()
    expect(useRunStore().isEvidenceOpen).toBe(false)
  })

  it('keeps the new workflow loading state when an old create request succeeds', async () => {
    const wrapper = mount(WorkflowTestView, {
      global: {
        plugins: [ElementPlus],
        stubs: { JsonComparePane: true, TraceTimeline: true, EvidenceDrawer: true },
      },
    })
    const runA = { ...run, id: 'run-A', workflow_id: 'workflow-A' }
    const runB = { ...run, id: 'run-B', workflow_id: 'workflow-B' }
    let resolveA!: (value: typeof runA) => void
    let resolveB!: (value: typeof runB) => void
    api.createRun
      .mockImplementationOnce(() => new Promise((resolve) => { resolveA = resolve }))
      .mockImplementationOnce(() => new Promise((resolve) => { resolveB = resolve }))

    const requestA = (wrapper.vm as unknown as { run: () => Promise<void> }).run()
    await nextTick()
    const route = useRoute() as unknown as { params: { id: string } }
    route.params.id = 'workflow-B'
    await nextTick()
    const requestB = (wrapper.vm as unknown as { run: () => Promise<void> }).run()
    await nextTick()

    resolveA(runA)
    await requestA
    await nextTick()

    expect((wrapper.vm as unknown as { running: boolean }).running).toBe(true)
    expect(useRunStore().run).toBeNull()

    resolveB(runB)
    await requestB
  })

  it('does not show an old create request error in the new workflow', async () => {
    const wrapper = mount(WorkflowTestView, {
      global: {
        plugins: [ElementPlus],
        stubs: { JsonComparePane: true, TraceTimeline: true, EvidenceDrawer: true },
      },
    })
    const runB = { ...run, id: 'run-B', workflow_id: 'workflow-B' }
    let rejectA!: (reason?: unknown) => void
    let resolveB!: (value: typeof runB) => void
    api.createRun
      .mockImplementationOnce(() => new Promise((_resolve, reject) => { rejectA = reject }))
      .mockImplementationOnce(() => new Promise((resolve) => { resolveB = resolve }))

    const requestA = (wrapper.vm as unknown as { run: () => Promise<void> }).run()
    await nextTick()
    const route = useRoute() as unknown as { params: { id: string } }
    route.params.id = 'workflow-B'
    await nextTick()
    const requestB = (wrapper.vm as unknown as { run: () => Promise<void> }).run()
    await nextTick()

    rejectA(new Error('workflow A failed'))
    await requestA
    await nextTick()

    expect((wrapper.vm as unknown as { running: boolean; errorMessage: string }).running).toBe(true)
    expect((wrapper.vm as unknown as { errorMessage: string }).errorMessage).toBe('')

    resolveB(runB)
    await requestB
  })

  it('uploads a complete JSON document into the masked test input', async () => {
    const wrapper = mount(WorkflowTestView, {
      global: {
        plugins: [ElementPlus],
        stubs: { JsonComparePane: true, TraceTimeline: true, EvidenceDrawer: true },
      },
    })
    const file = new File(['{"patient_data":{"age":42}}'], 'BC-001.json', { type: 'application/json' })
    const input = wrapper.get('input[type="file"]')
    Object.defineProperty(input.element, 'files', { value: [file] })

    await input.trigger('change')
    await wrapper.vm.$nextTick()

    expect(wrapper.find('textarea').element.value).toContain('"patient_data"')
    expect(wrapper.text()).toContain('BC-001.json')
  })

  it('keeps the current test input when an uploaded file is invalid', async () => {
    const wrapper = mount(WorkflowTestView, {
      global: {
        plugins: [ElementPlus],
        stubs: { JsonComparePane: true, TraceTimeline: true, EvidenceDrawer: true },
      },
    })
    const textarea = wrapper.find('textarea')
    await textarea.setValue('{"existing":true}')
    const file = new File(['[]'], 'array.json', { type: 'application/json' })
    const input = wrapper.get('input[type="file"]')
    Object.defineProperty(input.element, 'files', { value: [file] })

    await input.trigger('change')
    await wrapper.vm.$nextTick()

    expect(textarea.element.value).toBe('{"existing":true}')
    expect(wrapper.text()).toContain('上传内容必须是 JSON 对象。')
  })
})
