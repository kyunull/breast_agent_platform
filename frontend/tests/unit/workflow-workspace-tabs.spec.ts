import { mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import WorkflowWorkspaceTabs from '@/components/WorkflowWorkspaceTabs.vue'

const Dummy = { template: '<div />' }

describe('WorkflowWorkspaceTabs', () => {
  it('builds data, edit and test links and activates only current route', async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/workflows/:id/data', name: 'workflow-data', component: Dummy },
        { path: '/workflows/:id/edit', name: 'workflow-edit', component: Dummy },
        { path: '/workflows/:id/test', name: 'workflow-test', component: Dummy },
      ],
    })
    await router.push('/workflows/workflow-1/data')
    await router.isReady()
    const wrapper = mount(WorkflowWorkspaceTabs, {
      props: { workflowId: 'workflow-1' },
      global: { plugins: [router], stubs: { RouterLink: false } },
    })
    await wrapper.vm.$nextTick()
    const links = wrapper.findAll('a')
    expect(links.map((link) => link.attributes('href'))).toEqual([
      '/workflows/workflow-1/data',
      '/workflows/workflow-1/edit',
      '/workflows/workflow-1/test',
    ])
    expect(links[0].classes()).toContain('is-active')
    expect(links[1].classes()).not.toContain('is-active')
    expect(links[2].classes()).not.toContain('is-active')
  })
})
