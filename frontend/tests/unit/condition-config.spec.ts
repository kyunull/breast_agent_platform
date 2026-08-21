import { normalizeConditionConfig, serializeConditionConfig } from '@/composables/useConditionConfig'

describe('condition config helpers', () => {
  it('normalizes the legacy single condition and keeps branch settings', () => {
    const state = normalizeConditionConfig({
      operator: 'eq',
      left_path: 'facts.stage',
      right_value: 'IV',
      true_port: 'yes',
      false_port: 'no',
      branch_label: '命中',
    })

    expect(state.logic).toBe('and')
    expect(state.conditions).toEqual([{ left: 'facts.stage', operator: 'eq', right: 'IV' }])
    expect(state.truePort).toBe('yes')
    expect(state.falsePort).toBe('no')
    expect(state.trueLabel).toBe('命中')
    expect(state.falseLabel).toBe('不满足')
  })

  it('serializes an ordered condition group with stable ports', () => {
    const config = serializeConditionConfig(
      {
        logic: 'or',
        conditions: [
          { left: 'facts.a', operator: 'empty', right: null },
          { left: 'facts.age', operator: 'gte', right: 18 },
        ],
        truePort: 'satisfied',
        falsePort: 'unsatisfied',
        trueLabel: '进入治疗',
        falseLabel: '补充资料',
        missingStrategy: 'false',
      },
      { legacy_key: 'keep-me' },
    )

    expect(config).toMatchObject({
      legacy_key: 'keep-me',
      operator: 'or',
      operands: [
        { left: 'facts.a', operator: 'empty', right: null },
        { left: 'facts.age', operator: 'gte', right: 18 },
      ],
      true_port: 'satisfied',
      false_port: 'unsatisfied',
      true_label: '进入治疗',
      false_label: '补充资料',
      missing_strategy: 'false',
    })
  })
})
