<template>
  <section class="field-contract">
    <div class="field-contract__heading">
      <div><strong>{{ title }}</strong><small>可选择已定义字段，也可直接输入新路径</small></div>
    </div>
    <div v-if="fields.length" class="field-contract__list">
      <div v-for="(field, index) in fields" :key="field.key" class="field-row">
        <el-select
          :model-value="field.path"
          filterable
          allow-create
          default-first-option
          clearable
          size="small"
          class="field-path"
          placeholder="选择或输入字段路径"
          @update:model-value="updateField(index, { path: $event, name: field.name || String($event).split('.').pop() })"
        >
          <el-option-group v-for="group in optionGroups" :key="group.source" :label="group.source">
            <el-option v-for="option in group.options" :key="option.value" :label="option.label" :value="option.value">
              <span class="field-option-label">{{ option.label }}</span><small>{{ option.path || option.value }}<em v-if="option.typeLabel">{{ option.typeLabel }}</em></small>
            </el-option>
          </el-option-group>
        </el-select>
        <el-input :model-value="field.name" size="small" class="field-name" placeholder="字段名" @update:model-value="updateField(index, { name: $event })" />
        <el-select :model-value="field.type" size="small" class="field-type" @update:model-value="updateField(index, { type: $event })">
          <el-option v-for="type in valueTypes" :key="type.value" :label="type.label" :value="type.value" />
        </el-select>
        <el-checkbox :model-value="field.required" class="field-required" title="必填" @update:model-value="updateField(index, { required: Boolean($event) })">必填</el-checkbox>
        <button type="button" class="field-remove" title="删除字段" @click="removeField(index)"><Trash2 :size="13" aria-hidden="true" /></button>
      </div>
    </div>
    <div v-else class="field-contract__empty">还没有{{ title }}，点击下方按钮添加。</div>
    <button type="button" class="field-add" @click="addField"><Plus :size="13" aria-hidden="true" />新增{{ title }}</button>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Plus, Trash2 } from 'lucide-vue-next'

import type { WorkflowFieldOption } from '@/composables/useWorkflowFields'

export interface FieldContract {
  key: string
  name: string
  path: string
  type: string
  required: boolean
}

const props = defineProps<{ title: string; modelValue: unknown; options?: WorkflowFieldOption[] }>()
const emit = defineEmits<{ 'update:modelValue': [value: FieldContract[]] }>()

const valueTypes = [
  { value: 'string', label: '文本' },
  { value: 'number', label: '数值' },
  { value: 'integer', label: '整数' },
  { value: 'boolean', label: '布尔' },
  { value: 'object', label: '对象' },
  { value: 'array', label: '数组' },
  { value: 'any', label: '任意' },
]

const fields = computed<FieldContract[]>(() => {
  if (!Array.isArray(props.modelValue)) return []
  return props.modelValue.map((item, index) => {
    const field = item && typeof item === 'object' ? item as Record<string, unknown> : {}
    return {
      key: String(field.key ?? `${index}-${String(field.path ?? '')}`),
      name: String(field.name ?? field.alias ?? ''),
      path: String(field.path ?? field.input ?? ''),
      type: String(field.type ?? 'any'),
      required: Boolean(field.required),
    }
  })
})

const optionGroups = computed(() => {
  const groups = new Map<string, WorkflowFieldOption[]>()
  for (const option of props.options ?? []) {
    const current = groups.get(option.source) ?? []
    current.push(option)
    groups.set(option.source, current)
  }
  return [...groups.entries()].map(([source, options]) => ({ source, options }))
})

function updateField(index: number, patch: Partial<FieldContract>) {
  const next = fields.value.map((field, fieldIndex) => fieldIndex === index ? { ...field, ...patch } : field)
  emit('update:modelValue', next)
}

function addField() {
  emit('update:modelValue', [...fields.value, { key: `field-${Date.now()}`, name: '', path: '', type: 'any', required: false }])
}

function removeField(index: number) {
  emit('update:modelValue', fields.value.filter((_, fieldIndex) => fieldIndex !== index))
}
</script>

<style scoped>
.field-contract { margin: 3px 0 15px; padding: 10px; background: #f7f9f5; border: 1px solid #d8e0d9; }
.field-contract__heading { margin-bottom: 9px; }.field-contract__heading div { display: grid; gap: 3px; }.field-contract__heading strong { color: var(--ink-950); font-size: 12px; }.field-contract__heading small { color: var(--ink-650); font-size: 10px; line-height: 1.4; }
.field-contract__list { display: grid; gap: 6px; }.field-row { display: grid; grid-template-columns: minmax(105px, 1.6fr) minmax(62px, .8fr) 68px 38px 22px; gap: 4px; align-items: center; }.field-path,.field-type { min-width: 0; }.field-row :deep(.el-input__wrapper),.field-row :deep(.el-select__wrapper) { padding: 1px 6px; }.field-row :deep(input),.field-row :deep(.el-select__selected-item) { font-size: 10px; }.field-required { margin: 0; color: var(--ink-650); font-size: 10px; }.field-required :deep(.el-checkbox__label) { padding-left: 3px; font-size: 10px; }.field-remove { display: grid; width: 22px; height: 24px; color: var(--red-700); place-items: center; cursor: pointer; background: transparent; border: 0; }.field-contract__empty { padding: 8px 0; color: var(--ink-650); font-size: 10px; }.field-add { display: inline-flex; gap: 4px; align-items: center; margin-top: 8px; padding: 0; color: var(--teal-700); font-size: 10px; cursor: pointer; background: transparent; border: 0; }.field-add:hover { color: var(--teal-800); }.field-row :deep(.el-select-dropdown__item) { line-height: 1.25; }.field-row :deep(.el-select-dropdown__item small) { display: flex; gap: 8px; align-items: center; color: var(--ink-650); font-size: 9px; }.field-row :deep(.el-select-dropdown__item small em) { color: var(--teal-700); font-style: normal; }
</style>
