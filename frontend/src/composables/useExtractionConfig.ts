import type { ExtractionConfig } from '@/types/api'

export type ExtractionValueType = 'string' | 'number' | 'integer' | 'boolean' | 'object' | 'array' | 'any'
export type ExtractionTakeMode = 'all' | 'first' | 'latest'

export interface ExtractionFieldForm {
  alias: string
  path: string
  type: ExtractionValueType
  required: boolean
  defaultValue: unknown
  filterField: string
  filterValue: string
  sortBy: string
  order: 'asc' | 'desc'
  take: ExtractionTakeMode
  timeFrom: string
  timeTo: string
}

export interface ExtractionGroupForm {
  id: string
  label: string
  fields: ExtractionFieldForm[]
}

function optionalString(value: string) {
  return value.trim() || undefined
}

export function serializeExtractionConfig(groups: ExtractionGroupForm[]): ExtractionConfig {
  return {
    groups: groups.map((group) => ({
      id: group.id.trim(),
      label: group.label.trim(),
      required: group.fields.filter((field) => field.required).map((field) => field.alias.trim()).filter(Boolean),
      fields: group.fields.map((field) => {
        const filterField = optionalString(field.filterField)
        const filterValue = optionalString(field.filterValue)
        const sortBy = optionalString(field.sortBy)
        const timeFrom = optionalString(field.timeFrom)
        const timeTo = optionalString(field.timeTo)
        const hasArray = Boolean(filterField || filterValue || sortBy || timeFrom || timeTo || field.take !== 'all')
        return {
          alias: field.alias.trim(),
          path: field.path.trim(),
          type: field.type,
          required: field.required,
          default: field.defaultValue,
          ...(hasArray ? {
            array: {
              ...(filterField && filterValue ? { filter: { [filterField]: filterValue } } : {}),
              ...(sortBy ? { sort_by: sortBy } : {}),
              order: field.order,
              take: field.take,
              ...(timeFrom ? { time_from: timeFrom } : {}),
              ...(timeTo ? { time_to: timeTo } : {}),
            },
          } : {}),
        }
      }),
    })),
  }
}

export function extractionConfigToForms(config: unknown): ExtractionGroupForm[] {
  if (!config || typeof config !== 'object' || !Array.isArray((config as { groups?: unknown }).groups)) return []
  return ((config as { groups: Array<Record<string, unknown>> }).groups).map((group) => ({
    id: String(group.id ?? ''),
    label: String(group.label ?? ''),
    fields: Array.isArray(group.fields) ? group.fields.map((field) => {
      const array = field && typeof field === 'object' && field.array && typeof field.array === 'object' ? field.array as Record<string, unknown> : {}
      const filter = array.filter && typeof array.filter === 'object' ? array.filter as Record<string, unknown> : {}
      const [filterField, filterValue] = Object.entries(filter)[0] ?? ['', '']
      return {
        alias: String(field.alias ?? ''), path: String(field.path ?? '$'), type: (field.type ?? 'any') as ExtractionValueType, required: Boolean(field.required), defaultValue: field.default ?? null,
        filterField, filterValue: String(filterValue ?? ''), sortBy: String(array.sort_by ?? ''), order: array.order === 'desc' ? 'desc' : 'asc', take: (array.take ?? 'all') as ExtractionTakeMode,
        timeFrom: String(array.time_from ?? ''), timeTo: String(array.time_to ?? ''),
      }
    }) : [],
  }))
}
