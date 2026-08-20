import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import ProfileSettingsView from '@/views/ProfileSettingsView.vue'

const profileApi = vi.hoisted(() => ({
  listModelProfiles: vi.fn(),
  listKnowledgeProfiles: vi.fn(),
}))

vi.mock('@/api/profiles', () => ({
  listModelProfiles: profileApi.listModelProfiles,
  listKnowledgeProfiles: profileApi.listKnowledgeProfiles,
  createModelProfile: vi.fn(),
  createKnowledgeProfile: vi.fn(),
  patchModelProfile: vi.fn(),
  patchKnowledgeProfile: vi.fn(),
  testModelProfile: vi.fn(),
}))

describe('ProfileSettingsView', () => {
  beforeEach(() => {
    profileApi.listModelProfiles.mockResolvedValue([])
    profileApi.listKnowledgeProfiles.mockResolvedValue([])
  })

  it('shows the administrator model service form without a raw API key field', async () => {
    const wrapper = mount(ProfileSettingsView)
    await vi.waitFor(() => expect(profileApi.listModelProfiles).toHaveBeenCalled())
    await wrapper.find('el-button').trigger('click')

    expect(wrapper.text()).toContain('模型服务')
    expect(wrapper.text()).toContain('新增模型服务')
    expect(wrapper.html()).toContain('服务地址')
    expect(wrapper.html()).toContain('密钥环境变量引用')
    expect(wrapper.text()).toContain('测试连接')
    expect(wrapper.text()).not.toContain('API Key')
  })
})
