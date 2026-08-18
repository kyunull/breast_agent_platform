import type { UserRole } from '@/types/api'

const governedFields = ['temperature', 'top_p', 'top_k', 'bm25', 'score_threshold', 'deduplication', 'timeout', 'retries'] as const

export function visibleGovernedFields(role: UserRole): string[] {
  return role === 'admin_developer' ? [...governedFields] : []
}

export function isGovernedFieldVisible(role: UserRole, field: string) {
  return visibleGovernedFields(role).includes(field)
}
