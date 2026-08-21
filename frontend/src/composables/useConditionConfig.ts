export type ConditionLogic = 'and' | 'or'

export interface ConditionRule {
  left: string
  operator: string
  right: unknown
}

export interface ConditionEditorState {
  logic: ConditionLogic
  conditions: ConditionRule[]
  truePort: string
  falsePort: string
  trueLabel: string
  falseLabel: string
  missingStrategy: string
}

export const conditionOperators = [
  { label: '为空', value: 'empty', needsRight: false },
  { label: '不为空', value: 'not_empty', needsRight: false },
  { label: '等于', value: 'eq', needsRight: true },
  { label: '不等于', value: 'neq', needsRight: true },
  { label: '大于', value: 'gt', needsRight: true },
  { label: '小于', value: 'lt', needsRight: true },
  { label: '大于等于', value: 'gte', needsRight: true },
  { label: '小于等于', value: 'lte', needsRight: true },
  { label: '包含', value: 'contains', needsRight: true },
]

function stringValue(value: unknown, fallback = ''): string {
  return value === null || value === undefined ? fallback : String(value)
}

function normalizeRule(value: unknown): ConditionRule {
  const raw = value && typeof value === 'object' ? value as Record<string, unknown> : {}
  const operator = stringValue(raw.operator, 'not_empty')
  return {
    left: stringValue(raw.left ?? raw.value ?? raw.left_path),
    operator: operator === 'exists' ? 'not_empty' : operator,
    right: raw.right ?? raw.right_value ?? null,
  }
}

export function normalizeConditionConfig(config: Record<string, unknown>): ConditionEditorState {
  const operator = stringValue(config.operator).toLowerCase()
  const logic = (config.condition_logic === 'or' || operator === 'or') ? 'or' : 'and'
  const conditions = Array.isArray(config.operands)
    ? config.operands.map(normalizeRule)
    : [normalizeRule(config)]
  const truePort = stringValue(config.true_port ?? config.success_port, 'satisfied')
  const falsePort = stringValue(config.false_port ?? config.failure_port, 'unsatisfied')
  return {
    logic,
    conditions: conditions.length ? conditions : [{ left: '', operator: 'not_empty', right: null }],
    truePort,
    falsePort,
    trueLabel: '满足',
    falseLabel: '不满足',
    missingStrategy: stringValue(config.missing_strategy, 'false'),
  }
}

export function serializeConditionConfig(state: ConditionEditorState, previous: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    ...previous,
    operator: state.logic,
    operands: state.conditions.map((condition) => ({
      left: condition.left.trim(),
      operator: condition.operator,
      right: condition.right,
    })),
    true_port: state.truePort || 'satisfied',
    false_port: state.falsePort || 'unsatisfied',
    true_label: '满足',
    false_label: '不满足',
    missing_strategy: state.missingStrategy || 'false',
  }
}
