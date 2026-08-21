import type { GraphNode } from '@/types/graph'
import { breastCancerFieldLabel, breastCancerFieldTypeLabel } from '@/data/breastCancerInputSchema'

export interface WorkflowFieldOption {
  value: string
  label: string
  source: string
  type?: string
  typeLabel?: string
  path?: string
}

interface ExtractionFieldLike {
  alias?: unknown
  path?: unknown
  type?: unknown
}

interface ExtractionGroupLike {
  id?: unknown
  label?: unknown
  fields?: unknown
}

function addOption(options: WorkflowFieldOption[], seen: Set<string>, option: WorkflowFieldOption) {
  const value = option.value.trim()
  if (!value || seen.has(value)) return
  seen.add(value)
  options.push({ ...option, value })
}

function outputFields(node: GraphNode): Array<{ name: string; type?: string }> {
  const configured = node.config.output_fields
  if (Array.isArray(configured)) {
    return configured.flatMap((field) => {
      if (typeof field === 'string') return [{ name: field }]
      if (!field || typeof field !== 'object') return []
      const value = field as Record<string, unknown>
      const name = String(value.name ?? value.alias ?? value.path ?? '').trim()
      return name ? [{ name, type: typeof value.type === 'string' ? value.type : undefined }] : []
    })
  }
  if (configured && typeof configured === 'object') {
    return Object.entries(configured as Record<string, unknown>).map(([name, value]) => ({
      name,
      type: value && typeof value === 'object' && typeof (value as Record<string, unknown>).type === 'string'
        ? String((value as Record<string, unknown>).type)
        : undefined,
    }))
  }
  const legacy = String(node.config.output_alias ?? '').trim()
  return legacy ? [{ name: legacy }] : []
}

export function buildFieldCatalog(
  extractionGroups: ExtractionGroupLike[] = [],
  nodes: GraphNode[] = [],
  currentNodeId?: string,
): WorkflowFieldOption[] {
  const options: WorkflowFieldOption[] = []
  const seen = new Set<string>()

  for (const group of extractionGroups) {
    const groupId = String(group.id ?? '').trim()
    if (!groupId) continue
    const groupLabel = String(group.label ?? groupId).trim() || groupId
    const fields = Array.isArray(group.fields) ? group.fields as ExtractionFieldLike[] : []
    for (const field of fields) {
      const alias = String(field.alias ?? '').trim()
      if (!alias) continue
      addOption(options, seen, {
        value: `${groupId}.${alias}`,
        label: breastCancerFieldLabel(String(field.path ?? ''), alias),
        source: `数据准备 · ${groupLabel}`,
        type: typeof field.type === 'string' ? field.type : undefined,
        typeLabel: breastCancerFieldTypeLabel(String(field.path ?? ''), typeof field.type === 'string' ? field.type : ''),
        path: typeof field.path === 'string' ? field.path : undefined,
      })
    }
  }

  for (const node of nodes) {
    if (node.id === currentNodeId) continue
    for (const field of outputFields(node)) {
      addOption(options, seen, {
        value: `${node.id}.${field.name}`,
        label: field.name,
        source: `节点 · ${node.id}`,
        type: field.type,
        typeLabel: field.type ?? '',
      })
    }
  }

  return options
}
