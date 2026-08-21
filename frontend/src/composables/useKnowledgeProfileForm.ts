import type { Profile, ProfileCreatePayload } from '@/types/api'

export type KnowledgeProvider = 'knowledgebase' | 'generic_http'

export interface KnowledgeProfileForm {
  name: string
  description: string
  provider: KnowledgeProvider
  base_url: string
  search_path: string
  api_key_ref: string
  top_k: number
  timeout: number
  bm25: boolean
  query_field: string
  result_path: string
  field_mapping: string
  is_active: boolean
  exposed_to_medical: boolean
}

function technical(profile?: Profile): Record<string, unknown> {
  return profile && 'technical_config' in profile ? profile.technical_config : {}
}

function stringValue(value: unknown, fallback = ''): string {
  return typeof value === 'string' ? value : fallback
}

function numberValue(value: unknown, fallback: number): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback
}

export function knowledgeProfileToForm(profile?: Profile): KnowledgeProfileForm {
  const config = technical(profile)
  const provider = config.provider === 'generic_http' || config.provider === 'http' ? 'generic_http' : 'knowledgebase'
  const mapping = config.field_mapping
  return {
    name: profile?.name ?? '',
    description: profile?.description ?? '',
    provider,
    base_url: stringValue(config.base_url),
    search_path: stringValue(config.search_path, '/search'),
    api_key_ref: stringValue(config.api_key_ref),
    top_k: numberValue(config.top_k, 5),
    timeout: numberValue(config.timeout, 120),
    bm25: typeof config.bm25 === 'boolean' ? config.bm25 : true,
    query_field: stringValue(config.query_field, 'query'),
    result_path: stringValue(config.result_path, 'evidence'),
    field_mapping: mapping && typeof mapping === 'object' ? JSON.stringify(mapping, null, 2) : '{}',
    is_active: !profile || !('is_active' in profile) || profile.is_active,
    exposed_to_medical: profile?.exposed_to_medical ?? true,
  }
}

export function knowledgeFormToPayload(form: KnowledgeProfileForm): ProfileCreatePayload {
  const technical_config: Record<string, unknown> = {
    provider: form.provider,
    base_url: form.base_url.trim().replace(/\/$/, ''),
    search_path: form.search_path.trim().startsWith('/') ? form.search_path.trim() : `/${form.search_path.trim()}`,
    top_k: Number(form.top_k),
    timeout: Number(form.timeout),
    bm25: form.bm25,
  }
  if (form.api_key_ref.trim()) technical_config.api_key_ref = form.api_key_ref.trim()
  if (form.provider === 'generic_http') {
    technical_config.query_field = form.query_field.trim() || 'query'
    technical_config.result_path = form.result_path.trim() || 'evidence'
    const mapping: unknown = JSON.parse(form.field_mapping || '{}')
    if (!mapping || typeof mapping !== 'object' || Array.isArray(mapping)) throw new Error('字段映射必须是 JSON 对象。')
    if (Object.keys(mapping).length) technical_config.field_mapping = mapping
  }
  return {
    name: form.name.trim(),
    description: form.description.trim() || undefined,
    exposed_to_medical: form.exposed_to_medical,
    is_active: form.is_active,
    medical_options: {},
    technical_config,
  }
}
