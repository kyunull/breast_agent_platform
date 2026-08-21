import type { ProfileCreatePayload } from '@/types/api'
export { testModelProfile } from '@/api/profiles'

export interface ModelProfileForm {
  name: string
  description: string
  is_active: boolean
  exposed_to_medical: boolean
  base_url: string
  model: string
  api_key: string
  api_key_configured: boolean
  temperature: number | string
  top_p: number | string
  max_tokens: number | string
  timeout: number | string
  retries: number | string
  display_name: string
  clinical_scope: string
  supported_tasks: string | string[]
  output_style: string
}

const text = (value: unknown): string => typeof value === 'string' ? value : value == null ? '' : String(value)
const numberOrValue = (value: unknown): number | string => typeof value === 'number' ? value : text(value)

type ModelProfileLike = Partial<{
  name: string
  description: string | null
  is_active: boolean
  exposed_to_medical: boolean
  medical_options: Record<string, unknown>
  technical_config: Record<string, unknown>
  api_key_configured?: boolean
}>

export function modelProfileToForm(profile?: ModelProfileLike): ModelProfileForm {
  const technical = profile?.technical_config ?? {}
  const medical = profile?.medical_options ?? {}
  return {
    name: profile?.name ?? '', description: profile?.description ?? '',
    is_active: profile?.is_active ?? true,
    exposed_to_medical: profile?.exposed_to_medical ?? false,
    base_url: text(technical.base_url), model: text(technical.model ?? technical.model_name), api_key: '', api_key_configured: Boolean(profile?.api_key_configured),
    temperature: numberOrValue(technical.temperature), top_p: numberOrValue(technical.top_p), max_tokens: numberOrValue(technical.max_tokens),
    timeout: numberOrValue(technical.timeout), retries: numberOrValue(technical.retries),
    display_name: text(medical.display_name), clinical_scope: text(medical.clinical_scope),
    supported_tasks: Array.isArray(medical.supported_tasks) ? medical.supported_tasks.map(text) : text(medical.supported_tasks),
    output_style: text(medical.output_style),
  }
}

export function modelFormToPayload(form: Partial<ModelProfileForm>): ProfileCreatePayload {
  const technical_config: Record<string, unknown> = {
    provider: 'openai_compatible', base_url: text(form.base_url).trim(), model: text(form.model).trim(),
  }
  const apiKey = text(form.api_key).trim()
  for (const [key, value] of [['temperature', form.temperature], ['top_p', form.top_p], ['max_tokens', form.max_tokens], ['timeout', form.timeout], ['retries', form.retries]] as const) {
    const raw = typeof value === 'string' ? value.trim() : value
    if (raw !== '' && raw != null && Number.isFinite(Number(raw))) technical_config[key] = Number(raw)
  }
  const tasks = Array.isArray(form.supported_tasks) ? form.supported_tasks.map(text).map(v => v.trim()).filter(Boolean) : text(form.supported_tasks).split(',').map(v => v.trim()).filter(Boolean)
  return {
    name: text(form.name).trim(), description: text(form.description).trim() || undefined,
    is_active: form.is_active, exposed_to_medical: Boolean(form.exposed_to_medical),
    technical_config,
    ...(apiKey ? { api_key: apiKey } : {}),
    medical_options: {
      display_name: text(form.display_name).trim(), clinical_scope: text(form.clinical_scope).trim(), supported_tasks: tasks, output_style: text(form.output_style).trim(),
    },
  }
}
