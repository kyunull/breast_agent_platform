import { mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import ProfileSettingsView from '@/views/ProfileSettingsView.vue'

const api = vi.hoisted(() => ({ listModelProfiles: vi.fn(), listKnowledgeProfiles: vi.fn(), createModelProfile: vi.fn(), createKnowledgeProfile: vi.fn(), patchModelProfile: vi.fn(), patchKnowledgeProfile: vi.fn(), testModelProfile: vi.fn(), previewKnowledge: vi.fn() }))
vi.mock('@/api/profiles', () => api)
const modelProfile = { id: 'm1', name: '临床模型', description: null, is_active: true, exposed_to_medical: true, api_key_configured: true, technical_config: { provider: 'openai_compatible', base_url: 'https://models.example/v1', model: 'gpt-clinical' }, medical_options: {} }
const knowledgeProfile = { id: 'k1', name: '本地乳腺癌指南知识库', description: 'CACA、CSCO 与 NCCN 指南', is_active: true, exposed_to_medical: true, technical_config: { provider: 'knowledgebase', base_url: 'http://127.0.0.1:8101', search_path: '/search', top_k: 5, bm25: true, timeout: 120 }, medical_options: {} }
const mountView = () => mount(ProfileSettingsView, { attachTo: document.body, global: { plugins: [ElementPlus] } })
const dialogButtons = () => [...document.querySelectorAll<HTMLButtonElement>('.el-dialog button')]

describe('ProfileSettingsView', () => {
  beforeEach(() => { vi.clearAllMocks(); api.listModelProfiles.mockResolvedValue([]); api.listKnowledgeProfiles.mockResolvedValue([]) })
  afterEach(() => { document.body.innerHTML = '' })
  async function open(wrapper: ReturnType<typeof mountView>) { await wrapper.get('.page-heading button').trigger('click') }
  async function input(wrapper: ReturnType<typeof mountView>, field: 'name' | 'base_url' | 'model' | 'api_key', value: string) { (wrapper.vm as unknown as { modelForm: Record<string, string> }).modelForm[field] = value; await wrapper.vm.$nextTick() }

  it('shows a masked API Key input instead of an environment reference', async () => {
    const wrapper = mountView(); await open(wrapper)
    expect(document.body.textContent).toContain('模型服务'); expect(document.body.textContent).toContain('新增模型服务')
    expect(document.body.textContent).toContain('服务地址'); expect(document.body.textContent).toContain('API Key')
    expect(document.body.textContent).toContain('测试连接'); expect(document.body.textContent).not.toContain('密钥环境变量引用')
    expect(document.querySelector<HTMLInputElement>('input[type="password"]')).not.toBeNull()
    await input(wrapper, 'api_key', 'sk-secret')
    expect(document.querySelector('.el-input__password')).toBeNull()
  })

  it('blocks save and test when required model settings are incomplete', async () => {
    const wrapper = mountView(); await open(wrapper)
    dialogButtons()[dialogButtons().length - 1].click(); dialogButtons()[dialogButtons().length - 2].click(); await wrapper.vm.$nextTick()
    expect(document.body.textContent).toContain('请填写名称、服务地址和模型。'); expect(api.createModelProfile).not.toHaveBeenCalled(); expect(api.testModelProfile).not.toHaveBeenCalled()
  })

  it('lists model, service address, medical visibility, and enabled state', async () => {
    api.listModelProfiles.mockResolvedValue([modelProfile]); const wrapper = mountView()
    await vi.waitFor(() => expect(wrapper.text()).toContain('gpt-clinical'))
    expect(wrapper.text()).toContain('https://models.example/v1'); expect(wrapper.text()).toContain('对医学用户开放'); expect(wrapper.text()).toContain('运行中')
  })

  it('sends a directly entered key for testing and saving', async () => {
    api.testModelProfile.mockResolvedValue({ ok: true, model: 'gpt-test', latency_ms: 42 }); api.createModelProfile.mockResolvedValue({ ...modelProfile, name: '名称' })
    const wrapper = mountView(); await open(wrapper)
    await input(wrapper, 'name', '名称'); await input(wrapper, 'base_url', 'https://models.example/v1'); await input(wrapper, 'model', 'gpt-test'); await input(wrapper, 'api_key', 'sk-model-secret')
    dialogButtons().find(button => button.textContent?.trim() === '测试连接')!.click(); await vi.waitFor(() => expect(api.testModelProfile).toHaveBeenCalled())
    expect(api.testModelProfile).toHaveBeenCalledWith({ provider: 'openai_compatible', base_url: 'https://models.example/v1', model: 'gpt-test', api_key: 'sk-model-secret' }); await wrapper.vm.$nextTick(); expect(document.body.textContent).toContain('连接成功：gpt-test，耗时 42 毫秒')
    dialogButtons()[dialogButtons().length - 1].click(); await vi.waitFor(() => expect(api.createModelProfile).toHaveBeenCalled())
    expect(api.createModelProfile).toHaveBeenCalledWith(expect.objectContaining({ name: '名称', api_key: 'sk-model-secret', technical_config: { provider: 'openai_compatible', base_url: 'https://models.example/v1', model: 'gpt-test' } }))
  })

  it('keeps an existing key when editing with the password field left blank', async () => {
    api.listModelProfiles.mockResolvedValue([modelProfile]); api.patchModelProfile.mockResolvedValue(modelProfile)
    const wrapper = mountView(); await vi.waitFor(() => expect(wrapper.text()).toContain('临床模型'))
    expect(wrapper.text()).toContain('已配置凭据')
    await wrapper.get('[title="编辑临床模型"]').trigger('click')
    expect(document.querySelector<HTMLInputElement>('input[type="password"]')?.placeholder).toContain('已配置，留空将保留当前密钥')
    expect((wrapper.vm as unknown as { modelForm: { api_key: string } }).modelForm.api_key).toBe('')
    dialogButtons()[dialogButtons().length - 1].click(); await vi.waitFor(() => expect(api.patchModelProfile).toHaveBeenCalled())
    expect(api.patchModelProfile.mock.calls[0][1]).not.toHaveProperty('api_key')
  })

  it('uses a typed knowledge service form and saves the adapter settings', async () => {
    api.createKnowledgeProfile.mockResolvedValue(knowledgeProfile)
    const wrapper = mountView(); await wrapper.get('.profile-tabs button:nth-child(2)').trigger('click'); await open(wrapper)
    expect(document.body.textContent).toContain('检索连接');
    expect(document.body.textContent).toContain('返回条数')
    expect(document.body.textContent).toContain('关键词混合检索')
    expect(document.body.textContent).not.toContain('医学语义选项 JSON')
    expect(document.body.textContent).not.toContain('技术配置 JSON')
    Object.assign((wrapper.vm as unknown as { knowledgeForm: Record<string, unknown> }).knowledgeForm, {
      name: '本地乳腺癌指南知识库', base_url: 'http://127.0.0.1:8101', search_path: '/search', top_k: 5, timeout: 120, bm25: true,
    })
    await wrapper.vm.$nextTick(); dialogButtons()[dialogButtons().length - 1].click()
    await vi.waitFor(() => expect(api.createKnowledgeProfile).toHaveBeenCalled())
    expect(api.createKnowledgeProfile).toHaveBeenCalledWith(expect.objectContaining({
      name: '本地乳腺癌指南知识库',
      technical_config: expect.objectContaining({ provider: 'knowledgebase', base_url: 'http://127.0.0.1:8101', search_path: '/search', top_k: 5, bm25: true, timeout: 120 }),
    }))
  })

  it('lists knowledge metadata and previews retrieval for a saved service', async () => {
    api.listKnowledgeProfiles.mockResolvedValue([knowledgeProfile])
    api.previewKnowledge.mockResolvedValue({ evidence: [{ evidence_id: 'ev-1', text: 'HER2 阳性晚期乳腺癌应持续抗 HER2 治疗。', source_title: 'CACA 乳腺癌指南', locator: '第 44 页', score: 0.92 }] })
    const wrapper = mountView(); await wrapper.get('.profile-tabs button:nth-child(2)').trigger('click')
    await vi.waitFor(() => expect(wrapper.text()).toContain('本地乳腺癌指南知识库'))
    expect(wrapper.text()).toContain('本地知识库'); expect(wrapper.text()).toContain('http://127.0.0.1:8101')
    expect(wrapper.text()).toContain('对医学用户开放'); expect(wrapper.text()).toContain('运行中')
    await wrapper.get('[title="编辑本地乳腺癌指南知识库"]').trigger('click')
    ;(wrapper.vm as unknown as { previewQuery: string }).previewQuery = 'HER2 阳性乳腺癌如何治疗？'
    await wrapper.vm.$nextTick()
    dialogButtons().find(button => button.textContent?.trim() === '测试检索')!.click()
    await vi.waitFor(() => expect(api.previewKnowledge).toHaveBeenCalledWith({ knowledge_profile_id: 'k1', query: 'HER2 阳性乳腺癌如何治疗？', guideline_ids: [], version_ids: [], language: 'zh' }))
    await vi.waitFor(() => expect(document.body.textContent).toContain('找到 1 条证据'))
    expect(document.body.textContent).toContain('CACA 乳腺癌指南')
  })
})
