import { mount } from '@vue/test-utils'

import App from '@/App.vue'

describe('App', () => {
  it('mounts the clinical console router outlet', () => {
    const wrapper = mount(App)

    expect(wrapper.find('[data-testid="app-root"]').exists()).toBe(true)
  })
})
