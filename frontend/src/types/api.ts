export type UserRole = 'admin_developer' | 'medical_user'

export interface LoginCredentials {
  username: string
  password: string
}

export interface TokenResponse {
  access_token: string
  token_type: 'bearer'
  expires_at: string
}

export interface User {
  id: string
  username: string
  display_name: string
  role: UserRole
  is_active: boolean
}

export interface ApiErrorDetail {
  code?: string
  message?: string
  issues?: Array<Record<string, unknown>>
  node_id?: string
  run_id?: string
  path?: string
  [key: string]: unknown
}

export interface WorkflowSummary {
  id: string
  owner_id: string | null
  name: string
  description: string | null
  draft_version_number: number
}

export interface DraftResponse {
  id: string
  workflow_id: string
  version_number: number
  status: 'draft' | string
  name: string
  description: string | null
  graph: Record<string, unknown>
  extraction: Record<string, unknown>
  metadata: Record<string, unknown>
  template_refs: string[]
  definition_sha256: string | null
}

export interface ExtractionField {
  alias: string
  path: string
  type: 'string' | 'number' | 'integer' | 'boolean' | 'object' | 'array' | 'any'
  required: boolean
  default: unknown
  array?: {
    filter?: Record<string, unknown>
    sort_by?: string
    order?: 'asc' | 'desc'
    take?: 'all' | 'first' | 'latest'
    time_from?: string
    time_to?: string
  }
}

export interface ExtractionGroup {
  id: string
  label: string
  fields: ExtractionField[]
  required: string[]
}

export interface ExtractionConfig {
  groups: ExtractionGroup[]
}

export interface PublishedVersion {
  id: string
  workflow_id: string
  version_number: number
  status: string
  definition: Record<string, unknown>
  extraction: Record<string, unknown>
  definition_sha256: string | null
  created_at: string
}

export interface MedicalProfile {
  id: string
  name: string
  description: string | null
  exposed_to_medical: boolean
  medical_options: Record<string, unknown>
}

export interface AdminProfile extends MedicalProfile {
  technical_config: Record<string, unknown>
  is_active: boolean
  api_key_configured?: boolean
}

export type Profile = MedicalProfile | AdminProfile

export interface ProfileCreatePayload {
  name: string
  description?: string
  exposed_to_medical: boolean
  is_active?: boolean
  medical_options: Record<string, unknown>
  technical_config: Record<string, unknown>
  api_key?: string
}

export interface ModelProfileConnectionTestResponse {
  ok: boolean
  model: string
  latency_ms: number
}

export type RunStatus = 'queued' | 'running' | 'succeeded' | 'failed' | 'cancelled'

export interface RunResponse {
  id: string
  workflow_id: string
  workflow_version_id: string
  model_profile_id: string | null
  mode: 'sync' | 'async'
  status: RunStatus
  input_sha256: string
  input_summary: Record<string, unknown>
  output: Record<string, unknown> | null
  error: ApiErrorDetail | null
  started_at: string | null
  finished_at: string | null
  created_at: string
}

export interface TraceResponse {
  id: string
  run_id: string
  node_id: string
  parent_trace_id: string | null
  status: string
  sequence: number
  attempt: number
  input_summary: Record<string, unknown>
  output: Record<string, unknown> | null
  error: ApiErrorDetail | null
  evidence_refs: string[]
  duration_ms: number | null
  started_at: string | null
  finished_at: string | null
  created_at: string
}

export interface EvidenceResponse {
  id: string
  run_id: string
  trace_id: string | null
  evidence_id: string
  raw_chunk_id: string
  text: string
  score: number | null
  source_title: string
  guideline_id: string | null
  version_id: string | null
  locator: string | null
  source_level: string | null
  open_url: string | null
  created_at: string
}

export interface PromptOptimizationResponse {
  id: string
  workflow_id: string
  node_id: string
  source_run_id: string
  original_prompt: string
  candidate_prompt: string | null
  instruction: string
  model_profile_id: string | null
  test_input_sha256: string | null
  result_diff: Record<string, unknown> | null
  status: string
  created_by: string
  created_at: string
  applied_at: string | null
}
