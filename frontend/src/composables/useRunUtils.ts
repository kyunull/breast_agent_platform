import type { ApiErrorDetail, RunStatus, TraceResponse } from '@/types/api'

export function isRunTerminal(status: RunStatus | string) {
  return status === 'succeeded' || status === 'failed' || status === 'cancelled'
}

export function collectEvidenceRefs(output: Record<string, unknown> | null, traces: Array<Pick<TraceResponse, 'evidence_refs'>>): string[] {
  const refs: string[] = []
  const visit = (value: unknown) => {
    if (Array.isArray(value)) { value.forEach(visit); return }
    if (!value || typeof value !== 'object') return
    const record = value as Record<string, unknown>
    if (Array.isArray(record.evidence_refs)) record.evidence_refs.forEach((ref) => { if (typeof ref === 'string' && !refs.includes(ref)) refs.push(ref) })
    Object.entries(record).forEach(([key, child]) => { if (key !== 'evidence_refs') visit(child) })
  }
  visit(output)
  traces.forEach((trace) => trace.evidence_refs.forEach((ref) => { if (!refs.includes(ref)) refs.push(ref) }))
  return refs
}

export function formatRunError(error: ApiErrorDetail | null | undefined) {
  if (!error) return ''
  return `${error.code ?? 'run_failed'}：${error.message ?? '运行失败，请检查 trace。'}`
}
