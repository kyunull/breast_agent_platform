<template>
  <div class="semantic-form">
    <template v-if="node.type === 'input'">
      <FormIntro title="输入资料" text="套用数据准备中已保存的字段分组，再向后续节点传递。" />
      <section class="input-extraction" :data-scope="inputExtractionScope">
        <div class="input-extraction__heading"><div><strong>数据准备方案</strong><small>上游已保存 {{ extractionGroups.length }} 个分组</small></div><span>{{ selectedExtractionGroups.length }} 个分组 · {{ selectedExtractionFieldCount }} 个字段</span></div>
        <div v-if="inputExtractionOutdated" class="input-extraction__notice">字段方案已更新，请重新套用以同步最新字段。</div>
        <el-radio-group :model-value="inputExtractionScope" size="small" @update:model-value="setInputExtractionScope">
          <el-radio-button value="all">全部资料分组</el-radio-button>
          <el-radio-button value="selected">指定分组</el-radio-button>
        </el-radio-group>
        <el-select v-if="inputExtractionScope === 'selected'" :model-value="selectedExtractionGroupIds" multiple collapse-tags collapse-tags-tooltip placeholder="选择一个或多个分组" class="input-extraction__groups" @update:model-value="setInputExtractionGroups">
          <el-option v-for="group in extractionGroups" :key="group.id" :label="`${group.label}（${group.fields.length} 字段）`" :value="group.id" />
        </el-select>
        <div class="input-extraction__footer"><span v-if="extractionGroups.length">字段路径将保留所属分组，避免同名字段冲突。</span><span v-else>请先在数据准备中保存提取字段和分组。</span><button type="button" class="input-extraction__apply" :disabled="!selectedExtractionGroups.length" @click="applyExtractionGroups"><Layers3 :size="14" aria-hidden="true" />套用字段方案</button></div>
      </section>
      <FieldContractEditor title="输入字段" :model-value="fieldConfig('input_fields')" :options="fieldOptions" @update:model-value="setConfig('input_fields', $event)" />
      <FieldContractEditor title="输出字段" :model-value="fieldConfig('output_fields')" :options="fieldOptions" @update:model-value="setConfig('output_fields', $event)" />
    </template>

    <template v-else-if="node.type === 'condition'">
      <FormIntro title="条件组" text="按条件顺序计算，用且/或组合后只进入“满足”或“不满足”其中一条路径。" />
      <el-form label-position="top" size="small">
        <el-form-item v-if="conditionState.conditions.length > 1" class="condition-logic" label="条件关系"><el-radio-group :model-value="conditionState.logic" @update:model-value="updateCondition({ logic: $event === 'or' ? 'or' : 'and' })"><el-radio-button value="and">且</el-radio-button><el-radio-button value="or">或</el-radio-button></el-radio-group></el-form-item>
        <div class="condition-rules">
          <div v-for="(condition, index) in conditionState.conditions" :key="`${index}-${condition.left}`" class="condition-rule">
            <div class="condition-rule__header"><span class="condition-rule__title">条件 {{ String(index + 1).padStart(2, '0') }}</span><button v-if="conditionState.conditions.length > 1" type="button" class="condition-remove" title="删除条件" @click="removeCondition(index)"><Trash2 :size="15" aria-hidden="true" /></button></div>
            <el-select :model-value="condition.left" filterable allow-create default-first-option placeholder="判断字段" @update:model-value="updateConditionRule(index, { left: String($event ?? '') })"><el-option-group v-for="group in fieldOptionGroups" :key="group.source" :label="group.source"><el-option v-for="option in group.options" :key="option.value" :label="option.label" :value="option.value"><span>{{ option.label }}</span><small>{{ option.path || option.value }}<em v-if="option.typeLabel">{{ option.typeLabel }}</em></small></el-option></el-option-group></el-select>
            <div class="condition-rule__comparison" :class="{ 'condition-rule__comparison--single': !needsRight(condition.operator) }"><el-select :model-value="condition.operator" placeholder="比较方式" @update:model-value="updateConditionRule(index, { operator: String($event ?? 'not_empty'), right: needsRight(String($event ?? 'not_empty')) ? condition.right : null })"><el-option v-for="option in conditionOperators" :key="option.value" :label="option.label" :value="option.value" /></el-select><el-input v-if="needsRight(condition.operator)" :model-value="condition.right === null ? '' : String(condition.right)" placeholder="比较值" @update:model-value="updateConditionRule(index, { right: $event })" /></div>
          </div>
        </div>
        <button type="button" class="condition-add" @click="addCondition"><Plus :size="15" aria-hidden="true" /><span>新增条件</span></button>
        <el-form-item label="缺失值策略"><el-select :model-value="conditionState.missingStrategy" @update:model-value="updateCondition({ missingStrategy: String($event) })"><el-option label="按不满足处理" value="false" /><el-option label="标记待补充" value="needs_review" /><el-option label="终止运行" value="error" /></el-select></el-form-item>
        <div class="branch-labels" aria-label="条件出口"><span>满足</span><span>不满足</span></div>
      </el-form>
    </template>

    <template v-else-if="node.type === 'python_rule'">
      <FormIntro title="规则处理" text="优先用可视化规则；高级代码仅对管理员/开发人员开放。" />
      <el-form label-position="top" size="small">
        <el-form-item label="规则动作"><el-select :model-value="stringConfig('rule_kind', 'field_map')" @update:model-value="setConfig('rule_kind', $event)"><el-option label="字段映射" value="field_map" /><el-option label="列表筛选" value="list_filter" /><el-option label="文本清理" value="text_normalize" /></el-select></el-form-item>
        <el-form-item label="模拟样例"><el-input :model-value="stringConfig('sample_note')" placeholder="只写脱敏样例说明" @update:model-value="setConfig('sample_note', $event)" /></el-form-item>
        <el-form-item v-if="auth.isAdmin" label="高级代码"><el-input :model-value="stringConfig('code')" :rows="5" type="textarea" placeholder="受控 RuleSpec/Python" @update:model-value="setConfig('code', $event)" /></el-form-item>
      </el-form>
      <FieldContractEditor title="输入字段" :model-value="fieldConfig('input_fields')" :options="fieldOptions" @update:model-value="setConfig('input_fields', $event)" />
      <FieldContractEditor title="输出字段" :model-value="fieldConfig('output_fields')" :options="fieldOptions" @update:model-value="setConfig('output_fields', $event)" />
    </template>

    <template v-else-if="node.type === 'rag'">
      <FormIntro title="指南检索" text="医学用户只选择已批准知识库和查询语义。" />
      <el-form label-position="top" size="small"><el-form-item label="知识库配置档案"><el-select :model-value="stringConfig('knowledge_profile_ref')" placeholder="选择知识库" @update:model-value="setConfig('knowledge_profile_ref', $event)"><el-option v-for="profile in knowledgeProfiles" :key="profile.id" :label="profile.name" :value="profile.id" /></el-select></el-form-item><el-form-item label="查询模板"><el-input :model-value="stringConfig('query_template')" :rows="3" type="textarea" placeholder="例如：{{her2_status}} 的晚期治疗建议" @update:model-value="setConfig('query_template', $event)" /></el-form-item><el-form-item label="无证据策略"><el-select :model-value="stringConfig('empty_strategy', 'needs_review')" @update:model-value="setConfig('empty_strategy', $event)"><el-option label="标记待核实" value="needs_review" /><el-option label="跳过本节点" value="skip" /><el-option label="终止运行" value="error" /></el-select></el-form-item><el-form-item label="引用要求"><el-switch :model-value="booleanConfig('citation_required', true)" @update:model-value="setConfig('citation_required', $event)" /></el-form-item><el-form-item v-if="auth.isAdmin" label="管理员检索参数"><el-input :model-value="stringConfig('technical_note')" placeholder="由配置档案控制，不写入医学用户草稿" @update:model-value="setConfig('technical_note', $event)" /></el-form-item></el-form>
    </template>

    <template v-else-if="node.type === 'llm'">
      <FormIntro title="临床判断" text="选择任务模板、提示词变量和语义化详细程度。" />
      <el-form label-position="top" size="small"><el-form-item label="任务模板"><el-select :model-value="stringConfig('task_template', '方案生成')" @update:model-value="setConfig('task_template', $event)"><el-option v-for="label in ['判断', '信息提取', '方案生成', '监测建议', '总结']" :key="label" :label="label" :value="label" /></el-select></el-form-item><el-form-item label="模型配置档案"><el-select :model-value="stringConfig('model_profile_ref')" placeholder="选择已批准模型" @update:model-value="setConfig('model_profile_ref', $event)"><el-option v-for="profile in modelProfiles" :key="profile.id" :label="profile.name" :value="profile.id" /></el-select></el-form-item><el-form-item label="详细程度"><el-radio-group :model-value="stringConfig('detail_level', 'standard')" @update:model-value="setConfig('detail_level', $event)"><el-radio-button value="concise">简洁</el-radio-button><el-radio-button value="standard">标准</el-radio-button><el-radio-button value="detailed">详细</el-radio-button></el-radio-group></el-form-item><el-form-item label="任务提示词"><el-input :model-value="stringConfig('prompt')" :rows="5" type="textarea" placeholder="使用 {{变量名}} 引用提取字段或 RAG 证据" @update:model-value="setConfig('prompt', $event)" /></el-form-item><el-form-item label="引用不足策略"><el-select :model-value="stringConfig('citation_policy', 'required')" @update:model-value="setConfig('citation_policy', $event)"><el-option label="必须有可追溯证据" value="required" /><el-option label="允许标记待核实" value="optional" /></el-select></el-form-item><el-form-item v-if="auth.isAdmin" label="高级模型参数"><el-input :model-value="stringConfig('temperature')" placeholder="temperature / top_p / 超时由管理员维护" @update:model-value="setConfig('temperature', $event)" /></el-form-item></el-form>
      <FieldContractEditor title="输入字段" :model-value="fieldConfig('input_fields')" :options="fieldOptions" @update:model-value="setConfig('input_fields', $event)" />
      <FieldContractEditor title="输出字段" :model-value="fieldConfig('output_fields')" :options="fieldOptions" @update:model-value="setConfig('output_fields', $event)" />
    </template>

    <template v-else-if="node.type === 'parallel_agent'">
      <FormIntro title="并行 Agent" text="拆分不同医学视角，完成后使用确定性方式合并。" />
      <el-form label-position="top" size="small"><el-form-item label="子任务（每行一个）"><el-input :model-value="stringConfig('tasks')" :rows="4" type="textarea" placeholder="疗效判断&#10;安全性监测&#10;指南差异" @update:model-value="setConfig('tasks', $event)" /></el-form-item><el-form-item label="合并方式"><el-select :model-value="stringConfig('merge_mode', 'deterministic')" @update:model-value="setConfig('merge_mode', $event)"><el-option label="确定性合并" value="deterministic" /><el-option label="汇总 LLM" value="llm_summary" /></el-select></el-form-item></el-form>
    </template>

    <template v-else-if="node.type === 'output'">
      <FormIntro title="方案输出" text="定义最终 JSON 结构，引用会从上游继承。" />
      <el-form label-position="top" size="small"><el-form-item label="终点类型"><el-radio-group :model-value="stringConfig('endpoint', 'recommendation')" @update:model-value="setConfig('endpoint', $event)"><el-radio-button value="recommendation">给出方案</el-radio-button><el-radio-button value="handoff">转入工作流</el-radio-button></el-radio-group></el-form-item><el-form-item label="输出 Schema"><el-input :model-value="stringConfig('schema')" :rows="6" type="textarea" placeholder="填写字段结构和必填项" @update:model-value="setConfig('schema', $event)" /></el-form-item></el-form>
      <FieldContractEditor title="输入字段" :model-value="fieldConfig('input_fields')" :options="fieldOptions" @update:model-value="setConfig('input_fields', $event)" />
      <FieldContractEditor title="输出字段" :model-value="fieldConfig('output_fields')" :options="fieldOptions" @update:model-value="setConfig('output_fields', $event)" />
    </template>

    <template v-else-if="node.type === 'clinical_task'">
      <FormIntro title="资料补全任务" text="列出缺口、来源和负责人，不伪造患者数据。" />
      <el-form label-position="top" size="small"><el-form-item label="待补充资料"><el-input :model-value="stringConfig('missing_fields')" :rows="3" type="textarea" @update:model-value="setConfig('missing_fields', $event)" /></el-form-item><el-form-item label="负责科室"><el-input :model-value="stringConfig('owner_department')" @update:model-value="setConfig('owner_department', $event)" /></el-form-item><el-form-item label="优先级"><el-select :model-value="stringConfig('priority', 'routine')" @update:model-value="setConfig('priority', $event)"><el-option label="常规" value="routine" /><el-option label="优先" value="high" /><el-option label="紧急" value="urgent" /></el-select></el-form-item></el-form>
    </template>

    <template v-else-if="node.type === 'subworkflow'">
      <FormIntro title="MDT 子工作流" text="引用固定版本并声明输入输出契约。" />
      <el-form label-position="top" size="small"><el-form-item label="子工作流 ID"><el-input :model-value="stringConfig('workflow_id')" @update:model-value="setConfig('workflow_id', $event)" /></el-form-item><el-form-item label="引用版本"><el-input :model-value="stringConfig('version_number')" placeholder="发布版本号" @update:model-value="setConfig('version_number', $event)" /></el-form-item><el-form-item label="协作说明"><el-input :model-value="stringConfig('handoff_note')" :rows="3" type="textarea" @update:model-value="setConfig('handoff_note', $event)" /></el-form-item></el-form>
    </template>

    <template v-else-if="node.type === 'annotation'">
      <FormIntro title="说明与协同" text="承载医学备注、风险、时间、成本和外部文档链接。" />
      <el-form label-position="top" size="small"><el-form-item label="说明内容"><el-input :model-value="stringConfig('note')" :rows="5" type="textarea" @update:model-value="setConfig('note', $event)" /></el-form-item><el-form-item label="外部链接"><el-input :model-value="stringConfig('external_url')" @update:model-value="setConfig('external_url', $event)" /></el-form-item></el-form>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, defineComponent, h } from 'vue'
import { Layers3, Plus, Trash2 } from 'lucide-vue-next'

import FieldContractEditor from './FieldContractEditor.vue'
import { conditionOperators, normalizeConditionConfig, serializeConditionConfig, type ConditionEditorState, type ConditionLogic, type ConditionRule } from '@/composables/useConditionConfig'
import type { WorkflowFieldOption } from '@/composables/useWorkflowFields'
import { useAuthStore } from '@/stores/auth'
import type { MedicalProfile, ExtractionGroup } from '@/types/api'
import type { GraphNode as WorkflowGraphNode, GraphPort } from '@/types/graph'

const FormIntro = defineComponent({
  props: { title: { type: String, required: true }, text: { type: String, required: true } },
  setup(props) { return () => h('div', { class: 'form-intro' }, [h('strong', props.title), h('span', props.text)]) },
})

const props = defineProps<{ node: WorkflowGraphNode; extractionGroups?: ExtractionGroup[]; modelProfiles?: MedicalProfile[]; knowledgeProfiles?: MedicalProfile[]; fieldOptions?: WorkflowFieldOption[] }>()
const emit = defineEmits<{ update: [node: WorkflowGraphNode] }>()
const auth = useAuthStore()
const node = computed(() => props.node)
const extractionGroups = computed(() => props.extractionGroups ?? [])
const modelProfiles = computed(() => props.modelProfiles ?? [])
const knowledgeProfiles = computed(() => props.knowledgeProfiles ?? [])
const fieldOptions = computed(() => props.fieldOptions ?? [])
const inputExtractionScope = computed<'all' | 'selected'>(() => {
  if (node.value.config.extraction_scope === 'selected') return 'selected'
  if (node.value.config.extraction_scope === 'all') return 'all'
  return stringConfig('group_id') ? 'selected' : 'all'
})
const selectedExtractionGroupIds = computed(() => {
  if (inputExtractionScope.value === 'all') return extractionGroups.value.map((group) => group.id)
  const configured = node.value.config.extraction_group_ids
  if (Array.isArray(configured)) return configured.map(String).filter((id) => extractionGroups.value.some((group) => group.id === id))
  const legacy = stringConfig('group_id')
  return legacy && extractionGroups.value.some((group) => group.id === legacy) ? [legacy] : []
})
const selectedExtractionGroups = computed(() => {
  const selected = new Set(selectedExtractionGroupIds.value)
  return extractionGroups.value.filter((group) => selected.has(group.id))
})
const selectedExtractionFieldCount = computed(() => selectedExtractionGroups.value.reduce((total, group) => total + group.fields.length, 0))
const selectedExtractionSignature = computed(() => extractionSignature(selectedExtractionGroups.value))
const inputExtractionOutdated = computed(() => {
  const applied = stringConfig('extraction_signature')
  return Boolean(applied && applied !== selectedExtractionSignature.value)
})
const conditionState = computed(() => normalizeConditionConfig(node.value.config))
const fieldOptionGroups = computed(() => {
  const groups = new Map<string, WorkflowFieldOption[]>()
  for (const option of fieldOptions.value) groups.set(option.source, [...(groups.get(option.source) ?? []), option])
  return [...groups.entries()].map(([source, options]) => ({ source, options }))
})

function stringConfig(key: string, fallback = '') {
  const value = node.value.config[key]
  return value === undefined || value === null ? fallback : String(value)
}

function booleanConfig(key: string, fallback = false) {
  const value = node.value.config[key]
  return value === undefined ? fallback : Boolean(value)
}

function fieldConfig(key: string) {
  const value = node.value.config[key]
  return Array.isArray(value) ? value : []
}

function setConfig(key: string, value: unknown) {
  emit('update', { ...node.value, config: { ...node.value.config, [key]: value } })
}

function updateInputExtractionSelection(scope: 'all' | 'selected', groupIds: string[]) {
  const { group_id: _legacyGroupId, ...config } = node.value.config
  emit('update', {
    ...node.value,
    config: { ...config, extraction_scope: scope, extraction_group_ids: groupIds },
  })
}

function setInputExtractionScope(value: unknown) {
  const scope = value === 'selected' ? 'selected' : 'all'
  const groupIds = scope === 'all'
    ? extractionGroups.value.map((group) => group.id)
    : selectedExtractionGroupIds.value.slice(0, 1)
  updateInputExtractionSelection(scope, groupIds)
}

function setInputExtractionGroups(value: unknown) {
  const ids = Array.isArray(value) ? value.map(String) : []
  updateInputExtractionSelection('selected', ids)
}

function extractionSignature(groups: ExtractionGroup[]) {
  return groups.flatMap((group) => group.fields.map((field) => `${group.id}:${field.alias}:${field.path}:${field.type}:${field.required}`)).join('|')
}

function applyExtractionGroups() {
  const fields = selectedExtractionGroups.value.flatMap((group) => group.fields.map((field) => ({
    key: `${group.id}.${field.alias}`,
    name: field.alias,
    path: `${group.id}.${field.alias}`,
    type: field.type,
    required: field.required || group.required.includes(field.alias),
  })))
  const { group_id: _legacyGroupId, ...config } = node.value.config
  emit('update', {
    ...node.value,
    config: {
      ...config,
      extraction_scope: inputExtractionScope.value,
      extraction_group_ids: selectedExtractionGroupIds.value,
      extraction_signature: selectedExtractionSignature.value,
      input_fields: fields,
      output_fields: fields.map((field) => ({ ...field })),
    },
  })
}

function needsRight(operator: string) {
  return conditionOperators.find((item) => item.value === operator)?.needsRight ?? true
}

function updateCondition(patch: Partial<ConditionEditorState>) {
  const state = { ...conditionState.value, ...patch }
  const config = serializeConditionConfig(state, node.value.config)
  const output_ports: GraphPort[] = [
    { id: state.truePort || 'satisfied', label: state.trueLabel.trim() || '满足' },
    { id: state.falsePort || 'unsatisfied', label: state.falseLabel.trim() || '不满足' },
  ]
  emit('update', { ...node.value, config, output_ports })
}

function updateConditionRule(index: number, patch: Partial<ConditionRule>) {
  const conditions = conditionState.value.conditions.map((condition, conditionIndex) => conditionIndex === index ? { ...condition, ...patch } : condition)
  updateCondition({ conditions })
}

function addCondition() {
  updateCondition({ conditions: [...conditionState.value.conditions, { left: '', operator: 'not_empty', right: null }] })
}

function removeCondition(index: number) {
  if (conditionState.value.conditions.length <= 1) return
  updateCondition({ conditions: conditionState.value.conditions.filter((_, conditionIndex) => conditionIndex !== index) })
}
</script>

<style scoped>
.semantic-form { padding-top: 3px; }.form-intro { display: grid; gap: 5px; margin: 0 0 14px; padding: 10px; color: var(--ink-650); background: #eef4f0; border-left: 3px solid var(--teal-600); }.form-intro strong { color: var(--ink-950); font-size: 12px; }.form-intro span { font-size: 11px; line-height: 1.45; }.semantic-form :deep(.el-form-item) { margin-bottom: 16px; }.semantic-form :deep(.el-select) { width: 100%; }.semantic-form :deep(.el-radio-group) { display: flex; flex-wrap: wrap; }.semantic-form :deep(.el-radio-button__inner) { padding: 7px 10px; font-size: 11px; }.semantic-form :deep(.el-switch) { --el-switch-on-color: var(--teal-700); }
.input-extraction { display: grid; gap: 10px; margin: 0 0 15px; padding: 11px; background: #f3f7f3; border: 1px solid #cfdad2; }.input-extraction__heading,.input-extraction__footer { display: flex; gap: 10px; align-items: center; justify-content: space-between; }.input-extraction__heading > div { display: grid; gap: 2px; }.input-extraction__heading strong { color: var(--ink-950); font-size: 12px; }.input-extraction__heading small,.input-extraction__footer > span { color: var(--ink-650); font-size: 10px; line-height: 1.4; }.input-extraction__heading > span { color: var(--teal-700); font-size: 10px; font-weight: 700; white-space: nowrap; }.input-extraction :deep(.el-radio-group) { display: grid; grid-template-columns: 1fr 1fr; }.input-extraction :deep(.el-radio-button),.input-extraction :deep(.el-radio-button__inner) { width: 100%; }.input-extraction__groups { width: 100%; }.input-extraction__apply { display: inline-flex; flex: 0 0 auto; gap: 5px; align-items: center; min-height: 29px; padding: 5px 9px; color: #fff; font-size: 10px; font-weight: 700; cursor: pointer; background: var(--teal-700); border: 1px solid var(--teal-700); border-radius: 4px; }.input-extraction__apply:disabled { color: #899490; cursor: not-allowed; background: #e4e9e5; border-color: #d3dbd5; }
.input-extraction__notice { padding: 7px 8px; color: #7d5910; font-size: 10px; line-height: 1.45; background: #fff4d9; border-left: 3px solid #c68a19; }
.condition-logic { margin-bottom: 14px !important; }.condition-rules { display: grid; gap: 12px; margin: 0 0 12px; }.condition-rule { display: grid; gap: 9px; padding: 10px; background: #263a38; border: 1px solid #45625e; border-radius: 6px; box-shadow: inset 0 1px 0 rgb(255 255 255 / 8%); }.condition-rule__header { display: flex; align-items: center; justify-content: space-between; min-height: 26px; }.condition-rule__title { color: #f4f8f5; font-size: 11px; font-weight: 700; line-height: 1; }.condition-rule__comparison { display: grid; grid-template-columns: minmax(0, 1fr) minmax(92px, .85fr); gap: 8px; }.condition-rule__comparison--single { grid-template-columns: minmax(0, 1fr); }.condition-rule :deep(.el-input__wrapper),.condition-rule :deep(.el-select__wrapper) { min-height: 30px; padding: 1px 8px; background: #f9fbf8; box-shadow: 0 0 0 1px #d3ddd6 inset; }.condition-rule :deep(input),.condition-rule :deep(.el-select__selected-item) { color: var(--ink-900); font-size: 11px; }.condition-remove { display: grid; width: 26px; height: 26px; color: #f5c1bc; place-items: center; cursor: pointer; background: #38504d; border: 1px solid #5d7974; border-radius: 4px; transition: background .15s ease, color .15s ease; }.condition-remove:hover { color: #fff4f1; background: #7d443f; border-color: #ba6b63; }.condition-add { display: flex; width: 100%; min-height: 34px; gap: 6px; align-items: center; justify-content: center; margin: 0 0 18px; padding: 7px 10px; color: #155e56; font-size: 12px; font-weight: 700; cursor: pointer; background: #e5f0eb; border: 1px solid #aac9be; border-radius: 5px; transition: background .15s ease, border-color .15s ease; }.condition-add:hover { color: #0e4b44; background: #d5e8e0; border-color: #77a99b; }.branch-labels { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }.condition-rule :deep(.el-select-dropdown__item) { line-height: 1.25; }.condition-rule :deep(.el-select-dropdown__item small) { display: flex; gap: 8px; align-items: center; color: var(--ink-650); font-size: 9px; }.condition-rule :deep(.el-select-dropdown__item small em) { color: var(--teal-700); font-style: normal; }
</style>
