import { mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import ProfileSettingsView from '@/views/ProfileSettingsView.vue'

const api = vi.hoisted(() => ({ listModelProfiles: vi.fn(), listKnowledgeProfiles: vi.fn(), createModelProfile: vi.fn(), createKnowledgeProfile: vi.fn(), patchModelProfile: vi.fn(), patchKnowledgeProfile: vi.fn(), testModelProfile: vi.fn() }))
vi.mock('@/api/profiles', () => api)
const modelProfile = { id: 'm1', name: '临床模型', description: null, is_active: true, exposed_to_medical: true, technical_config: { provider: 'openai_compatible', base_url: 'https://models.example/v1', model: 'gpt-clinical' }, medical_options: {} }
const mountView = () => mount(ProfileSettingsView, { attachTo: document.body, global: { plugins: [ElementPlus] } })
const dialogButtons = () => [...document.querySelectorAll<HTMLButtonElement>('.el-dialog button')]

describe('ProfileSettingsView', () => {
  beforeEach(() => { vi.clearAllMocks(); api.listModelProfiles.mockResolvedValue([]); api.listKnowledgeProfiles.mockResolvedValue([]) })
  afterEach(() => { document.body.innerHTML = '' })
  async function open(wrapper: ReturnType<typeof mountView>) { await wrapper.get('.page-heading button').trigger('click') }
  async function input(wrapper: ReturnType<typeof mountView>, field: 'name' | 'base_url' | 'model' | 'api_key_ref', value: string) { (wrapper.vm as unknown as { modelForm: Record<string, string> }).modelForm[field] = value; await wrapper.vm.$nextTick() }

  it('shows the typed model service form without an API Key input', async () => {
    const wrapper = mountView(); await open(wrapper)
    expect(document.body.textContent).toContain('模型服务'); expect(document.body.textContent).toContain('新增模型服务')
    expect(document.body.textContent).toContain('服务地址'); expect(document.body.textContent).toContain('密钥环境变量引用')
    expect(document.body.textContent).toContain('测试连接'); expect(document.body.textContent).not.toContain('API Key')
  })

  it('blocks save and test when required model settings are incomplete or key reference is invalid', async () => {
    const wrapper = mountView(); await open(wrapper)
    dialogButtons()[dialogButtons().length - 1].click(); dialogButtons()[dialogButtons().length - 2].click(); await wrapper.vm.$nextTick()
    expect(document.body.textContent).toContain('请填写名称、服务地址和模型。'); expect(api.createModelProfile).not.toHaveBeenCalled(); expect(api.testModelProfile).not.toHaveBeenCalled()
    await input(wrapper, 'name', '名称'); await input(wrapper, 'base_url', 'https://models.example/v1'); await input(wrapper, 'model', 'gpt-test'); await input(wrapper, 'api_key_ref', 'lowercase')
    dialogButtons()[dialogButtons().length - 1].click(); await wrapper.vm.$nextTick()
    expect(document.body.textContent).toContain('密钥环境变量引用必须为大写 *_REF 名称'); expect(api.createModelProfile).not.toHaveBeenCalled()
  })

  it('lists model, service address, medical visibility, and enabled state', async () => {
    api.listModelProfiles.mockResolvedValue([modelProfile]); const wrapper = mountView()
    await vi.waitFor(() => expect(wrapper.text()).toContain('gpt-clinical'))
    expect(wrapper.text()).toContain('https://models.example/v1'); expect(wrapper.text()).toContain('对医学用户开放'); expect(wrapper.text()).toContain('启用')
  })

  it('sends only typed safe data for testing and saving', async () => {
    api.testModelProfile.mockResolvedValue({ ok: true, model: 'gpt-test', latency_ms: 42 }); api.createModelProfile.mockResolvedValue({ ...modelProfile, name: '名称' })
    const wrapper = mountView(); await open(wrapper)
    await input(wrapper, 'name', '名称'); await input(wrapper, 'base_url', 'https://models.example/v1'); await input(wrapper, 'model', 'gpt-test'); await input(wrapper, 'api_key_ref', 'MODEL_API_KEY_REF')
    dialogButtons().find(button => button.textContent?.trim() === '测试连接')!.click(); await vi.waitFor(() => expect(api.testModelProfile).toHaveBeenCalled())
    expect(api.testModelProfile).toHaveBeenCalledWith({ provider: 'openai_compatible', base_url: 'https://models.example/v1', model: 'gpt-test', api_key_ref: 'MODEL_API_KEY_REF' }); await wrapper.vm.$nextTick(); expect(document.body.textContent).toContain('连接成功：gpt-test，耗时 42 毫秒')
    dialogButtons()[dialogButtons().length - 1].click(); await vi.waitFor(() => expect(api.createModelProfile).toHaveBeenCalled())
    expect(api.createModelProfile).toHaveBeenCalledWith(expect.objectContaining({ name: '名称', technical_config: { provider: 'openai_compatible', base_url: 'https://models.example/v1', model: 'gpt-test', api_key_ref: 'MODEL_API_KEY_REF' } }))
  })

  it.each([['{', '{}', '医学语义选项必须是 JSON 对象。'], ['{}', '{', '技术配置必须是 JSON 对象。']])('reports invalid knowledge JSON', async (medical, technical, message) => {
    const wrapper = mountView(); await wrapper.get('.profile-tabs button:nth-child(2)').trigger('click'); await open(wrapper)
    const areas = document.querySelectorAll<HTMLTextAreaElement>('.el-dialog textarea'); areas[0].value = medical; areas[0].dispatchEvent(new Event('input')); areas[1].value = technical; areas[1].dispatchEvent(new Event('input')); await wrapper.vm.$nextTick(); dialogButtons()[dialogButtons().length - 1].click(); await wrapper.vm.$nextTick()
    expect(document.body.textContent).toContain(message); expect(api.createKnowledgeProfile).not.toHaveBeenCalled()
  })
})
