import { describe, expect, it } from 'vitest'
import { modelFormToPayload, modelProfileToForm } from '@/composables/useModelProfileForm'
import { testModelProfile } from '@/api/profiles'
import { apiClient } from '@/api/client'

describe('model profile form adapter', () => {
  it('serializes the API key outside technical configuration', () => {
    const payload = modelFormToPayload({
      name: '测试模型', description: '说明', is_active: true, exposed_to_medical: true,
      base_url: ' http://models.test/v1 ', model: ' gpt-test ', api_key: ' sk-model-secret ',
      temperature: '0.2', top_p: '0.9', max_tokens: '2048', timeout: '30', retries: '2',
      display_name: '临床模型', clinical_scope: '乳腺', supported_tasks: '判断, 总结', output_style: '严谨',
    })
    expect(payload.technical_config).toEqual({
      provider: 'openai_compatible', base_url: 'http://models.test/v1', model: 'gpt-test',
      temperature: 0.2, top_p: 0.9, max_tokens: 2048, timeout: 30, retries: 2,
    })
    expect(payload.api_key).toBe('sk-model-secret')
    expect(payload.medical_options).toEqual({ display_name: '临床模型', clinical_scope: '乳腺', supported_tasks: ['判断', '总结'], output_style: '严谨' })
  })

  it('backfills model from legacy model_name and leaves a configured key blank while editing', () => {
    const form = modelProfileToForm({ name: 'x', description: null, exposed_to_medical: false, medical_options: {}, technical_config: { provider: 'openai_compatible', base_url: 'url', model_name: 'legacy' }, is_active: false, api_key_configured: true })
    expect(form.model).toBe('legacy')
    expect(form.api_key).toBe('')
    expect(form.api_key_configured).toBe(true)
    expect(modelFormToPayload({ ...form, api_key: '  ' })).not.toHaveProperty('api_key')
  })

  it('splits comma separated supported tasks and preserves arrays', () => {
    expect(modelFormToPayload({ supported_tasks: '判断, 总结', name: 'x' }).medical_options.supported_tasks).toEqual(['判断', '总结'])
    expect(modelFormToPayload({ supported_tasks: ['判断', '总结'], name: 'x' }).medical_options.supported_tasks).toEqual(['判断', '总结'])
  })

  it('sends only the typed technical configuration for a connection test', async () => {
    const request = vi.spyOn(apiClient, 'post').mockResolvedValue({ data: { ok: true, model: 'gpt-test', latency_ms: 1 } } as never)
    await testModelProfile({ provider: 'openai_compatible', base_url: 'http://models.test/v1', model: 'gpt-test', api_key: 'sk-test', profile_id: 'profile-1' })
    expect(request).toHaveBeenCalledWith('/api/v1/model-profiles/test', {
      technical_config: { provider: 'openai_compatible', base_url: 'http://models.test/v1', model: 'gpt-test' },
      api_key: 'sk-test',
      profile_id: 'profile-1',
    })
    request.mockRestore()
  })
})
