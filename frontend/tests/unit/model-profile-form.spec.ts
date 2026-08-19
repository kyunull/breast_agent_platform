import { describe, expect, it } from 'vitest'
import { modelFormToPayload, modelProfileToForm } from '@/composables/useModelProfileForm'

describe('model profile form adapter', () => {
  it('serializes technical and medical model settings without raw api keys', () => {
    const payload = modelFormToPayload({
      name: '测试模型', description: '说明', is_active: true, exposed_to_medical: true,
      base_url: ' http://models.test/v1 ', model: ' gpt-test ', api_key_ref: ' MODEL_API_KEY_REF ',
      temperature: '0.2', top_p: '0.9', max_tokens: '2048', timeout: '30', retries: '2',
      display_name: '临床模型', clinical_scope: '乳腺', supported_tasks: '判断, 总结', output_style: '严谨',
    })
    expect(payload.technical_config).toEqual({
      provider: 'openai_compatible', base_url: 'http://models.test/v1', model: 'gpt-test',
      api_key_ref: 'MODEL_API_KEY_REF', temperature: 0.2, top_p: 0.9, max_tokens: 2048, timeout: 30, retries: 2,
    })
    expect(payload).not.toHaveProperty('api_key')
    expect(payload.medical_options).toEqual({ display_name: '临床模型', clinical_scope: '乳腺', supported_tasks: ['判断', '总结'], output_style: '严谨' })
  })

  it('backfills model from legacy model_name and omits empty key references', () => {
    const form = modelProfileToForm({ name: 'x', description: null, exposed_to_medical: false, medical_options: {}, technical_config: { provider: 'openai_compatible', base_url: 'url', model_name: 'legacy' }, is_active: false })
    expect(form.model).toBe('legacy')
    expect(modelFormToPayload({ ...form, api_key_ref: '  ' }).technical_config).not.toHaveProperty('api_key_ref')
  })

  it('splits comma separated supported tasks and preserves arrays', () => {
    expect(modelFormToPayload({ supported_tasks: '判断, 总结', name: 'x' }).medical_options.supported_tasks).toEqual(['判断', '总结'])
    expect(modelFormToPayload({ supported_tasks: ['判断', '总结'], name: 'x' }).medical_options.supported_tasks).toEqual(['判断', '总结'])
  })
})
